import XCTest
import AppKit
import Foundation
import Darwin
@testable import DiskInventoryDesktop

private final class AcknowledgementFaultIO: LibraryFileIO, @unchecked Sendable {
    var reads = 0
    var refuseAcknowledgement = true
    override func openRead(_ parent: Int32, _ name: String) throws -> Int32 {
        reads += 1
        if reads >= 2 && refuseAcknowledgement { throw LibraryStorageFailure.filesystem(EIO) }
        return try super.openRead(parent, name)
    }
}

@MainActor
extension LibraryApplicationTests {
    func settle(_ owner: LibraryInteraction) async throws {
        let deadline = Date().addingTimeInterval(8)
        while owner.busy && Date() < deadline { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(owner.busy)
        guard !owner.busy else { throw CataloguePreviewHost.Failure.expired }
    }
    func injected(_ store: LibraryStorage, codec: (any CatalogueValidating)? = nil) async throws -> (OwnedPreviewHarness, LibraryInteraction) {
        let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        let session = LibrarySession(host: h.host, source: BundledLibraryExamples())
        let owner = try LibraryInteraction(session: session, injection: OwnedLibraryInjection(storage: store), codec: codec ?? CatalogueCodec())
        return (h, owner)
    }
    func addExample(_ owner: LibraryInteraction, _ h: OwnedPreviewHarness, index: Int = 0) async throws {
        let session = owner.session
        session.choose(); session.select(session.source.choices[index]); session.prepare()
        try await ready(session, .reviewing)
        try await h.click("catalogue-confirm")
        session.finishReview(); try await ready(session, .ready)
    }
    func catalogueDirty(_ h: OwnedPreviewHarness) async throws -> String {
        let result = try await h.host.libraryCall(.status, id: UUID())
        return try XCTUnwrap(result.values["dirty"])
    }
    func testOwnedEmptySaveHasExactBytesAndRepeatedUnchangedSaveDoesNotWrite() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        owner.save(); owner.save(); owner.open(); owner.session.choose()
        XCTAssertEqual(owner.flight, .save); XCTAssertEqual(owner.session.state, .ready)
        try await settle(owner); XCTAssertEqual(owner.saveOutcome, .currentSaved)
        let first = try await store.list(); XCTAssertEqual(first.entries.count, 1)
        let bytes = try await store.open(try XCTUnwrap(first.entries.first), codec: CatalogueCodec()).bytes
        XCTAssertEqual(String(decoding: bytes, as: UTF8.self), #"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#)
        owner.save(); try await settle(owner)
        let second = try await store.list(); XCTAssertEqual(second.entries, first.entries)
        XCTAssertTrue(owner.message?.contains("No catalogue changes") == true)
        try fixture.assertSentinel(); await store.close()
    }
    func testLostPageAcknowledgementsBeforeAndAfterApplyNeverWriteAgain() async throws {
        for afterApply in [false, true] {
            let fixture = try OwnedStorageFixture(), store = try fixture.store()
            let (h, owner) = try await injected(store)
            if afterApply { h.host.dropAfterLibrary = .acknowledgeSaved }
            else { h.host.dropBeforeLibrary = .acknowledgeSaved }
            owner.save(); try await settle(owner)
            XCTAssertEqual(owner.saveOutcome, .pageUnresolved); XCTAssertFalse(owner.canSave); XCTAssertFalse(owner.canOpen)
            let before = try await store.list(); XCTAssertEqual(before.entries.count, 1)
            owner.checkSave(); try await settle(owner)
            XCTAssertEqual(owner.saveOutcome, .currentSaved)
            let after = try await store.list(); XCTAssertEqual(after.entries, before.entries)
        let observed1 = try await catalogueDirty(h)
        XCTAssertEqual(observed1, "clean")
            try fixture.assertSentinel(); _ = owner.finalClose(); h.close(); await store.close()
        }
    }
    func testPublishedButLostResultChecksOneAttemptAndDoesNotDuplicate() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.failAfterPublish = true
        let store = try fixture.store(io: io), (h, owner) = try await injected(store)
        defer { _ = owner.finalClose(); h.close() }
        owner.save(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .storageUnresolved)
        owner.save(); owner.open(); XCTAssertFalse(owner.busy)
        owner.checkSave(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .currentSaved)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1); XCTAssertEqual(listing.pendingCount, 0)
        try fixture.assertSentinel(); await store.close()
    }
    func testFailedPublicationRetainsIncompleteFileWithoutInventingSavedState() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.failBeforePublish = true
        let store = try fixture.store(io: io), (h, owner) = try await injected(store)
        defer { _ = owner.finalClose(); h.close() }
        owner.save(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .storageUnresolved)
        owner.checkSave(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .notPublished)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 0); XCTAssertEqual(listing.pendingCount, 1)
        XCTAssertTrue(owner.canSave); try fixture.assertSentinel(); await store.close()
    }
    func testStorageAcknowledgementMustSucceedBeforePageCanBecomeClean() async throws {
        let fixture = try OwnedStorageFixture(), io = AcknowledgementFaultIO()
        let store = try fixture.store(io: io), (h, owner) = try await injected(store)
        defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        owner.save(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .storageUnresolved)
        let observed2 = try await catalogueDirty(h)
        XCTAssertEqual(observed2, "dirty")
        XCTAssertFalse(h.host.libraryCalls.contains(.acknowledgeSaved))
        io.refuseAcknowledgement = false
        owner.checkSave(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .currentSaved)
        let observed3 = try await catalogueDirty(h)
        XCTAssertEqual(observed3, "clean")
        try fixture.assertSentinel(); await store.close()
    }
    func testLaterEditAfterExportStaysDirtyAfterEarlierRevisionSave() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), gate = HeldCatalogueAdmission()
        let (h, owner) = try await injected(store, codec: gate)
        defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        owner.save(); try await gate.waitForArrival()
        owner.session.choose(); XCTAssertEqual(owner.session.state, .ready)
        // Data setup only: native pointer/keyboard rename has its own UI case.
        _ = try await h.script("document.querySelector('.source-card .text-button').click(); document.getElementById('catalogue-name').value='Later edit'; document.getElementById('catalogue-form').requestSubmit(); return 'edited';")
        await gate.release(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .earlierSaved);
        let observed4 = try await catalogueDirty(h)
        XCTAssertEqual(observed4, "dirty")
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
        let value = try await store.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec())
        XCTAssertFalse(String(decoding: value.bytes, as: UTF8.self).contains("Later edit"))
        try fixture.assertSentinel(); await store.close()
    }
    func testCloseFencePreservesDraftAndTemporarySelectionAfterSave() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').click(); return 'selected';")
        owner.enquireClose(); try await settle(owner)
        XCTAssertEqual(owner.closeLoss?.selections, 1); XCTAssertEqual(owner.closeLoss?.dirty, true)
        owner.saveBeforeClose(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .currentSaved); XCTAssertEqual(owner.closeLoss?.selections, 1)
        XCTAssertFalse(owner.canCloseWithoutLoss); XCTAssertEqual(owner.closeLoss?.dirty, false)
        owner.keepOpen(); try await settle(owner)
        _ = try await h.script("document.querySelector('.source-card .text-button').click(); document.getElementById('catalogue-name').value='Uncommitted draft'; return 'draft';")
        owner.enquireClose(); try await settle(owner); XCTAssertTrue(owner.closeLoss?.hasDraft == true)
        owner.saveBeforeClose(); XCTAssertFalse(owner.busy)
        owner.keepOpen(); try await settle(owner)
        let observed5 = try await h.script("return document.getElementById('catalogue-name').value;")
        XCTAssertEqual(observed5, "Uncommitted draft")
        let observed6 = try await h.script("return document.activeElement.id;")
        XCTAssertEqual(observed6, "catalogue-name")
        try fixture.assertSentinel(); await store.close()
    }
    func testOpenRefusesDraftAndCancelPreservesCurrentState() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h); owner.save(); try await settle(owner)
        _ = try await h.script("document.querySelector('.source-card .text-button').click(); document.getElementById('catalogue-name').value='Keep this draft'; return 'draft';")
        owner.open(); try await settle(owner); XCTAssertEqual(owner.flight, .idle)
        let observed7 = try await h.script("return document.getElementById('catalogue-name').value;")
        XCTAssertEqual(observed7, "Keep this draft")
        try await h.key("\u{1b}", code: 53)
        _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').click(); document.getElementById('catalogue-search').value='Design'; document.getElementById('catalogue-search').dispatchEvent(new Event('input')); return 'selected';")
        owner.open(); try await settle(owner); XCTAssertEqual(owner.openPhase, .choosing)
        let entry = try XCTUnwrap(owner.listing?.entries.first)
        owner.selectSaved(entry); try await settle(owner); XCTAssertEqual(owner.preview?.locations.count, 1)
        owner.cancelOpen(); try await settle(owner); XCTAssertEqual(owner.flight, .idle)
        let observed8 = try await h.script("return document.getElementById('catalogue-search').value;")
        XCTAssertEqual(observed8, "Design")
        let status = try await h.host.libraryCall(.status, id: UUID()); XCTAssertEqual(status.loss?.selections, 1)
        try fixture.assertSentinel(); await store.close()
    }
    func testLostReplacementReplyAndLateCancelReportOneCommittedReplacement() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        owner.save(); try await settle(owner) // Deliberate zero-location saved version.
        try await addExample(owner, h)
        owner.open(); try await settle(owner)
        owner.selectSaved(try XCTUnwrap(owner.listing?.entries.first)); try await settle(owner)
        XCTAssertEqual(owner.preview?.locations.count, 0)
        h.host.dropAfterLibrary = .commitReplacement
        owner.replace(); owner.replace(); try await settle(owner); XCTAssertEqual(owner.openPhase, .unresolved)
        owner.cancelOpen(); try await settle(owner); XCTAssertEqual(owner.openPhase, .committed)
        let observed9 = try await h.script("return String(document.querySelectorAll('.source-card').length);")
        XCTAssertEqual(observed9, "0")
        XCTAssertEqual(h.host.libraryCalls.filter { $0 == .commitReplacement }.count, 1)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
        try fixture.assertSentinel(); await store.close()
    }
    func testDuplicateInjectionAndUnavailableExecutableModeRefuse() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), lease = OwnedLibraryInjection(storage: store)
        _ = try lease.claim(); XCTAssertThrowsError(try lease.claim())
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        let session = LibrarySession(host: h.host, source: BundledLibraryExamples())
        XCTAssertThrowsError(try LibraryInteraction(session: session, injection: OwnedLibraryInjection(storage: store)))
        let owner = try LibraryInteraction(session: session)
        owner.save(); owner.open(); XCTAssertFalse(owner.busy); XCTAssertFalse(owner.hasStorage)
        _ = owner.finalClose(); try fixture.assertSentinel(); await store.close()
    }
}

