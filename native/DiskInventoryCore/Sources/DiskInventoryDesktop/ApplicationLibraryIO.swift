import Foundation
import Darwin

// Namespace operations are separate from immutable catalogue-file operations.
// No fallback, recursive cleanup or permission repair is provided.
class ApplicationLibraryIO: LibraryFileIO, @unchecked Sendable {
    override func create(_ parent: Int32, _ name: String) throws -> Int32 {
        let fd = try super.create(parent, name)
        do { _ = try privateFile(fd, maximum: 0); return fd }
        catch { close(fd); throw error }
    }
    override func openRead(_ parent: Int32, _ name: String) throws -> Int32 {
        let fd = try super.openRead(parent, name)
        do { _ = try privateFile(fd, maximum: Int64.max); return fd }
        catch { close(fd); throw error }
    }
    func openDirectory(_ parent: Int32, _ name: String) throws -> Int32 {
        let fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return fd
    }
    func createDirectory(_ parent: Int32, _ name: String) throws {
        guard mkdirat(parent, name, 0o700) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
    }
    func openLease(_ parent: Int32) throws -> Int32 {
        let fd = openat(parent, ApplicationLibraryFactory.lockName, O_RDWR | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        return fd
    }
    func acquireLease(_ descriptor: Int32) throws {
        guard flock(descriptor, LOCK_EX | LOCK_NB) == 0 else {
            if errno == EWOULDBLOCK { throw ApplicationLibraryFailure.inUse }
            throw LibraryStorageFailure.filesystem(errno)
        }
    }
    func requireCloseOnExec(_ descriptor: Int32) throws {
        let flags = fcntl(descriptor, F_GETFD)
        guard flags >= 0, flags & FD_CLOEXEC != 0 else { throw LibraryStorageFailure.invalidScope }
    }
    func requireEmptyACL(_ descriptor: Int32) throws {
        // A successful extended descriptor stat distinguishes an absent ACL
        // from an unreadable/unsupported one. acl_get_fd_np alone returns nil
        // with ENOENT for ordinary files without an ACL on Darwin.
        guard let security = filesec_init() else { throw LibraryStorageFailure.filesystem(errno) }
        defer { filesec_free(security) }
        var info = stat()
        guard fstatx_np(descriptor, &info, security) == 0 else { throw LibraryStorageFailure.invalidScope }
        try requireEmptyACLMetadata(security)
    }
    // Kept separate so tests can exercise actual filesec/ACL API semantics in
    // memory without changing filesystem ACLs. Factory admission always starts
    // with the successful descriptor query above.
    func requireEmptyACLMetadata(_ security: filesec_t) throws {
        var present: Int32 = 0
        guard filesec_query_property(security, FILESEC_ACL, &present) == 0 else { throw LibraryStorageFailure.invalidScope }
        // Darwin returns a validity bit, not a normalized value of one.
        if present == 0 { return }
        var value: acl_t?
        guard filesec_get_property(security, FILESEC_ACL, &value) == 0, let acl = value else {
            throw LibraryStorageFailure.invalidScope
        }
        defer { _ = acl_free(UnsafeMutableRawPointer(acl)) }
        guard acl_valid(acl) == 0 else { throw LibraryStorageFailure.invalidScope }
        var entry: acl_entry_t?
        errno = 0
        let result = acl_get_entry(acl, Int32(ACL_FIRST_ENTRY.rawValue), &entry)
        guard result == -1, errno == EINVAL, entry == nil else { throw LibraryStorageFailure.invalidScope }
    }
    func privateDirectory(_ descriptor: Int32) throws -> LibraryFileStamp {
        try requireCloseOnExec(descriptor)
        let value = try metadata(descriptor)
        guard value.directoryPrivate, value.mode & 0o7000 == 0 else { throw LibraryStorageFailure.invalidScope }
        try requireEmptyACL(descriptor)
        return value
    }
    func privateFile(_ descriptor: Int32, maximum: Int64) throws -> LibraryFileStamp {
        try requireCloseOnExec(descriptor)
        let value = try metadata(descriptor)
        guard value.regularPrivate, value.mode & 0o7000 == 0, value.size <= maximum else { throw LibraryStorageFailure.invalidScope }
        try requireEmptyACL(descriptor)
        return value
    }
    func optionalMetadata(_ parent: Int32, _ name: String) throws -> LibraryFileStamp? {
        do { return try metadata(parent, name) }
        catch LibraryStorageFailure.filesystem(let code) where code == ENOENT { return nil }
    }
}

// One retained parent descriptor plus an address guard. Tests supply only a
// freshly owned descriptor at this internal seam, never a runtime path option.
final class ApplicationLibraryParent: @unchecked Sendable {
    let descriptor: Int32
    private let identity: LibraryFileStamp
    private let address: @Sendable (Int32) throws -> Void
    init(adopting descriptor: Int32, address: @escaping @Sendable (Int32) throws -> Void) throws {
        do {
            let io = ApplicationLibraryIO()
            try io.requireCloseOnExec(descriptor)
            let value = try io.metadata(descriptor)
            guard value.mode & UInt16(S_IFMT) == UInt16(S_IFDIR), value.owner == geteuid(),
                  value.mode & 0o022 == 0 else { throw LibraryStorageFailure.invalidScope }
            try address(descriptor)
            self.descriptor = descriptor; identity = value; self.address = address
        } catch { if descriptor >= 0 { _ = Darwin.close(descriptor) }; throw error }
    }
    deinit { _ = Darwin.close(descriptor) }
    func validate() throws {
        let value = try ApplicationLibraryIO().metadata(descriptor)
        guard value.sameIdentity(identity), value.mode & UInt16(S_IFMT) == UInt16(S_IFDIR),
              value.owner == geteuid(), value.mode & 0o022 == 0 else { throw LibraryStorageFailure.changed }
        try address(descriptor)
    }
}

protocol ApplicationLibraryParentOpening: Sendable {
    func openParent() throws -> ApplicationLibraryParent
}

struct SystemApplicationLibraryParent: ApplicationLibraryParentOpening {
    func openParent() throws -> ApplicationLibraryParent {
        // Deliberately not called at application launch or provider construction.
        let url = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                             appropriateFor: nil, create: false)
        guard url.isFileURL else { throw LibraryStorageFailure.invalidScope }
        let path = url.path
        let fd = try Self.openFixedPath(path)
        return try ApplicationLibraryParent(adopting: fd) { held in
            let current = try Self.openFixedPath(path)
            defer { _ = Darwin.close(current) }
            let io = ApplicationLibraryIO()
            guard try io.metadata(current).sameIdentity(io.metadata(held)) else { throw LibraryStorageFailure.changed }
        }
    }
    private static func openFixedPath(_ path: String) throws -> Int32 {
        let components = path.split(separator: "/", omittingEmptySubsequences: true).map(String.init)
        guard path.hasPrefix("/"), !path.contains("\0"), !components.isEmpty, components.count <= 64,
              components.allSatisfy({ $0 != "." && $0 != ".." && $0.utf8.count <= 255 }) else { throw LibraryStorageFailure.invalidScope }
        var fd = Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
        do {
            let io = ApplicationLibraryIO()
            var budget = LibraryIOBudget()
            for name in components {
                try budget.check()
                let next = try io.openDirectory(fd, name)
                _ = Darwin.close(fd); fd = next
                let value = try io.metadata(fd)
                guard value.mode & UInt16(S_IFMT) == UInt16(S_IFDIR),
                      value.owner == 0 || value.owner == geteuid(), value.mode & 0o022 == 0 else {
                    throw LibraryStorageFailure.invalidScope
                }
            }
            return fd
        } catch { _ = Darwin.close(fd); throw error }
    }
}
