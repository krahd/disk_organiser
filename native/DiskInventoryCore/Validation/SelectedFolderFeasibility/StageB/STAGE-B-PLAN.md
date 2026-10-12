# Stage B: one build-only feasibility check (v3)

## Decision and current evidence

PR34 has merged at `19a2c5f6955d3732ab5cfc205a962a7f64eff1bb`, tree
`d6684ce473ed84b3debe4ab908c0da26548b9289`. All six actual-main workflows pass;
the new isolated host has still not compiled or run. The existing native log
contains the same 233 methods plus six differential/six parser cases. The
ordinary real-folder control and the Stage C gate remain closed.

The next useful result is narrow: can the isolated app and UI-test bundles
compile on the pinned SDK, be ad-hoc signed with the exact intended entitlement
sets, and yield a configuration/signature packet our strict observer admits?
This catches actual API/build/schema failures before any native folder panel or
source grant. It is not a test of sandbox access, revocation or user-drive support.

This document is a proposal for source authoring and independent review. It
neither enables a gate nor dispatches a workflow. No new host action has run.

## Fixed source identities

The first host input is the nineteen-file pack already on main, under
`native/DiskInventoryCore/Validation/SelectedFolderFeasibility/{Host,UITests,Generated,Probe.xcodeproj}`.
Its sorted `(relative path, SHA-256)` list has the controller's canonical digest
`7646f4915c190357a4d916420ebcf6a6d7e442ba9264e14f4306c39e1dbc0466`.
The exact rows are in `HOST-SOURCE-MANIFEST.json`. This identifies the unsealed
source input; generated fixture/seal bytes are separately recorded after creation.

Record two different commits, never conflate them:

- `hostSourceCommit`: the main commit above, with that exact nineteen-file pack.
- `driverCommit`: the later independently reviewed driver/workflow checkout that
  actually performs this B attempt. Its exact SHA, workflow file hash, Python
  module hashes and expected dispatch SHA must be recorded and matched.

The future driver reads only a fixed literal source-file list beneath its own
checkout, through no-follow, nonblocking, regular-file bounded reads. It checks
all expected hashes and size limits before creating a build or fixture root.
No caller-supplied folder, source list, source commit, output root or environment
variable can substitute another source. GitHub dispatch's expected SHA is a
comparison value, not filesystem or permission authority. Source changes found
necessary after a compiler failure require a separately frozen/reviewed successor
and new source identities; do not claim the failed bytes compiled.

## Small source tranche

1. `Tools/stage_b_profile.py`: fixed source pins and `BUILD_ONLY_ENABLED = False`.
2. `Tools/stage_b_driver.py`: one build-only entry, no path/mode arguments and no
   generic command dispatch. It never calls `run_c`, `test`, `test-without-building`,
   app launch, panel APIs or an executable produced by this project.
3. A narrow controller admission change: retain closed default calls and all
   existing ownership algorithms; accept one same-thread, single-use B-only
   admission from the fixed driver after its explicit profile gate. The driver
   may issue it only when the separately reviewed build profile is enabled.
   `prepare` consumes it, `inspect_b` checks its retained owner and one-attempt
   state, and `close` retires it. Default calls still refuse before I/O. C remains
   literal false and cannot accept a B admission. No imported JSON/environment
   string becomes an admission. Python object privacy is a source-level guard,
   not a claimed OS security boundary or replacement for owner approval.
4. `Tools/stage_b_receipt.py`: bounded data-only result assembly and export using
   the existing owned descriptors. No new recursive traversal algorithm.
5. Focused memory/mock tests for the driver/admission/receipt plus the existing
   151 methods, nineteen source checks and original containment corpus. Existing
   233 native source identities and all ordinary-app sources stay unchanged.
6. An activation-aware source guard, authored while disabled. It inspects both
   `.yml` and `.yaml`; the disabled state permits no active host workflow. The
   enabled state permits only the designated manual workflow's exact reviewed
   bytes/hash and trigger/steps. All existing workflow bytes remain pinned;
   no workflow_call, reusable/local-action indirection or transitive host trigger
   is admitted. Cover renamed files, added callers and hidden helper invocations
   with mutation tests. Preserve ordinary-app graph and default/C refusals; never
   skip/delete a guard to enable the build. This guard is part of the reviewed
   disabled tranche, not an extra unreviewed activation change.
