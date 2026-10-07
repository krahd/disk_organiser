# Synthetic observations to an incomplete project draft

7 October 2026 · Bounded observation-model adapter

## Existing gap and scope

The accepted Disk Model exports describe observed roots and entries. The project-review demonstration accepts two separately authored Harbour fixtures. The canonical export cannot be passed directly to the planner: its strict input contract rejects it. The [slice plan](NEXT-SLICE.md#integration-plan-after-repository-approval) explicitly calls for a bounded adapter between these models.

`prototypes/drive_administration/observation_adapter.py` now maps a canonical, explicitly synthetic `disk-model/v1` export plus explicit project-member/path decisions to `disk-administration-observation-draft/v1`. This is an incomplete draft, not a planner review. It makes the recorded current addresses, intended placement, selected scope and missing evidence explicit without inventing the facts needed by the existing planner.

No existing UI, route, scanner, provider, execution/recovery code, dependency, workflow or canonical model/schema/fixture is changed. The adapter calls the existing pure `validate_inventory` function, never `scan_storage`, the planner's `review`, a filesystem operation or a network/provider client. Importing `backend.disk_model` has no I/O. The isolated HTTP demo still exposes only its two packaged scenarios and five existing paths; it does not accept arbitrary observation imports.

## Interface and explicit decisions

Call from the repository root with Python 3:

```python
from prototypes.drive_administration.observation_adapter import (
    observation_digest, build_observation_draft,
)

# observation is an already supplied canonical synthetic dictionary.
expected = observation_digest(observation)
decision = {
    "project_id": "aurora",
    "project_label": "Aurora project",
    "member_paths": [
        {"entry_id": selected_observed_entry_id, "project_path": "design.blend"},
    ],
    "destination_root_id": selected_observed_root_id,
    "destination_folder": "Projects/Aurora",
    "acknowledged": True,
}
draft = build_observation_draft(
    observation, decision,
    expected_observation_digest=expected,
    now="2026-10-06T12:00:00Z",
    max_observation_age_hours=2,
)
```

The decision object has exactly these fields. Selected IDs must be unique, present in the export and explicitly chosen. Project-relative paths and the intended folder are bounded portable lexical strings. Selecting a directory keeps that one unsupported member visible; it never expands into all descendants. Role, project, version and duplicate hypotheses never supply membership, dependency completeness or preferred copies. Acknowledgement reviews this data decision only.

`observation_digest` identifies the exact bounded synthetic dictionary. A changed dictionary invalidates an earlier expected digest. `decision_digest` identifies the exact supplied decision, including its order. Projected member rows are sorted by entry ID. Repeated evaluation of the same input produces the same result; blocker order follows evaluation and recorded occupancy order. Digests are neither signatures nor operation authority. Outputs are independent copies and do not mutate the input.

## Admission and rejected contradictions

Only `synthetic is True` is admitted. False, omitted, numeric or textual flags are rejected; real observations are never relabelled. The flag itself does not authenticate observations, which is why every output remains incomplete and non-executable.

The adapter deliberately has narrower bounds than the producer: 2,000 entries; four MiB of canonical JSON per observation/decision; 100,000 JSON values; depth 32; 4,096 characters per text value; 256 per key; and signed 64-bit input integers. The producer's canonical root/reference/schema limits also apply. Unsupported Python objects, tuples, cycles/deep structures, non-finite numbers and non-string keys are rejected. Exact canonical JSON byte cost is counted during traversal, including escaped keys/strings, scalars and container punctuation, before allocating the whole serialisation. Individual scalar encodings are text-bounded; the final byte check remains a defence in depth. The separate evaluation timestamp is text-bounded before parsing, including otherwise valid oversized fractional-second strings. The observation-age bound must be a positive integer of at most 8,760 hours. Concatenated intended paths are also checked against the text/path bound.

The canonical validator is reused for schema and references. The adapter additionally checks the observations it consumes: unique exact root-relative addresses; consistent parent/root relationships; compatible supplied root fingerprints; recorded hash states; order-independent object-alias metadata/hash agreement; entry/status/hash coverage counts; completion/cancellation consistency; and current-versus-absent change scope. Missing root identity stays missing; conflicting supplied fingerprints reject. Partial or incomparable observations cannot report established absence.

Collision review is separately limited to one million planned comparisons, checked before the comparison loops. Issue deduplication uses a set, and at most 512 distinct issue records may be emitted. Exceeding either budget rejects the entire draft with `AdapterError` and a request to reduce selected scope. Details are never silently truncated into an apparently complete result. These simultaneous limits are intentionally narrower than entry-count admission alone.

This is not a second full Disk Map viewer validator. Unused aggregate totals and hypotheses are not promoted or used for capacity, identity, membership or protection. The adapter derives its recorded selected-path byte subtotal from selected entry records and retains the source observation/analysis-coverage qualifications.

## Draft semantics and preserved uncertainty

- Source and intended addresses are pairs of an observed root ID and a lexical relative path. An observed root is not a physical volume. Root labels, paths, fingerprint device/inode fields and opaque object IDs never create volume identity or a failure domain.
- The exact same root/address is `current_address_requires_identity`. A different intended address is `proposed_address_requires_review`. Neither is called a copy or a successful no-op. The accepted planner's stronger declared keep-current contract remains separate and unchanged.
- Every member has `volume_id: null`, `content_version: null` and unknown dependency coverage. A recorded verified hash is preserved as an export observation, never authenticated current content or a version identifier that can satisfy backup policy.
- Root/entry states, source timestamps, scan policy, errors, exclusions, uncertainties, reported changes and omitted-analysis counts remain available. An unvisited or unavailable root is not an empty online drive. No reconnect, current mount or live availability is inferred.
- Freshness is calculated against the explicit evaluation clock using recorded scan start time. It is not a per-entry observation time or live-state check. Future/stale/incomplete snapshots and unavailable members remain blocked. A complete scan is still limited by its recorded policy and is not an atomic whole-drive snapshot.
- Only exact lexical target overlaps are identified. Existing file-like ancestors/descendants, an exact occupied directory, and conflicting project paths remain visible. Case and Unicode naming semantics stay unknown; no normalised alias or safe collision-free placement is inferred.
- `known_recorded_path_logical_bytes` is the sum of supplied known sizes for selected paths, including aliases. Unknown sizes remain listed. It is not current physical storage or required copy space. Integer sums remain exact Python integers, including values outside JavaScript's safe-integer range; this contract is not yet consumed by a browser.
- Logical copy bytes, required destination bytes, observed free space and physical-allocation prediction remain null for every draft. Reclaimed bytes stay zero because no removal is proposed.
- Configured targets, independent-copy count and project-restore satisfaction remain null. Missing evidence is not converted into either a successful backup or a known zero-copy inventory.

Every result has `status: blocked_observation_draft`, `read_only: true`, `executable: false`, null execution authority, false undo/source-erasure permission, and false live backup/restore verification. Fixed blockers explain the missing volume identity, name semantics, current availability, content versions, dependencies, destination capacity and protection evidence. These cannot be cleared by a supplied hash, role hypothesis, matching address or acknowledgement.

## Verification and review boundary

Local checks on the candidate:

- 140 standard-library tests pass: all 100 accepted planner/cost/keep-current tests unchanged plus 40 adapter tests.
- The exact existing workflow command also passes from `prototypes/drive_administration`; no workflow is extended or added.
- All 22 unchanged isolated HTTP tests and 123 unchanged frontend Jest tests pass. Packaged reference output equality remains intact.
- Python compilation and full frontend formatting pass. No browser rendering changes are made or claimed by this slice.

Tests use the unchanged canonical JSON fixture and explicit in-memory multi-root variants. They cover same-content roots and aliases, reused root labels, missing identity/hash/size, partial/cancelled/unvisited/stale/future states, false absence, unsupported links/placeholders/directories, explicit decisions and target overlaps, conflicting metadata/hashes/coverage, malformed/bounded inputs, stale references, deterministic ordering and independent outputs. File, socket, scanner and existing-planner calls are forbidden in a dedicated evaluation test. Independent pre-freeze review identified the separately supplied oversized timestamp and dense collision-detail/work boundaries. Both are repaired and have regressions, including complete unique detail below the budget, rapid rejection above it, and a supported 500-member noncolliding scope.

Independent frozen-source review reran all local checks and passed 11 additional adversarial methods covering 86 synthetic cases. The oversized-clock and collision-resource findings are closed; a documentation-only correction clarifies deterministic evaluation versus blocker ordering. The initial saved source `bd8126331c1f93cdcaec3d3a8c2ebacf7bdd2b6a` passed aggregate CI `37572443984`, planner `37572443945` and isolated UI `37572443997`. Before main integration, an additional resource check found that the byte limit was enforced after whole-document serialisation. The narrow upfront-accounting repair adds three regressions: oversized repeated ASCII/non-BMP observations and decisions must reject before full serialisation, and exact escaped-JSON size thresholds remain correct. The pre-fix guard tests fail without making the large allocation. Independent repair review and replacement exact-source CI remain pending; the initial runs do not test this later repair. Local checks do not establish native-drive, platform, provider, backup/restore or execution acceptance.

## Next boundary

The documented bridge is deliberately incomplete. A later reviewed adapter must establish permissioned native volume identity and naming semantics, actual availability/capacity, supported application dependencies and a read-only authenticated protection-evidence source. A separate decision would connect an accepted draft/import workflow to the UI. Nothing here authorises scanning user drives, opening paths from an export, installing a backup engine, provider credentials, scheduling, file execution, recovery deletion or public deployment.
