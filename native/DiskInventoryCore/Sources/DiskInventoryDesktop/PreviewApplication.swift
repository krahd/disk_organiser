import AppKit
import Foundation
import WebKit
import Darwin

@MainActor
private final class ApplicationRuleResult {
    var value: WKContentRuleList?
    var continuation: CheckedContinuation<Void, Error>?
    func finish(_ error: Error?) {
        guard let continuation else { return }
        self.continuation = nil
        if let error { continuation.resume(throwing: error) }
        else { continuation.resume() }
    }
}

// Rule compilation necessarily writes a framework cache. It receives a fresh
// private temporary directory, never the default store or a selected source.
@MainActor
final class ApplicationRuleCache {
    let directory: URL
    let store: WKContentRuleListStore
    private init(directory: URL, store: WKContentRuleListStore) { self.directory = directory; self.store = store }
    static func create() async throws -> (ApplicationRuleCache, WKContentRuleList) {
        var template = Array("/private/tmp/disk-organiser-preview-rules-XXXXXX".utf8CString)
        let path = try template.withUnsafeMutableBufferPointer { buffer in
            guard let result = mkdtemp(buffer.baseAddress!) else { throw CataloguePreviewHost.Failure.unavailable }
            return String(cString: result)
        }
        let directory = URL(fileURLWithPath: path, isDirectory: true)
        guard let store = WKContentRuleListStore(url: directory) else { throw CataloguePreviewHost.Failure.unavailable }
        let owner = ApplicationRuleCache(directory: directory, store: store)
        let result = ApplicationRuleResult()
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            result.continuation = continuation
            store.compileContentRuleList(forIdentifier: "disk-organiser-preview-" + UUID().uuidString,
                encodedContentRuleList: CataloguePreviewHost.ruleJSON) { rule, error in
                guard result.continuation != nil else { return }
                if let error { result.finish(error) }
                else if let rule { result.value = rule; result.finish(nil) }
                else { result.finish(CataloguePreviewHost.Failure.unavailable) }
            }
            Task { @MainActor in
                try? await Task.sleep(for: .seconds(10))
                result.finish(CataloguePreviewHost.Failure.expired)
            }
        }
        guard let rule = result.value else { throw CataloguePreviewHost.Failure.unavailable }
        return (owner, rule)
    }
    // The OS may retain/clean this cache. No recursive cleanup, catalogue write
    // or persistent source permission is introduced by the development shell.
}

@MainActor
private final class PreviewApplicationDelegate: NSObject, NSApplicationDelegate {
    private var library: LibraryWindowController?
    private var cache: ApplicationRuleCache?
    func applicationDidFinishLaunching(_ notification: Notification) {
        FileHandle.standardOutput.write(Data("DISK_PREVIEW_DID_LAUNCH\n".utf8))
        Task { @MainActor in
            var opened: LibraryWindowController?
            do {
                let (cache, rule) = try await ApplicationRuleCache.create()
                self.cache = cache
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_RULES_READY\n".utf8))
                let host = try CataloguePreviewHost(rule: rule)
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_HOST_CREATED\n".utf8))
                try await host.load()
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_VIEW_READY\n".utf8))
                let library = LibraryWindowController(session: LibrarySession(host: host, source: BundledLibraryExamples()), startReady: false)
                opened = library
                self.library = library
                library.didClose = { [weak self] in
                    self?.library = nil
                    // Return from the current applicationShouldTerminate before
                    // beginning the final normal attempt; never re-enter it.
                    Task { @MainActor in NSApp.terminate(nil) }
                }
                library.show()
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_WINDOW_SHOWN\n".utf8))
                try await host.requireEmptyLibrary()
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_EMPTY_CONFIRMED\n".utf8))
                let deadline = Date().addingTimeInterval(3)
                while (!NSApp.isActive || !library.window.isKeyWindow) && Date() < deadline {
                    try await Task.sleep(for: .milliseconds(20))
                }
                if NSApp.isActive { FileHandle.standardOutput.write(Data("DISK_PREVIEW_ACTIVE\n".utf8)) }
                if library.window.isKeyWindow { FileHandle.standardOutput.write(Data("DISK_PREVIEW_KEY\n".utf8)) }
                if library.window.isVisible { FileHandle.standardOutput.write(Data("DISK_PREVIEW_VISIBLE\n".utf8)) }
                guard NSApp.isActive, library.window.isKeyWindow, library.window.isVisible,
                      host.webView.window === library.window, !host.webView.isHidden,
                      library.completeStartup() else { throw CataloguePreviewHost.Failure.unavailable }
                // Fixed diagnostic receipt: no names, paths or user data.
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_READY_EMPTY_WINDOW\n".utf8))
            } catch {
                FileHandle.standardOutput.write(Data("DISK_PREVIEW_STARTUP_FAILED\n".utf8))
                if opened?.session.state == .closed { return }
                let alert = NSAlert(); alert.messageText = "The development preview could not open"
                alert.informativeText = "The bundled catalogue was not available. No source folder was opened or saved library changed."
                alert.addButton(withTitle: "Close"); alert.runModal(); NSApp.terminate(nil)
            }
        }
    }
    func applicationShouldOpenUntitledFile(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { false }
    func application(_ sender: NSApplication, openFile filename: String) -> Bool { false }
    func application(_ sender: NSApplication, openFiles filenames: [String]) { sender.reply(toOpenOrPrint: .failure) }
    func application(_ application: NSApplication, open urls: [URL]) { /* No document/URL access. */ }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        FileHandle.standardOutput.write(Data("DISK_PREVIEW_QUIT_REQUEST\n".utf8))
        guard let library else { return .terminateNow }
        library.requestClose(); return .terminateCancel
    }
    func applicationWillTerminate(_ notification: Notification) {
        FileHandle.standardOutput.write(Data("DISK_PREVIEW_WILL_TERMINATE\n".utf8))
    }
}

@MainActor
public enum DiskOrganiserPreviewApplication {
    private static var delegate: PreviewApplicationDelegate?
    public static func run() {
        FileHandle.standardOutput.write(Data("DISK_PREVIEW_ENTRY\n".utf8))
        // External startup context is never a source-selection route.
        guard CommandLine.arguments.count == 1,
              UserDefaults.standard.object(forKey: "NSOpen") == nil,
              UserDefaults.standard.object(forKey: "NSPrint") == nil else {
            FileHandle.standardOutput.write(Data("DISK_PREVIEW_INPUT_REJECTED\n".utf8))
            return
        }
        let application = NSApplication.shared
        guard application.delegate == nil, application.setActivationPolicy(.regular) else {
            FileHandle.standardOutput.write(Data("DISK_PREVIEW_BOOTSTRAP_REJECTED\n".utf8)); return
        }
        let delegate = PreviewApplicationDelegate(); Self.delegate = delegate; application.delegate = delegate
        let menu = NSMenu(); let applicationItem = NSMenuItem(); menu.addItem(applicationItem)
        let applicationMenu = NSMenu(); applicationItem.submenu = applicationMenu
        applicationMenu.addItem(withTitle: "Quit Disk Organiser Preview", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        application.mainMenu = menu
        FileHandle.standardOutput.write(Data("DISK_PREVIEW_RUN_LOOP\n".utf8))
        application.run()
    }
}
