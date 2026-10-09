import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class SyscallResultTests: XCTestCase {
    func testInjectedFcntlAndFdopendirReturnFailuresHaveOneCloseOwner() throws {
        for operation in [IOOperation.descriptorFlags, .closeOnExec, .streamOpen] {
            let fixture = try OwnedFixture()
            let audit = OwnershipAudit()
            var armed = false
            let io = DarwinDirectoryIO(seams: IOSeams(ownership: audit.record, failureResult: { op, _ in
                armed && op == operation ? EIO : nil
            }))
            let lease = try fixture.lease(io: io)
            armed = true
            let result = try ObservationController(lease: lease, io: io).observe(label: "Injected syscall result")
            XCTAssertEqual(result.state, .failed)
            XCTAssertNil(result.snapshot)
            audit.verify()
        }
    }

    func testInjectedReaddirNullWithErrnoDiscardsCollectedRootNames() throws {
        let fixture = try OwnedFixture()
        try fixture.file("a")
        try fixture.file("b")
        let audit = OwnershipAudit()
        var gathered = 0
        var childStats = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, _ in
            if op == .childStat { childStats += 1 }
        }, ownership: audit.record, failureResult: { op, _ in
            op == .readEntry && gathered == 1 ? EIO : nil
        }, didGatherName: { _ in gathered += 1 }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(gathered, 1)
        XCTAssertEqual(childStats, 0)
        XCTAssertEqual(result.state, .failed)
        XCTAssertNil(result.snapshot)
        audit.verify()
    }

    func testInjectedReaddirNullWithErrnoDiscardsCollectedChildNames() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/a")
        try fixture.file("child/b")
        let audit = OwnershipAudit()
        var streamCount = 0
        var childNames = 0
        let io = DarwinDirectoryIO(seams: IOSeams(ownership: { event in
            audit.record(event)
            if case .streamOwns = event { streamCount += 1 }
        }, failureResult: { op, _ in
            op == .readEntry && streamCount == 2 && childNames == 1 ? ENOENT : nil
        }, didGatherName: { _ in if streamCount == 2 { childNames += 1 } }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.count, 2)
        XCTAssertEqual(rows.last?["status"] as? String, "disappeared")
        XCTAssertEqual(try snapshotGaps(result)["error_count"] as? String, "1")
        audit.verify()
    }

    func testInjectedNullZeroIsEOFAndActualEmptyEOFAgrees() throws {
        for injected in [false, true] {
            let fixture = try OwnedFixture()
            let audit = OwnershipAudit()
            let io = DarwinDirectoryIO(seams: IOSeams(ownership: audit.record, failureResult: { op, _ in
                injected && op == .readEntry ? 0 : nil
            }))
            let result = try fixtureResult(fixture, io: io)
            XCTAssertEqual(result.state, .observed)
            XCTAssertEqual(try snapshotRows(result).count, 1)
            XCTAssertEqual(try snapshotGaps(result)["error_count"] as? String, "0")
            audit.verify()
        }
    }

    func testInjectedAliasMetadataConflictMarksBothObservedPathsStale() throws {
        let fixture = try OwnedFixture()
        try fixture.file("a", bytes: 3)
        try fixture.hardlink("a", "b")
        let io = DarwinDirectoryIO(seams: IOSeams(metadata: { op, _, name, metadata in
            if op == .childStat && name == Data("b".utf8) { return try replacement(metadata, size: 4) }
            return metadata
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result).filter { $0["kind"] as? String == "file" }
        XCTAssertEqual(rows.compactMap { $0["status"] as? String }, ["stale", "stale"])
        XCTAssertEqual(rows.compactMap { $0["logical_bytes"] as? String }, ["3", "4"])
    }

    func testInjectedChangedAncestorPropagatesToOutsideHardlinkAlias() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/a", bytes: 3)
        try fixture.hardlink("child/a", "z")
        var openingChild = false
        var childFD: Int32?
        var childStats = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .directoryOpen && name == Data("child".utf8) { openingChild = true }
        }, metadata: { op, fd, _, metadata in
            if op == .descriptorStat && fd == childFD {
                childStats += 1
                if childStats == 2 { return try replacement(metadata, size: metadata.fingerprint.size + 1) }
            }
            return metadata
        }, ownership: { event in
            if openingChild, case .acquired(let fd) = event { childFD = fd; openingChild = false }
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.dropFirst().compactMap { $0["status"] as? String }, ["stale", "stale", "stale"])
        XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]], [["reason": "changed_during_traversal", "count": "1"]])
    }
}
