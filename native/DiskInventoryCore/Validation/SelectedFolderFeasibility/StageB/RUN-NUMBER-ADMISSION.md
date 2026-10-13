# Disabled, single-counter build admission

## Observed gap and current boundary

[PR46](https://github.com/krahd/disk_organiser/pull/46) at `7b0ed4b222cda74312491fca212337d0d7eaa47b` passed eighteen ordinary workflows. Two distinct create-event allocations for its nonreserved source branch have numbers 5 and 6, both attempt 1: [38411469529](https://github.com/krahd/disk_organiser/actions/runs/38411469529) and [38411505462](https://github.com/krahd/disk_organiser/actions/runs/38411505462). Both experimental jobs skipped. The record contains one issued source-branch creation and one issued PR creation; no cause for the duplicate allocations is established. A one-call rule alone is therefore insufficient evidence of one operational admission.

This separate source successor disables the profile and removes the active build workflow. `EXPECTED_RUN_NUMBER = 0` is an unconfigured sentinel, not a selected run, counter prediction or reservation. Both active experimental workflows are absent. The ungated PR46 source must not be merged or triggered. Its exact source and executed ordinary evidence remain historical; this change has only local memory/source validation.

## Enforcement and its assumptions

A later independently reviewed activation must replace zero with one immutable integer from 1 through 1,000,000,000 and bind the same numeric literal in the workflow condition. Only the Boolean activation line is normalised for the profile hash; the counter, bootstrap bytes, workflow path and ref remain hash-bound. The decoder accepts zero only while disabled, and runtime counter admission never accepts it.

The job predicate adds numeric run-attempt 1 and the exact numeric run-number literal. It retains the original event/repository/ref clauses. [GitHub expression equality](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#operators) uses coercion and case-insensitive string comparison, so the scheduler is only an early filter. The memory model separately exercises null, Boolean, numeric and string coercions. It is not a complete Actions expression evaluator or proof of service execution. Exact-case dispatch and canonical-decimal runtime checks remain stricter.

The actual `github.run_number` is bound to a fixed step variable and passed as one quoted CLI argument. It is never interpolated into shell source or added to the eighteen-key startup environment. The bootstrap requires both hash and counter arguments. After the unchanged interpreter, environment and exact workflow/ref/source/checkout/attempt checks, it accepts only 1–10 ASCII decimal characters, no leading zero, sign, whitespace or exponent, within the finite bound and equal to the profile literal. It then admits the source closure and imports operational modules. No build/report/source owner is acquired before those checks. The admitted integer is included in the existing bounded identity record.

[GitHub's variable reference](https://docs.github.com/en/actions/reference/workflows-and-actions/variables) describes run-number uniqueness within a particular workflow, and unchanged run numbers with incremented attempts on rerun. The at-most-one reasoning is conditional on that stable GitHub workflow/counter identity and trusted Actions context: distinct event allocations have different numbers; only one can match; its later attempts refuse. This is not authentication of a compromised service or protection against an administrator replacing trusted source.

The operator must bind the known numeric workflow identity `382488090`, exact workflow path, source SHA and repository, and preserve that identity until terminal cleanup. No reset, rename, recreation or counter reuse may be assumed safe. A missing, changed or unverifiable workflow identity stops the procedure. Runtime source/path/ref/SHA checks do not independently query or authenticate the service's numeric workflow ID. No fabricated context field, API call, credential or new permission is added.

## Selection is a later decision, not a reservation

No positive literal is selected here. Complete source-publication allocations and inspect the relevant history before proposing one. The visible maximum plus one is only a prediction. Missing, deleted, delayed, incomplete or otherwise ambiguous history is a stop condition; supported read access must establish the required identity evidence. The connector's direct workflow-metadata endpoint was unavailable during investigation; individual run records provided the known ID/path, not a verified promise about future identity.

After a separately reviewed literal/source freeze, ordinary CI, normal integration and actual-main checks, repeat the source, workflow-identity, history, marker-absence and no-prior-attempt guards. Any uncertainty stops the trigger. An unrelated allocation can still consume the expected number between the read and the one call. That gives safe refusal, not a second selectable opportunity or a guaranteed successful build. If preparation consumes the literal, stop without triggering and return the evidence for a new source decision. Do not automatically repin repeatedly.

The final trigger review must bind the literal, stable workflow identity, exact verified main SHA and one connector payload. Never raise the literal after an attempted trigger, choose another duplicate event, rerun, change the reserved ref, or delete/recreate its marker. An uncertain call permits read-only reconciliation only. Keep all earlier consumed markers. Terminal cleanup disables the flag/removes the active copy without resetting workflow identity or counters, and retains all anchors and attempt evidence.

## Retained limits and historical evidence

The other thirteen operational helper bodies, nineteen host inputs, seven existing inert workflow anchors and ordinary native entrypoints remain exact. The standalone diagnostic retains its original whole-file, decoder and profile hashes; it rejects the new profile field. Its successful historical key observation is not relabelled as current execution.

The sole unread optional encoding marker and its residual ambient-value influence remain unchanged. The detached startup map still contains eighteen values, and every child command still receives the same six-key environment. There is no environment mutation, network preflight, credential, fallback, new filesystem access or new security grant.

The existing twenty-minute job, 720-second work/180-second finalisation reserve, 31 fixed commands, owned temporary roots and bounded packet rules remain. No application launch, UI execution, panel, user drive or Stage C activity is introduced. A matching counter does not establish successful compilation, signing, inspection or retirement; those remain actual execution gates.

## Local verification and next gate

All 400 memory/mock methods pass, retaining 375 and adding 25 counter cases. These cover exact profile bounds/hash binding, unconfigured refusal, duplicate ordering, no fallback after failure, rerun/source/ref mutations, admission ordering, quoted transport and scheduler-versus-bootstrap semantics. Nineteen structural checks and six no-argument entry refusals also pass. All 233 native method sources remain unchanged. No native or operational workflow ran for this successor.

Independent frozen-source review precedes publication. A later positive literal/activation needs separate source closure, ordinary CI and final trigger crosscheck. The current candidate intentionally cannot execute the experiment.
