import Foundation
import Darwin

// Quarantined feasibility source only. No production target imports this file.
enum ProbeFailure: Error {
    case refused(String)
    case syscall(String, Int32)
    case cleanup(String, Int32)
}

struct ProbeObject: Equatable, Sendable {
    let device: Int64
    let inode: UInt64
    let mode: UInt32
    let uid: UInt32
    let gid: UInt32
    let size: Int64
    let links: UInt64
    let modificationSeconds: Int64
    let modificationNanoseconds: Int64
    let changeSeconds: Int64
    let changeNanoseconds: Int64

    init(_ value: stat) {
        device = Int64(value.st_dev); inode = UInt64(value.st_ino)
        mode = UInt32(value.st_mode); uid = value.st_uid; gid = value.st_gid
        size = value.st_size
        links = UInt64(value.st_nlink)
        modificationSeconds = Int64(value.st_mtimespec.tv_sec)
        modificationNanoseconds = Int64(value.st_mtimespec.tv_nsec)
        changeSeconds = Int64(value.st_ctimespec.tv_sec)
        changeNanoseconds = Int64(value.st_ctimespec.tv_nsec)
    }
    init(device: Int64, inode: UInt64, mode: UInt32, uid: UInt32, gid: UInt32, size: Int64) {
        self.device = device; self.inode = inode; self.mode = mode
        self.uid = uid; self.gid = gid; self.size = size
        links = 1
        // Fixture claims bind identity/mode/size only. Actual before/after read
        // comparisons use the observed initializer and include both timestamps.
        modificationSeconds = 0; modificationNanoseconds = 0
        changeSeconds = 0; changeNanoseconds = 0
    }
    func matches(_ other: ProbeObject, directory: Bool) -> Bool {
        device == other.device && inode == other.inode && mode == other.mode &&
        uid == other.uid && gid == other.gid && (directory || size == other.size)
    }
}

// One syscall sequence owns this ledger on one worker. An acquired descriptor
// is registered before any following operation; close errors retire the number
// permanently and do not stop retirement of the remaining owned descriptors.
final class ProbeDescriptors {
    private var owned: [Int32] = []
    private var streams: [OpaquePointer] = []
    private var cleanupFailure: (String, Int32)?

    func acquire(_ operation: String, _ open: () -> Int32) throws -> Int32 {
        let fd = open()
        guard fd >= 0 else { throw ProbeFailure.syscall(operation, errno) }
        owned.append(fd)
        return fd
    }
    func retire(_ fd: Int32) {
        guard let index = owned.firstIndex(of: fd) else {
            if cleanupFailure == nil { cleanupFailure = ("unowned-retirement", EINVAL) }
            return
        }
        owned.remove(at: index)
        if Darwin.close(fd) != 0, cleanupFailure == nil {
            cleanupFailure = ("close", errno)
        }
    }
    func finish() throws {
        for stream in streams.reversed() {
            streams.removeAll { $0 == stream }
            if closedir(stream) != 0, cleanupFailure == nil { cleanupFailure = ("closedir", errno) }
        }
        for fd in owned.reversed() { retire(fd) }
        if let (operation, code) = cleanupFailure { throw ProbeFailure.cleanup(operation, code) }
    }
    deinit {
        for stream in streams.reversed() { _ = closedir(stream) }
        for fd in owned.reversed() { _ = Darwin.close(fd) }
    }

    func firstParentEntry(_ fd: Int32) throws {
        guard let index = owned.firstIndex(of: fd) else { throw ProbeFailure.refused("unowned-stream-transfer") }
        guard let stream = fdopendir(fd) else { throw ProbeFailure.syscall("parent-stream-open", errno) }
        owned.remove(at: index) // fdopendir consumes the descriptor only on success.
        streams.append(stream)
        errno = 0
        let item = readdir(stream)
        let code = errno
        if item == nil, code != 0 { throw ProbeFailure.syscall("parent-entry-read", code) }
        // No name is copied or logged; one successful result or genuine EOF is
        // an allowed listing operation and therefore fails the denial oracle.
    }

    func metadata(_ fd: Int32) throws -> ProbeObject {
        var value = stat()
        guard fstat(fd, &value) == 0 else { throw ProbeFailure.syscall("fstat", errno) }
        return ProbeObject(value)
    }

