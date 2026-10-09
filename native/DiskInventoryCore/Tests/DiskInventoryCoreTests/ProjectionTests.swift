import XCTest
import Foundation
import Darwin
@testable import DiskInventoryCore

final class ProjectionTests: XCTestCase {
    private let stamp = "2026-10-09T09:00:00.123456Z"
    private let scanID = "scan_0123456789abcdef01234567"

    private func rootInventory() -> Inventory {
        Inventory(entries: [InventoryEntry(path: Data(".".utf8), kind: .directory)])
    }

    private func encode(_ inventory: Inventory, label: String = "Owned fixture") throws -> Data {
        try SnapshotProjection.encode(inventory, label: label, stamp: stamp, scanID: scanID)
    }

    func testByteExactUnicodeKeysCaseAndNonBMPDoNotCollapse() throws {
        let names = ["é", "e\u{301}", "A", "a", "🧪", "prefix\u{301}\u{301}"]
        var inventory = rootInventory()
        for name in names {
            inventory.entries.append(InventoryEntry(path: Data(name.utf8), kind: .file, logicalBytes: "1"))
        }
        let data = try encode(inventory)
        let value = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let entries = try XCTUnwrap(value["entries"] as? [[String: Any]])
        let bytes = entries.compactMap { ($0["path"] as? String).map { Data($0.utf8) } }
        let expected = ([Data(".".utf8)] + names.map { Data($0.utf8) }).sorted { $0.lexicographicallyPrecedes($1) }
        XCTAssertEqual(bytes, expected)
        XCTAssertEqual(bytes.count, 7)
        XCTAssertNotEqual(Data(names[0].utf8), Data(names[1].utf8))
    }

    func testParentsUseExactBytesAndRejectCanonicallyEquivalentSubstitute() throws {
        var inventory = rootInventory()
        inventory.entries.append(InventoryEntry(path: Data("é".utf8), kind: .directory))
        inventory.entries.append(InventoryEntry(path: Data("e\u{301}/file".utf8), kind: .file, logicalBytes: "0"))
        XCTAssertThrowsError(try encode(inventory))
        inventory.entries.append(InventoryEntry(path: Data("e\u{301}".utf8), kind: .directory))
        XCTAssertNoThrow(try encode(inventory))
    }

    func testInvalidUTF8ControlsWhitespaceAndAmbiguousPathsReject() throws {
        let bad: [Data] = [Data([0xFF]), Data([0xED, 0xA0, 0x80]), Data([0xC0, 0xAF]),
            Data(" ".utf8), Data("\u{FEFF}".utf8), Data("\u{80}".utf8), Data("\u{2028}".utf8),
            Data("\u{2029}".utf8), Data([0]), Data("back\\slash".utf8), Data("/absolute".utf8),
            Data("a//b".utf8), Data("a/../b".utf8), Data("a/./b".utf8), Data("a/".utf8)]
        for name in bad {
            var inventory = rootInventory()
            inventory.entries.append(InventoryEntry(path: name, kind: .file, logicalBytes: "0"))
            XCTAssertThrowsError(try encode(inventory), "Must reject raw bytes \(name as NSData)")
        }
        for label in ["", " ", "\u{FEFF}", "\u{7F}", "\u{85}", "a\u{2028}b"] {
            XCTAssertThrowsError(try encode(rootInventory(), label: label))
        }
    }

    func testScalarLimitsAreNotGraphemeOrUTF16Counts() throws {
        let scalar240 = String(repeating: "e\u{301}", count: 120)
        XCTAssertNoThrow(try encode(rootInventory(), label: scalar240))
        XCTAssertThrowsError(try encode(rootInventory(), label: scalar240 + "x"))
        XCTAssertNoThrow(try encode(rootInventory(), label: String(repeating: "🧪", count: 240)))
        var inventory = rootInventory()
        inventory.entries.append(InventoryEntry(path: Data(String(repeating: "e\u{301}", count: 512).utf8), kind: .file, logicalBytes: "0"))
        XCTAssertNoThrow(try encode(inventory))
        inventory.entries.append(InventoryEntry(path: Data(String(repeating: "x", count: 1_025).utf8), kind: .file, logicalBytes: "0"))
        XCTAssertThrowsError(try encode(inventory))
    }

