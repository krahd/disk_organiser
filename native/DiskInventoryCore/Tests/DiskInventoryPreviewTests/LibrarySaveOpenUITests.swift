import XCTest
import AppKit
import Foundation
@testable import DiskInventoryDesktop

@MainActor
extension LibraryApplicationTests {
    func testNativePointerSaveOpenReplaceCancelCloseAndOriginalViews() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        let source = BundledLibraryExamples()
        let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: source), injection: OwnedLibraryInjection(storage: store))
        defer { window.discardAndClose(); h.close() }
        try h.useApplicationWindow(window.window); window.show()
        let owner = window.interaction, screens = try LibraryApplicationScreens(.saveOpen)
        defer { screens.close() }
        for choice in source.choices {
            try await clickNative("library-explore", using: h)
            try await clickNative("library-choice-" + choice.id, using: h)
            try await clickNative("library-prepare", using: h)
            try await ready(window.session, .reviewing)
            // The native key driver asserts trusted key events and current field
            // focus; it never repairs focus or substitutes a DOM click.
            if choice.id == "working" {
                _ = try await h.script("document.getElementById('catalogue-name').value = label; return 'fixture label prepared';",
                    arguments: ["label": "Creative collection · Projects and photos · Long user-labelled history · café <script>inert</script>"])
            }
            try await h.key("X", code: 7)
            try await h.click("catalogue-confirm")
            try await clickNative("library-done", using: h)
            try await ready(window.session, .ready)
        }
        try await clickNative("library-save", using: h); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .currentSaved)
        try await screens.native("80-native-library-saved.png", view: window.chrome)
        try await clickNative("library-open", using: h); try await settle(owner)
        try await clickNative("library-version-1", using: h); try await settle(owner)
        XCTAssertEqual(owner.preview?.locations.count, 2)
        try assertFirstVersionAtTop(in: try XCTUnwrap(h.window.attachedSheet))
        XCTAssertTrue(owner.preview?.locations.contains { $0.partial } == true)
        try await screens.native("81-native-open-two-locations.png", view: try XCTUnwrap(h.window.attachedSheet?.contentView))
        try await clickNative("library-open-cancel", using: h); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle)
        // Test-only stable IDs expose the existing control to the same checked
        // native pointer driver. No event/action is dispatched by this script.
        _ = try await h.script("document.querySelector('.source-card .text-button').id='owned-rename'; return 'identified';")
        try await h.click("owned-rename"); try await h.key("Z", code: 6); try await h.click("catalogue-confirm")
        try await clickNative("library-open", using: h); try await settle(owner)
        try await clickNative("library-version-1", using: h); try await settle(owner)
        XCTAssertTrue(owner.openLoss?.dirty == true)
        try await clickNative("library-replace", using: h); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .committed)
        try await screens.native("82-native-replace-result.png", view: window.chrome)
        try await screens.web("87-native-reopened-records.png", harness: h)
        _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').id='owned-selection'; return 'identified';")
        try await h.click("owned-selection")
        try await clickNative("window-close", using: h); try await settle(owner)
        XCTAssertEqual(owner.closeLoss?.selections, 1); XCTAssertFalse(owner.canCloseWithoutLoss)
        try await screens.native("83-native-selection-close.png", view: try XCTUnwrap(h.window.attachedSheet?.contentView))
        try await clickNative("library-keep", using: h); try await settle(owner)
        _ = try await h.script("document.querySelector('.source-card .text-button').id='owned-rename'; return 'identified';")
        try await h.click("owned-rename"); try await h.key("D", code: 2)
        try await clickNative("window-close", using: h); try await settle(owner)
        XCTAssertTrue(owner.closeLoss?.hasDraft == true)
        try await screens.native("84-native-draft-close.png", view: try XCTUnwrap(h.window.attachedSheet?.contentView))
        try await clickNative("library-keep", using: h); try await settle(owner)
        try await h.key("F", code: 3) // Restored existing field focus is required.
        try await h.click("catalogue-confirm")
        h.host.dropAfterLibrary = .acknowledgeSaved
        try await clickNative("library-save", using: h); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .pageUnresolved)
        try await screens.native("85-native-save-unconfirmed.png", view: window.chrome)
        try await clickNative("library-check", using: h); try await settle(owner)
        XCTAssertEqual(owner.saveOutcome, .currentSaved)
        h.window.setContentSize(NSSize(width: 680, height: 600))
        try await clickNative("library-open", using: h); try await settle(owner)
        try await clickNative("library-version-1", using: h); try await settle(owner)
        try assertFirstVersionAtTop(in: try XCTUnwrap(h.window.attachedSheet))
        try await screens.native("86-native-open-narrow.png", view: try XCTUnwrap(h.window.attachedSheet?.contentView))
        try await clickNative("library-open-cancel", using: h); try await settle(owner)
        let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 2)
        try fixture.assertSentinel(); try screens.finish()
        window.discardAndClose(); await store.close()
    }

    func testCompleteSavedListingPaginationAndAll32LocationPreview() async throws {
        // Metadata rows use fresh owned files; no app directory/path factory.
        let empty = Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)
        for count in [0, 1, 64, 65, 256] {
            let fixture = try OwnedStorageFixture()
            for _ in 0..<count { try fixture.file("catalogue-" + UUID().uuidString.lowercased() + ".json", bytes: empty) }
            let store = try fixture.store(), (h, owner) = try await injected(store)
            owner.open(); try await settle(owner)
            let listing = try XCTUnwrap(owner.listing); XCTAssertEqual(listing.entries.count, count)
            var all: [SavedLibraryEntry] = []
            for offset in stride(from: 0, to: count, by: 64) { all += try listing.page(offset) }
            XCTAssertEqual(all, listing.entries)
            owner.cancelOpen(); try await settle(owner); _ = owner.finalClose(); h.close(); await store.close()
            try fixture.assertSentinel()
        }
        let source = BundledLibraryExamples()
        let snapshotBytes = try await source.prepare(source.choices[1])
        let snapshot = try JSONSerialization.jsonObject(with: snapshotBytes)
        let records: [[String: Any]] = (0..<32).map { ["id": "source_" + UUID().uuidString.lowercased(), "label": "Location \($0 + 1) · <script>inert</script> · " + String(repeating: "é", count: 100), "snapshot": snapshot] }
        let bytes = try JSONSerialization.data(withJSONObject: ["schema_version": "disk-organiser/inventory-catalogue/v1", "records": records])
        let admitted = try await CatalogueCodec().validate(bytes)
        let preview = try LibraryCandidatePreview(admitted)
        XCTAssertEqual(preview.locations.count, 32); XCTAssertTrue(preview.locations.allSatisfy { $0.partial })
        XCTAssertTrue(preview.locations.last?.label.hasPrefix("Location 32") == true)
    }
}

