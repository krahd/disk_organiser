import Foundation

// Internal to an unlinked module. No URL, descriptor, bookmark or serialised
// authority is exposed by these ports. The observer is not a dependency.
protocol TransientFolderChoice: AnyObject, Sendable {
    var displayName: String { get }
    func claim(_ owner: UUID) -> Bool
    func release(_ owner: UUID)
}
@MainActor
protocol SelectionCancellation: AnyObject { func cancel() }
@MainActor
enum FolderPickOutcome { case cancelled, unavailable, selected(any TransientFolderChoice) }
@MainActor
protocol FolderPicking: AnyObject {
    func begin(_ reply: @escaping @MainActor (FolderPickOutcome) -> Void) -> any SelectionCancellation
}
// This tranche tests retirement ordering only; it does not return or manufacture
// a snapshot. A real observer adapter/result contract requires another review.
enum FolderReadOutcome: Sendable { case completed, cancelled, unavailable, failed }
@MainActor
protocol FolderReading: AnyObject {
    func begin(_ choice: any TransientFolderChoice,
               reply: @escaping @MainActor (FolderReadOutcome) -> Void) -> any SelectionCancellation
}
@MainActor
final class InertSelectionRequest: SelectionCancellation { func cancel() {} }
@MainActor
final class UnavailableFolderReader: FolderReading {
    func begin(_ choice: any TransientFolderChoice,
               reply: @escaping @MainActor (FolderReadOutcome) -> Void) -> any SelectionCancellation {
        reply(.unavailable)
        return InertSelectionRequest()
    }
}

// ARC retains this single claim through an in-flight completion even if the
// session disappears. A review-only abandoned claim retires immediately.
private final class ChoiceOwnership: Sendable {
    let choice: any TransientFolderChoice
    private let owner: UUID
    init?(_ choice: any TransientFolderChoice, owner: UUID) {
        guard choice.claim(owner) else { return nil }
        self.choice = choice; self.owner = owner
    }
    func release() { choice.release(owner) }
    deinit { choice.release(owner) }
}

@MainActor
final class FolderSelectionSession {
    enum State: Equatable, Sendable { case idle, choosing, reviewing, reading, stopping, finished, closed }
    enum Notice: Equatable { case unavailable, cancelled, failed, finished }
    private let picker: any FolderPicking
    private let reader: any FolderReading
    private let owner = UUID()
    private var generation = UUID()
    private var ownership: ChoiceOwnership?
    private var choice: (any TransientFolderChoice)? { ownership?.choice }
    private var request: (any SelectionCancellation)?
    private var closing = false
    private var cancelled = false
    private(set) var state: State = .idle
    private(set) var notice: Notice?
    var displayName: String? { choice?.displayName }
    var hasLiveChoice: Bool { choice != nil }

    init(picker: any FolderPicking, reader: (any FolderReading)? = nil) {
        self.picker = picker; self.reader = reader ?? UnavailableFolderReader()
    }
    func choose() {
        guard state == .idle || state == .finished, !closing else { return }
        let token = UUID(); generation = token; notice = nil; cancelled = false; state = .choosing
        let started = picker.begin { [weak self] outcome in
            guard let self else {
                Self.retireUnclaimed(outcome)
                return
            }
            self.picked(outcome, token: token)
        }
        // Inline completion is permitted; do not install a spent operation.
        if generation == token, state == .choosing { request = started }
        else { started.cancel() }
    }
    private static func retireUnclaimed(_ outcome: FolderPickOutcome) {
        if case .selected(let choice) = outcome {
            let disposal = UUID()
            if choice.claim(disposal) { choice.release(disposal) }
        }
    }
    private func picked(_ outcome: FolderPickOutcome, token: UUID) {
        guard token == generation, state == .choosing || state == .stopping else {
            Self.retireUnclaimed(outcome); return
        }
        request = nil
        if closing || cancelled {
            Self.retireUnclaimed(outcome)
            state = closing ? .closed : .idle; notice = .cancelled
            return
        }
        switch outcome {
        case .selected(let selected):
            guard let admitted = ChoiceOwnership(selected, owner: owner) else { state = .idle; notice = .failed; return }
            ownership = admitted; state = .reviewing
        case .cancelled: state = .idle; notice = .cancelled
        case .unavailable: state = .idle; notice = .unavailable
        }
    }
    func readMetadata() {
        guard state == .reviewing, let retirement = ownership, !closing else { return }
        let choice = retirement.choice
        let token = UUID(); generation = token; cancelled = false; state = .reading
        let started = reader.begin(choice) { [weak self, retirement] result in
            if let self { self.readFinished(result, token: token) }
            else { retirement.release() }
        }
        if generation == token, state == .reading { request = started }
        else { started.cancel() }
    }
    private func releaseChoice() {
        ownership?.release()
        ownership = nil
    }
    private func readFinished(_ result: FolderReadOutcome, token: UUID) {
        guard token == generation, state == .reading || state == .stopping else { return }
        request = nil
        // Completion means the injected worker has retired its borrowed access.
        // Cancel never closes that access while the worker is still active.
        releaseChoice()
        if closing { state = .closed; notice = .cancelled; return }
        if cancelled { state = .idle; notice = .cancelled; return }
        state = .finished
        switch result {
        case .completed: notice = .finished
        case .cancelled: notice = .cancelled
        case .unavailable: notice = .unavailable
        case .failed: notice = .failed
        }
    }
    func cancel() {
        guard state != .closed else { return }
        switch state {
        case .choosing, .reading:
            cancelled = true; state = .stopping; request?.cancel()
        case .stopping: break
        case .reviewing:
            cancelled = true; releaseChoice(); state = .idle; notice = .cancelled
        case .idle, .finished: break
        case .closed: break
        }
    }
    func close() {
        guard !closing else { return }
        closing = true
        if state == .choosing || state == .reading || state == .stopping {
            cancel()
        } else {
            releaseChoice(); state = .closed
        }
    }
}
