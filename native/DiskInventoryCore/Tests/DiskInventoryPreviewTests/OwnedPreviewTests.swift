import XCTest
import AppKit
import Foundation
import WebKit
import Darwin
@testable import DiskInventoryCore
@testable import DiskInventoryDesktop

@MainActor
final class OwnedPreviewTests: XCTestCase {
    private func snapshot(second: Bool = false) throws -> Data {
        let fixture = try OwnedFixture()
        try fixture.directory("Photos")
        try fixture.file("Photos/Trip.jpg", bytes: second ? 500 : 400)
        try fixture.file(second ? "Archive.txt" : "Notes.txt", bytes: 100)
        if second { try fixture.symlink("External link") }
        let io = DarwinDirectoryIO()
        var released = false
        let lease = try fixture.lease(io: io, release: { released = true })
        let controller = ObservationController(lease: lease, io: io, seams: ObservationSeams(clock: { 0 }))
        let result = try controller.observe(label: second ? "Archive <img src=x onerror=alert(1)>" : "Working projects")
        let bytes = try XCTUnwrap(controller.takeSnapshot(result))
        XCTAssertTrue(released); XCTAssertEqual(fcntl(lease.descriptor, F_GETFD), -1)
        try fixture.assertSentinel()
        return bytes // Fixture/lease are released before WebKit ever receives bytes.
    }
    private func expectFailure(_ action: () async throws -> Void) async {
        do { try await action(); XCTFail("Expected a fail-closed rejection") } catch {}
    }

