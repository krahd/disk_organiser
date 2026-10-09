import Foundation
import Darwin

// A bounded worker receives a live lease, never a pathname or caller-supplied inventory.
final class DescriptorWalker {
    private let io: DirectoryIO
    private let clock: () -> TimeInterval
    private let cancelled: () -> Bool
    private let progress: (Int) -> Void
    private let finishCallbacks: () -> Bool
    private let started: TimeInterval
    private var inventory = Inventory()

    init(io: DirectoryIO, clock: @escaping () -> TimeInterval, started: TimeInterval,
         cancelled: @escaping () -> Bool, progress: @escaping (Int) -> Void, finishCallbacks: @escaping () -> Bool) {
        self.io = io
        self.clock = clock
        self.cancelled = cancelled
        self.progress = progress
        self.finishCallbacks = finishCallbacks
        self.started = started
    }

    private func interrupted() -> Bool {
        if inventory.stopReason != nil { return true }
        if cancelled() { inventory.stopReason = "cancelled" }
        else if clock() - started >= Bounds.seconds { inventory.stopReason = "time_limit" }
        return inventory.stopReason != nil
    }

    private func terminalBoundary() -> Bool {
        if cancelled() { return false }
        if inventory.stopReason == nil && clock() - started >= Bounds.seconds { inventory.stopReason = "time_limit" }
        return true
    }

    func observe(_ lease: HeldRootLease) throws -> Inventory {
        guard !interrupted() else { throw CoreFailure.unavailable }
        let scanner = OwnedDescriptor(adopting: try io.duplicate(lease.descriptor), io: io)
        defer { scanner.close() }
        guard !interrupted() else { throw CoreFailure.unavailable }
        let root = try io.metadata(scanner.value)
        guard !interrupted() else { throw CoreFailure.unavailable }
        let selected = try io.metadata(lease.descriptor)
        guard !interrupted() else { throw CoreFailure.unavailable }
        let address = try lease.guardAddress(lease.descriptor, scanner.value)
        guard !interrupted() else { throw CoreFailure.unavailable }
        guard root.fingerprint.sameDirectory(as: lease.selected.fingerprint),
              selected.fingerprint.sameDirectory(as: root.fingerprint),
              address.fingerprint.sameDirectory(as: root.fingerprint),
              selected.fingerprint == root.fingerprint, address.fingerprint == root.fingerprint else {
            throw CoreFailure.rootChanged
        }
        inventory.entries.append(InventoryEntry(path: Data(".".utf8), metadata: root))
        try visit(scanner.value, relative: Data(".".utf8), depth: 0, rootDevice: root.fingerprint.device, index: 0)
        // Progress is an external callback and must precede terminal root admission.
        progress(inventory.entries.count)
        // Last user cancellation callback precedes the guard. Later boundaries poll
        // only controller-latched state; direct cancel/revoke remain effective.
        guard finishCallbacks() else { return inventory }
        // A time stop still requires fresh terminal root admission. Cancellation does not.
        guard terminalBoundary() else { return inventory }
        let finalScanner = try io.metadata(scanner.value)
        guard terminalBoundary() else { return inventory }
        let finalSelected = try io.metadata(lease.descriptor)
        guard terminalBoundary() else { return inventory }
        let finalAddress = try lease.guardAddress(lease.descriptor, scanner.value)
        guard terminalBoundary() else { return inventory }
        guard finalScanner.fingerprint == root.fingerprint,
              finalSelected.fingerprint == root.fingerprint,
              finalAddress.fingerprint == root.fingerprint else { throw CoreFailure.rootChanged }
        guard inventory.entries[0].status == .observed else { throw CoreFailure.unavailable }
        inventory.reconcileAliases()
        return inventory
    }

    private func visit(_ descriptor: Int32, relative: Data, depth: Int, rootDevice: Int64, index: Int) throws {
        if interrupted() { return }
        if depth >= Bounds.depth {
            inventory.exclude("depth_limit")
            return
        }
        let names: [Data]
        do {
            let batch = try io.names(descriptor, interrupted: interrupted)
            if interrupted() { return }
            switch batch {
            case .overLimit: inventory.exclude("directory_entry_limit"); return
            case .interrupted: return
            case .names(let gathered): names = gathered
            }
        } catch let failure as CoreFailure {
            if case .filesystem = failure { inventory.markError(at: index, failure); return }
            throw failure
        }
        for name in names {
            if interrupted() { return }
            if inventory.entries.count >= Bounds.entries {
                inventory.stopReason = "entry_limit"
                return
            }
            let path = relative == Data(".".utf8) ? name : relative + Data([47]) + name
            // Validate every admitted name before using it in a relative syscall or projection.
            _ = try SnapshotProjection.path(path)
            let observed: Metadata
            do {
                observed = try io.metadata(parent: descriptor, name: name)
                if interrupted() { return }
            } catch let failure as CoreFailure {
                guard case .filesystem = failure else { throw failure }
                inventory.entries.append(InventoryEntry(path: path))
                inventory.markError(at: inventory.entries.count - 1, failure)
                continue
            }
            let childIndex = inventory.entries.count
            inventory.entries.append(InventoryEntry(path: path, metadata: observed))
            let kind = observed.fingerprint.kind
            if kind == .symlink || kind == .special {
                inventory.entries[childIndex].status = .unsupported
                inventory.exclude(kind.rawValue + "_not_followed")
            } else if observed.knownPlaceholder || name.suffix(7) == Data(".icloud".utf8) {
                inventory.entries[childIndex].status = .unsupported
                inventory.exclude("known_placeholder_marker")
            } else if observed.fingerprint.device != rootDevice {
                inventory.entries[childIndex].status = .unsupported
                inventory.exclude("filesystem_boundary")
            } else if kind == .directory {
                try descend(parent: descriptor, name: name, relative: path, depth: depth,
                            rootDevice: rootDevice, index: childIndex, observed: observed)
            }
            if interrupted() { return }
            progress(inventory.entries.count)
        }
    }

    private func descend(parent: Int32, name: Data, relative: Data, depth: Int,
                         rootDevice: Int64, index: Int, observed: Metadata) throws {
        if interrupted() { return }
        do {
            let child = OwnedDescriptor(adopting: try io.openDirectory(parent: parent, name: name), io: io)
            defer { child.close() }
            if interrupted() { return }
            let opened = try io.metadata(child.value)
            if interrupted() { return }
            if opened.fingerprint.device != rootDevice {
                inventory.entries[index].status = .unsupported
                inventory.exclude("filesystem_boundary")
            } else if opened.fingerprint != observed.fingerprint {
                inventory.entries[index].status = .stale
                inventory.exclude("changed_before_traversal")
            } else {
                let subtree = inventory.entries.count
                try visit(child.value, relative: relative, depth: depth + 1, rootDevice: rootDevice, index: index)
                if !terminalBoundary() { return }
                let after = try io.metadata(child.value)
                if !terminalBoundary() { return }
                if after.fingerprint != observed.fingerprint {
                    inventory.entries[index].status = .stale
                    inventory.exclude("changed_during_traversal")
                    inventory.invalidate(from: subtree)
                }
            }
        } catch let failure as CoreFailure {
            guard case .filesystem = failure else { throw failure }
            inventory.markError(at: index, failure)
        }
    }
}
