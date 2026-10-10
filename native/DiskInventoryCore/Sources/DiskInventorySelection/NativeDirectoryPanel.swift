import AppKit
import Foundation

// There is deliberately no usable host permit or public override. A later
// signed-host review must supply one; this module is not linked to the app.
fileprivate struct SelectedFolderHostPermit { private init() {} }
fileprivate enum ProductionSelectionGate {
    static func acquire() -> SelectedFolderHostPermit? { nil }
}

// The panel-returned URL is retained directly, never reconstructed from a path.
// Its scope owner is private to this file, thread-safe and idempotent. No choice
// constructor taking a URL is available to tests or another module.
private final class PanelScopeOwner: @unchecked Sendable {
    private let url: URL
    private let lock = NSLock()
    private var claimant: UUID?
    private var released = false
    init(_ url: URL) { self.url = url }
    func claim(_ owner: UUID) -> Bool {
        lock.lock(); defer { lock.unlock() }
        guard !released, claimant == nil else { return false }
        claimant = owner; return true
    }
    func release(_ owner: UUID) {
        lock.lock()
        let mayRelease = !released && claimant == owner
        if mayRelease { released = true }
        lock.unlock()
        if mayRelease { url.stopAccessingSecurityScopedResource() }
    }
    deinit {
        // The final owner also covers an unclaimed result abandoned by a caller.
        if !released { url.stopAccessingSecurityScopedResource() }
    }
}
private final class PanelFolderChoice: TransientFolderChoice {
    let displayName: String
    private let scope: PanelScopeOwner
    init(_ url: URL) { displayName = url.lastPathComponent; scope = PanelScopeOwner(url) }
    func claim(_ owner: UUID) -> Bool { scope.claim(owner) }
    func release(_ owner: UUID) { scope.release(owner) }
}
@MainActor
private final class PanelRequest: SelectionCancellation {
    let panel: NSOpenPanel
    private var reply: (@MainActor (FolderPickOutcome) -> Void)?
    init(panel: NSOpenPanel, reply: @escaping @MainActor (FolderPickOutcome) -> Void) {
        self.panel = panel; self.reply = reply
    }
    func cancel() { if reply != nil { panel.cancel(nil) } }
    func complete(_ response: NSApplication.ModalResponse) {
        guard let reply else { return }
        self.reply = nil
        guard response == .OK else { reply(.cancelled); return }
        // Apple documents automatically started access on successful panel URLs.
        // Every returned URL is adopted before validation so refusal releases it.
        let urls = panel.urls
        let choices = urls.map { PanelFolderChoice($0) }
        guard choices.count == 1, urls[0].isFileURL else { reply(.unavailable); return }
        reply(.selected(choices[0]))
    }
}
@MainActor
final class NativeDirectoryPanel: FolderPicking {
    private let windowProvider: @MainActor () -> NSWindow?
    private var active: PanelRequest?
    init(windowProvider: @escaping @MainActor () -> NSWindow?) { self.windowProvider = windowProvider }
    func begin(_ reply: @escaping @MainActor (FolderPickOutcome) -> Void) -> any SelectionCancellation {
        // This guard precedes even window lookup and NSOpenPanel construction.
        guard let permit = ProductionSelectionGate.acquire() else {
            reply(.unavailable); return InertSelectionRequest()
        }
        return present(permit, reply: reply)
    }
    private func present(_ permit: SelectedFolderHostPermit,
                         reply: @escaping @MainActor (FolderPickOutcome) -> Void) -> any SelectionCancellation {
        guard active == nil, let window = windowProvider() else {
            reply(.unavailable); return InertSelectionRequest()
        }
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false
        panel.allowsMultipleSelection = false; panel.canCreateDirectories = false
        panel.resolvesAliases = false; panel.treatsFilePackagesAsDirectories = false
        panel.prompt = "Choose folder"
        panel.message = "Choose one folder to review before a bounded read-only metadata snapshot."
        let operation = PanelRequest(panel: panel, reply: reply)
        active = operation
        panel.beginSheetModal(for: window) { [weak self, operation] response in
            Task { @MainActor in
                operation.complete(response)
                if self?.active === operation { self?.active = nil }
            }
        }
        return operation
    }
}
