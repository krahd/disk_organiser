import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

// The only raw-root constructor lives in this test target. Every accepted path is
// inside this fixture's newly created directory; no environment variable selects a source.
final class OwnedFixture {
    let base: String
    let source: String
    let sentinel: String
    private let sentinelBytes = Data("owned adjacent sentinel: unchanged".utf8)

    init(sourceRelative: String = "selected") throws {
        var template = Array("/private/tmp/disk-inventory-owned-XXXXXX".utf8CString)
        base = try template.withUnsafeMutableBufferPointer { buffer in
            guard let created = mkdtemp(buffer.baseAddress!) else { throw CoreFailure.filesystem(errno) }
            return String(cString: created)
        }
        precondition(!sourceRelative.hasPrefix("/") && !sourceRelative.split(separator: "/").contains(".."))
        source = base + "/" + sourceRelative
        sentinel = base + "/sentinel.txt"
        try FileManager.default.createDirectory(atPath: source, withIntermediateDirectories: true)
        try sentinelBytes.write(to: URL(fileURLWithPath: sentinel), options: .withoutOverwriting)
    }

    func directory(_ relative: String) throws {
        try FileManager.default.createDirectory(atPath: owned(relative), withIntermediateDirectories: true)
    }

    func file(_ relative: String, bytes: Int = 0) throws {
        try Data(repeating: 65, count: bytes).write(to: URL(fileURLWithPath: owned(relative)), options: .withoutOverwriting)
    }

    func symlink(_ relative: String, target: String? = nil) throws {
        guard Darwin.symlink(target ?? sentinel, owned(relative)) == 0 else { throw CoreFailure.filesystem(errno) }
    }

    func hardlink(_ old: String, _ new: String) throws {
        guard Darwin.link(owned(old), owned(new)) == 0 else { throw CoreFailure.filesystem(errno) }
    }

    func fifo(_ relative: String) throws {
        guard mkfifo(owned(relative), 0o600) == 0 else { throw CoreFailure.filesystem(errno) }
    }

    func owned(_ relative: String) -> String {
        precondition(!relative.isEmpty && !relative.hasPrefix("/")
            && !relative.split(separator: "/").contains(".."))
        return source + "/" + relative
    }

    func assertSentinel(file: StaticString = #filePath, line: UInt = #line) throws {
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: sentinel)), sentinelBytes, file: file, line: line)
    }

    func lease(io: DirectoryIO, admission: SourceAdmission = .ownedFixture,
               release: @escaping () -> Void = {}) throws -> HeldRootLease {
        let descriptor = try openRoot(source, io: io)
        let owner = OwnedDescriptor(adopting: descriptor, io: io)
        let selected = try io.metadata(descriptor)
        return HeldRootLease(owner: owner, selected: selected, admission: admission, guardAddress: { [self] held, scanner in
            let reopened = try openRoot(source, io: io)
            defer { io.close(reopened) }
            let current = try io.metadata(reopened)
            let heldMetadata = try io.metadata(held)
            let scannerMetadata = try io.metadata(scanner)
            guard current.fingerprint.sameDirectory(as: heldMetadata.fingerprint),
                  current.fingerprint.sameDirectory(as: scannerMetadata.fingerprint) else { throw CoreFailure.rootChanged }
            return current
        }, endOwnership: release)
    }

    // This re-walk reads ancestor metadata only, never ancestor directory listings.
    private func openRoot(_ path: String, io: DirectoryIO) throws -> Int32 {
        let bytes = Data(path.utf8)
        guard bytes.count <= 4_096, bytes.starts(with: Data((base + "/").utf8)),
              !path.contains("//"), !path.contains("\\"), !path.hasSuffix("/"),
              !path.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }),
              path.split(separator: "/").allSatisfy({ $0 != "." && $0 != ".." }) else {
            throw CoreFailure.invalidMetadata
        }
        var descriptor = Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { throw CoreFailure.filesystem(errno) }
        var initial = true
        do {
            for component in bytes.split(separator: 47) {
                let child = try io.openDirectory(parent: descriptor, name: Data(component))
                if initial { _ = Darwin.close(descriptor) } else { io.close(descriptor) }
                descriptor = child
                initial = false
                guard try io.metadata(descriptor).fingerprint.kind == .directory else { throw CoreFailure.invalidMetadata }
            }
            return descriptor
        } catch {
            if initial { _ = Darwin.close(descriptor) } else { io.close(descriptor) }
            throw error
        }
    }

    deinit {
        // Cleanup is confined to a fresh directory created by this fixture.
        try? FileManager.default.removeItem(atPath: base)
    }
}

