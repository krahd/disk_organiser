# Accepted owned-fixture output evidence

These six JSON files are byte-for-byte outputs from the first successful native push run, [38003620756](https://github.com/krahd/disk_organiser/actions/runs/38003620756), at source `07b93c5e2f0f09746d024884681259aaf513903d`. `manifest.json` records their sizes, SHA-256 hashes and original artifact identity. Only fixed test-created names and metadata are present; no user folders were observed.

These files preserve execution evidence. They are not golden expectations used by tests, an alternate scanner input, or trusted catalogue data. Every CI run still creates fresh native and independent Python sources, and compares all v1 fields except observation time and scan ID. Imported or reopened copies remain unauthenticated historical claims.

The run compiled with Xcode 16.4 (16F6), macOS SDK 15.5 and Swift 6.1.2. All 59 XCTest cases, six native/Python comparisons and six unchanged-JavaScript parser/catalogue cases passed. The macOS filesystem refused creation of the deliberately invalid UTF-8 filename (errno 92); the unconditional synthetic invalid-UTF-8 rejection test passed. This is not native invalid-name-path coverage or a signed sandbox, picker, hardware, provider or backup acceptance result.
