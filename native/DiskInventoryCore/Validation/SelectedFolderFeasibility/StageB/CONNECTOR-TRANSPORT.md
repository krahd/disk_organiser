# One build-only attempt through the GitHub connector

## Terminal state: attempt consumed, workflow deactivated

The [single create-event attempt 38315666563](https://github.com/krahd/disk_organiser/actions/runs/38315666563)
ran from exact main `ba901b91d4f0d00cb0fbe8b954b16dcb50154e76`. It refused at
the pinned interpreter identity check before operational owners, build or signing.
There is no report packet; the artifact step failed for its missing input path.
The profile is now False and the active workflow is removed. Both inactive anchors
and `validation/owned-build-once-20261012` remain unchanged. The procedure below is
retained as the historical reviewed contract, not an instruction to trigger again.
STATUS.md records the original log identity and remaining compatibility gap.


This is the reviewed-transport successor to the historical manual workflow. It
does not expand the experiment. The currently exposed connector supports branch
creation and repository integration but has no workflow-dispatch operation.
Its generic fetch is GET-only; rerunning an existing job cannot create this first
attempt. The repository remains accessible. No new credential is needed.

## Source and event identity

The active workflow filters GitHub's real `create` event for
`krahd/disk_organiser`, `ref_type` equal to `branch`, and the reserved ref
`validation/owned-build-once-20261012`. GitHub's scheduler string equality ignores
case: a case-variant ref can allocate the macOS runner and run checkout/startup.
It cannot execute the build because the bootstrap and driver enforce the exact
case-sensitive event/repository/created-ref/full-ref identity before operational
owners or build tools. The job-level filter is not an exact-case security guard.
Ordinary nonmatching source branch names and main merges do not run this job.
Event fields are bounded environment values, never interpolated shell source.

The checkout, workflow commit and event commit must agree; attempt must be one.
`EXPECTED_DRIVER_SHA` is populated from the event commit for consistency checking.
It is **not** an independent authorisation value in this transport. The independent
expected SHA is the exact reviewed main commit in the retained connector branch
creation request. The operator must verify its result, reference and run readback
against that frozen request. No default-branch fetch or mutable ref substitutes
for the committed checkout.

`StageB/owned-selected-folder-build.yml.inert` remains the byte-identical manual
historical anchor. The active workflow must match the new
`StageB/owned-selected-folder-build.create.yml.inert` anchor exactly. The literal
profile binds that path, nineteen unchanged host inputs and fourteen exact helper
sources. Only the two transport-admission helpers require changed module pins.
There is one live trigger, not simultaneous manual and automatic alternatives.

## Integration before the trigger

1. Independently review the exact source and refusal tests. Publish through an
   ordinary, non-reserved source branch, then finish its ordinary CI and guarded
   integration. Creating such a branch may produce a skipped build-only workflow
   record; it must not allocate its native job.
2. Verify all ordinary checks on the actual merged main. Freeze the complete
   `create_branch` payload using that full commit SHA and the literal reserved
   branch name. Independently cross-check it before the trigger.
3. Confirm the reserved branch does not exist and no prior build-only attempt
   exists. Create it once from the exact SHA, never `base_ref`. If the call has an
   uncertain outcome, reconcile the existing reference and workflow records
   read-only. Do not blindly repeat it.
4. Record the returned ref, real create-event run ID, event/source/workflow SHA
   and attempt. If the expected event is not emitted, stop and report that fact;
   do not substitute push, labels, comments, a schedule or another branch.
5. Leave the reserved branch intact as an audit marker. Do not update, delete or
   recreate it. After the terminal attempt, review deactivation: restore the
   profile to False and remove only the active workflow copy. Retain both inactive
   anchors and the evidence.

Attempt one rejects a rerun of an existing run. It does not provide a durable
global one-shot lock against a separately recreated ref. The exact one-attempt
limit, retained branch and later deactivation remain operator obligations.

## Preserved bounds and evidence

The same 31 fixed tool tuples, 720-second work plus 180-second retirement budget,
twenty-minute job, pinned preinstalled toolchain, exact two inspected entitlements,
owned temporary roots and bounded data-only uploader remain. The clean bootstrap
environment has eighteen keys, adding only `CREATED_REF` and `CREATED_REF_TYPE` to
the previous sixteen; the uploader still has six. All native command, filesystem
ownership, cancellation, byte/count and finalisation policies are unchanged.

Build-for-testing and ad-hoc signing do not authorise a host launch, folder panel,
grant, persistent access, security-setting change or Stage C. Ordinary application
folder access remains unavailable. Source checks do not establish actual Xcode,
signature-output or emitted xctestrun compatibility. Failure is retained without
fallback or an automatic second build. Actions artifacts retain their existing
fourteen-day limit.

The eleven added memory-only methods exercise the real bootstrap/driver admission
and a deliberately narrow ASCII-fixture model of the workflow's case-insensitive
equality condition. Case-variant tests positively admit the scheduler model and
then prove real bootstrap refusal before admission/imports. That model is not
execution by GitHub or a claim about all Unicode folding semantics. They retain the 299 previous method
identities and all 233 existing native identities. Existing source, ordinary CI
and later actual build evidence remain separately attributed.

## Primary references

GitHub documents the [create event and its commit/ref semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#create)
and the [ref/ref_type payload](https://docs.github.com/en/webhooks/webhook-events-and-payloads#create).
Those definitions justify using the existing branch-creation connector instead
of assuming it emits a push event. Actual connector event delivery remains a
measured requirement of the single attempt.

GitHub's [expression operator documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#operators) explicitly states its string comparison is case-insensitive. This supersedes the first transport candidate's incorrect exact-case preallocation claim; the operational case-sensitive guards are unchanged.
