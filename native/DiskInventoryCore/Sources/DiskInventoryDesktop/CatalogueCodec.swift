import Foundation
import JavaScriptCore

// Construction of this value is confined to successful strict parser admission.
// Bytes remain untrusted historical claims; this is never source authority.
struct ValidatedCatalogue: Sendable {
    let bytes: Data
    fileprivate init(_ bytes: Data) { self.bytes = bytes }
}

// A conformer can return only a value already admitted by this codec file.
// The internal seam permits deterministic test suspension, never raw construction.
protocol CatalogueValidating: Actor {
    func validate(_ bytes: Data) async throws -> ValidatedCatalogue
}

actor CatalogueCodec: CatalogueValidating {
    enum Failure: Error { case unavailable, invalidCatalogue }
    static let maximumBytes = 4 * 1_024 * 1_024
    private var context: JSContext?
    private var validator: JSValue?

    // No path/URL/code/native object or callback is provided by callers.
    func validate(_ bytes: Data) throws -> ValidatedCatalogue {
        guard !bytes.isEmpty, bytes.count <= Self.maximumBytes,
              !bytes.starts(with: [0xef, 0xbb, 0xbf]),
              let text = String(data: bytes, encoding: .utf8), Data(text.utf8) == bytes else {
            throw Failure.invalidCatalogue
        }
        try prepare()
        guard let context, let validator else { throw Failure.unavailable }
        context.exception = nil
        // Input is an argument, never concatenated or evaluated as JavaScript.
        let value = validator.call(withArguments: [text])
        guard context.exception == nil, let value, value.isString,
              let canonical = value.toString(), canonical.utf8.count <= Self.maximumBytes else {
            context.exception = nil
            throw Failure.invalidCatalogue
        }
        return ValidatedCatalogue(Data(canonical.utf8))
    }

    private func prepare() throws {
        if validator != nil { return }
        guard let root = Bundle.module.resourceURL, let candidate = JSContext() else {
            throw Failure.unavailable
        }
        let capabilities = candidate.evaluateScript(#"["process", "require", "fetch", "XMLHttpRequest", "document", "window", "webkit", "readFile", "load", "ObjC"].every(key => typeof globalThis[key] === "undefined")"#)
        guard candidate.exception == nil, capabilities?.isBoolean == true, capabilities?.toBool() == true else {
            throw Failure.unavailable
        }
        // A trusted bundled-code assumption, checked by the asset parity gate.
        // The parser VM has no exposed native bindings, filesystem, network or DOM.
        let resources = [
            ("CatalogueValidation/utf8-encoder.js", 8_192),
            ("Catalogue/manual-planning-model.js", 131_072),
            ("Catalogue/inventory-snapshot-model.js", 65_536),
        ]
        for (name, limit) in resources {
            let bytes = try Data(contentsOf: root.appendingPathComponent(name), options: .uncached)
            guard !bytes.isEmpty, bytes.count <= limit, let source = String(data: bytes, encoding: .utf8) else {
                throw Failure.unavailable
            }
            candidate.evaluateScript(source)
            guard candidate.exception == nil else { throw Failure.unavailable }
        }
        let function = candidate.evaluateScript(#"""
            (function (text) {
              const value = InventoryCatalogue.parse(text);
              if (value.schema_version !== InventoryCatalogue.CATALOGUE)
                throw new Error("A saved library requires a catalogue.");
              return InventoryCatalogue.exportCatalogue(value);
            })
            """#)
        guard candidate.exception == nil, let function, function.isObject else {
            throw Failure.unavailable
        }
        context = candidate
        validator = function
    }
}
