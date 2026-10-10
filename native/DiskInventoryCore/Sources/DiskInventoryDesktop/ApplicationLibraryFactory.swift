import Foundation
import Darwin

enum ApplicationLibraryIntent: Sendable { case save, open }

// A cancellation request is observed at syscall-admission checkpoints. It never
// claims to interrupt an already-admitted syscall or delete retained setup data.
final class ApplicationLibraryCancellation: @unchecked Sendable {
    private let mutex = NSLock()
    private var requested = false
    func cancel() { mutex.lock(); requested = true; mutex.unlock() }
    var isCancelled: Bool { mutex.lock(); defer { mutex.unlock() }; return requested }
}
enum ApplicationLibraryFailure: Error { case inUse, incompleteSetup, ambiguousSetup, retired }

protocol LibraryStorageProviding: Sendable {
    func resolve(_ intent: ApplicationLibraryIntent, cancellation: ApplicationLibraryCancellation) async throws -> LibraryStorage?
    func retire() async
}

private struct ApplicationHomeMarker: Sendable {
    static let schema = "disk-organiser/app-library-home/v1"
    let instance: UUID
    let identity: LibraryFileStamp
    var bytes: Data {
        get throws {
            try JSONSerialization.data(withJSONObject: ["schema": Self.schema,
                "instance": instance.uuidString.lowercased(), "device": String(identity.device),
                "inode": String(identity.inode)], options: [.sortedKeys, .withoutEscapingSlashes])
        }
    }
    init(instance: UUID = UUID(), identity: LibraryFileStamp) { self.instance = instance; self.identity = identity }
    init(_ bytes: Data, identity: LibraryFileStamp) throws {
        guard bytes.count <= 512, let object = try JSONSerialization.jsonObject(with: bytes) as? [String: String],
              Set(object.keys) == Set(["schema", "instance", "device", "inode"]),
              object["schema"] == Self.schema, object["device"] == String(identity.device),
              object["inode"] == String(identity.inode), let raw = object["instance"],
              let id = UUID(uuidString: raw), id.uuidString.lowercased() == raw else {
            throw ApplicationLibraryFailure.incompleteSetup
        }
        instance = id; self.identity = identity
        // Exact canonical bytes also refuse duplicate keys, extra whitespace,
        // alternate escaping, malformed Unicode and lossy JSON interpretations.
        guard try self.bytes == bytes else { throw ApplicationLibraryFailure.incompleteSetup }
    }
}

// No duplicated lease descriptors, unlock-by-name, unlink or lock replacement.
// One actor lifetime owns this object; its lock serializes validate/retire.
final class ApplicationLibraryLease: @unchecked Sendable {
    private let mutex = NSLock()
    private let parent: ApplicationLibraryParent
    private var home: Int32
    private var lock: Int32
    private var ownsDescriptors = false
    private let homeIdentity: LibraryFileStamp
    private let lockIdentity: LibraryFileStamp
    private let markerIdentity: LibraryFileStamp
    private let io: ApplicationLibraryIO
    fileprivate init(parent: ApplicationLibraryParent, home: Int32, lock: Int32,
                     homeIdentity: LibraryFileStamp, lockIdentity: LibraryFileStamp,
                     markerIdentity: LibraryFileStamp, io: ApplicationLibraryIO) {
        self.parent = parent; self.home = home; self.lock = lock
        self.homeIdentity = homeIdentity; self.lockIdentity = lockIdentity
        self.markerIdentity = markerIdentity; self.io = io
    }
    deinit { retire() }
    fileprivate func adopt() {
        mutex.lock(); defer { mutex.unlock() }
        ownsDescriptors = true
    }
    func validate(_ versions: Int32) throws {
        mutex.lock(); defer { mutex.unlock() }
        guard home >= 0, lock >= 0 else { throw ApplicationLibraryFailure.retired }
        try parent.validate()
        let currentHome = try io.privateDirectory(home)
        let currentLock = try io.privateFile(lock, maximum: 0)
        let currentVersions = try io.privateDirectory(versions)
        guard homeIdentity.sameIdentity(currentHome), lockIdentity == currentLock,
              try io.metadata(parent.descriptor, ApplicationLibraryFactory.homeName).sameIdentity(currentHome),
              try io.metadata(home, ApplicationLibraryFactory.lockName) == lockIdentity,
              try io.metadata(home, ApplicationLibraryFactory.markerName) == markerIdentity,
              try io.metadata(home, ApplicationLibraryFactory.versionsName).sameIdentity(currentVersions) else {
            throw LibraryStorageFailure.changed
        }
        var budget = LibraryIOBudget()
        guard Set(try io.names(home, maximum: 3, budget: &budget)) == Set([
            ApplicationLibraryFactory.markerName, ApplicationLibraryFactory.lockName,
            ApplicationLibraryFactory.versionsName].map { Data($0.utf8) }) else { throw LibraryStorageFailure.changed }
        guard try io.optionalMetadata(parent.descriptor, ApplicationLibraryFactory.setupName) == nil else {
            throw ApplicationLibraryFailure.ambiguousSetup
        }
    }
    func retire() {
        mutex.lock(); defer { mutex.unlock() }
        if ownsDescriptors {
            if lock >= 0 { io.close(lock) }
            if home >= 0 { io.close(home) }
        }
        lock = -1; home = -1; ownsDescriptors = false
    }
}

