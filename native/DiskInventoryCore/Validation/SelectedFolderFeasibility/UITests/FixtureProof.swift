import Foundation
import Darwin

enum FixtureProof {
    static func verify(_ fixture: ProbeFixture) throws {
        guard let parent = fixture.objects["parent"], let selected = fixture.objects["selected"],
              let file = fixture.objects["selectedFile"], let sibling = fixture.objects["siblingFile"] else {
            throw ProbeFailure.refused("proof-object-set")
        }
        try ProbeDescriptors.perform { ledger in
            let base = try ledger.directory(fixture.parent)
            guard parent.matches(try ledger.metadata(base), directory: true) else {
                throw ProbeFailure.refused("proof-parent-identity")
            }
            try ledger.requireEmptyACL(base)
            try ledger.selectedControl(parent: fixture.selected, expectedDirectory: selected,
                                       expectedFile: file, expectedBytes: ProbeFixture.selectedBytes)
            try ledger.selectedControl(parent: fixture.parent + "/outside", expectedDirectory: nil,
                                       expectedFile: sibling, expectedBytes: ProbeFixture.siblingBytes,
                                       leafName: "sentinel.bin")
            let directory = try ledger.directory(fixture.selected)
            guard selected.matches(try ledger.metadata(directory), directory: true) else {
                throw ProbeFailure.refused("proof-selected-identity")
            }
            var absent = stat()
            errno = 0
            let result = fstatat(directory, "must-remain-absent.bin", &absent, AT_SYMLINK_NOFOLLOW)
            guard result == -1, errno == ENOENT else { throw ProbeFailure.refused("proof-absent-control") }
            guard parent.matches(try ledger.metadata(base), directory: true) else {
                throw ProbeFailure.refused("proof-parent-race")
            }
        }
    }
}
