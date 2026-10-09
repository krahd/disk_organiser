# Independent manual storage planning model

This browser-compatible module describes manually named drives, scopes, projects,
intended backup targets, desired policy and restore checklists. It is independent
of the synthetic project evaluator and the Flask application. It neither reads
referenced files nor contacts providers. No runtime dependency was added.

Its state carries no physical device identity, authenticated content version,
capacity observation, verified backup coverage, restore authority or safe-to-erase
claim. A provider nickname does not connect an account. A folder is a named scope,
not an enumeration of its descendants. Archived records remain addressable and do
not silently change membership or erase failures.

## Source and examples

- `frontend/manual-planning-model.js`: standalone UMD module; browser global
  `ManualPlanningModel` or CommonJS `require`.
- `prototypes/manual_planning/manual-storage-plan.schema.json`: reviewed v1 design with the pre-publication
  immutable-history extension described below, embedded in the module for offline loading without `fetch`.
- `prototypes/manual_planning/empty-plan.json`: an empty valid document.
- `prototypes/manual_planning/manual-plan.example.json`: illustrative photo plan.
- `prototypes/manual_planning/manual-reported-result.example.json`: illustrative
  sample-readability pass and metadata failure, retained as separate statements.
- `frontend/__tests__/manual-planning-model.test.js`: state, admission, history,
  resource, hostile-representation and browser-module isolation regressions.

Examples are invented illustrations. The model accepts real user-authored labels
and intentions without requiring invented hardware facts or hashes. Unknown
optional facts remain absent. Empty lists mean no choices recorded in that list.

## Representation and resource limits

These are explicit product limits, not claims that bigger files are corrupt:

| Boundary | Policy |
| --- | --- |
| Raw import | At most 1,048,576 UTF-8 bytes, including whitespace; string-only API |
| In-memory/export document | At most 1,048,576 bytes of compact JSON, counted before serialisation |
| Nesting | At most 24 nested object/array containers; the root container counts as one |
| JSON work | At most 100,000 value/container nodes plus object keys |
| Numbers | Integer tokens only; no decimal, exponent, positive sign or negative-zero spelling; values must be JavaScript safe integers |
| Revision | Integer 1 through 9,007,199,254,740,991; an overflowing edit fails intact |
| Collections | 100 drives; 2,000 items; 200 projects; 100 targets; 500 protection plans; 500 restore plans |
| Lists/history | 2,000 selected/member/excluded items; 100 targets per plan; 100 checks per exercise; 50 reports per check |
| Text | Unicode scalar values; schema limits count Unicode code points, not UTF-16 code units; unpaired surrogates reject |
| Characters | C0 controls and DEL/C1 controls reject, except ordinary tab/CR/LF in note fields; single-line fields also reject U+2028/U+2029 |
| Calendar | Real Gregorian dates, years 0001–9999; timestamps require a timezone and seconds, with at most six fractional digits; leap seconds reject |
| Timestamp offsets | `Z` or signed hours 00–23 and minutes 00–59; bookkeeping only, not a recency proof |
| Atomic batch | Between 1 and 100 non-nested edits; the action itself has the same JSON work/byte bounds |

JSON objects are closed: unknown fields, duplicate decoded keys, unsupported
versions, duplicate IDs, wrong-type/dangling references and duplicated list
choices reject. The parser never evaluates source or merges file objects into
application prototypes. It bounds depth and nodes while parsing. A BOM is not
accepted in the text API.

The direct JavaScript APIs accept same-realm, plain JSON data only. Accessors,
custom prototypes, symbols, hidden properties, sparse arrays, functions,
`undefined`, cycles and aliased object references reject before serialisation.
Imported objects are recreated in the module's realm. JavaScript proxies are not
a supported input boundary; pass text artifacts through `strictParse` instead.

