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

// All test setup and evidence writes stay outside the host. The WebKit rule
// compiler persists its cache, so it is given a fresh owned test directory,
// never the default/shared rule store or a user directory.
@MainActor
final class OwnedPreviewHarness {
    let host: OwnedPreviewHost
    let window: NSWindow
    let ruleStore: WKContentRuleListStore
    let cacheDirectory: URL

    private init(host: OwnedPreviewHost, ruleStore: WKContentRuleListStore, cacheDirectory: URL) {
        self.host = host; self.ruleStore = ruleStore; self.cacheDirectory = cacheDirectory
        window = NSWindow(contentRect: host.webView.frame, styleMask: [.titled, .closable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Disk Organiser · owned-fixture test preview"
        window.isReleasedWhenClosed = false
        window.contentView = host.webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        window.makeFirstResponder(host.webView)
    }
    static func open(width: CGFloat = 1280, height: CGFloat = 960) async throws -> OwnedPreviewHarness {
        _ = NSApplication.shared
        NSApp.setActivationPolicy(.regular)
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
    func click(_ id: String) async throws {
        let text = try await script("""
            const e = document.getElementById(id);
            e.scrollIntoView({block:'center'});
            const r = e.getBoundingClientRect();
            const x = r.left + r.width / 2, y = r.top + r.height / 2;
            return JSON.stringify({x,y,hit:document.elementFromPoint(x,y)===e,visible:r.width>0&&r.height>0});
            """, arguments: ["id": id])
        let data = try XCTUnwrap(text.data(using: .utf8))
        let rect = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(rect["hit"] as? Bool, true); XCTAssertEqual(rect["visible"] as? Bool, true)
        guard rect["hit"] as? Bool == true, let x = rect["x"] as? Double, let y = rect["y"] as? Double else {
            throw OwnedPreviewHost.Failure.unavailable
        }
        let view = host.webView
        let local = NSPoint(x: x, y: view.isFlipped ? y : view.bounds.height - y)
        let point = view.convert(local, to: nil)
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        for type in [NSEvent.EventType.leftMouseDown, .leftMouseUp] {
            let event = try XCTUnwrap(NSEvent.mouseEvent(with: type, location: point, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                context: nil, eventNumber: 1, clickCount: 1, pressure: 1))
            window.sendEvent(event)
        }
        try await Task.sleep(for: .milliseconds(80))
    }
    func key(_ characters: String, code: UInt16) async throws {
        for type in [NSEvent.EventType.keyDown, .keyUp] {
            let event = try XCTUnwrap(NSEvent.keyEvent(with: type, location: .zero, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                context: nil, characters: characters, charactersIgnoringModifiers: characters,
                isARepeat: false, keyCode: code))
            window.sendEvent(event)
        }
        try await Task.sleep(for: .milliseconds(80))
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
