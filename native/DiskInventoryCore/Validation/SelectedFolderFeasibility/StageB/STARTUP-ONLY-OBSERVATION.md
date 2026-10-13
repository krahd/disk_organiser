# Single startup-key observation

This isolated diagnostic records the real post-startup environment key set once. It has no operational build, signing or application path. The build profile remains False and the build workflow is absent. The temporary diagnostic workflow is a distinct surface.

## Fixed scope

- One `create` event for the exact new branch `validation/startup-keys-once-20261013`, at a separately frozen and checked main commit. The two consumed build markers remain untouched. No automatic rerun, replacement ref or delete/recreate. An uncertain call is reconciled read-only.
- GitHub `macos-15`; runtime requires Darwin/arm64, macOS 15.3 or later within major 15, and CPython 3.12.10 from the exact versioned framework executable. `-I -S -B` and exact integer flags remain required. Runner images can change under the label; use the run's normal image metadata and report differences instead of claiming a pinned historical image.
- Job limit five minutes, checkout one minute, single observation step one minute. The Python entry has a 45-second monotonic work deadline, checked around bounded source/system reads and the observation. These are observation bounds, not proof that an uninterruptible system call can be cancelled synchronously. GitHub owns process retirement at step/job expiry.
- The pinned checkout disables persisted credentials, submodules, LFS and safe-directory changes. A fixed SHA-256 of the entry is checked before invocation. The entry rechecks its bounded no-follow source bytes, equality of the active and inert diagnostic workflow, the unchanged literal profile hash and False profile, exact command-line event/checkout identities, interpreter and fixed system version. No operational module is imported and no `stage_b_bootstrap.main` exists in this entry.
- The workflow uses the same eighteen explicit `env -i` names and fixed PATH/LANG/LC_ALL as the failed build-only launch. Event identities now identify this diagnostic. Command-line identity arguments are separately validated before observation; they are not used to construct or filter the measured mapping. No arbitrary inherited value is copied by Python.

## Actual observation and output

The entry evaluates `set(os.environ)` exactly once after standard-library startup, bounded source/profile validation, interpreter admission and system-version validation. It does not run strict `startup_environment` first. Additional or missing keys therefore remain observable. Tests add keys during the simulated interpreter/system stages and prove that they reach the summary. No environment value is requested.

The shared imports and the applicable key-summary, interpreter and read/decode/system helpers are byte-exact with the reviewed bootstrap. The standalone entry excludes all operational loading, dispatch and driver bodies. Its extra source/template/system checks and different profile gate are deliberate differences from the previous run. This is a controlled startup observation, not an exact replay or a proof of the earlier cause.

Exactly one application record is emitted with prefix `OWNED_STARTUP_KEYS `; the full line including newline is at most 2,048 UTF-8 bytes. It contains schema 1 and either:

- `keys_match` or `keys_mismatch` plus the reviewed fixed summary: missing names solely from the eighteen-name expected set, Boolean presence for `LC_CTYPE`, `__PYVENV_LAUNCHER__`, `__CF_USER_TEXT_ENCODING` and `_`, and unexpected/unknown counts capped at 256 with explicit overflow flags; or
- `inconclusive` plus a fixed reason from `arguments`, `clock`, `source`, `profile`, `runtime`, `system`, `observation`, `output`. Exception text, raw paths/argv, arbitrary unknown names and all environment values are excluded.

A strict output schema refuses unexpected fields, names, types and contradictory counts. `keys_match` exits 0; mismatch or inconclusive exits 2. Both branches stop. A failed job with a valid mismatch record is useful negative evidence, never build acceptance. Missing, malformed or oversized output is inconclusive. An unknown count may establish that an extra key exists without identifying it. No result adds an allowlist exception or authorises another run.

Only Actions' ordinary run logs are used; there is no artefact upload, experiment directory, file-content scan, host launch, folder picker, grant, security change or user-device access. Actions also produces its own setup/checkout metadata outside the bounded application record.

