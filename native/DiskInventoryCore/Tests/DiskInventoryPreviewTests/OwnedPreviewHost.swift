import Foundation
@testable import DiskInventoryDesktop

// The delayed acknowledgement seam remains in the test target only.
@MainActor
final class OwnedPreviewHost: CataloguePreviewHost {
    var beforeStageAcknowledgement: (() async -> Void)?
    override func stageAcknowledged() async { await beforeStageAcknowledgement?() }
}
