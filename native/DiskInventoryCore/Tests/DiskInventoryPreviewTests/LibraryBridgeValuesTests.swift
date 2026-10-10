import XCTest
import Foundation
@testable import DiskInventoryDesktop

final class LibraryBridgeValuesTests: XCTestCase {
    let session = "12345678-1234-4234-8234-123456789abc"
    let id = UUID(uuidString: "00000000-0000-4000-8000-000000000001")!
    func testEveryOperationHasOneFixedBodyAndExactRequestKeys() throws {
        for operation in LibraryBridgeOperation.allCases {
            var fields: [String: String] = [:]
            for key in operation.requestFields {
                fields[key] = key == "candidate" ? id.uuidString.lowercased() : key == "text" ? "{}" : key == "fence" ? "" : "0"
            }
            let request = try LibraryBridgeWire.request(operation, session: session, id: id, fields: fields)
            XCTAssertEqual(Set(request.keys), LibraryBridgeWire.envelope.union(operation.requestFields))
            XCTAssertTrue(operation.body.hasPrefix("return window.DiskCatalogueNativeBridge."))
            XCTAssertTrue(operation.body.hasSuffix("(request);"))
            fields["path"] = "/forbidden"
            XCTAssertThrowsError(try LibraryBridgeWire.request(operation, session: session, id: id, fields: fields))
        }
        XCTAssertEqual(Set(LibraryBridgeOperation.allCases.map(\.body)).count, 12)
    }
    func testCountersAndUUIDsNeverCoerceOrWrap() {
        for value in ["", "00", "01", "-1", "+1", "1.0", " 1", "1 ", "١", "9007199254740992", "99999999999999999"] {
            XCTAssertFalse(LibraryBridgeWire.counter(value), value)
        }
        XCTAssertTrue(LibraryBridgeWire.counter("0")); XCTAssertTrue(LibraryBridgeWire.counter("9007199254740991"))
        XCTAssertFalse(LibraryBridgeWire.counter("2001", maximum: 2000)); XCTAssertTrue(LibraryBridgeWire.uuid(session))
        XCTAssertFalse(LibraryBridgeWire.uuid(session.uppercased())); XCTAssertFalse(LibraryBridgeWire.uuid("{" + session + "}"))
    }
    func testExactLossVariantsRejectTypesAndExtraFields() throws {
        let request = try LibraryBridgeWire.request(.prepareClose, session: session, id: id, fields: [:])
        let good = request.merging(["revision": "2", "epoch": "7", "dirty": "clean", "selections": "1", "dialog": "label-edit", "draft": "uncommitted", "state": "fenced"]) { _, new in new }
        let reply = try LibraryBridgeWire.decode(good, operation: .prepareClose, request: request)
        XCTAssertTrue(try XCTUnwrap(reply.loss).hasDraft); XCTAssertEqual(reply.loss?.selections, 1)
        for key in good.keys {
            var absent = good; absent.removeValue(forKey: key)
            XCTAssertThrowsError(try LibraryBridgeWire.decode(absent, operation: .prepareClose, request: request))
            var typed: [String: Any] = good; typed[key] = 1
            XCTAssertThrowsError(try LibraryBridgeWire.decode(typed, operation: .prepareClose, request: request))
        }
        for (key, value) in ["unexpected": "x", "dirty": "true", "dialog": "dialog", "draft": "saved", "selections": "2001", "version": "catalogue-data-bridge/v1", "operation": UUID().uuidString.lowercased()] {
            var wrong = good; wrong[key] = value
            XCTAssertThrowsError(try LibraryBridgeWire.decode(wrong, operation: .prepareClose, request: request))
        }
    }
    func testPayloadLimitsCountUTF8AndRejectMalformedOriginalUTF16() throws {
        let atLimit = String(repeating: "é", count: CatalogueCodec.maximumBytes / 2)
        XCTAssertEqual(try LibraryBridgeWire.payload(atLimit as NSString).utf8.count, CatalogueCodec.maximumBytes)
        for value in ["", "\u{feff}{}", atLimit + "x"] { XCTAssertThrowsError(try LibraryBridgeWire.payload(value as NSString)) }
        for units in [[unichar(0xd800)], [unichar(0xdc00)], [unichar(0xd800), 65]] {
            let value = units.withUnsafeBufferPointer { NSString(characters: $0.baseAddress!, length: $0.count) }
            XCTAssertThrowsError(try LibraryBridgeWire.payload(value))
        }
    }
    func testExportHasOnlyOneLargeFieldAndNoObjectPayload() throws {
        let request = try LibraryBridgeWire.request(.exportCatalogue, session: session, id: id, fields: ["fence": ""])
        let base = ["version": LibraryBridgeWire.version, "session": session, "operation": id.uuidString.lowercased(), "revision": "0", "epoch": "0", "state": "exported", "text": "{}"]
        XCTAssertEqual(try LibraryBridgeWire.decode(base, operation: .exportCatalogue, request: request).values["text"], "{}")
        var object: [String: Any] = base; object["text"] = ["records": []]
        XCTAssertThrowsError(try LibraryBridgeWire.decode(object, operation: .exportCatalogue, request: request))
        var large = base; large["epoch"] = String(repeating: "1", count: 65)
        XCTAssertThrowsError(try LibraryBridgeWire.decode(large, operation: .exportCatalogue, request: request))
    }
    func testSavedAndReplacementRepliesAreCorrelatedPerVariant() throws {
        let request = try LibraryBridgeWire.request(.acknowledgeSaved, session: session, id: id, fields: ["revision": "3"])
        var response = ["version": LibraryBridgeWire.version, "session": session, "operation": id.uuidString.lowercased(), "revision": "3", "current_revision": "4", "state": "earlier-saved"]
        XCTAssertEqual(try LibraryBridgeWire.decode(response, operation: .acknowledgeSaved, request: request).state, "earlier-saved")
        response["state"] = "current-saved"
        XCTAssertThrowsError(try LibraryBridgeWire.decode(response, operation: .acknowledgeSaved, request: request))
        response["current_revision"] = "3"
        XCTAssertEqual(try LibraryBridgeWire.decode(response, operation: .acknowledgeSaved, request: request).state, "current-saved")
        response["revision"] = "2"
        XCTAssertThrowsError(try LibraryBridgeWire.decode(response, operation: .acknowledgeSaved, request: request))
        let commit = try LibraryBridgeWire.request(.commitReplacement, session: session, id: id,
            fields: ["candidate": id.uuidString.lowercased(), "revision": "3", "epoch": "4"])
        var result = commit; result["revision"] = "4"; result["epoch"] = "5"; result["state"] = "committed"; result["view"] = "blocked"
        XCTAssertEqual(try LibraryBridgeWire.decode(result, operation: .commitReplacement, request: commit).values["view"], "blocked")
        result["candidate"] = UUID().uuidString.lowercased()
        XCTAssertThrowsError(try LibraryBridgeWire.decode(result, operation: .commitReplacement, request: commit))
    }
}
