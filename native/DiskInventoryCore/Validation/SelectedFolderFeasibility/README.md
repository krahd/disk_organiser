# Owned-folder selection feasibility: quarantined source

This directory contains an isolated AppKit probe, its UI-test project and bounded
build/configuration observers. It is **source-only and unexecuted**. It is outside
the production SwiftPM graph and every repository workflow. The ordinary app's
real-folder control remains closed. The checked-in probe seal is `UNSEALED`,
signing is disabled, and the two-entitlement template is inactive.

This is a new reconstruction. The earlier unpublished host became unavailable;
its bytes and native claims are not recovered or inherited. The reviewed memory
contracts added in PR30/32 are retained exactly. Current integrated main
`2417a402` has its own completed six workflows and 233 native methods plus six
differential/six parser cases. Those results do not execute this new project.

## The concrete question

Can a genuine read-only folder selection support the observer's exact no-follow
ancestor acquisition, then relinquish the selected access after all borrowed
descriptors and the original panel-returned scope retire? This probe measures
that question with a fresh, fixed 32-byte test control. It does not catalogue a
user folder, implement another inventory walker, or establish physical-drive,
backup, release or ordinary-app readiness.

Three authored UI methods use real buttons and the standard panel:

1. Select the one sealed owned folder. The identical selected-file operation
   must be denied before selection, succeed with identity and exact bytes while
   selected, and be denied again after retirement.
2. Cancel the actual panel. No selected scope or observing worker is adopted.
3. Cancel a held successful read. The worker retains its descriptors until it
   returns; only then does its owner retire the scope. Recheck denial and retry.

The positive operation retains checked descriptors through the held interval.
Cancel signals condition-protected memory; it does not close another thread's
resources. Terminal ordering is defined under that lock, and a later Cancel
cannot rewrite the worker result. A visible Cancel/Close accepted before queued
main-actor publication separately suppresses success; real failures remain
failures. Pure policy checks are authored in the UI module and remain unrun. Generation and identity guards reject stale
completion. Close requests retain the operation until retirement; the three new
UI methods exercise Cancel, while existing synchronous Close regressions remain
in the unchanged production test suite.

Parent **listing**, sibling read-open, selected write-open and exclusive-create
controls must be denied during the positive read. A parent-open denial would be
contradictory: the positive ancestor algorithm needs that same metadata-only
parent open. The parent control therefore performs one `readdir` attempt without
copying or reporting an entry name. No write or truncation is attempted; an
unexpected exclusive-create success leaves the owned failure evidence intact.
Only `EACCES`/`EPERM` from the explicitly permitted measured operation family
qualify as denial. `fstat`, ACL queries and other setup syscalls never qualify. Missing objects, `EEXIST`, changed identity,
ACL/type failures, cleanup failures and other errors cannot count as success.
Every denial retains its operation and errno in the bounded terminal receipt.

The separate UI runner positively proves the sealed fixture's identities,
private modes, empty ACLs, bytes and absent control before launch and after each
terminal result. It reads through those same checked descriptors and retires
all of them before the next host action. No descriptor, bookmark or reusable
grant is passed to the host. `HostIdentity.swift` validates static and running
code with public Security APIs, binds the actual executable and identifier, and
requires exactly App Sandbox and user-selected read-only entitlements, both
true Booleans. Successful signing-information retrieval alone is insufficient. The unsupported
private status API from the first local freeze has been removed; no dynamic
status word is fabricated from a validity result.

The runner additionally requires the exact B-observed host CDHash before
launch and again for the actual launched PID before any Choose/panel action.
Seven reserved runner-only comparison fields bind path, identifier, CDHash,
source commit, fixture digest and run/case identities. Missing, colliding,
extra or changed values refuse. These values are data checks, never permission
or a mechanism to acquire an owned root; the host launch environment stays empty.

## Source components and trust boundaries

- `Host/`: fixed-input AppKit controller, thread-safe worker, single-owner
  descriptor ledger, measured syscall matrix, fixture decoder and actual
  Security-framework identity observer. Acquisitions register immediately;
  cleanup continues after one error and never retries an ambiguous descriptor.
  Reads admit type/identity/size first and use no-follow/nonblocking descriptors.
- `Generated/`: deliberately inert placeholders. `Tools/fixture_inputs.py` can
  render three exact source inputs from strictly admitted **claimed** bytes;
  this supplies no access or execution permit. Fresh fixture creation is authored
  for a later approved stage and has not run.
