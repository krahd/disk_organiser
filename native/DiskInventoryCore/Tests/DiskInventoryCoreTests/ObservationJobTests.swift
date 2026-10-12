import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

// Waits are confined to the worker, never the main actor. Every test releases
// its gate in defer, and an unreleased test hold expires rather than hanging CI.
final class OwnedJobGate: @unchecked Sendable {
    let entered = LockedBox(false)
    let timedOut = LockedBox(false)
    private let resume = DispatchSemaphore(value: 0)
    func hold() {
        guard entered.update({ value in
            guard !value else { return false }; value = true; return true
        }) else { return }
        if resume.wait(timeout: .now() + 5) != .success { timedOut.update { $0 = true } }
    }
    func release() { resume.signal() }
}

@MainActor
final class ObservationJobTests: XCTestCase {
    private func start(_ job: ObservationJob) -> Task<ObservationJob.Result, any Error> {
        Task { try await job.run() }
    }
    private func entered(_ gate: OwnedJobGate) async throws {
        for _ in 0..<150 where !gate.entered.read() { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertTrue(gate.entered.read())
        guard gate.entered.read() else { throw ObservationJob.Failure.invalidProgress }
    }
    func testOwnedSuccessRetiresBeforeDeliveringAndRunsAwayFromMainActor() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file", bytes: 7)
        let released = LockedBox(0); let wrongThread = LockedBox(false)
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }), io: io)
        let job = ObservationJob(controller: controller, label: "Owned worker",
            seams: .init(afterProgress: { _ in if Thread.isMainThread { wrongThread.update { $0 = true } } }))
        let result = try await job.run()
        XCTAssertEqual(result.state, .observed); XCTAssertNotNil(result.snapshot)
        XCTAssertEqual(released.read(), 1); XCTAssertFalse(wrongThread.read()); XCTAssertNil(job.takeProgress())
        try fixture.assertSentinel()
    }
    func testCancellationBeforeStartRetiresOnWorkerWithoutSnapshot() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file")
        let released = LockedBox(0); let io = DarwinDirectoryIO()
        let job = ObservationJob(controller: ObservationController(lease: try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }), io: io), label: "Pre-cancel")
        job.cancel(); job.cancel()
        let result = try await job.run()
        XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot); XCTAssertEqual(released.read(), 1)
        XCTAssertNil(job.takeProgress()); try fixture.assertSentinel()
    }
    func testActiveCancellationKeepsDescriptorUntilWorkerRetirement() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file")
        let io = DarwinDirectoryIO(); let released = LockedBox(0)
        let lease = try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }); let held = lease.descriptor
        let gate = OwnedJobGate(); defer { gate.release() }
        let job = ObservationJob(controller: ObservationController(lease: lease, io: io), label: "Active cancellation",
            seams: .init(afterProgress: { count in if count == 2 { gate.hold() } }))
        let running = Task { try await job.run() }
        try await entered(gate)
        XCTAssertEqual(job.takeProgress(), 2)
        job.cancel(); job.cancel()
        XCTAssertEqual(released.read(), 0); XCTAssertGreaterThanOrEqual(fcntl(held, F_GETFD), 0)
        XCTAssertNil(job.takeProgress()); gate.release()
        let result = try await running.value
        XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot); XCTAssertEqual(released.read(), 1)
        XCTAssertEqual(fcntl(held, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
        XCTAssertFalse(gate.timedOut.read()); try fixture.assertSentinel()
    }
    func testCancelledRejectedSecondRunCannotCancelAdmittedWorker() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file")
        let io = DarwinDirectoryIO(); let released = LockedBox(0); let gate = OwnedJobGate(); defer { gate.release() }
        let lease = try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }); let held = lease.descriptor
        let job = ObservationJob(controller: ObservationController(lease: lease, io: io), label: "One admitted caller",
            seams: .init(afterProgress: { count in if count == 2 { gate.hold() } }))
        let first = start(job); try await entered(gate)
        let second = Task { () throws -> ObservationJob.Result in
            withUnsafeCurrentTask { $0?.cancel() }
            return try await job.run()
        }
        do { _ = try await second.value; XCTFail("The second caller must be refused") }
        catch ObservationJob.Failure.alreadyStarted {} catch { XCTFail("Wrong refusal: \(error)") }
        XCTAssertEqual(released.read(), 0); XCTAssertGreaterThanOrEqual(fcntl(held, F_GETFD), 0)
        XCTAssertEqual(job.takeProgress(), 2)
        gate.release(); let result = try await first.value
        XCTAssertEqual(result.state, .observed); XCTAssertNotNil(result.snapshot); XCTAssertEqual(released.read(), 1)
        XCTAssertEqual(fcntl(held, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
        XCTAssertFalse(gate.timedOut.read()); try fixture.assertSentinel()
    }
    func testCancelBetweenCoreAdmissionAndJobPublicationDiscardsBytes() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file")
        let io = DarwinDirectoryIO(); let released = LockedBox(0); let gate = OwnedJobGate(); defer { gate.release() }
        let job = ObservationJob(controller: ObservationController(lease: try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }), io: io), label: "Late cancellation",
            seams: .init(beforePublication: { gate.hold() }))
        let running = Task { try await job.run() }; try await entered(gate)
        XCTAssertEqual(released.read(), 1)
        job.cancel(); gate.release()
        let result = try await running.value
        XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot); XCTAssertFalse(gate.timedOut.read())
    }
    func testCancelAfterPublishedSuccessDoesNotRewriteResultAndRerunRefuses() async throws {
        let fixture = try OwnedFixture(); let io = DarwinDirectoryIO()
        let job = ObservationJob(controller: ObservationController(lease: try fixture.lease(io: io), io: io), label: "Completed")
        let result = try await job.run(); let bytes = try XCTUnwrap(result.snapshot)
        job.cancel(); job.cancel()
        XCTAssertEqual(result.state, .observed); XCTAssertEqual(result.snapshot, bytes)
        do { _ = try await job.run(); XCTFail("A job is one-use") }
        catch ObservationJob.Failure.alreadyStarted {} catch { XCTFail("Wrong refusal: \(error)") }
    }
    func testCancellationDuringEnumerationRetiresEveryOwnedDescriptor() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file")
        let audit = LockedBox(OwnershipAudit()); let released = LockedBox(0)
        let gate = OwnedJobGate(); defer { gate.release() }
        let io = DarwinDirectoryIO(seams: IOSeams(ownership: { @Sendable event in audit.update { $0.record(event) } },
            didGatherName: { @Sendable _ in gate.hold() }))
        let lease = try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }); let held = lease.descriptor
        let job = ObservationJob(controller: ObservationController(lease: lease, io: io), label: "Enumeration cancellation")
        let running = start(job); try await entered(gate)
        XCTAssertGreaterThanOrEqual(fcntl(held, F_GETFD), 0); XCTAssertEqual(released.read(), 0)
        job.cancel(); gate.release(); let result = try await running.value
        XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot); XCTAssertEqual(released.read(), 1)
        XCTAssertEqual(fcntl(held, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
        audit.update { $0.verify() }; XCTAssertFalse(gate.timedOut.read()); try fixture.assertSentinel()
    }
    func testJobCancellationAtProjectionAndAdmissionDiscardsAllBytes() async throws {
        for boundary in [ControllerBoundary.beforeProjection, .afterProjection, .beforeAdmission] {
            let fixture = try OwnedFixture(); try fixture.file("file")
            let audit = LockedBox(OwnershipAudit()); let released = LockedBox(0)
            let gate = OwnedJobGate(); defer { gate.release() }
            let io = DarwinDirectoryIO(seams: IOSeams(ownership: { @Sendable event in audit.update { $0.record(event) } }))
            let lease = try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }); let held = lease.descriptor
            let controller = ObservationController(lease: lease, io: io,
                seams: ObservationSeams(boundary: { @Sendable value in if value == boundary { gate.hold() } }))
            let job = ObservationJob(controller: controller, label: "Late core boundary")
            let running = start(job); try await entered(gate)
            job.cancel(); gate.release(); let result = try await running.value
            XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot); XCTAssertEqual(released.read(), 1)
            XCTAssertEqual(fcntl(held, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
            audit.update { $0.verify() }; XCTAssertFalse(gate.timedOut.read()); try fixture.assertSentinel()
        }
    }
    func testSuccessAndFailureReleaseCompletedJobsAndAllOwners() async throws {
        for fail in [false, true] {
            let fixture = try OwnedFixture(); try fixture.file("file")
            let audit = LockedBox(OwnershipAudit()); let released = LockedBox(0)
            let io = DarwinDirectoryIO(seams: IOSeams(ownership: { @Sendable event in audit.update { $0.record(event) } }))
            let lease = try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }); let held = lease.descriptor
            var job: ObservationJob? = ObservationJob(controller: ObservationController(lease: lease, io: io,
                seams: ObservationSeams(boundary: { @Sendable value in if fail && value == .beforeProjection { throw CoreFailure.invalidProjection } })), label: "Retirement")
            weak var retired = job
            let running = start(try XCTUnwrap(job)); let result = try await running.value
            XCTAssertEqual(result.state, fail ? .failed : .observed)
            XCTAssertEqual(result.snapshot == nil, fail); XCTAssertEqual(released.read(), 1)
            XCTAssertEqual(fcntl(held, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
            audit.update { $0.verify() }; job = nil
            for _ in 0..<100 where retired != nil { try await Task.sleep(for: .milliseconds(10)) }
            XCTAssertNil(retired); try fixture.assertSentinel()
        }
    }
    func testProgressCoalescesWithExactBoundsAndNoTerminalDelivery() async throws {
        let job = ObservationJob(controller: ObservationController(lease: nil, io: DarwinDirectoryIO()), label: "Mailbox")
        for count in 0...2_000 { try job.recordProgress(count) }
        XCTAssertEqual(job.takeProgress(), 2_000); XCTAssertNil(job.takeProgress())
        XCTAssertThrowsError(try job.recordProgress(-1)); XCTAssertThrowsError(try job.recordProgress(2_001))
        XCTAssertThrowsError(try job.recordProgress(1))
        let result = try await job.run(); XCTAssertEqual(result.state, .unsupported); XCTAssertNil(result.snapshot)
        XCTAssertNil(job.takeProgress()); XCTAssertThrowsError(try job.recordProgress(2_000))
    }
    func testTaskCancellationUsesSameRetirementAndReleasesCompletedJob() async throws {
        let fixture = try OwnedFixture(); let io = DarwinDirectoryIO(); let gate = OwnedJobGate(); defer { gate.release() }
        var job: ObservationJob? = ObservationJob(controller: ObservationController(lease: try fixture.lease(io: io), io: io), label: "Task cancel",
            seams: .init(afterProgress: { count in if count == 1 { gate.hold() } }))
        weak var retired = job
        let running = start(try XCTUnwrap(job))
        try await entered(gate); running.cancel(); gate.release()
        let result = try await running.value; XCTAssertEqual(result.state, .cancelled); XCTAssertNil(result.snapshot)
        job = nil
        for _ in 0..<100 where retired != nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNil(retired); XCTAssertFalse(gate.timedOut.read())
    }
    func testPartialSnapshotRetainsSymlinkExclusionWithoutReadingTarget() async throws {
        let fixture = try OwnedFixture(); try fixture.file("file", bytes: 7); try fixture.symlink("outside-link")
        let io = DarwinDirectoryIO()
        let job = ObservationJob(controller: ObservationController(lease: try fixture.lease(io: io), io: io), label: "Partial owned source")
        let result = try await job.run(); XCTAssertEqual(result.state, .partial)
        let bytes = try XCTUnwrap(result.snapshot)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        let gaps = try XCTUnwrap(object["gaps"] as? [String: Any])
        let exclusions = try XCTUnwrap(gaps["exclusions"] as? [[String: Any]])
        XCTAssertTrue(exclusions.contains { $0["reason"] as? String == "symlink_not_followed" && $0["count"] as? String == "1" })
        try fixture.assertSentinel()
    }
    func testWorkerFailureRetiresWithoutPublishingSnapshot() async throws {
        let fixture = try OwnedFixture(); let io = DarwinDirectoryIO(); let released = LockedBox(0)
        let controller = ObservationController(lease: try fixture.lease(io: io, release: { @Sendable in released.update { $0 += 1 } }), io: io,
            seams: ObservationSeams(boundary: { @Sendable value in if value == .beforeProjection { throw CoreFailure.invalidProjection } }))
        let result = try await ObservationJob(controller: controller, label: "Injected projection failure").run()
        XCTAssertEqual(result.state, .failed); XCTAssertNil(result.snapshot); XCTAssertEqual(released.read(), 1)
        try fixture.assertSentinel()
    }

}
