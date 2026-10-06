# Read-only Disk Map import/view checkpoint

## Scope and provenance

This is the first integration of the structured Disk Model into an explorable interface. It opens an exported observation snapshot; it does not activate a scanner endpoint, filesystem action, model provider or background job.

- Accepted guided foundation: `27b3c6760832f32d2b80a5e4ae95cf1362f17a52`, PR 12. Its source branch and review state are untouched by this checkpoint.
- Published model foundation: `96c58ba41a0bc0a61196c490e60cdc551164f7a7`, branch `codex/disk-model-v1-20261006`. Only its nine owned Python source/test/schema/fixture/document files are copied unchanged. The older model branch's shared STATUS is not copied over the accepted guided status.
- The producer has separate draft PR 13 at the published model revision. This integration is saved only on a new source branch; it creates or updates no PR and leaves accepted PR 12 unchanged.
- `docs/disk-model-v1.schema.json` and `backend/tests/fixtures/disk-model-v1.json` are the canonical import contract/example. Browser JSON copies are byte-identical; `model-assets/bundled.js` wraps those exact texts to avoid fetching data at runtime. `scripts/sync_disk_map_assets.py` and unit checks enforce parity.

Canonical Git blobs:

- Schema: `be2fd9b09dd864f3aeed5aaaf6807d80f61cc0a0`
- Synthetic fixture: `f844fcde2bb98dda0c1cf8eb5a1e1cb2d02f4f0a`

## Focused product audit before the slice

The earlier extension overview cannot explain a project's relationships or uncertainty. The model foundation now supplies observed entries, role/name-family hypotheses, evidence links, qualified accounting and non-executable review alternatives. It does not yet supply content-derived project understanding or a coherent reorganisation plan. The UI must not fill those gaps with its own invented inferences.

This slice therefore makes the model's existing structure useful:

1. Open a fabricated example or a model export with an explicit privacy boundary.
2. Understand the snapshot's selected roots, observation time, partial/cancelled coverage and omitted-analysis limits.
3. Distinguish path-based logical size, observed-object logical size, known allocation and unknown physical/recoverable space.
4. Explore questions, folders, relationships, neutral entries and review choices with bounded search/filtering.
5. Open a conclusion to inspect concrete evidence, member paths, confidence, counter-evidence and uncertainty.
6. Keep review alternatives visibly non-executable. Inspect/retain/clarify-intent choices do not move files or constitute coherent reorganisation plans.

There is no backup-health inference. A matching hash or possible archive is not evidence of a reliable backup, authoritative version, redundancy or safe deletion. Project/cache/inbox/archive roles remain hypotheses from the producer. Unclassified folders and uncertain observations stay visible.

## Opening and privacy

Open `/ui/disk-map.html` from the existing local application, or use the link added to the bounded folder-preview page. This does not change the backend capability contract: the guided session still makes its own scope/copy decisions, and the model has no new routes here.

A selected file is read into the browser tab and transferred to a fixed local Web Worker for fatal UTF-8 decoding, JSON parsing and validation. Cancelling terminates that worker; there is no synchronous validation fallback when workers are unavailable. Invalid UTF-8, JSON, unsupported contracts, invalid references, inconsistent displayed accounting, oversized or overly complex exports are rejected before replacing the accepted view. Raw selected paths are never opened, followed, turned into URLs or interpreted as HTML.

