import Foundation
@testable import DiskInventoryDesktop

// The delayed acknowledgement seam remains in the test target only.
@MainActor
final class OwnedPreviewHost: CataloguePreviewHost {
    var libraryCalls: [LibraryBridgeOperation] = []
    var dropBeforeLibrary: LibraryBridgeOperation?
    var dropAfterLibrary: LibraryBridgeOperation?
    var afterLibrary: ((LibraryBridgeOperation) async -> Void)?
    override func libraryCall(_ operation: LibraryBridgeOperation, id: UUID,
                              fields: [String: String] = [:]) async throws -> LibraryBridgeReply {
        libraryCalls.append(operation)
        if dropBeforeLibrary == operation { dropBeforeLibrary = nil; throw Failure.expired }
        let reply = try await super.libraryCall(operation, id: id, fields: fields)
        await afterLibrary?(operation)
        if dropAfterLibrary == operation { dropAfterLibrary = nil; throw Failure.expired }
        return reply
    }
    var beforeStageAcknowledgement: (() async -> Void)?
    override func stageAcknowledged() async { await beforeStageAcknowledgement?() }
}
