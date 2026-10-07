# One-shot scoped read-only observation

Source inspected: main `351e6a9c5a3067efd7cf7570c083859b931c9cfd`.
Status: independently accepted design; bounded local implementation/source-review candidate. Only owned temporary fixture directories have been observed.

## Customer-journey gap and bounded outcome

Roadmap Phase B requires a permissioned native folder/volume source before a person can review their own project. The next slice establishes only the in-process selection, scope and lifecycle boundary around the existing scanner. Its executable tests observe directories that the test creates and owns. It adds neither another synthetic scenario nor a user-facing real-folder capability.

No user's folder is selected or inspected. No persistent access, external-process token, route, CLI command, arbitrary import, native UI grant, background job, provider, execution or recovery connection is added. Actual user-folder integration needs its own separately reviewed selection/permission surface and supported environment.

## Existing interfaces to reuse, and those to avoid

- `backend.disk_model.ScanLimits`: existing validated entry, per-directory, depth, time, hashing and filesystem-boundary limits.
- `backend.disk_model.traversal_supported()`: requires POSIX descriptor-relative no-follow operations. Unsupported platforms abstain rather than falling back to weaker path traversal.
- `backend.disk_model._open_root(path)`: opens the selected address component by component with read-only directory/no-follow flags, rejecting symlink ancestors. It performs no directory enumeration. Reuse this existing internal helper; do not duplicate path traversal in the new controller.
- `backend.disk_model.scan_storage(roots, *, limits, previous, cancel, progress, started_at)`: metadata-only by default, cooperative interruption, partial coverage, explicit error/exclusion states, root/ancestor change checks and canonical `disk-model/v1` output. The new controller supplies one root, fixed conservative limits, `previous=None`, no clock override, no hashing and no cross-filesystem traversal.
- `backend/disk_model_cli.py` already translates SIGINT into `cancel`; its `load_export`/`--previous` paths accept saved files. Neither this CLI nor import path will be called or extended.
- There is no independent folder-permission object today. `backend.app.protect_local_api` supplies transport/origin/token checks, not a native folder grant. Its guided session/plans routes use `GuidedStore`, whose constructor creates SQLite state and whose class contains copy/recovery functionality. Do not import `backend.app`, `backend.guided`, `backend.op_store`, `backend.fs_ops`, `backend.tasks` or `backend.safety` into the new boundary, and do not reuse their tokens or stores.

## In-process API and lifecycle

New module `backend/observation_session.py`:

1. `select_root(path)` uses the exact pre-I/O admission rules below and creates a process-local `ReadOnlySelection` while holding the selected directory descriptor. Unsupported platforms produce an inactive unsupported selection with no descriptor or granted read authority. No implicit cwd, home directory, parent, extra root or remembered selection is used. No enumeration or content read happens at selection.
2. `observe_once(selection, *, cancel=None, progress=None)` accepts the live selection object only, never a string/dict/JSON/descriptor number reconstructed by a caller. It admits at most one observation attempt. Concurrent/repeated calls on an active, spent, closed or revoked selection fail closed. The scanner receives no caller-editable replacement root or arbitrary limit/hash option.
3. `selection.revoke()` is idempotent and terminal. Context-manager exit/close releases the held descriptor and invalidates unused authority. Copy, deepcopy and pickle operations reject rather than create another usable selection. Any optional diagnostic ID is only a label and can never reactivate a selection. Use one factory-created state identity, not a serialised permission record.
4. Completion, failure or cancellation spends the one-shot selection and closes resources. A fresh explicit selection is required for another attempt. No token, permission record, path history, database, config file or cache is persisted.

This is a cooperative library lifecycle boundary for trusted code inside one process, not an OS grant, an OS sandbox, an unforgeable capability or protection against hostile Python code already running with the same privileges. Copy/pickle/PID checks prevent accidental reuse; do not invent a reflection-resistant capability system. Only owned fixture tests invoke it in this slice. No untrusted request data is wired into this API.

