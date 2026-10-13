# Inactive XCTest actor-hook correction

## Measured failure and cleanup

The consumed [run-nine build](https://github.com/krahd/disk_organiser/actions/runs/38449777601)
recorded host compile/link for arm64 and x86_64, plus universal host-binary
construction. Full unsigned build-for-testing nevertheless failed with return 65
and 31 main-actor isolation errors in the UI test setup/teardown hooks. This is
not a complete build or signing acceptance. The [terminal record](RUN-NINE-ACTIVATION.md#terminal-result-and-deactivation-2026-10-13)
preserves the original streams, artifact hashes, four retired child/group records
and limits. No later explicit signing/static inspection or app/UI/panel ran.

[PR55](https://github.com/krahd/disk_organiser/pull/55) deactivated that experiment
at main `37d53c6a120d15e9a7ac038b6f2118ee2c181a24`, tree
`deb6a71ae3e2d5251f84c0721029acf4c9f115a0`. All twelve source/PR and six actual-main
ordinary workflows passed first attempt. Source `4b503664e015c8bf8a05925e612f5af86805490b`
and PR checkout `3a7cb70b979aa5bf031fa545fb90edfbb2a70cb2` have that same tree.
The three ordinary native lanes pass 233 distinct methods plus six differential
and six parser cases, with 82 true hit/visible-centre pairs and four Cancel phases.
Each browser lane passes thirteen journeys. Existing earlier native UI delivery
failures remain unresolved; a current pass does not establish their cause or
eliminate that intermittent risk. No new pixel inspection is claimed.

- Actual-main [native job 115487491189](https://github.com/krahd/disk_organiser/actions/runs/38452729322/job/115487491189):
  220,347-byte original log, SHA256 `3940fc0dd794b5e0e8886f1fdf670c776e2b65f2aa7ba41692c257d6877fa0f2`.
- Actual-main [browser job 115487491579](https://github.com/krahd/disk_organiser/actions/runs/38452729240/job/115487491579):
  60,336-byte original log, SHA256 `1ad7efe9a1ccfd6f00be06198befc1b4f4017ed1eeb0e82d9e9408edf3b2efe3`.

## Exact isolated source change

The existing MainActor UI test class now selects XCTest's asynchronous throwing
setup and teardown hooks, each explicitly MainActor. Only the two declarations
change; both complete bodies, all three test bodies and every other UI byte remain
exact. No isolation escape, Sendable assertion, Task/dispatch wrapper, super call,
test timeout, native event, proof, cleanup order or build flag changes.

The [host-only object](https://github.com/krahd/disk_organiser/commit/9eed307659fead2eb5e2824e0d6964277d48c6e6) is
`9eed307659fead2eb5e2824e0d6964277d48c6e6`, parented by the inactive main above. Its full remote tree changes only
`UITests/SelectionProbeUITests.swift`; all nineteen host rows were read back. No
branch was moved to the intermediate object. The final pin-chain commit retains
it as parent. The changed UI file is 13,830 bytes, SHA256
`c9c4e0bb0bf52959d8743f1846eceeb3ff9ed4666d081c844d7ed43d2d419fdc`.
The host-row aggregate is `53ce9d38d3ede095cc190140ac69991b4df3f5c024a940ef6985457ff992318c`.

The profile remains False with consumed counter nine and the same consumed ref.
Only the host commit/rows, explanatory docstring and new inert anchor path change.
All fourteen operational helpers and eighteen other host inputs remain exact.
The new inert anchor differs only in its complete profile pin. All thirteen old
anchors and the standalone historical diagnostic remain byte-exact. Both active
experimental workflows remain absent; all six consumed markers remain intact.

An exact disabled predecessor profile is saved as inert data for historical
run-nine and explicit-self copy oracles, each with a fixed SHA256. Current fixture
paths and current row assertions select the new source. The earlier descriptor
and explicit-self mutation guards remain unchanged. Three additional source-only
methods reverse the exact hook declarations, reject missing isolation and changed
proof/launch/cleanup/timeout bytes, and bind the inactive row/anchor composition.

All 415 memory/mock methods pass, retaining all 412 earlier identities. Nineteen
structural checks and six default refusals pass. All 233 ordinary native method
sources remain exact. Independent final composition review and ordinary successor
CI are still pending at this checkpoint. These local tests do not compile or run
the experimental UI target; new-hook compilation remains unmeasured.

## API basis and lifecycle limits

Apple's [XCTest lifecycle guidance](https://developer.apple.com/documentation/xctest/set-up-and-tear-down-state-in-your-tests)
explicitly describes main-actor asynchronous setup and teardown. The primary
[setup API](https://developer.apple.com/documentation/xctest/xctest/setup(completion:))
and [teardown API](https://developer.apple.com/documentation/xctest/xctest/teardown(completion:))
show the corresponding Swift async throwing signatures. Current primary pages
were checked on 2026-10-13. An exact Xcode 16.4 SDK interface dump is unavailable;
the old code's isolation defect is established by the actual Swift 6.1.2 compiler
log, while the new override import/compatibility still requires a later build.

All four dedicated UI files were audited. This class has no other lifecycle
override or teardown block; its five mutable fields, synchronous helpers and
three cases keep their existing MainActor isolation. OriginalCapture is already
MainActor. RunnerExpectation is immutable comparison data; FixtureProof keeps
synchronous descriptor-scoped checks. No new async closure or cross-actor state
transport is introduced. Each changed hook contains no await in its body.

Choosing async hooks changes their position relative to framework synchronous
hooks according to XCTest's documented ordering. No superclass behaviour is
invented or bypassed by adding a new super call. Existing blocking XCUI readiness
and XCTWaiter calls remain unchanged and runtime-unverified. This source review
does not promise teardown after a crash or guarantee no later compiler issue.

## Remaining gate

The twenty-minute, 31-command temporary build/sign/static-inspection envelope is
unchanged and inactive. Counter nine is consumed and cannot be reused. Any later
attempt requires separately reviewed identity/history/counter/ref selection and
a final exact-payload crosscheck. App/UI launch, panel, grant, user-drive access,
persistent access and Stage C remain closed. Ambient-marker influence and the
14-day artifact-retention limit remain disclosed; no permanent archive is claimed.
