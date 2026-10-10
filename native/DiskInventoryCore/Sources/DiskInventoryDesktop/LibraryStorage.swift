import Foundation
import Darwin

enum LibraryStorageAdmission: Equatable, Sendable { case ownedFixture, unavailable }

struct SavedLibraryEntry: Sendable, Equatable {
    let id: UUID
    let bytes: Int64
    let modifiedAt: Date
    fileprivate let owner: UUID
    fileprivate let name: String
    fileprivate let stamp: LibraryFileStamp
}

struct SavedLibraryListing: Sendable {
    let entries: [SavedLibraryEntry] // Complete bounded list; UI pagination must preserve its count.
    let pendingCount: Int
    let unknownCount: Int
    let listedLogicalBytes: Int64
    func page(_ offset: Int) throws -> [SavedLibraryEntry] {
        guard offset >= 0, offset <= entries.count else { throw LibraryStorageFailure.limit }
        return Array(entries.dropFirst(offset).prefix(64))
    }
}

struct LibrarySaveReceipt: Sendable, Equatable {
    let entry: SavedLibraryEntry
    fileprivate let attempt: UUID
}

enum LibrarySaveReconciliation: Sendable { case published(LibrarySaveReceipt), notPublishedPendingRetained }

// Synchronous one-lifetime interaction admission belongs to the actor identity,
// not to an injection wrapper. The lock protects only this in-memory bit; it is
// not a filesystem/root-wide or cross-process lock and is never reset.
private final class LibraryInteractionClaim: @unchecked Sendable {
    private let lock = NSLock()
    private var claimedOrRetired = false
    func claim() throws {
        lock.lock(); defer { lock.unlock() }
        guard !claimedOrRetired else { throw LibraryStorageFailure.busy }
        claimedOrRetired = true
    }
    func retire() {
        lock.lock(); defer { lock.unlock() }
        claimedOrRetired = true
    }
}

