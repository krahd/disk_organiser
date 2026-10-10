import Foundation

// A test-owned descriptor capability is injected once. This lease does not
// discover/create a directory and is never constructed by the sample executable.
@MainActor
final class OwnedLibraryInjection {
    private let storage: LibraryStorage
    init(storage: LibraryStorage) { self.storage = storage }
    func claim() throws -> LibraryStorage {
        try storage.claimInteractionOwner()
        return storage
    }
}

@MainActor
final class LibraryInteraction {
    enum Flight: Equatable { case idle, sample, save, open, close, closed }
    enum SaveOutcome: Equatable {
        case none, rejected, notPublished, storageUnresolved, pageUnresolved, currentSaved, earlierSaved, retired
    }
    enum OpenPhase: Equatable { case none, listing, choosing, reading, prepared, committing, unresolved, committed }
    private final class SaveAttempt {
        let id = UUID()
        let session: String
        let fence: UUID?
        var revision: String?
        var bytes: Data?
        var invokedStorage = false
        var receipt: LibrarySaveReceipt?
        var storageAcknowledged = false
        init(session: String, fence: UUID?) { self.session = session; self.fence = fence }
    }
    private final class OpenAttempt {
        let id = UUID()
        let session: String
        var loss: LibraryLossState?
        var candidate: UUID?
        var cancelled = false
        var preparedCount = 0
        var commitInvoked = false
        init(session: String) { self.session = session }
    }
    let session: LibrarySession
    private let page: any LibraryPageClient
    private let storage: LibraryStorage?
    private let codec: any CatalogueValidating
    private(set) var flight = Flight.idle
    private(set) var busy = false
    private(set) var message: String?
    private(set) var saveOutcome = SaveOutcome.none
    private(set) var openPhase = OpenPhase.none
    private(set) var listing: SavedLibraryListing?
    private(set) var selected: SavedLibraryEntry?
    private(set) var preview: LibraryCandidatePreview?
    private(set) var closeLoss: LibraryLossState?
    private(set) var closeUnknown = false
    private(set) var closeSample = false
    private(set) var closeID: UUID?
    private var resumeSampleAfterClose = false
    private var saved: SaveAttempt?
    private var opened: OpenAttempt?
    private var acknowledgedRevision: String?
    private var work: Task<Void, Never>?
    private var generation = UUID()
    var changed: (() -> Void)?
    var hasStorage: Bool { storage != nil }
    var unresolved: Bool { saveOutcome == .storageUnresolved || saveOutcome == .pageUnresolved || openPhase == .unresolved }
    var canSave: Bool { hasStorage && flight == .idle && !busy && !unresolved && session.state == .ready }
    var canOpen: Bool { canSave }
    var canExplore: Bool { flight == .idle && !busy && !unresolved && session.state == .ready }
    var canCloseWithoutLoss: Bool { flight == .close && !busy && !unresolved && !closeUnknown && closeLoss?.emptyLoss == true }
    var openLoss: LibraryLossState? { opened?.loss }
    var canCheckSave: Bool {
        !busy && flight != .closed && saved != nil && (saveOutcome == .storageUnresolved || saveOutcome == .pageUnresolved)
    }
    var canCheckReplacement: Bool {
        flight == .open && !busy && openPhase == .unresolved && opened?.commitInvoked == true && opened?.candidate != nil
    }
    var canCheckResult: Bool { canCheckSave || canCheckReplacement }
    var canSelectSaved: Bool {
        flight == .open && !busy && [.choosing, .prepared].contains(openPhase) && (opened?.preparedCount ?? 128) < 128
    }
    var previewLimitReached: Bool { (opened?.preparedCount ?? 0) >= 128 }
    var canReplace: Bool { flight == .open && !busy && openPhase == .prepared && preview != nil }

