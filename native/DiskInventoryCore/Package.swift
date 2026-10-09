// swift-tools-version: 6.0
import PackageDescription

// Phase A only: no executable or library product, no external dependencies.
let package = Package(
    name: "DiskInventoryCore",
    platforms: [.macOS(.v13)],
    products: [],
    targets: [
        .target(name: "DiskInventoryCore"),
        .testTarget(name: "DiskInventoryCoreTests", dependencies: ["DiskInventoryCore"]),
    ],
    swiftLanguageModes: [.v6]
)
