# Save the current Aurora display report

7 October 2026 · Accepted synthetic local-download checkpoint

## Existing gap and outcome

The accepted [Aurora observation view](OBSERVATION-VIEW.md) supports explicit project membership/path decisions, but its accepted review previously existed only in tab memory. **Save reviewed draft (JSON)** now offers a local, user-initiated record of the currently displayed successful explicit review.

This is a synthetic display report, not a canonical observation export and not replayable. It cannot authorise copy, restore, erasure or any other operation. It does not supply missing evidence or authenticate physical identity. Harbour, all HTTP routes, server/adapter code, source fixtures, styles and workflows are unchanged. No import, upload, autosave, native filesystem API, scanner, provider, executable plan or deployment is added.

## Availability and exact binding

Saving is enabled only after an explicit Review succeeds, the existing source/decision/authority checks pass, and the complete result renders. The displayed reference by itself cannot be saved through this action. Dismiss restores that reference and disables Save.

A private tab-memory snapshot binds the report to the current generation, immutable source revision/observation digest/reference-decision digest, projected decision revision 2 and decision digest. Review revisions remain stateless projections, not saved-project counters. Before every download, the current member selection, paths, intended root and folder must still equal the accepted intent, including a control change without an input event.

Any edit, new pending review, error, source reload, dismissal, page exit or back/forward-cache restoration clears export availability. Late responses cannot enable an old report. A download already requested before a later edit is not retroactively erased; later clicks cannot export that old snapshot.

## JSON display-report contract

Schema: `disk-administration-observation-review-export/v1`.

The explicit nested allowlist contains only displayed facts or identifiers needed to bind them:

- `report_kind: synthetic_display_report`, `canonical_observation_export: false`, `replayable: false`.
- Synthetic/read-only flags and false/null execution, undo, erasure and live backup/restore flags.
- Fixed scenario ID, source revision, observation/reference/decision digests as strings, and decision revision.
- Exact accepted explicit project/member/path/destination intent.
- Recorded and intended root-relative addresses and readable root labels; recorded kind/logical size/status/hash status; unresolved placement, retained sources and Unknown identity/version/dependencies.
- Exact displayed capacity and protection values, preserving null/Unknown and zero reclaimed bytes. Unknown-size paths remain named.
- Every blocker code/scope, the same human-readable explanation shown on screen, and readable recorded paths including unselectable occupants.
- Recorded root scopes/status, scan ID/status/counts, evaluation fixture clock/freshness and all displayed limitations.

The report deliberately excludes full canonical observations, fingerprints, device/inode/object identity assertions, nanosecond integers, raw hashes and undisplayed metadata. JavaScript cannot round undisplayed large fingerprint integers into a false identity claim because those fields are never serialised. Unknown extra response properties, nested headers/credentials and unrelated DOM/browser state are excluded; process tokens and request options never enter the report. Paths are JSON strings, never executable instructions or HTML.

The filename is fixed-shape ASCII: `disk-organiser-aurora-review-r2-<12 hexadecimal decision-digest characters>.json`. User-entered paths or labels cannot select a filename or destination. The MIME type is `application/json`. Normal browser download handling controls the local destination and any filename suffix.

## Download lifecycle and interruptions

A user activation creates a Blob and temporary object URL, activates a temporary download link and removes that link. Each URL is revoked on the next task, or sooner when intent changes/page cleanup occurs. Cleanup is idempotent across interrupted activation and timers. A failed revocation is disclosed and retained for a cleanup retry; it is not falsely reported as released.

Blob/URL creation or activation failure leaves the current accepted review available for retry. Repeated deliberate clicks use the same accepted report until a new successful review replaces it. The status says **Download requested**, never that a file was saved successfully; this page cannot observe the user's final save-dialog decision. Cancelling a browser download does not silently dismiss or invalidate the accepted review.

The browser cancellation check requests cancellation and records its actual result. Small JSON can finish before cancellation arrives; a completed download is not relabelled as cancelled. Subsequent download availability and exact bytes are checked in either case.

## Verification at source freeze

```sh
python -m unittest discover -s prototypes/drive_administration -v
python -m unittest discover -s prototypes/drive_administration/demo_tests -v
npm test -- --runInBand
npm run format:check
npx playwright test --config playwright.project-review.config.js --list
npx playwright test --config playwright.project-review.config.js
```

