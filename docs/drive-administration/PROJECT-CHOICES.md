# Save and reopen Aurora project choices

9 October 2026 · Bounded synthetic continuity slice

## Customer outcome

The Aurora form can save a person's membership, intended paths and destination,
then reopen them for further editing. This closes the lost-work loop without
turning a saved report into a plan, observed fact or permission to operate.

Open the isolated demo at `/observation-draft`. **Save project choices** works
before Review, provided the current choices are structurally valid. **Open
project choices** reads a deliberately selected local file, then shows current
and saved destination cards, membership changes and edited-path counts. Exact
member paths are available in an optional disclosure. **Replace choices** makes
the selected changes; **Cancel** preserves current choices and review. After
replacement, the prior review and its report export are cleared. The person
must explicitly press **Review observation draft** again.

The permanent synthetic banner remains. All eight choices still come from the
same packaged Aurora example. This does not yet let a person administer their
own project inventory. No Apply, Move, Undo or provider control is introduced.

## Intent and evidence are separate

The new `disk-administration-project-intent/v1` document has exactly four fields:

- `schema_version`: the version above.
- `document_kind`: `user_authored_project_intent`.
- `source`: `kind: packaged_synthetic_observations`, `scenario_id:
  aurora-observation`, positive safe-integer `source_revision`, and the exact
  `observation_digest` and `reference_decision_digest` strings from the loaded
  source. Digests are lowercase 64-character hexadecimal values.
- `intent`: `members`, `destination_root_id` and `destination_folder`.

Each of the eight known choice IDs occurs exactly once in `members`, with only
`entry_id`, boolean `included`, and `project_path`. At least one is included.
Unchecked paths are retained too, including empty or lexically unfinished text,
so unchecking a row does not discard the person's editing work. Output orders
rows by the reference choices. Only included rows project to the existing
`member_paths` review request.

The file contains no observations, file hashes, fingerprints, sizes, identity,
backup/restore evidence, clock, reviewed result, acknowledgement, credential,
process token, execution flag or operation. It is not signed or authenticated.
A matching source reference establishes consistency with this example only.
It cannot establish current drive, file, backup or permission state. The source
is never reconstructed from an imported path or a file's claimed evidence.

The existing [display-report format](SAVE-REVIEW.md) is unchanged and remains
non-replayable. Opening a display report, Disk Model export or manual inventory
through this control fails. Importing one format never silently converts it to
another. The synthetic observation adapter and existing review APIs are
unchanged.

## Admission limits

- Maximum file size: 8,192 bytes. Check the selected File size before reading and
  the actual ArrayBuffer size afterwards. Decode strict UTF-8 with no replacement
  characters; a BOM is not accepted as JSON whitespace.
- A bounded strict parser rejects duplicate decoded object keys, malformed JSON,
  noncanonical numeric tokens, unsafe integers and trailing data. It admits at
  most eight nesting levels and 256 parsed value/key nodes; individual keys are
  at most 64 UTF-16 code units. All records then pass exact-key allowlists.
- Text rejects C0 controls, DEL and lone surrogates. Editable paths are at most
  240 UTF-16 code units, matching the existing form's `maxlength`. This is
  intentionally no wider than the server's 240-code-point bound; for example,
  120 astral characters fit. No trimming, case folding or Unicode normalisation
  occurs. Text-input readback is checked before and after replacement.
- Included paths and the destination folder must be nonempty relative lexical
  paths: no leading slash, backslash, colon, empty segment, `.` or `..` segment.
  Unchecked text is bounded and preserved but is not a review path.
- Member IDs and the destination root must exist in the current packaged
  reference. Every source-reference field must match exactly. A stale file is
  rejected with current work retained; there is no automatic rebinding.
- The actual UTF-8 JSON projection to the existing review API must fit its
  unchanged 4,096-byte request limit. Saving cannot produce a choices file that
  is structurally too large for that review API.

These limits concern editable text, not filesystem lookup. No input is opened
as a filesystem address, used as a URL or interpreted as HTML.

## File, review and page lifecycle

Opening uses a separate import epoch from the review generation. Merely opening,
parsing, rejecting or cancelling a file leaves current controls, accepted review
DOM and report-download availability untouched. A staged replacement binds to
the source object and every control, including unchecked paths. Edits, a newer
open, reload, dismissal or page lifecycle invalidates pending import work. A
silent control change is checked again before replacement. Late file reads and
late review responses cannot replace newer work.

Only successful explicit replacement clears the previous review/report export.
Pending reviews are cancelled and their late responses remain ineligible.
Opening does not automatically send a review request. All file bytes stay in
the browser. There is no upload, localStorage, IndexedDB, autosave or background
access. The only new server path is the fixed static asset
`/project-intent-model.js`; the existing exact-host/origin/method/query/header
guards apply. Six fixed assets and four existing API routes make ten isolated
demo routes. The default application's 44-route contract is unchanged.

Save snapshots the current choices, creates a JSON Blob and asks the browser to
download `disk-organiser-aurora-project-choices.json`. It checks source, controls
and generation again before activation and before updating status. Object URLs
are revoked after activation or during page cleanup. Failures are disclosed;
download-requested status never claims the final save-dialog outcome. Repeated
deliberate saves and same-file reopen are supported.

## Verification

Source-only local checks are recorded in `STATUS.md`. The original admission
test failed before implementation. Independent review additionally reproduced
fractional numeric tokens rounding to the accepted revision and two re-entrant
download lifecycle faults. Canonical integer-token admission and generation-
bound activation/status repair those cases; permanent regressions cover them.

Acceptance includes strict type/size/path/source/parser boundaries, lossless
unchecked edits, stale source failure, report-format rejection, cancellation,
read failure, delayed A/B reads, ordinary and silent edits, pending reviews,
reload/dismissal/page exit/back-forward restoration, exact request projection,
text-only rendering, same-file reuse and object-URL cleanup.

Browser specifications exercise actual downloaded bytes, reload/open/replace/
explicit-review flow, keyboard focus, optional disclosures and desktop, 320/390
pixel and 200% CSS-zoom layouts. Local Chromium launch is blocked by sandbox process-socket restrictions, so no
local browser or pixel pass is claimed. Exact-source hosted evidence and independent
rendered review remain required before acceptance. Native browser zoom,
assistive technology, representative hardware and real data are not qualified
by these tests.

## Next useful boundary: the person's own inventory

The follow-on should let a person describe or import a bounded project inventory,
make editable decisions and reopen them. It should not add another fixed demo.
Keep two explicit source kinds in a new contract:

1. **Imported recorded inventory:** a validated canonical export is an untrusted
   recorded assertion, with source date, scope, exclusions, partial/offline state
   and original evidence retained. It supplies no current identity or native
   access. Reuse the existing Disk Model import validation; do not flip its
   synthetic flag or feed it to the synthetic-only adapter.
2. **User-declared inventory:** user-entered location labels and relative item
   addresses, optional declared sizes and explicit membership. Label these as
   declarations, never scanner observations. No generated fingerprint, invented
   hash, availability, dependency completeness or protection evidence.

Saved intent must remain separate from either inventory. Bind decisions to the
exact source and show a reconciliation screen when it changes: present old/new
rows, preserve unmatched intent and require explicit remapping. Never infer
deletion from an offline or partial source. Initially support one bounded
snapshot/project, no automatic root merging, no provider accounts and no native
drive writes. Acceptance requires useful task completion on an owned noncritical
inventory, understandable visual before/after layout, preserved unknowns,
save/reopen/reconcile and explicit fresh review. This contract is proposed, not
implemented or authorised live-data access.