- `Probe.xcodeproj` and its shared test scheme: one app and one UI-test target.
  `CODE_SIGNING_ALLOWED=NO`, sandbox activation is off, the host entitlement build
  variable is empty, and there are no launch/archive actions or workflow links.
- `Tools/probe_contract.py` / `configuration_pair.py`: unchanged memory-only
  contracts. Imported JSON and matching pairs remain claims. The 19-case link
  corpus resolves components against a complete inventory, never filesystem
  `realpath` or lexical `normpath`.
- `Tools/owned_build_observation.py`: a fresh-created owned-root capability, with
  no reopen-from-path/JSON constructor. It streams a bounded product inventory,
  validates the root separately from descendants through the existing contract,
  and binds raw configuration, full parsed tree, all three fixed products and
  exact driver context. Named/held product identity is checked; a replacement
  refuses. Whole-byte context changes invalidate the retained freeze.
- `Tools/experiment_controller.py`, `bounded_process.py` and `native_observations.py`:
  a single-thread owner creates and retains fresh build/fixture capabilities,
  exclusively writes the pinned source and generated inputs, runs only fixed
  build/sign/observation commands, and binds the real observations to a retained
  immutable inspection. Both B/C gates return false, the source pins are
  `UNREVIEWED`, and the CLI refuses. These operations are authored, not run.
  Stage C consumes that exact retained inspection once, re-observes it before
  `test-without-building` and after process retirement, and refuses changed
  configuration, signatures, products, source or fixture. No rebuild/re-sign,
  receipt deserialisation-to-capability, workflow or production entry point is
  supplied.
- `Tools/runner_expectations.py`: derives one fixed, separately named test
  configuration during B after actual signature observation. The original emitted
  configuration stays byte-exact; only seven reserved runner expectation fields
  may be added to its runner environment. Full parsed equality after removing
  those fields, original/derived raw bytes and observed values are all bound.
  Exclusive no-follow creation refuses any existing destination. C consumes the
  already frozen configuration and never writes expectations or re-signs products.
- `Tools/xctestrun_binding.py`: a strict XML FormatVersion-2 **prototype**, tested
  with synthetic configurations. A strict UTF-8/XML-1.0 declaration is required; conflicting/unsupported
  encodings refuse. Duplicate/unknown fields, entities, excessive
  nesting and unsupported versions refuse. Both environments, methods, skips,
  product paths and raw bytes are retained. This is not a verified parser for
  actual Xcode 16.4 output: that output must be inspected before any use.

The driver-context record pins source/fixture identities, roots, working
directory, executable, exact arguments/environment, toolchain and all three
signature observations. Supplying JSON is still only a claim. The closed
controller obtains observations through fixed bounded vendor calls and native
source-bound runner records. It requires executable and fixture-resource rows,
not merely product directory names, and binds preparation logs and generated
source hashes to the inspection. Its versioned fingerprint covers every
Inspection dataclass field, including nested raw configurations, observations,
source/generated rows and preparation evidence; it is only an evidence reference,
not an ownership deserializer. Static runner/test signatures must have no
extra entitlements; the host must have the exact two. Unexpected tool output,
identifiers, extra privileges or schema fields stop the experiment.

Each actual direct child would have one Popen owner, isolated process group,
closed inherited FDs, finite pipe capture/deadlines and bounded terminate/kill/
reap handling. Group absence is observed separately, with signal zero only;
service-launched host and UI-runner PIDs come from the source-bound native
records and must also be observed absent. A signal or test tearDown alone is
insufficient. Unknown/reused/alive processes refuse; no process-name kill or
unverified-PID termination is used. Missing process observations after partial
startup are an explicit failure, not successful cleanup. Failure output, source
checks and owned result/capture files remain for review; there is no automatic
recursive deletion or repeated attempt.

All three method outcomes must bind to that inspection's source, fixture,
host identifier/path/CDHash and per-method launched PID. Four original window
captures are written only by the isolated UI runner to a fixed newly created
capture directory whose device/inode is compiled into the seal. PNG bytes are
not resized, filled, composited or re-encoded. The controller requires exactly
those four filenames and their observed byte counts/hashes/dimensions, and
retains the complete original result-bundle inventory. These source checks
cannot replace later independent inspection of the actual pixels/results.

The host's bundled JSON is bound by its exact compiled digest and signature,
and the producer must admit the same bytes with the strict Python contract.
Foundation's JSON decoder is not claimed to have independent duplicate-key
parity. Native parser/signature behaviour still requires actual execution.

## Bounds and local checks

