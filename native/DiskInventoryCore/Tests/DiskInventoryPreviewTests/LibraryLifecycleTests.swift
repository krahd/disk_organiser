import XCTest
import AppKit
import Foundation
@testable import DiskInventoryDesktop

@MainActor
extension LibraryApplicationTests {
    func testImmediateCancelBeforeScheduledProviderMakesZeroCalls() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        let session = window.session
        session.choose(); session.select(source.choices[0]); session.prepare(); session.cancel()
        try await ready(session, .ready)
        XCTAssertEqual(source.calls, 0); XCTAssertFalse(session.hasTemporaryRecords)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "0")
    }

    func testImmediateCloseBeforeScheduledProviderMakesZeroCalls() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        let session = window.session
        session.choose(); session.select(source.choices[0]); session.prepare(); window.discardAndClose()
        await Task.yield(); try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(source.calls, 0); XCTAssertEqual(session.state, .closed)
        XCTAssertEqual(h.host.state, .closed); XCTAssertFalse(h.window.isVisible)
    }

    func testReentrantCloseFromPreparingNotificationNeverCallsProvider() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        let session = window.session
        session.choose(); session.select(source.choices[0])
        session.changed = { if session.state == .preparing { session.close() } }
        session.prepare()
        await Task.yield(); try await Task.sleep(for: .milliseconds(30))
        XCTAssertEqual(source.calls, 0); XCTAssertEqual(session.state, .closed)
        XCTAssertEqual(h.host.state, .closed)
    }

    func testSessionDelayedStageCancelBeforeAddFencesLateSubmit() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        var release: CheckedContinuation<Void, Never>?
        h.host.beforeStageAcknowledgement = { await withCheckedContinuation { release = $0 } }
        window.session.choose(); window.session.select(source.choices[0]); window.session.prepare()
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "true")
        for _ in 0..<100 where release == nil { try await Task.sleep(for: .milliseconds(10)) }
        window.session.cancel(); XCTAssertEqual(window.session.state, .stopping)
        try XCTUnwrap(release).resume(); h.host.beforeStageAcknowledgement = nil
        try await ready(window.session, .ready)
        _ = try await h.script("document.getElementById('catalogue-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})); return 'late attack';")
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "0")
        XCTAssertFalse(window.session.hasTemporaryRecords)
    }

    func testSessionDelayedStageRetainsAddProcessedBeforeCancellation() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        var release: CheckedContinuation<Void, Never>?
        h.host.beforeStageAcknowledgement = { await withCheckedContinuation { release = $0 } }
        window.session.choose(); window.session.select(source.choices[0]); window.session.prepare()
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "true")
        for _ in 0..<100 where release == nil { try await Task.sleep(for: .milliseconds(10)) }
        try await h.click("catalogue-confirm")
        window.session.cancel()
        try XCTUnwrap(release).resume(); h.host.beforeStageAcknowledgement = nil
        try await ready(window.session, .ready)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "1")
        XCTAssertTrue(window.session.hasTemporaryRecords)
        XCTAssertTrue(window.session.message.contains("added before cancellation"))
    }

    func testSessionCloseDuringDelayedStageNeverRevivesWindow() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        var release: CheckedContinuation<Void, Never>?
        h.host.beforeStageAcknowledgement = { await withCheckedContinuation { release = $0 } }
        window.session.choose(); window.session.select(source.choices[0]); window.session.prepare()
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "true")
        for _ in 0..<100 where release == nil { try await Task.sleep(for: .milliseconds(10)) }
        window.discardAndClose()
        try XCTUnwrap(release).resume(); h.host.beforeStageAcknowledgement = nil
        try await Task.sleep(for: .milliseconds(100))
        XCTAssertEqual(window.session.state, .closed); XCTAssertEqual(h.host.state, .closed)
        XCTAssertFalse(h.window.isVisible); XCTAssertFalse(window.session.hasTemporaryRecords)
    }

    func testNativePrepareTransfersKeyboardToReviewWithoutPointerRepair() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        try await clickNative("library-explore", using: h)
        try await clickNative("library-choice-one", using: h)
        try await clickNative("library-prepare", using: h)
        try await ready(window.session, .reviewing)
        // The existing key driver waits for active/key state and traces trusted
        // events, but does not call makeFirstResponder or click any web element.
        try await h.key("\u{1b}", code: 53)
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "false")
        window.session.finishReview(); try await ready(window.session, .ready)
        XCTAssertFalse(window.session.hasTemporaryRecords)
    }

    func testDirtyNativeCloseKeepRepeatedCloseAndDiscard() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { window.discardAndClose(); h.close() }
        window.session.choose(); window.session.select(source.choices[0]); window.session.prepare()
        try await ready(window.session, .reviewing)
        try await h.click("catalogue-confirm")
        window.session.finishReview(); try await ready(window.session, .ready)
        try await clickNative("window-close", using: h)
        let question = try XCTUnwrap(h.window.attachedSheet)
        window.requestClose(); window.requestClose()
        XCTAssertTrue(h.window.attachedSheet === question)
        try await clickNative("library-keep", using: h)
        XCTAssertTrue(h.window.isVisible); XCTAssertTrue(window.session.hasTemporaryRecords)
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "1")
        try await clickNative("window-close", using: h)
        try await clickNative("library-discard", using: h)
        XCTAssertFalse(h.window.isVisible); XCTAssertEqual(window.session.state, .closed)
    }

    func testKeepRestoresScopeAndLatePreparationCannotReplaceCloseQuestion() async throws {
        let source = OwnedLibrarySource()
        let (h, window) = try await open(source); defer { source.release(); window.discardAndClose(); h.close() }
        try await clickNative("library-explore", using: h)
        try await clickNative("library-choice-one", using: h)
        // Equivalent to the native Quit delegate's close request while a sheet
        // is active; response choices still use genuine AppKit pointer events.
        window.requestClose(); window.requestClose()
        try await clickNative("library-keep", using: h)
        XCTAssertEqual(window.session.state, .scope)
        source.hold = true
        try await clickNative("library-prepare", using: h)
        for _ in 0..<100 where source.continuation == nil { try await Task.sleep(for: .milliseconds(10)) }
        window.requestClose()
        let question = try XCTUnwrap(h.window.attachedSheet)
        source.release(); try await ready(window.session, .reviewing)
        XCTAssertTrue(h.window.attachedSheet === question)
        try await clickNative("library-keep", using: h)
        try await h.key("\u{1b}", code: 53)
        window.session.finishReview(); try await ready(window.session, .ready)
        XCTAssertFalse(window.session.hasTemporaryRecords)
    }

    func testStartupKeepsActionsUnavailableUntilEmptyReadyViewConfirmed() async throws {
        let source = OwnedLibrarySource()
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: source), startReady: false)
        defer { window.discardAndClose() }
        try h.useApplicationWindow(window.window); window.show()
        XCTAssertFalse(window.exploreButton.isEnabled); XCTAssertEqual(source.calls, 0)
        try await h.host.requireEmptyLibrary()
        XCTAssertTrue(window.completeStartup()); XCTAssertTrue(window.exploreButton.isEnabled)
        window.discardAndClose(); XCTAssertFalse(window.completeStartup())
    }
}
