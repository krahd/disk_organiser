import XCTest
import AppKit
import Foundation
import Darwin
@testable import DiskInventoryDesktop

// Tests launch only this package's just-built sample executable. No source
// argument, test-command endpoint, user app, global process search or permission.
private struct OwnedProcessOutput: Sendable { var bytes = Data(); var invalid = false }

@MainActor
final class LibraryProcessTests: XCTestCase {
    private func executable() throws -> URL {
        let package = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        let binary = package.appendingPathComponent(".build/debug/DiskOrganiserPreview").resolvingSymlinksInPath()
        let build = package.appendingPathComponent(".build", isDirectory: true).resolvingSymlinksInPath().path + "/"
        guard binary.path.hasPrefix(build), binary.lastPathComponent == "DiskOrganiserPreview",
              FileManager.default.isExecutableFile(atPath: binary.path) else { throw CataloguePreviewHost.Failure.unavailable }
        return binary
    }
    private func launch(arguments: [String] = []) throws -> (Process, Pipe, LockedBox<OwnedProcessOutput>, URL) {
        let binary = try executable()
        let process = Process(); process.executableURL = binary; process.arguments = arguments
        let pipe = Pipe(); let output = LockedBox(OwnedProcessOutput())
        process.standardOutput = pipe; process.standardError = FileHandle.nullDevice
        pipe.fileHandleForReading.readabilityHandler = { handle in
            do {
                let bytes = try handle.read(upToCount: 1024) ?? Data()
                if bytes.isEmpty { handle.readabilityHandler = nil; return }
                output.update { value in
                    guard value.bytes.count + bytes.count <= 4096 else { value.invalid = true; return }
                    value.bytes.append(bytes)
                }
            } catch { output.update { $0.invalid = true } }
        }
        try process.run()
        return (process, pipe, output, binary)
    }
    private func contains(_ receipt: String, in output: LockedBox<OwnedProcessOutput>) -> Bool {
        let current = output.read()
        return !current.invalid && String(data: current.bytes, encoding: .utf8)?.split(separator: "\n").contains(Substring(receipt)) == true
    }
    private func waitForExit(_ child: Process, seconds: TimeInterval) async -> Bool {
        let deadline = Date().addingTimeInterval(seconds)
        while child.isRunning && Date() < deadline { try? await Task.sleep(for: .milliseconds(30)) }
        if !child.isRunning { child.waitUntilExit(); return true }
        return false
    }
    private func cleanFailedChild(_ child: Process) async {
        // Cleanup is never normal-quit evidence. Only our still-running Process
        // is targeted. No process search, system setting or alternate app route.
        guard child.isRunning else { child.waitUntilExit(); return }
        child.terminate()
        if await waitForExit(child, seconds: 3) { return }
        if child.isRunning { _ = Darwin.kill(child.processIdentifier, SIGKILL) }
        let reaped = await waitForExit(child, seconds: 3)
        XCTAssertTrue(reaped, "Owned child cleanup did not complete; test remains failed")
    }

    func testOwnedSampleExecutableLoadsEmptyWindowAndQuitsNormally() async throws {
        let (child, pipe, output, binary) = try launch()
        defer { pipe.fileHandleForReading.readabilityHandler = nil }
        do {
            let deadline = Date().addingTimeInterval(20)
            while child.isRunning && !contains("DISK_PREVIEW_READY_EMPTY_WINDOW", in: output) && Date() < deadline {
                try await Task.sleep(for: .milliseconds(30))
            }
            guard child.isRunning, contains("DISK_PREVIEW_READY_EMPTY_WINDOW", in: output),
                  let application = NSRunningApplication(processIdentifier: child.processIdentifier),
                  application.processIdentifier == child.processIdentifier,
                  application.executableURL?.resolvingSymlinksInPath() == binary,
                  application.isFinishedLaunching, !application.isTerminated else {
                XCTFail("The exact owned sample process did not prove empty-window readiness")
                throw CataloguePreviewHost.Failure.unavailable
            }
            // Normal quit of that exact owned application, not SIGTERM or an
            // automation event to another process. A sent request is not exit.
            guard child.isRunning, application.terminate() else {
                XCTFail("Normal Quit could not be requested for the owned child")
                throw CataloguePreviewHost.Failure.unavailable
            }
            guard await waitForExit(child, seconds: 5) else {
                XCTFail("Owned application did not complete normal Quit")
                throw CataloguePreviewHost.Failure.expired
            }
            let receiptDeadline = Date().addingTimeInterval(1)
            while !contains("DISK_PREVIEW_WILL_TERMINATE", in: output) && Date() < receiptDeadline {
                try await Task.sleep(for: .milliseconds(20))
            }
            XCTAssertEqual(child.terminationReason, .exit); XCTAssertEqual(child.terminationStatus, 0)
            XCTAssertTrue(contains("DISK_PREVIEW_QUIT_REQUEST", in: output))
            XCTAssertTrue(contains("DISK_PREVIEW_WILL_TERMINATE", in: output))
            XCTAssertFalse(output.read().invalid)
            print("OWNED_APP_PROCESS readyEmptyWindow=true normalQuitRequested=true exit=\(child.terminationStatus)")
        } catch { await cleanFailedChild(child); throw error }
    }

    func testOwnedSampleExecutableRejectsUnknownArgumentBeforeReadiness() async throws {
        let (child, pipe, output, _) = try launch(arguments: ["--unsupported-owned-test-argument"])
        defer { pipe.fileHandleForReading.readabilityHandler = nil }
        guard await waitForExit(child, seconds: 5) else {
            XCTFail("Unknown argument did not reject promptly")
            await cleanFailedChild(child); throw CataloguePreviewHost.Failure.expired
        }
        let deadline = Date().addingTimeInterval(1)
        while !contains("DISK_PREVIEW_INPUT_REJECTED", in: output) && Date() < deadline {
            try await Task.sleep(for: .milliseconds(20))
        }
        XCTAssertEqual(child.terminationReason, .exit); XCTAssertEqual(child.terminationStatus, 0)
        XCTAssertTrue(contains("DISK_PREVIEW_INPUT_REJECTED", in: output))
        XCTAssertFalse(contains("DISK_PREVIEW_READY_EMPTY_WINDOW", in: output))
        XCTAssertFalse(output.read().invalid)
    }
}