Record the creator PID in the selection. Check it before acquiring any state lock on every operation, because a fork copy may contain an inherited locked lock. A changed-PID call rejects before locking, scanning, comparing or closing the inherited descriptor. The origin process remains responsible for its owned descriptor; this API does not attempt potentially unsafe child-process descriptor cleanup or claim fork support. Keep the descriptor private and non-inheritable across exec; this is not a claim that OS fork cannot duplicate it. A child-process inherited descriptor is never used by this API and is left to normal exec/process-exit cleanup. Test these accidental-reuse cases with mocked PID/copy operations only, without spawning or forking a process.

## Exact pre-I/O input admission

On every platform, require `type(path) is str` (not bytes, a path-like object or a str subclass), between 1 and 4,096 Unicode code points, and at most 4,096 bytes under strict UTF-8 encoding. Reject lone surrogates/encoding failure, NUL, C0 control characters U+0000–U+001F and DEL U+007F. Do not invoke a caller's `__fspath__`, expand environment variables or expand `~`.

After those pure type/encoding checks, an unsupported platform returns the inactive unsupported selection without any filesystem call or weaker path fallback. For supported POSIX execution, before any root open require exactly one leading `/`, reject `/` itself, any repeated `//`, trailing separator, backslash, or component exactly `.` or `..`, and require the input to equal `posixpath.normpath(input)` exactly. Reject aliases rather than silently normalising them; this includes `//`, `///` and double-leading-slash path forms. Names otherwise keep their supplied Unicode spelling; no NFC, casefold or durable-name inference occurs. The result is one explicitly supplied direct address, not proof of a directory's identity until the descriptor checks run.

## State lock, descriptor ownership and terminal admission

A per-selection lock protects lifecycle state, the active attempt/generation, cancellation/revocation latches, descriptor ownership and the terminal result-admission decision. Selection transitions are `granted → observing → spent`; revoke/close can invalidate a granted or observing selection, and unsupported selections never enter observing. Reserve the single attempt under this lock so repeated/concurrent calls cannot race into two scans.

The controller owns the descriptor held at selection. The scanner independently owns the descriptor it opens and passes to the root guard. Never transfer, expose or close the scanner's borrowed descriptor. While comparing the held descriptor to the scanner descriptor, retain the state lock, or an explicitly reference-counted borrow established under that lock. The implementation retains the process-checked state lock across these short `fstat` comparisons. Revoke/close cannot close and recycle a held descriptor during a comparison. After revocation of an active scan, retain ownership of that held descriptor until the observing call's finaliser closes it; revocation invalidates state immediately upon acquiring the lock but never closes a descriptor borrowed by another thread. Close each owned descriptor once and clear its ownership under the lock.

Arbitrary caller `cancel` and `progress` callbacks always run outside this lock. Admit a callback invocation under the lock while the attempt is valid, then release the lock to invoke it, and reacquire/recheck after it returns or raises. Callback re-entry into revoke/close must not deadlock. A callback admitted before revocation may start or finish afterward; do not block revocation on arbitrary callback code. No new progress/cancel callback is admitted after revocation has linearised. This is callback-admission ordering, not a promise that an already-running callback can be forcibly stopped. Callback errors fail closed and still release origin-process resources.

The observing call has one terminal admission point under the same lock used by revoke/close. Recheck all latches, scope-change evidence and the active generation there, choose the terminal outcome, spend the selection and retire its held descriptor. If revocation linearised before this admission point, no inventory is returned even if the scanner finished successfully. An inventory admitted before a later revocation cannot be un-read or erased from a caller's memory; it carries no continuing permission. This explicit ordering avoids promising a race-free instantaneous revocation at the Python return boundary.

## Root guard and scope binding

Add one optional keyword-only `root_guard: Callable[[str, int], bool] | None` to `scan_storage`. With its default `None`, all existing scanner/CLI outputs and behaviour remain unchanged.

For a guarded call, invoke the guard after the selected root is opened through the existing no-follow path walk, but before directory enumeration, descendant metadata collection or any content read. The scanner-owned descriptor is borrowed by the guard, not transferred or closed by it. Only an exact `True` admits traversal. A false/non-Boolean result or exception fails closed; all descriptors still close. No child is inspected following rejection.