    init(session: LibrarySession, injection: OwnedLibraryInjection? = nil,
         codec: any CatalogueValidating = CatalogueCodec()) throws {
        let client = session.host
        guard (injection != nil) == (client.storageMode == .ownedStorage),
              session.intentAdmission == nil else { throw LibraryStorageFailure.invalidScope }
        self.session = session; self.page = client; self.codec = codec
        storage = try injection?.claim()
        session.intentAdmission = { [weak self] intent in self?.admitSample(intent) == true }
        session.ownerChanged = { [weak self] in self?.sampleChanged() }
    }
    private func emit(_ text: String? = nil) { if let text { message = text }; changed?() }
    private func admitSample(_ intent: LibrarySession.Intent) -> Bool {
        switch intent {
        case .choose:
            guard canExplore else { return false }
            flight = .sample; message = nil; return true
        case .select, .prepare, .cancel, .finish:
            return flight == .sample
        case .close:
            // Direct component close is treated as explicit final retirement,
            // never a way to bypass an active storage operation.
            if flight == .closed { return true }
            guard !hasStorage, !busy, !unresolved, flight == .sample || flight == .idle else { return false }
            flight = .closed; generation = UUID(); return true
        }
    }
    private func sampleChanged() {
        if flight == .sample, session.state == .ready || session.state == .failed { flight = .idle }
        emit()
    }
    private func current(_ token: UUID, _ pageSession: String) -> Bool {
        generation == token && flight != .closed && page.session == pageSession
    }
    private func call(_ op: LibraryBridgeOperation, _ id: UUID, _ fields: [String: String] = [:]) async throws -> LibraryBridgeReply {
        try await page.libraryCall(op, id: id, fields: fields)
    }

