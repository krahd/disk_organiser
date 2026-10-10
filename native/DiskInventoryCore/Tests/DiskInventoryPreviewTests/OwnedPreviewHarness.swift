import XCTest
import Foundation
import AppKit
import WebKit
import CryptoKit
import Darwin
@testable import DiskInventoryCore

// Each asynchronous test observation has a one-shot deadline. A missing WebKit
// callback fails the test rather than hanging until the workflow timeout. Values
// crossing continuations are Sendable; native framework objects stay on MainActor.
@MainActor
private final class PreviewCallback<Value: Sendable> {
    private var continuation: CheckedContinuation<Value, Error>?
    init(_ continuation: CheckedContinuation<Value, Error>, seconds: Int = 10) {
        self.continuation = continuation
        Task { @MainActor in
            try? await Task.sleep(for: .seconds(seconds))
            self.finish(.failure(OwnedPreviewHost.Failure.expired))
        }
    }
    func finish(_ result: Result<Value, Error>) {
        guard let continuation else { return }
        self.continuation = nil
        continuation.resume(with: result)
    }
}

@MainActor
private final class PreviewRuleResult { var rule: WKContentRuleList? }

// This is only the standalone XCTest process's AppKit bootstrap. It cannot
// accept an external document/URL request or create an untitled document.
@MainActor
private final class OwnedPreviewApplicationDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldOpenUntitledFile(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { false }
    func application(_ sender: NSApplication, openFile filename: String) -> Bool { false }
    func application(_ sender: NSApplication, openFiles filenames: [String]) { sender.reply(toOpenOrPrint: .failure) }
    func application(_ application: NSApplication, open urls: [URL]) { /* Reject every URL. */ }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
}

// All test setup and evidence writes stay outside the host. The WebKit rule
// compiler persists its cache, so it is given a fresh owned test directory,
// never the default/shared rule store or a user directory.
@MainActor
final class OwnedPreviewHarness {
    let host: OwnedPreviewHost
    let window: NSWindow
    let ruleStore: WKContentRuleListStore
    let cacheDirectory: URL
    private var eventNumber = 0
    private static var applicationPrepared = false
    private static let applicationDelegate = OwnedPreviewApplicationDelegate()

    private static func prepareApplication() throws {
        guard !applicationPrepared else { return }
        let app = NSApplication.shared
        // finishLaunching can consume NSOpen defaults. Reject any such launch
        // context rather than clearing defaults or opening an external source.
        guard app.delegate == nil,
              UserDefaults.standard.object(forKey: "NSOpen") == nil,
              UserDefaults.standard.object(forKey: "NSPrint") == nil else {
            throw OwnedPreviewHost.Failure.unavailable
        }
        let regularPolicy = app.setActivationPolicy(.regular)
        print("OWNED_APP_BOOTSTRAP regularPolicy=\(regularPolicy) runningBefore=\(app.isRunning)")
        guard regularPolicy else { throw OwnedPreviewHost.Failure.unavailable }
        app.delegate = applicationDelegate
        app.finishLaunching()
        applicationPrepared = true
        print("OWNED_APP_BOOTSTRAP finishLaunchingReturned=true active=\(app.isActive)")
    }

