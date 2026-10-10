# Owned WebKit catalogue preview

This test-only host exercises the native-to-visual handoff with freshly created test folders. It is not an application target or a signed/sandboxed user-folder integration. There is no picker, source grant, entitlement, bookmark, provider, persistent catalogue, container save, file operation or JavaScript-to-native message handler.

## Data and view boundary

`DiskInventoryPreviewTests` contains the entire AppKit/WebKit host and its harness. The package still has no products or executable. Its existing core source is unchanged. A test creates its own `OwnedFixture`, obtains one core result, checks that source descriptors and ownership have been released, and passes only the bounded immutable UTF-8 snapshot bytes to the host. Absolute roots, descriptor numbers and native permission objects do not cross into the page.

The view uses a nonpersistent website data store and loads only its `Catalogue` resource directory. Seven copied HTML/JS/CSS files are checked byte-for-byte against the canonical frontend by `Validation/check_preview_assets.py`; its manifest and the directory allowlist must match. Updates use an explicit `--sync`; CI only checks and never silently repairs the copy.

The host accepts a prepared fixed content blocker from the test harness. Apple's [content-rule store](https://developer.apple.com/documentation/webkit/wkcontentruleliststore) persists its compiled cache, even when the website store is nonpersistent. The harness therefore creates a fresh owned temporary rule directory and compiles the fixed HTTP/HTTPS/WS/WSS/FTP blocker there before constructing the host. Failure prevents loading. The host contains no filesystem writer and never uses the default/shared rule store. These controls do not claim that WebKit or the OS performs no internal file activity.

The existing CSP remains unchanged. Navigation is restricted to the exact initial main document, including its `WKNavigation` object and current generation. Other navigation, redirects, subframes, windows and downloads are rejected. Upload panels return no URL; file drops are rejected. Rejected URLs are never handed to another app. A fixed document-start script marks embedded presentation only; this marker is not a grant or an authentication mechanism. Embedded Open/Save/manual-plan export are hidden, disabled and described as unavailable. The skip link moves focus without triggering navigation. Changes are explicitly described as temporary and unsaved.

## Bridge contract

