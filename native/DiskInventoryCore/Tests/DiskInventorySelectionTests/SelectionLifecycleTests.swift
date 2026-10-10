import XCTest
import Foundation
@testable import DiskInventorySelection

// Memory-owned doubles only. None accepts a real URL, descriptor or filesystem
// path; these lifecycles cannot create an observer lease or a native grant.
private final class Choice: TransientFolderChoice, @unchecked Sendable {
    let displayName = "Owned lifecycle example"
    private let lock = NSLock()
    private var owner: UUID?
    private var releaseCount = 0
    var releases: Int { lock.lock(); defer { lock.unlock() }; return releaseCount }
    func claim(_ owner: UUID) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard self.owner == nil, releaseCount == 0 else { return false }
        self.owner = owner; return true
    }
    func release(_ owner: UUID) {
        lock.lock(); defer { lock.unlock() }
        guard self.owner == owner, releaseCount == 0 else { return }
        releaseCount += 1
    }
}
@MainActor
private final class Request: SelectionCancellation {
    private(set) var cancellations = 0
    var onCancel: (() -> Void)?
    func cancel() { cancellations += 1; onCancel?() }
}
@MainActor
private final class Picker: FolderPicking {
    private(set) var replies: [@MainActor (FolderPickOutcome) -> Void] = []
    private(set) var requests: [Request] = []
    var inline: FolderPickOutcome?
    func begin(_ reply: @escaping @MainActor (FolderPickOutcome) -> Void) -> any SelectionCancellation {
        let request = Request(); replies.append(reply); requests.append(request)
        if let inline { reply(inline) }
        return request
    }
}
@MainActor
private final class Reader: FolderReading {
    private(set) var replies: [@MainActor (FolderReadOutcome) -> Void] = []
    private(set) var requests: [Request] = []
    var inline: FolderReadOutcome?
    func begin(_ choice: any TransientFolderChoice,
               reply: @escaping @MainActor (FolderReadOutcome) -> Void) -> any SelectionCancellation {
        let request = Request(); replies.append(reply); requests.append(request)
        if let inline { reply(inline) }
        return request
    }
}

