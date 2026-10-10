import AppKit
import Foundation

@MainActor
final class LibraryActionButton: NSButton {
    private let actionBody: () -> Void
    init(_ title: String, identifier: String, action: @escaping () -> Void) {
        actionBody = action
        super.init(frame: .zero)
        self.title = title; bezelStyle = .rounded; target = self
        self.action = #selector(performAction)
        self.identifier = NSUserInterfaceItemIdentifier(identifier)
        setAccessibilityIdentifier(identifier)
    }
    required init?(coder: NSCoder) { return nil }
    @objc private func performAction() { actionBody() }
}

@MainActor
final class LibraryWindowController: NSObject, NSWindowDelegate {
    let window: NSWindow
    let session: LibrarySession
    let interaction: LibraryInteraction
    let chrome = NSStackView()
    private let status = NSTextField(wrappingLabelWithString: "")
    private let actions = NSStackView()
    private var panel: NSWindow?
    private var panelState: LibrarySession.State?
    private var closing = false
    private var closeQuestion = false
    private var closeDiscardButton: NSButton?
    private var savedPanel: LibrarySavedPanel?
    private var startupReady: Bool
    private var lastSessionState: LibrarySession.State?
    private var lastFlight: LibraryInteraction.Flight?
    var didClose: (() -> Void)?
    private(set) var exploreButton: LibraryActionButton!
    private(set) var doneButton: LibraryActionButton!
    private(set) var cancelButton: LibraryActionButton!
    private(set) var saveButton: LibraryActionButton!
    private(set) var openButton: LibraryActionButton!
    private(set) var checkButton: LibraryActionButton!
    private(set) var cancelSaveButton: LibraryActionButton!

