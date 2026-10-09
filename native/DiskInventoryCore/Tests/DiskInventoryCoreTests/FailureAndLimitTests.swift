import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class FailureAndLimitTests: XCTestCase {
    func testDirectory500And501HaveNoArbitrarySubset() throws {
        for count in [500, 501] {
            let fixture = try OwnedFixture()
            for index in 0..<count { try fixture.file(String(format: "f%03d", index)) }
            let result = try fixtureResult(fixture, seams: ObservationSeams(clock: { 0 }))
            XCTAssertEqual(result.state, count == 500 ? .observed : .partial)
            XCTAssertEqual(try snapshotRows(result).count, count == 500 ? 501 : 1)
            if count == 501 {
                XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]],
                               [["reason": "directory_entry_limit", "count": "1"]])
            }
            try fixture.assertSentinel()
        }
    }

    func testDepthEightRecordedButNotEnumerated() throws {
        let fixture = try OwnedFixture()
        let deep = (0...8).map { "d\($0)" }.joined(separator: "/")
        try fixture.directory(deep)
        try fixture.file(deep + "/leaf.txt", bytes: 1)
        let result = try fixtureResult(fixture)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.count, 9)
        XCTAssertEqual(rows.last?["path"] as? String, (0...7).map { "d\($0)" }.joined(separator: "/"))
        XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]], [["reason": "depth_limit", "count": "1"]])
    }

    func testEntryBoundIncludesRootAtExactAndOverflowBoundary() throws {
        for overflow in [false, true] {
            let fixture = try OwnedFixture()
            for directory in 0..<4 {
                let name = "d\(directory)"
                try fixture.directory(name)
                let count = directory == 3 && !overflow ? 498 : 499
                for index in 0..<count { try fixture.file(name + "/" + String(format: "f%03d", index)) }
            }
            let result = try fixtureResult(fixture, seams: ObservationSeams(clock: { 0 }))
            XCTAssertEqual(result.state, overflow ? .partial : .observed)
            XCTAssertEqual(try snapshotRows(result).count, 2_000)
            let stop = try snapshotGaps(result)["stop_reason"]
            if overflow { XCTAssertEqual(stop as? String, "entry_limit") }
            else { XCTAssertTrue(stop is NSNull) }
        }
    }

    func testInjectedRootIteratorFailuresDiscardAllNamesAndCloseOnce() throws {
        for operation in [IOOperation.duplicate, .closeOnExec, .streamOpen, .readEntry] {
            let fixture = try OwnedFixture()
            try fixture.file("a")
            try fixture.file("b")
            let audit = OwnershipAudit()
            var armed = false
            var hits = 0
            let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, _ in
                if armed && op == operation {
                    hits += 1
                    // Root scanner duplicate succeeds, then iteration duplicate fails.
                    let target = operation == .duplicate || operation == .closeOnExec ? 2 : operation == .readEntry ? 3 : 1
                    if hits == target { throw CoreFailure.filesystem(EIO) }
                }
            }, ownership: audit.record))
            let lease = try fixture.lease(io: io)
            armed = true
            let result = try ObservationController(lease: lease, io: io).observe(label: "Injected root failure")
            XCTAssertEqual(result.state, .failed)
            XCTAssertNil(result.snapshot)
            audit.verify()
            try fixture.assertSentinel()
        }
    }

    func testInjectedChildIteratorErrorIsOneErrorWithNoNameSubset() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/a")
        try fixture.file("child/b")
        var childFD: Int32?
        var reads = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, fd, name in
            if op == .directoryOpen && name == Data("child".utf8) { childFD = nil }
            if op == .readEntry && childFD != nil {
                reads += 1
                if reads == 3 { throw CoreFailure.filesystem(EIO) }
            }
        }, ownership: { event in
            if case .streamOwns(let fd) = event {
                if reads == 0 { reads = -1 } // First stream is the root.
                else { childFD = fd; reads = 0 }
            }
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        let rows = try snapshotRows(result)
        XCTAssertEqual(rows.count, 2)
        XCTAssertEqual(rows.last?["status"] as? String, "unreadable")
        XCTAssertEqual(try snapshotGaps(result)["error_count"] as? String, "1")
    }

    func testInjectedChildStatErrorsRemainExplicit() throws {
        for code in [ENOENT, EACCES] {
            let fixture = try OwnedFixture()
            try fixture.file("gone")
            let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
                if op == .childStat && name == Data("gone".utf8) { throw CoreFailure.filesystem(code) }
            }))
            let result = try fixtureResult(fixture, io: io)
            let row = try XCTUnwrap(snapshotRows(result).last)
            XCTAssertEqual(result.state, .partial)
            XCTAssertEqual(row["kind"] as? String, "unknown")
            XCTAssertEqual(row["status"] as? String, code == ENOENT ? "disappeared" : "unreadable")
            XCTAssertEqual(try snapshotGaps(result)["error_count"] as? String, "1")
        }
    }

    func testInjectedOpenedChildStatFailureDoesNotCertifyDescendants() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/never")
        var childOpen = false
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .directoryOpen && name == Data("child".utf8) { childOpen = true }
            if op == .descriptorStat && childOpen { childOpen = false; throw CoreFailure.filesystem(EACCES) }
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        XCTAssertEqual(try snapshotRows(result).count, 2)
        XCTAssertEqual(try snapshotGaps(result)["error_count"] as? String, "1")
    }

    func testInjectedFilesystemBoundaryAtStatAndOpenedDescriptor() throws {
        for atOpen in [false, true] {
            let fixture = try OwnedFixture()
            try fixture.directory("child")
            try fixture.file("child/never")
            var childWasOpened = false
            let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
                if op == .directoryOpen && name == Data("child".utf8) { childWasOpened = true }
            }, metadata: { op, _, name, metadata in
                if (!atOpen && op == .childStat && name == Data("child".utf8)) || (atOpen && childWasOpened && op == .descriptorStat) {
                    childWasOpened = false
                    return try replacement(metadata, device: metadata.fingerprint.device + 1)
                }
                return metadata
            }))
            let result = try fixtureResult(fixture, io: io)
            XCTAssertEqual(result.state, .partial)
            XCTAssertEqual(try snapshotRows(result).count, 2)
            XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]], [["reason": "filesystem_boundary", "count": "1"]])
        }
    }

    func testInjectedChangedChildFingerprintBeforeDescent() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        try fixture.file("child/never")
        let io = DarwinDirectoryIO(seams: IOSeams(metadata: { op, _, name, metadata in
            if op == .childStat && name == Data("child".utf8) { return try replacement(metadata, size: metadata.fingerprint.size + 1) }
            return metadata
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .partial)
        XCTAssertEqual(try snapshotRows(result).last?["status"] as? String, "stale")
        XCTAssertEqual(try snapshotRows(result).count, 2)
        XCTAssertEqual(try snapshotGaps(result)["exclusions"] as? [[String: String]], [["reason": "changed_before_traversal", "count": "1"]])
    }

    func testInjectedNegativeLogicalSizeFailsProjection() throws {
        let fixture = try OwnedFixture()
        try fixture.file("file")
        let io = DarwinDirectoryIO(seams: IOSeams(metadata: { op, _, _, metadata in
            op == .childStat ? try replacement(metadata, size: -1) : metadata
        }))
        let result = try fixtureResult(fixture, io: io)
        XCTAssertEqual(result.state, .failed)
        XCTAssertNil(result.snapshot)
    }

    func testFinalRootGuardClockCrossingLatchesPartial() throws {
        let fixture = try OwnedFixture()
        var now: TimeInterval = 0
        var rootOpens = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, _, name in
            if op == .directoryOpen && name == Data("selected".utf8) {
                rootOpens += 1
                if rootOpens == 3 { now = 5 }
            }
        }))
        let result = try fixtureResult(fixture, io: io, seams: ObservationSeams(clock: { now }))
        XCTAssertEqual(result.state, .partial)
        XCTAssertEqual(try snapshotGaps(result)["stop_reason"] as? String, "time_limit")
    }

    func testElapsedTimeAndCancellationBeforeFirstReadHaveNoArtifact() throws {
        let fixture = try OwnedFixture()
        var calls = 0
        let result = try fixtureResult(fixture, seams: ObservationSeams(clock: {
            calls += 1
            return calls == 1 ? 0 : 5
        }))
        XCTAssertNil(result.snapshot)
        let io = DarwinDirectoryIO()
        let cancelled = try ObservationController(lease: fixture.lease(io: io), io: io).observe(label: "Cancelled", cancel: { true })
        XCTAssertEqual(cancelled.state, .cancelled)
        XCTAssertNil(cancelled.snapshot)
    }

    func testAllDuplicatedAndOpenedDescriptorsAreCloseOnExec() throws {
        let fixture = try OwnedFixture()
        try fixture.directory("child")
        var inspected = 0
        let io = DarwinDirectoryIO(seams: IOSeams(before: { op, fd, _ in
            if op == .streamOpen || op == .descriptorStat {
                XCTAssertNotEqual(fcntl(fd, F_GETFD) & FD_CLOEXEC, 0)
                inspected += 1
            }
        }))
        XCTAssertEqual(try fixtureResult(fixture, io: io).state, .observed)
        XCTAssertGreaterThan(inspected, 0)
    }
}
