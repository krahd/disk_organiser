import Foundation

// The only script selectors admitted by the persistence client. All data stays
// in one structured argument; no caller supplies JavaScript or a filesystem path.
enum LibraryBridgeOperation: CaseIterable, Sendable {
    case status, exportCatalogue, acknowledgeSaved, savedResult, prepareClose, releaseClose
    case prepareOpen, prepareReplacement, retireCandidate, commitReplacement, replacementResult, cancelOpen

    var body: String {
        switch self {
        case .status: return "return window.DiskCatalogueNativeBridge.status(request);"
        case .exportCatalogue: return "return window.DiskCatalogueNativeBridge.exportCatalogue(request);"
        case .acknowledgeSaved: return "return window.DiskCatalogueNativeBridge.acknowledgeSaved(request);"
        case .savedResult: return "return window.DiskCatalogueNativeBridge.savedResult(request);"
        case .prepareClose: return "return window.DiskCatalogueNativeBridge.prepareClose(request);"
        case .releaseClose: return "return window.DiskCatalogueNativeBridge.releaseClose(request);"
        case .prepareOpen: return "return window.DiskCatalogueNativeBridge.prepareOpen(request);"
        case .prepareReplacement: return "return window.DiskCatalogueNativeBridge.prepareReplacement(request);"
        case .retireCandidate: return "return window.DiskCatalogueNativeBridge.retireCandidate(request);"
        case .commitReplacement: return "return window.DiskCatalogueNativeBridge.commitReplacement(request);"
        case .replacementResult: return "return window.DiskCatalogueNativeBridge.replacementResult(request);"
        case .cancelOpen: return "return window.DiskCatalogueNativeBridge.cancelOpen(request);"
        }
    }
    var requestFields: Set<String> {
        switch self {
        case .exportCatalogue: return ["fence"]
        case .acknowledgeSaved: return ["revision"]
        case .prepareReplacement: return ["candidate", "revision", "epoch", "text"]
        case .commitReplacement: return ["candidate", "revision", "epoch"]
        case .retireCandidate, .replacementResult: return ["candidate"]
        default: return []
        }
    }
    var needsStorage: Bool {
        switch self {
        case .status, .prepareClose, .releaseClose: return false
        default: return true
        }
    }
}

struct LibraryLossState: Equatable, Sendable {
    let revision: String
    let epoch: String
    let dirty: Bool
    let selections: Int
    let dialog: String
    let draft: Bool
    var hasDraft: Bool { draft || dialog != "none" }
    var emptyLoss: Bool { !dirty && selections == 0 && !hasDraft }
}

struct LibraryBridgeReply: Sendable {
    let values: [String: String]
    var state: String { values["state"]! } // Exact decoder constructs this value.
    var loss: LibraryLossState? {
        guard let revision = values["revision"], let epoch = values["epoch"],
              let dirty = values["dirty"], let selections = values["selections"],
              let count = Int(selections), let dialog = values["dialog"], let draft = values["draft"] else { return nil }
        return LibraryLossState(revision: revision, epoch: epoch, dirty: dirty == "dirty",
            selections: count, dialog: dialog, draft: draft == "uncommitted")
    }
}

enum LibraryBridgeWire {
    enum Failure: Error { case invalid }
    static let version = "catalogue-data-bridge/v2"
    static let maximumCounter: UInt64 = 9_007_199_254_740_991
    static let envelope: Set<String> = ["version", "session", "operation"]
    static let lossFields: Set<String> = ["revision", "epoch", "dirty", "selections", "dialog", "draft", "state"]
    static let commitFields: Set<String> = ["candidate", "revision", "epoch", "state", "view"]

