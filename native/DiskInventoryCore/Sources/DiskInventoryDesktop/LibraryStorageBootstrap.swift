import Foundation

// Availability is not a Save result. This owner never captures/acknowledges a
// catalogue and never retries an uncertain version write.
@MainActor
final class LibraryStorageBootstrap {
    enum State: Equatable { case unavailable, unresolved, resolving, missing, ready, blocked, retiring, retired }
    private let provider: (any LibraryStorageProviding)?
    private(set) var storage: LibraryStorage?
    private(set) var state: State
    private(set) var failureMessage: String?
    private var cancellation: ApplicationLibraryCancellation?
    private var generation = UUID()
    var changed: (() -> Void)?
    var enabled: Bool { state != .unavailable && state != .retired }
    var resolving: Bool { state == .resolving }
    var cancellationRequested: Bool { cancellation?.isCancelled == true }
    let applicationData: Bool

    init(owned: OwnedLibraryInjection?, provider: (any LibraryStorageProviding)?) throws {
        guard owned == nil || provider == nil else { throw LibraryStorageFailure.invalidScope }
        self.provider = provider; applicationData = provider != nil
        storage = try owned?.claim()
        state = storage != nil ? .ready : provider != nil ? .unresolved : .unavailable
    }
    func obtain(_ intent: ApplicationLibraryIntent) async throws -> LibraryStorage? {
        if let storage, state == .ready { return storage }
        guard enabled, !resolving, let provider else { throw LibraryStorageFailure.unavailable }
        let cancellation = ApplicationLibraryCancellation(), token = generation
        self.cancellation = cancellation; failureMessage = nil; state = .resolving; changed?()
        do {
            let result = try await provider.resolve(intent, cancellation: cancellation)
            if let result { try result.claimInteractionOwner() }
            guard generation == token, state != .retired, !cancellation.isCancelled else {
                if let result { await result.close() }
                throw CancellationError()
            }
            if let result {
                storage = result; state = .ready
            } else { state = .missing }
            self.cancellation = nil; changed?()
            return result
        } catch {
            if generation == token, state != .retired {
                state = cancellation.isCancelled ? .unresolved : .blocked
                if cancellation.isCancelled {
                    failureMessage = "Storage preparation cancelled. Current work is retained; app-private setup data may remain."
                } else if case ApplicationLibraryFailure.inUse = error {
                    failureMessage = "This saved library is in use by another app instance. Close that instance, then try again. Current work stays here."
                } else if case ApplicationLibraryFailure.incompleteSetup = error {
                    failureMessage = "Saved-library setup is incomplete or unrecognised. Existing data was left untouched; this catalogue has not been saved."
                } else {
                    failureMessage = "Saved library storage could not be opened safely. Current work is retained; setup data may remain. You can keep working or retry."
                }
                self.cancellation = nil; changed?()
            }
            throw error
        }
    }
    func cancel() { cancellation?.cancel() }
    func releasePreparedStorage() async {
        guard applicationData, state == .ready, let storage else { return }
        let token = generation
        self.storage = nil; state = .retiring; changed?()
        await storage.close()
        if generation == token, state != .retired { state = .unresolved; changed?() }
    }
    func retire() {
        guard state != .retired else { return }
        generation = UUID(); cancellation?.cancel(); state = .retired
        let storage = storage, provider = provider
        self.storage = nil
        // Actor serialization waits for earlier filesystem work before releasing
        // the lease. No successor bootstrap is admitted after this state fence.
        Task { if let storage { await storage.close() }; await provider?.retire() }
        changed?()
    }
}