7. A manual-only workflow **template outside `.github/workflows`** until both
   source review and the explicit operational approval. README/STATUS document
   exact limitations. No existing workflow is changed or made to invoke B.

The frozen candidate keeps `BUILD_ONLY_ENABLED` false and supplies no runnable
new-host workflow. After source review, the only proposed activation delta is
that one explicit build-only profile value and moving the already reviewed
manual workflow into its reviewed location. This delta must be inspected and
bound to the exact dispatch commit; it is not an environment flag, monkeypatch,
runtime source rewrite or broad reconfiguration. All pre-approval checks remain
source/memory/mock only. The default API and C refusal regressions continue to
run, rather than being deleted to enable B.

## Exact eventual workflow and commands

Proposed active path: `.github/workflows/owned-selected-folder-build.yml`.
Only `workflow_dispatch`; no push, pull_request, workflow_run, schedule or
repository_dispatch trigger. One fresh `macos-15` ARM64 job, twenty-minute ceiling,
no matrix/retry/cancellation of other jobs, `contents: read`, checkout credentials
not persisted, and no new secret, identity, signing profile or Apple account.
Use the preinstalled Xcode 16.4 / 16F6, SDK 15.5 and Swift 6.1.2. A mismatch stops;
no installation, licence acceptance, global xcode-select or system setting change.
Require actual Darwin/arm64 and macOS 15.x at least 15.3; record OS build, runner
image name/version and architecture. The mutable label is not an image-content
pin. Today's existing main run reports macos-15-arm64, macOS 15.7.9/24G830,
image 20260907.0337.1. That corroborates availability; it does not pre-accept the
future runner. Apple and GitHub's official compatibility records are linked below.

Use only the preinstalled cached CPython 3.12.10 at
`/Users/runner/hostedtoolcache/Python/3.12.10/arm64/bin/python3`, matching today's
main-run cache record; missing/version/architecture mismatch refuses, no download.
Start with `-I -S -B`, a fixed script and fixed sanitized environment. Verify the
complete fixed project-Python import closure and expected module origins before
adding that one reviewed Tools directory. No ambient PYTHONPATH, current-directory
module substitution, user/system site hook or bytecode write. The disabled entry
must refuse without output/root creation. This is controlled startup, not a claim
that Python privacy isolates arbitrary attacker-controlled code.

Pin checkout to `actions/checkout@11d5960a326750d5838078e36cf38b85af677262`
and upload to `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02`.
Those v4 refs were resolved through the official repositories today; their exact
metadata/implementation and use still require the disabled-tranche source review.
No setup/install action, dynamic action version, local action or reusable workflow.
The fixed launcher contains no dispatch input substituted into shell source.

GitHub requires this manual workflow to exist on the default branch. Its dispatch
API accepts a branch/tag ref. Consequently publication/merge of the reviewed
manual-only file is distinct from dispatch: inspect the branch head immediately
before dispatch, pass the exact expected driver SHA, and refuse inside the job
before creation/tool work if event, ref, checkout or expected SHA differs. Do
not invent a workflow-on-an-unpublished-branch shortcut. Record actual checkout
identity, not a PR merge ref labelled as source.

Exact dispatch binding is: event `workflow_dispatch`, repository
`krahd/disk_organiser`, ref `refs/heads/main`, workflow path above, exact workflow
file hash, `GITHUB_WORKFLOW_REF`, `GITHUB_WORKFLOW_SHA`, actual checked-out Git
commit and expected dispatch SHA all reconciled; run ID recorded and run attempt
must equal 1. Reject missing/malformed values, mismatches, every other trigger and
reruns before fixture/tool work. The expected SHA is passed as data, validated as
forty lowercase hex digits, never evaluated. A second dispatch needs a new owner
decision. This local guard cannot consume an approval globally across jobs; the
operator's exact single dispatch and run ID are part of acceptance. Do not embed
a self-referential Git commit/hash: the independently reviewed source manifest
binds the complete driver/import closure, while the actual checkout/workflow
identities are matched to the separately supplied expected dispatch SHA.

Immediately after owned workspace preparation, before build or signing, run the
same three bounded fixed version observations listed below and reject mismatch.
Keep the two existing post-sign observation rounds as well. This preflight does
not widen the subprocess cwd to a repository or arbitrary caller directory.

After the fixed source checks, the driver runs the existing controller sequence:

- Create only fresh `/private/tmp/disk-selection-build-*` and
  `/private/tmp/disk-selection-owned-*` capabilities. The latter has two fixed
  32-byte test files, exact private modes and no permission repair or ACL change.
- Render the sealed fixture inputs in the new owned Source directory. Existing
  user folders, Application Support and prior experiment roots are never opened.
- Run the fixed `xcodebuild build-for-testing` command already authored in
  `Experiment.inspect_b`: Debug, fixed scheme/project, owned Derived/Products/
  Intermediates paths, signing disabled at build, and exactly the three authored
  UI methods selected for compilation. No test action follows.
- Ad-hoc sign only the inner test bundle, containing UI runner, then probe app,
  using the existing bounded owner. Test/runner observed entitlements must be
  empty; the probe must have exactly App Sandbox and user-selected read-only,
  both true. Extra entitlement/profile/identity requirements stop the attempt.
- Observe actual vendor version/signature outputs, original emitted xctestrun,
  full product inventory and sealed source/fixture identity. Preserve the emitted
  configuration and derive the separate seven-expectation configuration exactly
  as reviewed. Re-observe and freeze both; never use synthetic expected output as
  proof of vendor compatibility.

### Exact tool order and whole-attempt budget

The command admission compares complete tuples, their order and expected owned
identities before the subprocess owner is called. No executable-family shortcut.
Here `R` is the retained newly created workspace, `P = R + /Products`, and `X` is
`/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild`. These values
come only from held owners; no strings supplied by dispatch can replace them.

1. Preflight, in order: `(X, -version)`;
   `(/usr/bin/xcrun, --sdk, macosx, --show-sdk-version)`;
   `(/usr/bin/xcrun, swift, --version)`. Each has the existing twenty-second/
   65,536-byte maximum; the same strict version parsers are reused.
2. One exact build tuple:
   `(X, build-for-testing, -project, R/Source/Probe.xcodeproj, -scheme,
   OwnedFolderProbe, -configuration, Debug, -destination, platform=macOS,
   -derivedDataPath, R/Derived, SYMROOT=P, OBJROOT=R/Intermediates,
   CODE_SIGNING_ALLOWED=NO, CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO,
   -only-testing:SelectionProbeUITests/SelectionProbeUITests/testSelectedReadSucceedsOnlyDuringScope,
   -only-testing:SelectionProbeUITests/SelectionProbeUITests/testGenuinePanelCancellationRetiresWithoutSelection,
   -only-testing:SelectionProbeUITests/SelectionProbeUITests/testActiveReadCancelRetiresBeforeRetry)`.
   Tuple notation here denotes individual arguments, not a shell command.
3. Three signing tuples, inner test bundle, runner, host in that order:
   `(/usr/bin/codesign, --force, --sign, -, --timestamp=none, BUNDLE)`;
   only the final host tuple inserts `--entitlements,
   R/Source/Host/host.entitlements.inert.plist` before BUNDLE. Fixed product suffixes
   are `Debug/SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest`,
   `Debug/SelectionProbeUITests-Runner.app`, and `Debug/OwnedFolderProbe.app`.
4. Two existing observation rounds. Each repeats the three version tuples, then
   visits host, runner, test bundle in that order. For each fixed bundle:
   `(/usr/bin/codesign, --verify, --strict, BUNDLE)`;
   `(/usr/bin/codesign, --display, --verbose=4, BUNDLE)`;
   `(/usr/bin/codesign, --display, --entitlements, -, --xml, BUNDLE)`.
   No other tool call is admitted, including after an error or deadline.

Keep each existing per-call maximum and 32 MiB/64-call aggregate ceilings. Add a
monotonic whole-driver clock before admission: at 720 seconds, no new build,
signing or observation call may start. Clamp a call's timeout to the smaller of
its existing limit and remaining work time minus the existing nine-second
retirement allowance; refuse if no positive time remains. Include filesystem
work between calls in that same clock. This is a tighter total bound, not a
relaxation of individual gates. Reserve the next 180 seconds exclusively for
bounded independent evidence and retirement, with no new native subprocess.
The driver must finish by 900 seconds. Workflow limits: checkout one minute,
driver step sixteen minutes (one extra minute for interruption reporting), upload
two minutes, job twenty minutes. No continue-on-error or automatic retry. Hard
runner interruption, an uninterruptible syscall or missed finalisation deadline
is incomplete; cooperative timing is not a hard OS guarantee. Mocks exhaust the
budget before/within each phase and verify finalisation still attempts all owners.