    func requireEmptyACL(_ fd: Int32) throws {
        guard let security = filesec_init() else { throw ProbeFailure.syscall("filesec_init", errno) }
        defer { filesec_free(security) }
        var value = stat()
        guard fstatx_np(fd, &value, security) == 0 else { throw ProbeFailure.syscall("fstatx_np", errno) }
        var present: Int32 = 0
        guard filesec_query_property(security, FILESEC_ACL, &present) == 0 else {
            throw ProbeFailure.syscall("filesec_query", errno)
        }
        if present == 0 { return }
        var acl: acl_t?
        guard filesec_get_property(security, FILESEC_ACL, &acl) == 0, let acl else {
            throw ProbeFailure.refused("missing-acl")
        }
        defer { _ = acl_free(UnsafeMutableRawPointer(acl)) }
        guard acl_valid(acl) == 0 else { throw ProbeFailure.refused("invalid-acl") }
        var entry: acl_entry_t?
        errno = 0
        let result = acl_get_entry(acl, Int32(ACL_FIRST_ENTRY.rawValue), &entry)
        guard result == -1, errno == EINVAL, entry == nil else {
            throw ProbeFailure.refused("nonempty-or-unreadable-acl")
        }
    }

    // Identical operation before/during/after scope. This deliberately measures
    // the existing test admission's ancestor-open algorithm, without listings.
    // It never substitutes realpath, follows aliases or opens a broader root.
    func directory(_ path: String) throws -> Int32 {
        let parts = path.split(separator: "/", omittingEmptySubsequences: false)
        guard path.utf8.count <= 4096, parts.first == "", parts.count > 1,
              parts.dropFirst().allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              !path.contains("\\"), !path.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) else {
            throw ProbeFailure.refused("path-shape")
        }
        var current = try acquire("root-open") {
            Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        }
        for part in parts.dropFirst() {
            let next = try acquire("ancestor-open") {
                String(part).withCString { openat(current, $0, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC) }
            }
            retire(current)
            current = next
            guard try metadata(current).mode & UInt32(S_IFMT) == UInt32(S_IFDIR) else {
                throw ProbeFailure.refused("ancestor-type")
            }
        }
        return current
    }

    func selectedControl(parent: String, expectedDirectory: ProbeObject?,
                         expectedFile: ProbeObject, expectedBytes: Data,
                         leafName: String = "probe.bin",
                         whileBorrowed: () throws -> Void = {}) throws {
        guard expectedBytes.count == 32, ["probe.bin", "sentinel.bin"].contains(leafName) else {
            throw ProbeFailure.refused("control-length-or-leaf")
        }
        let directory = try self.directory(parent)
        let initialDirectory = try metadata(directory)
        guard initialDirectory.mode == UInt32(S_IFDIR | 0o700), initialDirectory.device == expectedFile.device,
              initialDirectory.uid == expectedFile.uid, initialDirectory.gid == expectedFile.gid,
              expectedDirectory?.matches(initialDirectory, directory: true) ?? true else {
            throw ProbeFailure.refused("selected-directory-identity")
        }
        try requireEmptyACL(directory)
        let file = try acquire("selected-content-open") {
            leafName.withCString { openat(directory, $0, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK) }
        }
        let initial = try metadata(file)
        guard initial.mode & UInt32(S_IFMT) == UInt32(S_IFREG), initial.size == 32, initial.links == 1,
              expectedFile.matches(initial, directory: false) else {
            throw ProbeFailure.refused("selected-content-identity")
        }
        try requireEmptyACL(file)
        var bytes = [UInt8](repeating: 0, count: 33)
        var used = 0
        var attempts = 0
        while used < bytes.count {
            attempts += 1
            guard attempts <= 64 else { throw ProbeFailure.refused("read-attempt-budget") }
            let amount = bytes.withUnsafeMutableBytes { buffer in
                read(file, buffer.baseAddress!.advanced(by: used), buffer.count - used)
            }
            if amount == 0 { break }
            if amount < 0 {
                let code = errno
                if code == EINTR { continue }
                throw ProbeFailure.syscall("selected-content-read", code)
            }
            used += amount
        }
        guard used == 32, Data(bytes.prefix(used)) == expectedBytes else {
            throw ProbeFailure.refused("control-content")
        }
        try whileBorrowed()
        guard
              initial == (try metadata(file)),
              initialDirectory == (try metadata(directory)) else {
            throw ProbeFailure.refused("control-content-or-race")
        }
    }

    static func perform<T>(_ body: (ProbeDescriptors) throws -> T) throws -> T {
        let ledger = ProbeDescriptors()
        do {
            let result = try body(ledger)
            try ledger.finish()
            return result
        } catch {
            // A cleanup problem outranks an apparent access denial. Finish keeps
            // its error latched and never retries an ambiguously closed number.
            let operationError = error
            try ledger.finish()
            throw operationError
        }
    }
}
