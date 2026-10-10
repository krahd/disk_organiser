// swift-tools-version: 6.0
import PackageDescription

// Development/sample application only. No live source picker or entitlement.
let package = Package(
    name: "DiskInventoryCore",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "DiskOrganiserPreview", targets: ["DiskOrganiserPreview"])],
    targets: [
        .target(name: "DiskInventoryCore"),
        .target(name: "DiskInventoryDesktop", resources: [.copy("Resources/Catalogue"), .copy("Resources/Examples")]),
        .executableTarget(name: "DiskOrganiserPreview", dependencies: ["DiskInventoryDesktop"]),
        .testTarget(name: "DiskInventoryCoreTests", dependencies: ["DiskInventoryCore"]),
        .testTarget(name: "DiskInventoryPreviewTests", dependencies: ["DiskInventoryCore", "DiskInventoryDesktop"]),
    ],
    swiftLanguageModes: [.v6]
)