The session's guard checks that the exact selected address and current process-local grant remain valid, and that the scanner-opened root matches the still-held selected directory object. It must also re-walk the selected address with the existing no-follow `_open_root` helper and compare that freshly opened address descriptor to the held object. A path-string comparison plus two old `fstat` results is insufficient: the selected path may have been replaced after scanner-open while both old descriptors still name the old object. Close the guard's temporary re-walk descriptor in all cases. Keep each held-descriptor comparison protected by the state lock/borrow rules; address re-walk I/O may occur outside the lock, followed by a lock/state recheck.

Perform another fresh no-follow selected-address re-walk and held-object comparison after scanner completion and before terminal result admission. A revoked/closed/spent selection or a changed address/object detected at either check is rejected. Existing no-follow, no-cross-filesystem and changed-root/ancestor checks remain intact. Do not silently rebind the grant to a replacement root. These are cooperative point-in-time checks; replacement after a check remains within the explicit post-check concurrent-writer limitation, not a guaranteed atomic pathname lease.

Descriptor and device/inode comparisons here are short-lived scope-enforcement checks tied to a held descriptor. They are not durable file identity, persistent volume identity, content-version proof, rename history, an independent-copy count, planner keep-current evidence or backup/restore proof. No such conversion is allowed.

## Fixed observation budget and evidence rules

For this first controller, use a single root and a deliberately small fixed `ScanLimits`: at most 2,000 entries, 500 entries in one enumerated directory, depth 8 and 5 seconds of cooperative work. Force `hash_files=False` and `cross_filesystems=False`. Do not expose optional content hashing, previous-model import, clock control or caller-increased limits.

Only directory and metadata operations are allowed. Regular-file contents are never opened/read. Symlinks and special files remain recorded unsupported/excluded entries and are never followed. Known placeholders are not hydrated; their unsupported state stays visible. Unknown cloud/network cases are still Unknown, not certified local files. Source error/exclusion/partial coverage remains explicit. Metadata reads may update filesystem access-time bookkeeping; this is not a promise that observation has no OS-level side effects.

While the selection remains valid, a bounded partial scan may return the unchanged canonical partial inventory, clearly labelled partial. A complete-within-policy scan is still non-atomic and proves neither an entire drive inventory nor successful project relocation/protection. Native scanner output remains native: do not add or flip a synthetic flag, and do not feed it into the synthetic-only observation adapter. Preserve canonical integers in Python; no general browser or export representation is added.

The controller result schema is `disk-administration-scoped-observation/v1`. A result distinguishes `observed`, `partial`, `cancelled`, `revoked`, `root_changed`, `unsupported` and `failed`. Cancelled/revoked/changed/unsupported/failed attempts return no admitted inventory, not a fabricated empty inventory or zero-byte result. Root open failure or guard rejection always yields no inventory: a demonstrated address/object replacement maps to `root_changed`; unsupported traversal maps to `unsupported`; otherwise an unavailable/unreadable root or guard/callback error maps to `failed`, unless the stronger latched outcomes below take precedence. Root/selected-address replacement detected after traversal also yields `root_changed` with no inventory. Descendant-only unreadable/disappeared/unsupported entries, known placeholders, depth/entry/directory/time budgets and other exclusions may return explicit canonical partial inventory while the selection itself remains valid. Do not conflate a root admission failure with an allowed descendant-level partial scan. A descriptive missing-evidence summary retains Unknown physical volume identity, current authenticated content versions, dependencies, copy/capacity requirements and protection/restore coverage. Read-only remains true; execution authority is null; executable/undo/erasure/live-backup/live-restore flags remain false.

## Revocation, cancellation and late results

Combine the existing cooperative cancel hook with selection revocation and an attempt generation. A caller cancellation callback must return exactly a Boolean; once `True` is observed, latch cancellation for the entire attempt, even if a later invocation would return `False`. Never clear a cancellation or revocation latch to admit a result. A callback may itself revoke/close the selection; the post-callback lock recheck observes that transition, and an already-admitted progress callback cannot rearm the attempt. Non-Boolean cancellation or callback error fails closed.

After scanner completion, perform the final selected-address check, then admit and poll the caller cancellation hook once more before terminal result admission, unless a stronger terminal invalidation already prevents callback admission. This catches cancellation triggered by the scanner's final progress callback after its last traversal checkpoint. Invoke that hook outside the state lock, latch any exact `True`, and recheck state under the lock. A caller signal arriving after the last poll is still subject to the explicitly cooperative, non-instantaneous cancellation limit.