    init(session: LibrarySession, startReady: Bool = true, injection: OwnedLibraryInjection? = nil, provider: (any LibraryStorageProviding)? = nil) throws {
        interaction = try LibraryInteraction(session: session, injection: injection, provider: provider)
        self.session = session
        startupReady = startReady
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1100, height: 850),
            styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        super.init()
        window.title = "Disk Organiser · development preview"
        window.contentMinSize = NSSize(width: 680, height: 540)
        window.isReleasedWhenClosed = false; window.delegate = self
        let content = NSView(); window.contentView = content
        chrome.orientation = .vertical; chrome.alignment = .leading; chrome.spacing = 9
        let title = NSTextField(labelWithString: "Your storage library")
        title.font = .systemFont(ofSize: 23, weight: .semibold)
        chrome.addArrangedSubview(title)
        let boundary = NSTextField(wrappingLabelWithString: interaction.applicationData
            ? "DEVELOPMENT PREVIEW · Save library versions on this Mac. Built-in examples only; real-folder access is unavailable."
            : interaction.hasStorage
            ? "DEVELOPMENT PREVIEW · Temporary test library storage. Each Save creates a new version. Real-folder access is unavailable."
            : "DEVELOPMENT PREVIEW · Built-in examples only. Real-folder access and saved library storage are unavailable.")
        boundary.font = .systemFont(ofSize: 12, weight: .medium)
        boundary.textColor = .secondaryLabelColor
        chrome.addArrangedSubview(boundary)
        actions.orientation = .horizontal; actions.spacing = 8
        exploreButton = LibraryActionButton("Explore sample folders", identifier: "library-explore") { [weak self] in self?.session.choose() }
        doneButton = LibraryActionButton("Done reviewing", identifier: "library-done") { [weak self] in self?.session.finishReview() }
        cancelButton = LibraryActionButton("Cancel preparation", identifier: "library-cancel") { [weak self] in self?.session.cancel() }
        let unavailable = LibraryActionButton("Choose my folder", identifier: "library-real-folder") {}
        unavailable.isEnabled = false
        unavailable.toolTip = "Unavailable: real folder selection needs a separately verified read-only native integration."
        for button in [exploreButton!, unavailable, doneButton!, cancelButton!] { actions.addArrangedSubview(button) }
        chrome.addArrangedSubview(actions)
        let persistence = NSStackView(); persistence.orientation = .horizontal; persistence.spacing = 8
        saveButton = LibraryActionButton("Save new library version", identifier: "library-save") { [weak self] in self?.interaction.save() }
        saveButton.keyEquivalent = "s"; saveButton.keyEquivalentModifierMask = [.command]
        openButton = LibraryActionButton("Open saved library", identifier: "library-open") { [weak self] in self?.interaction.open() }
        openButton.keyEquivalent = "o"; openButton.keyEquivalentModifierMask = [.command]
        checkButton = LibraryActionButton("Check same result", identifier: "library-check") { [weak self] in
            guard let self else { return }
            if self.interaction.canCheckReplacement { self.interaction.checkReplacement() }
            else { self.interaction.checkSave() }
        }
        cancelSaveButton = LibraryActionButton("Cancel Save preparation", identifier: "library-save-cancel") { [weak self] in self?.interaction.cancelSavePreparation() }
        let unavailableStorage = "Unavailable: this sample executable has no admitted library storage."
        if !interaction.hasStorage { saveButton.toolTip = unavailableStorage; openButton.toolTip = unavailableStorage }
        for button in [saveButton!, openButton!, checkButton!, cancelSaveButton!] { persistence.addArrangedSubview(button) }
        chrome.addArrangedSubview(persistence)
        status.font = .systemFont(ofSize: 12); status.setAccessibilityIdentifier("library-status")
        chrome.addArrangedSubview(status)
        let view = session.host.webView
        content.addSubview(chrome); content.addSubview(view)
        chrome.translatesAutoresizingMaskIntoConstraints = false; view.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            chrome.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            chrome.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
            chrome.topAnchor.constraint(equalTo: content.topAnchor, constant: 16),
            boundary.widthAnchor.constraint(equalTo: chrome.widthAnchor),
            status.widthAnchor.constraint(equalTo: chrome.widthAnchor),
            view.topAnchor.constraint(equalTo: chrome.bottomAnchor, constant: 14),
            view.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            view.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            view.bottomAnchor.constraint(equalTo: content.bottomAnchor),
        ])
        interaction.changed = { [weak self] in self?.refresh() }
        refresh()
    }

    func show() {
        window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        window.makeFirstResponder(exploreButton)
    }
    func completeStartup() -> Bool {
        guard !closing, session.state == .ready, session.host.state == .ready else { return false }
        startupReady = true; refresh(); return true
    }
    private func dismissPanel() {
        if let panel { window.endSheet(panel); panel.orderOut(nil) }
        panel = nil; panelState = nil
    }
    private func refresh() {
        guard !closing else { return }
        let sampleStateChanged = lastSessionState != session.state
        let releasedPage = lastFlight == .close && interaction.flight == .idle && !interaction.closeSample
        lastSessionState = session.state; lastFlight = interaction.flight
        if releasedPage { restorePageFocusAfterSheet() }
        status.stringValue = startupReady ? (interaction.message ?? session.message) : "Opening the bundled example library…"
        exploreButton.isEnabled = startupReady && interaction.canExplore
        saveButton.isEnabled = startupReady && interaction.canSave
        openButton.isEnabled = startupReady && interaction.canOpen
        cancelSaveButton.isHidden = !interaction.canCancelSavePreparation
        cancelSaveButton.isEnabled = interaction.canCancelSavePreparation
        checkButton.isHidden = !interaction.canCheckResult
        checkButton.isEnabled = interaction.canCheckResult
        doneButton.isEnabled = interaction.flight == .sample
        closeDiscardButton?.isEnabled = !interaction.busy
        // An awaited result may update status, never replace an active close sheet.
        guard !closeQuestion else { return }
        if interaction.canCloseWithoutLoss { discardAndClose(); return }
        if interaction.flight == .close, !interaction.busy, !closeQuestion { presentCloseQuestion(); return }
        if interaction.flight == .open {
            if savedPanel == nil { dismissPanel(); savedPanel = LibrarySavedPanel(owner: interaction, parent: window) }
            savedPanel?.refresh(); return
        } else if let savedPanel {
            savedPanel.dismiss(); self.savedPanel = nil
            restorePageFocusAfterSheet()
        }
        doneButton.isHidden = session.state != .reviewing
        cancelButton.isHidden = session.state != .preparing && session.state != .stopping
        cancelButton.isEnabled = session.state == .preparing && interaction.flight == .sample
        if session.state == .choosing || session.state == .scope {
            if panelState != session.state { presentPanel() }
        } else { dismissPanel() }
        if sampleStateChanged { restoreNativeFocus() }
    }
    private func restorePageFocusAfterSheet() {
        Task { @MainActor [weak self] in
            await Task.yield()
            guard let self, !self.closing, self.window.isVisible,
                  self.window.attachedSheet == nil, self.interaction.flight == .idle else { return }
            // The released page fence restores its exact prior DOM element.
            // Return AppKit keyboard dispatch to that same hosted view.
            self.window.makeFirstResponder(self.session.host.webView)
        }
    }
    private func restoreNativeFocus() {
        guard !closing, !closeQuestion, window.isVisible, window.attachedSheet == nil else { return }
        if session.state == .ready { window.makeFirstResponder(exploreButton) }
        else if session.state == .reviewing { window.makeFirstResponder(session.host.webView) }
    }
    private func presentPanel() {
        // Reuse the current sheet for selection -> scope so there is no race
        // between ending one modal session and beginning the next.
        let shouldAttach = panel == nil
        let sheet = panel ?? NSWindow(contentRect: NSRect(x: 0, y: 0, width: 500, height: 290),
            styleMask: [.titled], backing: .buffered, defer: false)
        sheet.isReleasedWhenClosed = false
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 14
        let title = NSTextField(labelWithString: session.state == .choosing ? "Explore an example location" : "Review this example's scope")
        title.font = .systemFont(ofSize: 20, weight: .semibold); stack.addArrangedSubview(title)
        let explanation = NSTextField(wrappingLabelWithString: session.state == .choosing ? "These are built-in example records, not connected drives. Choose one to explore the library workflow." : session.source.scopeDescription)
        stack.addArrangedSubview(explanation)
        var first: NSView?
        if session.state == .choosing {
            for item in session.source.choices {
                let button = LibraryActionButton(item.title, identifier: "library-choice-" + item.id) { [weak self] in self?.session.select(item) }
                button.toolTip = item.detail; stack.addArrangedSubview(button)
                if first == nil { first = button }
            }
        } else {
            let selected = NSTextField(labelWithString: session.choice?.title ?? "")
            selected.font = .systemFont(ofSize: 14, weight: .semibold); stack.addArrangedSubview(selected)
            let review = LibraryActionButton("Review example snapshot", identifier: "library-prepare") { [weak self] in self?.session.prepare() }
            review.keyEquivalent = "\r"; stack.addArrangedSubview(review); first = review
        }
        let cancel = LibraryActionButton("Cancel", identifier: "library-sheet-cancel") { [weak self] in self?.session.cancel() }
        cancel.keyEquivalent = "\u{1b}"; stack.addArrangedSubview(cancel)
        let content = NSView(); sheet.contentView = content; content.addSubview(stack)
        stack.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -24),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 22),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -20),
            explanation.widthAnchor.constraint(equalTo: stack.widthAnchor),
        ])
        panel = sheet; panelState = session.state
        if shouldAttach {
            window.beginSheet(sheet) { [weak self] _ in self?.restoreNativeFocus() }
        }
        sheet.makeFirstResponder(first)
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if closing { return true }
        requestClose(); return false
    }
    func requestClose() {
        guard !closeQuestion, !closing else { return }
        interaction.enquireClose()
        if interaction.closeUnknown, interaction.flight != .close { presentCloseQuestion() }
    }
    private func presentCloseQuestion() {
        guard !closeQuestion, !closing else { return }
        closeQuestion = true; dismissPanel()
        if let savedPanel { savedPanel.dismiss(); self.savedPanel = nil }
        let alert = NSAlert()
        let loss = interaction.closeLoss
        let draft = loss?.hasDraft == true
        let unknown = interaction.closeUnknown || interaction.unresolved
        alert.messageText = draft ? "Finish this edit before closing" : "Close this library?"
        if draft {
            alert.informativeText = "An unfinished edit or review is still open. Return to it so its draft is preserved. Saving the catalogue does not save that draft."
        } else if unknown {
            alert.informativeText = interaction.closeSample
                ? "An example selection, preparation or review is unfinished. Keep exploring to return to it, or explicitly discard the current temporary records and review."
                : "The current operation or view state is unconfirmed. Keep this window open and check its result. Closing abandons unconfirmed temporary work; retained files are not deleted and a save is not guaranteed."
        } else {
            let selections = loss?.selections ?? 0
            alert.informativeText = (loss?.dirty == true ? "The library has unsaved catalogue changes. " : "The catalogue has no unsaved changes. ") +
                (selections > 0 ? "There are \(selections) temporary project selections. Library saving does not include them. " : "") +
                (interaction.hasStorage ? "Saved versions are never overwritten." : "Saving is unavailable in this development preview.")
        }
        alert.addButton(withTitle: draft ? "Finish editing" : "Keep exploring")
        var saveIndex: Int?
        var checkIndex: Int?
        if !draft {
            let title = unknown && !interaction.closeSample ? "Discard unconfirmed work and close" :
                ((loss?.selections ?? 0) > 0 ? "Discard temporary work and close" : "Discard and close")
            alert.addButton(withTitle: title)
            alert.buttons[1].isEnabled = !interaction.busy
            closeDiscardButton = alert.buttons[1]
            if unknown, interaction.canCheckResult {
                checkIndex = alert.buttons.count
                alert.addButton(withTitle: "Check same result")
            }
            if !unknown, interaction.hasStorage, loss?.dirty == true {
                saveIndex = alert.buttons.count
                alert.addButton(withTitle: (loss?.selections ?? 0) > 0 ? "Save library, keep selections" : "Save library and close")
            }
        }
        for (index, button) in alert.buttons.enumerated() {
            let id = index == 0 ? "library-keep" : index == saveIndex ? "library-close-save" : index == checkIndex ? "library-close-check" : "library-discard"
            button.identifier = NSUserInterfaceItemIdentifier(id); button.setAccessibilityIdentifier(id)
        }
        alert.beginSheetModal(for: window) { [weak self] response in
            guard let self else { return }
            self.closeQuestion = false; self.closeDiscardButton = nil
            let index = response.rawValue - NSApplication.ModalResponse.alertFirstButtonReturn.rawValue
            if index == 1, !draft { self.discardAndClose() }
            else if index == saveIndex { self.interaction.saveBeforeClose() }
            else if index == checkIndex {
                if self.interaction.canCheckReplacement { self.interaction.checkReplacement() }
                else { self.interaction.checkSave() }
            } else {
                let sample = self.interaction.closeSample
                self.interaction.keepOpen(); self.refresh()
                if sample { self.restoreNativeFocus() }
            }
        }
    }
    func discardAndClose() {
        guard !closing else { return }
        closing = true
        guard interaction.finalClose() else { closing = false; return }
         dismissPanel(); savedPanel?.dismiss(); savedPanel = nil
        window.close(); didClose?()
    }
}