    func testOwnedNativeSnapshotsRenderAndCompareWithNativeEvents() async throws {
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        XCTAssertFalse(h.host.webView.configuration.websiteDataStore.isPersistent)
        let screens = try OwnedPreviewScreens(); defer { screens.close() }
        let first = try snapshot(), second = try snapshot(second: true)
        let unavailable = try await h.script("return String(['open-inventory','save-catalogue','prepare-plan','inventory-file'].every(id=>document.getElementById(id).hidden&&document.getElementById(id).disabled));")
        XCTAssertEqual(unavailable, "true")
        _ = try await h.host.stage(first)
        let focused = try await h.script("return document.activeElement.id;")
        XCTAssertEqual(focused, "catalogue-name")
        try await screens.capture("60-native-add-preview.png", from: h)
        try await h.click("catalogue-confirm")
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "1")
        let committed = try await h.host.retire(); XCTAssertEqual(committed, "committed")
        _ = try await h.host.stage(second)
        // Genuine NSEvent Escape exercises the focused native WebKit dialog cancellation.
        let cancelFocused = try await h.script("return document.activeElement.id;")
        XCTAssertEqual(cancelFocused, "catalogue-name")
        try await h.key("\u{1b}", code: 53)
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "false")
        let dismissed = try await h.host.retire(); XCTAssertEqual(dismissed, "dismissed")
        _ = try await h.host.stage(second); try await h.click("catalogue-confirm")
        try await h.wait("return String(document.querySelectorAll('.source-card').length);", equals: "2")
        let added = try await h.host.retire(); XCTAssertEqual(added, "committed")
        let inert = try await h.script("return String(document.querySelectorAll('img').length===0 && document.body.textContent.includes('<img src=x onerror=alert(1)>'));")
        XCTAssertEqual(inert, "true")
        _ = try await h.script("window.scrollTo(0,0); return 'top';")
        try await screens.capture("61-native-overview.png", from: h)
        try await h.click("choose-comparison"); try await h.click("catalogue-confirm")
        try await h.wait("return String(document.getElementById('comparison-view').hidden);", equals: "false")
        _ = try await h.script("document.querySelector('.comparison-section').scrollIntoView({block:'start'}); return 'comparison';")
        try await screens.capture("62-native-comparison.png", from: h)
        h.window.setContentSize(NSSize(width: 390, height: 1000))
        _ = try await h.script("document.querySelector('.comparison-section').scrollIntoView({block:'start'}); return 'narrow';")
        try await screens.capture("63-native-narrow-history.png", from: h)
        _ = try await h.script("const e=document.getElementById('comparison-filter'); e.value='uncertain'; e.dispatchEvent(new Event('change')); e.scrollIntoView({block:'start'}); return 'uncertain';")
        try await screens.capture("64-native-narrow-uncertainty.png", from: h)
        let noOverflow = try await h.script("return String(document.documentElement.scrollWidth<=innerWidth+1);")
        XCTAssertEqual(noOverflow, "true")
        try await h.click("clear-comparison")
        let returnedFocus = try await h.script("return document.activeElement.id;")
        XCTAssertEqual(returnedFocus, "choose-comparison")
        try screens.finish()
    }

    func testStageBeforeCompletionAndRetirementFence() async throws {
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        let bytes = try snapshot()
        var release: CheckedContinuation<Void, Never>?
        h.host.beforeStageAcknowledgement = { await withCheckedContinuation { release = $0 } }
        let staging = Task { @MainActor in try await h.host.stage(bytes) }
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "true")
        for _ in 0..<100 where release == nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(release)
        XCTAssertEqual(h.host.state, .staging)
        let retirement = Task { @MainActor in try await h.host.retire() }
        await expectFailure { _ = try await h.host.stage(bytes) }
        try await h.click("catalogue-confirm") // Add already processed before retirement fence.
        try XCTUnwrap(release).resume(); h.host.beforeStageAcknowledgement = nil
        _ = try await staging.value
        let outcome = try await retirement.value; XCTAssertEqual(outcome, "committed")
        _ = try await h.host.stage(bytes)
        let cancelled = try await h.host.retire(); XCTAssertEqual(cancelled, "cancelled")
        _ = try await h.script("document.getElementById('catalogue-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})); return 'attempted';")
        let count = try await h.script("return String(document.querySelectorAll('.source-card').length);")
        XCTAssertEqual(count, "1"); XCTAssertEqual(h.host.state, .ready)
    }

    func testRetiredViewCannotBeRevivedByLateStageCompletion() async throws {
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        let bytes = try snapshot()
        var release: CheckedContinuation<Void, Never>?
        h.host.beforeStageAcknowledgement = { await withCheckedContinuation { release = $0 } }
        let staging = Task { @MainActor in try await h.host.stage(bytes) }
        try await h.wait("return String(document.getElementById('catalogue-dialog').open);", equals: "true")
        for _ in 0..<100 where release == nil { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(release)
        // Inject the public delegate notification; this is not an actual process-kill test.
        h.host.webViewWebContentProcessDidTerminate(h.host.webView)
        try XCTUnwrap(release).resume(); h.host.beforeStageAcknowledgement = nil
        await expectFailure { _ = try await staging.value }
        XCTAssertEqual(h.host.state, .blocked); XCTAssertTrue(h.host.webView.isHidden)
        await expectFailure { _ = try await h.host.stage(bytes) }
    }

    func testMalformedAndCataloguePayloadsDoNotBecomeRecords() async throws {
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        await expectFailure { _ = try await h.host.stage(Data([0xff])) }
        await expectFailure { _ = try await h.host.stage(Data([0xef, 0xbb, 0xbf, 0x7b, 0x7d])) }
        await expectFailure { _ = try await h.host.stage(Data(repeating: 32, count: 1_048_577)) }
        XCTAssertEqual(h.host.state, .ready)
        _ = try await h.host.stage(snapshot())
        try await h.click("catalogue-confirm"); _ = try await h.host.retire()
        await expectFailure { _ = try await h.host.stage(Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)) }
        XCTAssertEqual(h.host.state, .blocked)
        let count = try await h.script("return String(document.querySelectorAll('.source-card').length);")
        XCTAssertEqual(count, "1")
        let malformed = try await OwnedPreviewHarness.open(); defer { malformed.close() }
        await expectFailure { _ = try await malformed.host.stage(Data(#"{"x":"one","x":"two"}"#.utf8)) }
        XCTAssertEqual(malformed.host.state, .blocked)
    }

    func testResourcesAndUnexpectedNavigationFailClosed() async throws {
        let h = try await OwnedPreviewHarness.open(); defer { h.close() }
        let result = try await h.script("""
            let violations=0;
            document.addEventListener('securitypolicyviolation', e=>{if(e.violatedDirective==='connect-src') violations++;});
            const rejected=await fetch('https://example.invalid/owned-preview-probe').then(()=>false,()=>true);
            await new Promise(r=>setTimeout(r,30));
            return String(rejected && violations>0);
            """)
        XCTAssertEqual(result, "true") // Actual CSP denial; not a network-wide proof.
        let noHandler = try await h.script("return String(!window.webkit || !window.webkit.messageHandlers || !window.webkit.messageHandlers.command);")
        XCTAssertEqual(noHandler, "true")
        _ = try? await h.script("location.href='https://example.invalid/owned-navigation-probe'; return 'requested';")
        let deadline = Date().addingTimeInterval(5)
        while h.host.state != .blocked && Date() < deadline { try await Task.sleep(for: .milliseconds(30)) }
        XCTAssertEqual(h.host.state, .blocked); XCTAssertGreaterThan(h.host.blockedNavigations, 0)
        XCTAssertTrue(h.host.webView.isHidden)
    }
}
