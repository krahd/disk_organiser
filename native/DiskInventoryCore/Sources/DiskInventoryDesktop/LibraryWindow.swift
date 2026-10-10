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
    let chrome = NSStackView()
    private let status = NSTextField(wrappingLabelWithString: "")
    private let actions = NSStackView()
    private var panel: NSWindow?
    private var panelState: LibrarySession.State?
    private var closing = false
    private var closeQuestion = false
    private var startupReady: Bool
    var didClose: (() -> Void)?
    private(set) var exploreButton: LibraryActionButton!
    private(set) var doneButton: LibraryActionButton!
    private(set) var cancelButton: LibraryActionButton!

    init(session: LibrarySession, startReady: Bool = true) {
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
        let boundary = NSTextField(wrappingLabelWithString: "DEVELOPMENT PREVIEW · Built-in examples only. Real folder reading, Save and Open are not connected yet.")
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
        session.changed = { [weak self] in self?.refresh() }
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
        status.stringValue = startupReady ? session.message : "Opening the bundled example library…"
        exploreButton.isEnabled = startupReady && session.state == .ready
        doneButton.isHidden = session.state != .reviewing
        cancelButton.isHidden = session.state != .preparing && session.state != .stopping
        cancelButton.isEnabled = session.state == .preparing
        // State completion must never replace a pending native close question.
        guard !closeQuestion else { return }
        if session.state == .choosing || session.state == .scope {
            if panelState != session.state { presentPanel() }
        } else { dismissPanel() }
        restoreNativeFocus()
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
        if !session.hasTemporaryRecords && session.state == .ready { discardAndClose(); return }
        closeQuestion = true
        dismissPanel()
        let alert = NSAlert(); alert.messageText = "Close this temporary library?"
        alert.informativeText = "Unsaved example records and the current review will be discarded. Save is unavailable in this development preview."
        alert.addButton(withTitle: "Keep exploring"); alert.addButton(withTitle: "Discard and close")
        alert.buttons[0].identifier = NSUserInterfaceItemIdentifier("library-keep")
        alert.buttons[1].identifier = NSUserInterfaceItemIdentifier("library-discard")
        alert.buttons[0].setAccessibilityIdentifier("library-keep")
        alert.buttons[1].setAccessibilityIdentifier("library-discard")
        alert.beginSheetModal(for: window) { [weak self] response in
            guard let self else { return }
            self.closeQuestion = false
            if response == .alertSecondButtonReturn { self.discardAndClose() }
            else { self.refresh() }
        }
    }
    func discardAndClose() {
        guard !closing else { return }
        closing = true; dismissPanel(); session.close(); window.close(); didClose?()
    }
}