Local checks pass: 140 unchanged pure tests, 37 unchanged HTTP tests, 204 Jest tests (176 accepted plus 28 new), formatting/syntax and 25 parsed browser specifications (18 accepted plus seven download flows). The new Save availability specification first failed against the accepted old UI. Two further failing-before-fix assertions exposed re-entrant activation updating stale Save status and double revocation; snapshot checks and idempotent cleanup now cover them. A further author check reproduced one silent-control-change failure during a pending request; the export snapshot now binds directly to the echoed accepted decision and rejects controls that no longer match, even without an input event, with folder/root/member/path regressions. Existing collision, evidence and stale-response controls remain.

The seven new browser flows check actual downloaded JSON/filename/MIME and URL cleanup, exact server-response/display projection, Unknown/alias/unreadable states, same-address uncertainty, unselected occupants, token/fingerprint exclusion, pending/error/dismissal/reload states, keyboard activation, repeated downloads, cancellation request, 390/320-pixel reflow and 200% CSS zoom. The existing workflow automatically discovers them; no CI infrastructure is added. New screenshots are written once to its existing artifact directory rather than duplicated as attachments.

A fresh local attempt starts only the synthetic server, then cannot find the existing locked Chromium executable. No download or alternate browser was attempted. Local download/pixel success is not claimed. Independent frozen source and hosted download/pixel review accept the exact source below. Main integration and post-main checks remain separately guarded. Native browser-UI zoom, screen readers, real-drive/provider actions, replay/import and production readiness remain outside this slice.

## Accepted exact source, downloaded bytes and pixels

Accepted runtime/test source: [`c6ffb62ebddee564af597b6732027cbf028e3e87`](https://github.com/krahd/disk_organiser/commit/c6ffb62ebddee564af597b6732027cbf028e3e87), tree `df169dd99604c116cc742bb5020501608f672929`. Independent review verified all seven intended changes and 76 unchanged supplied files, then passed 57 additional cases including 27 actual Python-response exports, metadata injected into 173 admitted objects, silent intent changes and interruption/cleanup/failure/retry controls. The silent pending-intent finding is closed.

All three exact-head workflows passed:

- [Planner 37584999433](https://github.com/krahd/disk_organiser/actions/runs/37584999433): 140 pure-data tests on Linux and Windows.
- [Aggregate CI 37584999415](https://github.com/krahd/disk_organiser/actions/runs/37584999415): Linux 230 backend tests; Windows 181 passed/49 skipped; 204 Jest; 22 existing Chromium flows; 44-route OpenAPI checks, dependency audits, compatibility and formatting.
- [Isolated UI 37584999457](https://github.com/krahd/disk_organiser/actions/runs/37584999457): 37 HTTP contracts on each OS, 23 existing focused Harbour Jest tests and all 25 Chromium flows. The full aggregate Jest command covers the Aurora Save tests; no workflow was added or expanded.

[Artifact 11465879693](https://github.com/krahd/disk_organiser/actions/runs/37584999457/artifacts/11465879693) has ZIP SHA-256 `7f086b8787e53bbf0a2b20955a57c1e3aa47e1df2b501e4d66bc7904c3202d3d`. All 38 file hashes were verified. The actual downloaded `aurora-reviewed-display-report.json` is 12,899 bytes with SHA-256 `835af08ae9b21096f828f5ca941b3f319816f2bc07c9ccb306e77ba4a6f8f165`. Independent reproduction from the accepted Python review and explicit JavaScript projection matches these bytes exactly. Filename, JSON MIME, excluded data, stale-intent admission and object-URL cleanup checks pass.

Seventeen distinct screenshots cover the retained review and Save interaction. Independent inspection finds readable Save controls, keyboard focus, requested-download status and synthetic/non-replayable disclosures at desktop, 390-pixel mobile, 320-pixel reflow and 200% CSS zoom. No clipping, overlap or evidence-label regression is found. All seven Harbour PNGs remain byte-identical; the six prior Aurora views change only at appended Save content.

The cancellation receipt is exactly `requested: true`, `failure: null`: this small download completed before cancellation. Subsequent review availability and repeated exact download pass. Early cancellation before completion remains unverified; neither the UI nor this report claims otherwise. Native browser-UI zoom, assistive technology and real storage/provider operations remain outside acceptance.

This documentation-only closeout preserves every runtime/test/style blob from the accepted source. It does not attribute those runs to a later commit or trigger public documentation publication. No import, replay, live identity/protection proof, execution or recovery authority is introduced.
