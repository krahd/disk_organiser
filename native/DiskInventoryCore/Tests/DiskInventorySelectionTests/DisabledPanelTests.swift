import XCTest
@testable import DiskInventorySelection

@MainActor
final class DisabledPanelTests: XCTestCase {
    func testProductionGateRejectsBeforeWindowLookupOrPanelConstruction() {
        var lookups = 0, replies = 0
        let panel = NativeDirectoryPanel(windowProvider: { lookups += 1; return nil })
        let request = panel.begin { result in
            replies += 1
            if case .unavailable = result {} else { XCTFail("Disabled gate admitted a native panel") }
        }
        request.cancel(); request.cancel()
        XCTAssertEqual(lookups, 0); XCTAssertEqual(replies, 1)
    }
    func testDisabledPanelSessionCanRetryAndCloseWithoutAcquiringChoice() {
        var lookups = 0
        let owner = FolderSelectionSession(picker: NativeDirectoryPanel(windowProvider: { lookups += 1; return nil }))
        owner.choose(); XCTAssertEqual(owner.state, .idle); XCTAssertEqual(owner.notice, .unavailable)
        owner.choose(); owner.readMetadata(); owner.close(); owner.choose()
        XCTAssertEqual(owner.state, .closed); XCTAssertFalse(owner.hasLiveChoice); XCTAssertEqual(lookups, 0)
    }
}
