# Inactive explicit-self compiler correction

## Evidence and scope

The consumed [run-eight build](https://github.com/krahd/disk_organiser/actions/runs/38436886388)
failed unsigned build-for-testing with return 65. Its original compiler stdout
contains 39 explicit-self diagnostics in Host/ProbeController.swift. The exact
[terminal record](RUN-EIGHT-ACTIVATION.md#terminal-result-and-deactivation-2026-10-13)
retains original streams, hashes, retirement evidence and limits. The prior DIR
diagnostics are absent from that log only; complete compilation is not claimed.

[PR52](https://github.com/krahd/disk_organiser/pull/52) deactivated the experiment
at main `ea9c2987d257c20bac0988b10c9cb07b1e1ea46d`, tree
`0df3de459779b602a93b1d66e484e5e9fe343716`. Its twelve source/PR workflows passed
first attempt. Five actual-main workflows passed first attempt. The ordinary
native main job initially failed one of 233 methods with two errors, including
an unmet ready-state assertion and an AppKit missing-key-binding-file exception.
This does not prove that the latter caused the former. The unchanged-source,
reviewed one-job rerun passed all 233 methods plus six differential/six parser
cases, 82 true hit/centre pairs and four Cancel phases. Browser main passes thirteen
journeys. No new pixel acceptance is claimed.

The original failure's four observations show source cancellation count staying
zero, then the owned gate timing out and state becoming reviewing. Passing
same-tree lanes and the rerun record cancellation count one, ready state and no
gate timeout. Event-delivery causation remains unresolved. No assertion, timeout,
input path or source was changed to obtain the rerun result, and this repair does
not address that separate ordinary UI reliability issue.

- Failed ordinary main job 115441265857: 210,569-byte original log, SHA256
  `0cbcaf97dd3f3ed96067e5e240ecc4cc7539aa51d1a258adbe03ea3973652aaa`.
  It records 232 passed methods, one failed method, 74 true logged hit pairs and
  skipped downstream differential/parser steps.
- Successful ordinary main [attempt-two job 115444345983](https://github.com/krahd/disk_organiser/actions/runs/38439264641/job/115444345983):
  220,332-byte original log, SHA256
  `9a286f6461c330b0f3f2e589fbcafc6024c81c7762ba45c6a5c10758ea224e44`.
- Main [browser job 115441264596](https://github.com/krahd/disk_organiser/actions/runs/38439264365/job/115441264596):
  60,448-byte original log, SHA256
  `417a425628a91a74901b98f8f232d49566a454fe42cd5302cfa8f237f9d97674`.

## Exact source correction

Only 39 `self.` prefixes are inserted at the measured compiler positions in the
controller. Removing those exact prefixes reconstructs every predecessor byte.
All ten weak-self capture lists, five guarded self bindings, five MainActor Task
closures and the existing scope-retirement order remain exact. No new strong
capture, operation, guard, actor, permission, call ordering or timing is added.

The real host-only source object is
[`b567f3468ae6f5383e5e857b58448c5042ca2836`](https://github.com/krahd/disk_organiser/commit/b567f3468ae6f5383e5e857b58448c5042ca2836),
parented by inactive main above. Its full remote tree changes only
Host/ProbeController.swift; all nineteen host rows were read back and verified.
The controller grows from 11,636 to 11,831 bytes, SHA256
`9127e320f409074590413a845dd43e5b5ea58bae687e73163e50b447f612e87d`.
The row aggregate is
`97e6c7d10b6d98eeb70902a51cd3327bcf470e66f20b75db6825af659b999047`.
No branch was moved to this intermediate object. The final source commit must
retain it as parent so that its identity is reachable in normal history.

The profile remains False with consumed counter eight and the same consumed ref.
Only the host commit/row data, new inert anchor path and explanatory docstring
change. All fourteen operational helper bodies and the other eighteen host inputs
remain exact. A new explicit-self inert anchor changes only the complete profile
hash. All eleven old anchors and the standalone historical diagnostic remain exact;
no active build or diagnostic workflow exists.

Current source fixtures select the new anchor. The run-eight copy oracle binds
its exact historical bytes/hash and retains paired Boolean parsing. The earlier
DIR declaration oracle remains intact; its current host-row check now binds the
successor object, without relabelling the old execution. Three new source-only
methods prove exact 39-prefix reconstruction, reject every singly omitted prefix
and ownership/guard/retirement mutations, and bind the new inactive anchor/rows.

The first structural run refused its stale `cancelAccepted: stopping` source
literal. That single required literal now reads `cancelAccepted: self.stopping`;
all nineteen checks remain present. The failed checkpoint is retained in the
review packet, and the corrected structural run passes.

All 410 memory/mock methods pass, retaining all 407 earlier identities. Nineteen
structural checks and six default refusals pass; all 233 ordinary native method
sources remain exact. These source checks do not compile or run the experimental
host. Independent final pin-chain review and ordinary successor CI remain pending
at this checkpoint. No new native compiler or lifecycle acceptance is claimed.

## Capture semantics and architecture

The [Swift language guide](https://github.com/swiftlang/swift-book/blob/main/TSPL.docc/LanguageGuide/Closures.md#escaping-closures)
describes explicit instance capture in escaping closures.
[SE-0365](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0365-implicit-self-weak-capture.md#detailed-design)
also permits implicit self for some unwrapped weak captures, with nested-closure
and binding rules. This correction does not claim every weak-self/guard pattern
is invalid or diagnose a compiler bug. The measured Swift 6.1.2 invocation in
Swift 6 language mode rejected these exact accesses; explicit qualification
addresses the reported requirement while preserving the intended ownership.

The full-file review retains weak-self preflight/panel/holding/retirement handoffs,
stale-generation and operation guards, unconditional scope retirement before the
completion's weak-owner check, and strong selected/operation retention while a
worker borrows resources. Inline choice/receipt map closures use their existing
parameters/local values. No abandoned-owner path is made dependent on a new
strong controller capture. These remain source judgments until native validation.

The fixed command uses `-destination platform=macOS` without an architecture or
ARCHS/ONLY_ACTIVE_ARCH override. Project/scheme/generated configuration likewise
have no such override. The actual compiler stdout records both x86_64 and arm64
target invocations, and the generated test configuration names both architectures.
An ARM runner therefore does not establish a single-architecture build. Apple's
[build-settings reference](https://developer.apple.com/documentation/xcode/build-settings-reference?changes=_1)
distinguishes target architectures from active-architecture narrowing. The repair
changes no build settings and does not exclude x86_64; no complete resolved-settings
dump or successful arm64 group is claimed.

## Remaining gate

The same twenty-minute, 31-command temporary build/sign/static-inspection envelope
is unchanged and inactive. Counter eight is consumed; it cannot be reused. Any
later attempt requires separately reviewed source/history/counter/ref selection
and a final exact-payload crosscheck. App/UI launch, panels, grants, user drives,
persistent access and Stage C remain closed. Ambient optional-marker influence
and evidence-retention limitations remain disclosed; no harmlessness guarantee
or permanent artifact archive is implied.

## Later conditional build source

The immutable-nine source activation is described in
[RUN-NINE-ACTIVATION.md](RUN-NINE-ACTIVATION.md). It retains every corrected host
byte and all previous evidence, requires fresh operational guards and root's
exact payload check, and does not claim compilation of this repair.