The unchanged contracts cap fixture JSON at 4 KiB, inventory JSON at 8 MiB,
20,000 inventory rows, 512 MiB per product file and 2 GiB total product bytes.
Containment uses the existing 19-case corpus and its 40-link / 128-component
limits. The observer additionally caps depth at 64 and checks a 30-second
cooperative budget between operations; it does not promise to interrupt a
blocked kernel call. Configuration reads cap allocation at 1 MiB, XML depth at
16, nodes at 4,096 and text at 4 KiB. Driver context is at most 64 KiB. Native
control reads are at most 33 bytes / 64 attempts, held reads at most five seconds,
and terminal receipts at most 2 KiB. Each tool captures at most 8 MiB, with
32 MiB aggregate / 64 calls per owner; observation calls cap output at 64 KiB.
Build and runtime deadlines are respectively 600/900 seconds, with bounded
retirement checks. PNG captures cap at 4 MiB and 8,192 pixels per dimension. None of these is whole-drive capacity.

Run only the source/memory checks from this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Tools -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 Tools/check_source_isolation.py
```

The authored checkpoint passes 151 memory/mock methods: all 54 existing methods
(including the unchanged 19-case corpus), all 27 first-freeze additions and
fifty new encoding, process, observation, fixture-owner and controller
regressions, including twenty additional exact-derivation, whole-inspection
fingerprint and partial-failure/write-ownership methods. Nineteen source-isolation checks also pass. Mocks perform no
real fixture/build-root operations. Source checks are not Swift compilation,
Xcode project validation, panel execution, grant proof or pixel acceptance.
All 233 existing native methods remain unchanged; the three new UI methods have
not compiled or run. No new native screenshot exists.

## Retained source review checkpoints

The first local freeze was changes-requested for the private Security call,
late visible cancellation, overbroad denial families, XML declaration mismatch
and missing controller. The second repaired those areas but its review still
found three defects: B host identity was checked only after panel actions,
partial B failures omitted disposition evidence, and the inspection fingerprint
omitted retained fields. This separate successor addresses all three; its independent source recheck
clears them without a new blocking finding. Earlier bytes and findings are
preserved, not relabelled accepted.

On B failure, bounded raw tool results (including direct-child/group retirement
ambiguity) remain retained. Source, fixture, partial-product and capture
observations are attempted independently; any missing/unreadable state is marked
unproved without erasing the original failure. Partial state is not described as
an accepted FrozenBuild. There is no signing retry, repair or deletion. A surviving
descendant/service process is a failed retirement observation; this controller
does not promise to terminate unverified processes.

## Independent source closeout

The source review binds manifest
`94a7695beb77079a84a574f01862f60e11241d694869f416046a2e02763fb8d9`:
151 supplied memory/mock methods, eleven independently authored mocked checks
and nineteen source checks pass. All 38 paths and the twelve-path v2 repair
delta reconstruct exactly, preserving 357 other baseline blobs and all 233
existing native methods. Original v1/v2 failures remain recorded above.
This documentation-only closeout changes no reviewed source/test/project bytes.
It establishes source clearance only; none of the native or permission gates
below has run or been approved by that review.

## Separate next gates

A. Freeze this source identity, independently review it, then save a reversible
repository checkpoint. No host execution is included.

B. After explicit build/sign approval, prepare fresh owned fixtures on a fresh
macOS runner, compile and ad-hoc sign only these experiment products, inspect the
actual toolchain/test configuration and exact two host entitlements. Unknown
fields, extra entitlements, signing profiles or privileges stop the attempt.
Freeze app, runner, test bundles, configuration and fixture inputs after sealing.
The retained owned workspace and in-process controller must remain available
through the later gate; if it
expires, restart an approved B preparation rather than adopt paths from a claim.

C. Only after the actual B receipt is reviewed and runtime approval is explicit,
reverify the immutable products and run without rebuild/re-sign. Actual process retirement, real Xcode configuration compatibility, real panel
accessibility hierarchy, all source-bound results and original screenshots
remain required acceptance work. The source controller exists; its activation
and hosted execution wiring still require separate review and permission. No new permission prompt may be
accepted automatically. If the exact ancestor operation is denied while the
grant is active, report its operation/errno and stop; do not follow aliases,
relax admission or substitute an unsandboxed/broader-access experiment.

Only a later independent production-admission/wiring review could connect a
real selected folder to progress, Cancel, reviewed Add and the existing offline
library. This source adds no ordinary-app capability, persistent grant,
user-computer/default-data-path execution, file move or backup claim.

## Primary references

Apple's [sandbox file-access guidance](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox)
describes standard-panel scope access and explicit retirement; it does not prove
compatibility of this ancestor algorithm. The [read-only entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.files.user-selected.read-only)
is the intended category. [TN2339](https://developer.apple.com/library/archive/technotes/tn2339/_index.html)
describes build-for-testing/test-without-building separation, not current ad-hoc
runner acceptance. Apple's [SecCode header](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_codesigning/lib/SecCode.h)
distinguishes validity/status from copied signing information. These sources
were checked on 12 October 2026; all platform results above remain unexecuted.

The fixed CLI observation adapters use Apple's documented [entitlement display](https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles)
and [CodeDirectory hash display](https://developer.apple.com/documentation/technotes/tn3126-inside-code-signing-hashes)
forms. Their exact output-format assumptions, runner identifiers and the actual
Xcode configuration still require inspection on the pinned toolchain. No
non-Apple CLI example is treated as proof of runtime compatibility.


## Disabled Stage B source candidate

The [reviewed build-only plan](StageB/STAGE-B-PLAN.md) has a source implementation.
The [implementation addendum](StageB/IMPLEMENTATION-ADDENDUM.md) records the first
source-review repairs and explicitly supersedes the historical move instruction.
`Tools/stage_b_profile.py` remains false; the template is
`StageB/owned-selected-folder-build.yml.inert`, outside active workflows. Default
controller calls and Stage C stay closed. No new host build/sign/launch has run.

The fixed bootstrap binds all nineteen unchanged host inputs, the complete Python
import closure and dispatch/checkout identities before owned-root creation. The
single-use admission retains one owner thread. The exact 31 native command tuples
are a version preflight, one build, three ad-hoc signatures and two observation
rounds. The driver work budget is 720 seconds; 180 seconds are reserved for
independent evidence and retirement. Actual compiler, signature and emitted
xctestrun compatibility remain unknown.

A separate report owner writes at most 64 MiB/96 regular files, preserves raw
bytes and closes after source owners. The manifest excludes itself; its identity
is emitted only after report close. The data-only upload verifier reopens that
retired report for read-only identity/hash validation, never a source/build owner.
The inert template writes only a validated single path to GitHub's standard
step-output file. It cannot treat output or JSON as a grant or resume Stage C.
Upload or finalisation failure prevents acceptance. Fourteen-day Actions retention
is not permanent archival.

The proposed runner is macOS15 ARM64 with the preinstalled pinned toolchain; the
fixed CPython cache must already exist. No installation, global xcode-select,
licence acceptance, credentials, permission repair or security-setting change is
included. The pinned checkout action disables credential persistence and global
safe-directory modification. Its [exact metadata](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/action.yml)
and the [pinned upload metadata](https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml)
were inspected; this is not a claim of new platform execution or an exhaustive
third-party dependency audit.

Source/memory checks (no operational owner or native process):

```sh
python -B -m unittest discover -s native/DiskInventoryCore/Validation/SelectedFolderFeasibility/Tools -p 'test_*.py' -v
python -B native/DiskInventoryCore/Validation/SelectedFolderFeasibility/Tools/check_source_isolation.py
```

The first source candidate passed 254 methods and nineteen source checks, then
independent review found six bounded repair groups. The successor preserves that
freeze and repairs failure/cleanup attribution, propagated deadlines, the native
source closure, sanitised startup and retained-anchor activation semantics. Its
final method count and independent recheck are recorded in STATUS.md. All 233 existing native source identities are unchanged. Exact
source review and a reversible checkpoint precede the owner's proposed one-run
build-only question. Only an explicitly reviewed activation changes the profile's
Boolean and copies the exact template into the active workflow directory while
retaining the inert comparison anchor. This
source candidate does neither. Real panel/grant and production integration are
separate decisions after actual feasibility evidence.


## Connector-only build trigger successor

The disabled-source and manual-activation sections above are historical checkpoints.
PR36 integrated the build-only activation, but no build attempt was started.
The current [connector transport contract](StageB/CONNECTOR-TRANSPORT.md) replaces
only how the one authorised experiment is started. It uses creation of one exact
reserved branch at a reviewed commit; normal source publication and main merges
do not run the experiment. The original manual template remains unchanged for
attribution; the new create-event anchor is separately retained and byte-bound.
The profile is enabled for that specific transport while both default controller
gates and Stage C remain closed. The current result is source/memory validation
only. Actual build/signature/parser acceptance still requires the one recorded run.

The scheduler filter ignores case, so a case-variant reserved name may allocate
a runner and run checkout/startup. The unchanged strict bootstrap then refuses
before operational owners or build tools. Exact-case preallocation is not claimed.