    func testCanonicalDecimalEdgesAndFileKindRules() throws {
        for size in ["0", "1", String(repeating: "9", count: 30), String(Int64.max)] {
            var inventory = rootInventory()
            inventory.entries.append(InventoryEntry(path: Data("file".utf8), kind: .file, logicalBytes: size))
            XCTAssertNoThrow(try encode(inventory))
        }
        for size in ["-1", "00", "01", "+1", "1.0", "1e3", "١", String(repeating: "9", count: 31), ""] {
            var inventory = rootInventory()
            inventory.entries.append(InventoryEntry(path: Data("file".utf8), kind: .file, logicalBytes: size))
            XCTAssertThrowsError(try encode(inventory))
        }
        var bad = rootInventory()
        bad.entries.append(InventoryEntry(path: Data("directory".utf8), kind: .directory, logicalBytes: "0"))
        XCTAssertThrowsError(try encode(bad))
    }

    func testTimestampUsesASCIIDigitsAndExactCalendarRules() throws {
        for valid in ["2000-02-29T23:59:59Z", "2026-10-09T09:00:00.000001-00:00", "0001-01-01T00:00:00+23:59"] {
            XCTAssertNoThrow(try SnapshotProjection.timestamp(valid))
        }
        for invalid in ["1900-02-29T00:00:00Z", "0000-01-01T00:00:00Z", "2026-04-31T00:00:00Z",
            "2026-10-09T24:00:00Z", "2026-10-09T09:00:60Z", "2026-10-09T09:00:00+24:00",
            "2026-10-09T09:00:00+00:60", "2026-10-09T09:00:00.1234567Z", "2026-10-09T09:00:00.١Z",
            "٢٠٢٦-10-09T09:00:00Z", "2026-10-09T09:00:00Z\n"] {
            XCTAssertThrowsError(try SnapshotProjection.timestamp(invalid), invalid)
        }
    }

    func testExactSnapshotByteBoundaryIsCountedBeforeMaterialisation() throws {
        var inventory = rootInventory()
        for index in 0..<999 {
            let path = String(format: "f%04d", index) + String(repeating: "x", count: 895)
            inventory.entries.append(InventoryEntry(path: Data(path.utf8), kind: .file, logicalBytes: "0"))
        }
        let initial = try encode(inventory)
        var remaining = Bounds.snapshotBytes - initial.count
        XCTAssertGreaterThan(remaining, 0)
        for index in 1..<inventory.entries.count where remaining > 0 {
            let old = inventory.entries[index]
            let added = min(1_024 - old.path.count, remaining)
            inventory.entries[index] = InventoryEntry(path: old.path + Data(repeating: 120, count: added), kind: .file, logicalBytes: "0")
            remaining -= added
        }
        XCTAssertEqual(remaining, 0)
        XCTAssertEqual(try encode(inventory).count, Bounds.snapshotBytes)
        let index = try XCTUnwrap(inventory.entries.indices.dropFirst().first { inventory.entries[$0].path.count < 1_024 })
        let old = inventory.entries[index]
        inventory.entries[index] = InventoryEntry(path: old.path + Data([120]), kind: .file, logicalBytes: "0")
        XCTAssertThrowsError(try encode(inventory))
    }