The shipped JSON Schema includes the pre-publication `reported_context` extension. Semantic references,
whole-drive constraints, Unicode/lexical representation, lifecycle rules and
resource accounting are additional model admission checks; schema validation
alone is insufficient.

## Immutable API

All admitted/new documents and derived results are deeply frozen. APIs throw
`PlanError` with `code`, `path` and a short `message`. They never partially mutate
an input document. Render these strings and all user text using text nodes.

```js
const M = ManualPlanningModel;
let plan = M.createEmptyPlan({
  title: "My storage plan",
  document_id: M.newId("plan"),
  now: new Date().toISOString(),
});
plan = M.reduce(plan, {
  type: "addRecord",
  expected_revision: plan.revision,
  now: new Date().toISOString(),
  collection: "drives",
  record: { id: M.newId("drive"), label: "Old photo drive" },
});
```

The state transformations take explicit IDs and timestamps. `newId(prefix)` is a
small optional boundary helper using browser cryptographic randomness; it fails
if unavailable, with no weak-random fallback. IDs identify document records only.
The module does not read a clock or start timers.

- `createEmptyPlan({title, document_id, now})`: revision 1 and six empty collections.
- `validatePlan(plan)`: returns `{warnings}` after full admission checks.
- `strictParse(text)`: bounded strict parsing, validation and frozen document.
- `exportPlan(plan)`: complete compact JSON for lossless reopening. It does not
  download, upload or persist anything.
- `reduce(plan, action)`: validated immutable edit. Every action requires
  `expected_revision` and `now`. A successful state change increments revision
  exactly once and updates `updated_at`; a no-op returns the original object
  without claiming a new edit. `created_at` and document ID stay unchanged.
- `derive(plan)`: `{coverage: "unknown", warnings, counts, projects}`. Counts
  describe listed records and manual report entries, never scanned files/copies.
  Project summaries expose listed membership and each protection plan's explicit
  member-minus-exclusion scope. Exclusions concern named IDs only and do not prove
  that an item is excluded inside a parent folder in any actual backup engine.

Supported actions:

| Type | Other required fields | Effect |
| --- | --- | --- |
| `setTitle` | `title` | Rename the planning document |
| `addRecord` | `collection`, `record` | Add a complete bounded record |
| `replaceRecord` | `collection`, `record` | Replace that ID's full record; omitted optional fields clear |
| `archiveRecord` | `collection`, `id`, `archived` | Explicit archive/unarchive, preserving references/history |
| `deleteRecord` | `collection`, `id` | Remove an unreferenced record; no hidden cascading delete |
| `addItemToProject` | `project_id`, `item` | Add scope and membership atomically |
| `appendReport` | `restore_plan_id`, `check_id`, `report` | Append one user statement; report omits `recorded_at`, supplied by action `now` |
| `batch` | `edits` | Apply 1–100 non-batch actions atomically, without nested revision/time fields |

Only the six documented collection names are valid. No command enables scanning,
backup, restoring, shell execution, URLs, deletion of actual files or providers.

## Restore history

Before a prepared checklist or any recorded result is admitted, its target,
nonempty selection, decided scope and user-described exercise scope must exist.
Report results are `reports_pass`, `reports_fail`, `inconclusive` or
`not_applicable`. Optional `performed_at` is a user statement. App-recorded time
is also untrusted after import and is not proof of when an exercise happened.

After the first report, the entire exercise definition is frozen, including its
selected IDs, target, snapshot text, destination, scope description, capacity/
access notes and check definitions. Only the exercise's label, general notes and
archive state can be changed. Use a new checklist for changed exercise details.
Only `appendReport` may add a report. Generic add/replace cannot manufacture,
remove, rewrite or reorder reports. Result-bearing exercises cannot be deleted;
archive them to retain history. These rules also hold within an atomic batch.

Reports with identical timestamps remain distinct insertion-ordered statements.
There is no latest-report-wins, combined success score, whole-project success or
verified state. Original failures remain visible even after later reported passes.
A repeated action fails its stale revision or duplicate report ID check.