    private init(host: OwnedPreviewHost, ruleStore: WKContentRuleListStore, cacheDirectory: URL) {
        self.host = host; self.ruleStore = ruleStore; self.cacheDirectory = cacheDirectory
        window = NSWindow(contentRect: host.webView.frame, styleMask: [.titled, .closable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Disk Organiser · owned-fixture test preview"
        window.isReleasedWhenClosed = false
        window.contentView = host.webView
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(host.webView)
    }
    static func open(width: CGFloat = 1280, height: CGFloat = 960) async throws -> OwnedPreviewHarness {
        try prepareApplication()
        var template = Array("/private/tmp/disk-preview-rules-XXXXXX".utf8CString)
        let path = try template.withUnsafeMutableBufferPointer { buffer in
            guard let created = mkdtemp(buffer.baseAddress!) else { throw CoreFailure.filesystem(errno) }
            return String(cString: created)
        }
        let directory = URL(fileURLWithPath: path, isDirectory: true)
        let store = try XCTUnwrap(WKContentRuleListStore(url: directory))
        let compiled = PreviewRuleResult()
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            let callback = PreviewCallback(continuation)
            store.compileContentRuleList(forIdentifier: "owned-preview-" + UUID().uuidString,
                encodedContentRuleList: OwnedPreviewHost.ruleJSON) { rule, error in
                if let error { callback.finish(.failure(error)) }
                else if let rule { compiled.rule = rule; callback.finish(.success(())) }
                else { callback.finish(.failure(OwnedPreviewHost.Failure.unavailable)) }
            }
        }
        let rule = try XCTUnwrap(compiled.rule)
        let host = try OwnedPreviewHost(rule: rule, width: width, height: height)
        let harness = OwnedPreviewHarness(host: host, ruleStore: store, cacheDirectory: directory)
        do { try await host.load(); return harness }
        catch { harness.close(); throw error }
    }
    func close() { host.close(); window.orderOut(nil); window.close() }

    // Test-only observations. Each body at a call site is fixed test source;
    // strings used as data are separate arguments, never interpolated JS.
    func script(_ body: String, arguments: [String: String] = [:]) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            let callback = PreviewCallback(continuation)
            host.webView.callAsyncJavaScript(body, arguments: arguments, in: nil, in: .page) { result in
                switch result {
                case .success(let value):
                    if let value = value as? String { callback.finish(.success(value)) }
                    else { callback.finish(.failure(OwnedPreviewHost.Failure.invalidReply)) }
                case .failure(let error): callback.finish(.failure(error))
                }
            }
        }
    }
    func wait(_ body: String, equals expected: String, seconds: TimeInterval = 5) async throws {
        let deadline = Date().addingTimeInterval(seconds)
        repeat {
            if try await script(body) == expected { return }
            try await Task.sleep(for: .milliseconds(30))
        } while Date() < deadline
        XCTFail("Owned WebKit condition did not reach the expected state")
        throw OwnedPreviewHost.Failure.expired
    }
    private func prepareInteraction() async throws {
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        let deadline = Date().addingTimeInterval(3)
        while (!NSApp.isActive || !window.isKeyWindow) && Date() < deadline {
            try await Task.sleep(for: .milliseconds(30))
        }
        print("OWNED_EVENT_WINDOW active=\(NSApp.isActive) key=\(window.isKeyWindow) visible=\(window.isVisible) responder=\(String(describing: window.firstResponder)) bounds=\(host.webView.bounds)")
        guard NSApp.isActive, window.isKeyWindow, window.isVisible, !host.webView.isHidden else {
            throw OwnedPreviewHost.Failure.unavailable
        }
    }
    private func startEventTrace() async throws {
        _ = try await script("""
            window.__ownedEventTrace=[];
            if(!window.__ownedEventListener) {
                window.__ownedEventListener=e=>{
                    if(window.__ownedEventTrace.length<16) window.__ownedEventTrace.push({
                        type:e.type,id:String(e.target.id||'').slice(0,64),trusted:e.isTrusted,
                        x:e.clientX??null,y:e.clientY??null,key:e.key??null});
                };
                for(const type of ['mousedown','mouseup','click','keydown','keyup'])
                    document.addEventListener(type,window.__ownedEventListener,true);
            }
            return 'tracing';
            """)
    }
    func click(_ id: String) async throws {
        try await prepareInteraction()
        try await startEventTrace()
        let text = try await script("""
            const e = document.getElementById(id);
            e.scrollIntoView({block:'center'});
            const r = e.getBoundingClientRect();
            const x = r.left + r.width / 2, y = r.top + r.height / 2;
            return JSON.stringify({x,y,hit:document.elementFromPoint(x,y)===e,
                visible:r.width>0&&r.height>0,enabled:!e.disabled,width:innerWidth,height:innerHeight});
            """, arguments: ["id": id])
        let data = try XCTUnwrap(text.data(using: .utf8))
        let rect = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(rect["hit"] as? Bool, true); XCTAssertEqual(rect["visible"] as? Bool, true)
        XCTAssertEqual(rect["enabled"] as? Bool, true)
        guard rect["hit"] as? Bool == true, rect["visible"] as? Bool == true,
              rect["enabled"] as? Bool == true,
              let x = rect["x"] as? Double, let y = rect["y"] as? Double else {
            throw OwnedPreviewHost.Failure.unavailable
        }
        let view = host.webView
        let local = NSPoint(x: x, y: view.isFlipped ? y : view.bounds.height - y)
        let point = view.convert(local, to: nil)
        let parent = try XCTUnwrap(view.superview)
        let hit = view.hitTest(parent.convert(point, from: nil))
        print("OWNED_EVENT_GEOMETRY id=\(id) dom=\(text) flipped=\(view.isFlipped) local=\(local) window=\(point) nativeHit=\(String(describing: hit))")
        guard let hit, hit === view || hit.isDescendant(of: view) else { throw OwnedPreviewHost.Failure.unavailable }
        for type in [NSEvent.EventType.leftMouseDown, .leftMouseUp] {
            eventNumber += 1
            let event = try XCTUnwrap(NSEvent.mouseEvent(with: type, location: point, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                context: nil, eventNumber: eventNumber, clickCount: 1, pressure: type == .leftMouseDown ? 1 : 0))
            // NSApplication performs responder dispatch; direct NSWindow.sendEvent
            // bypasses that route and is explicitly discouraged by AppKit.
            NSApp.sendEvent(event)
            try await Task.sleep(for: .milliseconds(40))
        }
        let trace = try await script("return JSON.stringify(window.__ownedEventTrace);")
        print("OWNED_EVENT_TRACE id=\(id) events=\(trace)")
        let rows = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(trace.utf8)) as? [[String: Any]])
        let events = rows.filter { $0["id"] as? String == id }
        XCTAssertEqual(events.compactMap { $0["type"] as? String }, ["mousedown", "mouseup", "click"])
        guard events.count == 3, events.allSatisfy({ $0["trusted"] as? Bool == true }) else {
            throw OwnedPreviewHost.Failure.unavailable
        }
        for event in events {
            XCTAssertEqual(try XCTUnwrap(event["x"] as? Double), x, accuracy: 1)
            XCTAssertEqual(try XCTUnwrap(event["y"] as? Double), y, accuracy: 1)
        }
    }
    func key(_ characters: String, code: UInt16) async throws {
        try await prepareInteraction()
        try await startEventTrace()
        for type in [NSEvent.EventType.keyDown, .keyUp] {
            let event = try XCTUnwrap(NSEvent.keyEvent(with: type, location: .zero, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                context: nil, characters: characters, charactersIgnoringModifiers: characters,
                isARepeat: false, keyCode: code))
            NSApp.sendEvent(event)
            try await Task.sleep(for: .milliseconds(40))
        }
        let trace = try await script("return JSON.stringify(window.__ownedEventTrace);")
        print("OWNED_KEY_TRACE events=\(trace)")
        let rows = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(trace.utf8)) as? [[String: Any]])
        XCTAssertTrue(rows.contains { $0["type"] as? String == "keydown" && $0["id"] as? String == "catalogue-name" && $0["trusted"] as? Bool == true })
    }
    func snapshot() async throws -> Data {
        let configuration = WKSnapshotConfiguration()
        configuration.rect = host.webView.bounds
        configuration.snapshotWidth = NSNumber(value: Double(host.webView.bounds.width))
        configuration.afterScreenUpdates = true
        return try await withCheckedThrowingContinuation { continuation in
            let callback = PreviewCallback(continuation)
            host.webView.takeSnapshot(with: configuration) { image, error in
                if let error { callback.finish(.failure(error)); return }
                do {
                    let image = try XCTUnwrap(image)
                    let tiff = try XCTUnwrap(image.tiffRepresentation)
                    let bitmap = try XCTUnwrap(NSBitmapImageRep(data: tiff))
                    let png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
                    XCTAssertGreaterThan(png.count, 20_000)
                    // Original WKWebView pixels; no resize, crop or composition.
                    callback.finish(.success(png))
                } catch { callback.finish(.failure(error)) }
            }
        }
    }
}