The controller's future C invocation in metadata is not permission to execute it.
A build script phase, dependency download, provisioning update, additional tool
or interactive privilege prompt is not part of the allowed command set.

## Lifecycle, failure evidence and honest retirement

This first B run is deliberately **build-only and terminal**. It exports evidence
while its owner is live, attempts close of both owned capabilities even after one
failure, records retirement, then exits. It does not wait on a network approval
message, introduce a command server or promise to preserve a live owner across
GitHub jobs. An interrupted/expired job is incomplete, never successful cleanup.
No automatic recursive deletion, ambiguous-descriptor retry or unverified-PID
kill is introduced. Surviving descendants remain an explicit failure/limitation.

This B receipt is historical build evidence, not a resumable C capability. The
later C stage must have a separately reviewed retained-process approval handoff
and a fresh approved B preparation if the earlier owner has retired. Source,
fixture and code identity must again be reviewed for that actual live attempt.
A downloaded archive or matching JSON cannot revive the old owner. This proposal
intentionally does not solve C's approval transport by relaxing that invariant.

Failures keep bounded original stdout/stderr and the existing independent
fixture/source/partial-product/capture dispositions. The exporter also attempts
bounded raw capture of emitted xctestrun candidates (at most four single leaves,
1 MiB each) even if strict parsing/signature observation failed, recording each
refusal separately. This allows examination of actual schema errors without
silently weakening the parser. Missing/ambiguous outputs are unproved; no later
successful observation erases the original build/sign failure. No success if
source/fixture or process/capability retirement cannot be established.

Failure ordering is explicit: retain the first preparation/build/inspection error;
append every independent configuration-capture, source/fixture/product/capture
check, export and close error as a secondary result. Never replace the first
failure with a later cleanup exception. A preparation failure before Experiment
exists must still expose the acquired owners' close dispositions and bounded raw
error to the driver. If no safe report owner exists, record this in stdout and
exit failure; do not create an alternate destination. Cancellation/deadline enters
that same finalisation path once and never restarts signing or observation.

## Evidence packet and acceptance

One fixed fresh owned report directory, exclusive file creation, no arbitrary
output path. Export at most 64 MiB / 96 regular files: finite raw tool logs,
actual signature/version observations, original/derived configurations when
present, generated fixture/seal data, canonical inspection and digest, source
manifest, product inventory, driver/workflow identities, outcome/failure and
retirement records, and a SHA-256/byte-count manifest. Read from retained owned
descriptors; type/size first, identity/stamp checks before/after, no-follow and
bounded attempts. Preserve raw bytes; do not interpolate logs through a shell.
Overflow or partial export is an explicit failure rather than a truncated pass.

The report owner is separate from the fixture/workspace owners. It is created
only after all admission/source checks, in one fresh fixed-prefix owned temporary
directory; its retained descriptor is not part of Experiment.close. Order is:
export available observations while source owners live; independently attempt all
remaining bounded raw/disposition checks even after an export failure; close both
fixture and workspace owners; write their final outcomes through the still-held
report descriptor; close each report file; write/close the final manifest; then
close the report directory owner exactly once. No source owner is reopened.
An ambiguous close is failure and is never retried.

The manifest covers every payload file by path/length/hash but excludes itself;
its own SHA-256/length is emitted in one bounded terminal stdout record after the
report descriptor close has actually succeeded. An outcome file may say only
`candidate_pass` pending that terminal record, zero driver exit, successful
artifact upload and independent receipt verification. A report-close failure is
reported on stdout with nonzero exit, never repaired by reopening it. There is no
circular self-hash or premature all-closed claim. Upload runs with `always()` only
against the single recorded report path, validates the fixed prefix and exact
packet first, and fails on absent files. Missing artifact, upload failure, driver
nonzero/interruption, manifest mismatch or absent terminal receipt prevents B
acceptance even if earlier payload said candidate_pass.

Upload only that data packet to this repository's Actions artifact store, with
fourteen-day retention. It contains generated test metadata and source/build
facts, no user records. Do not upload a whole runner directory, secrets, Derived
cache, `.git`, app binaries or an unrelated artifact. Original products remain
only on that ephemeral runner; no binary restoration or C resumption is claimed.
Artifact upload does not establish durability past retention or grant OS access.
No screenshots are expected because the app/UI cases are not launched.

