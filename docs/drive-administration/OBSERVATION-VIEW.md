# Aurora observation-backed project draft

7 October 2026 · Accepted fixed synthetic interaction checkpoint

## Product job and boundary

Aurora connects the accepted [observation adapter](OBSERVATION-DRAFT-ADAPTER.md) to the existing isolated project-administration demo. A person can choose explicit members, intended project-relative paths and a recorded destination root, then inspect those intentions alongside the original observations and missing evidence. It is an incomplete observation draft, not the planner's stronger declared copy/keep-current review.

Start the existing isolated server and open `http://127.0.0.1:8765/observation-draft`, or follow **Review Aurora from synthetic recorded observations** from Harbour:

```sh
python prototypes/drive_administration/demo_server.py --port 8765
```

The permanent banner identifies synthetic observations and disconnected drives/providers. Harbour's two fixtures, evaluator outputs, styles and controls are preserved. A scoped Aurora-only intrinsic grid rule keeps member labels readable at enlarged scale. The default application and its 44-route OpenAPI contract are unchanged; the separate demo routes are documented here and in [the interaction contract](INTERACTION-DEMO.md).

The observation-view checkpoint added no arbitrary import, file picker, upload, native scanning, provider call, filesystem mutation, execution/recovery, autosave, export, deployment or real-observation flag conversion. This observation-view checkpoint itself has no export. The later [Save review slice](SAVE-REVIEW.md) adds only a current, successful explicit display-report download; its verification is separate.

## Fixed source and explicit intent

`observation_demo_fixture.py` constructs one canonical-derived synthetic scenario entirely in memory from the existing pure fixture producer. The canonical producer, schema and JSON fixture are unchanged. The scenario contains 32 records across two recorded roots; the second root and its formerly observed entries are explicitly stale. Copied fingerprint/object assertions do not establish separate physical drives or independent copies.

Eight fixed records are selectable. Three begin included. The other choices expose unreadable/unsupported, stale and alias uncertainty. A separate 32-record ID/root/path display index names unselected occupants in collision explanations; it never expands selectable membership. Folder roles, project hints and hashes do not choose membership. Relative paths remain lexical strings, never file operations.

The reference is source revision 1 with a source digest, reference decision digest and fixed fixture clock. Review returns decision revision 2 against that immutable reference every time; it is a stateless projection, not a saved-project revision counter. The response echoes the exact accepted explicit decision and the Python adapter's draft. Nothing acknowledges or authenticates real source observations.

## HTTP contract

