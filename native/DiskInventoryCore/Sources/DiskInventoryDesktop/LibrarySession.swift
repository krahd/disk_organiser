import Foundation

struct LibraryChoice: Equatable, Sendable {
    let id: String
    let title: String
    let detail: String
}

// Data provider, never a serialised filesystem capability. The application ships
// only fixed bundled examples. Owned-directory providers exist in tests only.
@MainActor
protocol LibrarySource: AnyObject {
    var choices: [LibraryChoice] { get }
    var scopeDescription: String { get }
    func prepare(_ choice: LibraryChoice) async throws -> Data
    func cancel()
}

@MainActor
final class BundledLibraryExamples: LibrarySource {
    let choices = [
        LibraryChoice(id: "working", title: "Creative projects", detail: "A complete recorded example with photos and project folders."),
        LibraryChoice(id: "archive", title: "Archive collection", detail: "A partial recorded example with limits that remain visible."),
    ]
    let scopeDescription = "Built-in example data only. No folder or drive will be read. Recorded dates and contents belong to examples, not your current storage."
    func prepare(_ choice: LibraryChoice) async throws -> Data {
        guard choices.contains(choice), let root = Bundle.module.resourceURL else { throw CataloguePreviewHost.Failure.unavailable }
        try Task.checkCancellation()
        // The identifier comes from the fixed allowlist, never text/JSON/arguments.
        let file = root.appendingPathComponent("Examples", isDirectory: true).appendingPathComponent(choice.id + ".json")
        let bytes = try Data(contentsOf: file, options: .uncached)
        guard !bytes.isEmpty, bytes.count <= 1_048_576 else { throw CataloguePreviewHost.Failure.invalidPayload }
        try Task.checkCancellation()
        return bytes
    }
    func cancel() {}
}

@MainActor
final class LibrarySession {
    enum State: Equatable { case ready, choosing, scope, preparing, stopping, reviewing, finishing, failed, closed }
    let host: CataloguePreviewHost
    let source: any LibrarySource
    private(set) var state = State.ready
    private(set) var choice: LibraryChoice?
    private(set) var message = "Development preview. Explore example records; real-folder reading is not connected."
    private(set) var hasTemporaryRecords = false
    var changed: (() -> Void)?
    private var generation = UUID()
    private var work: Task<Void, Never>?

    init(host: CataloguePreviewHost, source: any LibrarySource) { self.host = host; self.source = source }
    private func show(_ next: State, _ text: String) { state = next; message = text; changed?() }
    func choose() {
        guard state == .ready, host.state == .ready else { return }
        choice = nil
        show(.choosing, "Choose an example to review. No source folder access is available.")
    }
    func select(_ item: LibraryChoice) {
        guard state == .choosing, source.choices.contains(item) else { return }
        choice = item
        show(.scope, source.scopeDescription)
    }
    func prepare() {
        guard state == .scope, let selected = choice, source.choices.contains(selected) else { return }
        let token = generation
        show(.preparing, "Preparing the selected example. Nothing has been added yet.")
        work = Task { @MainActor [weak self] in
            guard let self else { return }
            guard generation == token, state == .preparing, !Task.isCancelled else { finishStopped(); return }
            do {
                let bytes = try await source.prepare(selected)
                guard generation == token, state == .preparing, !Task.isCancelled else { finishStopped(); return }
                _ = try await host.stage(bytes)
                // A close/cancel may retire this generation while WebKit replies.
                guard generation == token, state == .preparing else {
                    var committed = false
                    if host.state == .staged || host.state == .staging { committed = try await host.retire() == "committed" }
                    if committed { hasTemporaryRecords = true }
                    finishStopped(committed: committed); return
                }
                show(.reviewing, "Review the snapshot below. Add or Cancel, then choose Done reviewing. This library is temporary.")
            } catch {
                if generation != token || Task.isCancelled { finishStopped() }
                else if host.state == .ready { show(.ready, "The example could not be prepared. Existing records are unchanged.") }
                else { show(.failed, "The catalogue view stopped safely. Close this preview and start a new one; no saved library was changed.") }
            }
            work = nil
        }
    }
    private func finishStopped(committed: Bool = false) {
        work = nil
        guard state != .closed else { return }
        if host.state == .ready { show(.ready, committed ? "Snapshot was added before cancellation; it remains in this temporary library." : "Preparation cancelled. Existing records are unchanged.") }
        else { show(.failed, "The catalogue view stopped safely. Close this preview and start a new one.") }
    }
    func cancel() {
        switch state {
        case .choosing, .scope:
            choice = nil; show(.ready, "Selection cancelled. Nothing was read or added.")
        case .preparing:
            generation = UUID(); source.cancel(); work?.cancel()
            show(.stopping, "Stopping preparation. Waiting for the current operation to return.")
        default: break
        }
    }
    func finishReview() {
        guard state == .reviewing else { return }
        let token = generation
        show(.finishing, "Finishing this snapshot review…")
        work = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let outcome = try await host.retire()
                guard token == generation, state != .closed else { return }
                if outcome == "committed" { hasTemporaryRecords = true }
                show(.ready, outcome == "committed" ? "Snapshot added to this temporary library. Explore another example or compare your records below." : "Snapshot review cancelled. Existing records are unchanged.")
            } catch {
                guard state != .closed else { return }
                show(.failed, "The catalogue view stopped safely. No save is available in this preview.")
            }
            work = nil
        }
    }
    func close() {
        guard state != .closed else { return }
        generation = UUID(); source.cancel(); work?.cancel(); host.close()
        show(.closed, "Preview closed. No folder access or saved library was retained.")
        changed = nil
    }
}
