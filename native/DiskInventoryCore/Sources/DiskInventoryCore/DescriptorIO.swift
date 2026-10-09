import Foundation
import Darwin

enum DirectoryNames {
    case names([Data])
    case overLimit
    case interrupted
}

protocol DirectoryIO: AnyObject {
    func metadata(_ descriptor: Int32) throws -> Metadata
    func metadata(parent: Int32, name: Data) throws -> Metadata
    func openDirectory(parent: Int32, name: Data) throws -> Int32
    func duplicate(_ descriptor: Int32) throws -> Int32
    func names(_ descriptor: Int32, interrupted: () -> Bool) throws -> DirectoryNames
    func close(_ descriptor: Int32)
}

enum IOOperation: Equatable {
    case descriptorStat, childStat, directoryOpen, duplicate, descriptorFlags, closeOnExec, streamOpen, readEntry
}

enum OwnershipEvent {
    case acquired(Int32)
    case closed(Int32)
    case streamOwns(Int32)
    case streamClosed(Int32)
}

// Internal deterministic syscall seams. Neither a path factory nor a production admission policy.
struct IOSeams {
    var before: ((IOOperation, Int32, Data?) throws -> Void)?
    var metadata: ((IOOperation, Int32, Data?, Metadata) throws -> Metadata)?
    var ownership: ((OwnershipEvent) -> Void)?
    // Optional errno result injection executes the same failure/ownership branches
    // as Darwin. For readEntry, zero represents genuine EOF, nonzero an error.
    var failureResult: ((IOOperation, Int32) -> Int32?)?
    var didGatherName: ((Data) -> Void)?
}

final class DarwinDirectoryIO: DirectoryIO {
    private let seams: IOSeams

    init(seams: IOSeams = IOSeams()) { self.seams = seams }

    func metadata(_ descriptor: Int32) throws -> Metadata {
        try seams.before?(.descriptorStat, descriptor, nil)
        var value = stat()
        guard fstat(descriptor, &value) == 0 else { throw CoreFailure.filesystem(errno) }
        let result = try Metadata(value)
        return try seams.metadata?(.descriptorStat, descriptor, nil, result) ?? result
    }

    func metadata(parent: Int32, name: Data) throws -> Metadata {
        try seams.before?(.childStat, parent, name)
        var value = stat()
        let (result, code) = try withRawName(name) {
            let result = fstatat(parent, $0, &value, AT_SYMLINK_NOFOLLOW)
            return (result, errno)
        }
        guard result == 0 else { throw CoreFailure.filesystem(code) }
        let metadata = try Metadata(value)
        return try seams.metadata?(.childStat, parent, name, metadata) ?? metadata
    }

    func openDirectory(parent: Int32, name: Data) throws -> Int32 {
        try seams.before?(.directoryOpen, parent, name)
        let (descriptor, code) = try withRawName(name) {
            let descriptor = openat(parent, $0, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            return (descriptor, errno)
        }
        guard descriptor >= 0 else { throw CoreFailure.filesystem(code) }
        seams.ownership?(.acquired(descriptor))
        return descriptor
    }

    func duplicate(_ descriptor: Int32) throws -> Int32 {
        try seams.before?(.duplicate, descriptor, nil)
        let copy = dup(descriptor)
        guard copy >= 0 else { throw CoreFailure.filesystem(errno) }
        seams.ownership?(.acquired(copy))
        do {
            try seams.before?(.closeOnExec, copy, nil)
            let getError = seams.failureResult?(.descriptorFlags, copy)
            if let getError { errno = getError }
            let flags = getError == nil ? fcntl(copy, F_GETFD) : -1
            guard flags >= 0 else { throw CoreFailure.filesystem(errno) }
            let setError = seams.failureResult?(.closeOnExec, copy)
            if let setError { errno = setError }
            let setResult = setError == nil ? fcntl(copy, F_SETFD, flags | FD_CLOEXEC) : -1
            guard setResult == 0 else {
                throw CoreFailure.filesystem(errno)
            }
            return copy
        } catch {
            close(copy)
            throw error
        }
    }

    func names(_ descriptor: Int32, interrupted: () -> Bool) throws -> DirectoryNames {
        if interrupted() { return .interrupted }
        let copy = try duplicate(descriptor)
        if interrupted() { close(copy); return .interrupted }
        // fdopendir consumes the FD only on success. There is exactly one owner.
        do { try seams.before?(.streamOpen, copy, nil) } catch {
            close(copy)
            throw error
        }
        if interrupted() { close(copy); return .interrupted }
        let streamError = seams.failureResult?(.streamOpen, copy)
        if let streamError { errno = streamError }
        let openedStream = streamError == nil ? fdopendir(copy) : nil
        guard let stream = openedStream else {
            let code = errno
            close(copy)
            throw CoreFailure.filesystem(code)
        }
        seams.ownership?(.streamOwns(copy))
        var answer: DirectoryNames = .interrupted
        var failure: Error?
        do {
            var names: [Data] = []
            while !interrupted() {
                try seams.before?(.readEntry, copy, nil)
                if interrupted() { break }
                errno = 0
                let readError = seams.failureResult?(.readEntry, copy)
                if let readError { errno = readError }
                let nextEntry = readError == nil ? readdir(stream) : nil
                guard let entry = nextEntry else {
                    let code = errno
                    if code != 0 { throw CoreFailure.filesystem(code) }
                    answer = .names(names.sorted { $0.lexicographicallyPrecedes($1) })
                    break
                }
                if interrupted() { break }
                let length = Int(entry.pointee.d_namlen)
                var field = entry.pointee.d_name
                let name = try withUnsafeBytes(of: &field) { bytes -> Data in
                    guard length > 0, length < bytes.count, bytes[length] == 0 else {
                        throw CoreFailure.invalidMetadata
                    }
                    return Data(bytes.prefix(length))
                }
                if name == Data(".".utf8) || name == Data("..".utf8) { continue }
                names.append(name)
                seams.didGatherName?(name)
                if names.count > Bounds.directoryEntries {
                    answer = .overLimit
                    break
                }
            }
        } catch { failure = error }
        let closeResult = closedir(stream)
        let closeError = errno
        seams.ownership?(.streamClosed(copy))
        if let failure { throw failure } // No gathered subset survives an iteration error.
        if closeResult != 0 { throw CoreFailure.filesystem(closeError) }
        return answer
    }

    func close(_ descriptor: Int32) {
        // Never retry close: the descriptor may already have been recycled.
        _ = Darwin.close(descriptor)
        seams.ownership?(.closed(descriptor))
    }
}

final class OwnedDescriptor {
    let value: Int32
    private let io: DirectoryIO
    private var closed = false

    init(adopting value: Int32, io: DirectoryIO) {
        self.value = value
        self.io = io
    }

    func close() {
        guard !closed else { return }
        closed = true
        io.close(value)
    }

    deinit { close() }
}