## Workflow closure and one-shot operation

The existing source-isolation guard admits the additional diagnostic workflow only as the byte-exact inert template and only with build enabled False. The build and diagnostic workflows cannot coexist under that guard. Unknown or renamed workflows, changed ordinary helpers and added ordinary native callers still refuse. Existing baseline pins and all build anchors are unchanged. Removing the diagnostic workflow restores the original disabled-workflow state.

GitHub string comparisons are case-insensitive: case variants can allocate a runner and checkout. Exact case-sensitive CLI admission refuses those variants before any observation. Do not describe the scheduler as an exact-case preallocation guard.

Before the single connector trigger: verify actual-main ordinary CI, exact head/source, reserved-ref absence and no prior matching attempt; freeze the exact create-branch payload for final review. Keep the new marker on every terminal outcome. After it is terminal, remove the diagnostic workflow through a reviewed normal source change, CI and main verification. Do not remove or reuse historical markers. No build or Stage C follows automatically.

## Validation state

The candidate has 363 passing memory/mock methods retaining all 331 earlier identities, nineteen structural checks, five existing default refusals, plus the new entry's fixed no-argument refusal. Shared helper/source parity, privacy/count limits, late mutation, dispatch failure, workflow closure and terminal output branches are checked without executing the macOS diagnostic. All 233 native method identities and existing runtime/UI source are unchanged. Exact successor ordinary CI and the one real startup observation remain pending.

## Executed one-shot result and terminal deactivation

The single [create-event run 38359714196](https://github.com/krahd/disk_organiser/actions/runs/38359714196), job 115170769056, attempt 1, ran the exact merged main `3389aa6d7d9dbd007e7d3c9987a82308e7c434fc`. The one application record reported `keys_mismatch`: no expected omissions; exactly one unexpected key; `__CF_USER_TEXT_ENCODING` present; `LC_CTYPE`, `__PYVENV_LAUNCHER__` and `_` absent; unknown count zero; neither count capped. The full prefixed record including newline is 324 bytes. No environment value or arbitrary name was logged.

The observation exited 2 by design, so GitHub reports failure. This is a successfully obtained negative observation, not build or application acceptance. Source ordering and that terminal record establish that fixed CLI/source/profile/interpreter/system gates completed before the actual key capture. No build, signing, operational import, host, panel or grant path exists in the entry. No artefacts were uploaded.

The retained decoded job log is 13,526 UTF-8 bytes including its initial BOM, SHA-256 `4c1ff2b5b87629e16c1182f2044b0819a9771350c190f90ae19035e5c94671ec`. Actions identifies image `20260907.0337.1`. The controlled launch's sole observed extra key is established; the previous build-only run's exact process history and cause are not proved. The added source/template/system checks and False gate remain disclosed differences. No key value, allowlist exception or further execution permission is inferred.

The active diagnostic workflow is removed after this terminal result. Its inert template and entry remain exact; the build profile remains False and the build workflow absent. The source-template test now recognises both explicit reviewed repository states, still rejecting altered bytes whenever the active path exists; all template syntax, argument, hash and bounds assertions remain. All 363 memory/mock methods and nineteen structural checks pass locally, with all earlier identities retained. Ordinary exact-successor CI remains pending at this deactivation checkpoint.

Keep the consumed diagnostic marker `validation/startup-keys-once-20261013` at `3389aa6d7d9dbd007e7d3c9987a82308e7c434fc`, and both previous build markers unchanged. No rerun, replacement marker or build follows from this observation.

## Later disabled profile evolution

The [encoding-marker source repair](ENCODING-MARKER-ADMISSION.md) changes the current build profile while retaining this consumed standalone entry and template byte-for-byte. Its original profile bytes are preserved as `startup-key-observation.profile.inert`, checked against the entry's unchanged literal hash. The unchanged decoder rejects the new current profile. This historical execution and its measured key record therefore do not become evidence for the later admission rule; no repeat observation is authorised.
