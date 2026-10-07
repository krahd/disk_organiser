# Organise and protect a project

Implementation slice and integration contract · 6 October 2026

## Purpose and boundary

Give a person a useful, editable administration decision: which files belong to a project, where that project should live, what proposed organisation would change, and what backup or restore evidence is missing. The larger product will administer storage and carry out qualified operations. This first slice is a **planning-stage capability**.

The local implementation accepts fabricated structured records and returns a non-executable review. It does not scan a drive, open a path, hydrate a placeholder, call a provider, install a backup engine, execute a plan, store credentials or modify existing Disk Organiser code. It does not implement a map.

## The customer journey to implement in the app

1. **Choose the job:** “Organise and protect this project.” Show the relevant connected/offline volumes and their observation dates.
2. **Review the project:** distinguish suggested membership from confirmed membership. Let the user include a missed asset, exclude an unrelated export, correct the project label and preserve a project-relative layout. Show the evidence behind suggestions and the effect of every correction.
3. **Choose its home:** select a volume and destination folder; compare keeping the present placement with the proposed whole-project layout. Current and intended addresses stay visible.
4. **Resolve problems:** show conflicts, absent dependencies, incomplete observation, unsupported links/packages, insufficient capacity and offline volumes. Unknowns are actionable requests for evidence, never hidden zeroes.
5. **Review protection:** list configured targets, known snapshot/content evidence and restore exercises separately. For every current project member, show missing, stale, mismatched, same-device or unknown evidence. Keep sample restores visibly limited to their sample.
6. **Review cost and effects:** copied logical bytes, unknown sizes, conservative capacity reserve, retained originals, provider assumptions and verification/restore costs. No reclaimable-space figure is fabricated.
7. **Save or revise the review:** produce a revision-bound record. A correction invalidates the previous review. At this stage the primary action is “Save review”, with no Apply, Move, Delete, Undo or Restore execution controls.

The first app integration needs an ordinary form and exact-change list rather than a treemap. No UI is implemented or visually tested by the local pure-data prototype.

## What is implemented locally

| File | Responsibility |
| --- | --- |
| `prototypes/drive_administration/planning_preview.py` | Strict synthetic input validation; membership/destination revisions; exact proposals; collision/dependency/capacity checks; evidence-scoped protection and restore review |
| `prototypes/drive_administration/fixtures.py` | Deterministic fabricated volumes, project members, targets, backup records and restore records |
| `prototypes/drive_administration/project-review-example.json` | Serialised reviewable fixture |
| `prototypes/drive_administration/project-review-blocked.json` | Serialised fixture with unknown dependencies, placeholder, stale version and sample-only restore |
| `prototypes/drive_administration/demo.py` | Emits the two review outputs to stdout |
| `prototypes/drive_administration/cost_preview.py` | Limited provider cost illustrations with dated rates, explicit units/assumptions, omitted costs and policy warnings |
| `prototypes/drive_administration/test_planning_preview.py` | Contract and behaviour tests |
| `prototypes/drive_administration/test_cost_preview.py` | Cost arithmetic and qualification tests |

Run from `prototypes/drive_administration/` with Python 3:

```sh
python -m unittest discover -v
python demo.py
```

The functions use only the standard library. The planner imports `copy`, `hashlib`, `json`, `unicodedata` and `datetime`; it has no disk/network/command/executor import or I/O function call. The demonstration's stdout can be redirected into the task workspace for inspection. Its data does not name real accounts or user files.

## Input contract

Version: `disk-administration-synthetic/v1`. `synthetic` must be exactly `true`. Unknown fields, versions, record IDs, JSON duplicate keys, non-finite values, invalid timestamps, duplicate member references and invalid relative addresses are rejected. Individual lists are limited to 2,000 records and the encoded document to 4 MiB. These are validation bounds, not tested production performance claims.

### Observation records

- `now`, `revision`: explicit timezone-aware evaluation time and revision number; no implicit system-clock dependence.
- `volumes`: IDs/labels, online state, observation date, coverage, name semantics, nullable free bytes and declared failure-domain label.
- `entries`: ID, volume reference, relative source address, project-relative destination suffix, kind, nullable logical bytes and version identity, observation date, explicit dependencies, declared dependency coverage and link count.
- `project`: ID/label and candidate members. Candidate membership is a suggestion, distinct from the decision.
- `decision`: selected members, intended volume/folder and reviewed acknowledgement. The acknowledgement means this synthetic grouping/destination was reviewed, never authority to operate on a filesystem.

