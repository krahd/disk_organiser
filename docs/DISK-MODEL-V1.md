# Disk Model v1: read-only storage understanding

## Scope and ownership

This is an independent observation and reasoning foundation. It does not import
`guided`, the operation store, model providers or any filesystem action executor.
It adds no Flask routes and does not change the default guided frontend. The
application capability flag remains `not_implemented` until a separately reviewed
integration exposes the model. A working CLI/library is not an integrated Disk Map.

The implementation order is storage understanding → inspectable evidence and
uncertainty → coherent read-only alternatives → separately reviewed transaction
support. Apply remains disabled by default; recovery deletion remains disabled.
Nothing in a model export is filesystem mutation authority.

Owned files:

- `backend/disk_model.py`: bounded observation, stable address IDs, refresh deltas,
  import validation, filtering and JSON export
- `backend/disk_model_analysis.py`: deterministic relationships, hypotheses,
  qualified aggregates, evidence and non-executable review alternatives
- `backend/disk_model_cli.py`: local CLI; results on stdout, progress on stderr
- `backend/disk_model_schema.py`: fixed contract and dependency-free full-shape
  validation, with semantic-reference validation in the inventory module
- `backend/disk_model_fixture.py`: deterministic synthetic data; no tree access
- `backend/tests/test_disk_model.py`: disposable-tree and pure-contract tests
- `docs/disk-model-v1.schema.json`: JSON Schema 2020-12 export contract
- `backend/tests/fixtures/disk-model-v1.json`: reproducible synthetic UX fixture

## Existing scanner audit

The retained `utils.find_duplicates`/`scan_index` flow is a duplicate-oriented
scanner with an import-initialised SQLite hash cache. `context_builder` can read
text, documents and optional image/OCR/embedding content and feeds the legacy
provider/planner flow. Neither is the metadata-only, explicitly bounded and
standalone Disk Model contract required here. Reusing those entry points would
also inherit their persistence/content-read behaviour. This slice therefore adds
small independent standard-library modules; it does not rewrite either scanner
or certify their safety.

## Architecture

1. The caller supplies 1–16 non-overlapping authorised directory roots and limits.
2. The scanner opens each root and each ancestor with descriptor-relative
   no-follow directory operations. It records names and `lstat`-equivalent facts.
3. Optional bounded local SHA-256 reads verify the object fingerprint before,
   after and at its directory entry. No content parser, embedding, LLM or network
   service is called. Imported hashes are never trusted or reused.
4. Pure analysis builds relationships, directory summaries, evidence and findings.
5. The caller may query entries, export JSON or pass the same versioned contract
   to a separately owned read-only viewer.

There is no arrow from the model to an action executor. The caller is responsible
for granting root access in its own UI/API. A directory argument to the standalone
CLI is the explicit root selection; it does not grant future background access.

## Run without a real disk

From the repository root, with Python 3.12:

```sh
python -m backend.disk_model_cli fixture
python -m backend.disk_model_cli query backend/tests/fixtures/disk-model-v1.json --kind file --limit 5
```

The fixture is fabricated metadata and hashes of small synthetic byte strings.
Its unreadable entry, hard-link alias, directory labels and unknown allocation
are demonstrations, not private user evidence. Regenerate it with:

```sh
python -m backend.disk_model_cli fixture > backend/tests/fixtures/disk-model-v1.json
```

For an explicitly selected disposable or user-authorised folder:

```sh
python -m backend.disk_model_cli scan /path/to/selected-folder --progress
python -m backend.disk_model_cli scan /path/to/selected-folder --hash-files --max-hash-total-bytes 1048576
python -m backend.disk_model_cli scan /path/to/selected-folder --previous prior-model.json
```

The CLI writes no database, cache or inventory file. JSON is emitted to stdout;
redirection explicitly chosen by the caller can save it elsewhere. Do not put an
output file inside the scanned tree: shell redirection creates that file before
the scanner starts. Exports contain selected absolute roots, relative filenames,
metadata and optional digests. Treat real exports as private; none are uploaded.

Exit codes: `0` for a complete metadata inventory or successful query/fixture,
`2` for a partial/cancelled inventory (valid JSON still emitted), `1` for invalid
input. Ctrl-C cooperatively cancels a scan and preserves available observations.

Library API:

```python
from backend.disk_model import ScanLimits, scan_storage, query_entries, export_json

model = scan_storage(
    ["/path/to/selected-folder"],
    limits=ScanLimits(hash_files=False, max_entries=20000),
    cancel=lambda: False,
    progress=lambda event: None,
)
page = query_entries(model, kind="file", min_bytes=1024, limit=100)
json_text = export_json(model)
```

