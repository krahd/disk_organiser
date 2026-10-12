import XCTest
import AppKit
import Foundation
import Darwin

@MainActor
final class SelectionProbeUITests: XCTestCase {
    private var app: XCUIApplication!
    private var launchedPID: pid_t = 0
    private var launchedIdentity: ObservedHostIdentity?
    private var fixture: ProbeFixture!
    private var expectedIdentity: RunnerExpectation!

    override func setUpWithError() throws {
        continueAfterFailure = false
        try assertPurePolicies()
        guard ProbeSeal.fixtureSHA256.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              ProbeSeal.sourceCommit.range(of: "^[0-9a-f]{40}$", options: .regularExpression) != nil,
              ProbeSeal.selectedPath.hasPrefix("/private/tmp/disk-selection-owned-"),
              ProbeSeal.executablePath.hasPrefix("/") else {
            throw ProbeFailure.refused("unsealed-test-build")
        }
        expectedIdentity = try RunnerExpectation(environment: ProcessInfo.processInfo.environment)
        fixture = try ProbeFixture.loadForRunner(expectedCDHash: expectedIdentity.cdhash)
        try expectedIdentity.requireFixture(fixture)
        try FixtureProof.verify(fixture)
        app = XCUIApplication(bundleIdentifier: ProbeSeal.bundleIdentifier)
        app.launchArguments = []
        app.launchEnvironment = [:]
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        let running = NSRunningApplication.runningApplications(withBundleIdentifier: ProbeSeal.bundleIdentifier)
        XCTAssertEqual(running.count, 1)
        let process = try XCTUnwrap(running.first)
        XCTAssertEqual(process.executableURL?.path, ProbeSeal.executablePath)
        XCTAssertTrue(process.isFinishedLaunching)
        launchedPID = process.processIdentifier
        launchedIdentity = try HostIdentity.observe(process: launchedPID,
                                                   expectedIdentifier: ProbeSeal.bundleIdentifier,
                                                   expectedExecutable: ProbeSeal.executablePath)
        // Reject a different actually launched guest before any Choose/panel
        // action, even if path, identifier and entitlements still agree.
        try expectedIdentity.requireIdentity(try XCTUnwrap(launchedIdentity), running: true)
        try emit("OWNED_SELECTION_PROCESS ", ["method": currentMethod(), "sourceCommit": ProbeSeal.sourceCommit,
                                               "runID": fixture.runID, "caseID": fixture.caseID,
                                               "runnerPID": ProcessInfo.processInfo.processIdentifier, "hostPID": launchedPID])
        XCTAssertTrue(waitStatus("READY_DENIED"))
    }

    override func tearDownWithError() throws {
        // Cleanup never contributes an acceptance assertion. The experiment
        // driver separately observes the launched PID's bounded retirement.
        app?.terminate()
        app = nil
    }


    private func currentMethod() throws -> String {
        let methods = ["testSelectedReadSucceedsOnlyDuringScope", "testGenuinePanelCancellationRetiresWithoutSelection",
                       "testActiveReadCancelRetiresBeforeRetry"]
        let matching = methods.filter { name.contains($0) }
        XCTAssertEqual(matching.count, 1)
        return "SelectionProbeUITests/" + (try XCTUnwrap(matching.first))
    }

    private func emit(_ marker: String, _ value: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        XCTAssertLessThanOrEqual(data.count, 4096)
        print(marker + (try XCTUnwrap(String(data: data, encoding: .utf8))))
    }

    private func completedCase() throws {
        try emit("OWNED_SELECTION_CASE ", ["method": currentMethod(), "sourceCommit": ProbeSeal.sourceCommit,
                                            "runID": fixture.runID, "caseID": fixture.caseID])
    }

