// swift-tools-version: 6.0
import PackageDescription

// Test-only core and owned WebKit preview: no product, executable or dependencies.
let package = Package(
    name: "DiskInventoryCore",
    platforms: [.macOS(.v13)],
    products: [],
    targets: [
        .target(name: "DiskInventoryCore"),
        .testTarget(name: "DiskInventoryCoreTests", dependencies: ["DiskInventoryCore"]),
        .testTarget(name: "DiskInventoryPreviewTests", dependencies: ["DiskInventoryCore"],
                    resources: [.copy("Resources/Catalogue")]),
    ],
    swiftLanguageModes: [.v6]
)
