import XCTest
import Foundation
import Darwin
@testable import DiskInventoryDesktop

@MainActor
final class LibraryStorageTests: XCTestCase {
    private let bytes = Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)
    private func catalogue() async throws -> ValidatedCatalogue { try await CatalogueCodec().validate(bytes) }
    private func completed(_ id: UUID) -> String { "catalogue-" + id.uuidString.lowercased() + ".json" }
    private func pending(_ id: UUID) -> String { "catalogue-" + id.uuidString.lowercased() + ".pending" }

    func testSavedRoundTripAndFreshStoreReopen() async throws {
        let fixture = try OwnedStorageFixture(), first = try fixture.store()
        let value = try await catalogue(), receipt = try await first.save(value)
        try await first.acknowledge(receipt)
        let listing = try await first.list()
        XCTAssertEqual(listing.entries.count, 1); XCTAssertEqual(listing.pendingCount, 0)
        let reopened = try await first.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec())
        XCTAssertEqual(reopened.bytes, bytes)
        await first.close()
        let second = try fixture.store(), after = try await second.list()
        let restored = try await second.open(try XCTUnwrap(after.entries.first), codec: CatalogueCodec())
        XCTAssertEqual(restored.bytes, bytes)
        try fixture.assertSentinel(); await second.close()
    }

    func testUnacknowledgedSaveRequiresReconciliationBeforeAnotherSave() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), value = try await catalogue()
        let receipt = try await store.save(value)
        do { _ = try await store.save(value); XCTFail("Second save started before acknowledgement") } catch {}
        guard case .published(let found) = try await store.reconcile() else { return XCTFail("Missing completed save") }
        XCTAssertEqual(found, receipt); try await store.acknowledge(found)
        let second = try await store.save(value); try await store.acknowledge(second)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 2)
        try fixture.assertSentinel(); await store.close()
    }

    func testRepeatedAttemptCannotOverwrite() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), value = try await catalogue(), id = UUID()
        let receipt = try await store.save(value, attempt: id); try await store.acknowledge(receipt)
        do { _ = try await store.save(value, attempt: id); XCTFail("Attempt reused") } catch {}
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: fixture.path(completed(id)))), bytes)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
        try fixture.assertSentinel(); await store.close()
    }

    func testExistingPendingCollisionPreservesOriginalBytes() async throws {
        let fixture = try OwnedStorageFixture(), id = UUID(), original = Data("prior pending".utf8)
        try fixture.file(pending(id), bytes: original)
        let store = try fixture.store(), value = try await catalogue()
        do { _ = try await store.save(value, attempt: id); XCTFail("Pending overwritten") } catch {}
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: fixture.path(pending(id)))), original)
        let listing = try await store.list(); XCTAssertEqual(listing.pendingCount, 1); XCTAssertTrue(listing.entries.isEmpty)
        try fixture.assertSentinel(); await store.close()
    }

    func testCompletedCollisionFailsClosedWithoutFallbackOrDuplicate() async throws {
        let fixture = try OwnedStorageFixture(), id = UUID()
        try fixture.file(completed(id), bytes: bytes)
        let store = try fixture.store(), value = try await catalogue()
        do { _ = try await store.save(value, attempt: id); XCTFail("Completed artifact overwritten") } catch {}
        do { _ = try await store.reconcile(); XCTFail("Foreign inode treated as our save") } catch {}
        do { _ = try await store.save(value); XCTFail("Uncertain save retried") } catch {}
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: fixture.path(completed(id)))), bytes)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1); XCTAssertEqual(listing.pendingCount, 1)
        try fixture.assertSentinel(); await store.close()
    }

    func testFailureBeforePublishReconcilesAndRetainsPending() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.failBeforePublish = true
        let store = try fixture.store(io: io), value = try await catalogue()
        do { _ = try await store.save(value); XCTFail("Failed publish accepted") } catch {}
        guard case .notPublishedPendingRetained = try await store.reconcile() else { return XCTFail("False published claim") }
        let before = try await store.list(); XCTAssertEqual(before.pendingCount, 1); XCTAssertTrue(before.entries.isEmpty)
        io.failBeforePublish = false
        let receipt = try await store.save(value); try await store.acknowledge(receipt)
        let after = try await store.list(); XCTAssertEqual(after.entries.count, 1); XCTAssertEqual(after.pendingCount, 1)
        try fixture.assertSentinel(); await store.close()
    }

    func testPublishedButUnacknowledgedSaveReconcilesWithoutWritingAgain() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.failAfterPublish = true
        let store = try fixture.store(io: io), value = try await catalogue()
        do { _ = try await store.save(value); XCTFail("Lost result reported saved") } catch {}
        let written = io.written
        guard case .published(let receipt) = try await store.reconcile() else { return XCTFail("Published file not reconciled") }
        try await store.acknowledge(receipt)
        XCTAssertEqual(io.written, written)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1); XCTAssertEqual(listing.pendingCount, 0)
        try fixture.assertSentinel(); await store.close()
    }

    func testPartialWritesReadsAndEINTRPreserveExactBytes() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO()
        io.writeChunk = 3; io.readChunk = 5; io.writeInterrupts = 2; io.readInterrupts = 2; io.flushInterrupts = 1
        let store = try fixture.store(io: io), receipt = try await store.save(try await catalogue())
        try await store.acknowledge(receipt)
        let value = try await store.open(receipt.entry, codec: CatalogueCodec())
        XCTAssertEqual(value.bytes, bytes); XCTAssertEqual(io.written, bytes.count)
        try fixture.assertSentinel(); await store.close()
    }

    func testWriteFailureRetainsIncompletePendingWithoutPublication() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.writeChunk = 3; io.failAfterBytes = 9
        let store = try fixture.store(io: io)
        do { _ = try await store.save(try await catalogue()); XCTFail("Incomplete save accepted") } catch {}
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty); XCTAssertEqual(listing.pendingCount, 1)
        XCTAssertEqual(listing.listedLogicalBytes, 9)
        try fixture.assertSentinel(); await store.close()
    }

    func testReadbackMismatchNeverPublishes() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.corruptRead = true
        let store = try fixture.store(io: io)
        do { _ = try await store.save(try await catalogue()); XCTFail("Wrong readback accepted") } catch {}
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty); XCTAssertEqual(listing.pendingCount, 1)
        try fixture.assertSentinel(); await store.close()
    }

    func testCancelledSaveCreatesNoArtifact() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), value = try await catalogue()
        let task = Task { try await store.save(value) }; task.cancel()
        do { _ = try await task.value; XCTFail("Cancelled save accepted") } catch {}
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty); XCTAssertEqual(listing.pendingCount, 0)
        try fixture.assertSentinel(); await store.close()
    }

    func testMovedOwnedDirectoryFailsAddressGuard() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        try FileManager.default.moveItem(atPath: fixture.directory, toPath: fixture.base + "/moved")
        do { _ = try await store.save(try await catalogue()); XCTFail("Moved root admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testForeignEntryCannotSelectAnotherStoreFile() async throws {
        let one = try OwnedStorageFixture(), two = try OwnedStorageFixture(), io = StorageFaultIO()
        let first = try one.store(), second = try two.store(io: io)
        let receipt = try await first.save(try await catalogue()); try await first.acknowledge(receipt)
        do { _ = try await second.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Foreign selection admitted") } catch {}
        XCTAssertEqual(io.readOpens, 0)
        try one.assertSentinel(); try two.assertSentinel(); await first.close(); await second.close()
    }

    func testMalformedCompletedCatalogueDoesNotBecomeAValidatedLibrary() async throws {
        let fixture = try OwnedStorageFixture(); try fixture.file(completed(UUID()), bytes: Data("{broken}".utf8))
        let store = try fixture.store(), listing = try await store.list()
        do { _ = try await store.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec()); XCTFail("Malformed library admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testChangedEntrySinceListingIsRejected() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        let fd = Darwin.open(fixture.path(completed(id)), O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC)
        XCTAssertGreaterThanOrEqual(fd, 0)
        let appended = [UInt8(32)].withUnsafeBytes { Darwin.write(fd, $0.baseAddress, $0.count) }
        XCTAssertEqual(appended, 1); Darwin.close(fd)
        do { _ = try await store.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Changed file admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testCompleteListingPagesDoNotOmitEntriesOrPendingCounts() async throws {
        let fixture = try OwnedStorageFixture()
        for n in 0..<130 {
            let id = try XCTUnwrap(UUID(uuidString: String(format: "00000000-0000-4000-8000-%012d", n)))
            try fixture.file(completed(id), bytes: bytes)
        }
        try fixture.file(pending(UUID()), bytes: bytes); try fixture.file("unknown-file", bytes: Data([65]))
        let store = try fixture.store(), listing = try await store.list()
        let pages = try listing.page(0) + listing.page(64) + listing.page(128)
        XCTAssertEqual(listing.entries.count, 130); XCTAssertEqual(pages.count, 130)
        XCTAssertEqual(Set(pages.map(\.id)).count, 130)
        XCTAssertEqual(listing.pendingCount, 1); XCTAssertEqual(listing.unknownCount, 1)
        XCTAssertThrowsError(try listing.page(-1)); XCTAssertThrowsError(try listing.page(131))
        try fixture.assertSentinel(); await store.close()
    }

    func testDirectoryEntryBoundRefusesRatherThanTruncating() async throws {
        let fixture = try OwnedStorageFixture()
        for n in 0...LibraryStorage.maximumEntries { try fixture.file("unknown-\(n)", bytes: Data()) }
        let store = try fixture.store()
        do { _ = try await store.list(); XCTFail("Overflow listing truncated silently") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testAggregateLogicalByteBoundRefusesOversizedStore() async throws {
        let fixture = try OwnedStorageFixture()
        for n in 0..<17 { try fixture.sparse("unknown-\(n)", bytes: Int64(CatalogueCodec.maximumBytes)) }
        let store = try fixture.store()
        do { _ = try await store.list(); XCTFail("Aggregate store overflow admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testNonRegularAndHardLinkedEntriesAreRefused() async throws {
        for kind in ["symlink", "hardlink", "fifo"] {
            let fixture = try OwnedStorageFixture(), name = completed(UUID())
            let result: Int32
            if kind == "symlink" { result = Darwin.symlink(fixture.sentinel, fixture.path(name)) }
            else if kind == "hardlink" { result = Darwin.link(fixture.sentinel, fixture.path(name)) }
            else { result = mkfifo(fixture.path(name), 0o600) }
            XCTAssertEqual(result, 0)
            let io = StorageFaultIO(), store = try fixture.store(io: io)
            do { _ = try await store.list(); XCTFail("Unsupported entry admitted: \(kind)") } catch {}
            XCTAssertEqual(io.readOpens, 0)
            try fixture.assertSentinel(); await store.close()
        }
    }

    func testSelectedPathChangedToSymlinkNeverReadsItsTarget() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), store = try fixture.store(io: io), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        XCTAssertEqual(Darwin.unlink(fixture.path(completed(id))), 0) // Only this test's generated file.
        XCTAssertEqual(Darwin.symlink(fixture.sentinel, fixture.path(completed(id))), 0)
        let reads = io.readCalls
        do { _ = try await store.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Symlink target read") } catch {}
        XCTAssertEqual(io.readCalls, reads, "Rejection must precede every data-read syscall")
        try fixture.assertSentinel(); await store.close()
    }

    func testGrowthDuringReadIsRejected() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), store = try fixture.store(io: io), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        let target = fixture.path(completed(id))
        io.afterRead = {
            let fd = Darwin.open(target, O_WRONLY | O_APPEND | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw LibraryStorageFailure.filesystem(errno) }
            defer { Darwin.close(fd) }
            let wrote = [UInt8(32)].withUnsafeBytes { Darwin.write(fd, $0.baseAddress, $0.count) }
            guard wrote == 1 else { throw LibraryStorageFailure.filesystem(errno) }
        }
        do { _ = try await store.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Growing file admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testReplacementDuringReadIsRejected() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), store = try fixture.store(io: io), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        let target = fixture.path(completed(id)), replacement = bytes
        io.afterRead = {
            guard Darwin.unlink(target) == 0 else { throw LibraryStorageFailure.filesystem(errno) }
            try OwnedStorageFixture.create(target, bytes: replacement)
        }
        do { _ = try await store.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Replaced file admitted") } catch {}
        try fixture.assertSentinel(); await store.close()
    }

    func testUnavailableAdmissionClosesTransferredRootExactlyOnce() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), fd = try fixture.rejectionDescriptor()
        do {
            _ = try LibraryStorage(adopting: fd, admission: .unavailable, guardAddress: { _ in }, io: io)
            XCTFail("Unavailable admission accepted")
        } catch {}
        XCTAssertEqual(io.closedDescriptors, [fd])
        try fixture.assertSentinel()
    }

    func testNonPrivateRootIsRefused() async throws {
        let fixture = try OwnedStorageFixture(mode: 0o500)
        do { _ = try fixture.store(); XCTFail("Unsupported root mode admitted") } catch {}
        try fixture.assertSentinel()
    }

    func testForeignAndReplayedAcknowledgementsAreRejected() async throws {
        let one = try OwnedStorageFixture(), two = try OwnedStorageFixture(), first = try one.store(), second = try two.store()
        let value = try await catalogue(), a = try await first.save(value), b = try await second.save(value)
        do { try await first.acknowledge(b); XCTFail("Foreign receipt accepted") } catch {}
        try await first.acknowledge(a)
        do { try await first.acknowledge(a); XCTFail("Receipt replay accepted") } catch {}
        try await second.acknowledge(b)
        try one.assertSentinel(); try two.assertSentinel(); await first.close(); await second.close()
    }

    func testClosedStoreRefusesReuseAndPreservesPublishedArtifact() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), value = try await catalogue(), id = UUID()
        let receipt = try await store.save(value, attempt: id)
        await store.close(); await store.close()
        do { try await store.acknowledge(receipt); XCTFail("Closed store acknowledged") } catch {}
        do { _ = try await store.list(); XCTFail("Closed store listed") } catch {}
        do { _ = try await store.save(value); XCTFail("Closed store wrote") } catch {}
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: fixture.path(completed(id)))), bytes)
        try fixture.assertSentinel()
    }

    func testRejectedCatalogueCannotCreateAnyStorageOutput() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), codec = CatalogueCodec()
        do {
            let rejected = try await codec.validate(Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[],"records":[]}"#.utf8))
            _ = try await store.save(rejected)
            XCTFail("Duplicate-key input reached storage")
        } catch {}
        let listing = try await store.list()
        XCTAssertTrue(listing.entries.isEmpty); XCTAssertEqual(listing.pendingCount, 0); XCTAssertEqual(listing.unknownCount, 0)
        try fixture.assertSentinel(); await store.close()
    }

    func testReadCapDoesNotTrustAReportedSmallerFileSize() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), store = try fixture.store(io: io), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        let fd = Darwin.open(fixture.path(completed(id)), O_WRONLY | O_NOFOLLOW | O_CLOEXEC)
        XCTAssertGreaterThanOrEqual(fd, 0)
        XCTAssertEqual(ftruncate(fd, Int64(CatalogueCodec.maximumBytes + 1)), 0); Darwin.close(fd)
        io.reportedSize = Int64(bytes.count)
        let before = io.readCalls
        do { _ = try await store.open(receipt.entry, codec: CatalogueCodec()); XCTFail("Oversized actual bytes admitted") }
        catch LibraryStorageFailure.limit {} // The hard read cap, before parsing/metadata agreement.
        catch { XCTFail("Wrong gate: \(error)") }
        XCTAssertGreaterThan(io.readCalls - before, 64)
        try fixture.assertSentinel(); await store.close()
    }

    func testRepeatedEINTRIsBoundedAndCannotPublish() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(); io.writeInterrupts = 10_000
        let store = try fixture.store(io: io), value = try await catalogue()
        do { _ = try await store.save(value); XCTFail("Unbounded interruption accepted") }
        catch LibraryStorageFailure.interrupted {}
        catch { XCTFail("Wrong gate: \(error)") }
        XCTAssertGreaterThan(io.writeInterrupts, 0); XCTAssertEqual(io.written, 0)
        let listing = try await store.list(); XCTAssertTrue(listing.entries.isEmpty); XCTAssertEqual(listing.pendingCount, 1)
        try fixture.assertSentinel(); await store.close()
    }
    func testCloseWhileStrictAdmissionIsHeldCannotReturnAStaleLibrary() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), gate = HeldCatalogueAdmission()
        let receipt = try await store.save(try await catalogue()); try await store.acknowledge(receipt)
        let operation = Task { try await store.open(receipt.entry, codec: gate) }
        try await gate.waitForArrival()
        await store.close(); await gate.release()
        do { _ = try await operation.value; XCTFail("Closed session returned a library") }
        catch LibraryStorageFailure.unavailable {}
        catch { XCTFail("Wrong gate: \(error)") }
        try fixture.assertSentinel()
    }

    func testReplacementDuringStrictAdmissionIsRejected() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), gate = HeldCatalogueAdmission(), id = UUID()
        let receipt = try await store.save(try await catalogue(), attempt: id); try await store.acknowledge(receipt)
        let operation = Task { try await store.open(receipt.entry, codec: gate) }
        try await gate.waitForArrival()
        // Keep the old inode allocated so this regression cannot reuse its identity.
        try FileManager.default.moveItem(atPath: fixture.path(completed(id)), toPath: fixture.path("owned-retired-file"))
        try fixture.file(completed(id), bytes: bytes)
        await gate.release()
        do { _ = try await operation.value; XCTFail("Replacement during validation admitted") }
        catch LibraryStorageFailure.changed {}
        catch { XCTFail("Wrong gate: \(error)") }
        try fixture.assertSentinel(); await store.close()
    }

    func testConcurrentOperationCannotEnterDuringHeldAdmission() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store(), gate = HeldCatalogueAdmission()
        let value = try await catalogue(), receipt = try await store.save(value); try await store.acknowledge(receipt)
        let operation = Task { try await store.open(receipt.entry, codec: gate) }
        try await gate.waitForArrival()
        do { _ = try await store.list(); XCTFail("Overlapping operation admitted") }
        catch LibraryStorageFailure.busy {}
        catch { XCTFail("Wrong gate: \(error)") }
        await gate.release()
        let opened = try await operation.value
        XCTAssertEqual(opened.bytes, bytes)
        let after = try await store.list(); XCTAssertEqual(after.entries.count, 1)
        try fixture.assertSentinel(); await store.close()
    }

    func testMissingCompletedAndPendingArtifactsRemainUncertain() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), id = UUID(); io.failBeforePublish = true
        let store = try fixture.store(io: io), value = try await catalogue()
        do { _ = try await store.save(value, attempt: id); XCTFail("Publish unexpectedly accepted") } catch {}
        XCTAssertEqual(Darwin.unlink(fixture.path(pending(id))), 0) // This test's generated pending file only.
        do { _ = try await store.reconcile(); XCTFail("Missing artifacts declared resolved") }
        catch LibraryStorageFailure.uncertain {}
        catch { XCTFail("Ambiguity lost: \(error)") }
        let writes = io.written
        do { _ = try await store.save(value); XCTFail("Uncertain attempt retried") }
        catch LibraryStorageFailure.busy {}
        catch { XCTFail("Wrong gate: \(error)") }
        XCTAssertEqual(io.written, writes)
        try fixture.assertSentinel(); await store.close()
    }

    func testReplacedPendingArtifactRemainsUncertainWithoutReadingIt() async throws {
        let fixture = try OwnedStorageFixture(), io = StorageFaultIO(), id = UUID(); io.failBeforePublish = true
        let store = try fixture.store(io: io), value = try await catalogue()
        do { _ = try await store.save(value, attempt: id); XCTFail("Publish unexpectedly accepted") } catch {}
        try FileManager.default.moveItem(atPath: fixture.path(pending(id)), toPath: fixture.path("owned-retired-pending"))
        XCTAssertEqual(mkfifo(fixture.path(pending(id)), 0o600), 0)
        let reads = io.readCalls
        do { _ = try await store.reconcile(); XCTFail("Replaced pending artifact declared resolved") }
        catch LibraryStorageFailure.uncertain {}
        catch { XCTFail("Ambiguity lost: \(error)") }
        XCTAssertEqual(io.readCalls, reads)
        do { _ = try await store.save(value); XCTFail("Uncertain attempt retried") }
        catch LibraryStorageFailure.busy {}
        catch { XCTFail("Wrong gate: \(error)") }
        try fixture.assertSentinel(); await store.close()
    }

    func testNonemptyLibraryPreservesEditedLabelsAndHistoricalPartialRecords() async throws {
        struct Row: Decodable { let name: String; let input: String; let canonical: String? }
        let url = try XCTUnwrap(Bundle.module.url(forResource: "corpus", withExtension: "json", subdirectory: "LibraryValidation"))
        let rows = try JSONDecoder().decode([Row].self, from: Data(contentsOf: url))
        let row = try XCTUnwrap(rows.first { $0.name == "two labelled historical locations" })
        let expected = Data(try XCTUnwrap(row.canonical).utf8)
        let admitted = try await CatalogueCodec().validate(Data(row.input.utf8))
        let fixture = try OwnedStorageFixture(), first = try fixture.store()
        let receipt = try await first.save(admitted); try await first.acknowledge(receipt)
        XCTAssertEqual(try Data(contentsOf: URL(fileURLWithPath: fixture.path(completed(receipt.entry.id)))), expected)
        await first.close()
        let second = try fixture.store(), listing = try await second.list()
        let reopened = try await second.open(try XCTUnwrap(listing.entries.first), codec: CatalogueCodec())
        XCTAssertEqual(reopened.bytes, expected)
        // Exact bytes preserve both edited labels, original source labels/dates,
        // relative paths, string-valued sizes and the partial record's gaps.
        try fixture.assertSentinel(); await second.close()
    }

}
