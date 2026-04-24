# Next Necessary Steps

This checklist captures the immediate follow-up work after the recent API
validation and documentation updates.

## 1) Close review feedback loop (highest priority)

- Confirm all inline PR comments are resolved and reflected in tests.
- Add a short "resolved comments" note in the PR description for reviewers.
- Request re-review from previous reviewers after CI is green.

## 2) Keep API docs in sync with code

- Add a lightweight CI check that compares documented endpoints in `docs/API.md`
  against Flask routes declared in `backend/app.py`.
- Fail CI when route docs drift so future endpoint additions don't go
  undocumented.

## 3) Strengthen request validation consistency

- Normalize and validate path payloads across any remaining endpoints that
  accept file paths (not only `duplicates`/`scan/start`).
- Introduce table-driven tests for invalid payload classes
  (wrong type, missing fields, empty strings, negative numbers).

## 4) Improve error response contract

- Standardize API errors to a shape like:
  `{ "error": { "code": "...", "message": "...", "details": ... } }`.
- Document error codes in `docs/API.md` so frontend and external clients can
  handle failures predictably.

## 5) Add production safety checks

- Add tests for edge-case path inputs (whitespace, mixed absolute/relative,
  non-UTF8 boundary cases where relevant).
- Add structured logs for validation failures to help support and debugging.

## 6) Decide on audit doc lifecycle

- Either keep date-stamped audit docs (with an index) or move to a single
  living `docs/AUDIT.md` to avoid document sprawl.

## Suggested execution order

1. PR comment resolution + re-review
2. CI docs drift guard
3. Validation consistency + table-driven tests
4. Error contract standardization
5. Production safety/logging hardening
6. Audit-doc policy cleanup
