import Foundation

// Fixed runner-only comparison data derived and frozen after the actual B
// signature observation. It grants no path access and is never forwarded as
// the host's launch environment. Missing or extra reserved values refuse.
struct RunnerExpectation {
    static let prefix = "OWNED_PROBE_EXPECT_"
    static let fields = ["CDHASH", "IDENTIFIER", "EXECUTABLE", "SOURCE_COMMIT", "FIXTURE_SHA256", "FIXTURE_RUN_ID", "FIXTURE_CASE_ID"]
    let values: [String: String]

    init(environment: [String: String]) throws {
        let expectedKeys = Set(Self.fields.map { Self.prefix + $0 })
        guard Set(environment.keys.filter { $0.hasPrefix(Self.prefix) }) == expectedKeys else {
            throw ProbeFailure.refused("runner-expectation-key-set")
        }
        let selected = environment.filter { expectedKeys.contains($0.key) }
        guard selected.values.allSatisfy({ !$0.isEmpty && $0.utf8.count <= 1024 }),
              let hash = selected[Self.prefix + "CDHASH"], hash.count % 2 == 0,
              hash.range(of: "^[0-9a-f]{40,128}$", options: .regularExpression) != nil,
              selected[Self.prefix + "IDENTIFIER"] == ProbeSeal.bundleIdentifier,
              selected[Self.prefix + "EXECUTABLE"] == ProbeSeal.executablePath,
              selected[Self.prefix + "SOURCE_COMMIT"] == ProbeSeal.sourceCommit,
              selected[Self.prefix + "FIXTURE_SHA256"] == ProbeSeal.fixtureSHA256 else {
            throw ProbeFailure.refused("runner-expectation-seal-mismatch")
        }
        for key in ["FIXTURE_RUN_ID", "FIXTURE_CASE_ID"] {
            guard let value = selected[Self.prefix + key],
                  UUID(uuidString: value)?.uuidString.lowercased() == value else {
                throw ProbeFailure.refused("runner-expectation-fixture-uuid")
            }
        }
        values = selected
    }

    var cdhash: String { values[Self.prefix + "CDHASH"]! }

    func requireFixture(_ fixture: ProbeFixture) throws {
        guard values[Self.prefix + "FIXTURE_RUN_ID"] == fixture.runID,
              values[Self.prefix + "FIXTURE_CASE_ID"] == fixture.caseID else {
            throw ProbeFailure.refused("runner-expectation-fixture-mismatch")
        }
    }

    func requireIdentity(_ identity: ObservedHostIdentity, running: Bool) throws {
        guard identity.identifier == values[Self.prefix + "IDENTIFIER"],
              identity.executablePath == values[Self.prefix + "EXECUTABLE"],
              identity.codeDirectoryHash.map({ String(format: "%02x", $0) }).joined() == cdhash,
              identity.runningValidityChecked == running else {
            throw ProbeFailure.refused("runner-expectation-host-mismatch")
        }
    }
}
