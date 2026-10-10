import XCTest
import Foundation
import Darwin
import CryptoKit
@testable import DiskInventoryDesktop

@MainActor
final class OwnedApplicationProbeProcess {
    private var pid: pid_t = 0
    private var input: Int32 = -1, output: Int32 = -1
    private var reaped = false
    private var pending = Data()
    private var total = 0
    let nonce = UUID().uuidString.lowercased()
    private(set) var status: Int32?
    static func fixtureBytes() throws -> Data {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        return try Data(contentsOf: root.appendingPathComponent("Validation/OwnedApplicationProbe/catalogue.json"))
    }
    init(fixture: OwnedStorageFixture, operation: String) throws {
        let package = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let binary = package.appendingPathComponent(".build/debug/owned-application-probe/DiskLibraryOwnedProbe").resolvingSymlinksInPath()
        let build = package.appendingPathComponent(".build").resolvingSymlinksInPath().path + "/"
        guard binary.path.hasPrefix(build), FileManager.default.isExecutableFile(atPath: binary.path),
              ["save-hold", "open", "hold"].contains(operation) else { throw LibraryStorageFailure.invalidScope }
        let original = try fixture.rejectionDescriptor()
        let root = fcntl(original, F_DUPFD_CLOEXEC, 20); Darwin.close(original)
        guard root >= 20 else { throw LibraryStorageFailure.filesystem(errno) }
        defer { Darwin.close(root) }
        let identity = try ApplicationLibraryIO().privateDirectory(root)
        let sentinel = Darwin.open(fixture.sentinel, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
        guard sentinel >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        let foreign = fcntl(sentinel, F_DUPFD_CLOEXEC, 200); Darwin.close(sentinel)
        guard foreign >= 200, foreign < 4096 else { if foreign >= 0 { Darwin.close(foreign) }; throw LibraryStorageFailure.invalidScope }
        defer { Darwin.close(foreign) }
        var incoming = [Int32](repeating: -1, count: 2), outgoing = incoming
        guard pipe(&incoming) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        guard pipe(&outgoing) == 0 else { incoming.forEach { Darwin.close($0) }; throw LibraryStorageFailure.filesystem(errno) }
        defer { Darwin.close(incoming[0]); Darwin.close(outgoing[1]) }
        input = incoming[1]; output = outgoing[0]
        var actions: posix_spawn_file_actions_t?
        var attributes: posix_spawnattr_t?
        guard posix_spawn_file_actions_init(&actions) == 0 else { closePipes(); throw LibraryStorageFailure.unavailable }
        defer { posix_spawn_file_actions_destroy(&actions) }
        guard posix_spawnattr_init(&attributes) == 0 else { closePipes(); throw LibraryStorageFailure.unavailable }
        defer { posix_spawnattr_destroy(&attributes) }
        do {
            for fd in incoming + outgoing {
                guard fcntl(fd, F_SETFD, FD_CLOEXEC) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
            }
            let flags = fcntl(output, F_GETFL)
            guard fcntl(input, F_SETNOSIGPIPE, 1) == 0, flags >= 0, fcntl(output, F_SETFL, flags | O_NONBLOCK) == 0,
                  posix_spawnattr_setflags(&attributes, Int16(POSIX_SPAWN_CLOEXEC_DEFAULT)) == 0,
                  posix_spawn_file_actions_adddup2(&actions, incoming[0], STDIN_FILENO) == 0,
                  posix_spawn_file_actions_adddup2(&actions, outgoing[1], STDOUT_FILENO) == 0,
                  posix_spawn_file_actions_addopen(&actions, STDERR_FILENO, "/dev/null", O_WRONLY, 0) == 0,
                  posix_spawn_file_actions_adddup2(&actions, root, 3) == 0 else { throw LibraryStorageFailure.unavailable }
            let argument = strdup(binary.path)
            guard let argument else { throw LibraryStorageFailure.unavailable }
            defer { free(argument) }
            var argv: [UnsafeMutablePointer<CChar>?] = [argument, nil]
            var environment: [UnsafeMutablePointer<CChar>?] = [nil]
            let result = argv.withUnsafeMutableBufferPointer { argv in
                environment.withUnsafeMutableBufferPointer { env in
                    posix_spawn(&pid, binary.path, &actions, &attributes, argv.baseAddress!, env.baseAddress!)
                }
            }
            guard result == 0, pid > 0 else { throw LibraryStorageFailure.filesystem(result) }
            try send(["nonce": nonce, "operation": operation, "device": String(identity.device), "inode": String(identity.inode), "foreignFD": String(foreign)])
        } catch { stop(); throw error }
    }
    private func closePipes() {
        if input >= 0 { Darwin.close(input); input = -1 }
        if output >= 0 { Darwin.close(output); output = -1 }
    }
    func send(_ fields: [String: String]) throws {
        var data = try JSONSerialization.data(withJSONObject: fields, options: [.sortedKeys]); data.append(10)
        guard input >= 0, data.count <= 512 else { throw LibraryStorageFailure.limit }
        var offset = 0
        while offset < data.count {
            let count = data.withUnsafeBytes { Darwin.write(input, $0.baseAddress!.advanced(by: offset), data.count - offset) }
            if count < 0 && errno == EINTR { continue }
            guard count > 0 else { throw LibraryStorageFailure.unavailable }; offset += count
        }
    }
    func read() async throws -> [String: String] {
        let until = Date().addingTimeInterval(8)
        while Date() < until {
            if let newline = pending.firstIndex(of: 10) {
                let data = pending.prefix(upTo: newline); pending.removeSubrange(...newline)
                guard data.count <= 512, let value = try JSONSerialization.jsonObject(with: data) as? [String: String], value["nonce"] == nonce else { throw LibraryStorageFailure.invalidFile }
                return value
            }
            var bytes = [UInt8](repeating: 0, count: 1024)
            let count = bytes.withUnsafeMutableBytes { Darwin.read(output, $0.baseAddress!, $0.count) }
            if count > 0 {
                total += count; guard total <= 2048 else { throw LibraryStorageFailure.limit }
                pending.append(contentsOf: bytes.prefix(count)); continue
            }
            if count == 0 { throw LibraryStorageFailure.unavailable }
            guard errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR else { throw LibraryStorageFailure.filesystem(errno) }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw LibraryStorageFailure.interrupted
    }
    func finish() async throws -> Int32 {
        let until = Date().addingTimeInterval(8)
        while Date() < until {
            var value: Int32 = 0
            let observed = waitpid(pid, &value, WNOHANG)
            if observed == pid { reaped = true; status = value; closePipes(); return value }
            guard observed == 0 || (observed == -1 && errno == EINTR) else { throw LibraryStorageFailure.unavailable }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw LibraryStorageFailure.interrupted
    }
    func closeNormally() async throws {
        try send(["nonce": nonce, "operation": "close"])
        let reply = try await read(); XCTAssertEqual(reply, ["nonce": nonce, "state": "closed"])
        let value = try await finish(); XCTAssertEqual(value, 0)
    }
    func crashOwnedChild() async throws {
        guard pid > 0, !reaped else { throw LibraryStorageFailure.invalidScope }
        XCTAssertEqual(Darwin.kill(pid, SIGKILL), 0)
        let value = try await finish(); XCTAssertEqual(value & 0x7f, SIGKILL)
    }
    func stop() {
        // Failure cleanup targets only the exact unreaped child created here.
        // It is never normal-exit or crash-release acceptance evidence.
        defer { closePipes() }
        guard pid > 0, !reaped else { return }
        let until = ProcessInfo.processInfo.systemUptime + 3
        var killed = false
        repeat {
            var value: Int32 = 0
            let observed = waitpid(pid, &value, WNOHANG)
            if observed == pid { reaped = true; status = value; return }
            if observed < 0 {
                if errno == EINTR { continue }
                // In particular ECHILD does not authorise a kill of a possibly
                // reused PID and is not a fabricated successful reap.
                XCTFail("Owned probe cleanup could not observe its child; reaping remains unconfirmed")
                return
            }
            if !killed {
                guard Darwin.kill(pid, SIGKILL) == 0 || errno == ESRCH else {
                    XCTFail("Owned probe cleanup could not signal its child"); return
                }
                killed = true
            }
            usleep(10_000)
        } while ProcessInfo.processInfo.systemUptime < until
        XCTFail("Owned probe cleanup exceeded its three-second reap deadline; no exit status was observed")
    }
}

@MainActor
final class ApplicationLibraryProcessTests: XCTestCase {
    func testOwnedProcessesProveContentionNormalRelaunchAndCrashLeaseRelease() async throws {
        let fixture = try OwnedStorageFixture()
        let expected = SHA256.hash(data: try OwnedApplicationProbeProcess.fixtureBytes()).map { String(format: "%02x", $0) }.joined()
        let first = try OwnedApplicationProbeProcess(fixture: fixture, operation: "save-hold")
        defer { first.stop() }
        let held = try await first.read()
        XCTAssertEqual(held, ["nonce": first.nonce, "state": "held", "sha256": expected, "foreignFD": "closed"])
        let second = try OwnedApplicationProbeProcess(fixture: fixture, operation: "open")
        defer { second.stop() }
        let refused = try await second.read()
        XCTAssertEqual(refused, ["nonce": second.nonce, "state": "in-use", "foreignFD": "closed"])
        let refusedExit = try await second.finish(); XCTAssertEqual(refusedExit, 0)
        try await first.closeNormally()
        let reopened = try OwnedApplicationProbeProcess(fixture: fixture, operation: "open")
        defer { reopened.stop() }
        let observed = try await reopened.read()
        XCTAssertEqual(observed, ["nonce": reopened.nonce, "state": "reopened", "sha256": expected, "foreignFD": "closed"])
        let closed = try await reopened.read(); XCTAssertEqual(closed["state"], "closed")
        let reopenedExit = try await reopened.finish(); XCTAssertEqual(reopenedExit, 0)
        let crash = try OwnedApplicationProbeProcess(fixture: fixture, operation: "hold")
        defer { crash.stop() }
        let beforeCrash = try await crash.read(); XCTAssertEqual(beforeCrash["sha256"], expected); XCTAssertEqual(beforeCrash["state"], "held")
        try await crash.crashOwnedChild()
        let after = try OwnedApplicationProbeProcess(fixture: fixture, operation: "open")
        defer { after.stop() }
        let afterCrash = try await after.read(); XCTAssertEqual(afterCrash["sha256"], expected); XCTAssertEqual(afterCrash["state"], "reopened")
        _ = try await after.read(); let afterExit = try await after.finish(); XCTAssertEqual(afterExit, 0)
        try fixture.assertSentinel()
        print("OWNED_APP_STORAGE_PROCESS contentions=1 normalRelaunch=1 crashRelease=1 exactBytes=true foreignDescriptorClosed=true")
    }
    func testOwnedProbeFailureCleanupHasObservedBoundedReap() async throws {
        let fixture = try OwnedStorageFixture()
        let child = try OwnedApplicationProbeProcess(fixture: fixture, operation: "save-hold")
        defer { child.stop() }
        let held = try await child.read(); XCTAssertEqual(held["state"], "held")
        let before = ProcessInfo.processInfo.systemUptime
        child.stop()
        XCTAssertLessThan(ProcessInfo.processInfo.systemUptime - before, 3.5)
        let status = try XCTUnwrap(child.status); XCTAssertEqual(status & 0x7f, SIGKILL)
        try fixture.assertSentinel()
    }

}