### Protection records

- `targets`: local/object-storage/managed-backup/sync kind, display label, region and declared failure domain. There are no account IDs, passwords, tokens or live endpoints.
- `policy`: desired targets, evidence/restore/inventory age windows, required distinct independent copy domains, whether a project restore exercise is required, the required bytes or bytes-and-application check, and a capacity reserve.
- `backups`: record identity, target and snapshot IDs, observation date, evidence level, completeness and member-version manifest. Evidence levels are configuration, provider report, manifest verified and content verified.
- `restores`: an exact backup-record reference, completion date, sample/project scope, passed/failed/unknown outcome, bytes/bytes-and-application method and member-version manifest.

For this prototype, all evidence is fictional. In a real product, imported reports cannot certify themselves. A future adapter must establish source/provenance, authentication/integrity, snapshot creation time, last-attempt/last-success, exclusions, independently verified content and the exact method used. None of these synthetic assertions should be promoted to live proof simply by changing the `synthetic` flag.

## Review result contract

Version: `disk-administration-review/v1`.

Every successful result fixes these properties:

```json
{
  "synthetic": true,
  "executable": false,
  "execution_authority": null,
  "undo_available": false,
  "source_safe_to_erase": false
}
```

The result includes:

- `input_digest` and `revision` for change detection; the digest is not a signature or operation permission.
- `member_ids` and `membership_corrections` showing additions/removals relative to candidates.
- `proposed_changes` with source volume/address/version and intended volume/address, preserving each member's declared project-relative structure and retaining originals.
- `blockers` with reason codes and member references. `reviewable_proposal_only` means the synthetic rules found no blocker; it never means safe to execute.
- `capacity` showing known logical copy bytes, unknown-size members, reserve, nullable required total and observed free space. Reclaimed bytes remain zero and unique physical allocation is unknown.
- `protection` showing configured targets, per-member evidence levels/currentness, independent declared-domain count, scoped restore results and explicitly false live-verification flags.

`revise(...)` requires the expected digest of the current document and explicit new membership/destination/acknowledgement. It returns a deep-copied revised document. Stale edits fail rather than overwriting a newer decision.

## Decision rules

### Organisation

The planner blocks an unqualified review for unavailable/stale/partially observed sources or destination, unknown source or destination name semantics, placeholders, symlinks, application bundles, unknown item kinds, hard links, absent version identity and incomplete dependency knowledge. Source-address overlap is checked symmetrically: a selected file below any declared file/link/package, or a selected file above another declared entry, is blocked even when the other entry is not selected. These items remain visible in the review.

Case/Unicode-normalised names, duplicate source addresses, proposed target collisions and ancestor/file collisions are checked without touching a path. Case-insensitive keys use canonical decomposition before folding and then the declared normalisation form, following the canonical caseless matching rule in [Unicode D145](https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-3/). Regressions include U+0345 and both NFC/NFD. Native filesystem comparison behaviour still needs its own adapter and acceptance. Common nonportable destination names receive a blocker. This is not exhaustive native filesystem name validation. Unknown sizes/capacity stay unknown; insufficient observed capacity is a blocker. All these checks must be repeated by a future native executor against actual state.

### Protection

Configured targets and provider success do not count as content verification. A counted fixture copy must have complete current-version content evidence, acceptable freshness, a non-sync target and a known declared failure domain distinct from that member's source. Multiple snapshots on one domain count once. Unknown failure domains do not establish redundancy. Domain labels do not establish off-site or ransomware isolation.

Later evidence for the same target/snapshot supersedes older success. Tied latest timestamps are ambiguous. A fresh project-scoped passed restore covering every selected current member may satisfy the fixture's project-restore policy; sample scope never does. Failure history is grouped by target and snapshot, even when reports have different evidence-record IDs. Every failed/unknown outcome, future event and ambiguous timestamp group is retained as an invalidation boundary throughout history. Only a later unambiguous, full current-project success with at least that event's check method resolves its alert. Sample success cannot reset a wider failure or historical ambiguity. A success on another snapshot cannot erase the unresolved snapshot's alert. A bytes-only pass can satisfy a bytes-only policy, but cannot satisfy a bytes-and-application policy. Tied and future events require attention even after a later insufficient sample pass. A latest failed attempt on another snapshot stays visible even when an older valid restore remains. Method, exact snapshot, timestamps and invalidation state stay visible. A past restore test does not prove that the proposed new layout will open in its application.