@MainActor
extension LibraryApplicationTests {
    func seedEmpty(_ store: LibraryStorage) async throws {
        let bytes = Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)
        let value = try await CatalogueCodec().validate(bytes)
        let receipt = try await store.save(value); try await store.acknowledge(receipt)
    }
    func testCancelDuringSelectedReadRetiresBeforePagePreparation() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), gate = HeldCatalogueAdmission()
        try await seedEmpty(store)
        let (h, owner) = try await injected(store, codec: gate); defer { _ = owner.finalClose(); h.close() }
        owner.open(); try await settle(owner)
        let entry = try XCTUnwrap(owner.listing?.entries.first)
        owner.selectSaved(entry); try await gate.waitForArrival()
        owner.selectSaved(entry); owner.replace(); owner.cancelOpen()
        XCTAssertTrue(owner.busy); await gate.release(); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle); XCTAssertNil(owner.preview)
        XCTAssertFalse(h.host.libraryCalls.contains(.prepareReplacement))
        XCTAssertFalse(h.host.libraryCalls.contains(.commitReplacement))
        try fixture.assertSentinel(); await store.close()
    }
    func testLostPreparedReplyCancelsItsSameCandidateWithoutReplacing() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        try await seedEmpty(store)
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        owner.open(); try await settle(owner)
        h.host.dropAfterLibrary = .prepareReplacement
        owner.selectSaved(try XCTUnwrap(owner.listing?.entries.first)); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .unresolved); XCTAssertFalse(owner.canReplace); XCTAssertFalse(owner.canCheckReplacement)
        owner.cancelOpen(); try await settle(owner); XCTAssertEqual(owner.flight, .idle)
        let count = try await h.script("return String(document.querySelectorAll('.source-card').length);")
        XCTAssertEqual(count, "1"); XCTAssertFalse(h.host.libraryCalls.contains(.commitReplacement))
        try fixture.assertSentinel(); await store.close()
    }
    func testLostCommitBeforeApplyQueriesThenCancelsWithoutRetryingCommit() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        try await seedEmpty(store)
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        owner.open(); try await settle(owner)
        owner.selectSaved(try XCTUnwrap(owner.listing?.entries.first)); try await settle(owner)
        h.host.dropBeforeLibrary = .commitReplacement
        owner.replace(); try await settle(owner); XCTAssertEqual(owner.openPhase, .unresolved)
        owner.checkReplacement(); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .unresolved); XCTAssertTrue(owner.message?.contains("No replacement is recorded") == true)
        owner.cancelOpen(); try await settle(owner)
        let count = try await h.script("return String(document.querySelectorAll('.source-card').length);")
        XCTAssertEqual(count, "1"); XCTAssertEqual(h.host.libraryCalls.filter { $0 == .commitReplacement }.count, 1)
        try fixture.assertSentinel(); await store.close()
    }
    func testRetiredViewNeverGetsNewAcknowledgementOrSecondWrite() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { h.close() }
        h.host.dropAfterLibrary = .acknowledgeSaved
        owner.save(); try await settle(owner); XCTAssertEqual(owner.saveOutcome, .pageUnresolved)
        h.host.invalidate(); owner.checkSave(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .pageUnresolved)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
        XCTAssertTrue(owner.finalClose()); XCTAssertEqual(h.host.state, .closed)
        try fixture.assertSentinel(); await store.close()
    }
}