@MainActor
extension LibraryApplicationTests {
    private func assertFirstVersionAtTop(in window: NSWindow) throws {
        window.contentView?.layoutSubtreeIfNeeded()
        let first = try button("library-version-1", in: window)
        let scroll = try XCTUnwrap(first.enclosingScrollView), document = try XCTUnwrap(scroll.documentView)
        let actual = document.convert(first.bounds, from: first), visible = scroll.documentVisibleRect
        print("OWNED_LIBRARY_FIRST_ROW frame=\(actual) visible=\(visible) flipped=\(document.isFlipped)")
        XCTAssertGreaterThan(actual.width, 0)
        XCTAssertGreaterThan(actual.height, 0)
        XCTAssertGreaterThan(visible.width, 0)
        XCTAssertGreaterThan(visible.height, 0)
        XCTAssertTrue(document.isFlipped)
        XCTAssertTrue(visible.contains(actual), "The first version must be fully visible without a pointer workaround")
        XCTAssertGreaterThanOrEqual(actual.minY - visible.minY, 0)
        XCTAssertLessThanOrEqual(actual.minY - visible.minY, 16, "Short lists start at the visible top, not below a blank area")
    }
    func testNativeReadAndPreparationFailuresOfferUsableCancelWithoutFalseCheck() async throws {
        let fixture = try OwnedStorageFixture(), store = try fixture.store()
        try await seedEmpty(store)
        let badID = UUID()
        try fixture.file("catalogue-" + badID.uuidString.lowercased() + ".json", bytes: Data("invalid catalogue".utf8))
        let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
        let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: BundledLibraryExamples()), injection: OwnedLibraryInjection(storage: store))
        defer { window.discardAndClose(); h.close() }
        try h.useApplicationWindow(window.window); window.show()
        let owner = window.interaction
        try await clickNative("library-open", using: h); try await settle(owner)
        let entries = try XCTUnwrap(owner.listing?.entries)
        let bad = try XCTUnwrap(entries.firstIndex { $0.id == badID }) + 1
        let good = try XCTUnwrap(entries.firstIndex { $0.id != badID }) + 1
        try await clickNative("library-version-\(bad)", using: h); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .choosing)
        var sheet = try XCTUnwrap(h.window.attachedSheet)
        try assertFirstVersionAtTop(in: sheet)
        XCTAssertTrue(try button("library-replacement-check", in: sheet).isHidden)
        XCTAssertTrue(window.checkButton.isHidden)
        XCTAssertTrue(try button("library-version-\(good)", in: sheet).isEnabled)
        XCTAssertTrue(try button("library-open-cancel", in: sheet).isEnabled)
        h.host.dropAfterLibrary = .prepareReplacement
        try await clickNative("library-version-\(good)", using: h); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .unresolved); XCTAssertFalse(owner.canCheckReplacement)
        sheet = try XCTUnwrap(h.window.attachedSheet)
        XCTAssertTrue(try button("library-replacement-check", in: sheet).isHidden)
        XCTAssertTrue(window.checkButton.isHidden)
        XCTAssertFalse(try button("library-replace", in: sheet).isEnabled)
        h.host.dropAfterLibrary = .cancelOpen
        try await clickNative("library-open-cancel", using: h); try await settle(owner)
        XCTAssertEqual(owner.openPhase, .unresolved); XCTAssertFalse(owner.canCheckResult)
        try await clickNative("library-open-cancel", using: h); try await settle(owner)
        XCTAssertEqual(owner.flight, .idle); XCTAssertTrue(window.openButton.isEnabled)
        XCTAssertFalse(h.host.libraryCalls.contains(.replacementResult))
        XCTAssertFalse(h.host.libraryCalls.contains(.commitReplacement))
        try fixture.assertSentinel(); await store.close()
    }

    func testNativeCloseLostSaveAcknowledgementOffersCheckAndRetainsSelections() async throws {
        for afterApply in [false, true] {
            let fixture = try OwnedStorageFixture(), store = try fixture.store()
            let h = try await OwnedPreviewHarness.open(storageMode: .ownedStorage)
            let window = try LibraryWindowController(session: LibrarySession(host: h.host, source: BundledLibraryExamples()), injection: OwnedLibraryInjection(storage: store))
            defer { window.discardAndClose(); h.close() }
            try h.useApplicationWindow(window.window); window.show()
            let owner = window.interaction
            // Fixed example setup is distinct from the native close/check actions.
            try await addExample(owner, h)
            _ = try await h.script("document.querySelector('#catalogue-results input:not(:disabled)').id='owned-close-selection'; return 'identified';")
            try await h.click("owned-close-selection")
            try await clickNative("window-close", using: h); try await settle(owner)
            if afterApply { h.host.dropAfterLibrary = .acknowledgeSaved }
            else { h.host.dropBeforeLibrary = .acknowledgeSaved }
            try await clickNative("library-close-save", using: h); try await settle(owner)
            XCTAssertEqual(owner.saveOutcome, .pageUnresolved)
            let deadline = Date().addingTimeInterval(3)
            while Date() < deadline {
                h.pumpApplicationEvents()
                if let sheet = h.window.attachedSheet, optionalButton("library-close-check", in: sheet) != nil { break }
                try await Task.sleep(for: .milliseconds(20))
            }
            let sheet = try XCTUnwrap(h.window.attachedSheet)
            XCTAssertNil(optionalButton("library-close-save", in: sheet))
            XCTAssertTrue(try button("library-close-check", in: sheet).isEnabled)
            XCTAssertTrue(try button("library-keep", in: sheet).isEnabled)
            try await clickNative("library-close-check", using: h); try await settle(owner)
            XCTAssertEqual(owner.saveOutcome, .currentSaved); XCTAssertEqual(owner.closeLoss?.dirty, false)
            XCTAssertEqual(owner.closeLoss?.selections, 1); XCTAssertFalse(owner.canCloseWithoutLoss)
            try await clickNative("library-keep", using: h); try await settle(owner)
            XCTAssertTrue(h.window.isVisible); XCTAssertEqual(owner.flight, .idle)
            let state = try await h.host.libraryCall(.status, id: UUID())
            XCTAssertEqual(state.loss?.selections, 1)
            let listing = try await store.list(); XCTAssertEqual(listing.entries.count, 1)
            try fixture.assertSentinel(); await store.close()
        }
    }
}
