import Foundation
import Darwin

// Internal descriptor-only primitives. Sources still belong only to tests;
// application-data admission has a separate fixed namespace factory.
enum LibraryStorageFailure: Error { case unavailable, invalidScope, invalidFile, limit, changed, busy, interrupted, uncertain, filesystem(Int32) }

struct LibraryFileStamp: Equatable, Sendable {
    let device: Int32
    let inode: UInt64
    let size: Int64
    let modifiedSeconds: Int64
    let modifiedNanos: Int64
    let changedSeconds: Int64
    let changedNanos: Int64
    let mode: UInt16
    let owner: UInt32
    let links: UInt16
    init(_ value: stat) throws {
        guard value.st_size >= 0 else { throw LibraryStorageFailure.invalidFile }
        device = value.st_dev; inode = value.st_ino; size = value.st_size
        modifiedSeconds = Int64(value.st_mtimespec.tv_sec); modifiedNanos = Int64(value.st_mtimespec.tv_nsec)
        changedSeconds = Int64(value.st_ctimespec.tv_sec); changedNanos = Int64(value.st_ctimespec.tv_nsec)
        mode = value.st_mode; owner = value.st_uid; links = value.st_nlink
    }
    var regularPrivate: Bool { mode & UInt16(S_IFMT) == UInt16(S_IFREG) && mode & 0o777 == 0o600 && owner == geteuid() && links == 1 }
    var directoryPrivate: Bool { mode & UInt16(S_IFMT) == UInt16(S_IFDIR) && mode & 0o777 == 0o700 && owner == geteuid() }
    func sameIdentity(_ other: Self) -> Bool { device == other.device && inode == other.inode }
}

struct LibraryIOBudget {
    private let until = ProcessInfo.processInfo.systemUptime + 5
    private var calls = 0
    private let cancelled: @Sendable () -> Bool
    init(cancelled: @escaping @Sendable () -> Bool = { false }) { self.cancelled = cancelled }
    mutating func check() throws {
        calls += 1
        guard calls <= 4096, ProcessInfo.processInfo.systemUptime < until, !Task.isCancelled, !cancelled() else {
            throw LibraryStorageFailure.interrupted
        }
    }
}

// The actor owns this object. Tests subclass syscall methods for bounded faults;
// application data uses its stricter namespace/privacy subclass.
class LibraryFileIO: @unchecked Sendable {
    func metadata(_ descriptor: Int32) throws -> LibraryFileStamp {
        var info = stat()
        guard fstat(descriptor, &info) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return try LibraryFileStamp(info)
    }
    func metadata(_ parent: Int32, _ name: String) throws -> LibraryFileStamp {
        var info = stat()
        guard fstatat(parent, name, &info, AT_SYMLINK_NOFOLLOW) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return try LibraryFileStamp(info)
    }
    func create(_ parent: Int32, _ name: String) throws -> Int32 {
        let fd = openat(parent, name, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK, 0o600)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return fd
    }
    func openRead(_ parent: Int32, _ name: String) throws -> Int32 {
        let fd = openat(parent, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return fd
    }
    func write(_ descriptor: Int32, _ bytes: UnsafeRawBufferPointer) throws -> Int {
        let result = Darwin.write(descriptor, bytes.baseAddress, bytes.count)
        guard result >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return result
    }
    func read(_ descriptor: Int32, maximum: Int) throws -> Data {
        var bytes = [UInt8](repeating: 0, count: maximum)
        let count = bytes.withUnsafeMutableBytes { Darwin.read(descriptor, $0.baseAddress, maximum) }
        guard count >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return Data(bytes.prefix(count))
    }
    func rewind(_ descriptor: Int32) throws {
        guard lseek(descriptor, 0, SEEK_SET) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
    }
    func flush(_ descriptor: Int32) throws {
        guard fsync(descriptor) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
    }
    func publish(_ parent: Int32, pending: String, completed: String) throws {
        guard renameatx_np(parent, pending, parent, completed, UInt32(RENAME_EXCL)) == 0 else {
            throw LibraryStorageFailure.filesystem(errno)
        }
    }
    func close(_ descriptor: Int32) { _ = Darwin.close(descriptor) }

    func names(_ parent: Int32, budget: inout LibraryIOBudget) throws -> [Data] {
        try names(parent, maximum: 256, budget: &budget)
    }
    func names(_ parent: Int32, maximum: Int, budget: inout LibraryIOBudget) throws -> [Data] {
        guard (0...256).contains(maximum) else { throw LibraryStorageFailure.limit }
        try budget.check()
        // A new file description gives each listing an independent directory cursor.
        let fd = openat(parent, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        guard let stream = fdopendir(fd) else {
            let error = errno; close(fd); throw LibraryStorageFailure.filesystem(error)
        }
        var streamOpen = true
        defer { if streamOpen { closedir(stream) } }
        var result: [Data] = []
        while true {
            try budget.check()
            errno = 0
            guard let entry = readdir(stream) else {
                guard errno == 0 else { throw LibraryStorageFailure.filesystem(errno) }
                let closed = closedir(stream)
                let closeError = errno
                streamOpen = false
                guard closed == 0 else { throw LibraryStorageFailure.filesystem(closeError) }
                return result
            }
            let length = Int(entry.pointee.d_namlen)
            var raw = entry.pointee.d_name
            let name = try withUnsafeBytes(of: &raw) { bytes -> Data in
                guard length > 0, length < bytes.count, bytes[length] == 0 else { throw LibraryStorageFailure.invalidFile }
                return Data(bytes.prefix(length))
            }
            if name == Data(".".utf8) || name == Data("..".utf8) { continue }
            result.append(name)
            guard result.count <= maximum else { throw LibraryStorageFailure.limit }
        }
    }
}
