import Foundation

// This encoder emits v1 data only. It accepts no JSON, source path or saved authority.
enum SnapshotProjection {
    static func text(_ bytes: Data, maximum: Int) throws -> String {
        guard let value = String(data: bytes, encoding: .utf8),
              !value.unicodeScalars.isEmpty, value.unicodeScalars.count <= maximum else {
            throw CoreFailure.invalidProjection
        }
        var visible = false
        for scalar in value.unicodeScalars {
            let c = scalar.value
            if c < 32 || (127...159).contains(c) || c == 0x2028 || c == 0x2029 {
                throw CoreFailure.invalidProjection
            }
            // ECMAScript trim whitespace, matching the unchanged v1 parser.
            let whitespace = c == 32 || c == 160 || c == 0x1680 || (0x2000...0x200A).contains(c)
                || c == 0x202F || c == 0x205F || c == 0x3000 || c == 0xFEFF
            visible = visible || !whitespace
        }
        guard visible else { throw CoreFailure.invalidProjection }
        return value
    }

    static func path(_ bytes: Data) throws -> String {
        let value = try text(bytes, maximum: 1_024)
        if bytes != Data(".".utf8) {
            let pieces = bytes.split(separator: 47, omittingEmptySubsequences: false)
            guard !bytes.contains(92), pieces.allSatisfy({ !$0.isEmpty && $0 != Data(".".utf8) && $0 != Data("..".utf8) }) else {
                throw CoreFailure.invalidProjection
            }
        }
        return value
    }

    static func decimal(_ value: String) throws {
        let bytes = Array(value.utf8)
        guard !bytes.isEmpty, bytes.count <= 30, bytes.allSatisfy({ (48...57).contains($0) }),
              bytes.count == 1 || bytes[0] != 48 else { throw CoreFailure.invalidProjection }
    }

    static func timestamp(_ value: String) throws {
        _ = try text(Data(value.utf8), maximum: 40)
        let expression = try NSRegularExpression(pattern: "^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\\.[0-9]{1,6})?(Z|[+-]([0-9]{2}):([0-9]{2}))$")
        let string = value as NSString
        guard let match = expression.firstMatch(in: value, range: NSRange(location: 0, length: string.length)),
              match.range.length == string.length else { throw CoreFailure.invalidProjection }
        func number(_ index: Int) -> Int { Int(string.substring(with: match.range(at: index))) ?? -1 }
        let year = number(1), month = number(2), day = number(3)
        let days = [31, year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) ? 29 : 28,
                    31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        guard year >= 1, (1...12).contains(month), (1...days[month - 1]).contains(day),
              (0...23).contains(number(4)), (0...59).contains(number(5)), (0...59).contains(number(6)) else {
            throw CoreFailure.invalidProjection
        }
        if string.substring(with: match.range(at: 7)) != "Z" {
            guard (0...23).contains(number(8)), (0...59).contains(number(9)) else { throw CoreFailure.invalidProjection }
        }
    }

