import Foundation
import Darwin

enum SourceAdmission: Equatable { case ownedFixture, unknown, unsupported }
enum ObservationState: String { case observed, partial, cancelled, revoked, rootChanged = "root_changed", unsupported, failed }
enum ControllerState: Equatable { case ready, observing, stopping, spent, revoked }
enum ControllerBoundary: Equatable { case beforeProjection, afterProjection, beforeAdmission }

// All state is process-local. No Codable conformance, token parser or path factory exists.
final class HeldRootLease {
    let descriptor: Int32
    let selected: Metadata
    let admission: SourceAdmission
    let guardAddress: (Int32, Int32) throws -> Metadata
    private let owner: OwnedDescriptor
    private let endOwnership: () -> Void
    private let ownershipLock = NSLock()
    private let process = getpid()
    private var claimedBy: UUID?
    private var released = false

    init(owner: OwnedDescriptor, selected: Metadata, admission: SourceAdmission,
         guardAddress: @escaping (Int32, Int32) throws -> Metadata,
         endOwnership: @escaping () -> Void = {}) {
        self.owner = owner
        self.descriptor = owner.value
        self.selected = selected
        self.admission = admission
        self.guardAddress = guardAddress
        self.endOwnership = endOwnership
    }

    fileprivate func claim(_ claimant: UUID) -> Bool {
        guard getpid() == process else { return false }
        ownershipLock.lock()
        defer { ownershipLock.unlock() }
        guard !released, claimedBy == nil else { return false }
        claimedBy = claimant
        return true
    }

    // Unclaimed test-owned leases can be released directly. A claimed lease can
    // only be released by its one owning controller, never a second controller.
    func release() { release(claimant: nil) }

    fileprivate func release(claimant: UUID?) {
        guard getpid() == process else { return }
        ownershipLock.lock()
        let permitted = !released && claimedBy == claimant
        if permitted { released = true }
        ownershipLock.unlock()
        if permitted { owner.close(); endOwnership() }
    }

    deinit {
        if !released && getpid() == process { owner.close(); endOwnership() }
    }
}

final class ObservationResult {
    let state: ObservationState
    let snapshot: Data?
    fileprivate let generation: UUID

    fileprivate init(state: ObservationState, snapshot: Data?, generation: UUID) {
        self.state = state
        self.snapshot = snapshot
        self.generation = generation
    }
}

struct ObservationSeams {
    var clock: () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }
    var timestamp: () -> String = {
        let formatter = ISO8601DateFormatter()
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: Date())
    }
    var boundary: ((ControllerBoundary) throws -> Void)?
}

// Synchronisation covers lifecycle state only. One active call owns the lease and IO;
// cancellation never closes its borrowed descriptors. User callbacks run outside the lock.
final class ObservationController: @unchecked Sendable {
    private let lock = NSLock()
    private let process = getpid()
    private let ownership = UUID()
    private let io: DirectoryIO
    private let seams: ObservationSeams
    private var lease: HeldRootLease?
    private var active = false
    private var consumed = false
    private var revoked = false
    private var changed = false
    private var cancelled = false
    private var unsupported = false
    private var failed = false
    private var generation = UUID()
    private var admitted: ObservationResult?
    private var previewTaken = false

    init(lease: HeldRootLease?, io: DirectoryIO, seams: ObservationSeams = ObservationSeams()) {
        self.io = io
        self.seams = seams
        if let lease, lease.claim(ownership) { self.lease = lease }
        else { self.lease = nil; self.failed = lease != nil }
    }

    private func locked<T>(_ body: () throws -> T) rethrows -> T {
        lock.lock()
        defer { lock.unlock() }
        return try body()
    }

    var state: ControllerState {
        guard getpid() == process else { return .revoked }
        return locked {
            if active { return revoked || cancelled || failed ? .stopping : .observing }
            if revoked { return .revoked }
            return consumed ? .spent : .ready
        }
    }

