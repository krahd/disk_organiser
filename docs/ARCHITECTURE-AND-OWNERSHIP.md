# Disk Organiser architecture and change ownership

Updated: 2026-10-06. Status: sustained development; safety acceptance held.

## Runtime surfaces

1. Default guided UI: `frontend/guided.html`, `guided.css`, `guided.js`. It presents scope, exact effects, approvals, uncertainty and saved history. The UI never supplies authoritative destinations or ownership data.
2. Local API: guided routes and local-origin/frame protections in `backend/app.py`. A process token prevents unintended browser POSTs; it is not a file-ownership proof or durable operation authorisation.
3. Pure journal schema: `backend/guided_schema.py`. Every persisted field and relationship is validated without filesystem I/O. Destinations are derived from a generated plan ID, a closed category mapping and validated leaf names.
4. Guided engine: `backend/guided.py`. It scans selected roots, holds a canonical preview digest in process memory, verifies sources, serialises applying with a local lock, creates exclusive copies and persists validated checkpoints. Recovery removal is disabled.
5. Runtime data: SQLite guided journal under the configured app state directory. Treat all persisted content as untrusted input. It records observations; it cannot authorise deletion or silently restore trust after a restart.
6. Legacy subsystem: analysis/model modules, `action_planner.py`, `fs_ops.py`, `op_store.py` and `frontend/index.html`/`main.js`. Preserved for compatibility; its mutation semantics are outside current guided acceptance. Trash-failure fallbacks are fail-closed, but full legacy move/undo hardening is still open.

## Current guided data flow

Choose root → no-follow scan/hash → pure schema validation → save preview plus trusted in-process digest → display exact effects → explicit approval → reload/validate journal → match fresh trusted digest → verify root and original snapshots → consume authorisation → journal apply intent → exclusive generated copies → verify output → record completion or interruption.

On restart, alteration, expiry or cache eviction: saved preview remains history and a fresh scan is required. On malformed/unsupported journal: retain record, count it as blocked, and do not open its paths. On recovery request: validate record and stop without any selected-folder operation or deletion.

## Safety boundaries

- Original sources are read-only in guided mode.
- Every operative descendant name must be a validated single component. Output/category names are derived, never accepted as arbitrary persisted path authority.
- Source/owned/directory identity sets must be disjoint in the schema. This consistency check is not proof of authentic ownership.
- A fresh process-memory snapshot is required for copying. No durable signing credential is introduced in this repair.
- There is no safe automatic removal path in this candidate. Data retention is the deliberate fallback until ownership is independently established.
- Remote model output, future planning suggestions, imported reports and saved history must never bypass this boundary.

## Ownership for concurrent work

| Slice | Owned paths | Coordination contract |
| --- | --- | --- |
| Core safety / journal / local API | `backend/guided.py`, `backend/guided_schema.py`, guided/security portions of `backend/app.py`, `backend/tests/test_guided*.py` | Own schema versions, trusted-preview authorisation and all filesystem-operation invariants. No other slice may weaken or duplicate execution authority. |
| Guided experience | `frontend/guided.*`, `frontend/__tests__/guided.test.js`, `frontend/visual/guided-runtime.spec.js`, UX-specific documentation | Consume `can_apply`, `recovery_available`, `recovery_notice`, `blocked_records`. No journal/engine changes. Never present saved metadata as permission. |
| Read-only Disk Model / organisation logic | New `backend/disk_model*.py`, `backend/tests/test_disk_model*.py`, model-specific docs | Return explanations/proposals only. Any category/schema change requires core-owner review. No filesystem writes or remote inference. |
| Reliability / fault evidence (next separate slice) | New isolated synthetic reliability tests and reports; exact paths reserved before implementation | Bounded temporary fixtures and read-only/copy-only checks. Do not reproduce unsafe real filesystem redirection. No weakening safety checks to make tests pass. |
| Integration / acceptance | `STATUS.md`, `README.md`, `docs/API.md`, `docs/openapi.json`, this map, safety backlog and implementation checkpoint | One integrator reconciles contracts, current SHA, CI and review findings. Independent review precedes acceptance. |
| Legacy mutation / commercial wrapper | Frozen except explicitly scoped fail-closed repairs | Existing rights and distribution holds remain. No launch, merge or release authority is implied. |

Separate branches/checkouts must publish only explicitly owned paths onto a freshly verified integration head. Do not overwrite another slice's changes. Exact API/schema changes require a short contract update before frontend or planning integration.

## Current API presentation contract

- Session and history expose explicit capabilities: `default_mode`, `mode`, `scan`, `copy_apply`, `recovery`, `disk_model`, `remote_inference`, `limits`, and `uncertainties`. Read-only is default; the structured Disk Model is not yet implemented. Copy testing requires explicit operator opt-in. Legacy mutation APIs are separately disabled by default.
- A described plan includes `can_apply: boolean`, `recovery_available: false`, and `recovery_notice: string` in addition to its validated saved fields.
- GET `/api/guided/plans` returns `{plans, blocked_records, recovery_notice}`. `blocked_records` counts retained records in the latest-50 window whose schema cannot be safely interpreted.
- POST scan creates a version-1 preview and its in-process authority; POST apply requires literal approval booleans and the unchanged fresh snapshot.
- POST recover returns 409 and retains all data. Its presence is compatibility, not availability of removal.
- A failed/uncertain browser request must not automatically retry an apply. Refresh history, explain uncertainty, and require a deliberate next step.

## Acceptance discipline

Green tests are evidence of tested behaviours, not a general safety certificate. The earlier green candidate `7ff5390` failed independent scrutiny of its persisted-data boundary. Keep that finding visible until a permitted independent confirmation verifies the repair and integration. Follow the backlog for durable gates rather than treating any bounded checkpoint as a commercially ready product.