    static func encode(_ inventory: Inventory, label: String, stamp: String, scanID: String) throws -> Data {
        _ = try text(Data(label.utf8), maximum: 240)
        try timestamp(stamp)
        let idBytes = Array(scanID.utf8)
        guard idBytes.count == 29, idBytes.starts(with: Array("scan_".utf8)),
              idBytes.dropFirst(5).allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              !inventory.entries.isEmpty, inventory.entries.count <= Bounds.entries,
              (0...Bounds.entries).contains(inventory.errorCount), inventory.exclusions.count <= 32 else {
            throw CoreFailure.invalidProjection
        }
        var paths: [Data: EntryKind] = [:]
        var root = false
        for entry in inventory.entries {
            _ = try path(entry.path)
            guard paths[entry.path] == nil else { throw CoreFailure.invalidProjection }
            paths[entry.path] = entry.kind
            if entry.path == Data(".".utf8) {
                root = entry.kind == .directory && entry.status == .observed
            }
            if entry.kind == .file {
                guard let size = entry.logicalBytes else { throw CoreFailure.invalidProjection }
                try decimal(size)
            } else if entry.logicalBytes != nil { throw CoreFailure.invalidProjection }
        }
        guard root else { throw CoreFailure.invalidProjection }
        for entry in inventory.entries where entry.path != Data(".".utf8) {
            let parent = entry.path.lastIndex(of: 47).map { Data(entry.path[..<$0]) } ?? Data(".".utf8)
            guard paths[parent] == .directory else { throw CoreFailure.invalidProjection }
        }
        for (reason, count) in inventory.exclusions {
            _ = try text(reason, maximum: 120)
            guard (1...10_000).contains(count) else { throw CoreFailure.invalidProjection }
        }
        if let stop = inventory.stopReason { _ = try text(Data(stop.utf8), maximum: 120) }
        let entries = inventory.entries.sorted { $0.path.lexicographicallyPrecedes($1.path) }
        let reasons = inventory.exclusions.keys.sorted { $0.lexicographicallyPrecedes($1) }

        func emit(_ writer: inout JSONWriter) throws {
            try writer.literal("{\"schema_version\":\"disk-organiser/inventory-snapshot/v1\",\"source\":{\"label\":")
            try writer.string(Data(label.utf8))
            try writer.literal(",\"observed_at\":")
            try writer.string(Data(stamp.utf8))
            try writer.literal(",\"scan_id\":")
            try writer.string(Data(scanID.utf8))
            try writer.literal(",\"coverage\":")
            try writer.string(Data((inventory.partial ? "partial" : "complete").utf8))
            try writer.literal("},\"entries\":[")
            for (index, entry) in entries.enumerated() {
                if index != 0 { try writer.literal(",") }
                try writer.literal("{\"path\":")
                try writer.string(entry.path)
                try writer.literal(",\"kind\":")
                try writer.string(Data(entry.kind.rawValue.utf8))
                try writer.literal(",\"status\":")
                try writer.string(Data(entry.status.rawValue.utf8))
                try writer.literal(",\"logical_bytes\":")
                if let size = entry.logicalBytes { try writer.string(Data(size.utf8)) }
                else { try writer.literal("null") }
                try writer.literal("}")
            }
            try writer.literal("],\"gaps\":{\"exclusions\":[")
            for (index, reason) in reasons.enumerated() {
                if index != 0 { try writer.literal(",") }
                try writer.literal("{\"reason\":")
                try writer.string(reason)
                try writer.literal(",\"count\":")
                try writer.string(Data(String(inventory.exclusions[reason]!).utf8))
                try writer.literal("}")
            }
            try writer.literal("],\"error_count\":")
            try writer.string(Data(String(inventory.errorCount).utf8))
            try writer.literal(",\"stop_reason\":")
            if let reason = inventory.stopReason { try writer.string(Data(reason.utf8)) }
            else { try writer.literal("null") }
            try writer.literal("}}")
        }
        // Count canonical UTF-8 before allocating the transferable JSON buffer.
        var counter = JSONWriter(materialise: false)
        try emit(&counter)
        var writer = JSONWriter(materialise: true, capacity: counter.count)
        try emit(&writer)
        guard writer.count == counter.count else { throw CoreFailure.invalidProjection }
        return writer.output
    }
}

private struct JSONWriter {
    private let materialise: Bool
    private(set) var count = 0
    private(set) var output = Data()

    init(materialise: Bool, capacity: Int = 0) {
        self.materialise = materialise
        if materialise { output.reserveCapacity(capacity) }
    }

    mutating func literal(_ value: String) throws { try append(Data(value.utf8)) }

    mutating func append(_ bytes: Data) throws {
        guard bytes.count <= Bounds.snapshotBytes - count else { throw CoreFailure.invalidProjection }
        count += bytes.count
        if materialise { output.append(bytes) }
    }

    mutating func string(_ bytes: Data) throws {
        try append(Data([34]))
        var start = bytes.startIndex
        for index in bytes.indices where bytes[index] == 34 || bytes[index] == 92 {
            try append(Data(bytes[start..<index]))
            try append(Data([92, bytes[index]]))
            start = bytes.index(after: index)
        }
        try append(Data(bytes[start...]))
        try append(Data([34]))
    }
}