The original five demo paths remain unchanged. These four are added under the same loopback/exact-host, origin, Fetch Metadata, process-token, CSP and response-header controls:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/observation-draft` | Fixed Aurora HTML with the process token |
| GET | `/project-observation-demo.js` | Fixed Aurora script |
| GET | `/api/observation/reference` | Fixed source identity, choices, root scopes, path labels and initial draft |
| POST | `/api/observation/review` | Review explicit intent against that immutable source |

All five frontend assets are read once at application creation. The source/reference is also constructed at startup. Handlers do not read files, open sockets, scan, call the existing planner, or connect to providers. No query parameters are accepted by the observation APIs. GET requires the token; POST additionally requires exact same-origin Origin and JSON MIME type. The existing 4096-byte strict JSON limit, duplicate-key/depth/non-finite rejection and safety-labelled errors remain.

The POST object accepts exactly:

```json
{
  "expected_source_revision": 1,
  "expected_observation_digest": "<reference observation digest>",
  "expected_reference_decision_digest": "<reference decision digest>",
  "member_paths": [{"entry_id": "<one of eight choices>", "project_path": "Design/final.blend"}],
  "destination_root_id": "<one of two recorded roots>",
  "destination_folder": "Projects/Aurora"
}
```

There must be one to eight distinct listed members. Each intended path and the destination folder is at most 240 characters and passes the adapter's relative-address validation. The project ID/label and reviewed acknowledgement are fixed server-side. Clients cannot submit models, clocks, evidence, volume identities, backup claims, policies, credentials or execution instructions. Any reference mismatch returns 409 without evaluating a different source.

## What remains Unknown

- Current physical volume identity, current availability, case/Unicode naming semantics and authenticated content versions remain Unknown. A recorded verified hash is shown only as a recorded assertion.
- Application dependencies, backup configuration/coverage, independent-copy count and restore scope/usability remain Unknown. Both live verification flags remain false.
- Logical copy bytes, required destination space, free destination space and physical allocation stay null/Unknown. Known recorded logical sizes count selected paths, including stale entries and aliases; missing sizes remain named. This small fixed scenario uses safe display-sized integers. No general large-integer browser import is introduced.
- Matching the same root/address remains `current_address_requires_identity`, with no safe no-op. A different intended address does not establish a copy. All sources are retained and reclaimed bytes remain zero.
- Partial scope, errors, exclusions, recorded stale status, unsupported/link states, collisions and omitted analysis are retained. A missing observation does not prove deletion or absence.

Every response remains synthetic/read-only, non-executable, with null execution authority and false undo/source-erasure permission. Digests bind this displayed synthetic input and intent; they are neither authentication nor operation authority.

## UI state and response integrity

Edits immediately remove the accepted result. Generation checks plus cancellation prevent late successes/errors from restoring a result after edits, dismissal, reload, a newer review or back/forward-cache restoration. Repeated activation creates only one pending request. Errors retain editable intent but clear the result. Dismiss restores the exact reference decision and returns focus to Review. Reload discards local edits; no draft is persisted.

Only text nodes are used for paths, labels, errors and evidence. Admission checks retain all false/null safety flags, all Unknown proof/capacity fields, source/reference identity and the exact submitted decision. Projected member IDs must uniquely cover the requested set; source observations, displayed provenance, address projection, unresolved placement and recorded-size summaries must agree with the immutable reference. These are transport/display consistency checks; dependency, collision and protection rules remain solely in the Python adapter.

Collision scopes use actual set equality before saying **All selected members**. Other scopes name the actual root/path participants, including recorded occupants outside selectable membership. Counting two participants does not mean two selected members are involved.

## Verification at source freeze

```sh
python -m unittest discover -s prototypes/drive_administration -v
(cd prototypes/drive_administration && python -m unittest discover -v)
python -m unittest discover -s prototypes/drive_administration/demo_tests -v
npm test -- --runInBand
npm run format:check
npx playwright test --config playwright.project-review.config.js --list
npx playwright test --config playwright.project-review.config.js
```

Local checks pass: 140 unchanged pure-data tests in both working directories, 37 HTTP tests (22 existing plus 15 new), 176 Jest tests (123 existing plus 53 new), full frontend formatting, compilation and 18 browser-spec parsing (seven existing plus 11 new). The original exact HTTP route/asset count assertion intentionally expands from five/three to nine/five; all routes are still explicitly allowlisted.

Pre-freeze adversarial review found a response-admission gap (duplicate rows, altered recorded facts and inconsistent placement) and a collision-scope label that compared counts instead of sets. Four and one respective failing-before-fix Jest assertions reproduce these findings, and the repairs pass. A further duplicate unselected reference-choice finding has one failing-before-fix assertion; unique choice/root admission and malformed provenance regressions pass. No negative collision or evidence test was removed.

A fresh local browser attempt starts only the isolated loopback server, then fails because the locked Chromium executable is absent at the configured Playwright cache path. It is not the historical socket-permission failure. No browser download or alternate launch was attempted; local pixels and browser success are not claimed. The unchanged existing hosted workflow discovers all 18 specifications and saves synthetic screenshot/geometry evidence. Independent frozen source/API review accepts source `e6961bc74bff10633a162d182ca06308365f88d9`, including 587 additional HTTP cases and 36 JSDOM cases. Its aggregate `37579859328`, planner `37579859269` and isolated UI `37579859355` workflows all passed, including 18 isolated Chromium flows. Pixel inspection nevertheless found that the fixed two-column member grid compressed labels at 200% CSS zoom. A scoped intrinsic-width grid repair now has a failing-before-fix Jest regression and explicit browser column/label-width assertions. The repaired source and replacement pixels are independently accepted below; the initial green runs are not attributed to the repair. CSS zoom is not native browser-UI zoom or assistive-technology acceptance.

## Accepted repaired source and rendered evidence

The accepted runtime/test source is [`57e06d1460ee689ffc8a0fda4ef85d394f6d88b5`](https://github.com/krahd/disk_organiser/commit/57e06d1460ee689ffc8a0fda4ef85d394f6d88b5), tree `fe55f3b32d722681e80d6a5be7772c01fa3cfcba`. Independent review verified the exact five-file zoom repair over the first source and every unrelated blob, including the manual-only documentation publisher. All four source/rendered findings are closed.

- [Planner run 37580973081](https://github.com/krahd/disk_organiser/actions/runs/37580973081): 140 pure-data tests on Linux and Windows.
- [Aggregate run 37580973068](https://github.com/krahd/disk_organiser/actions/runs/37580973068): Linux 230 backend; Windows 181 passed/49 skipped; 176 Jest; 22 existing Chromium flows; 44-route OpenAPI checks; dependency audits, compatibility and formatting.
- [Isolated UI run 37580973070](https://github.com/krahd/disk_organiser/actions/runs/37580973070): 37 HTTP contracts on both OSes, 23 existing focused Harbour Jest tests and all 18 Chromium flows, including eleven Aurora flows. The new Aurora unit tests run in aggregate CI's full Jest command; no workflow was expanded.

The [synthetic screenshot artifact 11464836743](https://github.com/krahd/disk_organiser/actions/runs/37580973070/artifacts/11464836743) has ZIP SHA-256 `b9e3cd6a77580157165354d595ac4600983c28604fa6bd2214197e4b7cd43e33`. All 32 screenshot/geometry file hashes were verified. Thirteen distinct screenshots cover Aurora and Harbour. Only the Aurora 200% screenshot changes after the repair; the other twelve are byte-identical, including every Harbour screenshot. Measured enlarged member labels are 332.672–358.281 CSS pixels wide in one column. The desktop stays two-column. Independent inspection confirms readable Unknown labels, current/intended addresses, unselected-occupant scope, 390/320-pixel reflow and keyboard focus, with no clipping or overlap. The accepted CSS-zoom screenshot is 1280×13562; this remains a long-form synthetic review, not a participant-tested compact production interface.

Keyboard edits/review/dismissal, stale responses after edit/dismiss/reload, stale-reference retry, text-only HTML-looking paths and back/forward navigation all pass against the actual loopback server. All action/restore/erasure limits remain visible. This is bounded synthetic interaction acceptance, not native browser-UI zoom, screen-reader, real-drive, provider, restore or commercial acceptance. This documentation-only closeout preserves every runtime/test blob from the tested source and does not attribute those runs to a later commit. Main integration and post-main CI are separately guarded; no public documentation deployment is implied.

## Next boundary

The later [Save review slice](SAVE-REVIEW.md) implements a user-initiated display-report download of the exact currently displayed successful explicit synthetic review, revision-bound and non-executable. Its source/browser acceptance is separate from this observation-view checkpoint. It must not save pending, edited, errored or stale results or process tokens, and must not introduce import, execution or autosave authority. Native volume identity, permissioned scanning, authenticated backup evidence, real execution/recovery and commercial readiness remain separately held.
