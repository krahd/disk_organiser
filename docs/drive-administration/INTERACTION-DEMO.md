# Simulated project organisation and protection review

## Purpose and boundary

This standalone interaction demonstrates a small part of the drive-administration product: decide which files belong to Harbour, choose a proposed home, then read the layout, dependency, capacity and protection consequences. A map supports that decision; it is not the product endpoint.

The permanent page banner says **Simulated project; no drives or providers connected**. Only the two existing packaged synthetic fixtures can be loaded. No scanning, file picker, arbitrary document import, upload, provider credential, telemetry, external request, execution, restore, undo or recovery-deletion route is present. The existing default app, navigation, backend and execution/recovery gates are unchanged.

The example contains fabricated dated backup and restore records. A fixture claim never becomes live verification. Every result, including errors, has `executable: false`, `execution_authority: null`, `undo_available: false`, `source_safe_to_erase: false`, `live_backup_verified: false` and `live_restore_verified: false`.

## Run the isolated demo

Use the repository's existing pinned Python dependencies and Node lockfile; no dependency was added.

```sh
python -m pip install -r backend/requirements-locked.txt
python prototypes/drive_administration/demo_server.py --port 8765
```

Open `http://127.0.0.1:8765/` in the same computer's browser. `localhost`, a different Host header, proxy publication and non-loopback clients are deliberately rejected. Stop the process to end the demo. This is a development-only server, not a production deployment.

`create_demo_app()` is separate from `backend.app`, `guided` and `op_store`. It loads exactly three named frontend assets once during creation. It makes no request-time filesystem or network calls. No draft is stored on disk or in the Flask process; drafts live only in the current page's memory. Reload, scenario switch and back/forward cache restoration discard the draft. The ephemeral process token is regenerated on restart and is never stored in browser storage or logs.

## Three-step decision loop

1. **Project members.** Suggested, added, removed and excluded members are explicit. Each entry shows its kind, size, content version, declared dependencies and dependency-coverage uncertainty. An impossible selection is rejected; missing dependencies remain visible as blockers from the accepted Python evaluator.
2. **Proposed home.** Choose one packaged volume and a relative folder. Current paths remain beside the decision, and the reviewed result places each current path beside its exact proposed copy path. Sources are retained and no space reclamation is claimed. Choosing the existing home produces the evaluator's occupied-path blocker. There is no fake “keep current” or successful no-op contract.
3. **Layout and protection.** Review issues, logical capacity and reserve, per-target/version backup evidence, snapshot identity, dates, checks, restore scope, matching members and unresolved alerts remain visible. Configuration is distinguished from content verification, a sample restore from a project restore, and recorded outcomes from verified live protection. The fixture clock is displayed and is not the current time.

**Review proposed layout** calls the Python `revise` and `review` functions. JavaScript renders their results and does not reproduce their dependency, collision, capacity or protection rules. **Dismiss proposal** restores the exact scenario reference decision and reference review, then returns keyboard focus to the review button. It does not invoke undo or any file action.

## HTTP contract

Only five paths exist:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Demo HTML containing the ephemeral process token |
| GET | `/project-review-demo.js` | Fixed script asset |
| GET | `/project-review-demo.css` | Fixed stylesheet asset |
| GET | `/api/reference?scenario_id=harbour-reference` | Immutable reference, with `harbour-uncertain` as the only other accepted ID |
| POST | `/api/review` | Evaluate bounded membership/destination edits |

All access requires a loopback remote address and the exact configured `http://127.0.0.1:PORT` host. Cross-site Origin and Fetch Metadata are rejected. APIs require `X-Demo-Token`; POST also requires an exact same-origin Origin header. No CORS permission is granted. Responses use a restrictive CSP, no-store, nosniff, no-referrer, frame denial and disabled camera/microphone/geolocation permissions. Assets cannot be selected by a client-supplied path, and errors do not reflect route paths or filesystem details.

The POST content type is `application/json`, its body is at most 4096 bytes, and its object must contain exactly these fields:

