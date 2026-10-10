import Foundation

// Projection of already strictly admitted bytes only. This is display data, not
// another permissive import path or proof of physical identity/protection.
struct LibraryCandidatePreview: Sendable {
    struct Location: Sendable {
        let label: String
        let origin: String
        let claimedDate: String
        let entries: Int
        let partial: Bool
        let gaps: String
    }
    let locations: [Location]
    var entries: Int { locations.reduce(0) { $0 + $1.entries } }
    init(_ admitted: ValidatedCatalogue) throws {
        guard let root = try JSONSerialization.jsonObject(with: admitted.bytes) as? [String: Any],
              let records = root["records"] as? [[String: Any]], records.count <= 32 else { throw LibraryBridgeWire.Failure.invalid }
        locations = try records.map { record in
            guard let label = record["label"] as? String, let snapshot = record["snapshot"] as? [String: Any],
                  let source = snapshot["source"] as? [String: Any], let origin = source["label"] as? String,
                  let date = source["observed_at"] as? String, let coverage = source["coverage"] as? String,
                  let entries = snapshot["entries"] as? [[String: Any]], let gaps = snapshot["gaps"] as? [String: Any],
                  let errors = gaps["error_count"] as? String, let exclusions = gaps["exclusions"] as? [[String: Any]] else { throw LibraryBridgeWire.Failure.invalid }
            let reasons = try exclusions.map { gap -> String in
                guard let reason = gap["reason"] as? String, let count = gap["count"] as? String else { throw LibraryBridgeWire.Failure.invalid }
                return reason + " (" + count + ")"
            }
            let stop = gaps["stop_reason"] as? String
            return Location(label: label, origin: origin, claimedDate: date, entries: entries.count,
                partial: coverage == "partial", gaps: (["Recorded errors: " + errors] + reasons + (stop.map { ["Stopped: " + $0] } ?? [])).joined(separator: " · "))
        }
    }
}
