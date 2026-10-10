# Isolated selected-folder adapter: source tranche

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
