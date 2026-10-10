# Saved-library preparation: owned-storage source tranche

Baseline: merged application preview `08793c6cdceb79f2624f1123bdd07f7cb6464d9c`. This next tranche prepares bounded catalogue validation and saved-file storage. It does not activate Save/Open in the application, select a real folder or establish a signed app container. All six actual-main workflows passed, including 84 XCTest + six differential + six parser cases on the exact merged checkout.

## Outcome and authority

The user-facing next milestone is retaining edited labels and multiple historical locations, then deliberately reopening a saved library. This tranche supplies the strict data admission and non-overwriting storage needed for that loop. The existing app, native host, sample controls, saved schemas and observer remain unchanged. UI Save/Open and production container admission require a separate boundary review before activation.

Only tests may create a fresh temporary storage root and supply a held directory lease. There is no public path constructor, environment-selected storage directory, unsandboxed Application Support fallback or production container factory. Holding a storage directory does not authorise reading any source path found inside JSON. All source/history claims remain untrusted.

## Strict catalogue admission

`CatalogueCodec` runs the exact bundled canonical parser in an isolated JavaScriptCore context. Only fixed trusted bundle scripts are evaluated; payloads are structured function arguments. No native callback/object, filesystem, network or DOM API is exported into that context. A successful result is immutable canonical UTF-8 catalogue data, not a grant or command.

The native preflight rejects empty, malformed UTF-8, BOM and more than 4 MiB before conversion. The unchanged parser enforces duplicate keys (including escaped-equivalent keys), fatal field Unicode, depth 12/150,000 nodes, no numeric/Boolean values, 32 records/10,000 entries, nested 1 MiB/2,000-entry snapshots and all hierarchy/gap rules. Canonical output has its own 4 MiB bound. JavaScriptCore does not supply the browser TextEncoder API, so a private parser-only encode shim is verified against the platform TextEncoder over boundary and deterministic Unicode samples. It is not presented as a full browser TextEncoder implementation.

The context is actor-isolated and not a user-code runtime. Allocation is bounded by admitted input and parser budgets; no hard execution-time or JavaScript sandbox security guarantee is claimed. Trusted bundle parity is a separate pre-execution check. Native and Node admission must agree on the shared fixed corpus and byte-identical canonical output before acceptance.

## Authored storage contract, native execution pending

- A pinned directory FD, one owner, fixed owned-fixture admission and required address/identity guard. No directory is inferred from a label, catalogue, URL, environment or CLI argument.
- Generated single-component pending/completed names; exclusive no-follow private file creation. Only regular single-link files owned by the fixture identity are admitted. No link traversal, overwrite, deletion, cleanup or external Save As.
- Bounded partial-write/read loops with explicit EINTR/error/EOF handling and cooperative operation limits. Readback must equal the validated bytes before atomic no-replace publication. Unsupported publication fails closed without a fallback.
- A published-but-unacknowledged attempt is not retried as another save. Reconcile the same generated identity, exact bytes and file metadata; otherwise report uncertainty and preserve the artifact.
- Read only a deliberately selected completed artifact, with a hard read cap independent of stat size and before/after identity/size/mtime/ctime checks. Growing/replaced/changed files reject; bytes pass strict catalogue admission again before a replacement preview.
- At most 256 directory entries and 64 MiB total listed logical bytes, including pending/unknown files; completed files retain the 4 MiB per-file bound. Complete bounded enumeration precedes 64-item pagination; overflow is explicit and preserves state. Pending/unknown entries are disclosed, never passed off as saved catalogues. No unbounded eager parsing of every saved file.
- Guard failures and cancellation withhold successful publication/acknowledgement. A held descriptor does not establish universal confinement against a hostile writer moving an already-open directory. No power-loss durability, physical-source identity, live presence or backup protection claim.

## Gates and scope

Source checks and generated tests are not native execution. New code remains unwired until independent boundary review. Four codec and 35 storage cases are authored (123 total XCTest methods), covering canonical admission, exact byte roundtrip and new store reconstruction, generated-name collisions, partial/EINTR operations, disk-full seams, wrong readback, uncertain publication reconciliation, acknowledgement ownership/replay, links/FIFO refusal, growing/replaced files, complete pagination, aggregate bounds, cancellation and closed/moved roots. A test-only actor suspends only after real strict admission to exercise Close, concurrent operations and file replacement across the validation await; it cannot construct an unvalidated result. None has compiled or run on macOS yet. Hosted checks must use fresh owned storage only and preserve all 84 existing XCTest plus six differential/six parser cases. The next UI bridge must retain native-initiated fixed data operations, revision/generation fences, explicit Replace/Cancel and dirty-close Save/Discard/Cancel. No JavaScript-to-native invocation channel is proposed.

A signed application/container is a later gate. Do not describe an unsandboxed Application Support directory as that container or activate an entitlement/profile to make this source tranche pass. User-device work and real source grants remain separate.

## Primary references

- [Apple JSContext](https://developer.apple.com/documentation/javascriptcore/jscontext) and [structured JSValue calls](https://developer.apple.com/documentation/javascriptcore/jsvalue).
- [WHATWG UTF-8 encoding](https://encoding.spec.whatwg.org/#interface-textencoder) for the parser-only shim's tested encode behaviour.
- [Apple exclusive-rename capability](https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey). Ordinary [rename](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/rename.2.html) can replace a destination and is not an acceptable fallback.

These references guide source design. They do not substitute for actual pinned-toolchain compilation, owned-filesystem tests or independent review.

The 256-entry and 64 MiB storage budgets include pending and unknown regular private files. Unknown names are counted but never opened as completed catalogues; invalid UTF-8, links, nonregular files or incompatible ownership/modes refuse the whole listing. A session admits at most 256 distinct one-use save attempts. Store reconstruction in tests proves the engine can reopen its own completed files, not an actual application relaunch or signed-container lifecycle.

Initial independent source review found that errors within the absent-completed-file reconciliation branch could escape the promised uncertainty classification. The repair normalises all unresolved pending-artifact failures, retains in-flight state and tests both missing artifacts and a replaced pending FIFO. A selected-symlink regression asserts zero data-read syscalls. The combined two-location saved roundtrip retains edited labels, distinct historical origins and the partial record’s gaps through a fresh store instance. These are authored regressions awaiting native execution.
