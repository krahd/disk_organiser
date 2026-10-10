import XCTest
import AppKit
import Foundation
@testable import DiskInventoryDesktop

@MainActor
extension LibraryApplicationTests {
    private func lazy(_ provider: any LibraryStorageProviding, codec: (any CatalogueValidating)? = nil) async throws -> (OwnedPreviewHarness, LibraryInteraction) {
        let h = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let owner = try LibraryInteraction(session: LibrarySession(host: h.host, source: BundledLibraryExamples()), provider: provider, codec: codec ?? CatalogueCodec())
        return (h, owner)
    }
    func testLazyApplicationOpenMissingPreservesSelectionFocusAndCreatesNothing() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), io = ApplicationFaultIO()
        let (h, owner) = try await lazy(ApplicationLibraryFactory(opener: opener, io: io))
        defer { _ = owner.finalClose(); h.close() }
        XCTAssertTrue(owner.canSave); XCTAssertTrue(owner.canOpen); XCTAssertEqual(opener.calls, 0)
        try await addExample(owner, h)
        _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').click(); const s=document.getElementById('catalogue-search');s.value='Design';s.dispatchEvent(new Event('input'));s.focus();return 'ready';")
        owner.open(); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle); XCTAssertEqual(owner.bootstrap.state, .missing)
        XCTAssertTrue(owner.message?.contains("No saved library versions yet") == true)
        let status = try await h.host.libraryCall(.status, id: UUID()); XCTAssertEqual(status.loss?.selections, 1); XCTAssertTrue(status.loss?.dirty == true)
        let focus = try await h.script("return document.activeElement.id;"); XCTAssertEqual(focus, "catalogue-search")
        let search = try await h.script("return document.getElementById('catalogue-search').value;"); XCTAssertEqual(search, "Design")
        XCTAssertEqual(io.creates, 0); XCTAssertEqual(io.writes, 0); try fixture.assertSentinel()
    }
    func testDraftRefusalNeverStartsLazyStorage() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let (h, owner) = try await lazy(ApplicationLibraryFactory(opener: opener)); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        _ = try await h.script("document.querySelector('.source-card .text-button').click();document.getElementById('catalogue-name').value='Unfinished';return 'draft';")
        owner.save(); try await settle(owner); owner.open(); try await settle(owner)
        XCTAssertEqual(opener.calls, 0); XCTAssertFalse(owner.canCheckResult)
        let draft = try await h.script("return document.getElementById('catalogue-name').value;"); XCTAssertEqual(draft, "Unfinished")
        try fixture.assertSentinel()
    }
    func testSaveCapturesEditsMadeDuringLazyBootstrapAndReservesOneFlight() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let provider = HeldApplicationProvider(ApplicationLibraryFactory(opener: opener))
        let (h, owner) = try await lazy(provider); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.save(); try await provider.wait()
        owner.save(); owner.open(); owner.session.choose()
        XCTAssertEqual(owner.flight, .save); XCTAssertEqual(owner.session.state, .ready)
        _ = try await h.script("document.querySelector('.source-card .text-button').click();document.getElementById('catalogue-name').value='Edited while preparing';document.getElementById('catalogue-form').requestSubmit();return 'edited';")
        await provider.release(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .currentSaved)
        let calls = await provider.callCount(); XCTAssertEqual(calls, 1)
        let store = try XCTUnwrap(owner.bootstrap.storage), listing = try await store.list()
        let value = try await store.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec())
        XCTAssertTrue(String(decoding: value.bytes, as: UTF8.self).contains("Edited while preparing")); try fixture.assertSentinel()
    }
    func testImmediateSaveCancelPreventsFactoryAndKeepsDirtyRecords() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let (h, owner) = try await lazy(ApplicationLibraryFactory(opener: opener)); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.save(); owner.cancelSavePreparation(); try await settle(owner)
        XCTAssertEqual(opener.calls, 0); XCTAssertEqual(owner.saveOutcome, .rejected); XCTAssertTrue(owner.canSave)
        let dirty = try await catalogueDirty(h); XCTAssertEqual(dirty, "dirty"); XCTAssertFalse(owner.canCheckResult)
        try fixture.assertSentinel()
    }
    func testCancelLateReturnedActorClosesItsLeaseWithoutCatalogueSave() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let provider = ReturnedApplicationProvider(ApplicationLibraryFactory(opener: opener))
        let (h, owner) = try await lazy(provider); defer { _ = owner.finalClose(); h.close() }
        owner.save(); try await provider.wait(); owner.cancelSavePreparation(); await provider.release(); try await settle(owner)
        XCTAssertEqual(owner.bootstrap.state, .unresolved); XCTAssertNil(owner.bootstrap.storage)
        let result = try await ApplicationLibraryFactory(opener: opener).resolve(.open, cancellation: ApplicationLibraryCancellation())
        let store = try XCTUnwrap(result), listing = try await store.list()
        XCTAssertTrue(listing.entries.isEmpty); await store.close(); try fixture.assertSentinel()
    }
    func testCancelAfterAdmissionBeforeSaveRetiresPreparedLease() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture), codec = HeldCatalogueAdmission()
        let (h, owner) = try await lazy(ApplicationLibraryFactory(opener: opener), codec: codec); defer { _ = owner.finalClose(); h.close() }
        owner.save(); try await codec.waitForArrival(); XCTAssertEqual(owner.bootstrap.state, .ready)
        owner.cancelSavePreparation(); await codec.release(); try await settle(owner)
        XCTAssertEqual(owner.bootstrap.state, .unresolved); XCTAssertNil(owner.bootstrap.storage)
        XCTAssertFalse(h.host.libraryCalls.contains(.acknowledgeSaved))
        let result = try await ApplicationLibraryFactory(opener: opener).resolve(.open, cancellation: ApplicationLibraryCancellation())
        let store = try XCTUnwrap(result), listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty)
        await store.close(); try fixture.assertSentinel()
    }
    func testCloseDuringBootstrapCancelsThenQueriesFreshLoss() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let provider = HeldApplicationProvider(ApplicationLibraryFactory(opener: opener))
        let (h, owner) = try await lazy(provider); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.save(); try await provider.wait(); owner.enquireClose()
        XCTAssertFalse(owner.closeUnknown); await provider.release(); try await settle(owner)
        XCTAssertEqual(opener.calls, 0); XCTAssertEqual(owner.flight, .close)
        XCTAssertTrue(owner.closeLoss?.dirty == true); XCTAssertFalse(owner.closeUnknown); XCTAssertFalse(owner.canCloseWithoutLoss)
        owner.keepOpen(); try await settle(owner); XCTAssertTrue(owner.canSave); try fixture.assertSentinel()
    }
    func testCancelOpenDuringBootstrapReleasesFenceAndPreservesCatalogue() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let provider = HeldApplicationProvider(ApplicationLibraryFactory(opener: opener))
        let (h, owner) = try await lazy(provider); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.open(); try await provider.wait(); owner.cancelOpen(); await provider.release(); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle); XCTAssertEqual(opener.calls, 0)
        let dirty = try await catalogueDirty(h); XCTAssertEqual(dirty, "dirty")
        let count = try await h.script("return String(document.querySelectorAll('.source-card').length);"); XCTAssertEqual(count, "1")
        XCTAssertTrue(owner.canSave); try fixture.assertSentinel()
    }
    func testInUseBeforeSaveOffersRetryWithoutAcknowledgement() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let first = try await ApplicationLibraryFactory(opener: opener).resolve(.save, cancellation: ApplicationLibraryCancellation())
        let held = try XCTUnwrap(first)
        let (h, owner) = try await lazy(ApplicationLibraryFactory(opener: opener)); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.save(); try await settle(owner)
        XCTAssertEqual(owner.bootstrap.state, .blocked); XCTAssertTrue(owner.message?.contains("in use") == true)
        XCTAssertFalse(owner.canCheckResult); XCTAssertTrue(owner.canSave)
        let dirty = try await catalogueDirty(h); XCTAssertEqual(dirty, "dirty")
        await held.close(); owner.save(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .currentSaved)
        try fixture.assertSentinel()
    }
    func testRetiredBootstrapRejectsAndClosesDelayedActor() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let provider = ReturnedApplicationProvider(ApplicationLibraryFactory(opener: opener))
        let bootstrap = try LibraryStorageBootstrap(owned: nil, provider: provider)
        let operation = Task { @MainActor in try await bootstrap.obtain(.save) }
        try await provider.wait(); bootstrap.retire(); await provider.release()
        do { _ = try await operation.value; XCTFail("Late actor installed") } catch {}
        XCTAssertEqual(bootstrap.state, .retired); XCTAssertNil(bootstrap.storage)
        let result = try await ApplicationLibraryFactory(opener: opener).resolve(.open, cancellation: ApplicationLibraryCancellation())
        let store = try XCTUnwrap(result), listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty)
        await store.close(); try fixture.assertSentinel()
    }
    func testBrokenProviderCannotClaimOrRetireAnExistingInteractionOwner() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let first = try LibraryStorageBootstrap(owned: OwnedLibraryInjection(storage: store), provider: nil)
        let second = try LibraryStorageBootstrap(owned: nil, provider: DuplicateApplicationProvider(store))
        do { _ = try await second.obtain(.save); XCTFail("Duplicate owner accepted") } catch {}
        XCTAssertEqual(second.state, .blocked); XCTAssertNil(second.storage)
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty)
        XCTAssertTrue(first.storage === store); second.retire(); await store.close(); first.retire(); try fixture.assertSentinel()
    }
    func testApplicationModeRequiresExactlyItsExplicitLazyProvider() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let h = try await OwnedPreviewHarness.open(storageMode: .applicationData); defer { h.close() }
        let session = LibrarySession(host: h.host, source: BundledLibraryExamples())
        XCTAssertThrowsError(try LibraryInteraction(session: session))
        XCTAssertThrowsError(try LibraryInteraction(session: session, injection: OwnedLibraryInjection(storage: store)))
        let owner = try LibraryInteraction(session: session, provider: ApplicationLibraryFactory(opener: OwnedApplicationParentOpener(fixture)))
        XCTAssertTrue(owner.hasStorage); XCTAssertNil(owner.bootstrap.storage)
        _ = owner.finalClose(); await store.close(); try fixture.assertSentinel()
    }

}