```json
{
  "scenario_id": "harbour-reference",
  "expected_revision": 1,
  "expected_digest": "<immutable reference_digest returned by /api/reference>",
  "member_ids": ["edit", "media", "notes"],
  "destination_volume_id": "archive",
  "destination_folder": "Client projects/Harbour"
}
```

Member IDs must be unique and drawn from the chosen fixture, with one to four selected. Destination volume IDs must be from the same fixture. The folder is bounded to 240 characters and validated as a portable relative address by the existing evaluator. Unsupported fields, duplicate JSON keys, malformed/deep JSON, non-finite numbers, invalid types and extra query parameters are rejected. No client field can change backup, restore, policy or observation evidence.

### Revision semantics and races

`expected_revision` and `expected_digest` always identify the immutable fixture reference. They **never** refer to the previous projected result. Every request independently revises reference revision 1 into projected revision 2, so a second or third valid edit does not falsely conflict. A digest is an identity check, not execution authority. A changed or mismatched reference returns HTTP 409 and requires reloading the scenario; there is no silent retry against a different baseline.

The UI invalidates the accepted review whenever membership/destination changes. A generation guard plus cancellation ensures an old success or error cannot replace newer edits, a newer review, another scenario, a reload or dismissal. Repeated clicks produce only one outstanding request until an edit or reset invalidates it. Errors retain the editable draft while clearing the invalid result. Response identity and all safety flags are checked before rendering. Labels, paths, evidence and errors are inserted as text, never interpreted as HTML or URLs.

## Verification

```sh
python -m unittest discover -s prototypes/drive_administration -v
python -m unittest discover -s prototypes/drive_administration/demo_tests -v
npm test -- --runInBand
npm run format:check
npx playwright test --config playwright.project-review.config.js
```

The new HTTP tests live in a non-package subdirectory so the existing standard-library-only evaluator workflow still runs only its 68 tests. The isolated demo workflow installs the existing dependency lock and tests HTTP contracts on Linux and Windows, then runs Jest and Chromium against only this synthetic loopback server. No production app is started. Browser traces are disabled; screenshot artifacts contain only synthetic page content.

Local results at source freeze: 68 evaluator tests, 20 HTTP tests and 19 focused UI tests passed. Full copied-frontend Jest and formatting results are recorded in `STATUS.md`. Seven browser specifications were parsed and listed, but local Chromium could not launch because the execution environment denied its socket operation. No alternate launch or bypass was attempted. No local screen, browser pass or native hardware check is claimed. On source `63150c5`, both remote HTTP jobs passed and six of seven Chromium flows passed. The 200% CSS-zoom locator click failed before overflow and 320-pixel reflow checks were reached. Its actual screenshot shows an unobstructed Review button. The narrowly revised harness records the raw/scaled DOM rectangle and `elementFromPoint` evidence, requires an in-viewport hit on the visible enabled button, then performs an ordinary mouse click. It never uses force-click or programmatic control activation. All outcome, overflow and screenshot assertions remain. On source `74e5dde`, [isolated run 37545358916](https://github.com/krahd/disk_organiser/actions/runs/37545358916) passed Linux/Windows HTTP contracts and all seven browser flows, reaching the zoom, overflow and 320-pixel assertions. The subsequent evidence-only edit writes the numeric geometry JSON to the uploaded test-output directory, since an in-memory attachment alone was absent from the artifact. It does not change the pointer test or runtime. Final exact-head CI and persisted artifact results must be checked separately.

The browser specifications cover rendered desktop, mobile, 320-pixel reflow, keyboard flow and 200% CSS zoom screenshots; successive reviews; dependency removal; current-home collision; missing protection; stale response/error cancellation; and HTML-looking text. The 200% check is actual rendered CSS zoom, **not a claim of native browser-UI zoom**. Native browser zoom, screen-reader behaviour and representative hardware remain unverified.

## Remaining gates

This branch requires fresh independent review after source freeze. It is not a complete organiser or backup service. Native observation, authenticated backup evidence, safe execution/recovery, provider integration, persistent projects and commercial readiness remain separately gated. No merge, deployment, release, store submission or provider access is implied.
