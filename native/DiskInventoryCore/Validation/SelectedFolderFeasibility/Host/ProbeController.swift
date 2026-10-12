import AppKit
import Foundation

@MainActor
final class ProbeController: NSObject, NSWindowDelegate {
    enum Phase { case checking, ready, choosing, reviewing, reading, holding, stopping, retiring, done, failed, closed }
    private(set) var phase = Phase.checking
    private let fixture: ProbeFixture
    private let window: NSWindow
    private let status: NSTextField
    private let receipt: NSTextField
    private let choose: NSButton
    private let read: NSButton
    private let finish: NSButton
    private let cancel: NSButton
    private var panel: NSOpenPanel?
    private var scope: ProbePanelScope?
    private var work: ProbeWork?
    private var generation: UInt64 = 0
    private var stopping = false
    private var closeRequested = false
    private var mayClose = false
    private var preDenial: ObservedDenial?
    private var activeDenials: [ObservedDenial] = []

    init(fixture: ProbeFixture, window: NSWindow, status: NSTextField, receipt: NSTextField,
         choose: NSButton, read: NSButton, finish: NSButton, cancel: NSButton) {
        self.fixture = fixture; self.window = window; self.status = status; self.receipt = receipt
        self.choose = choose; self.read = read; self.finish = finish; self.cancel = cancel
        super.init()
        window.delegate = self
        for (button, action) in [(choose, #selector(chooseFolder)), (read, #selector(readSelected)),
                                 (finish, #selector(finishRead)), (cancel, #selector(cancelCurrent))] {
            button.target = self; button.action = action
        }
        preflight(thenChoose: false)
    }

    private func show(_ next: Phase, _ text: String) {
        phase = next; status.stringValue = text
        choose.isEnabled = next == .ready || next == .done
        read.isEnabled = next == .reviewing
        finish.isEnabled = next == .holding
        cancel.isEnabled = next == .choosing || next == .reviewing || next == .reading || next == .holding
    }
    private func fail(_ error: String) {
        show(.failed, "FAILED: " + error)
        _ = writeReceipt(outcome: "failed", after: nil, error: error)
        if closeRequested { closeNow() }
    }
    private func preflight(thenChoose: Bool) {
        guard work == nil, scope == nil, panel == nil else { fail("overlapping-preflight"); return }
        generation &+= 1
        let token = generation, fixture = fixture
        stopping = false; preDenial = nil; activeDenials = []; receipt.stringValue = ""
        show(.checking, "Checking the sealed owned fixture before selection…")
        DispatchQueue(label: "org.diskorganiser.owned-selection-probe.before").async { [weak self] in
            let result: Result<ObservedDenial, Error> = Result { try ProbeMatrix.selectedDenied(fixture) }
            Task { @MainActor [weak self] in
                guard let self, generation == token, phase == .checking else { return }
                switch result {
                case .success(let denied):
                    preDenial = denied
                    if closeRequested { closeNow(); return }
                    show(.ready, "READY_DENIED · the owned selected-file read is denied before selection.")
                    if thenChoose { chooseFolder() }
                case .failure(let error): fail(ProbeWork.failureCode(error))
                }
            }
        }
    }

    @objc private func chooseFolder() {
        if phase == .done { preflight(thenChoose: true); return }
        guard phase == .ready, preDenial != nil, panel == nil, scope == nil, work == nil else { return }
        stopping = false
        show(.choosing, "Choose only the sealed temporary test folder, or Cancel.")
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false
        panel.allowsMultipleSelection = false; panel.canCreateDirectories = false
        panel.resolvesAliases = false; panel.treatsFilePackagesAsDirectories = false
        panel.prompt = "Choose owned fixture"
        panel.message = "Isolated feasibility test. Only the sealed test-created folder is eligible."
        self.panel = panel
        let token = generation
        panel.beginSheetModal(for: window) { [weak self, panel] response in
            Task { @MainActor [weak self, panel] in
                // Adopt every successful returned scope before any validation.
                let choices = response == .OK ? panel.urls.map { ProbePanelScope(panelURL: $0) } : []
                guard let self, generation == token, self.panel === panel else {
                    choices.forEach { $0.retire() }; return
                }
                self.panel = nil
                guard !stopping, response == .OK else {
                    choices.forEach { $0.retire() }
                    afterRetirement(outcome: "panel-cancelled"); return
                }
                guard choices.count == 1, choices[0].matches(fixture.selected) else {
                    choices.forEach { $0.retire() }; fail("unexpected-selection"); return
                }
                scope = choices[0]
                show(.reviewing, "REVIEW_OWNED · one sealed folder selected. Run the bounded read or Cancel.")
            }
        }
    }

    @objc private func readSelected() {
        guard phase == .reviewing, let selected = scope, work == nil else { return }
        let operation = ProbeWork(), token = generation
        work = operation
        show(.reading, "Reading the 32-byte owned control and checking denied operations…")
        let began = operation.start(fixture: fixture, onHolding: { @Sendable [weak self, weak operation] in
            Task { @MainActor [weak self, weak operation] in
                guard let self, let operation, generation == token, work === operation,
                      phase == .reading, operation.isHolding else { return }
                show(.holding, "HELD_READ · positive read passed; the worker still owns its descriptors. Finish or Cancel.")
            }
        }, completion: { @Sendable [weak self, selected, operation] result in
            // The retained selected owner outlives the borrowed worker even if
            // its window/controller is abandoned. No cancellation closes it.
            Task { @MainActor [weak self, selected, operation] in
                selected.retire()
                guard let self, generation == token, work === operation else { return }
                scope = nil; work = nil
                switch result {
                case .completed(let controls):
                    activeDenials = controls; afterRetirement(outcome: ProbePolicy.completedOutcome(cancelAccepted: stopping))
                case .cancelled(let controls):
                    activeDenials = controls; afterRetirement(outcome: "read-cancelled")
                case .failed(let code): fail(code)
                }
            }
        })
        if !began { work = nil; scope = nil; selected.retire(); fail("worker-reused") }
    }

    @objc private func finishRead() { if phase == .holding { work?.resume() } }

    @objc private func cancelCurrent() {
        stopping = true
        switch phase {
        case .choosing:
            show(.stopping, "Waiting for the native panel to retire…")
            panel?.cancel(nil)
        case .reviewing:
            scope?.retire(); scope = nil
            afterRetirement(outcome: "review-cancelled")
        case .reading, .holding:
            show(.stopping, "Waiting for the observing worker to retire its descriptors…")
            work?.cancel()
        default: break
        }
    }

    private func afterRetirement(outcome: String) {
        guard scope == nil, work == nil, panel == nil else { fail("retirement-order"); return }
        let token = generation, fixture = fixture
        show(.retiring, "Checking the identical selected-file read after scope retirement…")
        DispatchQueue(label: "org.diskorganiser.owned-selection-probe.after").async { [weak self] in
            let result: Result<ObservedDenial, Error> = Result { try ProbeMatrix.selectedDenied(fixture) }
            Task { @MainActor [weak self] in
                guard let self, generation == token, phase == .retiring else { return }
                switch result {
                case .success(let denied):
                    guard writeReceipt(outcome: outcome, after: denied, error: nil) else {
                        show(.failed, "FAILED: terminal signature or receipt validation")
                        if closeRequested { closeNow() }
                        return
                    }
                    show(.done, "RETIRED_DENIED · " + outcome + ". The identical selected-file read is denied again.")
                    if closeRequested { closeNow() }
                case .failure(let error): fail(ProbeWork.failureCode(error))
                }
            }
        }
    }

    private func writeReceipt(outcome: String, after: ObservedDenial?, error: String?) -> Bool {
        let identity: ObservedHostIdentity
        do {
            identity = try HostIdentity.observe(expectedIdentifier: ProbeSeal.bundleIdentifier,
                                                expectedExecutable: ProbeSeal.executablePath)
        } catch {
            receipt.stringValue = "RECEIPT_SIGNATURE_FAILED"
            print("OWNED_SELECTION_RECEIPT_FAILED signature")
            return false
        }
        let values: [String: Any] = ["schemaVersion": 1, "runID": fixture.runID, "caseID": fixture.caseID,
                                  "sourceCommit": ProbeSeal.sourceCommit, "pid": ProcessInfo.processInfo.processIdentifier,
                                  "observedIdentifier": identity.identifier, "observedExecutable": identity.executablePath,
                                  "observedCDHash": identity.codeDirectoryHash.map { String(format: "%02x", $0) }.joined(),
                                  "runningValidityChecked": identity.runningValidityChecked,
                                  "activeControls": activeDenials.map { ["operation": $0.operation, "errno": $0.code] as [String: Any] },
                                  "positiveReadReachedControls": activeDenials.count == 4,
                                  "outcome": outcome, "beforeOperation": preDenial?.operation ?? "missing",
                                  "beforeErrno": preDenial?.code ?? 0, "afterOperation": after?.operation ?? "missing",
                                  "afterErrno": after?.code ?? 0, "error": error ?? "", "borrowedWorkerRetired": work == nil,
                                  "scopeRetired": scope == nil, "panelRetired": panel == nil]
        guard let data = try? JSONSerialization.data(withJSONObject: values, options: [.sortedKeys]),
              data.count <= 2048, let text = String(data: data, encoding: .utf8) else {
            receipt.stringValue = "RECEIPT_ENCODING_FAILED"; return false
        }
        receipt.stringValue = text
        print("OWNED_SELECTION_RECEIPT " + text)
        return true
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if mayClose { return true }
        closeRequested = true
        switch phase {
        case .ready, .done, .failed: closeNow()
        case .choosing, .reviewing, .reading, .holding: cancelCurrent()
        default: break // An admitted before/after operation must return first.
        }
        return false
    }
    private func closeNow() {
        guard scope == nil, work == nil, panel == nil else { return }
        mayClose = true; phase = .closed; window.close()
    }
}