At the terminal admission point apply deterministic priority: `revoked` > `root_changed` > `cancelled` > `unsupported` > `failed` > `partial` > `observed`. Only evidence actually detected by the admission point participates: do not infer a root change from a cancellation. A detected scope change wins over cancellation; revocation wins over both. Unsupported/root-open/guard errors cannot publish an inventory. Neither a transient true cancellation nor a revoke that has linearised before admission can be overwritten by a late successful scanner return. Provide progress only in the existing bounded counts/status shape, without paths or file contents.

An in-flight OS call cannot necessarily be interrupted. Do not promise instantaneous cancellation, hard wall-clock termination or that a revoked read already underway is undone. Once that call returns, stop at the next cooperative checkpoint, release resources and invalidate the result. Test this explicitly with controlled owned-fixture interruption, not a blocking real disk/provider call.

No hostile concurrent-writer, mount-namespace or representative native-hardware acceptance is claimed. The guaranteed pre-admission substitution cases are: a replacement already present when the guard re-walk opens the selected address, including replacement after scanner-open but before that re-walk; a symlink at the selected address or an ancestor; and a child substituted with a symlink before the existing no-follow child open. Those cases must reject before outside descendant enumeration/content access. The guard cannot universally prevent a previously admitted child directory from being renamed elsewhere while its descriptor is held. Preserve existing post-read change detection/invalidated evidence, withhold a changed selected root, and explicitly retain that post-admission concurrent-writer limitation. Do not describe a single root guard as a universal confinement primitive.

## Bounded source patch

1. New `backend/observation_session.py`: selection object, one-shot lifecycle, fixed budget, root binding, revocation/cancellation and evidence-preserving result wrapper.
2. `backend/disk_model.py`: only the optional pre-traversal root guard; retain default semantics and all existing checks.
3. New `backend/tests/test_observation_session.py`: owned temporary project/adjacent-sentinel fixtures and lifecycle/security tests.
4. `backend/tests/test_disk_model.py`: minimal guard-order/fail-closed/default-parity regressions. Existing scanner tests remain intact; no historical journal/path reproducer is run.
5. New `docs/drive-administration/READONLY-SCOPE.md`: accepted boundary, commands, evidence limits and future user-folder gate.
6. `STATUS.md`: source/test/permission state and accurate architecture notes with matching timestamps.

No frontend, demo server, API/OpenAPI route, CLI, scanner schema, synthetic adapter/planner, dependency, workflow, provider, store or executor change is intended. Existing workflows already discover backend tests; do not add CI infrastructure.

## Required tests and exit gate

- Exact type/code-point/UTF-8/control-character bounds and POSIX lexical policy before I/O, including `//` filesystem-root aliases, surrogate/encoding rejection and non-normalised paths. Unsupported platforms abstain after pure generic checks without native I/O. Reject accidental fake/deserialised/spent/revoked selections and repeated/concurrent attempts. Mock PID changes and assert rejection before inherited locks or descriptor operations; reject copy/deepcopy/pickle and check non-inheritable private descriptor ownership. Do not claim resistance to arbitrary in-process reflection.
- Root/ancestor symlinks, non-directory roots and pre-admission selected-root replacement fail closed; child symlink substitution is not followed. Specifically replace the selected path after scanner-open but before guard re-walk, and after scanner completion but before the final re-walk. Prove guard rejection precedes `scandir`/child stat/content access. Keep an adjacent owned sentinel directory unread and unenumerated in these guaranteed pre-admission cases. Separately test detected post-admission rename/change invalidation without claiming universal prevention.
- Force metadata-only/no-cross-filesystem limits and test entry/directory/depth/time bounds, unreadable/disappeared entries and known placeholders. Regular-file contents, writes, network, subprocesses and mutation/provider imports are forbidden during observation.
- Revocation before start/from progress, transient true cancellation latching, cancellation triggered by the scanner's final progress callback, callback re-entry/error/non-Boolean cancellation, deterministic precedence, and controlled in-flight call completion after revocation. Use barriers to exercise revoke-before-result-admission and result-admission-before-revoke ordering, progress-callback admission before/after revoke, descriptor borrowing versus close/reuse, and repeated/concurrent attempts. Close descriptors once on every outcome. Distinguish root admission failures from allowed descendant-level partial inventory; never turn no admitted result into an empty or fully reviewed project.
- Unsupported-platform abstention without any weak fallback. Exercise real descriptor traversal only on supported test hosts; preserve honest unsupported results elsewhere.
- Exact default scanner/CLI output parity, canonical validation and all existing Disk Model/planner/HTTP/Jest checks. Metadata-only fixture bytes remain unchanged. Do not rerun dangerous historical execution/recovery reproducers.
- Independent contract review before implementation; failing-before-fix specs, bounded source patch and independent source review; exact guarded repo save/hosted CI and final-main checks before completion. No real-user path, provider or native-product acceptance is inferred.

