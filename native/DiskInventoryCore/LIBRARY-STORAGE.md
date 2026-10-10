# Saved-library preparation: owned-storage source tranche

Baseline: merged application preview `08793c6cdceb79f2624f1123bdd07f7cb6464d9c`. This next tranche prepares bounded catalogue validation and saved-file storage. It does not activate Save/Open in the application, select a real folder or establish a signed app container. All six actual-main workflows passed, including 84 XCTest + six differential + six parser cases on the exact merged checkout.

## Outcome and authority

The user-facing next milestone is retaining edited labels and multiple historical locations, then deliberately reopening a saved library. This tranche supplies the strict data admission and non-overwriting storage needed for that loop. The existing app, native host, sample controls, saved schemas and observer remain unchanged. UI Save/Open and production container admission require a separate boundary review before activation.

Only tests may create a fresh temporary storage root and supply a held directory lease. There is no public path constructor, environment-selected storage directory, unsandboxed Application Support fallback or production container factory. Holding a storage directory does not authorise reading any source path found inside JSON. All source/history claims remain untrusted.

## Strict catalogue admission

`CatalogueCodec` runs the exact bundled canonical parser in an isolated JavaScriptCore context. Only fixed trusted bundle scripts are evaluated; payloads are structured function arguments. No native callback/object, filesystem, network or DOM API is exported into that context. A successful result is immutable canonical UTF-8 catalogue data, not a grant or command.

The native preflight rejects empty, malformed UTF-8, BOM and more than 4 MiB before conversion. The unchanged parser enforces duplicate keys (including escaped-equivalent keys), fatal field Unicode, depth 12/150,000 nodes, no numeric/Boolean values, 32 records/10,000 entries, nested 1 MiB/2,000-entry snapshots and all hierarchy/gap rules. Canonical output has its own 4 MiB bound. JavaScriptCore does not supply the browser TextEncoder API, so a private parser-only encode shim is verified against the platform TextEncoder over boundary and deterministic Unicode samples. It is not presented as a full browser TextEncoder implementation.

The context is actor-isolated and not a user-code runtime. Allocation is bounded by admitted input and parser budgets; no hard execution-time or JavaScript sandbox security guarantee is claimed. Trusted bundle parity is a separate pre-execution check. Native and Node admission must agree on the shared fixed corpus and byte-identical canonical output before acceptance.

## Executed owned-storage contract

- A pinned directory FD, one owner, fixed owned-fixture admission and required address/identity guard. No directory is inferred from a label, catalogue, URL, environment or CLI argument.
- Generated single-component pending/completed names; exclusive no-follow private file creation. Only regular single-link files owned by the fixture identity are admitted. No link traversal, overwrite, deletion, cleanup or external Save As.
- Bounded partial-write/read loops with explicit EINTR/error/EOF handling and cooperative operation limits. Readback must equal the validated bytes before atomic no-replace publication. Unsupported publication fails closed without a fallback.
- A published-but-unacknowledged attempt is not retried as another save. Reconcile the same generated identity, exact bytes and file metadata; otherwise report uncertainty and preserve the artifact.
- Read only a deliberately selected completed artifact, with a hard read cap independent of stat size and before/after identity/size/mtime/ctime checks. Growing/replaced/changed files reject; bytes pass strict catalogue admission again before a replacement preview.
- At most 256 directory entries and 64 MiB total listed logical bytes, including pending/unknown files; completed files retain the 4 MiB per-file bound. Complete bounded enumeration precedes 64-item pagination; overflow is explicit and preserves state. Pending/unknown entries are disclosed, never passed off as saved catalogues. No unbounded eager parsing of every saved file.
- Guard failures and cancellation withhold successful publication/acknowledgement. A held descriptor does not establish universal confinement against a hostile writer moving an already-open directory. No power-loss durability, physical-source identity, live presence or backup protection claim.

## Gates and scope

