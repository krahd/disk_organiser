# Next milestone: a usable native storage library

Proposal for review, 10 October 2026. Baseline: PR23 merged main `2952fa64db55944096cc80777964e24a187857c0`, tree `1e25f6784d8060ce3111f9b2d4c5f2e2f88da768`. All six actual-main workflows passed. Approved source scope: slice 1 application shell/shared presentation and owned-sample selection/scope/progress/cancel, followed by a separately reviewed slice 2 bounded Save/Open/relaunch. Execution is limited to fresh owned fixtures; real picker activation, entitlements/security settings and user-device access remain separate gates.

## User outcome

Open a native Disk Organiser window, see a visual library of labelled recorded locations, deliberately choose one project folder, review the exact read-only scope, observe bounded metadata, review/Add or Cancel the snapshot, then explicitly save the edited library and reopen it after relaunch. Search and comparison remain useful while a source is unplugged. Recorded folder names are not physical-drive IDs; capacity, current presence and backup protection stay unknown unless separately evidenced.

The first useful product is this coherent loop, rather than another standalone scanner, file-hunting workflow or test-only bridge. It does not need backup deals, a backend server or filesystem mutations.

## Smallest source implementation sequence

1. **Native application shell and source-selection experience.** Add an isolated AppKit application module/bundle definition and library window, with native toolbar actions, empty state and scope/progress/cancel panels. Reuse the canonical bundled catalogue and reviewed bridge policies through a narrowly extracted shared presentation component; keep event injection, screenshots and fixture constructors in test targets. The default home is empty and never scans at launch. Use native AppKit rather than a second UI framework or Python process.

2. **Complete the library loop.** Native Save requests a versioned, bounded data-only catalogue export from the fixed current view; Open lists only this app's known generated catalogue files and stages replace/cancel. Add strict validation, revision/nonce acknowledgement, one-use save intent, exclusive fixed-directory publication and an uncertain-result reconciliation path. No arbitrary path, name, code or native command is accepted from JavaScript. Save records edited labels/history, not only the latest scan. Dirty Close/Quit offers Save/Discard/Cancel. This is a separately reviewed extension beyond PR23's inbound-only bridge and no-writer host.

3. **Author the real selection adapter behind its own gate.** A native directory-only, single-selection NSOpenPanel action, followed by scope review and an explicit Read metadata action, is the eventual sole production admission route. The picker adapter is compiled and source-reviewed separately from the fixture application, but not invoked or linked into a runnable development fixture route before the signed-sandbox gate. No CLI/environment/drop/imported-string source factory. No bookmark, recent-root reopen, background watcher or automatic reconnect.

The work can be split into reversible PRs, but the milestone is not described as a usable real-folder product until selection, read-only sandbox admission and save/relaunch all pass their relevant gates.

## Code authoring versus runtime authority

**Safe to build and execute after source-scope review now:** application window, shared presentation component, selection/scope/progress state machine, native Save/Open lifecycle and bounded storage implementation against fresh test-owned source/storage fixtures only. A dedicated fixture configuration creates its own temporary sources in-process. Its selector presents a fixed list of those owned sources and Cancel, labelled “Owned sample folders”. The catalogue remains honestly temporary until an owned-fixture save succeeds. No default paths or externally supplied fixture roots are accepted.

**Safe to author and compile, but not activate now:** the real NSOpenPanel adapter and production admission interface. Production must fail closed if signed read-only admission is unavailable. A plain unsandboxed app with a working picker is not an acceptable shortcut. The owned-fixture source class must never be reused or renamed to admit a real selection.

**Needs a separate reviewed runtime/security gate:** the signed app target's exact sandbox/entitlement set, transient panel-scope ownership and release, compatibility of the current no-follow ancestor opens with the selected grant, and actual container persistence. No entitlement/profile activation or sandbox/security-setting change is part of the immediate source work. A suitable GitHub-hosted owned-fixture probe may establish some of this; generic XCTest or ad-hoc signing alone cannot certify the delivered app. Report any required signing/account capability before using it.

