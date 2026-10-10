import Foundation
import Darwin
@testable import DiskInventoryDesktop

// This seam is compiled only into XCTest/probe. Every opener receives a newly
// created test directory; no environment or ordinary executable path override.
final class OwnedApplicationParentOpener: ApplicationLibraryParentOpening, @unchecked Sendable {
    let fixture: OwnedStorageFixture
    private let mutex = NSLock()
    private var count = 0
    init(_ fixture: OwnedStorageFixture) { self.fixture = fixture }
    var calls: Int { mutex.lock(); defer { mutex.unlock() }; return count }
    func openParent() throws -> ApplicationLibraryParent {
        mutex.lock(); count += 1; mutex.unlock()
        let fd = try fixture.rejectionDescriptor()
        return try ApplicationLibraryParent(adopting: fd) { [fixture] held in
            let current = try fixture.rejectionDescriptor()
            defer { Darwin.close(current) }
            let io = LibraryFileIO()
            guard try io.metadata(held).sameIdentity(io.metadata(current)) else { throw LibraryStorageFailure.changed }
        }
    }
}

final class ApplicationFaultIO: ApplicationLibraryIO, @unchecked Sendable {
    var creates = 0, writes = 0, publications = 0
    var failCreateName: String?
    var failBeforePublish = false, failAfterPublish = false, failFlush = false
    var syntheticACLRefusal = false, syntheticWrongOwner = false
    var beforePublish: (@Sendable () throws -> Void)?
    var afterPublish: (@Sendable () -> Void)?
    override func createDirectory(_ parent: Int32, _ name: String) throws {
        creates += 1
        if name == failCreateName { throw LibraryStorageFailure.filesystem(ENOSPC) }
        try super.createDirectory(parent, name)
    }
    override func create(_ parent: Int32, _ name: String) throws -> Int32 {
        creates += 1
        if name == failCreateName { throw LibraryStorageFailure.filesystem(ENOSPC) }
        return try super.create(parent, name)
    }
    override func metadata(_ descriptor: Int32) throws -> LibraryFileStamp {
        if !syntheticWrongOwner { return try super.metadata(descriptor) }
        var raw = stat()
        guard fstat(descriptor, &raw) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        raw.st_uid = geteuid() == 0 ? 1 : 0
        return try LibraryFileStamp(raw)
    }
    override func requireEmptyACL(_ descriptor: Int32) throws {
        if syntheticACLRefusal { throw LibraryStorageFailure.invalidScope }
        try super.requireEmptyACL(descriptor)
    }
    override func write(_ descriptor: Int32, _ bytes: UnsafeRawBufferPointer) throws -> Int {
        writes += 1; return try super.write(descriptor, bytes)
    }
    override func flush(_ descriptor: Int32) throws {
        if failFlush { throw LibraryStorageFailure.filesystem(EIO) }
        try super.flush(descriptor)
    }
    override func publish(_ parent: Int32, pending: String, completed: String) throws {
        publications += 1
        if failBeforePublish { throw LibraryStorageFailure.filesystem(EIO) }
        try beforePublish?()
        try super.publish(parent, pending: pending, completed: completed)
        afterPublish?()
        if failAfterPublish { throw LibraryStorageFailure.filesystem(EIO) }
    }
}

actor HeldApplicationProvider: LibraryStorageProviding {
    private let factory: ApplicationLibraryFactory
    private var arrived = false, released = false
    private var resolves = 0
    init(_ factory: ApplicationLibraryFactory) { self.factory = factory }
    func resolve(_ intent: ApplicationLibraryIntent, cancellation: ApplicationLibraryCancellation) async throws -> LibraryStorage? {
        resolves += 1; arrived = true
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !released {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
        return try await factory.resolve(intent, cancellation: cancellation)
    }
    func wait() async throws {
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !arrived {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
    }
    func release() { released = true }
    func callCount() -> Int { resolves }
    func retire() async { await factory.retire() }
}

actor ReturnedApplicationProvider: LibraryStorageProviding {
    private let factory: ApplicationLibraryFactory
    private var result: LibraryStorage?
    private var arrived = false, released = false
    init(_ factory: ApplicationLibraryFactory) { self.factory = factory }
    func resolve(_ intent: ApplicationLibraryIntent, cancellation: ApplicationLibraryCancellation) async throws -> LibraryStorage? {
        result = try await factory.resolve(intent, cancellation: cancellation); arrived = true
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !released {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
        return result
    }
    func wait() async throws {
        let deadline = ProcessInfo.processInfo.systemUptime + 5
        while !arrived {
            guard ProcessInfo.processInfo.systemUptime < deadline else { throw LibraryStorageFailure.interrupted }
            try await Task.sleep(for: .milliseconds(5))
        }
    }
    func release() { released = true }
    func retire() async { await factory.retire() }
}

actor DuplicateApplicationProvider: LibraryStorageProviding {
    let existing: LibraryStorage
    init(_ existing: LibraryStorage) { self.existing = existing }
    func resolve(_ intent: ApplicationLibraryIntent, cancellation: ApplicationLibraryCancellation) async throws -> LibraryStorage? { existing }
    func retire() {}
}
