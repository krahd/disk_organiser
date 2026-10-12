import Foundation

// Stage B may generate these three values only after creating and admitting a
// fresh owned fixture. This checked-in project is intentionally unsealed.
// There is no launch argument/environment override and no production linkage.
enum ProbeSeal {
    static let captureDirectory = "UNSEALED"
    static let captureDevice: Int64 = 0
    static let captureInode: UInt64 = 0
    static let sourceCommit = "UNSEALED"
    static let fixtureSHA256 = "UNSEALED"
    static let bundleIdentifier = "org.diskorganiser.owned-selection-probe.unsealed"
    static let executablePath = "UNSEALED"
    static let selectedPath = "UNSEALED"
}

