import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class LifecycleTests: XCTestCase {
    func testUnavailableAndUnknownAdmissionDoNotReadDescendants() throws {
        let io = DarwinDirectoryIO(seams: IOSeams(before: { _, _, _ in XCTFail("Unavailable grant must do no IO") }))
        XCTAssertEqual(try ObservationController(lease: nil, io: io).observe(label: "Unavailable").state, .unsupported)
        for classification in [SourceAdmission.unknown, .unsupported] {
            let fixture = try OwnedFixture()
            var armed = false
            var reads = 0
            let io = DarwinDirectoryIO(seams: IOSeams(before: { _, _, _ in if armed { reads += 1 } }))
            let lease = try fixture.lease(io: io, admission: classification)
            armed = true
            let result = try ObservationController(lease: lease, io: io).observe(label: "Not admitted")
            XCTAssertEqual(result.state, .unsupported)
            XCTAssertNil(result.snapshot)
            XCTAssertEqual(reads, 0)
        }
    }

    func testRepeatedObserveAndCallbackReentryAreRejectedWithoutDeadlock() throws {
        let fixture = try OwnedFixture()
        try fixture.file("file")
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io)
        var callbacks = 0
        let result = try controller.observe(label: "Once", progress: { _ in
            callbacks += 1
            XCTAssertThrowsError(try controller.observe(label: "Reentry"))
        })
        XCTAssertGreaterThan(callbacks, 0)
        XCTAssertEqual(result.state, .observed)
        XCTAssertThrowsError(try controller.observe(label: "Again"))
        XCTAssertNotNil(controller.takeSnapshot(result))
        XCTAssertNil(controller.takeSnapshot(result))
    }

    func testOneLeaseCannotBeConsumedByTwoControllers() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        var releases = 0
        let lease = try fixture.lease(io: io, release: { releases += 1 })
        let winner = ObservationController(lease: lease, io: io)
        var rejected: ObservationController? = ObservationController(lease: lease, io: io)
        let result = try XCTUnwrap(rejected).observe(label: "Rejected claimant")
        XCTAssertEqual(result.state, .failed)
        XCTAssertNil(result.snapshot)
        rejected?.cancel()
        rejected = nil
        lease.release() // An unowned release cannot retire a claimed lease.
        XCTAssertEqual(releases, 0)
        XCTAssertGreaterThanOrEqual(fcntl(lease.descriptor, F_GETFD), 0)
        XCTAssertEqual(try winner.observe(label: "Owner").state, .observed)
        XCTAssertEqual(releases, 1)
    }

    func testConcurrentObserveAndRevokeDoNotCloseBorrowedDescriptor() throws {
        let fixture = try OwnedFixture()
        try fixture.file("file")
        let io = DarwinDirectoryIO()
        let releases = LockedBox(0)
        let lease = try fixture.lease(io: io, release: { releases.update { $0 += 1 } })
        let held = lease.descriptor
        let controller = ObservationController(lease: lease, io: io)
        let entered = DispatchSemaphore(value: 0)
        let resume = DispatchSemaphore(value: 0)
        let done = DispatchSemaphore(value: 0)
        let result = LockedBox<ObservationResult?>(nil)
        let thrown = LockedBox(false)
        Thread.detachNewThread {
            do {
                let observation = try controller.observe(label: "Owned concurrent", progress: { _ in
                    entered.signal()
                    _ = resume.wait(timeout: .now() + 10)
                })
                result.update { $0 = observation }
            } catch { thrown.update { $0 = true } }
            done.signal()
        }
        XCTAssertEqual(entered.wait(timeout: .now() + 10), .success)
        XCTAssertThrowsError(try controller.observe(label: "Concurrent"))
        controller.revoke()
        XCTAssertEqual(controller.state, .stopping)
        XCTAssertGreaterThanOrEqual(fcntl(held, F_GETFD), 0)
        XCTAssertEqual(releases.read(), 0)
        // Another descriptor cannot reuse a still-owned slot.
        let extra = Darwin.open(fixture.base, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        XCTAssertNotEqual(extra, held)
        _ = Darwin.close(extra)
        resume.signal()
        XCTAssertEqual(done.wait(timeout: .now() + 10), .success)
        XCTAssertFalse(thrown.read())
        XCTAssertEqual(result.read()?.state, .revoked)
        XCTAssertNil(result.read()?.snapshot)
        XCTAssertEqual(releases.read(), 1)
        XCTAssertEqual(fcntl(held, F_GETFD), -1)
        try fixture.assertSentinel()
    }

    func testCancelBeforeObserveReleasesWithoutReadingAndIsOneUse() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        var releases = 0
        let controller = ObservationController(lease: try fixture.lease(io: io, release: { releases += 1 }), io: io)
        controller.cancel()
        controller.cancel()
        XCTAssertEqual(releases, 1)
        XCTAssertThrowsError(try controller.observe(label: "Cancelled"))
    }

    func testCancellationAtProgressProjectionAndFinalAdmissionLatches() throws {
        for boundary in [ControllerBoundary.beforeProjection, .afterProjection, .beforeAdmission] {
            let fixture = try OwnedFixture()
            let io = DarwinDirectoryIO()
            var controller: ObservationController!
            controller = ObservationController(lease: try fixture.lease(io: io), io: io,
                seams: ObservationSeams(boundary: { if $0 == boundary { controller.cancel() } }))
            let result = try controller.observe(label: "Retired before admission")
            XCTAssertEqual(result.state, .cancelled)
            XCTAssertNil(result.snapshot)
            XCTAssertNil(controller.takeSnapshot(result))
            controller = nil
        }
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io)
        let result = try controller.observe(label: "Progress cancellation", progress: { _ in controller.cancel() })
        XCTAssertEqual(result.state, .cancelled)
        XCTAssertNil(result.snapshot)
    }

    func testCancelAndProgressCallbackFailuresHaveNoArtifact() throws {
        enum CallbackFailure: Error { case injected }
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        let first = ObservationController(lease: try fixture.lease(io: io), io: io)
        XCTAssertEqual(try first.observe(label: "Cancel failure", cancel: { throw CallbackFailure.injected }).state, .failed)
        let second = ObservationController(lease: try fixture.lease(io: io), io: io)
        let result = try second.observe(label: "Progress failure", progress: { _ in throw CallbackFailure.injected })
        XCTAssertEqual(result.state, .failed)
        XCTAssertNil(result.snapshot)
    }

    func testFinalProgressRootReplacementIsWithheld() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io)
        var callbacks = 0
        let result = try controller.observe(label: "Final progress", progress: { count in
            XCTAssertEqual(count, 1)
            callbacks += 1
            XCTAssertEqual(Darwin.rename(fixture.source, fixture.base + "/retired"), 0)
            try FileManager.default.createDirectory(atPath: fixture.source, withIntermediateDirectories: false)
        })
        XCTAssertEqual(callbacks, 1)
        XCTAssertEqual(result.state, .rootChanged)
        XCTAssertNil(result.snapshot)
    }

    func testFinalAdmittedCancelCallbackPrecedesGuardAndThenIsSealed() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        var finalProgress = false
        var changed = false
        var afterGuardCalls = 0
        var projectionStarted = false
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io,
            seams: ObservationSeams(boundary: { _ in projectionStarted = true }))
        let result = try controller.observe(label: "Last cancel poll", cancel: {
            if projectionStarted { afterGuardCalls += 1 }
            if finalProgress && !changed {
                changed = true
                XCTAssertEqual(Darwin.rename(fixture.source, fixture.base + "/retired"), 0)
                try FileManager.default.createDirectory(atPath: fixture.source, withIntermediateDirectories: false)
            }
            return false
        }, progress: { _ in finalProgress = true })
        XCTAssertTrue(changed)
        XCTAssertEqual(result.state, .rootChanged)
        XCTAssertNil(result.snapshot)
        XCTAssertEqual(afterGuardCalls, 0)
    }

    func testSuccessfulObservationHasNoUserCallbacksAfterGuard() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        var projection = false
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io,
            seams: ObservationSeams(boundary: { _ in projection = true }))
        let result = try controller.observe(label: "Sealed callbacks", cancel: {
            XCTAssertFalse(projection)
            return false
        }, progress: { _ in XCTAssertFalse(projection) })
        XCTAssertEqual(result.state, .observed)
    }

    func testRevocationOutranksCancellationAndLateResultIsNotReusable() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        let controller = ObservationController(lease: try fixture.lease(io: io), io: io)
        let result = try controller.observe(label: "Observed")
        controller.cancel()
        controller.revoke()
        XCTAssertNil(controller.takeSnapshot(result))
        let second = ObservationController(lease: try fixture.lease(io: io), io: io)
        let terminal = try second.observe(label: "Both", progress: { _ in second.cancel(); second.revoke() })
        XCTAssertEqual(terminal.state, .revoked)
        XCTAssertNil(terminal.snapshot)
        XCTAssertNil(second.takeSnapshot(result))
    }

    func testLeaseReleaseCallbackRunsBeforeAdmissionAndCanReenter() throws {
        let fixture = try OwnedFixture()
        let io = DarwinDirectoryIO()
        var controller: ObservationController!
        var released = false
        let lease = try fixture.lease(io: io, release: {
            released = true
            XCTAssertEqual(controller.state, .observing)
            controller.revoke()
        })
        controller = ObservationController(lease: lease, io: io)
        let result = try controller.observe(label: "Release cancellation")
        XCTAssertTrue(released)
        XCTAssertEqual(result.state, .revoked)
        XCTAssertNil(result.snapshot)
        controller = nil
    }
}
