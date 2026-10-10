import XCTest
import Foundation
import AppKit
import CryptoKit
import Darwin
@testable import DiskInventoryCore

// Original captures of exactly the named native view or WebKit viewport.
// No screen-recording permission, composite, resize or full-window claim.
@MainActor
final class LibraryApplicationScreens {
    private var descriptor: Int32?
    private var rows = [[String: String]]()
    private let names: Set<String> = ["70-native-library-controls.png", "71-native-sample-selector.png",
        "72-native-scope-review.png", "73-native-progress-controls.png", "74-native-library-record.png", "75-native-close-confirmation.png"]
    init() throws {
        let environment = ProcessInfo.processInfo.environment
        if let output = environment["DISK_APPLICATION_PREVIEW_OUTPUT"] {
            let root = try XCTUnwrap(environment["RUNNER_TEMP"])
            guard root.hasPrefix("/"), output == root + "/disk-application-preview-screens" else { throw CoreFailure.invalidProjection }
            guard mkdir(output, 0o700) == 0 else { throw CoreFailure.filesystem(errno) }
            let fd = Darwin.open(output, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw CoreFailure.filesystem(errno) }; descriptor = fd
        }
    }
    func native(_ name: String, view: NSView) async throws {
        let window = try XCTUnwrap(view.window)
        NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil)
        let deadline = Date().addingTimeInterval(3)
        repeat {
            for _ in 0..<32 {
                guard let event = NSApp.nextEvent(matching: .any, until: .distantPast, inMode: .default, dequeue: true) else { break }
                NSApp.sendEvent(event)
            }
            NSApp.updateWindows()
            if window.isKeyWindow && NSApp.isActive { break }
            try await Task.sleep(for: .milliseconds(20))
        } while Date() < deadline
        guard window.isVisible, window.isKeyWindow, NSApp.isActive,
              !view.isHiddenOrHasHiddenAncestor else { throw CoreFailure.invalidProjection }
        view.layoutSubtreeIfNeeded(); view.displayIfNeeded()
        let representation = try XCTUnwrap(view.bitmapImageRepForCachingDisplay(in: view.bounds))
        view.cacheDisplay(in: view.bounds, to: representation)
        let bytes = try XCTUnwrap(representation.representation(using: .png, properties: [:]))
        try admit(bytes, name: name, kind: "original AppKit named-view capture")
    }
    func web(_ name: String, harness: OwnedPreviewHarness) async throws {
        let bytes = try await harness.snapshot()
        try admit(bytes, name: name, kind: "original WebKit viewport capture")
    }
    private func admit(_ bytes: Data, name: String, kind: String) throws {
        guard names.contains(name), !rows.contains(where: { $0["file"] == name }), rows.count < 6,
              !bytes.isEmpty, bytes.count <= 5 * 1024 * 1024 else { throw CoreFailure.invalidProjection }
        let hash = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        try write(bytes, name: name)
        rows.append(["file": name, "bytes": String(bytes.count), "sha256": hash, "scope": kind])
    }
    func finish() throws {
        guard Set(rows.compactMap { $0["file"] }) == names else { throw CoreFailure.invalidProjection }
        try write(JSONSerialization.data(withJSONObject: ["screenshots": rows], options: [.prettyPrinted, .sortedKeys]), name: "manifest.json")
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
