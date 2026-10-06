# Verification and current limits

6 October 2026

## Local checks completed

- `python -m unittest discover -v` from `prototypes/drive_administration/`: **68 tests passed** (61 planning tests, 7 cost tests).
- `python demo.py`: emitted valid JSON for the blocked and reviewable synthetic examples.
- Both generated input fixtures round-trip through the strict input decoder and evaluator in the tests.
- Planner AST/import inspection: only standard-library pure-data modules; no disk/network/process/executor imports and no `open`, `eval`, `exec`, `compile` or dynamic-import call.

These checks apply to the local isolated prototype, not the pre-existing Disk Organiser app or any live filesystem/provider.

## Deliberate boundaries

No scan, live backup, restore, provider account, credential, purchase, upload, filesystem mutation or original executor test was performed. Existing mutation and automatic recovery-removal safety limits are not relaxed. No executable action or inverse/undo mechanism was implemented.

No production API or frontend was changed. Browser/visual usability, native-platform filesystem semantics, concurrency, memory/performance limits at maximum input size, app dependency discovery, provider authentication, real backup evidence and end-to-end restore remain unverified. Independent v1 review found four planning-contract blockers. Review of v2 exposed four remaining variations: reversed source ancestry, cross-snapshot unresolved failures, historical ambiguity, and canonical caseless U+0345 handling. The v3 candidate repairs these through symmetric source overlap, history-wide invalidation and scope/method-aware resolution, and canonical decomposition before case folding. Independent v3 re-review accepts the bounded synthetic planning contract: all former repros are blocked, 68 tests pass, and additional review exercises passed 2,048 restore-history permutations, 72 organisation cases and 50,662 canonical-key assertions. This acceptance does not cover real filesystem semantics, live evidence, execution or restoration.

## Repository observations

Inspected the existing repository instructions, README, status, legacy planner/execution helper/model client/operation store, the accepted candidate's guided safety documentation and observation model, and the Vertinant launch specification. The observation model is usable supporting infrastructure, with documented scope/identity limitations. It is not the product definition.

The existing legacy operation store initialises persistent state on import; the new pure planner does not import it. The guided safety document retains its mutation/recovery acceptance hold. No source file from those modules was executed in this task.

## Publication boundary

All files in this package were initially prepared separately from the existing partial repository checkout. No existing README, STATUS, UX acceptance checkpoint or cross-repository ledger was changed during preparation.

This source-only checkpoint is based on `241c558da5cf7ce530f3a2502caa9e6d1be00f6d` and preserves its accepted runtime and UX checkpoint. STATUS records the broader product direction and isolated prototype honestly. A separate Linux/Windows standard-library workflow checks the new source; exact remote results must be read on the commit rather than inferred from the local counts. Main merge, release, deployment and real-drive acceptance remain outside this checkpoint.

Independent review used frozen v3 archive SHA-256 `76ab1c550d2b3c966d40e2ccdfb554cb34625b8f30851d10a1992acc68708021`. Publication relocates the same Python and JSON fixture bytes; documentation links and acceptance wording are adjusted for their repository locations.