Source checks alone are not native execution. The engine remains unwired after independent source boundary review. Four codec and 35 storage cases are executed (123 total XCTest methods), covering canonical admission, exact byte roundtrip and new store reconstruction, generated-name collisions, partial/EINTR operations, disk-full seams, wrong readback, uncertain publication reconciliation, acknowledgement ownership/replay, links/FIFO refusal, growing/replaced files, complete pagination, aggregate bounds, cancellation and closed/moved roots. A test-only actor suspends only after real strict admission to exercise Close, concurrent operations and file replacement across the validation await; it cannot construct an unvalidated result. Both exact-source and same-tree PR hosted runs compile and pass these cases using fresh owned storage, preserving all 84 existing XCTest plus six differential/six parser cases. The next UI bridge must retain native-initiated fixed data operations, revision/generation fences, explicit Replace/Cancel and dirty-close Save/Discard/Cancel. No JavaScript-to-native invocation channel is proposed.

A signed application/container is a later gate. Do not describe an unsandboxed Application Support directory as that container or activate an entitlement/profile to make this source tranche pass. User-device work and real source grants remain separate.

## Primary references

- [Apple JSContext](https://developer.apple.com/documentation/javascriptcore/jscontext) and [structured JSValue calls](https://developer.apple.com/documentation/javascriptcore/jsvalue).
- [WHATWG UTF-8 encoding](https://encoding.spec.whatwg.org/#interface-textencoder) for the parser-only shim's tested encode behaviour.
- [Apple exclusive-rename capability](https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey). Ordinary [rename](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/rename.2.html) can replace a destination and is not an acceptable fallback.

These references guide source design. They do not substitute for actual pinned-toolchain compilation, owned-filesystem tests or independent review.

The 256-entry and 64 MiB storage budgets include pending and unknown regular private files. Unknown names are counted but never opened as completed catalogues; invalid UTF-8, links, nonregular files or incompatible ownership/modes refuse the whole listing. A session admits at most 256 distinct one-use save attempts. Store reconstruction in tests proves the engine can reopen its own completed files, not an actual application relaunch or signed-container lifecycle.

Initial independent source review found that errors within the absent-completed-file reconciliation branch could escape the promised uncertainty classification. The repair normalises all unresolved pending-artifact failures, retains in-flight state and tests both missing artifacts and a replaced pending FIFO. A selected-symlink regression asserts zero data-read syscalls. The combined two-location saved roundtrip retains edited labels, distinct historical origins and the partial record’s gaps through a fresh store instance. Both native runs execute these regressions successfully. This source review and test result do not activate application storage.

## Executed source and limits

Source `5dd71ae3eca1b6570d809b81e0c7895098536825`, tree `a0dd024c702d9222adaf79162cf906fbda6a58e1`, passes all twelve workflows. [Push native run 38029109382](https://github.com/krahd/disk_organiser/actions/runs/38029109382), job 114146121590, tests the source head. [PR native run 38029128386](https://github.com/krahd/disk_organiser/actions/runs/38029128386), job 114146175444, tests merge `779c03a346d3cf869855c1078eab8b0e8428c5e1` with the same tree. Both execute 123 distinct XCTest methods with zero failures/skips, six independent native/Python comparisons and six unchanged-parser roundtrips. The pre-native gate passes 22 admission cases and 4,102 UTF-8 encoding samples. Remote tree readback preserves all 300 unaffected baseline blobs.

Pinned Xcode 16.4/16F6, SDK 15.5 and Swift 6.1.2 run on macOS 15.7.9/24G830, arm64 image 20260907.0337.1. The actual just-built sample process still proves empty-window readiness and normal Quit exit 0; the existing UI/assets are unchanged. No new visual acceptance is inferred from this engine tranche or its automatically generated screenshots. APFS refuses invalid UTF-8 filename creation, errno 92; the existing core's synthetic rejection is not native invalid-name-path coverage. Actions artifacts expire after 14 days; no permanent archive is asserted.

Raw native log SHA-256: push `367bde4f5f07c33f44167ae5d4960017368b53f9a705763a3f00f3c635d21491`; PR `671466eb8e3ca1c28191b4357fb25d0d6718197a2ad76e09d8aa9fbb792c02c0`. Independent source review and focused repair recheck accept the bounded engine; independent exact-source/raw-log closeout also accepts the bounded executed evidence, with both fetched log hashes reverified. This is evidence review, not another native run or pixel inspection. Documentation successor checks and guarded integration are separate from this exact tested source.

The tests establish owned-store reconstruction and strict data preservation, not an actual application Save/Open/relaunch journey, signed app container, user-granted folder access, power-loss durability or general hostile-writer confinement. Native Save/Open interaction and storage admission remain the next separately reviewed implementation.