    func save() {
        guard canSave else { return }
        beginSave(fence: nil)
    }
    private func beginSave(fence: UUID?) {
        guard !busy, let storage else { return }
        let attempt = SaveAttempt(session: page.session, fence: fence), token = generation
        saved = attempt; saveOutcome = .none; busy = true
        if fence == nil { flight = .save }
        emit("Saving a new library version. Temporary project selections are not included.")
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                try Task.checkCancellation()
                let status = try await call(.status, fence ?? attempt.id)
                if let loss = status.loss, !loss.hasDraft, !loss.dirty, acknowledgedRevision == loss.revision {
                    saveOutcome = .currentSaved
                    if fence == nil { flight = .idle } else { closeLoss = loss }
                    emit("No catalogue changes since that saved version.")
                    return
                }
                let result = try await call(.exportCatalogue, attempt.id, ["fence": fence?.uuidString.lowercased() ?? ""])
                attempt.revision = result.values["revision"]
                attempt.bytes = Data(result.values["text"]!.utf8)
                guard current(token, attempt.session) else { saveOutcome = .retired; return }
                try Task.checkCancellation()
                let admitted = try await codec.validate(attempt.bytes!)
                try Task.checkCancellation()
                guard current(token, attempt.session) else { saveOutcome = .retired; return }
                attempt.invokedStorage = true
                do {
                    let receipt = try await storage.save(admitted, attempt: attempt.id)
                    // Record a real artifact before checking view lifetime.
                    attempt.receipt = receipt
                } catch LibraryStorageFailure.uncertain {
                    saveOutcome = .storageUnresolved
                    emit("The save result is unconfirmed. Check this same save before starting another.")
                    return
                } catch {
                    saveOutcome = .notPublished
                    if fence == nil { flight = .idle }
                    emit("The version was not published. Incomplete data may remain in the test library; current edits are retained.")
                    return
                }
                await acknowledge(attempt, token: token)
            } catch {
                saveOutcome = .rejected
                if fence == nil { flight = .idle }
                emit("Saving could not start. Finish or cancel any open edit, then try Save again. Current records are retained.")
            }
        }
    }
    private func acknowledge(_ attempt: SaveAttempt, token: UUID) async {
        guard let storage, let receipt = attempt.receipt else { return }
        if !attempt.storageAcknowledged {
            do {
                try await storage.acknowledge(receipt)
                attempt.storageAcknowledged = true // Engine pending receipt is now cleared.
            } catch {
                saveOutcome = .storageUnresolved
                emit("A saved version exists, but its verification is unconfirmed. Check the same save; edits remain unacknowledged.")
                return
            }
        }
        guard current(token, attempt.session) else { saveOutcome = .retired; return }
        do {
            let result = try await call(.acknowledgeSaved, attempt.id, ["revision": attempt.revision!])
            guard current(token, attempt.session), result.values["revision"] == attempt.revision else { saveOutcome = .retired; return }
            finishSaved(result, attempt: attempt)
            await refreshSavedCloseLoss(attempt)
        } catch {
            saveOutcome = .pageUnresolved
            emit("The version is stored. This view has not confirmed its saved state; check the same save before continuing.")
        }
    }
    private func refreshSavedCloseLoss(_ attempt: SaveAttempt) async {
        guard let fence = attempt.fence, flight == .close, closeID == fence else { return }
        do {
            closeLoss = try await call(.status, fence).loss
            closeUnknown = closeLoss == nil
        } catch { closeUnknown = true }
    }
    private func finishSaved(_ result: LibraryBridgeReply, attempt: SaveAttempt) {
        acknowledgedRevision = attempt.revision
        saveOutcome = result.state == "current-saved" ? .currentSaved : .earlierSaved
        if attempt.fence == nil { flight = .idle }
        emit(result.state == "current-saved" ? "Library version saved. Temporary project selections remain here and are not saved." : "An earlier library revision was saved. Your newer changes are still unsaved.")
    }
    func checkSave() {
        guard canCheckSave, let attempt = saved, let storage else { return }
        busy = true; let token = generation
        // A fresh task deliberately does not inherit the cancelled operation's
        // cancellation flag. It reconciles one attempt and never calls save.
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            if !attempt.storageAcknowledged {
                do {
                    switch try await storage.reconcile() {
                    case .published(let receipt): attempt.receipt = receipt
                    case .notPublishedPendingRetained:
                        saveOutcome = .notPublished
                        if attempt.fence == nil { flight = .idle }
                        emit("The version was not published. Its incomplete file is retained; current edits remain.")
                        return
                    }
                } catch { saveOutcome = .storageUnresolved; emit("The same save remains unconfirmed. No new write was attempted."); return }
                await acknowledge(attempt, token: token)
            } else {
                guard current(token, attempt.session) else { saveOutcome = .retired; return }
                do {
                    let reply = try await call(.savedResult, attempt.id)
                    guard current(token, attempt.session), reply.values["revision"] == attempt.revision else { throw LibraryBridgeWire.Failure.invalid }
                    if reply.state == "not-applied" { await acknowledge(attempt, token: token) }
                    else {
                        finishSaved(reply, attempt: attempt)
                        await refreshSavedCloseLoss(attempt)
                    }
                } catch { saveOutcome = .pageUnresolved; emit("The version is stored; this view's saved state is still unconfirmed.") }
            }
        }
    }

    func open() {
        guard canOpen, let storage else { return }
        let item = OpenAttempt(session: page.session), token = generation
        opened = item; flight = .open; openPhase = .listing; busy = true
        listing = nil; selected = nil; preview = nil
        emit("Checking saved version names and sizes. Contents are checked only after you select a version.")
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                let before = try await call(.status, item.id)
                if before.loss?.hasDraft == true || before.state != "idle" {
                    flight = .idle; openPhase = .none
                    emit("Finish or cancel the open edit before opening a saved version. Your draft is retained.")
                    return
                }
                let result = try await call(.prepareOpen, item.id)
                item.loss = result.loss
                guard current(token, item.session) else { return }
                if item.cancelled { await cancelOpened(item); return }
                listing = try await storage.list()
                guard current(token, item.session) else { return }
                if item.cancelled { await cancelOpened(item); return }
                openPhase = .choosing
                emit("Choose a saved version to preview. Your current library has not changed.")
            } catch {
                // prepareOpen may have fenced before its reply was lost.
                await cancelOpened(item)
                if flight == .idle { emit("Saved versions could not be listed safely. Your current library is unchanged.") }
            }
        }
    }
    func selectSaved(_ entry: SavedLibraryEntry) {
        guard canSelectSaved, let item = opened, let loss = item.loss, let storage,
              listing?.entries.contains(entry) == true else { return }
        busy = true; openPhase = .reading; selected = entry; preview = nil
        let token = generation
        emit("Checking this saved version and preparing its full location preview…")
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                if let previous = item.candidate {
                    let reply = try await call(.retireCandidate, item.id, ["candidate": previous.uuidString.lowercased()])
                    guard reply.state == "retired" else { throw LibraryBridgeWire.Failure.invalid }
                    item.candidate = nil
                }
                if item.cancelled { await cancelOpened(item); return }
                let value = try await storage.open(entry, codec: codec)
                guard current(token, item.session) else { return }
                if item.cancelled { await cancelOpened(item); return }
                let candidate = UUID(), summary = try LibraryCandidatePreview(value)
                item.candidate = candidate; item.preparedCount += 1
                _ = try await call(.prepareReplacement, item.id, ["candidate": candidate.uuidString.lowercased(),
                    "revision": loss.revision, "epoch": loss.epoch, "text": String(decoding: value.bytes, as: UTF8.self)])
                guard current(token, item.session) else { return }
                if item.cancelled { await cancelOpened(item); return }
                preview = summary; openPhase = .prepared
                emit(previewLimitReached
                    ? "Preview ready. The 128-preview limit is reached. Replace this preview, or Cancel Open and reopen to choose another version."
                    : "Preview ready. Replace changes only this open window; saved files are never overwritten.")
            } catch {
                preview = nil
                if item.candidate == nil {
                    // No preparation was sent: a rejected read/codec/summary
                    // cannot have changed the page. Keep the Open fence and
                    // allow another selection, without a fictitious result check.
                    selected = nil; openPhase = .choosing
                    emit("This saved version could not be read or validated. Your current library is unchanged. Choose another version or Cancel Open.")
                } else {
                    // A lost retirement/preparation reply may still hold a
                    // candidate. Only Cancel retires that unconfirmed preparation.
                    openPhase = .unresolved
                    emit("This version's preview is unconfirmed. Cancel Open to retain your current library.")
                }
                if item.cancelled { await cancelOpened(item) }
            }
        }
    }
    func replace() {
        guard canReplace, let item = opened, let candidate = item.candidate, let loss = item.loss else { return }
        busy = true; openPhase = .committing; item.commitInvoked = true
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                let reply = try await call(.commitReplacement, item.id, ["candidate": candidate.uuidString.lowercased(), "revision": loss.revision, "epoch": loss.epoch])
                try finishReplacement(reply, item: item)
            } catch { openPhase = .unresolved; emit("Replacement is unconfirmed. Check this same result; do not choose another version.") }
        }
    }
    private func finishReplacement(_ reply: LibraryBridgeReply, item: OpenAttempt) throws {
        guard reply.state == "committed", reply.values["candidate"] == item.candidate?.uuidString.lowercased(),
              let loss = item.loss, let revision = UInt64(loss.revision), let epoch = UInt64(loss.epoch),
              revision < LibraryBridgeWire.maximumCounter, epoch < LibraryBridgeWire.maximumCounter,
              reply.values["revision"] == String(revision + 1), reply.values["epoch"] == String(epoch + 1) else { throw LibraryBridgeWire.Failure.invalid }
        // Record commit before any window callback. A blocked render is still a
        // committed in-memory replacement, never an unchanged/cancelled result.
        openPhase = .committed; acknowledgedRevision = reply.values["revision"]
        if reply.values["view"] == "ready" { flight = .idle }
        emit(reply.values["view"] == "ready" ? "Saved library opened. Temporary selections and search/comparison state were cleared as confirmed." : "The library was replaced, but its view could not render. Close this window; saved files are unchanged.")
    }
    func checkReplacement() {
        guard canCheckReplacement, let item = opened, let candidate = item.candidate else { return }
        busy = true
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                let reply = try await call(.replacementResult, item.id, ["candidate": candidate.uuidString.lowercased()])
                if reply.state == "committed" { try finishReplacement(reply, item: item) }
                else { emit("No replacement is recorded. Cancel Open to keep your current library.") }
            } catch { emit("The same replacement result remains unconfirmed. No second replacement was sent.") }
        }
    }
    func cancelOpen() {
        guard flight == .open, let item = opened else { return }
        item.cancelled = true
        guard !busy else { emit("Cancelling Open after the current check returns…"); return }
        busy = true
        work = Task { @MainActor [self] in
            await cancelOpened(item); busy = false; work = nil; emit()
        }
    }
    private func cancelOpened(_ item: OpenAttempt) async {
        do {
            let result = try await call(.cancelOpen, item.id)
            if result.state == "committed" { try finishReplacement(result, item: item) }
            else {
                flight = .idle; openPhase = .none; preview = nil; selected = nil; listing = nil
                emit("Open cancelled. Your records, selections, searches and unfinished work are unchanged.")
            }
        } catch { openPhase = .unresolved; emit("Open's cancellation is unconfirmed. Keep this window open or explicitly discard unconfirmed temporary work.") }
    }

    func enquireClose() {
        guard flight != .closed, flight != .close else { return }
        if busy || unresolved || flight == .open {
            closeUnknown = true; closeSample = false; emit("An operation is unfinished. Check its result before closing, or explicitly discard unconfirmed temporary work.")
            return
        }
        resumeSampleAfterClose = flight == .sample
        closeSample = resumeSampleAfterClose
        flight = .close; closeLoss = nil; closeUnknown = false
        let id = UUID(); closeID = id
        // A sample review/preparation may already own the page. No clean/saved
        // inference is made; the native close sheet names the unfinished work.
        if closeSample { closeUnknown = true; emit(); return }
        busy = true
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                let reply = try await call(.prepareClose, id)
                closeLoss = reply.loss

            } catch { closeUnknown = true }
        }
    }
    func keepOpen() {
        guard !busy else { return }
        if flight != .close { closeUnknown = false; emit(); return }
        if closeSample { flight = session.state == .ready ? .idle : .sample; closeUnknown = false; closeID = nil; message = nil; emit(); return }
        guard let id = closeID else { return }
        busy = true
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do {
                _ = try await call(.releaseClose, id)
                flight = .idle; closeID = nil; closeLoss = nil; closeUnknown = false
            } catch { closeUnknown = true; emit("The close fence could not be released. Keep the window open or explicitly discard unconfirmed work.") }
        }
    }
    func saveBeforeClose() {
        guard flight == .close, !busy, !unresolved, !closeUnknown, let id = closeID,
              let loss = closeLoss, !loss.hasDraft, hasStorage else { return }
        beginSave(fence: id)
    }
    func refreshCloseLoss() {
        guard flight == .close, !busy, !unresolved, let id = closeID, !closeSample else { return }
        busy = true
        work = Task { @MainActor [self] in
            defer { busy = false; work = nil; emit() }
            do { closeLoss = try await call(.status, id).loss }
            catch { closeUnknown = true }
        }
    }
    // Caller has presented an explicit discard choice. Active IO is never cut
    // off before its result is classified; it can be checked/abandoned afterward.
    @discardableResult func finalClose() -> Bool {
        guard !busy, flight != .closed else { return flight == .closed }
        flight = .closed; generation = UUID(); session.close()
        if let storage { Task { await storage.close() } }
        emit(); return true
    }
}