final class LockedBox<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var value: Value
    init(_ value: Value) { self.value = value }
    func read() -> Value { lock.lock(); defer { lock.unlock() }; return value }
    func update<T>(_ body: (inout Value) -> T) -> T {
        lock.lock(); defer { lock.unlock() }; return body(&value)
    }
}

final class OwnershipAudit {
    private(set) var descriptors: Set<Int32> = []
    private(set) var streams: Set<Int32> = []
    private(set) var problems: [String] = []
    private(set) var acquisitions = 0
    private(set) var closures = 0

    func record(_ event: OwnershipEvent) {
        switch event {
        case .acquired(let fd):
            if descriptors.contains(fd) || streams.contains(fd) { problems.append("Acquired an already owned FD") }
            descriptors.insert(fd)
            acquisitions += 1
        case .closed(let fd):
            if descriptors.remove(fd) == nil { problems.append("Closed a non-owned FD") }
            closures += 1
        case .streamOwns(let fd):
            if descriptors.remove(fd) == nil { problems.append("Transferred a non-owned FD") }
            streams.insert(fd)
        case .streamClosed(let fd):
            if streams.remove(fd) == nil { problems.append("Closed a non-owned stream") }
            closures += 1
        }
    }

    func verify(file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(problems, [], file: file, line: line)
        XCTAssertEqual(descriptors, [], file: file, line: line)
        XCTAssertEqual(streams, [], file: file, line: line)
        XCTAssertEqual(acquisitions, closures, file: file, line: line)
    }
}

func fixtureResult(_ fixture: OwnedFixture, io: DirectoryIO = DarwinDirectoryIO(),
                   seams: ObservationSeams = ObservationSeams(), label: String = "Owned fixture") throws -> ObservationResult {
    let controller = ObservationController(lease: try fixture.lease(io: io), io: io, seams: seams)
    return try controller.observe(label: label)
}

func snapshotObject(_ result: ObservationResult, file: StaticString = #filePath, line: UInt = #line) throws -> [String: Any] {
    let data = try XCTUnwrap(result.snapshot, file: file, line: line)
    return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any], file: file, line: line)
}

func snapshotRows(_ result: ObservationResult) throws -> [[String: Any]] {
    try XCTUnwrap(snapshotObject(result)["entries"] as? [[String: Any]])
}

func snapshotGaps(_ result: ObservationResult) throws -> [String: Any] {
    try XCTUnwrap(snapshotObject(result)["gaps"] as? [String: Any])
}

func replacement(_ value: Metadata, device: Int64? = nil, inode: UInt64? = nil,
                 size: Int64? = nil, change: Int64? = nil, mode: UInt32? = nil, flags: UInt32? = nil) throws -> Metadata {
    let p = value.fingerprint
    return try Metadata(fingerprint: Fingerprint(device: device ?? p.device, inode: inode ?? p.inode,
        size: size ?? p.size, modificationSeconds: p.modificationSeconds, modificationNanoseconds: p.modificationNanoseconds,
        changeSeconds: change ?? p.changeSeconds, changeNanoseconds: p.changeNanoseconds,
        mode: mode ?? p.mode, links: p.links), flags: flags ?? value.flags)
}
