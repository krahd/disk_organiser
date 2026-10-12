import AppKit
import Foundation

@MainActor
final class ProbeDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    private var controller: ProbeController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 420),
                              styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Owned-folder feasibility"
        window.identifier = NSUserInterfaceItemIdentifier("owned-probe-window")
        window.isReleasedWhenClosed = false
        let title = NSTextField(labelWithString: "Selected-folder access test")
        title.font = .boldSystemFont(ofSize: 22)
        let explanation = NSTextField(wrappingLabelWithString: "Isolated engineering probe. Only a sealed temporary test folder is eligible. This is not the Disk Organiser application.")
        let status = NSTextField(wrappingLabelWithString: "Validating the sealed test build…")
        status.setAccessibilityIdentifier("probe-status")
        let receipt = NSTextField(wrappingLabelWithString: "")
        receipt.setAccessibilityIdentifier("probe-receipt")
        receipt.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        let choose = button("Choose owned folder", "probe-choose")
        let read = button("Run selected read", "probe-read")
        let finish = button("Finish read", "probe-finish")
        let cancel = button("Cancel", "probe-cancel")
        let buttons = NSStackView(views: [choose, read, finish, cancel])
        buttons.orientation = .horizontal; buttons.spacing = 8
        let stack = NSStackView(views: [title, explanation, buttons, status, receipt])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 18
        stack.edgeInsets = NSEdgeInsets(top: 24, left: 24, bottom: 24, right: 24)
        stack.translatesAutoresizingMaskIntoConstraints = false
        guard let content = window.contentView else { NSApp.terminate(nil); return }
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.topAnchor.constraint(equalTo: content.topAnchor),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor),
            explanation.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -48),
            status.widthAnchor.constraint(equalTo: explanation.widthAnchor),
            receipt.widthAnchor.constraint(equalTo: explanation.widthAnchor),
        ])
        self.window = window
        do {
            let fixture = try ProbeFixture.load()
            guard fixture.selected == ProbeSeal.selectedPath else { throw ProbeFailure.refused("sealed-path-mismatch") }
            controller = ProbeController(fixture: fixture, window: window, status: status, receipt: receipt,
                                         choose: choose, read: read, finish: finish, cancel: cancel)
        } catch {
            status.stringValue = "UNAVAILABLE · " + ProbeWork.failureCode(error)
            // No fixture read, panel, source grant or override is offered.
        }
        window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func button(_ title: String, _ id: String) -> NSButton {
        let button = NSButton(title: title, target: nil, action: nil)
        button.bezelStyle = .rounded; button.isEnabled = false
        button.setAccessibilityIdentifier(id)
        return button
    }
    func application(_ sender: NSApplication, openFiles filenames: [String]) {
        sender.reply(toOpenOrPrint: .failure)
    }
    func application(_ sender: NSApplication, open urls: [URL]) { /* Refuse external input. */ }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard let window, window.isVisible, let controller else { return .terminateNow }
        _ = controller.windowShouldClose(window)
        return window.isVisible ? .terminateCancel : .terminateNow
    }
}

let app = NSApplication.shared
let delegate = ProbeDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
let menu = NSMenu()
let applicationItem = NSMenuItem()
let applicationMenu = NSMenu()
applicationMenu.addItem(withTitle: "Quit owned probe", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
applicationItem.submenu = applicationMenu; menu.addItem(applicationItem)
let fileItem = NSMenuItem()
let fileMenu = NSMenu(title: "File")
fileMenu.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
fileItem.submenu = fileMenu; menu.addItem(fileItem)
app.mainMenu = menu
app.run()
