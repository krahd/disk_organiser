import Foundation
import CryptoKit
import Darwin

struct ProbeFixture: Sendable {
    let runID: String
    let caseID: String
    let parent: String
    let selected: String
    let file: String
    let sibling: String
    let absent: String
    let objects: [String: ProbeObject]
    static let selectedBytes = Data("0123456789abcdef0123456789abcdef".utf8)
    static let siblingBytes = Data("fedcba9876543210fedcba9876543210".utf8)

    static func load() throws -> ProbeFixture {
        guard ProbeSeal.fixtureSHA256.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              ProbeSeal.sourceCommit.range(of: "^[0-9a-f]{40}$", options: .regularExpression) != nil,
              ProbeSeal.executablePath.hasPrefix("/"),
              let url = Bundle.main.url(forResource: "fixture", withExtension: "json") else {
            throw ProbeFailure.refused("unsealed-build")
        }
        _ = try HostIdentity.observe(expectedIdentifier: ProbeSeal.bundleIdentifier,
                                     expectedExecutable: ProbeSeal.executablePath)
        return try loadResource(url)
    }

    // The separate UI runner verifies the fixed sealed host bundle, not itself.
    // It closes every fixture descriptor before launching the sandbox process.
    static func loadForRunner(expectedCDHash: String) throws -> ProbeFixture {
        guard ProbeSeal.fixtureSHA256.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              ProbeSeal.executablePath.hasSuffix("/Contents/MacOS/OwnedFolderProbe") else {
            throw ProbeFailure.refused("unsealed-runner-build")
        }
        let executable = URL(fileURLWithPath: ProbeSeal.executablePath)
        let bundle = executable.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let observed = try HostIdentity.observeStatic(bundle: bundle, expectedIdentifier: ProbeSeal.bundleIdentifier,
                                           expectedExecutable: ProbeSeal.executablePath)
        guard observed.codeDirectoryHash.map({ String(format: "%02x", $0) }).joined() == expectedCDHash,
              !observed.runningValidityChecked else {
            throw ProbeFailure.refused("prelaunch-host-differs-from-inspected-B")
        }
        return try loadResource(bundle.appendingPathComponent("Contents/Resources/fixture.json"))
    }

    private static func loadResource(_ url: URL) throws -> ProbeFixture {
        let bytes: Data = try ProbeDescriptors.perform { ledger in
            let fd = try ledger.acquire("bundled-fixture-open") {
                url.path.withCString { Darwin.open($0, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC) }
            }
            let initial = try ledger.metadata(fd)
            guard initial.mode & UInt32(S_IFMT) == UInt32(S_IFREG),
                  initial.size > 0, initial.size <= 4096 else { throw ProbeFailure.refused("fixture-resource-type-size") }
            var bytes = [UInt8](repeating: 0, count: Int(initial.size) + 1)
            var count = 0
            for _ in 0..<64 {
                let amount = bytes.withUnsafeMutableBytes { raw in
                    read(fd, raw.baseAddress!.advanced(by: count), raw.count - count)
                }
                if amount < 0 {
                    if errno == EINTR { continue }
                    throw ProbeFailure.syscall("fixture-resource-read", errno)
                }
                if amount == 0 {
                    guard count == initial.size, initial == (try ledger.metadata(fd)) else {
                        throw ProbeFailure.refused("fixture-resource-race")
                    }
                    return Data(bytes.prefix(count))
                }
                count += amount
                guard count <= initial.size else { throw ProbeFailure.refused("fixture-resource-overflow") }
            }
            throw ProbeFailure.refused("fixture-resource-attempt-budget")
        }
        let digest = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        guard digest == ProbeSeal.fixtureSHA256 else { throw ProbeFailure.refused("fixture-resource-digest") }
        // The Stage B producer must first admit these exact bytes with the
        // existing Python fixture contract; the signature and fixed digest bind
        // that reviewed input, never arbitrary imported JSON.
        return try decode(bytes)
    }