@MainActor
extension LibraryApplicationTests {
    func testDistinctInjectionWrappersCannotShareOrReclaimOneActor() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let first = OwnedLibraryInjection(storage: store), second = OwnedLibraryInjection(storage: store)
        let (h, owner) = try await injectedWithLease(first)
        defer { _ = owner.finalClose(); h.close() }
        let other = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        defer { other.close() }
        let otherSession = LibrarySession(host: other.host, source: BundledLibraryExamples())
        XCTAssertThrowsError(try LibraryInteraction(session: otherSession, injection: second))
        XCTAssertNil(otherSession.intentAdmission)
        XCTAssertTrue(owner.canSave)
        XCTAssertTrue(owner.finalClose()); await store.close()
        XCTAssertThrowsError(try OwnedLibraryInjection(storage: store).claim())
        XCTAssertEqual(owner.session.message, "Preview closed. Saved versions, if any, are retained.")
        let unused = try fixture.store(); await unused.close()
        XCTAssertThrowsError(try OwnedLibraryInjection(storage: unused).claim())
        try fixture.assertSentinel()
    }
    private func injectedWithLease(_ lease: OwnedLibraryInjection) async throws -> (OwnedPreviewHarness, LibraryInteraction) {
        let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        let owner = try LibraryInteraction(session: LibrarySession(host: h.host, source: BundledLibraryExamples()), injection: lease)
        return (h, owner)
    }
    func testRejectedSelectedBytesPermitAnotherSelectionWithoutResultQuery() async throws {
        for changed in [false, true] {
            let fixture = try OwnedStorageFixture(), store = try fixture.store()
            try await seedEmpty(store)
            let badID = UUID(), name = "catalogue-" + badID.uuidString.lowercased() + ".json"
            try fixture.file(name, bytes: Data("malformed catalogue".utf8))
            let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
            try await addExample(owner, h)
            owner.open(); try await settle(owner)
            let entries = try XCTUnwrap(owner.listing?.entries)
            let bad = try XCTUnwrap(entries.first { $0.id == badID }), good = try XCTUnwrap(entries.first { $0.id != badID })
            if changed { try Data("changed after listing".utf8).write(to: URL(fileURLWithPath: fixture.path(name))) }
            owner.selectSaved(bad); try await settle(owner)
            XCTAssertEqual(owner.openPhase, .choosing); XCTAssertTrue(owner.canSelectSaved)
            XCTAssertNil(owner.preview); XCTAssertNil(owner.selected); XCTAssertFalse(owner.canCheckResult)
            XCTAssertTrue(owner.message?.contains("current library is unchanged") == true)
            owner.checkReplacement(); XCTAssertFalse(owner.busy)
            XCTAssertFalse(h.host.libraryCalls.contains(.replacementResult)); XCTAssertFalse(h.host.libraryCalls.contains(.prepareReplacement))
            owner.selectSaved(good); try await settle(owner); XCTAssertTrue(owner.canReplace)
            owner.cancelOpen(); try await settle(owner)
            let count = try await h.script("return String(document.querySelectorAll('.source-card').length);")
            XCTAssertEqual(count, "1"); try fixture.assertSentinel(); await store.close()
        }
    }
    func testLostCancelWithoutCandidateHasOnlyActionableCancelRecovery() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        owner.open(); try await settle(owner)
        h.host.dropAfterLibrary = .cancelOpen
        owner.cancelOpen(); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .unresolved); XCTAssertFalse(owner.canCheckResult)
        owner.checkReplacement(); XCTAssertFalse(owner.busy)
        XCTAssertFalse(h.host.libraryCalls.contains(.replacementResult))
        owner.cancelOpen(); try await settle(owner); XCTAssertEqual(owner.flight, .idle)
        XCTAssertTrue(owner.canOpen); try fixture.assertSentinel(); await store.close()
    }
    func testSaveBeforeCloseRecoversSameFenceLossBeforeAndAfterLostAcknowledgement() async throws {
        for afterApply in [false, true] {
            for selected in [false, true] {
                let fixture = try OwnedStorageFixture(), store = try fixture.store()
                let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
                try await addExample(owner, h)
                if selected { _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').click(); return 'selected';") }
                owner.enquireClose(); try await settle(owner)
                let fence = owner.closeID
                if afterApply { h.host.dropAfterLibrary = .acknowledgeSaved }
                else { h.host.dropBeforeLibrary = .acknowledgeSaved }
                owner.saveBeforeClose(); try await settle(owner)
                XCTAssertEqual(owner.saveOutcome, .pageUnresolved); XCTAssertTrue(owner.canCheckSave)
                XCTAssertEqual(owner.closeLoss?.dirty, true)
                let before = try await store.list(); XCTAssertEqual(before.entries.count, 1)
                owner.saveBeforeClose(); XCTAssertFalse(owner.busy)
                owner.checkSave(); try await settle(owner)
                XCTAssertEqual(owner.saveOutcome, .currentSaved); XCTAssertEqual(owner.closeID, fence)
                XCTAssertFalse(owner.closeUnknown); XCTAssertEqual(owner.closeLoss?.dirty, false)
                XCTAssertEqual(owner.closeLoss?.selections, selected ? 1 : 0)
                XCTAssertEqual(owner.canCloseWithoutLoss, !selected)
                let after = try await store.list(); XCTAssertEqual(after.entries, before.entries)
                owner.keepOpen(); try await settle(owner); XCTAssertEqual(owner.flight, .idle)
                let status = try await h.host.libraryCall(.status, id: UUID())
                XCTAssertEqual(status.loss?.selections, selected ? 1 : 0)
                try fixture.assertSentinel(); await store.close()
            }
        }
    }
    func testRecoveredSaveWithLostCloseStatusRetainsUnknownLoss() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let (h, owner) = try await injected(store); defer { _ = owner.finalClose(); h.close() }
        try await addExample(owner, h)
        owner.enquireClose(); try await settle(owner)
        h.host.dropAfterLibrary = .acknowledgeSaved
        owner.saveBeforeClose(); try await settle(owner)
        h.host.afterLibrary = { [weak host = h.host] operation in
            if operation == .savedResult { host?.dropBeforeLibrary = .status }
        }
        owner.checkSave(); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .currentSaved); XCTAssertTrue(owner.closeUnknown)
        XCTAssertFalse(owner.canCloseWithoutLoss)
        owner.saveBeforeClose(); XCTAssertFalse(owner.busy)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
        h.host.afterLibrary = nil; owner.keepOpen(); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle); try fixture.assertSentinel(); await store.close()
    }
    func testPreviewLimitPreservesLastCandidateAndRequiresExplicitNewOpen() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        try await seedEmpty(store)
        let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: BundledLibraryExamples()), injection: OwnedLibraryInjection(storage: store))
        defer { window.discardAndClose(); h.close() }
        try h.useApplicationWindow(window.window); window.show()
        let owner = window.interaction
        owner.open(); try await settle(owner)
        let entry = try XCTUnwrap(owner.listing?.entries.first)
        for _ in 0..<128 {
            XCTAssertTrue(owner.canSelectSaved)
            owner.selectSaved(entry); try await settle(owner); XCTAssertTrue(owner.canReplace)
        }
        XCTAssertTrue(owner.previewLimitReached); XCTAssertFalse(owner.canSelectSaved)
        XCTAssertTrue(owner.message?.contains("128-preview limit") == true)
        let calls = h.host.libraryCalls.count
        owner.selectSaved(entry); XCTAssertFalse(owner.busy); XCTAssertEqual(h.host.libraryCalls.count, calls)
        XCTAssertTrue(owner.canReplace); XCTAssertNotNil(owner.preview)
        let sheet = try XCTUnwrap(h.window.attachedSheet)
        XCTAssertFalse(try button("library-version-1", in: sheet).isEnabled)
        XCTAssertTrue(try button("library-replace", in: sheet).isEnabled)
        XCTAssertTrue(try button("library-open-cancel", in: sheet).isEnabled)
        owner.cancelOpen(); try await settle(owner)
        owner.open(); try await settle(owner); XCTAssertFalse(owner.previewLimitReached); XCTAssertTrue(owner.canSelectSaved)
        owner.cancelOpen(); try await settle(owner); try fixture.assertSentinel(); await store.close()
    }
}
