import AppKit
import Foundation
import WebKit

// Shared data-only presentation. No filesystem writer, source selection,
// persistent grant or JavaScript-to-native message handler exists in this host.
@MainActor
class CataloguePreviewHost: NSObject, WKNavigationDelegate, WKUIDelegate, LibraryPageClient {
    enum Failure: Error { case unavailable, wrongDocument, invalidPayload, invalidReply, busy, expired }
    enum State: Equatable { case idle, loading, ready, staging, staged, retiring, blocked, closed }
    static let version = "catalogue-data-bridge/v2"
    static let ruleJSON = #"[{"trigger":{"url-filter":"^https?://"},"action":{"type":"block"}},{"trigger":{"url-filter":"^wss?://"},"action":{"type":"block"}},{"trigger":{"url-filter":"^ftp://"},"action":{"type":"block"}}]"#
    static let modeScript = "Object.defineProperty(globalThis, 'DiskCatalogueEmbedded', {value:true,writable:false,configurable:false});"
    private enum Operation {
        case initialise, stage, retire, emptyReadiness
        var body: String {
            switch self {
            case .initialise: return "return window.DiskCatalogueNativeBridge.initialise(version, session, mode);"
            case .stage: return "return window.DiskCatalogueNativeBridge.stage(version, session, delivery, text);"
            case .retire: return "return window.DiskCatalogueNativeBridge.retire(version, session, delivery);"
            case .emptyReadiness: return "return {version, session, state: document.querySelectorAll('.source-card').length === 0 && !document.getElementById('catalogue-dialog').open ? 'empty' : 'not-empty'};"
            }
        }
    }
    @MainActor
    private final class Once<Value: Sendable> {
        private var continuation: CheckedContinuation<Value, Error>?
        init(_ continuation: CheckedContinuation<Value, Error>) { self.continuation = continuation }
        func finish(_ result: Result<Value, Error>) {
            guard let continuation else { return }
            self.continuation = nil
            continuation.resume(with: result)
        }
    }
    private final class Delivery {
        let id = UUID().uuidString.lowercased()
        let navigation: UUID
        var retiring = false
        init(navigation: UUID) { self.navigation = navigation }
    }
    enum StorageMode: String { case temporary, ownedStorage = "owned-storage" }
    let storageMode: StorageMode
    let webView: NoDropWebView
    let document: URL
    let readRoot: URL
    let session = UUID().uuidString.lowercased()
    private(set) var state = State.idle
    private(set) var blockedNavigations = 0
    private var navigationGeneration = UUID()
    private var expectedNavigation: WKNavigation?
    private var pending: Delivery?
    private var stageTask: Task<Void, Error>?
    private var finishLoad: ((Result<Void, Error>) -> Void)?
    private var deliveryCount = 0
    // Internal lifecycle hook; the app has no override. Only the test subclass
    // supplies an acknowledgement barrier, outside the application target.
    func stageAcknowledged() async {}

    init(rule: WKContentRuleList, width: CGFloat = 1280, height: CGFloat = 960, storageMode: StorageMode = .temporary) throws {
        self.storageMode = storageMode
        guard let root = Bundle.module.resourceURL?.appendingPathComponent("Catalogue", isDirectory: true) else {
            throw Failure.unavailable
        }
        readRoot = root
        document = root.appendingPathComponent("inventory-catalogue.html", isDirectory: false)
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        configuration.userContentController.add(rule)
        configuration.userContentController.addUserScript(WKUserScript(source: Self.modeScript,
            injectionTime: .atDocumentStart, forMainFrameOnly: true))
        webView = NoDropWebView(frame: NSRect(x: 0, y: 0, width: width, height: height), configuration: configuration)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.isHidden = true
        webView.unregisterDraggedTypes()
    }