A successful B result requires actual compiler/build success, exact signature
and toolchain observations, exact source/generated/product/configuration binding,
complete bounded evidence and retired ownership. Root and an independent reviewer
must inspect source, raw logs and the original data packet. A green workflow
alone is insufficient. Build failure still provides useful compiler evidence,
but is never called native UI, folder access or commercial-product acceptance.

## Required new regressions

- Disabled profile and absent/forged/reused/foreign-thread B admission perform no
  creation or tool call; B admission never enables C or revives a retired owner.
- Source byte/path/type/size mismatches, moved dispatch ref and changed driver
  identity refuse before creation. Keep host and driver commits distinct.
- Both workflow extensions, renamed/manual triggers, workflow_call/reusable/local
  action or helper indirection, activation hash mismatch and ordinary-app graph
  changes refuse. Disabled startup creates no bytecode or output artifact and
  ignores/refuses ambient module substitutions.
- Whole-attempt deadline exhaustion before/within each phase reserves finalisation;
  first failure survives combined preparation, partial-export and multi-close
  failures. Report ownership remains live only until its own final close.
- The observed command sequence is strictly build/sign/inspect; any test/launch
  vector refuses before subprocess invocation, including failure/cancel paths.
- Build failure and each signing/observer failure preserve raw bytes and attempt
  all independent evidence/retirement operations; no retry or partial success.
- Packet missing output, nonregular file, replacement, symlink, overflow, short
  write/read and retirement error fail closed; raw dollar/backtick/UTF-8 bytes
  roundtrip unchanged. Every read/write test is mocked until operational approval.
- All existing 151 memory methods, eleven independent counterexamples where
  retained, source/graph guards and 233 native identities are preserved. New test
  counts are reported only after actual execution; no arbitrary target count.

## Approval gates and owner question

1. Root accepts this concrete plan and the independent plan review.
2. Author the small disabled driver/profile/template tranche; freeze and obtain
   independent exact-source review plus source-only tests. Save it reversibly.
3. Then ask the owner one bounded question tied to the reviewed candidate:

“May I enable and run one build-only Disk Organiser check on a fresh GitHub macOS
runner? It will create temporary test folders, compile and ad-hoc sign the
isolated test app, and save its build/signature records in GitHub. It will not
launch a folder picker or access your computer or drives.”

4. Only after that approval and root's exact activation-diff review may the
   manual workflow be integrated and dispatched against the guarded commit.
   A denied call stops; no alternate trigger or permission route.
5. Stage C, real panels/grants, production folder admission, persistent access,
   signing identity/distribution and any security-setting change stay separate.

## Primary sources checked 12 October 2026

- Apple [Xcode system requirements](https://developer.apple.com/xcode/system-requirements)
  lists Xcode 16.4 support beginning with macOS 15.3. GitHub's current
  [macOS 15 ARM64 image inventory](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-arm64-Readme.md)
  lists Xcode 16.4/16F6, SDK 15.5 and cached Python 3.12.10. These support the
  chosen profile, not a guarantee about the later dispatched runner.
- Official [checkout v4 ref](https://api.github.com/repos/actions/checkout/git/ref/tags/v4)
  and [upload-artifact v4 ref](https://api.github.com/repos/actions/upload-artifact/git/ref/tags/v4)
  were resolved to the immutable commits above; mutable ref names are not used
  as the proposed workflow pins.
- Apple [TN2339](https://developer.apple.com/library/archive/technotes/tn2339/_index.html):
  build-for-testing compiles without running tests and generates an xctestrun;
  test-without-building is a separate action. This older document does not prove
  our current SDK/schema/runner assumptions.
- GitHub [workflow_dispatch rules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch):
  the workflow must exist on the default branch.
- GitHub [dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event):
  the ref is a branch or tag. Exact-SHA comparisons above are our fail-closed
  implementation requirement, not a claimed API compare-and-dispatch primitive.
- Apple's current TN3125 page returned a JavaScript shell in this fetch. The
  existing source references it for entitlement-display syntax; no fresh page
  extraction is claimed as actual tool-format evidence. Actual fixed-tool output
  remains a B observation gate.
