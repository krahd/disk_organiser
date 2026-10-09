# Legacy read/status request contract checkpoint

Updated: 2026-10-09. Tests and documentation only; runtime behaviour is unchanged.

## Scope and result

The explicit malformed-input backlog for `GET /api/ops`,
`GET /api/recycle/list` and `GET /api/maintenance/status` is covered by
`backend/tests/test_read_status_input_fuzz.py`. All 276 request cases pass against
unchanged runtime source from main `33e74a23eaeb192c11cf0be19dbf09d38da12932`.
No source bug was reproduced and no validation repair is claimed. A separate
collection-name bound regression brings the focused suite to 277 tests.

These endpoints do not accept query parameters or request bodies. Arbitrary
query values, apparent pagination, paths, action/cancellation flags and GET
JSON do not select a folder, change the result scope, or initiate an operation.
The tests preserve that compatibility contract rather than inventing validation
for unsupported parameters. This is not new pagination or cancellation support.

## Deterministic coverage

- A fixed-seed query corpus covers duplicate and bracket-shaped parameters,
  invalid numeric values, Unicode/control text, percent encoding, traversal-like
  strings, 8,192-digit limits, 16,384-character encoded values and 1,024 repeated
  parameters. No random case is unbounded or depends on wall-clock timing.
- GET bodies cover JSON scalars/arrays/objects, malformed JSON, invalid UTF-8,
  deep incomplete arrays and a 65,547-byte object. A raising input stream proves
  the endpoint never consumes an unfinished body.
- Closing three unbuffered responses early leaves a subsequent read unchanged.
  This is WSGI response-close coverage, not a real browser/network cancellation
  claim or a guarantee about transport-level memory use.
- Unsupported write methods stop at HTTP 405. Non-local Host, mismatched Origin
  and malformed Host inputs stop at HTTP 403 before any mocked read backend.
  Valid localhost/IPv4/IPv6 hosts preserve the JSON success responses.
- Operation/recycle read failures retain the existing HTTP 500 JSON error
  contract. Missing maintenance data remains `unknown`; malformed maintenance
  bytes return an error and are preserved byte-for-byte without a rewrite.

## Isolation and limits

During request handling, operation and recycle readers return inert synthetic dictionaries and assert
zero unexpected arguments. Maintenance reads use one owned temporary file,
with an explicit read-only open guard. Mutation, scan, guided-store and provider
entry points are replaced with forbidden mocks. No test request grants path
access, enables copying/recovery, or uses a model/provider. Existing runtime
initialisation and the broader accepted suites are unchanged. Importing the app
happens before fixture guards: it initialises app-state databases and starts a
maintenance thread. A fresh owned `DISK_ORGANISER_DATA_DIR` must be set before
Python starts, so no saved user configuration or state can be loaded. The
request-read guards do not claim to suppress those import-time app-state writes.

This tranche verifies the HTTP handler boundary. It does not audit legacy
`list_backups` traversal, add a database read-only connection, bound stored
result sizes, add pagination, validate all persisted legacy schemas, establish
real-drive safety or resolve the release/commercial holds. Those would need
separate scoped fixtures and review. It does not reproduce the historical
unsafe persisted-journal path operation.

## Hosted Windows harness repair

Initial published source `5b1409ca` passed the full Linux backend/browser job and
both planner/demo workflows, but Windows could not set `PYTEST_CURRENT_TEST`
for three large-body cases: the default expanded parameter IDs exceeded the
32,767-character environment-variable limit (three setup plus three teardown
errors). This was a test-collection defect, not an API response failure.

Body and malformed-file IDs now use short length-based labels. A collection-name bound regression
fails before that repair (one failure, 276 passes on Linux) and passes after it
(277 passes). Request bytes and every original request assertion are unchanged.
The initial Linux pass does not establish Windows or repaired-source acceptance.

## Verification

Local and hosted evidence is recorded in `STATUS.md`. On POSIX, the focused
command uses a new empty temporary app-state directory:

```bash
state_dir="$(mktemp -d)"
DISK_ORGANISER_DATA_DIR="$state_dir" python -m pytest -q backend/tests/test_read_status_input_fuzz.py
```

For another shell, set the same environment variable to a newly created empty
owned temporary directory before starting Python. Ordinary CI starts from a
fresh checkout without saved application state.

Independent review accepts the repaired request-boundary coverage at source
`0ae3d6b54cd47f674f087bb41105fef6847b6e3b`. Exact-source hosted results:

- [Aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37871477246):
  Linux 590; Windows 495 passed/95 skipped; both 44-route OpenAPI checks;
  Jest 204; existing Chromium 22; audits, formatting and YAML compatibility.
- [Planner CI](https://github.com/krahd/disk_organiser/actions/runs/37871477241):
  140 tests on each OS.
- [Isolated UI CI](https://github.com/krahd/disk_organiser/actions/runs/37871477132):
  37 HTTP tests on each OS, 23 focused Jest and 25 Chromium flows.

The documentation-only closeout retains those runtime/test bytes. It does not
attribute these runs to a later commit or claim new pixel/hardware acceptance.
Documentation publication stays manual-only; no workflow, deployment,
dependency, UI, route or execution/recovery code changes.
