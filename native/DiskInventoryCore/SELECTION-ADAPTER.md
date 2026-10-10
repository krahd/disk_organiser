# Isolated selected-folder adapter: source tranche

## Synchronous cancellation: executed regression

PR28 merged at `ecc64105fe05049ea23ccc2831b1078d5d3bb73f`; all six actual-main workflows passed, including 213 distinct XCTest methods and six differential/six parser cases. The earlier source/acceptance sections below are historical checkpoints.

PR29 source `dbb55a0963f3cab2a60c401dabc4db4c8d9b8aa0`, tree `2ace110bcc677e2288b7b2c19c4e9cb8727618b8`, changes only `SelectionLifecycleTests.swift` and status documentation. All 347 unaffected baseline blobs remain. All twelve push/PR workflows and 28 check runs pass. Native [push 38053041626](https://github.com/krahd/disk_organiser/actions/runs/38053041626), job `114215881779`, and [PR 38053048220](https://github.com/krahd/disk_organiser/actions/runs/38053048220), job `114215899228`, each start and pass **217 unique XCTest methods**, with all 213 actual-main identities retained, plus six differential and six parser cases. The PR job checks out `ce9242917b66852721b7a2f7bfb3237937a28acf`, independently read back to the identical tree rather than labelled the source commit.

The four added methods invoke completion synchronously from picker Cancel, picker Close returning a choice, reader Cancel returning success and reader Close returning failure. They assert stopping state inside the hook, prevent overlapping work, dispose matching ownership once, discard late success and preserve closed-state refusal. Each removes fixture/local strong references and asserts weak request retirement while the session stays alive. Picker Cancel does so before starting a replacement flight, which could otherwise hide stale retention. These are actual executed lifecycle tests; no OS grant or private panel owner is exercised.

Raw push log SHA-256: `ac1ac5fdbc19f608e667739b75c59b92154ed13cff2cc367f2c763642bd398bb`. Raw PR log SHA-256: `08bab8a495bd29abdd1d22dfe24cca8ab03f848c88ec5585c7e69707860c3891`. Xcode 16.4/16F6, SDK 15.5 and Swift 6.1.2 are recorded. Independent exact-source/raw-log review verifies these fresh originals and accepts the bounded execution; final documentation-head and merged-main checks remain required.

Evidence-transfer correction: two earlier local diagnostic copies were each 624 bytes shorter because shell interpolation altered echoed command/warning text. They are preserved as transformed diagnostics, not raw logs. The fresh originals above match independently fetched bytes and a verified hex-only connector round-trip (208,787 and 208,386 bytes). Every method identity/outcome is unchanged; no native rerun is required for this correction.

No new screenshot or aggregate browser/Windows coverage claim is made for this unchanged-UI tranche. Earlier complete original-pixel attribution remains `86d3620b`, with the documented named-region/scrolled/count-only limits and 14-day artifact retention. The APFS invalid-UTF-8 name refusal (errno 92), synthetic rejection, in-memory ACL versus owned absent-ACL tests, and owned-process/default-path boundaries remain unchanged. Skipped coverage is not promoted into a pass.

The synchronous callback prerequisite is now implemented and executed within memory-owned tests. Genuine signed-host selection, positive/denial transitions, ancestor compatibility, scope retirement and eventual private adapter/reader integration remain separate unexecuted gates. No quarantined feasibility host source, new workflow, signing, entitlement activation, real panel, permission or user-drive access is included in PR29.

## Isolated selection: executed owned validation

At exact source `1e669bdc36033b6165a460b7f80f48d4b1577acd`, tree `9b3cf7de79f45f6693152d556eb3f3074e9f1d11`, all twelve push/PR workflows pass. Both native [push 38049840760](https://github.com/krahd/disk_organiser/actions/runs/38049840760) and [PR 38049859463](https://github.com/krahd/disk_organiser/actions/runs/38049859463) validate the actual SwiftPM dependency graph, compile the isolated selection target, ordinary app and owned probe, and pass **213 XCTest methods + six differential + six parser cases**. All 194 baseline method identities remain, with 19 new methods. Xcode 16.4 build 16F6, SDK 15.5 and Swift 6.1.2 are recorded. PR checks out merge `0d174c4ad2c58454f5b4ebbde3895c48dfb4416a`, independently read back to the same tree; it is not the source commit.

The new executed methods prove memory-owned choice lifecycle and rejection before window lookup/panel construction. No real panel, private OS scope owner, selected-folder observer or signed host ran. Neither the ordinary product nor Desktop gains a selection/observer dependency. The 194 unchanged existing tests retain their own bounded fixture/process/UI evidence; this does not activate default-path user-device persistence or a real source grant.

Independent source and raw-log closeout verifies the exact twelve changed/new paths and 337 preserved repository blobs. Both logs contain 213 unique started/passed identities, without counting skipped or merely authored methods. The push log SHA-256 is `91bdc5513bd8f6ac7f8e345c34771eafeb4e9f986a2701b06e9a3e0fc874d65f`; PR log SHA-256 is `51dd64214540ce99c11e637574072718e1c54673241bc3555ad25c9d8974e8da`. This is review of hosted evidence, not another device test.

Five fixture archive digests and all 26 original captures are retained locally. Ordinary UI/assets and capture tests are unchanged. Nineteen PNGs match the earlier `86d3620b` originals byte-for-byte; the author opened the seven refreshed date/time views without alteration. Earlier complete pixel acceptance remains attributed to `86d3620b`; no new panel or full-window acceptance is claimed. These are named native chrome/sheet/WebKit regions, with view 87 scrolled and view 96 showing the reopened count. GitHub artifact retention remains 14 days; this is not a durable screenshot archive.

The earlier APFS invalid-UTF-8 filename refusal and synthetic rejection, in-memory ACL fixtures versus actual absent-ACL descriptor checks, and owned process-probe limitations remain as documented in [ordinary persistence acceptance](APP-PERSISTENCE-ACCEPTANCE.md). No aggregate browser/Windows coverage count is newly claimed here. Future integration must add synchronous cancellation-callback coverage and separately prove signed-host selection/scope retirement, source-write/sibling/parent denial and no-follow traversal compatibility before activation. Current signing, entitlement, bookmark, grant, user-device and real-drive gates remain closed.

Final documentation-head CI, guarded integration and actual-main checks remain required. The source-candidate checkpoint below is retained as history; its pending compile/review statements are superseded only for the exact executed source above.

10 October 2026. Approved source proposal SHA-256 `1c405bd117a46d31110668ee4fbea5059ef203e5b4b159ce929b624106f07d73`. Baseline PR27 main `41ad370cdfffe729458c6c319ccdce30afe00bb2` has all six workflows green, including 194 XCTest methods plus six differential and six parser cases. The following new code is authored but not yet compiled or executed on macOS.

## Purpose and build boundary

This is a small step towards Choose folder → Review scope → Read metadata → Review/Add or Cancel → Save library. It is not another source scanner or permission channel.

`DiskInventorySelection` is an isolated SwiftPM target with no dependency on the observer or application. No product exposes it; neither Desktop nor the ordinary executable depends on it. Its two source files supply a native panel adapter and a lifecycle model. The existing application UI, observer admission, storage, bundled assets and v1 schemas are unchanged. The real-folder button remains unavailable.

The dedicated workflow inspects SwiftPM's actual resolved target graph and compiles the target. The graph check only proves graph isolation. Separate native tests require the production gate to reject before window lookup or panel construction. No test presents NSOpenPanel. Five pure graph-oracle tests pass locally; **19 additional XCTest methods are authored**, for 213 total including the 194 unchanged baseline methods. New native results are pending.

## Production adapter, intentionally unavailable

- A private host-permit type has no accessible constructor. The only gate returns nil. There is no boolean/JSON/argument/environment switch, signing fallback or test unlock for the real adapter.
- The gate runs before even querying the supplied native window, creating NSOpenPanel or reading any location. The adapter has no default directory or remembered/reopened URL.
- Behind that closed gate, the compiled implementation configures directory-only, single selection, no creation and no alias/package resolution. It owns a native sheet operation and adopts only successful panel-returned URL objects directly, without rebuilding them from strings.
- The private scope owner permits one claimant and idempotent retirement. Cancellation/refusal and abandoned results release owned scope; a duplicate callback cannot release a choice claimed by another owner. No URL, descriptor or permission is exposed through the lifecycle protocol or persisted.
- Apple documents that successful standard-panel URLs arrive with security-scoped access already started; this adapter does not start it again and its private owner balances the adopted scope with stop. This is source design, not actual panel/sandbox lifetime proof.

## Lifecycle contract and owned tests

The injected picker, reader and choices are memory-owned test doubles, not OS grants, file paths or observation leases. The production default reader is unavailable. No actual observer or snapshot output is connected; a fake reader's completed marker tests ordering only and cannot authenticate or create a catalogue record.

| State | Action/result | Required outcome |
| --- | --- | --- |
| Idle/finished | Choose | One pending picker; duplicate Choose does nothing |
| Choosing | Cancel/Close | Stop admitting results; wait for picker retirement |
| Choosing | Selected | Claim exactly one opaque lifetime and show its inert display name |
| Reviewing | Cancel/Close/abandon | Retire unborrowed choice; no read starts |
| Reviewing | Read | New generation invalidates old picker callbacks; one injected worker |
| Reading | Cancel/Close | Request cancellation; retain borrowed lifetime until worker completion |
| Stopping | Late picker/read completion | Release the matching lifetime; discard success; do not overlap a new choice |
| Any | Old/duplicate callback | No replacement of current state and no release of another owner's choice |
| Closed | Any new action | Remain closed |

A retained claim survives an abandoned session while its reader completion remains outstanding. An unborrowed review claim retires on abandonment. A completion is the injected worker's promise that borrowed access is retired; cancellation does not forcibly interrupt an OS call. An unreturned completion remains stopping rather than permitting overlapping work. These are lifecycle tests, not filesystem or sandbox claims.

## Later gates

Independent frozen-source review precedes publication. Actual macOS compilation and all preserved native tests remain required. No new screenshot claim is requested because the ordinary application's UI is unchanged and the new native panel is never shown.

Before any real adapter activation, a separately reviewed signed-host probe must establish the exact sandbox/read-only entitlement set, genuine owned-folder panel selection, source-write/sibling/parent denial, transient scope retirement and compatibility of the current no-follow ancestor opens. If that algorithm fails under the actual grant, stop rather than follow aliases or weaken checks. Broad roots and unsupported source classes need deliberate admission policy. Do not relabel `.ownedFixture` or use an unsandboxed picker as a substitute.

No signing, entitlement activation, persistent bookmark, native panel presentation, user Mac/default-path access or real-folder observation is authorised by this tranche. Device and representative-drive validation remain later explicit gates.

## Checked primary sources

On 10 October 2026, Apple's [sandbox file-access guidance](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox) documents OS-mediated selection, automatic scope start for panel URLs, explicit stop and recursive selected-folder access subject to other controls. Its [user-selected read-only entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.files.user-selected.read-only) defines the proposed access category. The [entitlement reference](https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/EntitlementKeyReference/Chapters/EnablingAppSandbox.html) requires App Sandbox for those restrictions. None of these sources proves this implementation's unexecuted native path works.
