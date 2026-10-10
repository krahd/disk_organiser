# Native application development preview

Slice 1 adds a real AppKit application entry point and library window around the shared catalogue. **It is a development/sample preview, not a usable real-folder product.** No signed app, installer, picker, source grant, entitlement/profile, persistent bookmark, native library Save/Open or user-device access is enabled.

## Modules and experience

- `DiskOrganiserPreview` is a SwiftPM executable that calls the single public `DiskOrganiserPreviewApplication.run()` entry. No external argument, document or URL selects data.
- `DiskInventoryDesktop` owns the AppKit window, sample selector/scope sheet, preparation/cancel/review lifecycle and shared hardened WebKit presentation. It has no dependency on `DiskInventoryCore`.
- The application only reads two fixed bundled example JSON resources, byte-identical to the existing public owned examples. These describe example history, not current storage. The default library is empty; opening the app performs no source scan.
- “Explore sample folders” opens an explicit native selector and scope review. “Review example snapshot” prepares that fixed data, then the existing strict WebKit preview requires Add or Cancel. “Done reviewing” retires the delivery fence and reports whether Add occurred. Search and comparison then operate on the temporary records.
- “Choose my folder” is disabled with its unavailable reason. Save/Open/manual-plan export remain explicitly unavailable. Dirty close asks Keep exploring or Discard and close. A later Save/Open slice must replace this temporary-only contract, not merely expose a dead button.

The core's five source files, existing 59 tests and private source constructors are unchanged. The prior five WebKit tests use a small test subclass of the extracted host. Its delayed acknowledgement seam, native-event driver, actual owned-directory providers and evidence writers remain in the test target. Only fresh owned directories or the fixed public examples are used by the new application tests.

## Trust and lifecycle

The shared view retains exact bundle navigation, narrow local read root, nonpersistent website data store, fixed resource blocker, no upload/drop/external navigation, structured JavaScript arguments and no JavaScript-to-native handler. Imported JSON is still untrusted history. The application owns no real source lease, scanner or raw-path constructor.

Every preparation carries a current generation. Cancel, close and late completions cannot create a new record after retirement. A previously processed Add remains a valid temporary record and is reported honestly. New selection cannot overlap stopping work. Errors preserve existing history or block the view without pretending a save occurred. Cancellation is cooperative; it is not a guaranteed interruption of an OS/WebKit call.

The fixed WebKit blocker necessarily has a compiled framework cache. Startup creates a fresh private `mkdtemp` directory for that cache rather than using the default rule store. It is not a catalogue save or persistent source grant. This initial source does not recursively clean it; OS/framework temporary-cache retention is a disclosed footprint. The host itself has no filesystem writer.

## Build and validation

On the separately approved owned macOS build route:

```sh
DEVELOPER_DIR=/Applications/Xcode_16.4.app/Contents/Developer \
  xcrun swift build --package-path native/DiskInventoryCore --product DiskOrganiserPreview
DEVELOPER_DIR=/Applications/Xcode_16.4.app/Contents/Developer \
  xcrun swift test --package-path native/DiskInventoryCore
```

The entry point is compiled and a new bounded test launches only that just-built sample executable. It requires a fixed receipt after the actual shared view is empty and the native window is ready, then requests normal Quit of the exact live child by process/executable identity and requires successful exit. Unknown startup arguments must reject before readiness. No source path or test command is accepted by the executable. Timeout cleanup targets only that owned child and is always failed execution, never normal-Quit evidence. Hosted control interactions also exercise the same application window/module inside XCTest. This is not a packaged `.app` launch or signed-product acceptance. No executable artifact is uploaded or deployed. A distributable bundle, signing and the live picker remain separate gates.