### Costs

The separate cost module estimates selected storage/egress line items only and explicitly assumes a 30-day cycle. Unknown timed-deleted storage keeps a Wasabi subtotal unknown. Egress beyond the Wasabi guideline creates a suitability warning, not a charge silently set to zero. Tax, support, requests, fees, future growth and contractual variation prevent any output from becoming a complete quote. No pricing computation authorises a purchase or provider policy change.

## Acceptance fixtures and tests

Current local suite: **68 tests pass**. It covers:

- Exact project-relative proposals and retained originals
- User membership/destination correction, visible exclusions and stale-edit rejection
- Missing/unknown dependencies, offline volumes, partial and stale/future observations
- Placeholder/symlink/bundle handling, hard links and unknown link identity
- Case, Unicode, occupied-name, ancestor and duplicate-source collisions
- Unknown/insufficient capacity and no invented reclaimed bytes
- Configuration/report/manifest versus content evidence; version mismatch; stale/incomplete evidence
- Same-device/unknown-domain copies, repeated snapshots, sync targets and ambiguous latest evidence
- Sample, incomplete, failed, old and superseded restore evidence
- Input version/type/shape/path/JSON validation and deterministic non-mutating evaluation
- B2 allowance/egress arithmetic; Wasabi minimum/deleted-storage arithmetic; explicit unit assumptions; no full-cost claim

Independent v1 review found four false-reviewability cases: unknown source name semantics, source ancestry through unselected file-like entries, casefold-induced Unicode equivalence, and earlier project restore success revived after failure by a sample pass. Review of v2 additionally found reversed source ancestry, an unresolved failure on another snapshot hidden by a sample, historical ambiguity hidden by a sample, and the U+0345 canonical-caseless edge case. The v3 candidate uses symmetric overlap and history-wide invalidation reduction, with invariant-style regressions; independent v3 re-review accepts this bounded pure-data contract. It does not certify native filesystem handling, real evidence or execution.

These tests exercise the new pure contract only. They do not test the original guided executor or the previously blocked journal/path reproducer, and they do not establish mutation, backup, restore, privacy, platform or production acceptance.

## Integration plan after repository approval

1. Land this as an isolated source-only prototype with no app route/default-navigation change. Preserve both mutation flags OFF and automatic recovery removal unavailable.
2. Add its standard-library tests to CI for Linux and Windows. Do not confuse cross-platform pure-data success with scanning/execution support.
3. Implement the review-only app form with synthetic inputs; test text-only rendering, keyboard flow, user correction, stale edit, no-op/keep-current choice and interruption. Inspect rendered browser results before claiming UI acceptance.
4. Add a bounded adapter from the existing observation model. Preserve incomplete coverage and its identity limits; do not flatten hypotheses into confirmed project membership. The [synthetic observation-draft adapter](OBSERVATION-DRAFT-ADAPTER.md) is the bounded first bridge: it retains explicit member/path intent and missing-evidence blockers without manufacturing volumes or a successful planner review. Native observations and UI import remain separately gated.
5. Independently design the live evidence trust boundary and permissioned native project/volume access. No mutation or provider control follows merely from review UI completion.

Proposed later API naming, not implemented: a review endpoint and a revision endpoint under `/api/administration/`. Their initial dependencies must be pure planner and validator modules; never import the legacy operation store to obtain a preview, because that module initialises persistent state on import.

## Explicit prototype gaps

The later [declared keep-current contract](KEEP-CURRENT.md) adds exact current-location no-ops and explicitly unresolved current locations. Only proven synthetic same-volume, same-address identities avoid their own occupied-path check and copy-capacity charge; all other collisions and uncertainty remain. This extends the original copy-only evaluator and UI without adding execution authority. Project-relative paths and dependency completeness are supplied fixture declarations, not discovered identity or parsed application references. Restore records do not authenticate an actual restored layout, metadata fidelity or application state. All of these limits must remain visible when this contract becomes a real-data adapter.

## Work still required before execution

Actual volume identity, project/app dependency adapters, app packages, filesystem-native collision checks, ACL/xattr/resource-fork fidelity, locking/concurrent changes, full cost/retention modelling, authenticated evidence, background scheduling, consent and credentials, trusted execution receipts, crash recovery and separately qualified undo. No plan JSON inverse is an acceptable substitute for those mechanisms.