// Its constructor is file-private: the namespace factory, not an enum value or
// arbitrary module caller, establishes application-data admission.
final class ApplicationLibraryRoot: @unchecked Sendable {
    private let mutex = NSLock()
    private var descriptor: Int32
    private let lease: ApplicationLibraryLease
    fileprivate init(adopting descriptor: Int32, lease: ApplicationLibraryLease) {
        self.descriptor = descriptor; self.lease = lease
    }
    deinit { if descriptor >= 0 { _ = Darwin.close(descriptor); lease.retire() } }
    func consume() throws -> (Int32, ApplicationLibraryLease) {
        mutex.lock(); defer { mutex.unlock() }
        guard descriptor >= 0 else { throw LibraryStorageFailure.busy }
        let value = descriptor; descriptor = -1
        return (value, lease)
    }
}

actor ApplicationLibraryFactory: LibraryStorageProviding {
    static let homeName = "Disk Organiser Preview"
    static let setupName = ".disk-organiser-preview-setup-v1"
    static let markerName = "home.json"
    static let lockName = "library.lock"
    static let versionsName = "versions"
    private let opener: any ApplicationLibraryParentOpening
    private let io: ApplicationLibraryIO
    private var parent: ApplicationLibraryParent?
    private var retired = false
    private var pendingSetup: ApplicationHomeMarker?
    init(opener: any ApplicationLibraryParentOpening = SystemApplicationLibraryParent(),
         io: ApplicationLibraryIO = ApplicationLibraryIO()) {
        self.opener = opener; self.io = io
    }
    func retire() { retired = true; parent = nil }
    func resolve(_ intent: ApplicationLibraryIntent, cancellation: ApplicationLibraryCancellation) throws -> LibraryStorage? {
        guard !retired else { throw ApplicationLibraryFailure.retired }
        var budget = LibraryIOBudget(cancelled: { cancellation.isCancelled }); try budget.check()
        if parent == nil { parent = try opener.openParent() }
        let parent = parent!
        try parent.validate()
        let final = try io.optionalMetadata(parent.descriptor, Self.homeName)
        let setup = try io.optionalMetadata(parent.descriptor, Self.setupName)
        guard final == nil || setup == nil else { throw ApplicationLibraryFailure.ambiguousSetup }
        if final != nil {
            let root = try admit(parent, name: Self.homeName, expected: pendingSetup, publish: false, budget: &budget)
            try budget.check(); pendingSetup = nil
            return try LibraryStorage(applicationData: root)
        }
        if intent == .open {
            if setup != nil { throw ApplicationLibraryFailure.incompleteSetup }
            return nil // Open never creates even a lock file.
        }
        if setup == nil {
            guard pendingSetup == nil else { throw LibraryStorageFailure.changed }
            try budget.check(); try parent.validate()
            try io.createDirectory(parent.descriptor, Self.setupName)
            let home = try io.openDirectory(parent.descriptor, Self.setupName)
            defer { io.close(home) }
            let stamp = try io.privateDirectory(home)
            let marker = ApplicationHomeMarker(identity: stamp)
            pendingSetup = marker // Retained before the next fallible syscall.
            var lock: Int32 = -1
            defer { if lock >= 0 { io.close(lock) } }
            try budget.check(); lock = try io.create(home, Self.lockName)
            let lockStamp = try io.privateFile(lock, maximum: 0)
            guard try io.metadata(home, Self.lockName) == lockStamp else { throw LibraryStorageFailure.changed }
            try io.acquireLease(lock)
            try budget.check(); try io.createDirectory(home, Self.versionsName)
            let versions = try io.openDirectory(home, Self.versionsName)
            defer { io.close(versions) }
            _ = try io.privateDirectory(versions)
            try budget.check()
            let markerFile = try io.create(home, Self.markerName)
            defer { io.close(markerFile) }
            let bytes = try marker.bytes
            var offset = 0
            while offset < bytes.count {
                try budget.check()
                do {
                    let amount = try bytes.withUnsafeBytes { try io.write(markerFile, UnsafeRawBufferPointer(rebasing: $0[offset...])) }
                    guard amount > 0, amount <= bytes.count - offset else { throw LibraryStorageFailure.invalidFile }
                    offset += amount
                } catch LibraryStorageFailure.filesystem(let code) where code == EINTR { continue }
            }
            _ = try readMarker(home, identity: stamp, budget: &budget)
            try budget.check(); try io.flush(markerFile)
            try budget.check(); try io.flush(versions)
            try budget.check(); try io.flush(home)
            // Retain this exact lease until publication, rather than reopening a
            // new lock while another creator may be completing initialization.
            let root = try publishPrepared(parent, home: home, lock: lock, marker: marker, budget: &budget)
            lock = -1 // Ownership transferred only after successful root creation.
            pendingSetup = nil
            return try LibraryStorage(applicationData: root)
        }
        let root = try admit(parent, name: Self.setupName, expected: pendingSetup, publish: true, budget: &budget)
        try budget.check(); pendingSetup = nil
        return try LibraryStorage(applicationData: root)
    }
    private func exactEntries(_ home: Int32, budget: inout LibraryIOBudget) throws {
        let names = try io.names(home, maximum: 3, budget: &budget)
        guard Set(names) == Set([Self.markerName, Self.lockName, Self.versionsName].map { Data($0.utf8) }) else {
            throw ApplicationLibraryFailure.incompleteSetup
        }
    }
    private func readMarker(_ home: Int32, identity: LibraryFileStamp, budget: inout LibraryIOBudget) throws -> (ApplicationHomeMarker, LibraryFileStamp) {
        try budget.check()
        let fd = try io.openRead(home, Self.markerName)
        defer { io.close(fd) }
        let stamp = try io.privateFile(fd, maximum: 512)
        var bytes = Data()
        while true {
            try budget.check()
            do {
                let chunk = try io.read(fd, maximum: 513 - bytes.count)
                if chunk.isEmpty { break }
                bytes.append(chunk)
                guard bytes.count <= 512 else { throw ApplicationLibraryFailure.incompleteSetup }
            } catch LibraryStorageFailure.filesystem(let code) where code == EINTR { continue }
        }
        guard stamp.size == Int64(bytes.count), try io.metadata(fd) == stamp,
              try io.metadata(home, Self.markerName) == stamp else { throw LibraryStorageFailure.changed }
        return (try ApplicationHomeMarker(bytes, identity: identity), stamp)
    }
    private func admit(_ parent: ApplicationLibraryParent, name: String, expected: ApplicationHomeMarker?,
                       publish: Bool, budget: inout LibraryIOBudget) throws -> ApplicationLibraryRoot {
        try budget.check()
        var home = try io.openDirectory(parent.descriptor, name)
        var lock: Int32 = -1
        defer { if home >= 0 { io.close(home) }; if lock >= 0 { io.close(lock) } }
        let stamp = try io.privateDirectory(home)
        try exactEntries(home, budget: &budget)
        lock = try io.openLease(home); let lockStamp = try io.privateFile(lock, maximum: 0)
        guard try io.metadata(home, Self.lockName) == lockStamp else { throw LibraryStorageFailure.changed }
        try io.acquireLease(lock)
        let (marker, _) = try readMarker(home, identity: stamp, budget: &budget)
        if let expected {
            guard expected.instance == marker.instance, expected.identity.sameIdentity(stamp) else { throw LibraryStorageFailure.changed }
        }
        if publish {
            pendingSetup = marker
            let result = try publishPrepared(parent, home: home, lock: lock, marker: marker, budget: &budget)
            lock = -1
            return result
        }
        let result = try makeRoot(parent, home: home, lock: lock, budget: &budget)
        home = -1; lock = -1
        return result
    }
    private func publishPrepared(_ parent: ApplicationLibraryParent, home: Int32, lock: Int32,
                                 marker: ApplicationHomeMarker, budget: inout LibraryIOBudget) throws -> ApplicationLibraryRoot {
        try exactEntries(home, budget: &budget)
        let versions = try io.openDirectory(home, Self.versionsName)
        defer { io.close(versions) }
        _ = try io.privateDirectory(versions)
        _ = try io.names(versions, maximum: 0, budget: &budget)
        let markerFile = try io.openRead(home, Self.markerName)
        defer { io.close(markerFile) }
        // Recovery re-flushes complete setup before publication as well. This
        // never repairs content, permissions or an unrecognised partial setup.
        try budget.check(); try io.flush(markerFile)
        try budget.check(); try io.flush(versions)
        try budget.check(); try io.flush(home)
        try parent.validate()
        guard try io.metadata(parent.descriptor, Self.setupName).sameIdentity(marker.identity),
              try io.optionalMetadata(parent.descriptor, Self.homeName) == nil else { throw LibraryStorageFailure.changed }
        try budget.check()
        try io.publish(parent.descriptor, pending: Self.setupName, completed: Self.homeName)
        // Cancellation after rename is retained setup uncertainty, not a fake
        // cancellation receipt. No catalogue file has been created yet.
        try budget.check(); try io.flush(parent.descriptor)
        // A new home descriptor transfers into the lease. The caller still owns
        // its setup-era descriptor, which its defer closes without unlocking.
        let finalHome = try io.openDirectory(parent.descriptor, Self.homeName)
        do {
            guard try io.metadata(finalHome).sameIdentity(marker.identity) else { throw LibraryStorageFailure.changed }
            return try makeRoot(parent, home: finalHome, lock: lock, budget: &budget)
        } catch { io.close(finalHome); throw error }
    }
    private func makeRoot(_ parent: ApplicationLibraryParent, home: Int32, lock: Int32,
                          budget: inout LibraryIOBudget) throws -> ApplicationLibraryRoot {
        try budget.check(); try parent.validate()
        let homeStamp = try io.privateDirectory(home), lockStamp = try io.privateFile(lock, maximum: 0)
        let (_, markerStamp) = try readMarker(home, identity: homeStamp, budget: &budget)
        let versions = try io.openDirectory(home, Self.versionsName)
        do {
            _ = try io.privateDirectory(versions)
            let lease = ApplicationLibraryLease(parent: parent, home: home, lock: lock,
                homeIdentity: homeStamp, lockIdentity: lockStamp, markerIdentity: markerStamp, io: io)
            try lease.validate(versions)
            lease.adopt() // Transfer home/lock only after every throwing guard.
            return ApplicationLibraryRoot(adopting: versions, lease: lease)
        } catch { io.close(versions); throw error }
    }
}