## Observation boundary and budgets

Descriptor-relative `open`/`stat`/`scandir` plus `O_NOFOLLOW` are required. Current
traversal supports suitable POSIX hosts. Windows or another unsupported platform
returns an explicit partial inventory with an unsupported-root observation; it
does not silently substitute weaker path-based traversal. Pure fixture, analysis,
query and export work across platforms. No Windows disk-scanning support is
claimed.

Defaults: 20,000 entries, 5,000 names per directory, depth 32, 30 cooperative
seconds. Hashing is off; opt-in defaults are 16 MiB per file, 64 MiB total content
reads, 1,000 file-open/hash attempts (including failures) and a 64 KiB read buffer. Limits reject invalid values and have
hard configurable ceilings (100,000 entries, 20,000 names per directory, depth 64,
one hour, 1 GiB per hashed file, 4 GiB content reads and 10,000 hashed files).

- A directory exceeding its name budget is excluded as a whole. Each directory exposes its own
  complete/incomplete coverage and reasons, propagated to ancestors. Picking the first
  names from OS enumeration would produce a nondeterministic subset.
- Entries are sorted; a total-entry cutoff and configured-name exclusions are
  explicit. Excluded names have entries with unknown kind and `excluded` status.
- Roots cannot overlap. Directory symlinks, symlink ancestors, special files,
  recognised placeholder names/flags and child filesystem boundaries are not
  followed. Crossing filesystems is an explicit library option, not a CLI default.
- Cancellation and time checks happen during enumeration, traversal and hashing.
  They cannot interrupt a blocking kernel/network-filesystem call. Pure analysis
  is bounded by entry counts, not a hard wall-clock timeout.
- Findings and relationships have explicit caps of 400 and 2,000 respectively;
  omitted counts are reported in `analysis_coverage`.
- This is a bounded in-memory index, not a constant-memory streaming index.
  Output size grows with paths, evidence and alternatives. Very large datasets
  need the persistent/paged indexing work listed below.

No intentional writes occur in the selected roots. Filesystem access times can
still change when the operating system services metadata or content reads.

## Export contract and identities

`schema_version` is `disk-model/v1`; `read_only` must be `true`. The JSON Schema is
the field reference. Consumers must refuse unknown major contracts and must
render all path/text fields as text, never executable markup.

- `scan`: identity/time, selected roots and original root fingerprints, limits,
  content-read policy, status, coverage counts, exclusions, errors and uncertainties
- `entries`: stable root-relative address, parent, kind/status, observed file
  length, nullable allocation, inode/device-derived object ID, link count,
  nanosecond modification/change timestamps, fingerprint and hash status
- `directories`: neutral direct members, recursive logical totals, uncertain
  entry counts and optional role hypotheses
- `relationships`: hard-link aliases, full-hash matches across distinct observed
  objects, and same-parent/suffix version-like filename families
- `aggregates`: logical totals by path and observed object, qualified allocation,
  unknown allocation count, extension-category groups and partial coverage
- `evidence`: concrete observed facts with member IDs; findings and relationships
  refer back to these stable IDs
- `findings`: kind, members, evidence IDs, confidence, counter-evidence and
  uncertainties; largest observed files and older modification times are
  observations, not cleanup recommendations
- `plan_alternatives`: explicitly non-executable ways to retain the structure or
  inspect evidence and ask about grouping intent, with dependencies, reasons,
  consequences and unchanged/uncertain member lists
- `changes`: refresh deltas against a previous export, not transaction history

Confidence vocabulary has exactly three categories:

- `observed`: a stated metadata/hash observation with inspectable evidence
- `hypothesis`: a rule-derived possibility, such as a directory label or version
  token, which must be checked against user intent
- `unknown`: insufficient observations; the model abstains

`uncertain_member_ids` describes uncertainty in member observations (for example,
stale metadata), not uncertainty of a relationship. A name-family hypothesis can
have an empty uncertain-member list while its relationship remains hypothetical;
views must show the finding/relationship confidence and uncertainties separately.

There are no invented numerical certainty scores. Project markers such as
`package.json` are filename observations; they are not parsed and can be empty,
misnamed or unrelated. Multiple directory roles may coexist. Unclassified folders
stay unknown. A 180-day modification threshold never means unwanted or dormant;
modification time is not last use. `ctime_ns` is metadata-change time, not a
portable file-creation timestamp.

