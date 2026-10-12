import Foundation
import Darwin

enum ProbeMatrix {
    private static func requireDenial(_ operations: Set<String>, _ body: () throws -> Void) throws -> ObservedDenial {
        do { try body() }
        catch {
            if let denial = ProbePolicy.denial(error, operations: operations) { return denial }
            throw error
        }
        // ENOENT/EEXIST, type/identity/ACL failures, cleanup errors and every
        // other error propagate. A failed setup is never an access-denial pass.
        throw ProbeFailure.refused("operation-unexpectedly-allowed")
    }

    private static func selectedRead(_ fixture: ProbeFixture, whileBorrowed: () throws -> Void = {}) throws {
        guard let folder = fixture.objects["selected"], let file = fixture.objects["selectedFile"] else {
            throw ProbeFailure.refused("missing-selected-object")
        }
        try ProbeDescriptors.perform {
            try $0.selectedControl(parent: fixture.selected, expectedDirectory: folder,
                                   expectedFile: file, expectedBytes: ProbeFixture.selectedBytes,
                                   whileBorrowed: whileBorrowed)
        }
    }

    static func selectedDenied(_ fixture: ProbeFixture) throws -> ObservedDenial {
        try requireDenial(ProbePolicy.selectedOperations) { try selectedRead(fixture) }
    }

    static func selectedAllowed(_ fixture: ProbeFixture, whileBorrowed: () throws -> Void) throws {
        // Exactly the same operation as the before/after denial controls.
        try selectedRead(fixture, whileBorrowed: whileBorrowed)
    }

    static func outsideAndWriteDenied(_ fixture: ProbeFixture, stopped: () -> Bool) throws -> [ObservedDenial] {
        func admit() throws { if stopped() { throw ProbeFailure.refused("work-cancelled") } }
        try admit()
        let sibling = try requireDenial(ProbePolicy.activeOperations[0]) {
            try ProbeDescriptors.perform { ledger in
                let directory = try ledger.directory(fixture.parent + "/outside")
                let fd = try ledger.acquire("sibling-read-open") {
                    openat(directory, "sentinel.bin", O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
                }
                guard let expected = fixture.objects["siblingFile"],
                      expected.matches(try ledger.metadata(fd), directory: false) else {
                    throw ProbeFailure.refused("sibling-target-changed")
                }
                // Opening for read is already unexpected access; do not consume
                // the sibling's contents or turn this into a filesystem scan.
            }
        }
        try admit()
        let parent = try requireDenial(ProbePolicy.activeOperations[1]) {
            try ProbeDescriptors.perform { ledger in
                let fd = try ledger.directory(fixture.parent)
                guard let expected = fixture.objects["parent"],
                      expected.matches(try ledger.metadata(fd), directory: true) else {
                    throw ProbeFailure.refused("parent-target-changed")
                }
                // Metadata-only ancestor opens are also needed by the positive
                // control. Denial here concerns listing, not that same open.
                try ledger.firstParentEntry(fd)
            }
        }
        try admit()
        let write = try requireDenial(ProbePolicy.activeOperations[2]) {
            try ProbeDescriptors.perform { ledger in
                let directory = try ledger.directory(fixture.selected)
                guard let selected = fixture.objects["selected"],
                      selected.matches(try ledger.metadata(directory), directory: true) else {
                    throw ProbeFailure.refused("write-parent-changed")
                }
                let fd = try ledger.acquire("selected-write-open") {
                    openat(directory, "probe.bin", O_WRONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
                }
                guard let expected = fixture.objects["selectedFile"],
                      expected.matches(try ledger.metadata(fd), directory: false) else {
                    throw ProbeFailure.refused("write-target-changed")
                }
                // No write or truncation occurs, even on a failed boundary.
            }
        }
        try admit()
        let create = try requireDenial(ProbePolicy.activeOperations[3]) {
            try ProbeDescriptors.perform { ledger in
                let directory = try ledger.directory(fixture.selected)
                guard let selected = fixture.objects["selected"],
                      selected.matches(try ledger.metadata(directory), directory: true) else {
                    throw ProbeFailure.refused("create-parent-changed")
                }
                _ = try ledger.acquire("selected-create-exclusive") {
                    openat(directory, "must-remain-absent.bin", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0o600)
                }
                // Unexpected creation fails the experiment. The host does not
                // delete or repair it; the external fixture controller records
                // it before retiring its own test directory after process exit.
            }
        }
        return [sibling, parent, write, create]
    }
}