The existing 64 native cases remain required, followed by six independent native/Python differential and six unchanged-parser/catalogue checks. Twenty new application cases cover the native sample/scope/Add/Cancel journey, immediate cancellation/close before provider invocation, notification re-entry, held-provider and delayed-stage cancellation/close, Add-before-retirement bookkeeping, real dirty-close Keep/Discard/repeated requests, close-question preservation, native-to-WebKit Escape/focus, startup gating, fixed examples, separate-process startup/normal quit/argument rejection and bounded pipe collection. Source checks also verify all seven canonical view assets and the two allowed examples plus manifests. No source path comes from a test environment variable.

Six new original captures are required for the application journey: native library controls, sample selector, scope review, preparation controls, the embedded catalogue viewport and the native discard confirmation. AppKit captures are explicitly scoped to the named native view; the WebKit image is a viewport snapshot. They are not combined, resized, whole-screen or full-window evidence. Screenshot writes are test-only, exclusive/no-follow, fixed-name, six-image/5-MiB-per-image bounded and restricted to `RUNNER_TEMP/disk-application-preview-screens`. A complete manifest is required. Actions retention is 14 days; no permanent archive is claimed.

## Executed sample-application evidence

Source `c55f1894c48c5c13451f730426634a97fbf2f8f2`, tree `8500f70563036adc1a161c5f2ff1ad02988411ec`, passes all twelve push/PR workflows. [Native push 38024562204](https://github.com/krahd/disk_organiser/actions/runs/38024562204) checks out that source; [native PR 38024564977](https://github.com/krahd/disk_organiser/actions/runs/38024564977) checks out GitHub merge commit `2eb68da5124203d9b8b2a3a259e79848cea30827`. The merge and source trees are identical. These runs are attributed to that source, not a later documentation or main commit.

Both native runs compile the sample executable and pass **84 XCTest cases, six independent native/Python comparisons and six unchanged parser/catalogue roundtrips**. The 84 cases comprise 59 existing core, five existing WebKit, 16 application window/lifecycle and four owned-process/receipt cases. The actual just-built child completes every fixed startup phase, proves an empty visible active/key window and exits zero after normal Quit with the required delegate receipts. Registration alone, a quit request alone and timeout cleanup are not counted as success. Native pointer/keyboard, interrupted/repeated flows, delayed Add/Cancel, close-confirmation and focus assertions remain required.

Toolchain: Xcode 16.4 build 16F6, SDK 15.5, Apple Swift 6.1.2, macOS 15.7.9 (24G830), arm64 runner image `20260907.0337.1`. The filesystem refuses invalid UTF-8 filename creation with errno 92; unconditional synthetic rejection passes, but native invalid-name-path coverage is not established. No XCTest is silently skipped. All observed sources are fresh owned fixtures. The sample executable itself only reads its two fixed bundled examples.

[Aggregate push CI](https://github.com/krahd/disk_organiser/actions/runs/38024562097) passes 709 Linux backend tests, 665 Jest tests, formatting, dependency audits, 44-route OpenAPI validation and 27 existing browser journeys. Windows passes 607 with 102 existing platform skips. Local Linux source checks separately pass 39 catalogue DOM groups, 16 bridge DOM groups and asset/example parity; they do not substitute for macOS execution.

### Original visual evidence and limits

Each successful native run retains six application originals and five existing WebKit originals, with byte-count/SHA-256 manifests. All 22 downloaded PNGs match those manifests and retain their original dimensions. All six application images are byte-identical between the push and PR runs. The author and an independent reviewer inspected all eleven push originals and the four differing PR originals. Independent exact-source, raw-log and all-15-distinct-original review accepts this bounded sample evidence; this is evidence review, not a new local macOS or user-device run.

The application screenshots exercise the production window/controller with a test-only fresh-owned-source provider. The separate actual executable test proves empty-window startup and normal Quit; these are complementary gates, not screenshots of a child-process bundled-example journey. The five AppKit images are named-view regions rendered through the actual same-window visible ancestor; the sixth application image is an original WebKit viewport. The capture code retains ancestry/visibility/bounds and original bitmap dimensions, performs no fill/composite/resize and requires at least 99% fully opaque pixels with zero non-opaque interior pixels outside a 16-backing-pixel edge band. Every actual pixel in these five images is fully opaque in both runs. This measurement establishes rendered coverage only; original-pixel review is a separate gate.

Requested geometry is clamped by the hosted runner. Actual originals are: native controls/preparation 984×104, selector/scope 500×290, close confirmation 260×266, application catalogue viewport 1024×522, existing WebKit desktop 1024×656 and narrow 390×656. The screenshots are separate regions/viewports, not a composite, full-window, whole-screen or physical-device acceptance claim. Application image 74 shows the one-record count and only the beginning of its card in the 1024×522 viewport; it does not establish full-record visibility.

- [Push application artifact](https://github.com/krahd/disk_organiser/actions/runs/38024562204/artifacts/11659837730): ZIP SHA-256 `108f1aa02fdc134dd6a84815ecd5807001c09d33230a33ff52db4e708fe6c576`.
- [Push WebKit artifact](https://github.com/krahd/disk_organiser/actions/runs/38024562204/artifacts/11659812698): ZIP SHA-256 `cbc1de8b3cd46ca5cc25d7207d4d1c3a0ecfa2ec35e873f869aa294944da1313`.
- [PR application artifact](https://github.com/krahd/disk_organiser/actions/runs/38024564977/artifacts/11659603229): ZIP SHA-256 `b74e790c18d88d57acd02179cd56789489633fddb54dbb3bfe82c81223c75d85`.
- [PR WebKit artifact](https://github.com/krahd/disk_organiser/actions/runs/38024564977/artifacts/11660182736): ZIP SHA-256 `824f67101ca36fe00f85582b701195d43659bf6bab293d1a11a9ea6388b5f301`.

Actions retention is 14 days. These links and hashes are provenance, not a permanent image archive; no durable archive is claimed.

### Superseded diagnostic checkpoints

- `66bed567` compiled and ran 82 cases: 81 passed, but separate-process readiness collected no receipt before its bound. Normal Quit was not reached and downstream checks were skipped. `32c88e95` preserved that result while reporting the exact child active/registered and zero receipt bytes.
- `a86de13f` repaired only the test's owned-pipe collector: one 1-KiB nonblocking read, unchanged 4-KiB aggregate cap, deliberate EOF/error retirement and EAGAIN/EINTR handling. Two added regressions cover a short write while the writer remains open and aggregate overflow. Both runs passed 84 + 6 + 6, including the unchanged production startup and normal-Quit contract. The receipt-collection gap was therefore resolved without relaxing application readiness.
- Initial native view caches contained transparent undrawn regions. `f82e249d` and `7617af00` preserved process success but rejected the ancestor's `isOpaque=false` declaration before capturing (83/84 cases; downstream skipped). The latter confirmed same-window/ancestry/visible geometry. `c55f1894` retains those geometry/dimension gates and validates actual unaltered alpha instead; both runs pass and original images are now complete.

The pipe implementation follows Apple's [read](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/read.2.html) and [fcntl](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fcntl.2.html) contracts. Apple documents [cache transparency](https://developer.apple.com/documentation/appkit/nsview/cachedisplay(in:to:)), the [ancestor lookup](https://developer.apple.com/documentation/appkit/nsview/opaqueancestor), [drawing-opacity declaration](https://developer.apple.com/documentation/appkit/nsview/isopaque) and [bitmap pixel read](https://developer.apple.com/documentation/appkit/nsbitmapimagerep/colorat(x:y:)). These sources explain the bounded repairs; hosted logs and original images establish the observed result.

### Remaining product gates

Independent exact-source/log/original-pixel closeout accepts the scoped sample evidence. Final documentation-head CI, guarded merge and actual-main verification remain open. Native success applies to the development/sample preview only. It does not establish a signed/distributed app, OS-selected read-only folder grant, container Save/Open/relaunch, actual external-drive identity/reconnect, content identity or backup protection. The next approved source slice is separately reviewed bounded app-owned library Save/Open/relaunch against fresh owned storage, followed promptly by signed-picker feasibility. User-drive access remains a separate gate.