    static func decode(_ data: Data) throws -> ProbeFixture {
        guard !data.isEmpty, data.count <= 4096,
              let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw ProbeFailure.refused("fixture-shape")
        }
        let keys: Set<String> = ["schemaVersion", "runID", "caseID", "bundleIdentifier", "fixtureParent",
                                 "selectedPath", "selectedFile", "siblingFile", "absentPath", "objects",
                                 "selectedBytesHex", "siblingBytesHex"]
        guard Set(value.keys) == keys, try integer(value["schemaVersion"]) == 1,
              let run = value["runID"] as? String, let caseID = value["caseID"] as? String,
              UUID(uuidString: run)?.uuidString.lowercased() == run,
              UUID(uuidString: caseID)?.uuidString.lowercased() == caseID,
              let parent = value["fixtureParent"] as? String,
              parent.hasPrefix("/private/tmp/disk-selection-owned-"), parent.utf8.count <= 1024,
              !parent.contains("\\"), !parent.hasSuffix("/"),
              parent.split(separator: "/", omittingEmptySubsequences: false).dropFirst().allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              !parent.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }),
              value["bundleIdentifier"] as? String == "org.diskorganiser.owned-selection-probe." + caseID,
              value["bundleIdentifier"] as? String == ProbeSeal.bundleIdentifier,
              value["selectedBytesHex"] as? String == selectedBytes.map({ String(format: "%02x", $0) }).joined(),
              value["siblingBytesHex"] as? String == siblingBytes.map({ String(format: "%02x", $0) }).joined() else {
            throw ProbeFailure.refused("fixture-coordinates")
        }
        let selected = parent + "/selected", file = selected + "/probe.bin"
        let sibling = parent + "/outside/sentinel.bin", absent = selected + "/must-remain-absent.bin"
        for (key, expected) in [("selectedPath", selected), ("selectedFile", file), ("siblingFile", sibling), ("absentPath", absent)] {
            guard value[key] as? String == expected else { throw ProbeFailure.refused("fixture-derived-path") }
        }
        guard let raw = value["objects"] as? [String: Any],
              Set(raw.keys) == ["parent", "selected", "selectedFile", "siblingFile"] else {
            throw ProbeFailure.refused("fixture-object-set")
        }
        var objects: [String: ProbeObject] = [:]
        for (name, item) in raw {
            guard let fields = item as? [String: Any], Set(fields.keys) == ["device", "inode", "mode", "uid", "gid", "size"] else {
                throw ProbeFailure.refused("fixture-object-shape")
            }
            let device = try integer(fields["device"]), inode = try integer(fields["inode"])
            let mode = try integer(fields["mode"]), uid = try integer(fields["uid"]), gid = try integer(fields["gid"]), size = try integer(fields["size"])
            let directory = name == "parent" || name == "selected"
            guard device <= UInt64(Int64.max), size <= UInt64(Int64.max), uid <= UInt64(UInt32.max), gid <= UInt64(UInt32.max),
                  mode == UInt64(directory ? S_IFDIR | 0o700 : S_IFREG | 0o600), directory || size == 32 else {
                throw ProbeFailure.refused("fixture-object-range")
            }
            objects[name] = ProbeObject(device: Int64(device), inode: inode, mode: UInt32(mode), uid: UInt32(uid), gid: UInt32(gid), size: Int64(size))
        }
        guard Set(objects.values.map { "\($0.device):\($0.inode)" }).count == 4,
              Set(objects.values.map { "\($0.device):\($0.uid):\($0.gid)" }).count == 1 else {
            throw ProbeFailure.refused("fixture-object-alias")
        }
        return ProbeFixture(runID: run, caseID: caseID, parent: parent, selected: selected,
                            file: file, sibling: sibling, absent: absent, objects: objects)
    }

    private static func integer(_ value: Any?) throws -> UInt64 {
        guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
              number.stringValue.range(of: "^(0|[1-9][0-9]*)$", options: .regularExpression) != nil,
              let integer = UInt64(number.stringValue) else { throw ProbeFailure.refused("fixture-integer") }
        return integer
    }
}
