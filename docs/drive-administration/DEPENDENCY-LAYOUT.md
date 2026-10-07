# Declared dependency-layout review

7 October 2026 · Pure-data planner correctness checkpoint

## Reproduced gap

The accepted synthetic planner checked that dependency IDs were selected, but did not compare their declared source and proposed relative addresses. Changing only Harbour's media `project_path` from `Media/clip.mov` to `Elsewhere/renamed.mov` returned no blocker. Its source address and dependent edit file were unchanged. Historical fixture restore evidence still matched those content versions, although it said nothing about the proposed new layout.

## Bounded repair

For each dependency edge whose declaring member and dependency are both selected:

- If the source volume IDs differ, or source/destination name semantics are unknown, emit `project_dependency_layout_unknown` with both member IDs. Matching volume labels never establish a shared address space.
- Otherwise compare the dependency's exact, lexical parent-relative address from the declaring member, first using the declared source paths and then the proposed project paths. A changed address emits `project_dependency_layout_requires_review` with both member IDs.
- Comparison preserves spelling, including case and Unicode representation. It deliberately does not assume that an application's references follow the filesystem's case-folding rules. A common prefix added to every proposed project path does not alter a dependency's relative address.
- Missing or unobserved dependencies retain the existing membership blocker. Unselected declaring members do not invent dependency edges for the selected scope.

The helper splits and compares strings only. It does not open, resolve or normalise a real path. The prototype still cannot parse application references, determine whether a dependency is relative/absolute/content-addressed, approve a relocation policy, or prove that an application opens. A matching lexical layout means only that this additional check found no changed declared relative address. It is not application validation. An application-specific relocation workflow may eventually support some currently blocked cases, but none is inferred here.

## Evidence and authority boundaries

Historical backup/restore results keep their existing exact-version scope. A fixture restore can remain satisfied while the overall proposal is blocked for changed or unknown dependency layout. No restore record can clear either new layout blocker. No live verification, execution authority, undo, reclamation or source-erasure permission is introduced.

The same-home occupied-path blocker remains unchanged. A genuine keep-current/no-op contract is still open. The two packaged scenarios, their returned reference JSON, the accepted UI, HTTP surface and all original tests are unchanged. No real drive, provider, account, credential, download, filesystem mutation or recovery deletion is involved.

## Local verification

- Original evaluator/cost suite: 68 tests pass unchanged before and after the repair.
- Fourteen added layout tests pass; the complete pure-data suite is 82 tests.
- Running those added tests against the original planner reproduces failures, with no import/runtime errors.
- Original isolated HTTP contract: 20 tests pass, including exact packaged-reference equality, using the previously available pinned test dependencies. The default interpreter initially lacked Flask; no dependency was installed or changed.
- Original copied-frontend Jest suite: 119 tests pass. Frontend formatting and Python compilation pass.

The new tests cover renamed/reparented dependencies and declaring members, parent-relative traversal as data, source-root flattening, preserved common prefixes, cross-volume and unknown-semantics uncertainty, case/Unicode spelling, missing and unselected dependencies, cycles, historical restore separation, deterministic non-mutating output and null authority.

This partial checkout does not establish fresh aggregate backend, native-platform or browser acceptance. The existing UI files and baseline tests remain byte-identical to the accepted interaction checkpoint. Independent review and publication evidence for this repair must be recorded separately; prior green CI does not certify new source.