The page exposes a frozen, non-writable `DiskCatalogueNativeBridge` only in embedded mode. The standalone catalogue has no ingress. Native calls use [fixed `callAsyncJavaScript` bodies and separately supplied arguments](https://developer.apple.com/documentation/webkit/wkwebview/callasyncjavascript(_:arguments:in:contentworld:)); no imported string is evaluated as JavaScript, HTML, URL or a native command.

- Version: `catalogue-data-bridge/v1`, distinct from all unchanged saved v1 formats.
- `initialise(version, session)`: one lower-case UUID session per loaded document; returns only version/session/ready.
- `stage(version, session, delivery, text)`: one lower-case UUID delivery, at most 1 MiB raw UTF-8. The existing strict catalogue parser must admit a snapshot, never a whole catalogue. It then uses the exact same snapshot preview and `C.add` path as file import. A busy preview/edit or pending delivery rejects. Delivery returns staged, not added or saved.
- `retire(version, session, delivery)`: establishes the page's synchronous Add fence and returns cancelled, committed or dismissed. An Add processed before the fence remains a valid historical record. A later Add closure cannot run. Retirement never closes a newer unrelated edit. An exact repeated retirement acknowledgement is idempotent; a different or unknown ID rejects.
- Each view retains at most 128 staged delivery IDs, with no eviction that could enable replay. Reaching this explicit test-session bound requires a newly created view. This does not change the independent 32-record catalogue budget.

The native host authenticates only its own current view/session/delivery objects in memory. Echoed UUIDs, imported source references and a successful schema check do not authenticate saved JSON, source identity, content versions, present storage or backups. Every admitted record remains unauthenticated historical data, with source dates and partial gaps retained.

The host waits for stage completion before issuing a requested retirement, including when Add was already displayed before that completion arrived. It checks exact shallow reply fields and current navigation identity. Invalid replies, missing acknowledgement or a retired view fail closed. Native calls have a ten-second acknowledgement timer; it retires the application state but cannot interrupt an arbitrary blocked OS/WebKit operation. A blocked view is hidden and cannot receive a new delivery. Recovery must construct a new host; no automatic retry or silent catalogue persistence is offered. Page navigation also permanently invalidates its bridge session.

## Verification plan and current evidence

The initial source checkpoint has 16 new DOM groups passing, together with the existing 39 catalogue checks, 665 Jest cases and formatting. It covers strict schema/byte checks, wrong sessions/versions, repeated delivery, busy edits, retirement ordering, inert hostile labels, unavailable controls, unchanged standalone operation and the explicit replay budget. Actual macOS compilation and WebKit test execution have **not yet run** at this checkpoint.

Five new XCTest methods are prepared:

1. Fresh core metadata → WebKit preview → native-event Add/Cancel → two-record comparison, focus return and desktop/narrow original screenshots.
2. Add before stage completion/retirement, and rejection of Add after the fence.
3. Late completion after an injected content-process-termination delegate notification. This is a lifecycle seam, not an actual process-crash test.
4. Invalid UTF-8, oversized, malformed and catalogue payload rejection, retaining prior records.
5. Actual CSP connection denial and denied top-level navigation. A CSP violation is evidence for that policy; it does not independently certify every possible network/resource channel or the content blocker alone.

The UI harness sends native `NSEvent` mouse events after checking geometry/hit targets, and Escape events while the snapshot label has focus. Test-only fixed JS queries observe state and frame screenshots; they do not replace Add with DOM `.click()`. Pointer/keyboard failure must remain a failure. Original [WebKit snapshots](https://developer.apple.com/documentation/webkit/wkwebview/takesnapshot(with:completionhandler:)) are written only by the harness, with fixed generated names and SHA-256 hashes in the exact runner-owned output directory. No user data is included. Five images are each capped at 5 MiB; a complete five-image manifest is required before acceptance. Failed/partial screenshot output is evidence of failure, not visual acceptance.

The existing macOS workflow retains its Xcode 16.4/16F6, SDK 15.5 and runner-identity assertions. It checks asset parity before running all existing 59 core tests plus the new target, and preserves the independent six native/Python and six unchanged-parser cases. The APFS invalid-name limitation from Phase A remains unchanged. The catalogue workflow also runs the new data-only DOM checks on Linux and Windows.

## Remaining gates

Independent source/trust-boundary review precedes publication. Exact-source hosted macOS compilation, actual WebKit interaction, original-pixel review, final-head CI and guarded main verification are required before accepting this host slice. Unsigned XCTest success cannot establish signed sandbox permissions, picker behaviour, grant lifetime, removable-volume identity, real user-drive behaviour, catalogue persistence, native browser-UI zoom or assistive-technology usability. Those remain separate implementation and device gates.

### Pre-review native API and timeout audit

The harness initializes NSApplication before WebKit and uses one-shot 10-second deadlines for rule compilation, script observations and snapshots. Framework objects remain on MainActor; snapshot continuations carry PNG Data. Delegate callback signatures explicitly retain MainActor/Sendable isolation. These source checks do not substitute for the pinned macOS compile and actual WebKit tests.

### First hosted event-driver failure

Source `f60ad3b9a949b5ed308ffc1ade4a2c60c525ea1f` compiled on the pinned toolchain. All 59 existing core cases and two new resource/lifecycle cases passed. The three new flows requiring native pointer Add failed; the differential/parser steps were skipped. The single original preview screenshot is failure evidence only, not a complete visual packet.

The original harness invoked `NSWindow.sendEvent` directly and did not wait for asynchronous app activation. [AppKit's window documentation](https://developer.apple.com/documentation/appkit/nswindow/sendevent(_:)) says not to invoke that dispatcher directly; [NSApplication dispatch](https://developer.apple.com/documentation/appkit/nsapplication/sendevent(_:)) routes events through the application. [Activation can lag](https://developer.apple.com/documentation/appkit/nsapplication/activate(ignoringotherapps:)). The proposed harness repair waits for active/key/visible state, preserves DOM/native geometry and enabled-state checks, dispatches ordered native events through NSApplication, and requires observed trusted mousedown/up/click events at the intended DOM coordinates. It logs the actual view dimensions, native hit target, activation/focus and event trace. No JavaScript click or keyboard substitute is used for Add. This is a source-supported diagnosis; the repaired hosted run must establish the actual cause and outcome.

The diagnostic PR run at source `447380fe` compiled and reached the same three pointer flows, but the new pre-dispatch guard measured `active=false`, `key=false`, `visible=true` in each. No native pointer was dispatched or counted as passing. The next test-only bootstrap performs [finishLaunching](https://developer.apple.com/documentation/appkit/nsapplication/finishlaunching()) once, which AppKit normally invokes before its event loop. Because that API can process launch-file defaults, the harness first rejects any NSOpen/NSPrint value and any existing application delegate, and installs a retained test delegate that rejects file, URL, untitled-document and reopen requests. It does not clear defaults, open documents, change permissions or add an application product. Active/key readiness, geometry and trusted native-event assertions remain unchanged. Whether this bootstrap resolves the runner's activation state remains a hosted-test question.

Source `9d55bd54` confirms that checked regular activation policy and finishLaunching alone leave the hosted XCTest application inactive with no key window. Its three pointer cases still fail before dispatch. The next harness diagnostic services only its own application's queue through [nextEvent](https://developer.apple.com/documentation/appkit/nsapplication/nextevent(matching:until:inmode:dequeue:)) and the normal NSApplication dispatcher: at most 32 already-available events per turn, a nonblocking expiration and the unchanged three-second readiness deadline. It also requests normal window updates. This is not a global event monitor, a permission change or a force-click path. Screenshots now require the same active/key readiness before capture. The missing AppKit event-loop hypothesis remains unproven until the hosted result; no input or visual assertion is waived.
