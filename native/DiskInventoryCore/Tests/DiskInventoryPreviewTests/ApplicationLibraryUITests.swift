import XCTest
import AppKit
import Foundation
@testable import DiskInventoryDesktop

@MainActor
extension LibraryApplicationTests {
    func testNativeApplicationStorageMissingSaveContentionReopenAndCancelViews() async throws {
        let fixture = try OwnedStorageFixture(), opener = OwnedApplicationParentOpener(fixture)
        let screens = try LibraryApplicationScreens(.applicationData); defer { screens.close() }
        let first = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let window = try LibraryWindowController(session: LibrarySession(host: first.host, source: BundledLibraryExamples()), provider: ApplicationLibraryFactory(opener: opener))
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
        try await clickNative("library-save", using: first); try await settle(window.interaction)
        XCTAssertEqual(window.interaction.saveOutcome, .currentSaved)
        try await screens.native("94-application-library-saved.png", view: window.chrome)
        let next = try await OwnedPreviewHarness.open(storageMode: .applicationData)
        let reopened = try LibraryWindowController(session: LibrarySession(host: next.host, source: BundledLibraryExamples()), provider: ApplicationLibraryFactory(opener: opener))
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