    func load() async throws {
        guard state == .idle else { throw Failure.unavailable }
        state = .loading
        do {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                let once = Once(continuation)
                finishLoad = { once.finish($0) }
                expectedNavigation = webView.loadFileURL(document, allowingReadAccessTo: readRoot)
                if expectedNavigation == nil { finishLoad?(.failure(Failure.unavailable)) }
                Task { @MainActor [weak self] in
                    try? await Task.sleep(for: .seconds(15))
                    guard let self, self.state == .loading else { return }
                    self.invalidate()
                }
            }
            guard state == .loading, webView.url == document else { throw Failure.wrongDocument }
            let reply = try await call(.initialise, arguments: ["version": Self.version, "session": session, "mode": storageMode.rawValue])
            guard state == .loading, reply == ["version": Self.version, "session": session, "mode": storageMode.rawValue, "state": "ready"] else {
                throw Failure.invalidReply
            }
            state = .ready
            webView.isHidden = false
        } catch { invalidate(); throw error }
    }

    // A fixed data-only startup query, not a script/command entry point. It is
    // used before any example delivery and gives no authority to imported JSON.
    func requireEmptyLibrary() async throws {
        guard state == .ready, pending == nil else { throw Failure.unavailable }
        let generation = navigationGeneration
        let reply = try await call(.emptyReadiness, arguments: ["version": Self.version, "session": session])
        guard state == .ready, pending == nil, navigationGeneration == generation,
              reply == ["version": Self.version, "session": session, "state": "empty"] else { throw Failure.invalidReply }
    }

    func stage(_ bytes: Data) async throws -> String {
        guard state == .ready, pending == nil, deliveryCount < 128, webView.url == document else { throw Failure.busy }
        guard !bytes.isEmpty, bytes.count <= 1_048_576, !bytes.starts(with: [0xef, 0xbb, 0xbf]),
              let text = String(data: bytes, encoding: .utf8), Data(text.utf8) == bytes else {
            throw Failure.invalidPayload
        }
        // Strict schema/duplicate/hierarchy validation is shared with file import
        // in the bundled page before it can stage. UTF-8/byte preflight is not a
        // native duplicate-key validator and confers no saved-artifact trust.
        let item = Delivery(navigation: navigationGeneration)
        pending = item; state = .staging; deliveryCount += 1
        let task = Task { @MainActor [self] in
            do {
                let reply = try await call(.stage, arguments: ["version": Self.version, "session": session,
                    "delivery": item.id, "text": text])
                await stageAcknowledged()
                guard pending === item, navigationGeneration == item.navigation, state == .staging,
                      reply == ["version": Self.version, "session": session, "delivery": item.id, "state": "staged"] else {
                    throw Failure.invalidReply
                }
                state = .staged
            } catch { invalidate(); throw error }
        }
        stageTask = task
        try await task.value
        return item.id // Delivery correlation only; never "added" or "saved".
    }

    func retire() async throws -> String {
        guard let item = pending, !item.retiring, state == .staging || state == .staged else { throw Failure.busy }
        item.retiring = true
        do {
            // A page can already be showing Add before its completion arrives.
            // Wait for that stage acknowledgement, then establish the page fence.
            try await stageTask?.value
            guard pending === item, navigationGeneration == item.navigation, state == .staged else { throw Failure.expired }
            state = .retiring
            let reply = try await call(.retire, arguments: ["version": Self.version, "session": session, "delivery": item.id])
            guard pending === item, navigationGeneration == item.navigation, state == .retiring,
                  Set(reply.keys) == ["version", "session", "delivery", "state", "outcome"],
                  reply["version"] == Self.version, reply["session"] == session,
                  reply["delivery"] == item.id, reply["state"] == "retired",
                  let outcome = reply["outcome"], ["committed", "cancelled", "dismissed"].contains(outcome) else {
                throw Failure.invalidReply
            }
            pending = nil; stageTask = nil; state = .ready
            return outcome
        } catch { invalidate(); throw error }
    }

    // This is a view/session retirement, not a claim of instantaneous WebKit or
    // OS cancellation. Hiding the old view prevents later user interaction;
    // explicit recovery must construct a new host, never retry the old delivery.
    func invalidate() {
        guard state != .closed else { return }
        state = .blocked; navigationGeneration = UUID(); pending = nil
        webView.isHidden = true; webView.stopLoading()
        let finish = finishLoad; finishLoad = nil; finish?(.failure(Failure.expired))
    }
    func close() { invalidate(); state = .closed; webView.navigationDelegate = nil; webView.uiDelegate = nil }

    private func call(_ operation: Operation, arguments: [String: String]) async throws -> [String: String] {
        let generation = navigationGeneration
        return try await withCheckedThrowingContinuation { continuation in
            let once = Once(continuation)
            // Completion and timer share one MainActor-owned continuation gate.
            // Late callbacks cannot resume twice or revive a retired document.
            webView.callAsyncJavaScript(operation.body, arguments: arguments, in: nil, in: .page) { [weak self] result in
                guard let self, self.navigationGeneration == generation, self.webView.url == self.document,
                      self.state != .blocked, self.state != .closed else {
                    once.finish(.failure(Failure.expired)); return
                }
                switch result {
                case .success(let value):
                    guard let reply = value as? [String: String], reply.count <= 5,
                          reply.allSatisfy({ $0.key.utf8.count <= 16 && $0.value.utf8.count <= 64 }) else {
                        once.finish(.failure(Failure.invalidReply)); return
                    }
                    once.finish(.success(reply))
                case .failure(let error): once.finish(.failure(error))
                }
            }
            Task { @MainActor in
                try? await Task.sleep(for: .seconds(10))
                once.finish(.failure(Failure.expired))
            }
        }
    }

    // Fixed persistence operations have their own exact decoder. The existing
    // five-field snapshot decoder above deliberately remains unchanged.
    func libraryCall(_ operation: LibraryBridgeOperation, id: UUID,
                     fields: [String: String] = [:]) async throws -> LibraryBridgeReply {
        guard state == .ready, pending == nil, webView.url == document,
              !operation.needsStorage || storageMode == .ownedStorage else { throw Failure.busy }
        let request = try LibraryBridgeWire.request(operation, session: session, id: id, fields: fields)
        let generation = navigationGeneration
        return try await withCheckedThrowingContinuation { continuation in
            let once = Once(continuation)
            webView.callAsyncJavaScript(operation.body, arguments: ["request": request], in: nil, in: .page) { [weak self] result in
                guard let self, self.navigationGeneration == generation, self.webView.url == self.document,
                      self.state == .ready, self.pending == nil else {
                    once.finish(.failure(Failure.expired)); return
                }
                switch result {
                case .success(let value):
                    do { once.finish(.success(try LibraryBridgeWire.decode(value, operation: operation, request: request))) }
                    catch { once.finish(.failure(Failure.invalidReply)) }
                case .failure: once.finish(.failure(Failure.unavailable))
                }
            }
            Task { @MainActor in
                try? await Task.sleep(for: .seconds(10))
                // The owner must reconcile the same nonce; timeout is not proof
                // that an acknowledgement or replacement was not applied.
                once.finish(.failure(Failure.expired))
            }
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void) {
        let initial = state == .loading && action.targetFrame?.isMainFrame == true &&
            action.request.url == document && action.request.httpMethod == "GET" && !action.shouldPerformDownload
        if initial { decisionHandler(.allow) }
        else { blockedNavigations += 1; invalidate(); decisionHandler(.cancel) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void) {
        if state == .loading && response.isForMainFrame && response.response.url == document &&
            response.canShowMIMEType && response.response.mimeType == "text/html" { decisionHandler(.allow) }
        else { invalidate(); decisionHandler(.cancel) }
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard state == .loading, navigation === expectedNavigation, webView.url == document else { invalidate(); return }
        let finish = finishLoad; finishLoad = nil; finish?(.success(()))
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { invalidate() }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { invalidate() }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) { invalidate() }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        blockedNavigations += 1; invalidate(); return nil
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping @MainActor @Sendable ([URL]?) -> Void) { completionHandler(nil) }
    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping @MainActor @Sendable () -> Void) { invalidate(); completionHandler() }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping @MainActor @Sendable (Bool) -> Void) { invalidate(); completionHandler(false) }
    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                 defaultText: String?, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping @MainActor @Sendable (String?) -> Void) { invalidate(); completionHandler(nil) }
}

@MainActor
final class NoDropWebView: WKWebView {
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation { [] }
    override func draggingUpdated(_ sender: NSDraggingInfo) -> NSDragOperation { [] }
    override func prepareForDragOperation(_ sender: NSDraggingInfo) -> Bool { false }
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool { false }
}