The first report materialises an immutable, bounded `reported_context` inside the
exercise. It captures the first report ID/time, protection-plan/project IDs and
labels, target label/kind/provider/account nickname/region/independence and storage
drive description, selected item labels/kinds/locations/described versions, and
the exercise destination including its named drive label. General record notes
and archive flags are not captured. All values are manual descriptions, never
observations or authentication.

The context target/plan/item IDs and destination must match the frozen exercise;
its first report ID/time must resolve within that exercise. Historical drive and
project references must remain addressable even if current records stop referring
to them. Context records are snapshots, so their repeated IDs are references and
do not create new globally unique application records.

Current items, targets, drive labels, projects and plans remain editable. Their
later corrections cannot rewrite snapshots. `historical_context_drift` warns when
current descriptions differ; membership/target-choice warnings remain separate.
UI history must use the saved labels/locations/provider/version descriptions and
show current values separately. All later reports retain the initial context;
changing exercise details requires a new checklist.

Snapshots consume the same document byte/node limits, with at most 2,000 selected
item snapshots. If adding the first report would exceed a bound, the entire edit
fails and the existing plan remains unchanged. No snapshot/history is truncated.
Reported imports must contain valid context; drafts must omit it. Earlier
unpublished examples without context are rejected explicitly rather than having
current descriptions invented as historical facts. The checked-in reported
example was deliberately revised before publication; the independent original
39-case design harness is not a test of this stronger history contract.

## Staged import and browser responsibilities

```js
const staged = M.stageImport(text, plan);
// Present staged.preview, including private-data and history replacement warning.
// If the user deliberately confirms replacement:
plan = M.replaceImport(plan, staged, { confirm: true });
// Or, on cancellation:
M.cancelImport(staged);
```

`stageImport(text, currentPlan)` validates the entire incoming artifact before
creating a frozen preview/token. Its preview contains title, revision, record and
report counts, warnings and privacy disclosure. A one-use internal token binds it
to the exact current document bytes, not just its revision. Replacement needs the
same unchanged workspace and explicit confirmation. Invalid, cancelled, forged,
reused or stale previews cannot replace it. This is whole-document replacement,
not a merge or migration. Imported revision/history are retained as untrusted
claims; the model cannot authenticate an artifact's authorship or earlier edits.

The UI owns file selection, download requests, unsaved-edit tracking and the
confirmation dialogue. Check selected `File.size` before reading, decode its
`ArrayBuffer` with `TextDecoder("utf-8", {fatal: true, ignoreBOM: true})`, then
stage the text. Do not use `File.text()` to silently replace malformed UTF-8.
Read only the chosen planning artifact, never locations mentioned inside it.

Before export, disclose that labels, paths, nicknames, notes and report history
are plaintext and may be private. Warn against passwords, recovery keys and
secrets in notes; text validation cannot detect every secret. A browser download
request is not proof a durable file exists. Keep the workspace until the user has
saved as intended; report failures without clearing edits.

Every view must retain unknown coverage and manual provenance. Optional detail
controls reveal precision without resetting hidden fields or giving execution
power. Editing plan records is a planning decision, never a file move. This model
has no storage, network, DOM, app, provider, filesystem or telemetry primitive.

## Verification

Run the new suite through the repository's existing Jest setup:

```sh
npm test -- --runInBand frontend/__tests__/manual-planning-model.test.js
npm test -- --runInBand
npm run format:check
python scripts/validate_openapi.py
```

A separate browser-module VM test makes network/storage/import primitives throw
and exercises parsing, editing, deriving and staged replacement. This checks the
model boundary; it is not browser rendering, screen-reader, hardware, actual file
save/reopen or physical backup/restore acceptance. UI browser/keyboard/mobile QA
is a separate integration requirement. No application/back-end change is needed
to load the model in a standalone local HTML workspace.
