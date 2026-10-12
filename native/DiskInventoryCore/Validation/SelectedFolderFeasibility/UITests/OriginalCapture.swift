import XCTest
import AppKit
import CryptoKit
import Darwin

@MainActor
struct OriginalCapture {
    let screenshot: XCUIScreenshot
    let digest: String
    let byteCount: Int
    let width: Int
    let height: Int

    static func write(_ window: XCUIElement, name: String) throws -> OriginalCapture {
        let names = ["100-selected-read-retired", "101-panel-cancelled", "102-active-cancelled", "103-retry-retired"]
        guard names.contains(name), window.exists, window.frame.width > 0, window.frame.height > 0,
              window.frame.width <= 8192, window.frame.height <= 8192,
              ProbeSeal.captureDirectory.hasPrefix("/private/tmp/disk-selection-build-"),
              ProbeSeal.captureDirectory.hasSuffix("/Captures") else { throw ProbeFailure.refused("capture-coordinate") }
        let screenshot = window.screenshot()
        let bytes = screenshot.pngRepresentation
        guard !bytes.isEmpty, bytes.count <= 4 * 1024 * 1024,
              let bitmap = NSBitmapImageRep(data: bytes), bitmap.pixelsWide > 0, bitmap.pixelsHigh > 0,
              bitmap.pixelsWide <= 8192, bitmap.pixelsHigh <= 8192 else { throw ProbeFailure.refused("capture-byte-dimensions") }
        try ProbeDescriptors.perform { ledger in
            let parent = try ledger.directory(ProbeSeal.captureDirectory)
            let initial = try ledger.metadata(parent)
            guard initial.device == ProbeSeal.captureDevice, initial.inode == ProbeSeal.captureInode,
                  initial.uid == getuid(), initial.mode == UInt32(S_IFDIR | 0o700) else {
                throw ProbeFailure.refused("capture-owner-identity")
            }
            let fd = try ledger.acquire("owned-capture-create") {
                (name + ".png").withCString {
                    openat(parent, $0, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0o600)
                }
            }
            let created = try ledger.metadata(fd)
            guard created.mode == UInt32(S_IFREG | 0o600), created.links == 1, created.size == 0,
                  created.uid == getuid() else { throw ProbeFailure.refused("capture-file-shape") }
            var used = 0
            for _ in 0..<4096 {
                if used == bytes.count { break }
                let count = bytes.withUnsafeBytes { raw in
                    Darwin.write(fd, raw.baseAddress!.advanced(by: used), raw.count - used)
                }
                if count < 0 {
                    if errno == EINTR { continue }
                    throw ProbeFailure.syscall("owned-capture-write", errno)
                }
                guard count > 0 else { throw ProbeFailure.refused("capture-write-progress") }
                used += count
            }
            guard used == bytes.count, fsync(fd) == 0 else { throw ProbeFailure.refused("capture-write-incomplete") }
            let final = try ledger.metadata(fd)
            let parentNow = try ledger.metadata(parent)
            guard final.device == created.device, final.inode == created.inode, final.size == Int64(bytes.count),
                  final.mode == created.mode, final.links == 1, final.uid == created.uid,
                  initial.matches(parentNow, directory: true) else { throw ProbeFailure.refused("capture-write-race") }
        }
        // The exact screenshot bytes are persisted, without resize, fill,
        // compositing, re-encoding or substitution. Pixels still need review.
        return OriginalCapture(screenshot: screenshot,
                               digest: SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined(),
                               byteCount: bytes.count, width: bitmap.pixelsWide, height: bitmap.pixelsHigh)
    }
}