- Maximum import: 8 MiB, 20,000 entries, 350,000 JSON values, nesting depth 32, 4,096 UTF-16 units per text value, 256 per key, four MiB of combined text, and 100,000 reference links. Free-text arrays and generic objects have a 128-item/field ceiling. These simultaneous viewer limits are deliberately narrower than the producer contract.
- Rendering is bounded separately: 2,000 newly constructed nodes and 512 KiB of text per rendering operation, with a total-map ceiling of 7,000 elements and two MiB of text. A replacement view is prepared off-DOM and committed only after it passes these limits. Rendering failure therefore preserves the prior accepted model, filters, details and focus.
- Lists show at most 20 items with exact omitted counts; evidence shows ten records and ten top-level fields per record; nested evidence summaries are bounded to 64 visits and 1,024 characters. Member/result pages contain 25 records. Every capped display points to the original export and avoids an absence claim.
- Search uses one precomputed lowercase string per unique path and tests bounded ID references against matching IDs. Empty queries do not inspect or concatenate member paths. Input/reference limits bound work without multiplying repeated long paths into group search strings.
- This validator implements every keyword used by the pinned canonical schema and fails on unknown schema vocabulary. It is not advertised as a general JSON Schema implementation.
- Additional validation reconciles unique IDs/references, parent/address structure, recursive directory bytes/file/uncertainty counts, directory gap propagation, scan completion, disjoint change categories, per-file hash states, preserved review scope and displayed accounting. Contradictory same-object aliases are rejected before object totals are checked, independent of record order.
- Counts and storage values outside JavaScript's exact integer range are rejected. Large decimal integer observations are retained as BigInt internally, so nanosecond or inode differences are not silently rounded when checking alias consistency. They never create file identity or action authority: grouping uses only the export's opaque object ID. Dates are displayed approximately; raw out-of-range timestamps remain in the export.
- Imports are not uploaded or saved to localStorage/sessionStorage/IndexedDB. The page CSP disables outgoing connections, objects and form submissions and permits only a same-origin worker. The worker imports only two fixed local source assets and has no network or filesystem API use.
- Opening does not authenticate exported observations or verify them against a drive. Hashes remain statements in the export.
- Newer imports supersede older reads. Cancel and Clear invalidate pending results. Invalid replacements preserve the previous accepted model. Native file selection is cleared immediately so the same file can be opened again.
- Clear releases this viewer's model references and rendered imported text. It is not a secure memory-erasure guarantee or deletion of the source export.

## Interaction and accessibility

Five keyboard-operable views expose different questions without hiding measurement boundaries. Search/filter results are paged at 25 records, and never change snapshot totals. Evidence details use ordinary document structure with focus placement, Back and Close; closing returns focus to the originating control when it is still present. The layout stacks on narrow screens. No treemap implies physical precision the model does not have.

The detail view caps evidence expansion at ten records/ten fields and member pages at 25. Pager focus moves to the announced page summary when the last Next button disappears. It says when additional evidence remains in the original export. Generic nested evidence is bounded and rendered as text. No imported instruction, path, label or field becomes a command, link target or application action.

## Verification and acceptance criteria

Verification history, with explicit boundaries:

- Before the cancelled command: 83 tests across six suites and 59 canonical model tests had passed. Those results did not establish the later helper/hash assertions or final source.
- The command on 2026-10-06 at approximately 18:36 UTC wrote helper/document/test changes, then returned “network approval was cancelled before a decision was returned”. Its remaining checks were unconfirmed and were not retried until explicit approval. The partial state was preserved in local commit `b79b80764754aaa62a7c2ff760e9ae2bc69b4df1`.
- After explicit approval, the exact format/sync/test chain completed on 2026-10-06 at 19:21 UTC: canonical raw-asset/browser-bundle parity, 83 tests and full frontend formatting passed at that preserved baseline.
- The current R1–R4 repair source has 100 tests across six suites passing, plus 59 unchanged canonical model tests. The parity checker and JavaScript syntax checks pass. Full frontend formatting and whitespace checks also pass before source preservation. These are local execution results, not browser or release acceptance.

Ten browser scenarios are specified in `frontend/visual/disk-map-runtime.spec.js`, serving local static assets only. There is no scanner or action API. They cover the original desktop/mobile/privacy/import flows plus complexity rejection with a live main-thread heartbeat, long labels/enlarged text, full member pagination/focus, and injected detached-render failure. Screenshots assert stable full-page height. The exact source-branch run and actual pixel inspection must be reported separately after publication; they have not been replaced by unit tests or this source audit.

