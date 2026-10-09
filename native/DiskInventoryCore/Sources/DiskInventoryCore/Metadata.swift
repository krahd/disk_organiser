import Foundation
#if canImport(Darwin)
import Darwin
#else
#error("DiskInventoryCore Phase A requires Darwin. There is no traversal fallback.")
#endif

enum Bounds {
    static let entries = 2_000
    static let directoryEntries = 500
    static let depth = 8
    static let seconds: TimeInterval = 5
    static let snapshotBytes = 1_048_576
}

enum CoreFailure: Error {
    case filesystem(Int32)
    case invalidMetadata
    case invalidProjection
    case rootChanged
    case unavailable
    case alreadyConsumed
    case wrongProcess
}

enum EntryKind: String { case file, directory, symlink, special, unknown }
enum EntryStatus: String { case observed, stale, disappeared, unreadable, unsupported, excluded }

struct Fingerprint: Equatable {
    let device: Int64
    let inode: UInt64
    let size: Int64
    let modificationSeconds: Int64
    let modificationNanoseconds: Int64
    let changeSeconds: Int64
    let changeNanoseconds: Int64
    let mode: UInt32
    let links: UInt64

    var kind: EntryKind {
        switch mode & UInt32(S_IFMT) {
        case UInt32(S_IFREG): return .file
        case UInt32(S_IFDIR): return .directory
        case UInt32(S_IFLNK): return .symlink
        default: return .special
        }
    }

    func validate() throws {
        guard (0..<1_000_000_000).contains(modificationNanoseconds),
              (0..<1_000_000_000).contains(changeNanoseconds) else {
            throw CoreFailure.invalidMetadata
        }
    }

    func sameDirectory(as other: Fingerprint) -> Bool {
        kind == .directory && other.kind == .directory && device == other.device && inode == other.inode
    }
}

struct Metadata: Equatable {
    let fingerprint: Fingerprint
    let flags: UInt32

    init(fingerprint: Fingerprint, flags: UInt32 = 0) throws {
        try fingerprint.validate()
        self.fingerprint = fingerprint
        self.flags = flags
    }

    init(_ value: stat) throws {
        guard let device = Int64(exactly: value.st_dev),
              let inode = UInt64(exactly: value.st_ino),
              let size = Int64(exactly: value.st_size),
              let ms = Int64(exactly: value.st_mtimespec.tv_sec),
              let mn = Int64(exactly: value.st_mtimespec.tv_nsec),
              let cs = Int64(exactly: value.st_ctimespec.tv_sec),
              let cn = Int64(exactly: value.st_ctimespec.tv_nsec),
              let mode = UInt32(exactly: value.st_mode),
              let links = UInt64(exactly: value.st_nlink),
              let flags = UInt32(exactly: value.st_flags) else { throw CoreFailure.invalidMetadata }
        try self.init(fingerprint: Fingerprint(device: device, inode: inode, size: size,
            modificationSeconds: ms, modificationNanoseconds: mn,
            changeSeconds: cs, changeNanoseconds: cn, mode: mode, links: links), flags: flags)
    }

    var knownPlaceholder: Bool { flags & UInt32(SF_DATALESS) != 0 }
}

struct ObjectKey: Hashable {
    let device: Int64
    let inode: UInt64
}

struct InventoryEntry {
    // Data is intentional: String equality merges canonically equivalent spelling.
    let path: Data
    let kind: EntryKind
    var status: EntryStatus
    let logicalBytes: String?
    let fingerprint: Fingerprint?

    init(path: Data, metadata: Metadata? = nil, status: EntryStatus = .observed) {
        self.path = path
        self.kind = metadata?.fingerprint.kind ?? .unknown
        self.status = status
        self.fingerprint = metadata?.fingerprint
        self.logicalBytes = kind == .file ? String(metadata!.fingerprint.size) : nil
    }

    // Projection-only values are data, not a source lease or scanning entry point.
    init(path: Data, kind: EntryKind, status: EntryStatus = .observed, logicalBytes: String? = nil) {
        self.path = path
        self.kind = kind
        self.status = status
        self.logicalBytes = logicalBytes
        self.fingerprint = nil
    }

    var objectKey: ObjectKey? {
        guard kind == .file, let fingerprint, fingerprint.inode != 0 else { return nil }
        // st_dev == 0 is valid; only a zero file inode suppresses alias matching.
        return ObjectKey(device: fingerprint.device, inode: fingerprint.inode)
    }
}

struct Inventory {
    var entries: [InventoryEntry] = []
    var exclusions: [Data: Int] = [:]
    var exclusionCount = 0
    var errorCount = 0
    var stopReason: String?

    mutating func exclude(_ reason: String) {
        guard exclusionCount < Bounds.entries else {
            if stopReason == nil { stopReason = "exclusion_limit" }
            return
        }
        exclusions[Data(reason.utf8), default: 0] += 1
        exclusionCount += 1
    }

    mutating func markError(at index: Int, _ error: CoreFailure) {
        if case .filesystem(let code) = error, code == ENOENT {
            entries[index].status = .disappeared
        } else {
            entries[index].status = .unreadable
        }
        errorCount += 1
    }

    mutating func invalidate(from start: Int) {
        for index in start..<entries.count where entries[index].status == .observed {
            entries[index].status = .stale
        }
    }

    mutating func reconcileAliases() {
        var first: [ObjectKey: Fingerprint] = [:]
        var conflicts: Set<ObjectKey> = []
        for entry in entries {
            guard let key = entry.objectKey, let fingerprint = entry.fingerprint else { continue }
            if entry.status == .stale { conflicts.insert(key) }
            if entry.status == .observed {
                if let previous = first[key], previous != fingerprint { conflicts.insert(key) }
                if first[key] == nil { first[key] = fingerprint }
            }
        }
        for index in entries.indices {
            if let key = entries[index].objectKey, conflicts.contains(key) {
                entries[index].status = .stale
            }
        }
        entries.sort { $0.path.lexicographicallyPrecedes($1.path) }
    }

    var partial: Bool {
        stopReason != nil || errorCount != 0 || exclusionCount != 0 || !exclusions.isEmpty || entries.contains { $0.status != .observed }
    }
}

func withRawName<T>(_ bytes: Data, _ body: (UnsafePointer<CChar>) throws -> T) throws -> T {
    guard !bytes.isEmpty, !bytes.contains(0), !bytes.contains(47),
          bytes != Data(".".utf8), bytes != Data("..".utf8) else { throw CoreFailure.invalidMetadata }
    let terminated = Array(bytes) + [UInt8(0)]
    return try terminated.withUnsafeBytes { buffer in
        try body(buffer.baseAddress!.assumingMemoryBound(to: CChar.self))
    }
}
