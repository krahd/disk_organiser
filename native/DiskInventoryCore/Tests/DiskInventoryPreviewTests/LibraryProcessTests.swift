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
        let pipe = Pipe(); let output = try collect(pipe)
        process.standardOutput = pipe; process.standardError = FileHandle.nullDevice
        do { try process.run() }
        catch { pipe.fileHandleForReading.readabilityHandler = nil; throw error }
        return (process, pipe, output, binary)
    }
    private func collect(_ pipe: Pipe) throws -> LockedBox<OwnedProcessOutput> {
        let output = LockedBox(OwnedProcessOutput())
        let descriptor = pipe.fileHandleForReading.fileDescriptor
        let flags = fcntl(descriptor, F_GETFL)
        guard flags >= 0, fcntl(descriptor, F_SETFL, flags | O_NONBLOCK) == 0 else { throw CataloguePreviewHost.Failure.unavailable }
        pipe.fileHandleForReading.readabilityHandler = { handle in
            // One bounded nonblocking syscall observes a short live write
            // without waiting for 1 KiB or EOF. This is our own pipe only.
            var buffer = [UInt8](repeating: 0, count: 1024)
            let count = buffer.withUnsafeMutableBytes { Darwin.read(handle.fileDescriptor, $0.baseAddress!, $0.count) }
            if count == 0 { handle.readabilityHandler = nil; return }
            if count < 0 {
                if errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK { return }
                output.update { $0.invalid = true }; handle.readabilityHandler = nil; return
            }
            let bytes = Data(buffer.prefix(count))
            output.update { value in
                guard value.bytes.count + bytes.count <= 4096 else { value.invalid = true; return }
                value.bytes.append(bytes)
            }
            if output.read().invalid { handle.readabilityHandler = nil }
        }
        return output
    }
    private func contains(_ receipt: String, in output: LockedBox<OwnedProcessOutput>) -> Bool {
        let current = output.read()
        return !current.invalid && String(data: current.bytes, encoding: .utf8)?.split(separator: "\n").contains(Substring(receipt)) == true
    }
    private func diagnose(_ child: Process, output: LockedBox<OwnedProcessOutput>, binary: URL) {
        // Report only fixed allowlisted phases and booleans, never child output,
        // paths, error descriptions, source labels or an unbounded log stream.
        let phases = ["ENTRY", "INPUT_REJECTED", "BOOTSTRAP_REJECTED", "RUN_LOOP", "DID_LAUNCH",
            "RULES_READY", "HOST_CREATED", "VIEW_READY", "WINDOW_SHOWN", "EMPTY_CONFIRMED",
            "ACTIVE", "KEY", "VISIBLE", "READY_EMPTY_WINDOW", "STARTUP_FAILED", "QUIT_REQUEST", "WILL_TERMINATE"]
        let observed = phases.filter { contains("DISK_PREVIEW_" + $0, in: output) }.joined(separator: ",")
        let application = child.isRunning ? NSRunningApplication(processIdentifier: child.processIdentifier) : nil
        let matches = application?.executableURL?.resolvingSymlinksInPath() == binary
        print("OWNED_APP_STARTUP phases=\(observed) bytes=\(output.read().bytes.count) invalid=\(output.read().invalid) running=\(child.isRunning) registered=\(application != nil) executableMatches=\(matches) finishedLaunching=\(application?.isFinishedLaunching ?? false) active=\(application?.isActive ?? false)")
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

    func testOwnedReceiptPipeObservesShortWriteBeforeWriterCloses() async throws {
        let pipe = Pipe(); let output = try collect(pipe)
        defer { pipe.fileHandleForReading.readabilityHandler = nil; try? pipe.fileHandleForWriting.close() }
        let receipt = Data("OWNED_SHORT\n".utf8)
        try pipe.fileHandleForWriting.write(contentsOf: receipt)
        let deadline = Date().addingTimeInterval(1)
        while output.read().bytes.isEmpty && Date() < deadline { try await Task.sleep(for: .milliseconds(10)) }
        // The writer is deliberately still open and fewer than 1 KiB exists.
        XCTAssertEqual(output.read().bytes, receipt); XCTAssertFalse(output.read().invalid)
    }

    func testOwnedReceiptPipeRejectsAggregateOverflow() async throws {
        let pipe = Pipe(); let output = try collect(pipe)
        defer { pipe.fileHandleForReading.readabilityHandler = nil; try? pipe.fileHandleForWriting.close() }
        try pipe.fileHandleForWriting.write(contentsOf: Data(repeating: 65, count: 4097))
        let deadline = Date().addingTimeInterval(1)
        while !output.read().invalid && Date() < deadline { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertTrue(output.read().invalid); XCTAssertLessThanOrEqual(output.read().bytes.count, 4096)
    }

    func testOwnedSampleExecutableLoadsEmptyWindowAndQuitsNormally() async throws {
        let (child, pipe, output, binary) = try launch()
        defer { pipe.fileHandleForReading.readabilityHandler = nil }
        do {
            let deadline = Date().addingTimeInterval(20)
            while child.isRunning && !contains("DISK_PREVIEW_READY_EMPTY_WINDOW", in: output) && Date() < deadline {
                try await Task.sleep(for: .milliseconds(30))
            }
            diagnose(child, output: output, binary: binary)
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
