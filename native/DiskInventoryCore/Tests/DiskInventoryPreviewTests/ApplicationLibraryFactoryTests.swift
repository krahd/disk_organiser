import XCTest
import Foundation
import Darwin
@testable import DiskInventoryDesktop

@MainActor
final class ApplicationLibraryFactoryTests: XCTestCase {
    private let bytes = Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)
    private func resolve(_ factory: ApplicationLibraryFactory, _ intent: ApplicationLibraryIntent = .save) async throws -> LibraryStorage? {
        try await factory.resolve(intent, cancellation: ApplicationLibraryCancellation())
    }
    private func names(_ fixture: OwnedStorageFixture) throws -> [String] { try FileManager.default.contentsOfDirectory(atPath: fixture.directory).sorted() }
    private func home(_ fixture: OwnedStorageFixture, _ name: String = ApplicationLibraryFactory.homeName) -> String { fixture.path(name) }
    private func setup(_ fixture: OwnedStorageFixture) -> String { home(fixture, ApplicationLibraryFactory.setupName) }
    private func requireRejected(_ factory: ApplicationLibraryFactory, _ intent: ApplicationLibraryIntent = .save) async {
        do { let value = try await resolve(factory, intent); if let value { await value.close() }; XCTFail("Unsafe admission succeeded") } catch {}
    }
    func testConstructionAndAbsentOpenAreNonCreating() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), io = ApplicationFaultIO()
        let factory = ApplicationLibraryFactory(opener: opener, io: io)
        XCTAssertEqual(opener.calls, 0); XCTAssertEqual(try names(fixture), [])
        let missing = try await resolve(factory, .open)
        XCTAssertNil(missing); XCTAssertEqual(opener.calls, 1)
        XCTAssertEqual(io.creates, 0); XCTAssertEqual(io.writes, 0); XCTAssertEqual(io.publications, 0)
        XCTAssertEqual(try names(fixture), []); try fixture.assertSentinel()
    }
    func testFirstSaveCreatesExactPrivateNamespaceAndFreshFactoryReopensBytes() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let factory = ApplicationLibraryFactory(opener: opener)
        let result = try await resolve(factory); let store = try XCTUnwrap(result)
        XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.homeName])
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: home(fixture)).sorted(), ["home.json", "library.lock", "versions"])
        let value = try await CatalogueCodec().validate(bytes), receipt = try await store.save(value)
        try await store.acknowledge(receipt); await store.close(); await factory.retire()
        let reopened = try await resolve(ApplicationLibraryFactory(opener: opener), .open)
        let second = try XCTUnwrap(reopened), listing = try await second.list()
        XCTAssertEqual(listing.entries.count, 1)
        let loaded = try await second.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec())
        XCTAssertEqual(loaded.bytes, bytes); await second.close(); try fixture.assertSentinel()
    }
    func testSecondFactoryRefusesHeldLeaseThenAdmitsAfterClose() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let firstResult = try await resolve(ApplicationLibraryFactory(opener: opener)), first = try XCTUnwrap(firstResult)
        let next = ApplicationLibraryFactory(opener: opener)
        do { _ = try await resolve(next, .open); XCTFail("Lease duplicated") }
        catch ApplicationLibraryFailure.inUse {} catch { XCTFail("Wrong contention result") }
        await first.close()
        let result = try await resolve(next, .open), second = try XCTUnwrap(result)
        await second.close(); try fixture.assertSentinel()
    }
    func testUnmarkedFinalAndSetupArePreservedWithoutAdoption() async throws {
        for name in [ApplicationLibraryFactory.homeName, ApplicationLibraryFactory.setupName] {
            let fixture = try OwnedStorageFixture(), io = ApplicationFaultIO()
            XCTAssertEqual(mkdir(home(fixture, name), 0o700), 0)
            let factory = ApplicationLibraryFactory(opener: OwnedApplicationParentOpener(fixture), io: io)
            await requireRejected(factory); await requireRejected(factory, .open)
            XCTAssertEqual(io.creates, 0); XCTAssertEqual(io.writes, 0)
            XCTAssertEqual(try names(fixture), [name]); try fixture.assertSentinel()
        }
    }
    func testBothFinalAndSetupRefuseWithoutChoosingOrDeleting() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result)
        await store.close(); XCTAssertEqual(mkdir(setup(fixture), 0o700), 0)
        await requireRejected(ApplicationLibraryFactory(opener: opener), .open)
        XCTAssertEqual(try names(fixture).count, 2); try fixture.assertSentinel()
    }
    func testCompleteSetupSurvivesFailedRenameAndExplicitSaveResumes() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), io = ApplicationFaultIO()
        io.failBeforePublish = true
        await requireRejected(ApplicationLibraryFactory(opener: opener, io: io))
        XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.setupName])
        let next = ApplicationLibraryFactory(opener: opener)
        await requireRejected(next, .open)
        let result = try await resolve(next), store = try XCTUnwrap(result)
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty)
        await store.close(); XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.homeName]); try fixture.assertSentinel()
    }
    func testLostRenameResultRechecksSameFinalWithoutSecondNamespace() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), io = ApplicationFaultIO()
        io.failAfterPublish = true
        let factory = ApplicationLibraryFactory(opener: opener, io: io)
        await requireRejected(factory); XCTAssertEqual(io.publications, 1)
        io.failAfterPublish = false
        let result = try await resolve(factory), store = try XCTUnwrap(result)
        XCTAssertEqual(io.publications, 1); XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.homeName])
        await store.close(); try fixture.assertSentinel()
    }
    func testPreMarkerFailureRetainsOneRefusedSetupAcrossRetries() async throws {
        let fixture = try OwnedStorageFixture(), io = ApplicationFaultIO(); io.failCreateName = ApplicationLibraryFactory.markerName
        let factory = ApplicationLibraryFactory(opener: OwnedApplicationParentOpener(fixture), io: io)
        await requireRejected(factory); let created = io.creates
        io.failCreateName = nil
        for _ in 0..<3 { await requireRejected(factory) }
        XCTAssertEqual(io.creates, created); XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.setupName])
        try fixture.assertSentinel()
    }
    func testFlushFailureDoesNotAdmitOrPublishAndRecoveryKeepsIdentity() async throws {
        let fixture = try OwnedStorageFixture(), io = ApplicationFaultIO(); io.failFlush = true
        let factory = ApplicationLibraryFactory(opener: OwnedApplicationParentOpener(fixture), io: io)
        await requireRejected(factory); XCTAssertEqual(io.publications, 0)
        io.failFlush = false
        let result = try await resolve(factory), store = try XCTUnwrap(result)
        await store.close(); XCTAssertEqual(io.publications, 1); try fixture.assertSentinel()
    }
    func testCancelledBeforeAdmissionCreatesNothing() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), token = ApplicationLibraryCancellation()
        token.cancel()
        do { _ = try await ApplicationLibraryFactory(opener: opener).resolve(.save, cancellation: token); XCTFail("Cancelled admission") } catch {}
        XCTAssertEqual(opener.calls, 0); XCTAssertEqual(try names(fixture), []); try fixture.assertSentinel()
    }
    func testCancellationAfterRenameRetainsFinalAndNeverSavesCatalogue() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), token = ApplicationLibraryCancellation(), io = ApplicationFaultIO()
        io.afterPublish = { token.cancel() }
        let factory = ApplicationLibraryFactory(opener: opener, io: io)
        do { _ = try await factory.resolve(.save, cancellation: token); XCTFail("Cancelled result admitted") } catch {}
        XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.homeName])
        io.afterPublish = nil
        let result = try await resolve(factory, .open), store = try XCTUnwrap(result), listing = try await store.list()
        XCTAssertTrue(listing.entries.isEmpty); await store.close(); try fixture.assertSentinel()
    }
    func testMalformedOversizedAndDuplicateMarkersRefuseWithoutRewrite() async throws {
        for replacement in [Data("{}".utf8), Data(repeating: 32, count: 513), Data(#"{"schema":"x","schema":"y"}"#.utf8)] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result); await store.close()
            let marker = home(fixture) + "/home.json"
            try replacement.write(to: URL(fileURLWithPath: marker))
            await requireRejected(ApplicationLibraryFactory(opener: opener), .open)
            XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: marker)), replacement); try fixture.assertSentinel()
        }
    }
    func testSymlinkFinalAndEveryFixedLeafRefuseWithoutFollowing() async throws {
        for leaf in ["", "home.json", "library.lock", "versions"] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            if leaf.isEmpty {
                XCTAssertEqual(symlink(fixture.directory, home(fixture)), 0)
            } else {
                let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result); await store.close()
                let name = home(fixture) + "/" + leaf
                XCTAssertEqual(rename(name, name + ".retained"), 0)
                // Remove the extra-name variable from the guard: keep the moved
                // owned object in the parent, then present only the symlink leaf.
                XCTAssertEqual(rename(name + ".retained", fixture.path("retained")), 0)
                XCTAssertEqual(symlink(fixture.sentinel, name), 0)
            }
            await requireRejected(ApplicationLibraryFactory(opener: opener), .open); try fixture.assertSentinel()
        }
    }
    func testExtraRootEntryAndForeignModeAreRefusedWithoutRepair() async throws {
        for variant in ["extra", "mode"] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result); await store.close()
            if variant == "extra" { try OwnedStorageFixture.create(home(fixture) + "/unexpected", bytes: Data()) }
            else { XCTAssertEqual(chmod(home(fixture), 0o755), 0) }
            await requireRejected(ApplicationLibraryFactory(opener: opener), .open)
            if variant == "mode" { var info = stat(); XCTAssertEqual(lstat(home(fixture), &info), 0); XCTAssertEqual(info.st_mode & 0o777, 0o755) }
            try fixture.assertSentinel()
        }
    }
    func testSyntheticOwnerAndACLFailuresAreNotNativePrivacyClaims() async throws {
        for owner in [true, false] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result); await store.close()
            let io = ApplicationFaultIO(); io.syntheticWrongOwner = owner; io.syntheticACLRefusal = !owner
            await requireRejected(ApplicationLibraryFactory(opener: opener, io: io), .open)
            XCTAssertEqual(io.writes, 0); XCTAssertEqual(io.creates, 0); try fixture.assertSentinel()
        }
    }
    func testNamedLockReplacementRetiresNoForeignLockAndFailsOperations() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result)
        let lock = home(fixture) + "/library.lock"
        XCTAssertEqual(rename(lock, fixture.path("original-lock")), 0)
        try OwnedStorageFixture.create(lock, bytes: Data())
        do { _ = try await store.list(); XCTFail("Replaced lock accepted") } catch {}
        await store.close(); XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: lock)), Data()); try fixture.assertSentinel()
    }
    func testRetiredFactoryCannotReopenOrCreate() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), factory = ApplicationLibraryFactory(opener: opener)
        await factory.retire(); await requireRejected(factory)
        XCTAssertEqual(opener.calls, 0); XCTAssertEqual(try names(fixture), []); try fixture.assertSentinel()
    }
    func testConcurrentFinalCreationNeverReplacesEitherDirectory() async throws {
        let fixture = try OwnedStorageFixture(), io = ApplicationFaultIO()
        io.beforePublish = { XCTAssertEqual(mkdir(fixture.path(ApplicationLibraryFactory.homeName), 0o700), 0) }
        let factory = ApplicationLibraryFactory(opener: OwnedApplicationParentOpener(fixture), io: io)
        await requireRejected(factory)
        XCTAssertEqual(try names(fixture).count, 2)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: home(fixture)), [])
        io.beforePublish = nil; await requireRejected(factory); try fixture.assertSentinel()
    }
    func testCompleteSetupContainingVersionsCannotBePublishedAsNewHome() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), io = ApplicationFaultIO()
        io.failBeforePublish = true; await requireRejected(ApplicationLibraryFactory(opener: opener, io: io))
        try OwnedStorageFixture.create(setup(fixture) + "/versions/unexpected", bytes: Data("retain".utf8))
        await requireRejected(ApplicationLibraryFactory(opener: opener))
        XCTAssertEqual(try names(fixture), [ApplicationLibraryFactory.setupName]); try fixture.assertSentinel()
    }
    func testRetainedHomeVersionsAndMarkerAddressReplacementFailClosed() async throws {
        for leaf in ["", "versions", "home.json"] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result)
            let target = home(fixture) + (leaf.isEmpty ? "" : "/" + leaf)
            XCTAssertEqual(rename(target, fixture.path("retained")), 0)
            if leaf == "home.json" { try OwnedStorageFixture.create(target, bytes: Data("{}".utf8)) }
            else { XCTAssertEqual(mkdir(target, 0o700), 0) }
            do { _ = try await store.list(); XCTFail("Changed address admitted") } catch {}
            await store.close(); try fixture.assertSentinel()
        }
    }
    func testHardLinkedLockRefusesWithoutUnlinkingEitherName() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result); await store.close()
        let target = home(fixture) + "/library.lock"
        XCTAssertEqual(link(target, fixture.path("lock-link")), 0)
        await requireRejected(ApplicationLibraryFactory(opener: opener), .open)
        var stamp = stat(); XCTAssertEqual(lstat(target, &stamp), 0); XCTAssertEqual(stamp.st_nlink, 2); try fixture.assertSentinel()
    }
    func testApplicationActorPreservesEntryAndAggregateLimits() async throws {
        for count in [257, 17] {
            let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
            let result = try await resolve(ApplicationLibraryFactory(opener: opener)), store = try XCTUnwrap(result)
            for index in 0..<count {
                let path = home(fixture) + "/versions/owned-\(index)"
                let fd = Darwin.open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
                guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
                let amount: off_t = count == 17 ? 4 * 1024 * 1024 : 0
                XCTAssertEqual(ftruncate(fd, amount), 0); Darwin.close(fd)
            }
            do { _ = try await store.list(); XCTFail("App-data budget bypassed") } catch LibraryStorageFailure.limit {} catch { XCTFail("Unexpected budget result") }
            do { _ = try await store.save(try await CatalogueCodec().validate(bytes)); XCTFail("Over-budget save started") } catch {}
            await store.close(); try fixture.assertSentinel()
        }
    }

}
