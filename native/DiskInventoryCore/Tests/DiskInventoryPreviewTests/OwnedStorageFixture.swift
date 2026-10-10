import XCTest
import Foundation
import Darwin
@testable import DiskInventoryDesktop

// The sole raw-root factory. Every path comes from this newly created private
// test directory. No environment variable, user selection or legacy data enters.
final class OwnedStorageFixture: @unchecked Sendable {
    let base: String
    let directory: String
    let sentinel: String
    private let sentinelBytes = Data("owned storage adjacent sentinel".utf8)
    init(mode: mode_t = 0o700) throws {
        var template = Array("/private/tmp/disk-library-storage-owned-XXXXXX".utf8CString)
        base = try template.withUnsafeMutableBufferPointer {
            guard let result = mkdtemp($0.baseAddress!) else { throw LibraryStorageFailure.filesystem(errno) }
            return String(cString: result)
        }
        directory = base + "/library"; sentinel = base + "/sentinel"
        guard mkdir(directory, mode) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        try Self.create(sentinel, bytes: sentinelBytes)
    }
    func store(io: LibraryFileIO = LibraryFileIO()) throws -> LibraryStorage {
        let fd = try Self.openDirectory(directory)
        return try LibraryStorage(adopting: fd, admission: .ownedFixture, guardAddress: { [self] held in
            let current = try Self.openDirectory(directory)
            defer { Darwin.close(current) }
            let plain = LibraryFileIO()
            let selected = try plain.metadata(current), actual = try plain.metadata(held)
            guard selected.directoryPrivate, actual.directoryPrivate, selected.sameIdentity(actual) else { throw LibraryStorageFailure.changed }
        }, io: io)
    }
    func rejectionDescriptor() throws -> Int32 { try Self.openDirectory(directory) }
    private static func openDirectory(_ path: String) throws -> Int32 {
        var fd = Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        do {
            for component in path.split(separator: "/") {
                let child = openat(fd, String(component), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard child >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
                Darwin.close(fd); fd = child
            }
            return fd
        } catch { Darwin.close(fd); throw error }
    }
    func path(_ name: String) -> String {
        precondition(!name.isEmpty && !name.contains("/") && !name.contains("\0") && name != "." && name != "..")
        return directory + "/" + name
    }
    func file(_ name: String, bytes: Data) throws { try Self.create(path(name), bytes: bytes) }
    func sparse(_ name: String, bytes: Int64) throws {
        let fd = Darwin.open(path(name), O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        defer { Darwin.close(fd) }
        guard ftruncate(fd, bytes) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
    }
    static func create(_ path: String, bytes: Data) throws {
        let fd = Darwin.open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        defer { Darwin.close(fd) }
        var offset = 0
        while offset < bytes.count {
            let wrote = bytes.withUnsafeBytes { Darwin.write(fd, $0.baseAddress!.advanced(by: offset), bytes.count - offset) }
            guard wrote > 0 else { throw LibraryStorageFailure.filesystem(errno) }
            offset += wrote
        }
    }
    func assertSentinel(file: StaticString = #filePath, line: UInt = #line) throws {
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: sentinel)), sentinelBytes, file: file, line: line)
    }
    deinit { try? FileManager.default.removeItem(atPath: base) }
}

// Fault state is configured before each awaited actor call and read afterwards.
// No concurrent test or production path shares this instance.
final class StorageFaultIO: LibraryFileIO, @unchecked Sendable {
    var writeChunk = 65_536, readChunk = 65_536
    var writeInterrupts = 0, readInterrupts = 0, flushInterrupts = 0
    var failAfterBytes: Int?
    var written = 0
    var failBeforePublish = false, failAfterPublish = false, corruptRead = false
    var afterRead: (@Sendable () throws -> Void)?
    var reportedSize: Int64?
    var readCalls = 0
    override func metadata(_ descriptor: Int32) throws -> LibraryFileStamp {
        var raw = stat()
        guard fstat(descriptor, &raw) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        if raw.st_mode & UInt16(S_IFMT) == UInt16(S_IFREG), let reportedSize { raw.st_size = reportedSize }
        return try LibraryFileStamp(raw)
    }
    var readOpens = 0
    var closedDescriptors: [Int32] = []
    override func close(_ descriptor: Int32) { closedDescriptors.append(descriptor); super.close(descriptor) }
    override func openRead(_ parent: Int32, _ name: String) throws -> Int32 {
        readOpens += 1
        return try super.openRead(parent, name)
    }
    override func write(_ descriptor: Int32, _ bytes: UnsafeRawBufferPointer) throws -> Int {
        if writeInterrupts > 0 { writeInterrupts -= 1; throw LibraryStorageFailure.filesystem(EINTR) }
        if let maximum = failAfterBytes, written >= maximum { throw LibraryStorageFailure.filesystem(ENOSPC) }
        let count = try super.write(descriptor, UnsafeRawBufferPointer(rebasing: bytes.prefix(writeChunk)))
        written += count
        return count
    }
    override func read(_ descriptor: Int32, maximum: Int) throws -> Data {
        readCalls += 1
        if readInterrupts > 0 { readInterrupts -= 1; throw LibraryStorageFailure.filesystem(EINTR) }
        var data = try super.read(descriptor, maximum: min(maximum, readChunk))
        if corruptRead, !data.isEmpty { data[0] ^= 1 }
        if let action = afterRead { afterRead = nil; try action() }
        return data
    }
    override func flush(_ descriptor: Int32) throws {
        if flushInterrupts > 0 { flushInterrupts -= 1; throw LibraryStorageFailure.filesystem(EINTR) }
        try super.flush(descriptor)
    }
    override func publish(_ parent: Int32, pending: String, completed: String) throws {
        if failBeforePublish { throw LibraryStorageFailure.filesystem(EINTR) }
        try super.publish(parent, pending: pending, completed: completed)
        if failAfterPublish { throw LibraryStorageFailure.filesystem(EIO) }
    }
}

// Tests suspend only after real strict admission; there is no fake accepted value.
actor HeldCatalogueAdmission: CatalogueValidating {
    private var arrived = false
    private var released = false
    func validate(_ bytes: Data) async throws -> ValidatedCatalogue {
        let result = try await CatalogueCodec().validate(bytes)
        arrived = true
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !released {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
        return result
    }
    func waitForArrival() async throws {
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !arrived {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
    }
    func release() { released = true }
}
