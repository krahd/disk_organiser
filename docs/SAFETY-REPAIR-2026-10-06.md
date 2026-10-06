# Defensive journal-boundary repair

Status: implemented for synthetic development checks; independent safety confirmation and frontend integration are pending. This is not acceptance for real user data.

## Finding and response

Independent review of `7ff5390a5401a674c77ccff743212b2297e1ca9d` identified that saved journal fields were trusted as filesystem authority. Green functional tests did not establish that boundary. The repair does not try to prove ownership from the same editable metadata.

Changes:

1. Added `backend/guided_schema.py`, a pure complete-schema validator. It checks exact fields/types/version, row ID, numeric bounds, closed categories, leaf names, derived destinations, byte totals, state/result consistency, and disjoint original/owned/directory identities. JSON duplicate keys and malformed/non-finite input fail closed.
2. Validated journal data on save, load and history before it is used. Invalid and unsupported earlier-version records stay in the database and are counted as blocked; their paths are not opened or silently repaired.
3. Bound copy application to a canonical digest of the exact preview produced in the current process. A structurally valid edit is still not authorised. Restart, alteration, expiry or eviction requires a new scan. Copy paths are derived from the generated plan ID and closed category mapping, not arbitrary persisted destinations.
4. Removed the automatic recovery-removal implementation. The retained endpoint validates its record and returns a safe stop. It does not open the selected folder, unlink, rmdir, mutate the journal or infer app ownership. All uncertain files and recovery data stay intact.
5. Made guided copy application and legacy file-mutating endpoints disabled by default. The ordinary app is read-only. Explicit operator flags exist only for isolated compatibility/copy-fixture testing; they do not enable recovery removal or establish safety acceptance.
6. Exposed capability and uncertainty data to the UI. It distinguishes the narrow current scan, disabled mutation/recovery, absent structured Disk Model, no remote inference, supported bounds and unresolved cases.

## Non-destructive verification

- Full local pinned backend suite: 171 tests passed.
- Guided engine/schema/Python test lint: passed.
- OpenAPI coverage: 44 routes passed; diff whitespace checks passed.
- Pure data-only corruption tests exercise malformed top-level/action fields, key/version/row-ID mismatches, duplicate sources, false ownership relationships and inconsistent completed results. Invalid path strings are given only to the pure validator; no path-redirection operation is performed.
- Benign integration checks alter a scalar in temporary app-state JSON or remove an in-memory preview digest. Selected-folder I/O is mocked and asserted not called.
- Recovery checks assert no selected-folder open, unlink, rmdir or journal change. Originals, copied fixtures, partial output and malformed records remain intact.
- Existing positive copy and legacy compatibility tests use ordinary isolated temporary fixtures and explicit opt-in. This does not imply those operations are enabled by default.

The old frontend/browser suite assumes recovery removal and must be replaced by the separately owned safety-state UX integration before the complete pipeline can be accepted. No tests are removed or bypassed to disguise that contract change. No previously blocked review operation is reproduced.

## Residual gate

A permitted independent reviewer must confirm the repaired persisted-data/authorisation boundary using source inspection and benign in-scope checks. Automatic recovery removal stays disabled until a separately designed ownership and crash-recovery mechanism is independently established. Read-only Disk Model work can continue in its separate pure modules without widening mutation authority.

The architecture/ownership map and durable acceptance backlog define subsequent iterations. MIT rights, commercial eligibility holds and the private wrapper remain unchanged. No merge, release, deployment or Apple upload is part of this repair.
