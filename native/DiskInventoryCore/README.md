# Owned native inventory core

The Swift/Darwin observation core remains an isolated bounded metadata-only prototype with no public scanner API or production source-selection factory. A separate `DiskInventoryDesktop` module now supplies an AppKit development/sample application and shared data-only catalogue presentation. `DiskOrganiserPreview` is an explicit sample executable; it has no dependency on the observer core, no real folder picker, entitlement or persistent grant. This is not yet a usable real-folder product. [Current application scope and validation](APPLICATION-PREVIEW.md).

Only the test target constructs a source lease, from a fresh temporary directory it creates and owns. A private held descriptor and the test's address guard are process-local objects, never JSON, persisted permissions or physical-drive identity. No production source-class admission is implemented. The supplied classifier means only “owned test fixture”. The test adapter supplies the absolute-address ancestor re-walk; a production picker/admission adapter does not exist.

## Purpose and limits

The core is the first verification gate towards explicitly selecting one project folder in a future native catalogue. It observes directory metadata and logical file sizes without intentionally reading file contents. Results use the unchanged inventory-snapshot v1 format and remain historical claims when imported or reopened. Names do not grant access. Listed logical bytes are neither disk capacity nor independent copies or backup protection.

Fixed bounds are 2,000 entries including the root, 500 entries per directory, depth 8, five cooperative seconds and a 1 MiB snapshot. A directory with a 501st name becomes an explicit gap; enumeration order cannot select an arbitrary first 500. No file hashing, link following, filesystem crossing, stored observation reuse or mutation is enabled. A `.icloud` suffix and Darwin `SF_DATALESS` flag are known exclusion markers only; tests inject the latter and make no provider-detection or no-hydration guarantee.

A held lease accepts exactly one controller ownership claim, and a rejected claimant cannot release it. The one-shot controller keeps borrowed descriptors owned until its worker finishes. User callback admission ends before the final root guard; direct cancellation remains live through projection and result admission. Cancellation is latched and late results cannot become snapshots; it does not interrupt a blocked OS call. Root/address changes withhold the artifact, descendant uncertainty remains explicit, and changed hard-link aliases are stale. The result is not an atomic snapshot or a universal defence against a hostile writer, moved open directory or same-filesystem alias.

The exact source/identity/race/cancellation contract and later platform gates are in [native onboarding](../../docs/drive-administration/NATIVE-ONBOARDING.md).

## Owned verification

The dedicated `Owned native inventory core` workflow uses `macos-15` with Xcode 16.4 build 16F6 and SDK 15.5 selected through `DEVELOPER_DIR`. It fails if those reviewed versions are unavailable and records the actual Swift compiler, OS and runner image. No new package dependencies or filesystem permissions are requested.

On a suitable owned macOS development checkout, the test command is:

```sh
DEVELOPER_DIR=/Applications/Xcode_16.4.app/Contents/Developer \
  xcrun swift test --package-path native/DiskInventoryCore
```

This command takes no source-path argument. Darwin tests do not substitute a weaker Linux or Windows walker. Tests create only temporary sources and adjacent owned sentinels; no existing user folders are scanned.

In hosted CI, a golden-output test exclusively creates the fixed `RUNNER_TEMP/disk-inventory-goldens` output directory. Six fixtures cover empty/nested folders, links, a known placeholder marker, depth and per-directory bounds. The independent Python harness creates its own fresh sources and compares every v1 field except generated observation time and scan ID. The unchanged JavaScript parser then validates the native artifacts, rejects injected authority/duplicate keys and roundtrips the combined historical catalogue. These scripts are test harnesses, not export/import entry points for the app.

The assigned Linux workspace has no Swift compiler. Local Python-oracle and parser-harness self-checks do not constitute native acceptance. The hosted execution below is separate evidence.

## Executed Phase A evidence

Source `07b93c5e2f0f09746d024884681259aaf513903d` passed [native push CI](https://github.com/krahd/disk_organiser/actions/runs/38003620756): 59 XCTest cases, six independently created native/Python comparisons and six unchanged-JavaScript parser/catalogue cases. [PR CI](https://github.com/krahd/disk_organiser/actions/runs/38003624967) repeated that result on merge checkout `eebe7971a9bc0c21cde4c6a1231d32c3752a94aa`, whose tree exactly matched the source tree. All twelve existing/new workflow runs passed.

Both native runs used Xcode 16.4 (16F6), SDK 15.5 and Apple Swift 6.1.2 on macOS 15.7.9 (24G830), arm64 image `20260907.0337.1`. The filesystem refused invalid UTF-8 filename creation (errno 92); unconditional synthetic rejection passed, but native invalid-name-path coverage is not claimed. No XCTest was silently skipped. All source trees were freshly created and owned by tests; no user-drive or signed-sandbox acceptance follows.

[Original owned outputs and their hash manifest](Validation/accepted-fixtures/README.md) preserve fixture-only evidence. Tests continue to create independent fresh sources rather than using these saved outputs as expectations. Independent source and evidence reviews accepted this bounded Phase A result, not a new hardware test or production integration. Root `STATUS.md` records exact source/run identities and the initial repaired workflow-validation failure.

## Not established by Phase A

- OS-granted read-only selected-folder access, signed sandbox behaviour or release of panel-origin access
- Safe classification of arbitrary local/cloud/provider-backed sources
- Native picker, window lifecycle, WebKit handoff or container save/reopen
- Physical-volume matching, remembered access, automatic reconnect or mount monitoring
- Real external-drive reads, unplug/reconnect behaviour, user usability, backup/restore or provider integration

Those remain separately reviewed gates. Passing a descriptor test or producing a valid JSON snapshot cannot activate them.

## Owned visual handoff test target

PR23 established five isolated owned-fixture AppKit/WebKit tests. The current source extracts their data-only host into the shared desktop module; event injection, acknowledgement barriers, actual source constructors and evidence writers remain in tests. Canonical assets move to that module’s narrow resource bundle with byte-for-byte parity checks. The new sample executable is separate from the observer core and signed source-access gates. Successful source `356ff01` passes all 64 XCTest cases (59 core + five WebKit), six native/Python differential and six unchanged-parser/catalogue cases on the pinned macOS runner. The native event queue repair retains genuine AppKit pointer/Escape assertions and produces five verified original viewport screenshots. Independent source/runtime/all-five-pixel evidence review is accepted. PR23 actual-main `2952fa64` passes all six workflows and the same 64 + 6 + 6 results. This historical owned-test-host evidence does not establish acceptance of the newly authored application shell, signed app or user drives. See [the exact preview boundary and test plan](OWNED-PREVIEW.md). Existing core source, limits and saved formats are unchanged.

## Executed sample application checkpoint

Source `c55f1894` passes all twelve workflows, including both native runs with 84 XCTest cases, six differential comparisons and six parser/catalogue roundtrips. The just-built sample executable proves actual empty-window readiness and normal Quit. Six application and five existing WebKit originals are verified per run; independent source/log/all-original-pixel closeout accepts the scoped sample evidence. This is bounded development/sample evidence, not real-folder or signed-product acceptance. [Exact source/run identities, diagnostic history, screenshot scope and retention limits](APPLICATION-PREVIEW.md).