**Needs separate user-device permission later:** installation/launch on a user's Mac, selecting their project folder, unexpected OS prompts, representative external-drive unplug/reconnect and any claim about their hardware. No persistent source grants are proposed.

## Scope and state contract

- Native state: empty/ready → choosing → scope review → observing/stopping → snapshot review → catalogue preview. Cancel retires the current generation; no second selection overlaps unfinished release.
- Before descendant reads, show the exact chosen folder locally as inert text and ask for explicit observation. Reject broad system/home/volume roots and unknown, provider/cloud, network, package or unsupported source classes. Resolve neither symlinks nor aliases as a fallback.
- Reuse 2,000-entry/500-per-directory/depth-8/five-cooperative-second observation limits and 1 MiB snapshot limit. Preserve 32-record/10,000-entry/4 MiB catalogue budgets. Overflow preserves existing history.
- Hold native source authority only through observation; release descriptors and owned transient scope before preview or saving. Root-change/cancel/revoke/unsupported has no snapshot; descendant gaps produce honest partial data where admitted.
- Do not export native identifiers, selected absolute paths, grants or descriptor numbers. Native delivery stays untrusted historical JSON. No source identity, live-presence, content-identity or backup inference.
- Save/Open has a separate generation/revision fence. A delayed save cannot mark newer edits saved. Fixed app-owned destination only; no overwrite, autosave, cleanup, external Save As or Finder fallback in the minimal milestone.

## Required review and evidence

1. Review the module extraction, production/fixture build separation and capability factory before publication. Prove no public path-taking fallback or fixture admission in the real adapter.
2. Preserve all 64 native tests and six differential/six parser checks; add native app-controller cases for cancellation at every stage, double action, stale callbacks, resource release and window closure.
3. Add owned-storage tests for malformed/duplicate/oversized bytes, collisions, partial writes, readback mismatch, disk-full seams, save acknowledgement lost, edit-after-save, bounded listing and close/relaunch. Never test these on user records.
4. Run actual hosted AppKit/WebKit app-window journeys with genuine native event dispatch, keyboard focus and complete original viewport screenshots: empty home; scope review; progress/cancel; partial snapshot; two labelled locations; search/comparison; explicit save/reopen and dirty-close choices. Fixture selection is not OS-panel acceptance.
5. Independently review exact source, actual logs and originals, then final-head CI and guarded main integration. Preserve explicit runner, artifact-retention and skipped-coverage limitations.
6. Separately review and run the signed read-only native panel/grant probes on owned sources, including source-write denial, sibling/parent denial, ancestor-open compatibility and lifetime. Only then consider the real user-folder pilot.

## Source anchors

- [Current package has no product and test-only WebKit target](https://github.com/krahd/disk_organiser/blob/2952fa64db55944096cc80777964e24a187857c0/native/DiskInventoryCore/Package.swift).
- [Current controller only admits ownedFixture; lease ownership is process-local](https://github.com/krahd/disk_organiser/blob/2952fa64db55944096cc80777964e24a187857c0/native/DiskInventoryCore/Sources/DiskInventoryCore/ObservationController.swift). A production adapter therefore requires deliberate reviewed work, not wiring a URL to the existing fixture constructor.
- [Reviewed test-only view boundary](https://github.com/krahd/disk_organiser/blob/2952fa64db55944096cc80777964e24a187857c0/native/DiskInventoryCore/Tests/DiskInventoryPreviewTests/OwnedPreviewHost.swift).
- [Existing native onboarding contract: selection, transient scope, data-only save and signed gates](https://github.com/krahd/disk_organiser/blob/2952fa64db55944096cc80777964e24a187857c0/docs/drive-administration/NATIVE-ONBOARDING.md).
- [Executed owned-only preview acceptance and limitations](https://github.com/krahd/disk_organiser/blob/2952fa64db55944096cc80777964e24a187857c0/native/DiskInventoryCore/OWNED-PREVIEW.md).

This plan is a repository-derived design proposal, not new Apple API research or evidence that the unimplemented product gates have passed.