    private func assertPurePolicies() throws {
        let uuid = "11111111-1111-4111-8111-111111111111"
        var environment = Dictionary(uniqueKeysWithValues: zip(RunnerExpectation.fields.map { RunnerExpectation.prefix + $0 },
            [String(repeating: "a", count: 40), ProbeSeal.bundleIdentifier, ProbeSeal.executablePath,
             ProbeSeal.sourceCommit, ProbeSeal.fixtureSHA256, uuid, uuid]))
        let expected = try RunnerExpectation(environment: environment)
        let good = ObservedHostIdentity(identifier: ProbeSeal.bundleIdentifier, executablePath: ProbeSeal.executablePath,
                                       codeDirectoryHash: Data(repeating: 0xaa, count: 20), runningValidityChecked: true)
        try expected.requireIdentity(good, running: true)
        XCTAssertThrowsError(try expected.requireIdentity(ObservedHostIdentity(identifier: good.identifier,
            executablePath: good.executablePath, codeDirectoryHash: Data(repeating: 0xbb, count: 20), runningValidityChecked: true), running: true))
        XCTAssertThrowsError(try expected.requireIdentity(good, running: false))
        for key in RunnerExpectation.fields {
            var missing = environment; missing.removeValue(forKey: RunnerExpectation.prefix + key)
            XCTAssertThrowsError(try RunnerExpectation(environment: missing))
        }
        for key in ["IDENTIFIER", "EXECUTABLE", "SOURCE_COMMIT", "FIXTURE_SHA256"] {
            var changed = environment; changed[RunnerExpectation.prefix + key] = "changed"
            XCTAssertThrowsError(try RunnerExpectation(environment: changed))
        }
        environment[RunnerExpectation.prefix + "UNEXPECTED"] = "refuse"
        XCTAssertThrowsError(try RunnerExpectation(environment: environment))
        XCTAssertEqual(ProbePolicy.completedOutcome(cancelAccepted: false), "passed")
        // Terminal-success / accepted Cancel / pending main-actor publication.
        XCTAssertEqual(ProbePolicy.completedOutcome(cancelAccepted: true), "read-cancelled")
        for operations in [ProbePolicy.selectedOperations] + ProbePolicy.activeOperations {
            for operation in operations {
                for code in [EACCES, EPERM] {
                    XCTAssertEqual(ProbePolicy.denial(ProbeFailure.syscall(operation, code), operations: operations),
                                   ObservedDenial(operation: operation, code: code))
                }
                for code in [ENOENT, EEXIST, EIO] {
                    XCTAssertNil(ProbePolicy.denial(ProbeFailure.syscall(operation, code), operations: operations))
                }
            }
            for operation in ["fstat", "fstatx_np", "filesec_init", "filesec_query", "other-operation"] {
                for code in [EACCES, EPERM] {
                    XCTAssertNil(ProbePolicy.denial(ProbeFailure.syscall(operation, code), operations: operations))
                }
            }
            XCTAssertNil(ProbePolicy.denial(ProbeFailure.cleanup("close", EPERM), operations: operations))
            XCTAssertNil(ProbePolicy.denial(ProbeFailure.refused("invalid-acl"), operations: operations))
        }
    }