// Descriptor capability. Only a test-target factory creates/adopts an owned
// root; native interaction requires its one-use injected lease. No production
// path/container constructor or default executable storage capability exists.
actor LibraryStorage {
    static let maximumEntries = 256
    static let maximumListedBytes: Int64 = 64 * 1_024 * 1_024
    private struct Pending {
        let id: UUID
        let bytes: Data
        let original: LibraryFileStamp
        var receipt: LibrarySaveReceipt?
    }
    private nonisolated let interactionClaim = LibraryInteractionClaim()
    private var descriptor: Int32
    private let identity: LibraryFileStamp
    private let owner = UUID()
    private let io: LibraryFileIO
    private let guardAddress: @Sendable (Int32) throws -> Void
    private var active = false
    private var generation = UUID()
    private var usedAttempts = Set<UUID>()
    private var pending: Pending?

    // Ownership transfers even on rejected admission. A held FD and this enum do
    // not certify a signed app container; callers outside the module see no API.
    init(adopting descriptor: Int32, admission: LibraryStorageAdmission,
         guardAddress: @escaping @Sendable (Int32) throws -> Void,
         io: LibraryFileIO = LibraryFileIO()) throws {
        do {
            guard admission == .ownedFixture, descriptor >= 0 else { throw LibraryStorageFailure.invalidScope }
            let descriptorFlags = fcntl(descriptor, F_GETFD)
            guard descriptorFlags >= 0, descriptorFlags & FD_CLOEXEC != 0 else { throw LibraryStorageFailure.invalidScope }
            let identity = try io.metadata(descriptor)
            guard identity.directoryPrivate else { throw LibraryStorageFailure.invalidScope }
            try guardAddress(descriptor)
            self.descriptor = descriptor; self.identity = identity
            self.io = io; self.guardAddress = guardAddress
        } catch { if descriptor >= 0 { io.close(descriptor) }; throw error }
    }
    deinit { if descriptor >= 0 { io.close(descriptor) } }

    nonisolated func claimInteractionOwner() throws { try interactionClaim.claim() }

    func close() {
        interactionClaim.retire()
        generation = UUID()
        if descriptor >= 0 { io.close(descriptor); descriptor = -1 }
        pending = nil
    }

    private static func completed(_ id: UUID) -> String { "catalogue-" + id.uuidString.lowercased() + ".json" }
    private static func staging(_ id: UUID) -> String { "catalogue-" + id.uuidString.lowercased() + ".pending" }
    private static func identifier(_ name: String, suffix: String) -> UUID? {
        guard name.hasPrefix("catalogue-"), name.hasSuffix(suffix) else { return nil }
        let middle = String(name.dropFirst(10).dropLast(suffix.count))
        guard let id = UUID(uuidString: middle), id.uuidString.lowercased() == middle else { return nil }
        return id
    }
    private func guardRoot() throws {
        guard descriptor >= 0 else { throw LibraryStorageFailure.unavailable }
        let current = try io.metadata(descriptor)
        guard current.directoryPrivate, identity.sameIdentity(current) else { throw LibraryStorageFailure.changed }
        try guardAddress(descriptor)
    }
    private func begin() throws {
        guard !active, descriptor >= 0 else { throw LibraryStorageFailure.busy }
        try guardRoot(); active = true
    }
    private func entry(_ id: UUID, name: String, stamp: LibraryFileStamp) -> SavedLibraryEntry {
        SavedLibraryEntry(id: id, bytes: stamp.size,
            modifiedAt: Date(timeIntervalSince1970: Double(stamp.modifiedSeconds)),
            owner: owner, name: name, stamp: stamp)
    }

    private func scan(_ budget: inout LibraryIOBudget) throws -> SavedLibraryListing {
        try budget.check(); try guardRoot()
        let before = try io.metadata(descriptor)
        let names = try io.names(descriptor, budget: &budget)
        var entries: [SavedLibraryEntry] = [], pendingCount = 0, unknownCount = 0
        var total: Int64 = 0
        for raw in names {
            try budget.check()
            guard let name = String(data: raw, encoding: .utf8), Data(name.utf8) == raw,
                  !name.contains("/"), !name.contains("\0") else { throw LibraryStorageFailure.invalidFile }
            let stamp = try io.metadata(descriptor, name)
            guard stamp.regularPrivate, stamp.size <= Int64(CatalogueCodec.maximumBytes) else { throw LibraryStorageFailure.invalidFile }
            total += stamp.size
            guard total <= Self.maximumListedBytes else { throw LibraryStorageFailure.limit }
            if let id = Self.identifier(name, suffix: ".json") { entries.append(entry(id, name: name, stamp: stamp)) }
            else if Self.identifier(name, suffix: ".pending") != nil { pendingCount += 1 }
            else { unknownCount += 1 }
        }
        try guardRoot()
        guard before == (try io.metadata(descriptor)) else { throw LibraryStorageFailure.changed }
        entries.sort { $0.modifiedAt == $1.modifiedAt ? $0.name < $1.name : $0.modifiedAt > $1.modifiedAt }
        return SavedLibraryListing(entries: entries, pendingCount: pendingCount, unknownCount: unknownCount, listedLogicalBytes: total)
    }

    func list() throws -> SavedLibraryListing {
        try begin(); defer { active = false }
        var budget = LibraryIOBudget()
        return try scan(&budget)
    }

    private func read(_ fd: Int32, budget: inout LibraryIOBudget) throws -> (Data, LibraryFileStamp) {
        try budget.check()
        let before = try io.metadata(fd)
        guard before.regularPrivate, before.size <= Int64(CatalogueCodec.maximumBytes) else { throw LibraryStorageFailure.invalidFile }
        try io.rewind(fd)
        var bytes = Data()
        while true {
            try budget.check()
            do {
                let chunk = try io.read(fd, maximum: min(65_536, CatalogueCodec.maximumBytes - bytes.count + 1))
                if chunk.isEmpty { break }
                bytes.append(chunk)
                guard bytes.count <= CatalogueCodec.maximumBytes else { throw LibraryStorageFailure.limit }
            } catch LibraryStorageFailure.filesystem(let code) where code == EINTR { continue }
        }
        guard before == (try io.metadata(fd)), before.size == Int64(bytes.count) else { throw LibraryStorageFailure.changed }
        return (bytes, before)
    }
    private func read(_ name: String, budget: inout LibraryIOBudget) throws -> (Data, LibraryFileStamp) {
        try budget.check()
        let fd = try io.openRead(descriptor, name)
        defer { io.close(fd) }
        let result = try read(fd, budget: &budget)
        guard result.1 == (try io.metadata(descriptor, name)) else { throw LibraryStorageFailure.changed }
        return result
    }

    func save(_ catalogue: ValidatedCatalogue, attempt: UUID = UUID()) throws -> LibrarySaveReceipt {
        try begin(); defer { active = false }
        guard pending == nil, !usedAttempts.contains(attempt), usedAttempts.count < Self.maximumEntries else { throw LibraryStorageFailure.busy }
        usedAttempts.insert(attempt)
        var budget = LibraryIOBudget()
        let listing = try scan(&budget)
        guard listing.entries.count + listing.pendingCount + listing.unknownCount < Self.maximumEntries,
              listing.listedLogicalBytes + Int64(catalogue.bytes.count) <= Self.maximumListedBytes else { throw LibraryStorageFailure.limit }
        try budget.check(); try guardRoot()
        let name = Self.staging(attempt)
        let fd = try io.create(descriptor, name)
        defer { io.close(fd) }
        let initial = try io.metadata(fd)
        guard initial.regularPrivate, initial.size == 0 else { throw LibraryStorageFailure.invalidFile }
        var offset = 0
        while offset < catalogue.bytes.count {
            try budget.check()
            do {
                let count = try catalogue.bytes.withUnsafeBytes { raw in
                    try io.write(fd, UnsafeRawBufferPointer(rebasing: raw[offset..<min(offset + 65_536, raw.count)]))
                }
                guard count > 0, count <= min(65_536, catalogue.bytes.count - offset) else { throw LibraryStorageFailure.invalidFile }
                offset += count
            } catch LibraryStorageFailure.filesystem(let code) where code == EINTR { continue }
        }
        while true {
            try budget.check()
            do { try io.flush(fd); break }
            catch LibraryStorageFailure.filesystem(let code) where code == EINTR { continue }
        }
        let verified = try read(fd, budget: &budget)
        guard verified.0 == catalogue.bytes, initial.sameIdentity(verified.1),
              verified.1 == (try io.metadata(descriptor, name)) else { throw LibraryStorageFailure.changed }
        try budget.check(); try guardRoot()
        // From this point any ambiguous syscall/result is retained for explicit
        // reconciliation. No automatic retry, overwrite, deletion or fallback.
        pending = Pending(id: attempt, bytes: catalogue.bytes, original: verified.1)
        do {
            try io.publish(descriptor, pending: name, completed: Self.completed(attempt))
            return try verifyPublished(&budget)
        } catch { throw LibraryStorageFailure.uncertain }
    }

    private func verifyPublished(_ budget: inout LibraryIOBudget) throws -> LibrarySaveReceipt {
        guard let expected = pending else { throw LibraryStorageFailure.unavailable }
        try budget.check(); try guardRoot()
        let name = Self.completed(expected.id)
        let observed = try read(name, budget: &budget)
        guard observed.0 == expected.bytes, expected.original.sameIdentity(observed.1) else { throw LibraryStorageFailure.changed }
        if let receipt = expected.receipt { guard receipt.entry.stamp == observed.1 else { throw LibraryStorageFailure.changed } }
        try guardRoot()
        let receipt = LibrarySaveReceipt(entry: entry(expected.id, name: name, stamp: observed.1), attempt: expected.id)
        pending?.receipt = receipt
        return receipt
    }

    func reconcile() throws -> LibrarySaveReconciliation {
        try begin(); defer { active = false }
        guard let expected = pending else { throw LibraryStorageFailure.unavailable }
        var budget = LibraryIOBudget()
        do { return .published(try verifyPublished(&budget)) }
        catch LibraryStorageFailure.filesystem(let code) where code == ENOENT {
            // A completed artifact absent now is insufficient: require the exact
            // original pending file and bytes before reporting unpublished.
            do {
                let observed = try read(Self.staging(expected.id), budget: &budget)
                guard observed.0 == expected.bytes, observed.1 == expected.original, expected.receipt == nil else { throw LibraryStorageFailure.uncertain }
                try guardRoot(); pending = nil
                return .notPublishedPendingRetained
            } catch { throw LibraryStorageFailure.uncertain }
        } catch { throw LibraryStorageFailure.uncertain }
    }

    func acknowledge(_ receipt: LibrarySaveReceipt) throws {
        try begin(); defer { active = false }
        guard receipt.entry.owner == owner, pending?.receipt == receipt else { throw LibraryStorageFailure.unavailable }
        var budget = LibraryIOBudget()
        guard try verifyPublished(&budget) == receipt else { throw LibraryStorageFailure.changed }
        pending = nil
    }

    func open(_ entry: SavedLibraryEntry, codec: any CatalogueValidating) async throws -> ValidatedCatalogue {
        try begin(); defer { active = false }
        guard pending == nil, entry.owner == owner, Self.completed(entry.id) == entry.name else { throw LibraryStorageFailure.unavailable }
        let token = generation
        var budget = LibraryIOBudget()
        let observed = try read(entry.name, budget: &budget)
        guard observed.1 == entry.stamp else { throw LibraryStorageFailure.changed }
        try guardRoot()
        let validated = try await codec.validate(observed.0)
        try budget.check()
        guard token == generation, descriptor >= 0 else { throw LibraryStorageFailure.unavailable }
        guard entry.stamp == (try io.metadata(descriptor, entry.name)) else { throw LibraryStorageFailure.changed }
        try guardRoot()
        return validated
    }
}
