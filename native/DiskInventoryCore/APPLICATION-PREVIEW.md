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

The existing 64 native cases remain required, followed by six independent native/Python differential and six unchanged-parser/catalogue checks. Eighteen new application cases cover the native sample/scope/Add/Cancel journey, immediate cancellation/close before provider invocation, notification re-entry, held-provider and delayed-stage cancellation/close, Add-before-retirement bookkeeping, real dirty-close Keep/Discard/repeated requests, close-question preservation, native-to-WebKit Escape/focus, startup gating, fixed examples and separate-process startup/normal quit/argument rejection. Source checks also verify all seven canonical view assets and the two allowed examples plus manifests. No source path comes from a test environment variable.

Six new original captures are required for the application journey: native library controls, sample selector, scope review, preparation controls, the embedded catalogue viewport and the native discard confirmation. AppKit captures are explicitly scoped to the named native view; the WebKit image is a viewport snapshot. They are not combined, resized, whole-screen or full-window evidence. Screenshot writes are test-only, exclusive/no-follow, fixed-name, six-image/5-MiB-per-image bounded and restricted to `RUNNER_TEMP/disk-application-preview-screens`. A complete manifest is required. Actions retention is 14 days; no permanent archive is claimed.

## Current acceptance

Local Linux checks pass 665 Jest, 39 catalogue DOM groups, 16 native-bridge DOM groups and frontend formatting. Asset/example parity and strict parser admission of the two example files pass. Independent initial review confirmed a missing pre-provider fence and synchronous Quit re-entry. The source repair adds those fences, defers final termination, restores WebKit focus after native sheets and protects an active close question from late state updates. Independent source review accepted the repaired source before publication. At `66bed5675a6cbc0782d8a827e009d792df69ff7f`, both hosted native runs compile the executable and run all 82 cases: 81 pass; the separate-process empty-window readiness case fails after 20 seconds with two assertions. The 16 native window/lifecycle cases, prior 64 cases and unknown-argument rejection pass. Normal Quit is not reached and the downstream six differential/six parser checks are skipped. All ten other workflows pass. The failure does not yet identify the child startup phase. A narrow successor adds only fixed phase/boolean diagnostics with the same bounds/readiness/Quit requirements. There is no local Swift compiler. Process success, downstream checks and original-pixel closeout remain **incomplete**. PR23's separately documented 64 + 6 + 6 success is previous evidence, not acceptance of this extraction or app shell.

Next: finish slice 1's actual native/pixel gates; then implement separately reviewed bounded app-owned library Save/Open/relaunch; promptly investigate the signed read-only picker and ancestor-open feasibility on owned fixtures. Actual user-folder administration stays the product goal. No real-folder, physical-drive, capacity, content-identity or backup claim follows from exploring samples.


### Owned-pipe receipt repair checkpoint

The diagnostic push run at `32c88e958af8cd5394f4cbbf9e1044dcd2ad3ece` sees the exact child registered, finished launching and active while collecting zero receipt bytes. This is evidence of an observation gap, not proof that the child view passed readiness. The next test-only collector uses a single 1-KiB nonblocking `read` on its own pipe, with the unchanged 4-KiB aggregate cap. Two additional cases require a short write to arrive while its writer remains open and reject overflow. All prior 82 cases remain, so 84 are required. The application, startup/quit assertions and time bounds remain unchanged; the repair is unexecuted.

The owned-pipe implementation follows the bounded/nonblocking semantics of [read](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/read.2.html) and [fcntl](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fcntl.2.html). These references do not replace actual hosted execution. The separate transparent native-capture gap remains open; this receipt repair does not change capture source or images.
