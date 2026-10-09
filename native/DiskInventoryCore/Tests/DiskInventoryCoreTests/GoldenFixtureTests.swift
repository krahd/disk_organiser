import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class GoldenFixtureTests: XCTestCase {
    func testSixOwnedGoldenObservations() throws {
        let environment = ProcessInfo.processInfo.environment
        var output: Int32?
        if let destination = environment["DISK_INVENTORY_GOLDEN_OUTPUT"] {
            let parent = try XCTUnwrap(environment["RUNNER_TEMP"])
            guard !parent.isEmpty, parent.hasPrefix("/"), destination == parent + "/disk-inventory-goldens" else {
                throw CoreFailure.invalidProjection
            }
            // The workflow owns RUNNER_TEMP; this test exclusively creates its fixed
            // generated-artifact directory. No source selection is taken from the environment.
            guard mkdir(destination, 0o700) == 0 else { throw CoreFailure.filesystem(errno) }
            let fd = Darwin.open(destination, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw CoreFailure.filesystem(errno) }
            output = fd
        }
        defer { if let output { _ = Darwin.close(output) } }
        for name in ["empty", "nested", "links", "placeholder", "depth-limit", "directory-limit"] {
            let fixture = try OwnedFixture()
            switch name {
            case "nested":
                try fixture.directory("Projects")
                try fixture.file("notes.txt", bytes: 3)
                try fixture.file("Projects/README.md", bytes: 5)
                try fixture.file("Projects/Clip.mov", bytes: 7)
            case "links":
                try fixture.file("regular.txt", bytes: 3)
                try fixture.hardlink("regular.txt", "alias")
                try fixture.symlink("outside")
            case "placeholder":
                try fixture.file("report.icloud")
                try fixture.file("okay.txt", bytes: 1)
            case "depth-limit":
                let deep = (0...8).map { "d\($0)" }.joined(separator: "/")
                try fixture.directory(deep)
                try fixture.file(deep + "/leaf.txt", bytes: 1)
            case "directory-limit":
                for index in 0...500 { try fixture.file(String(format: "f%03d", index)) }
            default: break
            }
            let io = DarwinDirectoryIO()
            var released = false
            let lease = try fixture.lease(io: io, release: { released = true })
            let controller = ObservationController(lease: lease, io: io, seams: ObservationSeams(clock: { 0 }))
            let result = try controller.observe(label: "Owned fixture " + name)
            let bytes = try XCTUnwrap(result.snapshot)
            XCTAssertTrue(released)
            XCTAssertEqual(fcntl(lease.descriptor, F_GETFD), -1)
            XCTAssertLessThanOrEqual(bytes.count, Bounds.snapshotBytes)
            try fixture.assertSentinel()
            if let output { try writeGenerated(bytes, name: name + ".json", directory: output) }
        }
    }

    private func writeGenerated(_ bytes: Data, name: String, directory: Int32) throws {
        let (descriptor, code) = try withRawName(Data(name.utf8)) {
            let descriptor = openat(directory, $0, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
            return (descriptor, errno)
        }
        guard descriptor >= 0 else { throw CoreFailure.filesystem(code) }
        defer { _ = Darwin.close(descriptor) }
        // Artifact output is test-only, never the production source reader.
        try bytes.withUnsafeBytes { buffer in
            var written = 0
            while written < buffer.count {
                let count = Darwin.write(descriptor, buffer.baseAddress!.advanced(by: written), buffer.count - written)
                guard count > 0 else { throw CoreFailure.filesystem(errno) }
                written += count
            }
        }
    }
}