    func testGapMapAloneCannotClaimCompleteAndBoundsReject() throws {
        var inventory = rootInventory()
        inventory.exclusions[Data("depth_limit".utf8)] = 1
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encode(inventory)) as? [String: Any])
        XCTAssertEqual((object["source"] as? [String: String])?["coverage"], "partial")
        inventory.errorCount = 2_001
        XCTAssertThrowsError(try encode(inventory))
        inventory.errorCount = 0
        inventory.exclusions[Data("depth_limit".utf8)] = 0
        XCTAssertThrowsError(try encode(inventory))
        inventory.exclusions = Dictionary(uniqueKeysWithValues: (0..<33).map { (Data("reason\($0)".utf8), 1) })
        XCTAssertThrowsError(try encode(inventory))
    }

    func testExclusionLimitLatchesAndDoesNotDropSilently() {
        var inventory = rootInventory()
        for _ in 0..<2_000 { inventory.exclude("depth_limit") }
        XCTAssertNil(inventory.stopReason)
        inventory.exclude("depth_limit")
        XCTAssertEqual(inventory.stopReason, "exclusion_limit")
        XCTAssertEqual(inventory.exclusions[Data("depth_limit".utf8)], 2_000)
    }

    func testRootDuplicateMissingParentAndWrongRootStatusReject() throws {
        var inventory = rootInventory()
        inventory.entries.append(inventory.entries[0])
        XCTAssertThrowsError(try encode(inventory))
        inventory = rootInventory()
        inventory.entries[0].status = .stale
        XCTAssertThrowsError(try encode(inventory))
        inventory = rootInventory()
        inventory.entries.append(InventoryEntry(path: Data("missing/child".utf8), kind: .file, logicalBytes: "1"))
        XCTAssertThrowsError(try encode(inventory))
        inventory = Inventory()
        XCTAssertThrowsError(try encode(inventory))
    }

    func testFingerprintNanosecondsAndFullFieldsAreChecked() throws {
        let original = Fingerprint(device: 0, inode: UInt64.max, size: Int64.max,
            modificationSeconds: Int64.min, modificationNanoseconds: 999_999_999,
            changeSeconds: Int64.max, changeNanoseconds: 0, mode: UInt32(S_IFREG) | 0o644, links: UInt64.max)
        XCTAssertNoThrow(try Metadata(fingerprint: original))
        let invalid = Fingerprint(device: 0, inode: 1, size: 0,
            modificationSeconds: 0, modificationNanoseconds: 1_000_000_000,
            changeSeconds: 0, changeNanoseconds: -1, mode: UInt32(S_IFREG), links: 1)
        XCTAssertThrowsError(try Metadata(fingerprint: invalid))
    }

    func testHardlinkConflictsAndStaleAliasesIncludeZeroDevice() throws {
        let fingerprint = Fingerprint(device: 0, inode: 17, size: 3, modificationSeconds: 0,
            modificationNanoseconds: 0, changeSeconds: 0, changeNanoseconds: 0, mode: UInt32(S_IFREG), links: 2)
        let first = try Metadata(fingerprint: fingerprint)
        let changed = try replacement(first, size: 4)
        var inventory = rootInventory()
        inventory.entries += [InventoryEntry(path: Data("a".utf8), metadata: first), InventoryEntry(path: Data("b".utf8), metadata: changed)]
        inventory.reconcileAliases()
        XCTAssertEqual(inventory.entries.dropFirst().map(\.status), [.stale, .stale])
        XCTAssertEqual(inventory.entries.compactMap(\.logicalBytes), ["3", "4"])
        XCTAssertTrue(inventory.partial)
        var stale = rootInventory()
        stale.entries += [InventoryEntry(path: Data("a".utf8), metadata: first, status: .stale), InventoryEntry(path: Data("b".utf8), metadata: first)]
        stale.reconcileAliases()
        XCTAssertEqual(stale.entries.dropFirst().map(\.status), [.stale, .stale])
        let unknown = try replacement(first, inode: 0)
        XCTAssertNil(InventoryEntry(path: Data("z".utf8), metadata: unknown).objectKey)
    }

    func testIdentityAndAuthorityFieldsNeverEnterProjection() throws {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: encode(rootInventory())) as? [String: Any])
        XCTAssertEqual(Set(object.keys), Set(["schema_version", "source", "entries", "gaps"]))
        let source = try XCTUnwrap(object["source"] as? [String: Any])
        XCTAssertEqual(Set(source.keys), Set(["label", "observed_at", "scan_id", "coverage"]))
        let data = try encode(rootInventory())
        let text = try XCTUnwrap(String(data: data, encoding: .utf8))
        for forbidden in ["/private/", "device", "inode", "volume", "grant", "trusted", "bookmark", "capacity"] {
            XCTAssertFalse(text.contains(forbidden))
        }
    }
    func testQuotedAndMultibyteTextEscapesWithoutChangingItsBytes() throws {
        let name = "quote\"-🧪-<&>.txt"
        var inventory = rootInventory()
        inventory.entries.append(InventoryEntry(path: Data(name.utf8), kind: .file, logicalBytes: "1"))
        let data = try encode(inventory, label: "Owned \"label\" </script> 🧪")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let rows = try XCTUnwrap(object["entries"] as? [[String: Any]])
        XCTAssertEqual(Data(try XCTUnwrap(rows.last?["path"] as? String).utf8), Data(name.utf8))
        let source = try XCTUnwrap(object["source"] as? [String: String])
        XCTAssertEqual(source["label"], "Owned \"label\" </script> 🧪")
    }

}
