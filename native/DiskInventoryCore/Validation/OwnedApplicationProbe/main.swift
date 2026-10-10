import Foundation
import Darwin
import CryptoKit
@testable import DiskInventoryDesktop

// Separate test binary. No ordinary application target links this entry point.
// Descriptor 3 is the sole inherited directory capability; stdin/stdout are
// bounded control/receipt pipes. No path, environment or user-folder resolver.
private struct ProbeParent: ApplicationLibraryParentOpening {
    let parent: ApplicationLibraryParent
    func openParent() throws -> ApplicationLibraryParent { parent }
}
private func line() throws -> [String: String] {
    var data = Data()
    while data.count < 512 {
        var byte: UInt8 = 0
        let count = Darwin.read(STDIN_FILENO, &byte, 1)
        if count < 0 && errno == EINTR { continue }
        guard count == 1 else { throw LibraryStorageFailure.unavailable }
        if byte == 10 {
            guard let value = try JSONSerialization.jsonObject(with: data) as? [String: String] else { throw LibraryStorageFailure.invalidFile }
            return value
        }
        data.append(byte)
    }
    throw LibraryStorageFailure.limit
}
private func receipt(_ value: [String: String]) throws {
    var bytes = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    bytes.append(10)
    guard bytes.count <= 512 else { throw LibraryStorageFailure.limit }
    var offset = 0
    while offset < bytes.count {
        let amount = bytes.withUnsafeBytes { Darwin.write(STDOUT_FILENO, $0.baseAddress!.advanced(by: offset), bytes.count - offset) }
        if amount < 0 && errno == EINTR { continue }
        guard amount > 0 else { throw LibraryStorageFailure.unavailable }; offset += amount
    }
}
@main
struct OwnedApplicationProbe {
    static func main() async {
        do {
            guard CommandLine.arguments.count == 1 else { throw LibraryStorageFailure.invalidScope }
            let request = try line()
            guard Set(request.keys) == Set(["nonce", "operation", "device", "inode", "foreignFD"]),
                  let nonce = request["nonce"], UUID(uuidString: nonce)?.uuidString.lowercased() == nonce,
                  let operation = request["operation"], ["save-hold", "open", "hold"].contains(operation),
                  let foreign = Int32(request["foreignFD"]!), foreign >= 200, foreign < 4096 else { throw LibraryStorageFailure.invalidScope }
            errno = 0
            guard fcntl(foreign, F_GETFD) == -1, errno == EBADF else { throw LibraryStorageFailure.invalidScope }
            let flags = fcntl(3, F_GETFD)
            guard flags >= 0, fcntl(3, F_SETFD, flags | FD_CLOEXEC) == 0 else { throw LibraryStorageFailure.invalidScope }
            let stamp = try ApplicationLibraryIO().privateDirectory(3)
            guard request["device"] == String(stamp.device), request["inode"] == String(stamp.inode) else { throw LibraryStorageFailure.changed }
            // Parent identity is authenticated by the parent test's private pipe
            // and inherited descriptor. There is no pathname to re-resolve here.
            let parent = try ApplicationLibraryParent(adopting: 3) { held in
                guard try LibraryFileIO().metadata(held).sameIdentity(stamp) else { throw LibraryStorageFailure.changed }
            }
            let factory = ApplicationLibraryFactory(opener: ProbeParent(parent: parent))
            let store: LibraryStorage
            do {
                guard let admitted = try await factory.resolve(operation == "save-hold" ? .save : .open,
                                                               cancellation: ApplicationLibraryCancellation()) else { throw LibraryStorageFailure.unavailable }
                store = admitted
            } catch ApplicationLibraryFailure.inUse {
                try receipt(["nonce": nonce, "state": "in-use", "foreignFD": "closed"]); return
            }
            let fixtureURL = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent().appendingPathComponent("catalogue.json")
            let fixtureFD = Darwin.open(fixtureURL.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
            guard fixtureFD >= 0 else { throw LibraryStorageFailure.unavailable }
            defer { Darwin.close(fixtureFD) }
            let fixtureIO = LibraryFileIO(), fixtureStamp = try fixtureIO.metadata(fixtureFD)
            guard fixtureStamp.mode & UInt16(S_IFMT) == UInt16(S_IFREG), fixtureStamp.size > 0,
                  fixtureStamp.size <= 16_384, fixtureStamp.owner == geteuid() else { throw LibraryStorageFailure.invalidFile }
            var expected = Data(), fixtureBudget = LibraryIOBudget()
            while true {
                try fixtureBudget.check()
                let chunk = try fixtureIO.read(fixtureFD, maximum: 16_385 - expected.count)
                if chunk.isEmpty { break }; expected.append(chunk)
                guard expected.count <= 16_384 else { throw LibraryStorageFailure.limit }
            }
            guard Int64(expected.count) == fixtureStamp.size, try fixtureIO.metadata(fixtureFD) == fixtureStamp else { throw LibraryStorageFailure.changed }
            let validated = try await CatalogueCodec().validate(expected)
            if operation == "save-hold" {
                let saved = try await store.save(validated); try await store.acknowledge(saved)
            }
            let listing = try await store.list()
            guard listing.entries.count == 1, listing.pendingCount == 0,
                  let entry = listing.entries.first else { throw LibraryStorageFailure.invalidFile }
            let loaded = try await store.open(entry, codec: CatalogueCodec())
            guard loaded.bytes == validated.bytes else { throw LibraryStorageFailure.changed }
            let digest = SHA256.hash(data: loaded.bytes).map { String(format: "%02x", $0) }.joined()
            try receipt(["nonce": nonce, "state": operation == "open" ? "reopened" : "held", "sha256": digest, "foreignFD": "closed"])
            if operation != "open" {
                let close = try line()
                guard close == ["nonce": nonce, "operation": "close"] else { throw LibraryStorageFailure.invalidScope }
            }
            await store.close(); await factory.retire()
            try receipt(["nonce": nonce, "state": "closed"])
        } catch {
            // Fixed failure receipt cannot disclose fixture paths or content.
            try? receipt(["state": "failed"])
            exit(1)
        }
    }
}
