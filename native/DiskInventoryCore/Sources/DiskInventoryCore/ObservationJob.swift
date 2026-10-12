import Foundation

// Internal worker for an already admitted controller. No path, URL, bookmark or
// source constructor is exposed. The ordinary application does not link this module.
final class ObservationJob: @unchecked Sendable {
    enum Failure: Error { case alreadyStarted, invalidProgress }
    struct Result: Sendable {
        let state: ObservationState
        let snapshot: Data?
    }
    struct Seams: Sendable {
        var afterProgress: (@Sendable (Int) -> Void)?
        var beforePublication: (@Sendable () -> Void)?
    }
    private let controller: ObservationController
    private let label: String
    private let seams: Seams
    private let lock = NSLock()
    private var started = false
    private var terminal = false
    private var cancelled = false
    private var latest: Int?
    private var greatestCount = 0
    private var completion: CheckedContinuation<Result, any Error>?

    init(controller: ObservationController, label: String, seams: Seams = Seams()) {
        self.controller = controller; self.label = label; self.seams = seams
    }
    private func locked<T>(_ body: () throws -> T) rethrows -> T {
        lock.lock(); defer { lock.unlock() }
        return try body()
    }
    // A cancellation request is just memory. Only the worker enters the observer,
    // including its existing cooperative cancel polls and descriptor retirement.
    // This avoids publishing before an off-thread pre-start release has finished.
    func cancel() {
        locked { if !terminal { cancelled = true; latest = nil } }
    }
    private var cancellationRequested: Bool { locked { cancelled } }
    func takeProgress() -> Int? {
        locked {
            guard !terminal, !cancelled else { return nil }
            let value = latest; latest = nil; return value
        }
    }
    // Internal count-only port also permits direct boundary tests; no I/O authority.
    func recordProgress(_ count: Int) throws {
        try locked {
            guard !terminal, (0...2_000).contains(count), count >= greatestCount else { throw Failure.invalidProgress }
            greatestCount = count
            if !cancelled { latest = count }
        }
    }
    func run() async throws -> Result {
        // Only the admitted caller may install a cancellation handler. A refused
        // caller, including an already-cancelled task, cannot cancel this worker.
        let admitted = locked {
            guard !started else { return false }
            started = true; return true
        }
        guard admitted else { throw Failure.alreadyStarted }
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                locked { completion = continuation }
                // One closure per job, never one task per progress callback. The
                // queue owns this closure until completion; the job owns no task.
                DispatchQueue(label: "DiskInventory.owned-observation").async { self.observe() }
            }
        } onCancel: { self.cancel() }
    }
    private func observe() {
        let result: Result
        do {
            let observed = try controller.observe(label: label,
                cancel: { self.cancellationRequested }, progress: { count in
                    try self.recordProgress(count); self.seams.afterProgress?(count)
                })
            let bytes = controller.takeSnapshot(observed)
            // Only the core can admit bytes, after retiring every source owner.
            let expected = observed.state == .observed || observed.state == .partial
            result = Result(state: expected && bytes == nil ? .failed : observed.state, snapshot: bytes)
        } catch { result = Result(state: .failed, snapshot: nil) }
        seams.beforePublication?()
        let delivery: (CheckedContinuation<Result, any Error>?, Result) = locked {
            // This is the job's terminal linearisation. Cancel before here wins;
            // cancel after here cannot rewrite a delivered immutable value.
            let value = cancelled ? Result(state: .cancelled, snapshot: nil) : result
            terminal = true; latest = nil
            let waiter = completion; completion = nil
            return (waiter, value)
        }
        delivery.0?.resume(returning: delivery.1)
    }
}
