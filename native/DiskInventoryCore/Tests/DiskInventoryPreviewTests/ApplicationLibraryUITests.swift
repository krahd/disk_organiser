import XCTest
import AppKit
import Foundation
@testable import DiskInventoryDesktop

@MainActor
extension LibraryApplicationTests {
    func testNativeApplicationStorageMissingSaveContentionReopenAndCancelViews() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let screens = try LibraryApplicationScreens(.applicationData); defer { screens.close() }
        let observedSource = OwnedLibrarySource()
        let first = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let window = try LibraryWindowController(session: LibrarySession(host: first.host, source: observedSource), provider: ApplicationLibraryFactory(opener: opener))
        defer { window.discardAndClose(); first.close() }
        try first.useApplicationWindow(window.window); window.show()
        XCTAssertTrue(window.saveButton.isEnabled); XCTAssertTrue(window.openButton.isEnabled); XCTAssertEqual(opener.calls, 0)
        try await screens.native("90-application-storage-controls.png", view: window.chrome)
        try await clickNative("library-open", using: first); try await settle(window.interaction)
        XCTAssertEqual(window.interaction.bootstrap.state, .missing)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: fixture.directory), [])
        try await screens.native("91-application-missing-library.png", view: window.chrome)
        for choice in window.session.source.choices {
            try await clickNative("library-explore", using: first)
            try await clickNative("library-choice-" + choice.id, using: first)
            try await clickNative("library-prepare", using: first); try await ready(window.session, .reviewing)
            try await first.key("K", code: 40); try await first.click("catalogue-confirm")
            try await clickNative("library-done", using: first); try await ready(window.session, .ready)
        }
        XCTAssertEqual(observedSource.calls, 2)
        XCTAssertEqual(observedSource.completedSourceRoots.count, 2)
        XCTAssertTrue(observedSource.completedSourceRoots.allSatisfy { !FileManager.default.fileExists(atPath: $0) })
        try await clickNative("library-save", using: first); try await settle(window.interaction)
        XCTAssertEqual(window.interaction.saveOutcome, .currentSaved)
        try await screens.native("94-application-library-saved.png", view: window.chrome)
        let unopenedSource = OwnedLibrarySource()
        let next = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let reopened = try LibraryWindowController(session: LibrarySession(host: next.host, source: unopenedSource), provider: ApplicationLibraryFactory(opener: opener))
        defer { reopened.discardAndClose(); next.close() }
        try next.useApplicationWindow(reopened.window); reopened.show()
        try await clickNative("library-save", using: next); try await settle(reopened.interaction)
        XCTAssertEqual(reopened.interaction.bootstrap.state, .blocked)
        XCTAssertTrue(reopened.interaction.message?.contains("in use") == true)
        XCTAssertFalse(reopened.interaction.canCheckResult); XCTAssertTrue(reopened.saveButton.isEnabled)
        try await screens.native("92-application-library-in-use.png", view: reopened.chrome)
        // The acceptance path must release its lease through the real native
        // Close action. No direct actor/model close can make this proof pass.
        try await clickNative("window-close", using: first); try await settle(window.interaction)
        let closeDeadline = Date().addingTimeInterval(3)
        while window.window.isVisible && Date() < closeDeadline { first.pumpApplicationEvents(); try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(window.window.isVisible); XCTAssertEqual(window.interaction.flight, .closed)
        guard !window.window.isVisible, window.interaction.flight == .closed else { throw CataloguePreviewHost.Failure.expired }
        let reopenDeadline = Date().addingTimeInterval(3)
        repeat {
            try await clickNative("library-open", using: next); try await settle(reopened.interaction)
            if reopened.interaction.openPhase == .choosing { break }
            guard reopened.interaction.bootstrap.state == .blocked,
                  reopened.interaction.message?.contains("in use") == true else { throw CataloguePreviewHost.Failure.unavailable }
            try await Task.sleep(for: .milliseconds(10))
        } while Date() < reopenDeadline
        XCTAssertEqual(reopened.interaction.openPhase, .choosing)
        guard reopened.interaction.openPhase == .choosing else { throw CataloguePreviewHost.Failure.expired }
        try await clickNative("library-version-1", using: next); try await settle(reopened.interaction)
        XCTAssertEqual(reopened.interaction.preview?.locations.count, 2)
        try assertFirstVersionAtTop(in: try XCTUnwrap(next.window.attachedSheet))
        try await screens.native("95-application-reopen-preview.png", view: try XCTUnwrap(next.window.attachedSheet?.contentView))
        try await clickNative("library-open-cancel", using: next); try await settle(reopened.interaction)
        let empty = try await next.script("return String(document.querySelectorAll('.source-card').length);"); XCTAssertEqual(empty, "0")
        try await clickNative("library-open", using: next); try await settle(reopened.interaction)
        try await clickNative("library-version-1", using: next); try await settle(reopened.interaction)
        try await clickNative("library-replace", using: next); try await settle(reopened.interaction)
        let count = try await next.script("return String(document.querySelectorAll('.source-card').length);"); XCTAssertEqual(count, "2")
        // Both real owned source folders have already been retired and removed.
        // Searching this reopened history must not invoke either source again.
        try await next.click("catalogue-search")
        let searchKeys: [(String, UInt16)] = [("D", 2), ("e", 14), ("s", 1), ("i", 34), ("g", 5), ("n", 45)]
        for (letter, code) in searchKeys {
            try await next.key(letter, code: code, expectedTarget: "catalogue-search")
        }
        try await next.wait("return String(document.querySelectorAll('#catalogue-results > *').length);", equals: "2")
        try await next.wait("return document.getElementById('catalogue-search').value;", equals: "Design")
        let resultRows = try await next.script("return JSON.stringify([...document.querySelectorAll('#catalogue-results > *')].map(r => ({path:r.querySelector('strong').textContent,kind:r.querySelector('.entry-kind').textContent,record:r.querySelector('[id^=result-source-]').textContent})));")
        let rows = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(resultRows.utf8)) as? [[String: String]])
        XCTAssertEqual(rows.count, 2)
        guard rows.count == 2 else { throw CataloguePreviewHost.Failure.invalidPayload }
        XCTAssertEqual(rows.map { $0["path"] }, ["Projects/Design.txt", "Projects/Design.txt"])
        XCTAssertEqual(rows.map { $0["kind"] }, ["File · 600 B listed", "File · 700 B listed"])
        XCTAssertTrue(rows[0]["record"]?.hasPrefix("Record 1:") == true)
        XCTAssertTrue(rows[1]["record"]?.hasPrefix("Record 2:") == true)
        let partial = try await next.script("return document.querySelectorAll('.source-card')[1].textContent;")
        XCTAssertTrue(partial.contains("Partial folder record · gaps remain"))
        XCTAssertEqual(observedSource.calls, 2); XCTAssertEqual(unopenedSource.calls, 0)
        try await screens.web("96-application-reopened-records.png", harness: next)
        let cancelledFixture = try OwnedStorageFixture(), cancelledOpener = OwnedApplicationParentOpener(cancelledFixture)
        let provider = HeldApplicationProvider(ApplicationLibraryFactory(opener: cancelledOpener))
        let cancelHost = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let cancelWindow = try LibraryWindowController(session: LibrarySession(host: cancelHost.host, source: BundledLibraryExamples()), provider: provider)
        defer { cancelWindow.discardAndClose(); cancelHost.close() }
        try cancelHost.useApplicationWindow(cancelWindow.window); cancelWindow.show()
        try await clickNative("library-save", using: cancelHost); try await provider.wait()
        try await clickNative("library-save-cancel", using: cancelHost)
        await provider.release(); try await settle(cancelWindow.interaction)
        XCTAssertEqual(cancelledOpener.calls, 0); XCTAssertEqual(cancelWindow.interaction.saveOutcome, .rejected)
        XCTAssertTrue(cancelWindow.saveButton.isEnabled)
        try await screens.native("93-application-preparation-cancelled.png", view: cancelWindow.chrome)
        try screens.finish(); try fixture.assertSentinel(); try cancelledFixture.assertSentinel()
    }
}
