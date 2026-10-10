import AppKit
import Foundation

// Short document content starts at its upper edge, just like long previews.
// This changes native coordinates/layout only, not scrolling or input authority.
@MainActor
private final class LibraryTopOriginStack: NSStackView {
    override var isFlipped: Bool { true }
}

@MainActor
final class LibrarySavedPanel {
    let window: NSWindow
    private weak var parent: NSWindow?
    private let owner: LibraryInteraction
    private var offset = 0
    private var signature = ""
    init(owner: LibraryInteraction, parent: NSWindow) {
        self.owner = owner; self.parent = parent
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 650, height: 510), styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false; window.title = "Open a saved library version"
        refresh(); parent.beginSheet(window)
    }
    func dismiss() { parent?.endSheet(window); window.orderOut(nil) }
    private func label(_ text: String, bold: Bool = false) -> NSTextField {
        let view = NSTextField(wrappingLabelWithString: text)
        view.font = .systemFont(ofSize: bold ? 15 : 12, weight: bold ? .semibold : .regular)
        view.isSelectable = true
        return view
    }
    private func scroll(_ stack: NSStackView) -> NSScrollView {
        let view = NSScrollView(); view.hasVerticalScroller = true; view.borderType = .bezelBorder
        view.documentView = stack
        stack.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: view.contentView.leadingAnchor, constant: 8),
            stack.trailingAnchor.constraint(equalTo: view.contentView.trailingAnchor, constant: -8),
            stack.topAnchor.constraint(equalTo: view.contentView.topAnchor, constant: 8),
        ])
        return view
    }
    func refresh() {
        let total = owner.listing?.entries.count ?? 0
        if offset >= total { offset = 0 }
        let nextSignature = "\(owner.openPhase)-\(owner.busy)-\(owner.selected?.id.uuidString ?? "")-\(total)-\(offset)-\(owner.message ?? "")"
        guard signature != nextSignature else { return }; signature = nextSignature
        let content = NSView(); window.contentView = content
        let stack = NSStackView(); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 10
        let title = label("Open a saved library version", bold: true); stack.addArrangedSubview(title)
        let explanation = label("Temporary test library storage · Select a version to check its contents. Replace changes only this window. Saved files are never overwritten.")
        stack.addArrangedSubview(explanation)
        let summary: String
        if let listing = owner.listing {
            summary = "\(total) saved candidates · \(listing.pendingCount) incomplete · \(listing.unknownCount) other files · \(listing.listedLogicalBytes) listed bytes. Retained incomplete files use the same 256-entry / 64-MiB budget."
        } else { summary = "Checking the complete bounded list…" }
        let counts = label(summary); stack.addArrangedSubview(counts)
        let columns = NSStackView(); columns.orientation = .horizontal; columns.alignment = .top; columns.spacing = 12
        let rows = LibraryTopOriginStack(); rows.orientation = .vertical; rows.alignment = .leading; rows.spacing = 8
        let detail = LibraryTopOriginStack(); detail.orientation = .vertical; detail.alignment = .leading; detail.spacing = 10
        let formatter = DateFormatter(); formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0); formatter.dateFormat = "dd MMM yyyy HH:mm:ss 'UTC'"
        if let listing = owner.listing {
            if listing.entries.isEmpty { rows.addArrangedSubview(label("No saved versions yet. Cancel and save your first library version.")) }
            for (local, entry) in listing.entries.dropFirst(offset).prefix(64).enumerated() {
                let ordinal = offset + local + 1
                let button = LibraryActionButton("Version \(ordinal) · \(entry.bytes) bytes", identifier: "library-version-\(ordinal)") { [weak self] in self?.owner.selectSaved(entry) }
                button.isEnabled = owner.canSelectSaved
                button.state = owner.selected == entry ? .on : .off
                button.toolTip = owner.previewLimitReached ? "Cancel Open and reopen to choose another version; the 128-preview limit is reached." : "File reference: " + entry.id.uuidString.lowercased()
                rows.addArrangedSubview(button)
                rows.addArrangedSubview(label("File modified: " + formatter.string(from: entry.modifiedAt)))
            }
        }
        if let preview = owner.preview {
            detail.addArrangedSubview(label("\(preview.locations.count) recorded locations · \(preview.entries) file/folder entries", bold: true))
            detail.addArrangedSubview(label("Historical imported claims. Live presence, physical drive identity, contents and backup protection have not been verified. File modification dates do not authenticate these claimed observation dates."))
            if preview.locations.isEmpty { detail.addArrangedSubview(label("This is an empty library. Replace will deliberately clear the current in-memory records.")) }
            for (index, location) in preview.locations.enumerated() {
                detail.addArrangedSubview(label("\(index + 1). " + location.label, bold: true))
                detail.addArrangedSubview(label("Original folder label: " + location.origin + "\nObservation claimed: " + location.claimedDate + "\n\(location.entries) entries · " + (location.partial ? "Partial listing" : "Folder listing completed · live storage not checked") + "\n" + location.gaps))
            }
        } else { detail.addArrangedSubview(label("Select a version to see all of its recorded locations here. No candidate content is accepted before validation.")) }
        let rowScroll = scroll(rows), detailScroll = scroll(detail)
        columns.addArrangedSubview(rowScroll); columns.addArrangedSubview(detailScroll)
        rowScroll.widthAnchor.constraint(equalToConstant: 220).isActive = true
        detailScroll.widthAnchor.constraint(equalTo: columns.widthAnchor, constant: -232).isActive = true
        stack.addArrangedSubview(columns)
        let page = NSStackView(); page.orientation = .horizontal; page.spacing = 8
        let previous = LibraryActionButton("Previous 64", identifier: "library-previous") { [weak self] in
            guard let self, !self.owner.busy else { return }; self.offset = max(0, self.offset - 64); self.refresh()
        }
        let next = LibraryActionButton("Next 64", identifier: "library-next") { [weak self] in
            guard let self, !self.owner.busy else { return }; self.offset += 64; self.refresh()
        }
        previous.isEnabled = !owner.busy && offset > 0; next.isEnabled = !owner.busy && offset + 64 < total
        page.addArrangedSubview(previous); page.addArrangedSubview(label(total == 0 ? "0 versions" : "\(offset + 1)–\(min(offset + 64, total)) of \(total)")); page.addArrangedSubview(next)
        stack.addArrangedSubview(page)
        let warning = label((owner.openLoss?.dirty == true ? "Unsaved catalogue edits will be discarded. " : "") + "Replace also clears temporary project selections and search/comparison state. Cancel preserves them.")
        stack.addArrangedSubview(warning)
        let status = label(owner.message ?? ""); status.setAccessibilityIdentifier("library-open-status"); stack.addArrangedSubview(status)
        let actions = NSStackView(); actions.orientation = .horizontal; actions.spacing = 8
        let cancel = LibraryActionButton("Cancel Open", identifier: "library-open-cancel") { [weak self] in self?.owner.cancelOpen() }
        cancel.keyEquivalent = "\u{1b}"
        let replace = LibraryActionButton("Replace current library", identifier: "library-replace") { [weak self] in self?.owner.replace() }
        replace.isEnabled = owner.canReplace
        let check = LibraryActionButton("Check same replacement", identifier: "library-replacement-check") { [weak self] in self?.owner.checkReplacement() }
        check.isHidden = !owner.canCheckReplacement; check.isEnabled = owner.canCheckReplacement
        for button in [cancel, replace, check] { actions.addArrangedSubview(button) }; stack.addArrangedSubview(actions)
        content.addSubview(stack); stack.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 18),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -18),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 18),
            stack.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -18),
            columns.widthAnchor.constraint(equalTo: stack.widthAnchor),
            columns.heightAnchor.constraint(greaterThanOrEqualToConstant: 150),
            rowScroll.heightAnchor.constraint(equalTo: columns.heightAnchor),
            detailScroll.heightAnchor.constraint(equalTo: columns.heightAnchor),
            explanation.widthAnchor.constraint(equalTo: stack.widthAnchor), counts.widthAnchor.constraint(equalTo: stack.widthAnchor),
            warning.widthAnchor.constraint(equalTo: stack.widthAnchor), status.widthAnchor.constraint(equalTo: stack.widthAnchor),
        ])
        for child in rows.arrangedSubviews { child.widthAnchor.constraint(equalTo: rows.widthAnchor).isActive = true }
        for child in detail.arrangedSubviews { child.widthAnchor.constraint(equalTo: detail.widthAnchor).isActive = true }
        content.layoutSubtreeIfNeeded()
        window.makeFirstResponder(cancel)
    }
}