@MainActor
final class OwnedPreviewScreens {
    private var descriptor: Int32?
    private var rows = [[String: String]]()
    init() throws {
        let environment = ProcessInfo.processInfo.environment
        if let output = environment["DISK_INVENTORY_PREVIEW_OUTPUT"] {
            let root = try XCTUnwrap(environment["RUNNER_TEMP"])
            guard root.hasPrefix("/"), !root.isEmpty, output == root + "/disk-inventory-preview-screens" else {
                throw CoreFailure.invalidProjection
            }
            guard mkdir(output, 0o700) == 0 else { throw CoreFailure.filesystem(errno) }
            let fd = Darwin.open(output, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw CoreFailure.filesystem(errno) }; descriptor = fd
        }
    }
    func capture(_ name: String, from harness: OwnedPreviewHarness) async throws {
        guard name.range(of: "^[0-9]{2}-[a-z-]+\\.png$", options: .regularExpression) != nil,
              !rows.contains(where: { $0["file"] == name }), rows.count < 5 else { throw CoreFailure.invalidProjection }
        let bytes = try await harness.snapshot()
        guard bytes.count <= 5 * 1024 * 1024 else { throw CoreFailure.invalidProjection }
        let hash = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        try write(bytes, name: name)
        rows.append(["file": name, "bytes": String(bytes.count), "sha256": hash])
    }
    func finish() throws {
        guard rows.count == 5 else { throw CoreFailure.invalidProjection }
        let bytes = try JSONSerialization.data(withJSONObject: ["screenshots": rows], options: [.prettyPrinted, .sortedKeys])
        try write(bytes, name: "manifest.json")
        close()
    }
    func close() { if let descriptor { _ = Darwin.close(descriptor); self.descriptor = nil } }
    private func write(_ bytes: Data, name: String) throws {
        guard let descriptor else { return }
        let fd = openat(descriptor, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw CoreFailure.filesystem(errno) }
        defer { _ = Darwin.close(fd) }
        try bytes.withUnsafeBytes { buffer in
            var offset = 0
            while offset < buffer.count {
                let count = Darwin.write(fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw CoreFailure.filesystem(errno) }; offset += count
            }
        }
    }
}
