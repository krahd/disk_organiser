import Foundation

enum ProbeWorkResult: Sendable {
    case completed([ObservedDenial])
    case cancelled([ObservedDenial])
    case failed(String)
}

// The worker owns all descriptor operations. Cancel signals memory only; the
// owner must wait for terminal delivery before retiring the panel scope.
final class ProbeWork: @unchecked Sendable {
    private let condition = NSCondition()
    private var started = false
    private var cancelled = false
    private var proceed = false
    private var holding = false
    private var terminal = false

    var isHolding: Bool {
        condition.lock(); defer { condition.unlock() }
        return holding && !terminal && !cancelled
    }
    func cancel() {
        condition.lock()
        if !terminal { cancelled = true; condition.broadcast() }
        condition.unlock()
    }
    func resume() {
        condition.lock()
        if holding && !terminal { proceed = true; condition.broadcast() }
        condition.unlock()
    }
    private func isCancelled() -> Bool {
        condition.lock(); defer { condition.unlock() }; return cancelled
    }
    func start(fixture: ProbeFixture, onHolding: @escaping @Sendable () -> Void,
               completion: @escaping @Sendable (ProbeWorkResult) -> Void) -> Bool {
        condition.lock()
        guard !started else { condition.unlock(); return false }
        started = true
        condition.unlock()
        DispatchQueue(label: "org.diskorganiser.owned-selection-probe.read").async { [self] in
            var denials: [ObservedDenial] = []
            var result = ProbeWorkResult.cancelled([])
            do {
                if !isCancelled() {
                    try ProbeMatrix.selectedAllowed(fixture) {
                        if isCancelled() { throw ProbeFailure.refused("work-cancelled") }
                        denials = try ProbeMatrix.outsideAndWriteDenied(fixture, stopped: isCancelled)
                        if isCancelled() { throw ProbeFailure.refused("work-cancelled") }
                        condition.lock(); holding = true; condition.unlock()
                        onHolding()
                        let deadline = Date(timeIntervalSinceNow: 5)
                        condition.lock()
                        while !cancelled && !proceed {
                            if !condition.wait(until: deadline) { break }
                        }
                        let didProceed = proceed
                        let didCancel = cancelled
                        holding = false
                        condition.unlock()
                        if !didProceed && !didCancel { throw ProbeFailure.refused("held-read-deadline") }
                        if didCancel { throw ProbeFailure.refused("work-cancelled") }
                    }
                    result = .completed(denials)
                }
            } catch ProbeFailure.refused("work-cancelled") {
                result = .cancelled(denials)
            } catch {
                result = .failed(Self.failureCode(error))
            }
            // All synchronous ledger scopes have returned, including cleanup.
            // This lock defines terminal ordering; a later Cancel cannot rewrite
            // a delivered result. A failure never becomes a cancellation pass.
            condition.lock()
            if cancelled, case .completed = result { result = .cancelled(denials) }
            terminal = true; holding = false
            condition.unlock()
            completion(result)
        }
        return true
    }

    static func failureCode(_ error: Error) -> String {
        switch error {
        case ProbeFailure.refused(let reason): return "refused:\(reason)"
        case ProbeFailure.syscall(let operation, let code): return "syscall:\(operation):\(code)"
        case ProbeFailure.cleanup(let operation, let code): return "cleanup:\(operation):\(code)"
        default: return "unexpected-error"
        }
    }
}

// Constructed only by the actual panel callback in this quarantined host.
// The original URL is kept; no bookmark, path recreation or extra scope start.
final class ProbePanelScope: @unchecked Sendable {
    private let url: URL
    private let lock = NSLock()
    private var retired = false

    init(panelURL: URL) { url = panelURL }
    func matches(_ expected: String) -> Bool { url.isFileURL && url.path == expected }
    func retire() {
        lock.lock()
        let shouldStop = !retired
        retired = true
        lock.unlock()
        if shouldStop { url.stopAccessingSecurityScopedResource() }
    }
    deinit { retire() }
}
