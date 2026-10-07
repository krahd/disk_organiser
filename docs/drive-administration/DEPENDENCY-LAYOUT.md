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

At this dependency-layout checkpoint, the same-home occupied-path blocker remained unchanged. The subsequent [declared keep-current contract](KEEP-CURRENT.md) addresses that separate gap. The two packaged scenarios, their returned reference JSON, the accepted UI, HTTP surface and all original tests are unchanged. No real drive, provider, account, credential, download, filesystem mutation or recovery deletion is involved.

## Local verification

- Original evaluator/cost suite: 68 tests pass unchanged before and after the repair.
- Fourteen added layout tests pass; the complete pure-data suite is 82 tests.
- Running those added tests against the original planner reproduces failures, with no import/runtime errors.
- Original isolated HTTP contract: 20 tests pass, including exact packaged-reference equality, using the previously available pinned test dependencies. The default interpreter initially lacked Flask; no dependency was installed or changed.
- Original copied-frontend Jest suite: 119 tests pass. Frontend formatting and Python compilation pass.

The new tests cover renamed/reparented dependencies and declaring members, parent-relative traversal as data, source-root flattening, preserved common prefixes, cross-volume and unknown-semantics uncertainty, case/Unicode spelling, missing and unselected dependencies, cycles, historical restore separation, deterministic non-mutating output and null authority.

The local partial checkout alone does not establish aggregate backend, native-platform or browser acceptance. The existing UI files and baseline tests remain byte-identical to the accepted interaction checkpoint. Fresh remote verification is scoped below; no real-drive, native-hardware or sale-readiness acceptance is implied.

## Independent review and exact-source CI

Independent review accepts the bounded five-file repair. It reran all 82 tests, checked the full code/tests/documentation, compared 10,000 lexical relative-path cases against a separate standard-library oracle, and confirmed non-mutating/null-authority behaviour.

Published source: [`27bce28350d7e83a443f1f0788748cbf5259a480`](https://github.com/krahd/disk_organiser/commit/27bce28350d7e83a443f1f0788748cbf5259a480), tree `6b2094c2c413c94b442dfb09dabc3648dbd6d6dd`, directly above accepted interaction/documentation head `2970140dca2b916489996dc3fc8d3d3cb90084fb`. Remote blob readback matches the frozen five-file candidate, and the commit comparison contains exactly those five files.

All three exact-source workflows completed successfully:

- [Aggregate CI 37556460692](https://github.com/krahd/disk_organiser/actions/runs/37556460692): Linux 230 backend tests; Windows 181 passed and 49 skipped; 119 Jest tests; 22 existing Chromium flows; OpenAPI coverage for 44 routes; Python/Node audits and frontend formatting.
- [Pure planner 37556461031](https://github.com/krahd/disk_organiser/actions/runs/37556461031): 82 tests on both Linux and Windows.
- [Isolated interaction 37556460867](https://github.com/krahd/disk_organiser/actions/runs/37556460867): 20 HTTP contracts on both OSes, 19 focused Jest tests and seven actual Chromium flows. The new [synthetic screenshot artifact](https://github.com/krahd/disk_organiser/actions/runs/37556460867/artifacts/11454807264) is tied to this source. Its pixels were not reinspected for this planner-only change; existing UI blobs remain unchanged.

The hosted Windows dependency install reports conflicts with preinstalled `pipx` requirements for `filelock` and `packaging`, but exits successfully and all required tests pass. No dependency change is part of this repair.

## Integration lineage and preserved holds

The accepted interaction base descends from guided core head `a5048e950d2d9dcda8fa148b56fb0c68a338b7ab` ([PR #11](https://github.com/krahd/disk_organiser/pull/11)) and guided UI head `27b3c6760832f32d2b80a5e4ae95cf1362f17a52` ([PR #12](https://github.com/krahd/disk_organiser/pull/12)). Disk Model [PR #13](https://github.com/krahd/disk_organiser/pull/13), head `96c58ba41a0bc0a61196c490e60cdc551164f7a7`, has separate commit ancestry, but all nine added model runtime/test/fixture/specification/documentation files have identical Git blobs in the accepted interaction base. Its status text was reconciled into the later report. Integrate the latest reviewed stack once rather than replaying identical model code or older status text.

This repair changes no execution/recovery flags, provider access, release or deployment workflow. Real-drive mutation and automatic recovery deletion remain held. Main integration must separately account for the repository's existing main-triggered documentation publication; source review and green tests do not authorise deployment.