    func cancel() { retire(revoke: false) }
    func revoke() { retire(revoke: true) }

    private func retire(revoke: Bool) {
        guard getpid() == process else { return }
        let released: HeldRootLease? = locked {
            if revoke { revoked = true } else { cancelled = true }
            generation = UUID()
            admitted = nil
            if active { return nil }
            consumed = true
            let old = lease
            lease = nil
            return old
        }
        released?.release(claimant: ownership)
    }

    private func eligible(_ token: UUID) -> Bool {
        active && generation == token && !revoked && !changed && !cancelled && !unsupported && !failed
    }

    func observe(label: String, cancel: (() throws -> Bool)? = nil,
                 progress: ((Int) throws -> Void)? = nil) throws -> ObservationResult {
        guard getpid() == process else { throw CoreFailure.wrongProcess }
        let token: UUID = try locked {
            guard !consumed, !active else { throw CoreFailure.alreadyConsumed }
            consumed = true
            active = true
            return generation
        }
        // Ownership is not transferred by a result, including a failed result.
        var bytes: Data?
        var partial = false
        let started = seams.clock()
        let stamp = seams.timestamp()

        var callbacksAdmitted = true
        func stop() -> Bool {
            guard locked({ eligible(token) }) else { return true }
            if callbacksAdmitted, let cancel {
                do {
                    let value = try cancel()
                    locked { cancelled = cancelled || value }
                } catch { locked { failed = true } }
            }
            return locked { !eligible(token) }
        }
        func notify(_ count: Int) {
            guard let progress, locked({ eligible(token) }) else { return }
            do { try progress(count) } catch { locked { failed = true } }
        }
        do {
            _ = try SnapshotProjection.text(Data(label.utf8), maximum: 240)
            if let lease {
                if lease.admission != .ownedFixture { locked { unsupported = true } }
                else if !stop() {
                    let walker = DescriptorWalker(io: io, clock: seams.clock, started: started, cancelled: stop, progress: notify,
                        finishCallbacks: {
                            let stopped = stop()
                            callbacksAdmitted = false
                            return !stopped
                        })
                    let inventory = try walker.observe(lease)
                    partial = inventory.partial
                    if !stop() {
                        try seams.boundary?(.beforeProjection)
                        if !stop() {
                            let id = "scan_" + String(UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased().prefix(24))
                            bytes = try SnapshotProjection.encode(inventory, label: label, stamp: stamp, scanID: id)
                            try seams.boundary?(.afterProjection)
                            _ = stop()
                        }
                    }
                }
            } else { locked { if !failed { unsupported = true } } }
        } catch CoreFailure.rootChanged { locked { changed = true } }
        catch { locked { failed = true } }

        // Retiring remains active until every descriptor and injected scope owner is released.
        let finishedLease = lease
        finishedLease?.release(claimant: ownership)
        do { try seams.boundary?(.beforeAdmission) } catch { locked { failed = true } }
        _ = stop()
        return locked {
            lease = nil
            active = false
            let outcome: ObservationState = revoked ? .revoked : changed ? .rootChanged : cancelled ? .cancelled
                : unsupported ? .unsupported : failed || bytes == nil ? .failed : partial ? .partial : .observed
            let result = ObservationResult(state: outcome,
                snapshot: outcome == .observed || outcome == .partial ? bytes : nil, generation: token)
            if result.snapshot != nil, generation == token { admitted = result }
            return result
        }
    }

    // One-use, controller-owned result admission for a future preview adapter, not a WebKit bridge.
    func takeSnapshot(_ result: ObservationResult) -> Data? {
        guard getpid() == process else { return nil }
        return locked {
            guard !active, !previewTaken, admitted === result, result.generation == generation,
                  !revoked, !cancelled else { return nil }
            previewTaken = true
            admitted = nil
            return result.snapshot
        }
    }

    deinit { lease?.release(claimant: ownership) }
}