@MainActor
final class SelectionLifecycleTests: XCTestCase {
    func testChooseReviewCancelReleasesExactlyOnce() {
        let picker = Picker(), choice = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); picker.replies[0](.selected(choice))
        XCTAssertEqual(owner.state, .reviewing); XCTAssertEqual(owner.displayName, choice.displayName)
        XCTAssertEqual(choice.releases, 0)
        owner.cancel(); owner.cancel(); owner.close()
        XCTAssertEqual(choice.releases, 1); XCTAssertFalse(owner.hasLiveChoice); XCTAssertEqual(owner.state, .closed)
    }
    func testPanelCancellationAndUnavailableAreDistinctNonAdmissions() {
        for outcome in [FolderPickOutcome.cancelled, .unavailable] {
            let picker = Picker(), owner = FolderSelectionSession(picker: picker)
            owner.choose(); picker.replies[0](outcome)
            XCTAssertEqual(owner.state, .idle); XCTAssertFalse(owner.hasLiveChoice)
            if case .cancelled = outcome { XCTAssertEqual(owner.notice, .cancelled) }
            else { XCTAssertEqual(owner.notice, .unavailable) }
        }
    }
    func testDuplicateChooseDoesNotStartAnotherPicker() {
        let picker = Picker(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); owner.choose(); owner.readMetadata()
        XCTAssertEqual(picker.replies.count, 1); XCTAssertEqual(owner.state, .choosing)
        owner.cancel(); owner.choose()
        XCTAssertEqual(owner.state, .stopping); XCTAssertEqual(picker.replies.count, 1)
        picker.replies[0](.cancelled); owner.choose()
        XCTAssertEqual(picker.replies.count, 2)
    }
    func testCancelledPickerLateSuccessRetiresRatherThanAdmits() {
        let picker = Picker(), choice = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); owner.cancel(); XCTAssertEqual(picker.requests[0].cancellations, 1)
        picker.replies[0](.selected(choice)); picker.replies[0](.selected(choice))
        XCTAssertEqual(owner.state, .idle); XCTAssertEqual(choice.releases, 1); XCTAssertFalse(owner.hasLiveChoice)
    }
    func testCloseWhileChoosingWaitsForRetirementAndNeverReopens() {
        let picker = Picker(), choice = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); owner.close(); owner.close(); owner.choose()
        XCTAssertEqual(owner.state, .stopping); XCTAssertEqual(picker.requests[0].cancellations, 1)
        picker.replies[0](.selected(choice)); owner.choose()
        XCTAssertEqual(owner.state, .closed); XCTAssertEqual(choice.releases, 1); XCTAssertEqual(picker.replies.count, 1)
    }
    func testDuplicateSelectedCallbackCannotReleaseCurrentChoice() {
        let picker = Picker(), choice = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); picker.replies[0](.selected(choice)); picker.replies[0](.selected(choice))
        XCTAssertEqual(owner.state, .reviewing); XCTAssertEqual(choice.releases, 0)
        owner.close(); XCTAssertEqual(choice.releases, 1)
    }
    func testAnotherOwnerCannotAcquireOrRetireHeldChoice() {
        let picker = Picker(), other = Picker(), choice = Choice()
        let first = FolderSelectionSession(picker: picker), second = FolderSelectionSession(picker: other)
        first.choose(); picker.replies[0](.selected(choice)); second.choose(); other.replies[0](.selected(choice))
        XCTAssertEqual(second.notice, .failed); XCTAssertEqual(choice.releases, 0)
        second.close(); XCTAssertEqual(choice.releases, 0); first.close(); XCTAssertEqual(choice.releases, 1)
    }
    func testOlderPickerResultDoesNotReplaceANewerFlight() {
        let picker = Picker(), stale = Choice(), latest = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); picker.replies[0](.cancelled); owner.choose()
        picker.replies[0](.selected(stale)); XCTAssertEqual(stale.releases, 1); XCTAssertEqual(owner.state, .choosing)
        picker.replies[1](.selected(latest)); XCTAssertEqual(latest.releases, 0); owner.close()
        XCTAssertEqual(latest.releases, 1)
    }
    func testReadCompletionReleasesBeforePublishingTerminalState() {
        let picker = Picker(), reader = Reader(), choice = Choice(), owner = FolderSelectionSession(picker: picker, reader: reader)
        owner.choose(); picker.replies[0](.selected(choice)); owner.readMetadata(); owner.readMetadata()
        XCTAssertEqual(reader.replies.count, 1); XCTAssertEqual(choice.releases, 0)
        reader.replies[0](.completed)
        XCTAssertEqual(owner.state, .finished); XCTAssertEqual(owner.notice, .finished); XCTAssertEqual(choice.releases, 1)
        reader.replies[0](.completed); XCTAssertEqual(choice.releases, 1)
    }
    func testReadCancelRetainsBorrowedChoiceUntilWorkerCompletion() {
        let picker = Picker(), reader = Reader(), choice = Choice(), owner = FolderSelectionSession(picker: picker, reader: reader)
        owner.choose(); picker.replies[0](.selected(choice)); owner.readMetadata(); owner.cancel(); owner.choose()
        XCTAssertEqual(owner.state, .stopping); XCTAssertEqual(choice.releases, 0); XCTAssertEqual(reader.requests[0].cancellations, 1)
        // The old panel completion cannot end a newer, retiring read flight.
        picker.replies[0](.selected(choice)); XCTAssertEqual(owner.state, .stopping); XCTAssertEqual(choice.releases, 0)
        reader.replies[0](.completed)
        XCTAssertEqual(owner.state, .idle); XCTAssertEqual(owner.notice, .cancelled); XCTAssertEqual(choice.releases, 1)
    }
    func testCloseDuringReadDiscardsLateSuccessAndWaitsForRelease() {
        let picker = Picker(), reader = Reader(), choice = Choice(), owner = FolderSelectionSession(picker: picker, reader: reader)
        owner.choose(); picker.replies[0](.selected(choice)); owner.readMetadata(); owner.close()
        XCTAssertEqual(owner.state, .stopping); XCTAssertEqual(choice.releases, 0)
        reader.replies[0](.completed)
        XCTAssertEqual(owner.state, .closed); XCTAssertEqual(owner.notice, .cancelled); XCTAssertEqual(choice.releases, 1)
        owner.choose(); XCTAssertEqual(picker.replies.count, 1)
    }
    func testReadFailureAndUnavailableReleaseWithoutSnapshotClaim() {
        for result in [FolderReadOutcome.failed, .unavailable, .cancelled] {
            let picker = Picker(), reader = Reader(), choice = Choice(), owner = FolderSelectionSession(picker: picker, reader: reader)
            owner.choose(); picker.replies[0](.selected(choice)); owner.readMetadata(); reader.replies[0](result)
            XCTAssertEqual(owner.state, .finished); XCTAssertNotEqual(owner.notice, .finished); XCTAssertEqual(choice.releases, 1)
        }
    }
    func testInlinePickerAndReaderCompletionsDoNotLeaveLiveRequests() {
        let picker = Picker(), reader = Reader(), choice = Choice()
        picker.inline = .selected(choice); reader.inline = .completed
        let owner = FolderSelectionSession(picker: picker, reader: reader)
        owner.choose(); XCTAssertEqual(owner.state, .reviewing)
        owner.readMetadata(); XCTAssertEqual(owner.state, .finished); XCTAssertEqual(choice.releases, 1)
        owner.close(); XCTAssertEqual(owner.state, .closed)
    }
    func testDefaultReaderIsUnavailableAndNeverCreatesAnObservation() {
        let picker = Picker(), choice = Choice(), owner = FolderSelectionSession(picker: picker)
        owner.choose(); picker.replies[0](.selected(choice)); owner.readMetadata()
        XCTAssertEqual(owner.notice, .unavailable); XCTAssertEqual(choice.releases, 1); XCTAssertFalse(owner.hasLiveChoice)
    }
    func testAbandonedReviewSessionRetiresItsUnborrowedChoice() {
        let picker = Picker(), choice = Choice()
        var owner: FolderSelectionSession? = FolderSelectionSession(picker: picker)
        owner?.choose(); picker.replies[0](.selected(choice)); owner = nil
        XCTAssertEqual(choice.releases, 1)
    }
    func testAbandonedSessionLatePickerResultIsRetired() {
        let picker = Picker(), choice = Choice()
        var owner: FolderSelectionSession? = FolderSelectionSession(picker: picker)
        owner?.choose(); owner = nil; picker.replies[0](.selected(choice))
        XCTAssertEqual(choice.releases, 1)
    }
    func testAbandonedSessionKeepsBorrowedChoiceUntilReadCompletion() {
        let picker = Picker(), reader = Reader(), choice = Choice()
        var owner: FolderSelectionSession? = FolderSelectionSession(picker: picker, reader: reader)
        owner?.choose(); picker.replies[0](.selected(choice)); owner?.readMetadata(); owner = nil
        XCTAssertEqual(choice.releases, 0); reader.replies[0](.completed); XCTAssertEqual(choice.releases, 1)
    }
}
