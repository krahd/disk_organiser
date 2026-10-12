import Foundation
import Darwin

struct ObservedDenial: Equatable, Sendable {
    let operation: String
    let code: Int32
}

// Pure publication/classification rules shared with the authored UI test
// module. No descriptor or grant operation is performed here.
enum ProbePolicy {
    static let ancestors: Set<String> = ["root-open", "ancestor-open"]
    static let selectedOperations = ancestors.union(["selected-content-open", "selected-content-read"])
    static let activeOperations = [
        ancestors.union(["sibling-read-open"]),
        ancestors.union(["parent-stream-open", "parent-entry-read"]),
        ancestors.union(["selected-write-open"]),
        ancestors.union(["selected-create-exclusive"]),
    ]
    static func denial(_ error: Error, operations: Set<String>) -> ObservedDenial? {
        guard case ProbeFailure.syscall(let operation, let code) = error,
              operations.contains(operation), code == EACCES || code == EPERM else { return nil }
        return ObservedDenial(operation: operation, code: code)
    }
    static func completedOutcome(cancelAccepted: Bool) -> String {
        // The worker's terminal lock controls ownership. A later visible Cancel
        // accepted before main-actor publication still suppresses success.
        cancelAccepted ? "read-cancelled" : "passed"
    }
}
