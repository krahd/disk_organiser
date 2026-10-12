import XCTest
import AppKit
import Foundation
import WebKit
@testable import DiskInventoryCore
@testable import DiskInventoryDesktop

// Every actual directory read is still constructed and performed in this test
// target. The shared application receives only retired, bounded metadata bytes.
// Test-only count for cross-thread retirement evidence.
final class OwnedSourceCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func increment() { lock.lock(); count += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return count }
}

final class OwnedSourceProgressGate: @unchecked Sendable {
    private let lock = NSLock()
    private let resume = DispatchSemaphore(value: 0)
    private var didEnter = false
    private var expired = false
    var entered: Bool { lock.lock(); defer { lock.unlock() }; return didEnter }
    var timedOut: Bool { lock.lock(); defer { lock.unlock() }; return expired }
    func hold() {
        lock.lock()
        guard !didEnter else { lock.unlock(); return }
        didEnter = true; lock.unlock()
        if resume.wait(timeout: .now() + 5) != .success { lock.lock(); expired = true; lock.unlock() }
    }
    func release() { resume.signal() }
}

@MainActor
final class OwnedLibrarySource: LibrarySource {
    let choices = [LibraryChoice(id: "one", title: "Owned project folder", detail: "Fresh test source"),
                   LibraryChoice(id: "two", title: "Owned archive folder", detail: "Fresh partial test source")]
    let scopeDescription = "A temporary test-owned source only. No user folder is selected."
    var calls = 0
    var cancellations = 0
    var hold = false
    var continuation: CheckedContinuation<Void, Never>?
    private(set) var job: ObservationJob?
    var workerSeams = ObservationJob.Seams()
    var afterWorkerCancel: (() -> Void)?
    var receivedCounts: [Int] = []
    private(set) var completedSourceRoots: [String] = []
    private(set) var latestProgressCallback: (@MainActor (LibraryPreparationProgress) -> Void)?
    func prepare(_ choice: LibraryChoice, progress: @escaping @MainActor (LibraryPreparationProgress) -> Void) async throws -> Data {
        calls += 1
        latestProgressCallback = progress
        if hold { await withCheckedContinuation { continuation = $0 } }
        // This provider honours cancellation; the separate late-success provider
        // below exercises the session fence after successful worker retirement.
        let fixture = try OwnedFixture()
        try fixture.directory("Projects")
        try fixture.file("Projects/Design.txt", bytes: choice.id == "one" ? 600 : 700)
        if choice.id == "two" { try fixture.symlink("Excluded link") }
        let io = DarwinDirectoryIO()
        let released = OwnedSourceCounter()
        let lease = try fixture.lease(io: io, release: { @Sendable in released.increment() })
        let active = ObservationJob(controller: ObservationController(lease: lease, io: io), label: choice.title, seams: workerSeams)
        job = active
        let delivery = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                if let count = active.takeProgress(), let update = LibraryPreparationProgress(inspectedEntries: count) {
                    self?.receivedCounts.append(count); progress(update)
                }
                do { try await Task.sleep(for: .milliseconds(20)) } catch { return }
            }
        }
        let result: ObservationJob.Result
        do { result = try await active.run() }
        catch { delivery.cancel(); await delivery.value; job = nil; throw error }
        delivery.cancel(); await delivery.value; job = nil
        XCTAssertEqual(released.value, 1); try fixture.assertSentinel()
        if result.state == .cancelled { throw CancellationError() }
        let bytes = try XCTUnwrap(result.snapshot)
        completedSourceRoots.append(fixture.source)
        return bytes
    }
    func cancel() { cancellations += 1; job?.cancel(); afterWorkerCancel?() }
    func release() { let value = continuation; continuation = nil; value?.resume() }
}