## Environment and permission record

The 2026-10-07 07:48 UTC environment catalogue contains no computers or saved coding environments. The current cloud workspace may create and observe its own temporary fixtures under existing writable roots. No user's computer, drives or real project directory is involved. Real-folder UI/HTTP access, persistent grants and arbitrary imports remain held until a separate scoped plan and current environment/permission checks approve them.

## Local implementation checkpoint

The accepted design freeze is SHA-256 `233783cdfc38e9f9cdd880d51f5a47cd3423ad2a2b4c0461a650f367cb57f078`. Independent design review resolved lifecycle/descriptor ownership, callback/result linearisation, cancellation latching, exact input bounds, result mapping, copy/PID misuse and the accurately limited pre-/post-check race claims. This does not itself qualify the implementation or native-user access.

The implementation adds `backend/observation_session.py` and the optional scanner guard only. The scanner's default output is byte-for-byte unchanged for the same owned fixture and fixed clock. The controller validates the returned canonical model before admission; malformed producer metadata returns no inventory instead of being normalised or silently dropped. Native descendant spellings that the canonical contract permits remain literal observation data, including a POSIX backslash in a filename. This does not make those strings valid project intent paths or executable addresses.

All observations in this task use directories and files created by the tests under owned temporary storage. No user folder, real drive, provider, store, route or executor is opened. The following commands run that bounded fixture suite and unchanged pure/UI contracts:

```sh
python -m pytest -q backend/tests/test_disk_model.py backend/tests/test_observation_session.py
python -m unittest discover -s prototypes/drive_administration -v
(cd prototypes/drive_administration && python -m unittest discover -v)
python -m unittest discover -s prototypes/drive_administration/demo_tests -v
npm test -- --runInBand
npm run format:check
```

Local verification passes 142 scanner/session cases: all 59 original scanner tests, ten added guard tests and 73 session tests. The unchanged 140 planner/adapter tests pass in both working directories; 37 HTTP and 204 Jest tests, formatting and Python compilation also pass. No frontend or browser behaviour changes, and no new pixel acceptance is claimed. Existing hosted workflows discover the backend additions without a workflow change.

The root-guard interface specification first failed on the accepted scanner. Two development regressions additionally reproduced an incorrectly admitted guard after re-entrant revocation and admission of malformed canonical producer metadata; final state rechecking and canonical validation repair them. A test assumption that canonical observation paths forbid POSIX backslashes was corrected after inspecting the actual validator: such native data is preserved, while the separately specified selected-root syntax remains strict. No test was weakened to infer scope, identity or execution authority.

The fixture suite covers exact UTF-8/path bounds, unsupported platforms, no content reads, fixed directory/depth/entry/time budgets, symlinks/placeholders/filesystem boundaries, unreadable/disappeared descendants, root replacement before guard re-walk and after scanner completion, cancellation from final progress, latched cancellation, revocation priority, callback re-entry and lock separation, already-admitted callback completion, concurrent attempts, late-result discard, admission-before-revoke, descriptor cleanup, wrong-PID rejection before inherited locks and copy/serialization rejection. Provider/network/mutation calls and executor imports are prohibited during observation.

Independent frozen source review and exact-head hosted checks remain pending. This is a cooperative in-process foundation for the roadmap's permissioned read-only customer workflow, not a connected real-folder product surface. User-folder access, native UI/HTTP permission handling, authenticated volume/content/protection evidence, execution/recovery and production/native-hardware acceptance remain held.