Entry IDs identify `(selected-root address, relative path)` and survive refreshes
at that address. They do not track renames or prove unchanged content. Object IDs
identify observed `(device, inode)` pairs for hard-link accounting; inode reuse
means they are not permanent file identities. Scan IDs include observation time,
roots, entries and coverage. Unchanged trees/policies and a fixed `started_at`
produce deterministic JSON; clocks, inode assignments and changed files normally
produce different scan IDs.

## Correctness and uncertainty

Byte-identical full-hash observations do not prove safe deletion, authority,
redundancy, backup sufficiency or equal metadata. Multiple paths to one observed
object form hard-link relationships rather than duplicate-storage claims. An
external hard link can exist outside the selected roots. Conflicting metadata
observed for one object is marked stale and excluded from confident aggregates.

Logical bytes by path include hard-link aliases. Logical bytes by observed object
count each identified object once when all object identities are available.
If any file object identity is missing, object-level totals and hard-link alias
counts are null; `object_identity_unknown_paths` exposes the affected path count.
Allocation comes only from available
`st_blocks × 512` observations; missing data stays null. Sparse files, shared
extents, copy-on-write clones, compression and filesystem accounting prevent
conversion into unique physical storage or recoverable space. `physical_bytes`
and `recoverable_bytes` are always null.

A scan is not an atomic snapshot. Fingerprint checks can detect many changes but
cannot establish hostile-concurrent-writer safety. Changed traversed ancestors
invalidate descendant confidence. Unreadable, disappeared, stale, excluded,
unsupported and unvisited states remain explicit; no empty/deleted inference is
made from absent observations. Cloud placeholders and network mounts cannot be
universally identified; metadata-first is the default, and optional content reads
can still hydrate an unrecognised placeholder. A complete metadata scan is not
complete hash coverage; inspect `hash_status_counts` before interpreting matches.

Refreshes always re-enumerate bounded metadata. They reuse stable IDs and emit
added/changed/unchanged-metadata sets for an incremental consumer. They do not
persist an index or reuse cached hashes. A path missing from a complete scan with
the same roots and policy is labelled `no_longer_observed`; a partial/different
scope scan uses `unverified_absent`. Neither label authorises an action.

## Acceptance and open backlog

Implemented and covered by disposable/pure tests:

- metadata-only default, no writable opens and no scan/index persistence
- bounded opt-in hashes, exact-match evidence and hard-link-aware accounting
- symlink ancestors/children, special files and recognised placeholder abstention
- changed content, changed ancestors, disappearing/unreadable entries and partial
  coverage; independent allocation uncertainty and import limits
- entry/directory/depth/content/time budgets, cancellation and progress
- stable IDs/JSON, incremental metadata deltas and filtering/pagination
- inspectable findings, evidence/member references, non-executable alternatives
- reproducible synthetic fixture and JSON Schema validation

Required before an integrated product milestone is called complete:

1. Review and wire the read-only model to a dedicated Disk Map UI/API without
   granting mutation authority or exposing unrestricted roots.
2. Exercise representative macOS hardware, placeholder providers, NAS/mount
   behaviour and exceptional permissions with user-authorised disposable data.
3. Implement a separately reviewed Windows metadata boundary; currently abstains.
4. Design a local persistent/paged index, memory/output budgets and resumable
   checkpoints. Current incremental support is metadata refresh/deltas only.
5. Expand filename/context families across directories with bounded comparisons,
   explicit contrary evidence and abstention. V1 is deliberately local-context.
6. Add optional local semantic analysis only with explicit content-read budgets,
   provenance and clear disclosure. It is not implemented here.
7. Extend review alternatives into coherent, editable proposed grouping plans;
   current steps inspect/retain/ask and cannot be sent to the action executor.
8. Continue the separately owned transaction/recovery acceptance programme.
   Arbitrary historic undo, physical reclaim estimates, automatic classification
   and mutation enablement are not supplied by this model.

Validation commands:

```sh
python -m pytest -q backend/tests/test_disk_model.py
python -m flake8 backend/disk_model*.py backend/tests/test_disk_model.py
python -m pytest -q backend/tests
python scripts/validate_openapi.py
```

Runtime imports validate the complete fixed contract and evidence/member/step
references; invalid executable alternatives, missing digests, malformed limits or
paths and unknown fields are rejected. This establishes shape, not truth or trust
in an imported observation. The embedded fixed-schema validator and published
schema are tested for equality and accept/reject regressions. Independent schema
validation also used the execution environment's existing JSON Schema validator;
no new production or test dependency was added. Exact-commit remote CI and an
independent review remain required before any broader integration or readiness
claim. No private research, user-disk inventory, credentials or contents are
included in the committed fixture or documentation.
