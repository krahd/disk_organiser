# Inactive Darwin directory-stream type repair

## Actual failure and narrow correction

The consumed [run 38424419438](https://github.com/krahd/disk_organiser/actions/runs/38424419438)
at `9f38511032e6b296ce13cdec98d95321663a55fd` reached Xcode 16.4/16F6,
SDK 15.5 and Swift 6.1.2. The original compiler output reports three type errors
at `Host/ProbeDescriptors.swift`:76,82,90 in x86_64 compilation: the stored
`OpaquePointer` does not match the imported `UnsafeMutablePointer<DIR>` argument
and result types. The exact original streams and terminal record remain in
[the run-seven failure record](RUN-SEVEN-ACTIVATION.md#terminal-result-and-deactivation-2026-10-13).
No successful arm64 compilation or absence of further compiler errors is inferred.

The only host-source change is line 54's stream array element type, from
`OpaquePointer` to `UnsafeMutablePointer<DIR>`. Every other byte in the file is
unchanged. Acquisition, successful descriptor transfer, stream registration,
reverse retirement, one-time removal, close-error handling and deinit remain
exact. There is no cast, changed syscall, architecture override, broader read or
new runtime capability.

The actual SDK type evidence is the preserved compiler diagnostic. Apple's
[public Libc dirent.h](https://github.com/apple-oss-distributions/Libc/blob/71bbe350ab79eef58113991d817ccc6165061a64/include/dirent.h#L74-L85)
defines DIR; the same header declares closedir, readdir and fdopendir with DIR
pointers. This corroborates the C contract, but is not claimed to be the exact
SDK 15.5 header. Apple's [archived directory manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/directory.3.html)
describes closedir releasing the directory stream. The fix preserves that
ownership behaviour rather than converting pointers around the mismatch.

## Exact host-source provenance

The separately reviewed one-line host object is commit
`93db00f686daf5acac064beadf3115cad7a36605`, tree
`eaa128791ef1559fb32ea0d9319047ada3d6a3fb`, parent
`3ee2e6daf865a0772f723707fcf82da8037017f1`. It was created without moving a
branch and without execution. Its full tree differs from that parent at only
the reviewed host file. All nineteen host rows were read back against this
object before binding its SHA; the old `19a2c5f` source is not relabelled.

This inactive successor points HOST_SOURCE_COMMIT to that real source object,
changes the one host-row hash and aggregate rows hash, and selects a new inert
comparison anchor. The new anchor differs from exact historical run-seven bytes
only at the complete normalised-profile hash. Current-source anchor selectors
move explicitly; every prior anchor and all fourteen operational helpers remain
unchanged. The historical run-seven regression now explicitly binds its old
profile hash and whole anchor hash instead of implying current-source identity.
The consumed standalone startup decoder, entry and profile remain exact.

The host-only object is an intermediate provenance snapshot with the older
profile still present. It was not a runnable or independently CI-accepted
checkpoint. The final combined tree requires independent review before any
branch move and ordinary CI afterwards. Neither object authorises another
operational attempt.

## Verification and remaining gates

All 405 local memory/mock methods pass, retaining the exact 402 previous method
identities. Three new source tests cover the one-declaration-only correction,
mutation counterexamples affecting storage/casts/ownership, all nineteen current
host-row hashes and their aggregate, the exact host object, and the profile-hash-only
anchor delta with False, consumed 7 and both workflows absent. The existing
profile mutation test now changes the actual current source SHA and asserts the
mutation differs from its input, avoiding a stale-literal no-op. The historical
anchor-count assertion increases by exactly one. The initial author run exposed
those two stale test expectations; its failed log is retained, and the repaired
full run passes without changing admission or ownership behaviour.

Nineteen structural checks, six default refusals, all 233 ordinary native method
sources and full patch reconstruction are retained. These tests inspect source
or use memory mocks; they do not compile this corrected host. The ordinary app
and source-selection graph remain unchanged. The prior cleanup's actual-main
checks belong to `3ee2e6da`, not this successor.

BUILD_ONLY_ENABLED remains False. EXPECTED_RUN_NUMBER remains the consumed 7;
both active experimental workflows are absent. All four consumed markers remain.
No activation, future counter selection, new run, signing, host/UI launch, panel,
grant, user drive, Stage C or external release follows from this source repair.
Actual compiler effectiveness and subsequent build/signature stages remain open.
Any later attempt requires a separately reviewed source/identity/history/counter
and exact-payload decision; consumed 7 cannot be reused. Ambient encoding-marker
influence remains a disclosed residual risk.