### Published baseline and selector repair

The ordinary [CI run at `e0cb4e1`](https://github.com/krahd/disk_organiser/actions/runs/37523207811) passed 230 Linux backend tests, 181 Windows backend tests with 49 skipped, 100 frontend tests, both dependency audits, formatting, YAML consumer compatibility and both OpenAPI checks. Chromium passed 20 of 22 scenarios. The two failures stopped at `#scope-details summary`, which matched both the outer scope disclosure and its nested exclusions/error disclosure. Unknown-allocation/future-clock freshness and long-label/enlarged-text pixels were therefore not established by that run.

Both selectors now use `#scope-details > summary`. This restores the intended test target without changing application behaviour or weakening an assertion. After the old checkout became unavailable, the repair was reconstructed from the published source and exact CI failures; its Git blob is `d02124f643113f63cd6987f14381da77b4e3429f`, matching the previously recorded repair prefix. The prior local-only commit/tree were not available remotely, so this documentation is a current reconstruction rather than a claim to have recovered their exact bytes.

Fresh local verification on 2026-10-06 passed 100 frontend tests across six suites, full frontend formatting, canonical raw-asset/browser-bundle parity, YAML consumer compatibility and JavaScript syntax. Local Chromium could not launch because sandbox socket creation was denied; no scenario or pixel result is claimed for that attempt, and the restriction was not bypassed. The ordinary CI run on the saved final head and its downloaded artifacts must establish the remaining browser and pixel evidence separately. No test specification is deleted or skipped by this repair, and no production source, model contract or mutation/recovery guard changes.

Review criteria:

- Canonical model source/schema/fixture bytes are preserved; schema interpretation has no silent unsupported rules.
- Relationships/findings only reference listed entries/evidence; hypotheses never become confirmed project knowledge.
- Unknown allocation/physical/recoverable values never become zero or a cleanup recommendation.
- Partial, stale, cancelled and future-dated observations remain visibly qualified.
- Untrusted labels/paths remain text, with no network or filesystem authority.
- Rejection, cancellation, a newer import or clearing cannot resurrect or replace the wrong accepted model.
- Search/paging do not alter source scope or imply a selected action subset.
- The current read-only integration is useful on its own and remains separate from mutation/recovery acceptance.

## Next review round, before expansion

Obtain fresh independent source/ordinary read-only/browser review of this slice. Correct findings before adding a live scan connection or more interpretation. No real-user data, provider calls, deployment, Apple upload, billing or release belongs to this checkpoint.

Remaining product work includes clearer priority/order for questions, participant comprehension sessions, screen-reader and browser diversity, larger indexed/persistent models, guided user corrections, coherent multi-step reorganisation plans, and a separately reviewed transaction/recovery design. The evidence-first direction is coherent but not an uncontested market feature; see the first-party competitor check in `FOLDER-UNDERSTANDING-2026-10-06.md`.


## Source-review corrections

- R1: worker validation is cancellable; explicit input/reference/render budgets apply; every displayed collection is capped with an omission notice; search does not expand repeated paths; replacements are staged off-DOM and rejected atomically on rendering failure.
- R2: directory totals are recomputed from the validated parent graph. Known gaps and interruption propagate to ancestors, and scan completion must agree with errors, exclusions, root/entry states and stop reason. Contradictions are rejected, never repaired into invented confidence.
- R3: aliases sharing an opaque object ID must agree on logical size, allocation, link count and fingerprints; conflicting verified hashes also reject. Large integer lexemes are preserved, and permutation regressions ensure order-independent accounting.
- R4: the cancellation, partial-write checkpoint, explicit approval, historical passes and current local/browser gates are separated above. A source-only review was not treated as execution evidence.

The exact producer schema remains copied unchanged. Keyword coverage, canonical fixture compatibility and explicit narrower admission rules are tested; this is not a claim to accept every possible schema-valid export. No scanner, transaction, recovery or root-access contract was changed by these repairs.