    static func uuid(_ text: String) -> Bool {
        guard let value = UUID(uuidString: text) else { return false }
        return text.utf8.count == 36 && value.uuidString.lowercased() == text
    }
    static func counter(_ text: String, maximum: UInt64 = maximumCounter) -> Bool {
        let bytes = Array(text.utf8)
        guard !bytes.isEmpty, bytes.count <= 16, bytes.allSatisfy({ $0 >= 48 && $0 <= 57 }),
              bytes.count == 1 || bytes[0] != 48, let value = UInt64(text) else { return false }
        return value <= maximum
    }
    static func payload(_ value: NSString) throws -> String {
        // Swift String bridging can repair invalid UTF-16. Examine the original
        // NSString first so malformed WebKit text is never silently repaired.
        guard value.length > 0, value.length <= CatalogueCodec.maximumBytes, value.character(at: 0) != 0xfeff else { throw Failure.invalid }
        var offset = 0
        while offset < value.length {
            let unit = value.character(at: offset)
            if unit >= 0xd800 && unit <= 0xdbff {
                offset += 1
                guard offset < value.length else { throw Failure.invalid }
                let next = value.character(at: offset)
                guard next >= 0xdc00 && next <= 0xdfff else { throw Failure.invalid }
            } else if unit >= 0xdc00 && unit <= 0xdfff { throw Failure.invalid }
            offset += 1
        }
        let text = value as String
        guard text.utf8.count <= CatalogueCodec.maximumBytes else { throw Failure.invalid }
        return text
    }
    static func bounded(_ raw: Any, textAllowed: Bool) throws -> [String: String] {
        guard let object = raw as? [String: Any], object.count <= 12 else { throw Failure.invalid }
        var result: [String: String] = [:], metadata = 0
        for (key, value) in object {
            guard key.utf8.count <= 24, let string = value as? NSString else { throw Failure.invalid }
            if key == "text" {
                guard textAllowed else { throw Failure.invalid }
                result[key] = try payload(string)
            } else {
                guard string.length <= 64 else { throw Failure.invalid }
                let text = string as String
                guard text.utf8.count <= 64 else { throw Failure.invalid }
                metadata += key.utf8.count + text.utf8.count
                guard metadata <= 1024 else { throw Failure.invalid }
                result[key] = text
            }
        }
        return result
    }
    static func request(_ operation: LibraryBridgeOperation, session: String, id: UUID,
                        fields: [String: String]) throws -> [String: String] {
        guard Set(fields.keys) == operation.requestFields, uuid(session) else { throw Failure.invalid }
        let result = fields.merging(["version": version, "session": session, "operation": id.uuidString.lowercased()]) { _, _ in "" }
        _ = try bounded(result, textAllowed: operation == .prepareReplacement)
        try validateScalars(result)
        return result
    }
    private static func validateScalars(_ value: [String: String]) throws {
        for key in ["session", "operation", "candidate"] {
            if let text = value[key], !uuid(text) { throw Failure.invalid }
        }
        if let text = value["fence"], text != "", !uuid(text) { throw Failure.invalid }
        for key in ["revision", "epoch", "current_revision"] {
            if let text = value[key], !counter(text) { throw Failure.invalid }
        }
        if let text = value["selections"], !counter(text, maximum: 2000) { throw Failure.invalid }
    }
    static func decode(_ raw: Any, operation: LibraryBridgeOperation,
                       request: [String: String]) throws -> LibraryBridgeReply {
        let value = try bounded(raw, textAllowed: operation == .exportCatalogue)
        guard value["version"] == version, value["session"] == request["session"],
              value["operation"] == request["operation"], let state = value["state"] else { throw Failure.invalid }
        try validateScalars(value)
        let fields: Set<String>
        switch operation {
        case .status:
            guard ["idle", "busy"].contains(state) else { throw Failure.invalid }; fields = lossFields
        case .prepareClose, .prepareOpen:
            guard state == "fenced" else { throw Failure.invalid }; fields = lossFields
        case .exportCatalogue:
            guard state == "exported" else { throw Failure.invalid }; fields = ["revision", "epoch", "state", "text"]
        case .acknowledgeSaved, .savedResult:
            let allowed = operation == .savedResult ? ["current-saved", "earlier-saved", "not-applied"] : ["current-saved", "earlier-saved"]
            guard allowed.contains(state), let revision = value["revision"], let current = value["current_revision"],
                  state != "current-saved" || revision == current,
                  state != "earlier-saved" || revision != current else { throw Failure.invalid }
            if operation == .acknowledgeSaved, revision != request["revision"] { throw Failure.invalid }
            fields = ["revision", "current_revision", "state"]
        case .releaseClose:
            guard state == "released" else { throw Failure.invalid }; fields = ["state"]
        case .prepareReplacement:
            guard state == "prepared", value["candidate"] == request["candidate"],
                  value["revision"] == request["revision"], value["epoch"] == request["epoch"] else { throw Failure.invalid }
            fields = ["candidate", "revision", "epoch", "state"]
        case .retireCandidate:
            guard ["retired", "committed"].contains(state), value["candidate"] == request["candidate"] else { throw Failure.invalid }
            fields = state == "retired" ? ["candidate", "state"] : commitFields
        case .commitReplacement, .replacementResult:
            let allowed = operation == .replacementResult ? ["committed", "not-committed"] : ["committed"]
            guard allowed.contains(state), value["candidate"] == request["candidate"] else { throw Failure.invalid }
            fields = commitFields
        case .cancelOpen:
            guard ["cancelled", "committed"].contains(state) else { throw Failure.invalid }
            fields = state == "cancelled" ? ["state"] : commitFields
        }
        guard Set(value.keys) == envelope.union(fields) else { throw Failure.invalid }
        if fields == lossFields {
            guard ["clean", "dirty"].contains(value["dirty"]!),
                  ["none", "label-edit", "snapshot-review", "catalogue-review", "other-edit"].contains(value["dialog"]!),
                  ["none", "uncommitted"].contains(value["draft"]!) else { throw Failure.invalid }
        }
        if fields == commitFields, !["ready", "blocked"].contains(value["view"]!) { throw Failure.invalid }
        return LibraryBridgeReply(values: value)
    }
}

@MainActor
protocol LibraryPageClient: AnyObject {
    var session: String { get }
    var storageMode: CataloguePreviewHost.StorageMode { get }
    func libraryCall(_ operation: LibraryBridgeOperation, id: UUID, fields: [String: String]) async throws -> LibraryBridgeReply
}
