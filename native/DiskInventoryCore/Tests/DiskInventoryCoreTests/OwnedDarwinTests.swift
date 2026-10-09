import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class OwnedDarwinTests: XCTestCase {
    func testTrueEmptyIsObservedAndSourceReleased() throws {
        let fixture = try OwnedFixture()
        let audit = OwnershipAudit()
        let io = DarwinDirectoryIO(seams: IOSeams(ownership: audit.record))
        var releaseCount = 0
        let lease = try fixture.lease(io: io, release: { releaseCount += 1 })
        let held = lease.descriptor
        let controller = ObservationController(lease: lease, io: io)
        let result = try controller.observe(label: "Empty")
        XCTAssertEqual(result.state, .observed)
        XCTAssertEqual(try snapshotRows(result).count, 1)
        XCTAssertEqual(releaseCount, 1)
        XCTAssertEqual(fcntl(held, F_GETFD), -1)
        XCTAssertEqual(controller.state, .spent)
        audit.verify()
        try fixture.assertSentinel()
    }

    func testNestedFilesLogicalSizesAndExactPathOrder() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("Projects")
        try fixture.file("notes.txt", bytes: 3)
        try fixture.file("Projects/README.md", bytes: 5)
        try fixture.file("Projects/Clip.mov", bytes: 7)
        let result = try fixtureResult(fixture)
        XCTAssertEqual(result.state, .observed)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.compactMap { $0["path"] as? String }, [".", "Projects", "Projects/Clip.mov", "Projects/README.md", "notes.txt"])
        XCTAssertEqual(rows.compactMap { $0["logical_bytes"] as? String }, ["7", "5", "3"])
        try fixture.assertSentinel()
    }

    func testHardlinksKeepBothPathsAndSymlinkNeverOpensTarget() throws {
        let fixture = try OwnedFixture()
        try fixture.file("regular.txt", bytes: 3)
        try fixture.hardlink("regular.txt", "alias")
        try fixture.symlink("outside")
        var childOpens: [Data] = []
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .directoryOpen, let name { childOpens.append(name) }
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.filter { $0["kind"] as? String == "file" }.compactMap { $0["logical_bytes"] as? String }, ["3", "3"])
        XCTAssertFalse(childOpens.contains(Data("outside".utf8)))
        XCTAssertFalse(childOpens.contains(Data("regular.txt".utf8)))
        XCTAssertFalse(childOpens.contains(Data("alias".utf8)))
        XCTAssertEqual(rows.last?["status"] as? String, "observed")
        try fixture.assertSentinel()
    }

    func testFIFOAndSocketAreUnsupportedWithoutSpecialOpen() throws {
        let fixture = try OwnedFixture()
        try fixture.fifo("pipe")
        let socketFD = socket(AF_UNIX, SOCK_STREAM, 0)
        XCTAssertGreaterThanOrEqual(socketFD, 0)
        defer { _ = Darwin.close(socketFD) }
        var address = sockaddr_un()
        address.sun_family = sa_family_t(AF_UNIX)
        let pathname = Array(fixture.owned("socket").utf8CString)
        let capacity = MemoryLayout.size(ofValue: address.sun_path)
        XCTAssertLessThan(pathname.count, capacity)
        withUnsafeMutableBytes(of: &address.sun_path) { destination in
            pathname.withUnsafeBytes { source in destination.copyBytes(from: source) }
        }
        address.sun_len = UInt8(MemoryLayout<sockaddr_un>.size)
        let bound = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { Darwin.bind(socketFD, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) }
        }
        XCTAssertEqual(bound, 0)
        var opens: [Data] = []
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .directoryOpen, let name { opens.append(name) }
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let special = try snapshotRows(result).filter { $0["kind"] as? String == "special" }
        XCTAssertEqual(special.count, 2)
        XCTAssertTrue(special.allSatisfy { $0["status"] as? String == "unsupported" })
        XCTAssertFalse(opens.contains(Data("pipe".utf8)))
        XCTAssertFalse(opens.contains(Data("socket".utf8)))
        try fixture.assertSentinel()
    }

    func testKnownMarkersExcludedIncludingInjectedDatalessFlag() throws {
        let fixture = try OwnedFixture()
        try fixture.file("report.icloud")
        try fixture.file("dataless")
        try fixture.file("okay.txt", bytes: 1)
        let io = DarwinDirectoryIO(seams: IOSeams(metadata: { op, _, name, metadata in
            if op == .childStat && name == Data("dataless".utf8) {
                return try replacement(metadata, flags: UInt32(SF_DATALESS))
            }
            return metadata
        }))
        let result = try fixtureResult(fixture, io: io)
        let exclusions = try XCTUnwrap(snapshotGaps(result)["exclusions"] as? [[String: String]])
        XCTAssertEqual(exclusions, [["reason": "known_placeholder_marker", "count": "2"]])
        XCTAssertEqual(result.state, .partial)
        try fixture.assertSentinel()
    }

    func testRootReplacementWithholdsAllRowsBeforeDescendantRead() throws {
        let fixture = try OwnedFixture()
        try fixture.file("secret.txt")
        var readEntries = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, _ in if op == .readEntry { readEntries += 1 } }))
        let lease = try fixture.lease(io: io)
        XCTAssertEqual(Darwin.rename(fixture.source, fixture.base + "/retired"), 0)
        try FileManager.default.createDirectory(atPath: fixture.source, withIntermediateDirectories: false)
        let result = try ObservationController(lease: lease, io: io).observe(label: "Replacement")
        XCTAssertEqual(result.state, .rootChanged)
        XCTAssertNil(result.snapshot)
        XCTAssertEqual(readEntries, 0)
        try fixture.assertSentinel()
    }

    func testRootAndAncestorSymlinkRejectedByTestOnlyConstructor() throws {
        let fixture = try OwnedFixture()
        XCTAssertEqual(Darwin.rename(fixture.source, fixture.base + "/old"), 0)
        XCTAssertEqual(Darwin.symlink(fixture.base + "/old", fixture.source), 0)
        XCTAssertThrowsError(try fixture.lease(io: DarwinDirectoryIO()))
        // Replace an owned nested ancestor, keeping both destinations inside base.
        let ancestorFixture = try OwnedFixture(sourceRelative: "ancestor/selected")
        let io = DarwinDirectoryIO()
        let lease = try ancestorFixture.lease(io: io)
        let ancestor = ancestorFixture.base + "/ancestor"
        let moved = ancestorFixture.base + "/retired-ancestor"
        XCTAssertEqual(Darwin.rename(ancestor, moved), 0)
        XCTAssertEqual(Darwin.symlink(moved, ancestor), 0)
        let result = try ObservationController(lease: lease, io: io).observe(label: "Ancestor")
        XCTAssertEqual(result.state, .failed)
        XCTAssertNil(result.snapshot)
        try ancestorFixture.assertSentinel()
    }

    func testChildReplacedBySymlinkBetweenStatAndOpenNeverDescends() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/inside")
        var changed = false
        var statNames: [Data] = []
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .childStat, let name { statNames.append(name) }
            if op == .directoryOpen && name == Data("child".utf8) && !changed {
                changed = true
                XCTAssertEqual(Darwin.rename(fixture.owned("child"), fixture.base + "/moved-child"), 0)
                XCTAssertEqual(Darwin.symlink(fixture.base, fixture.owned("child")), 0)
            }
        }))
        let result = try fixtureResult(fixture, io: io)
        // A selected-root fingerprint changed, so even a partial child gap cannot be admitted.
        XCTAssertEqual(result.state, .rootChanged)
        XCTAssertNil(result.snapshot)
        XCTAssertFalse(statNames.contains(Data("inside".utf8)))
        XCTAssertFalse(statNames.contains(Data("sentinel.txt".utf8)))
        try fixture.assertSentinel()
    }

    func testAlreadyOpenedChildMovedIsDetectedWithoutConfinementClaim() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/file")
        var moved = false
        let result = try ObservationController(lease: fixture.lease(io: DarwinDirectoryIO()), io: DarwinDirectoryIO()).observe(label: "Moved", progress: { count in
            if count >= 3 && !moved {
                moved = true
                XCTAssertEqual(Darwin.rename(fixture.owned("child"), fixture.base + "/moved-child"), 0)
            }
        })
        XCTAssertTrue(moved)
        XCTAssertEqual(result.state, .rootChanged)
        XCTAssertNil(result.snapshot)
        try fixture.assertSentinel()
    }

    func testScopeReviewChangesEstablishNewBaseline() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        let lease = try fixture.lease(io: io)
        try fixture.file("added-before-observe", bytes: 2)
        let result = try ObservationController(lease: lease, io: io).observe(label: "New baseline")
        XCTAssertEqual(result.state, .observed)
        XCTAssertEqual(try snapshotRows(result).count, 2)
    }

    func testActualInvalidNamesRejectWholeProjection() throws {
        for bytes in [Data([0x66, 0x80]), Data("back\\slash".utf8), Data([0x63, 0x0A]) ] {
            let fixture = try OwnedFixture()
            let root = Darwin.open(fixture.source, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            XCTAssertGreaterThanOrEqual(root, 0)
            let (fd, code) = try withRawName(bytes) {
                let descriptor = openat(root, $0, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0o600)
                return (descriptor, errno)
            }
            if fd < 0 && bytes.contains(0x80) {
                XCTAssertTrue(code == EILSEQ || code == EINVAL, "Unexpected owned-name creation error")
                print("OWNED_FIXTURE_NOTE: filesystem rejected invalid UTF-8 name, errno \(code); synthetic rejection is unconditional")
                _ = Darwin.close(root)
                continue
            }
            XCTAssertGreaterThanOrEqual(fd, 0)
            _ = Darwin.close(fd)
            _ = Darwin.close(root)
            let result = try fixtureResult(fixture)
            XCTAssertEqual(result.state, .failed)
            XCTAssertNil(result.snapshot)
            try fixture.assertSentinel()
        }
    }

    func testNonBMPAndDecomposedSpellingRemainExactWhenStored() throws {
        let fixture = try OwnedFixture()
        let name = "e\u{301}-🧪.txt"
        try fixture.file(name, bytes: 1)
        let result = try fixtureResult(fixture)
        let paths = try snapshotRows(result).compactMap { ($0["path"] as? String).map { Data($0.utf8) } }
        // APFS may choose an on-disk spelling. Assert the native reader agrees with raw readdir,
        // rather than pretending a case-sensitive/NFC-distinct fixture exists on every runner.
        let io = DarwinDirectoryIO()
        let lease = try fixture.lease(io: io)
        defer { lease.release() }
        guard case .names(let names) = try io.names(lease.descriptor, interrupted: { false }) else { return XCTFail("Expected names") }
        XCTAssertEqual(paths, [Data(".".utf8)] + names)
        XCTAssertEqual(names.count, 1)
    }
    func testOwnedChildMutationInvalidatesDescendantsAndHardlinkAliases() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/a", bytes: 3)
        try fixture.hardlink("child/a", "z")
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io)
        var changed = false
        let result = try controller.observe(label: "Child changed", progress: { count in
            if count == 3 && !changed {
                changed = true
                try fixture.file("child/late", bytes: 1)
            }
        })
        XCTAssertTrue(changed)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.dropFirst().compactMap { $0["status"] as? String }, ["stale", "stale", "stale"])
        XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]],
                       [["reason": "changed_during_traversal", "count": "1"]])
        try fixture.assertSentinel()
    }

}