    private func waitStatus(_ prefix: String) -> Bool {
        let label = app.staticTexts["probe-status"]
        return XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: NSPredicate(format: "value BEGINSWITH %@ OR label BEGINSWITH %@", prefix, prefix), object: label)], timeout: 8) == .completed
    }

    private func click(_ id: String) throws {
        let button = app.buttons[id]
        XCTAssertTrue(button.waitForExistence(timeout: 5))
        XCTAssertTrue(button.isEnabled)
        XCTAssertTrue(button.isHittable)
        XCTAssertGreaterThan(button.frame.width, 0)
        XCTAssertGreaterThan(button.frame.height, 0)
        button.click()
    }

    private func chooseFixture() throws {
        try click("probe-choose")
        let sheet = app.sheets.firstMatch
        XCTAssertTrue(sheet.waitForExistence(timeout: 5))
        // Genuine standard-panel navigation. No synthetic OK completion, URL
        // injection or fallback path opens are allowed if the panel differs.
        app.typeKey("g", modifierFlags: [.command, .shift])
        let goSheet = sheet.sheets.firstMatch
        XCTAssertTrue(goSheet.waitForExistence(timeout: 5))
        XCTAssertTrue(goSheet.staticTexts["Go to the folder:"].exists)
        XCTAssertEqual(goSheet.textFields.count, 1)
        let pathField = goSheet.textFields.firstMatch
        XCTAssertTrue(pathField.waitForExistence(timeout: 5))
        XCTAssertTrue(pathField.isHittable)
        pathField.click(); app.typeKey("a", modifierFlags: .command)
        pathField.typeText(ProbeSeal.selectedPath)
        app.typeKey(.return, modifierFlags: [])
        let confirm = sheet.buttons["Choose owned fixture"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 5))
        XCTAssertTrue(confirm.isEnabled && confirm.isHittable)
        confirm.click()
        XCTAssertTrue(waitStatus("REVIEW_OWNED"))
    }

    private func terminal(_ outcome: String, image: String) throws {
        XCTAssertTrue(waitStatus("RETIRED_DENIED"))
        let control = app.staticTexts["probe-receipt"]
        let text = (control.value as? String) ?? control.label
        XCTAssertLessThanOrEqual(text.utf8.count, 2048)
        let data = try XCTUnwrap(text.data(using: .utf8))
        let receipt = try XCTUnwrap(try JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertEqual(receipt["outcome"] as? String, outcome)
        XCTAssertEqual(receipt["sourceCommit"] as? String, ProbeSeal.sourceCommit)
        XCTAssertEqual(receipt["runID"] as? String, fixture.runID)
        XCTAssertEqual(receipt["caseID"] as? String, fixture.caseID)
        XCTAssertEqual(receipt["pid"] as? Int32, launchedPID)
        XCTAssertTrue([EACCES, EPERM].contains(try XCTUnwrap(receipt["beforeErrno"] as? Int32)))
        XCTAssertTrue([EACCES, EPERM].contains(try XCTUnwrap(receipt["afterErrno"] as? Int32)))
        XCTAssertEqual(receipt["error"] as? String, "")
        XCTAssertEqual(receipt["runningValidityChecked"] as? Bool, true)
        let controls = try XCTUnwrap(receipt["activeControls"] as? [[String: Any]])
        XCTAssertEqual(controls.count, outcome == "panel-cancelled" ? 0 : 4)
        XCTAssertEqual(receipt["positiveReadReachedControls"] as? Bool, outcome != "panel-cancelled")
        for (index, control) in controls.enumerated() {
            XCTAssertTrue(ProbePolicy.activeOperations[index].contains(try XCTUnwrap(control["operation"] as? String)))
            XCTAssertTrue([EACCES, EPERM].contains(try XCTUnwrap(control["errno"] as? Int32)))
        }
        for name in ["beforeOperation", "afterOperation"] {
            XCTAssertTrue(ProbePolicy.selectedOperations.contains(try XCTUnwrap(receipt[name] as? String)))
        }
        for flag in ["borrowedWorkerRetired", "scopeRetired", "panelRetired"] {
            XCTAssertEqual(receipt[flag] as? Bool, true)
        }
        let now = try HostIdentity.observe(process: launchedPID, expectedIdentifier: ProbeSeal.bundleIdentifier,
                                           expectedExecutable: ProbeSeal.executablePath)
        try expectedIdentity.requireIdentity(now, running: true)
        XCTAssertEqual(now.codeDirectoryHash, launchedIdentity?.codeDirectoryHash)
        XCTAssertEqual(receipt["observedCDHash"] as? String,
                       now.codeDirectoryHash.map { String(format: "%02x", $0) }.joined())
        XCTAssertEqual(receipt["observedExecutable"] as? String, ProbeSeal.executablePath)
        XCTAssertEqual(receipt["observedIdentifier"] as? String, ProbeSeal.bundleIdentifier)
        // This unsandboxed test-owned proof is distinct from the host denial.
        // It binds existing objects/bytes/absence and retires its own FDs before
        // any next panel action; no descriptor is passed to the host.
        try FixtureProof.verify(fixture)
        let original = try OriginalCapture.write(app.windows.firstMatch, name: image)
        let capture = XCTAttachment(screenshot: original.screenshot)
        capture.name = image; capture.lifetime = .keepAlways; add(capture)
        try emit("OWNED_SELECTION_UI_RECEIPT ", ["method": currentMethod(), "capture": image, "captureSHA256": original.digest,
                                                   "captureBytes": original.byteCount, "pixelWidth": original.width,
                                                   "pixelHeight": original.height, "receipt": receipt])
    }

    func testSelectedReadSucceedsOnlyDuringScope() throws {
        try chooseFixture()
        try click("probe-read")
        XCTAssertTrue(waitStatus("HELD_READ"))
        try click("probe-finish")
        try terminal("passed", image: "100-selected-read-retired")
        try completedCase()
    }

    func testGenuinePanelCancellationRetiresWithoutSelection() throws {
        try click("probe-choose")
        let sheet = app.sheets.firstMatch
        XCTAssertTrue(sheet.waitForExistence(timeout: 5))
        let cancel = sheet.buttons["Cancel"]
        XCTAssertTrue(cancel.waitForExistence(timeout: 5))
        XCTAssertTrue(cancel.isHittable && cancel.isEnabled)
        cancel.click()
        try terminal("panel-cancelled", image: "101-panel-cancelled")
        try completedCase()
    }

    func testActiveReadCancelRetiresBeforeRetry() throws {
        try chooseFixture()
        try click("probe-read")
        XCTAssertTrue(waitStatus("HELD_READ"))
        try click("probe-cancel")
        try terminal("read-cancelled", image: "102-active-cancelled")
        try chooseFixture()
        try click("probe-read")
        XCTAssertTrue(waitStatus("HELD_READ"))
        try click("probe-finish")
        try terminal("passed", image: "103-retry-retired")
        try completedCase()
    }
}