// A separate test-only provider seals successful owned bytes before its hold.
// Its cancellation is deliberately non-cooperative only at data delivery, so the
// session must reject a real late success rather than merely catching an error.
@MainActor
final class LateSuccessfulLibrarySource: LibrarySource {
    private let owned = OwnedLibrarySource()
    var choices: [LibraryChoice] { owned.choices }
    var scopeDescription: String { owned.scopeDescription }
    private(set) var calls = 0
    private(set) var cancellations = 0
    private(set) var successfulReturns = 0
    private(set) var continuation: CheckedContinuation<Void, Never>?
    func prepare(_ choice: LibraryChoice, progress: @escaping @MainActor (LibraryPreparationProgress) -> Void) async throws -> Data {
        calls += 1
        let bytes = try await owned.prepare(choice, progress: progress)
        XCTAssertNil(owned.job)
        XCTAssertTrue(owned.completedSourceRoots.allSatisfy { !FileManager.default.fileExists(atPath: $0) })
        await withCheckedContinuation { continuation = $0 }
        successfulReturns += 1
        return bytes
    }
    func cancel() { cancellations += 1 }
    func release() { let value = continuation; continuation = nil; value?.resume() }
}

@MainActor
final class LibraryApplicationTests: XCTestCase {
    private var controlEventNumber = 1000
    func ready(_ session: LibrarySession, _ state: LibrarySession.State, seconds: TimeInterval = 5) async throws {
        let deadline = Date().addingTimeInterval(seconds)
        while session.state != state && Date() < deadline { try await Task.sleep(for: .milliseconds(20)) }
        XCTAssertEqual(session.state, state)
        guard session.state == state else { throw CataloguePreviewHost.Failure.expired }
    }
    func open(_ source: any LibrarySource) async throws -> (OwnedPreviewHarness, LibraryWindowController) {
        let h = try await OwnedPreviewHarness.open()
        let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: source))
        try h.useApplicationWindow(window.window); window.show()
        return (h, window)
    }
    // Polling and expected absence must not record an XCTest failure.
    func optionalButton(_ id: String, in window: NSWindow) -> NSButton? {
        func find(_ view: NSView) -> NSButton? {
            if let button = view as? NSButton, button.identifier?.rawValue == id { return button }
            for child in view.subviews { if let result = find(child) { return result } }
            return nil
        }
        return window.contentView.flatMap(find)
    }
    func button(_ id: String, in window: NSWindow) throws -> NSButton {
        try XCTUnwrap(optionalButton(id, in: window))
    }
    // AppKit controls use a tracking loop. Queue both events before dispatching
    // down so that the control can consume its corresponding native mouse-up.
    func clickNative(_ id: String, using h: OwnedPreviewHarness) async throws {
        let deadline = Date().addingTimeInterval(3)
        var selectedWindow: NSWindow?
        var selectedControl: NSButton?
        repeat {
            h.pumpApplicationEvents()
            let candidate = id == "window-close" ? h.window : (h.window.attachedSheet ?? h.window)
            candidate.contentView?.layoutSubtreeIfNeeded()
            let control: NSButton?
            if id == "window-close" {
                control = h.window.attachedSheet == nil ? candidate.standardWindowButton(.closeButton) : nil
            } else { control = optionalButton(id, in: candidate) }
            if let control, control.isEnabled, !control.isHiddenOrHasHiddenAncestor {
                NSApp.activate(ignoringOtherApps: true); candidate.makeKeyAndOrderFront(nil)
                if NSApp.isActive, candidate.isKeyWindow, candidate.isVisible {
                    selectedWindow = candidate; selectedControl = control; break
                }
            }
            try await Task.sleep(for: .milliseconds(20))
        } while Date() < deadline
        let window = try XCTUnwrap(selectedWindow)
        let control = try XCTUnwrap(selectedControl)
        guard NSApp.isActive, window.isKeyWindow, window.isVisible, control.isEnabled,
              !control.isHiddenOrHasHiddenAncestor else { throw CataloguePreviewHost.Failure.unavailable }
        let point = control.convert(NSPoint(x: control.bounds.midX, y: control.bounds.midY), to: nil)
        let parent = try XCTUnwrap(control.superview)
        let hit = control.hitTest(parent.convert(point, from: nil))
        let localVisible = control.visibleRect
        let centre = NSPoint(x: control.bounds.midX, y: control.bounds.midY)
        let ownHit = hit.map { $0 === control || $0.isDescendant(of: control) } ?? false
        print("OWNED_APP_HIT id=\(id) frame=\(control.frame) bounds=\(control.bounds) visible=\(localVisible) windowPoint=\(point) ownHit=\(ownHit) centreVisible=\(localVisible.contains(centre))")
        guard ownHit, localVisible.contains(centre) else { throw CataloguePreviewHost.Failure.unavailable }
        print("OWNED_APP_CONTROL id=\(id) active=\(NSApp.isActive) key=\(window.isKeyWindow) enabled=\(control.isEnabled) point=\(point)")
        for (offset, type) in [NSEvent.EventType.leftMouseDown, .leftMouseUp].enumerated() {
            controlEventNumber += 1
            let event = try XCTUnwrap(NSEvent.mouseEvent(with: type, location: point, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime + Double(offset) * 0.02,
                windowNumber: window.windowNumber, context: nil, eventNumber: controlEventNumber,
                clickCount: 1, pressure: offset == 0 ? 1 : 0))
            NSApp.postEvent(event, atStart: false)
        }
        h.pumpApplicationEvents(); try await Task.sleep(for: .milliseconds(30)); h.pumpApplicationEvents()
    }

    func testActualLibraryWindowNativeSelectionScopeAddAndCancel() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        let screens = try LibraryApplicationScreens(); defer { screens.close() }
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "0")
        XCTAssertFalse(try button("library-real-folder", in: h.window).isEnabled)
        XCTAssertEqual(source.calls, 0)
        try await screens.native("70-native-library-controls.png", view: window.chrome)
        try await clickNative("library-explore", using: h)
        XCTAssertEqual(window.session.state, .choosing)
        let sheet = try XCTUnwrap(h.window.attachedSheet)
        XCTAssertNotNil(sheet.firstResponder)
        try await screens.native("71-native-sample-selector.png", view: try XCTUnwrap(sheet.contentView))
        try await clickNative("library-choice-one", using: h)
        XCTAssertEqual(window.session.state, .scope); XCTAssertEqual(source.calls, 0)
        try await screens.native("72-native-scope-review.png", view: try XCTUnwrap(h.window.attachedSheet?.contentView))
        let gate = OwnedSourceProgressGate(); defer { gate.release() }
        source.workerSeams = .init(afterProgress: { count in if count == 3 { gate.hold() } })
        source.afterWorkerCancel = { gate.release() }
        try await clickNative("library-prepare", using: h)
        try await ready(window.session, .preparing)
        for _ in 0..<150 where window.session.inspectedEntries != 3 { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(window.session.inspectedEntries, 3); XCTAssertTrue(gate.entered)
        XCTAssertTrue(window.cancelButton.isEnabled)
        try await screens.native("73-native-progress-controls.png", view: window.chrome)
        // Genuine AppKit pointer cancellation while the worker is inside an
        // actual owned observation; the main actor must remain responsive.
        try await clickNative("library-cancel", using: h)
        try await ready(window.session, .ready)
        XCTAssertFalse(gate.timedOut); XCTAssertNil(source.job); XCTAssertNil(window.session.inspectedEntries)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "0")
        source.workerSeams = .init(); source.afterWorkerCancel = nil
        try await clickNative("library-explore", using: h)
        try await clickNative("library-choice-one", using: h)
        try await clickNative("library-prepare", using: h)
        try await ready(window.session, .reviewing)
        try await h.click("catalogue-confirm")
        try await clickNative("library-done", using: h)
        try await ready(window.session, .ready)
        XCTAssertTrue(window.session.hasTemporaryRecords)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "1")
        try await screens.web("74-native-library-record.png", harness: h)
        try await clickNative("library-explore", using: h)
        try await clickNative("library-sheet-cancel", using: h)
        XCTAssertEqual(window.session.state, .ready); XCTAssertEqual(source.calls, 2)
        XCTAssertTrue(h.window.firstResponder === window.exploreButton)
        try await clickNative("window-close", using: h)
        let closeSheet = try XCTUnwrap(h.window.attachedSheet)
        try await screens.native("75-native-close-confirmation.png", view: try XCTUnwrap(closeSheet.contentView))
        try await clickNative("library-keep", using: h)
        XCTAssertTrue(h.window.isVisible); XCTAssertEqual(window.session.state, .ready)
        try screens.finish()
    }

    func testCancelDuringPreparationDiscardsLateOwnedBytesAndAllowsNextChoice() async throws {
        let source = LateSuccessfulLibrarySource()
        let (h, window) = try await open(source); defer { source.release(); window.discardAndClose(); h.close() }
        let session = window.session
        session.choose(); session.select(source.choices[0]); session.prepare()
        for _ in 0..<100 where source.continuation == nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(source.continuation); XCTAssertEqual(source.successfulReturns, 0)
        session.cancel(); XCTAssertEqual(session.state, .stopping)
        session.choose(); session.prepare(); XCTAssertEqual(source.calls, 1)
        source.release(); try await ready(session, .ready)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "0")
        XCTAssertEqual(source.successfulReturns, 1); XCTAssertEqual(h.host.state, .ready)
        XCTAssertFalse(session.hasTemporaryRecords); XCTAssertEqual(source.cancellations, 1)
        session.choose(); XCTAssertEqual(session.state, .choosing)
        session.select(source.choices[1]); session.prepare()
        for _ in 0..<100 where source.continuation == nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(source.continuation); XCTAssertEqual(source.successfulReturns, 1)
        source.release(); try await ready(session, .reviewing)
        XCTAssertEqual(source.successfulReturns, 2)
        try await h.click("catalogue-cancel"); session.finishReview(); try await ready(session, .ready)
        XCTAssertFalse(session.hasTemporaryRecords)
    }

    func testCloseDuringPreparationCannotReviveNativeLibrary() async throws {
        let source = LateSuccessfulLibrarySource()
        let (h, window) = try await open(source); defer { source.release(); window.discardAndClose(); h.close() }
        let session = window.session
        session.choose(); session.select(source.choices[0]); session.prepare()
        for _ in 0..<100 where source.continuation == nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(source.continuation); XCTAssertEqual(source.successfulReturns, 0)
        window.discardAndClose(); source.release()
        for _ in 0..<100 where source.successfulReturns != 1 { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(source.successfulReturns, 1)
        XCTAssertEqual(session.state, .closed); XCTAssertEqual(h.host.state, .closed)
        XCTAssertFalse(h.window.isVisible); XCTAssertFalse(session.hasTemporaryRecords)
    }

    func testNativeCancelBeforePrepareAndUnknownChoiceNeverReads() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        let session = window.session
        session.select(source.choices[0]); session.prepare(); XCTAssertEqual(source.calls, 0)
        session.choose(); session.select(LibraryChoice(id: "../../outside", title: "Invalid", detail: ""))
        XCTAssertEqual(session.state, .choosing)
        session.select(source.choices[0]); session.cancel(); session.prepare()
        XCTAssertEqual(source.calls, 0); XCTAssertEqual(session.state, .ready)
        session.choose(); session.cancel(); XCTAssertEqual(source.calls, 0)
    }

    func testNativeEscapeCancelsSampleSheetAndReturnsFocus() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        try await clickNative("library-explore", using: h)
        let sheet = try XCTUnwrap(h.window.attachedSheet)
        XCTAssertTrue(sheet.isKeyWindow); XCTAssertNotNil(sheet.firstResponder)
        for type in [NSEvent.EventType.keyDown, .keyUp] {
            let event = try XCTUnwrap(NSEvent.keyEvent(with: type, location: .zero, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: sheet.windowNumber,
                context: nil, characters: "\u{1b}", charactersIgnoringModifiers: "\u{1b}",
                isARepeat: false, keyCode: 53))
            NSApp.sendEvent(event); h.pumpApplicationEvents()
        }
        try await ready(window.session, .ready)
        XCTAssertNil(h.window.attachedSheet); XCTAssertEqual(source.calls, 0)
        XCTAssertTrue(h.window.firstResponder === window.exploreButton)
    }

    func testBundledExamplesAreExplicitFixedDataAndUseUnchangedParser() async throws {
        let source = BundledLibraryExamples()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        for item in source.choices {
            window.session.choose(); window.session.select(item); window.session.prepare()
            try await ready(window.session, .reviewing)
            try await h.click("catalogue-confirm"); window.session.finishReview()
            try await ready(window.session, .ready)
        }
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "2")
        do {
            _ = try await source.prepare(LibraryChoice(id: "../working", title: "Forged", detail: ""))
            XCTFail("A source ID is not a path input")
        } catch {}
    }
}
