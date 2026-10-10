import XCTest
import Foundation
@testable import DiskInventoryDesktop

@MainActor
final class CatalogueCodecTests: XCTestCase {
    private struct AdmissionCase: Decodable {
        let name: String
        let input: String
        let canonical: String?
    }
    private let empty = Data(#"{"schema_version":"disk-organiser/inventory-catalogue/v1","records":[]}"#.utf8)

    func testCanonicalAdmissionCorpusMatchesNodeExactly() async throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "corpus", withExtension: "json", subdirectory: "LibraryValidation"))
        let bytes = try Data(contentsOf: url)
        XCTAssertLessThan(bytes.count, 131_072)
        let rows = try JSONDecoder().decode([AdmissionCase].self, from: bytes)
        XCTAssertEqual(rows.count, 22)
        let codec = CatalogueCodec()
        for row in rows {
            do {
                let admitted = try await codec.validate(Data(row.input.utf8))
                let expected = try XCTUnwrap(row.canonical, row.name)
                XCTAssertEqual(admitted.bytes, Data(expected.utf8), row.name)
            } catch {
                XCTAssertNil(row.canonical, "Unexpected rejection: \(row.name)")
            }
        }
    }

    func testRawByteAndEncodingPreflightRejectsBeforeAdmission() async throws {
        let codec = CatalogueCodec()
        let rejected = [Data(), Data([0xff]), Data([0xc0, 0x80]), Data([0xed, 0xa0, 0x80]),
                        Data([0xef, 0xbb, 0xbf]) + empty,
                        Data(repeating: 32, count: CatalogueCodec.maximumBytes + 1)]
        for bytes in rejected {
            do { _ = try await codec.validate(bytes); XCTFail("Invalid bytes admitted") }
            catch { XCTAssertTrue(error is CatalogueCodec.Failure) }
        }
        let good = try await codec.validate(empty)
        XCTAssertEqual(good.bytes, empty)
    }

    func testRawWhitespaceLimitAndNoStaleExceptionAfterFailure() async throws {
        let codec = CatalogueCodec()
        let padded = empty + Data(repeating: 32, count: CatalogueCodec.maximumBytes - empty.count)
        let value = try await codec.validate(padded)
        XCTAssertEqual(value.bytes, empty)
        do { _ = try await codec.validate(padded + Data([32])); XCTFail("Overflow admitted") }
        catch {}
        do { _ = try await codec.validate(Data("{broken}".utf8)); XCTFail("Malformed input admitted") }
        catch {}
        let good = try await codec.validate(empty)
        XCTAssertEqual(good.bytes, empty)
    }

    func testPayloadCannotExecuteCodeOrChangeTheCodec() async throws {
        let codec = CatalogueCodec()
        for text in ["globalThis.InventoryCatalogue = null", "(() => {throw Error('execute')})()", "null"] {
            do { _ = try await codec.validate(Data(text.utf8)); XCTFail("Non-catalogue admitted") }
            catch {}
        }
        for _ in 0..<8 {
            let good = try await codec.validate(empty)
            XCTAssertEqual(good.bytes, empty)
        }
    }
}
