# Native Save/Open interaction: revised implementation contract

Revision 2, 10 October 2026. Incorporates R1–R8 from independent review `9ebc59cfd949e1953f0de58e52a1325f0ca6f8358ee6b42d71a0096e1c70eb8f`. Approved for source authoring within the injected-owned-storage boundary. The local interaction candidate is authored; native compilation, execution and visual acceptance remain open.

Baseline is merged main `f22e8ec0f0b61c396b86fdef5852139ab203eabb`, tree `9331712a8997f9fc6eaf0ddfab5a00cedec69cd6`. All six main workflows pass, including 123 XCTest, six differential/six parser cases and 22 admission/4,102 encoding samples. Those baseline results do not test this new interaction.

## 1. Outcome, source scope and production boundary

An actual AppKit/WebKit window with one injected, fresh test-owned store supports Add examples → rename locations → Save new library version → Open saved candidate → inspect all recorded locations → Replace/Cancel, plus honest close choices. This is an owned native interaction milestone, not an installed persistent product.

Source scope is the canonical catalogue controller, shared native host/session/window, a persistence coordinator and owned UI tests, bundled asset parity, workflow evidence and docs/STATUS. Catalogue/snapshot v1 schemas, parser strictness, observer core, standalone browser file behaviour and provider gates stay unchanged. There is no new production dependency, file cleanup, overwrite, Save As or manual-plan export.

The normal executable receives no storage capability. Its Save/Open controls stay visibly unavailable with an accessible reason; it must not infer a writable directory from JSON, arguments, environment, Application Support or a container-looking path. The injected window says “Temporary test library storage” and explains that each Save creates a new saved version. Both modes disclose that real-folder access is unavailable. Native and page copy must agree: remove universal “nothing saved” wording only in the injected mode, while retaining the ordinary preview's temporary-only wording.

Production persistence remains a concrete later tranche: real packaged/signed identity and sandbox configuration, a separately admitted app-created container subdirectory, one-writer policy, then actual process Save/Quit/relaunch/Open evidence. Container-only persistence does not require a source-drive grant. Actual folder observation is a separate later read-only picker/grant gate. Do not invoke either gate, sign/activate entitlements, change security settings, use a user device or persist a source bookmark in this slice.

## 2. One native owner and one writer

A single MainActor interaction owner admits every native intent: sample choose/scope/prepare/review/retire, Save, saved-list loading/selection/read/replace, Close and Quit. Existing LibrarySession can remain a component but its public entry points cannot bypass that admission. Buttons and shortcuts use identical guards. Reserve an operation synchronously before the first await.

Native states distinguish idle, sample flow, saving, checking save, opening, preparing replacement, replacement unresolved, close enquiry, close decision, stopping and closed. Keep four separate identities: window lifetime, host navigation/session, operation nonce and page revision/interaction epoch. Every awaited result first records any real artifact fact, then checks whether it can affect the current view. Stale results cannot revive controls, clear dirty state or target a successor. Preserve the existing “snapshot committed before cancellation” retirement distinction.

One coordinator owns one LibraryStorage actor/root. Tests create a fresh root, inject it once and close that owner before reconstruction. They never share a root between concurrent writers or create an actor per button. An injection lease refuses duplicate ownership within this fixture lifecycle. No root-wide or cross-process locking/quota guarantee is claimed; future production admission must enforce one writer or separately solve that problem.

Ordinary Save excludes other native operations but allows later catalogue edits after export, so “earlier revision saved” remains meaningful. An edit/review already active when Save begins blocks export. Open and Close instead hold a page mutation fence. While an unresolved operation exists, another Save/Open is withheld. An explicit check runs as a new uncancelled checking task for the same attempt, never as another write.

## 3. Versioned data-only bridge and exact bounds

Use `catalogue-data-bridge/v2`; reject every other version. Keep canonical saved schema v1 unchanged. All native calls select fixed source strings with structured arguments. No arbitrary code interpolation, path field, native object binding or JavaScript-to-native handler is introduced. The bundled, parity-checked controller is trusted code; all imported fields remain untrusted claims. An echoed nonce or successful schema/save check is correlation, not drive/source authority.

Every request/reply is an exact dictionary with only the listed keys; values are strings. Booleans/numbers/null/arrays/objects, extra/missing keys and coercion reject. Common envelope fields `version`, `session`, `operation` are required unless the legacy snapshot call uses its existing `delivery` field. Session/operation/delivery/fence/candidate IDs are canonical lowercase 36-character UUIDs. An optional fence is represented by the exact empty string, never null or a path.

The existing short decoder stays at five fields, key size 16/value size 64 UTF-8 bytes for initialise/snapshot stage/retire. New control decoding has an exact operation-specific key set, at most 12 fields, key size 24/value size 64 bytes, and at most 1,024 total UTF-8 bytes of keys and values. The sole large response adds `text` to an exact export envelope; control metadata keeps its separate 1,024-byte cap. Fixed error enums map to native-owned messages; never display arbitrary page errors as commands or instructions.

Catalogue `text` is nonempty, BOM-free, valid Unicode/UTF-8 and at most 4,194,304 UTF-8 bytes, checked by the page before return and natively before CatalogueCodec. Canonical output has the same bound. Test exact-boundary/one-byte-over multibyte payloads; no UTF-16-character substitution. Snapshot bounds remain 1,048,576 bytes/2,000 entries; catalogue bounds remain 32 records/10,000 entries plus the unchanged parser depth/node/field budgets.

`revision` and `epoch` are canonical decimal strings in 0…9007199254740991, no signs/leading zeros/coercion. Revision advances on committed catalogue changes; epoch also advances for selection changes and edit/review state/input changes. Neither wraps or resets within a session. Exhaustion rejects before mutation and reports recovery unavailable; it never reuses an old value. Selection count is canonical decimal 0…2000. Fixed dialog values are `none`, `label-edit`, `snapshot-review`, `catalogue-review`, `other-edit`; draft values `none`/`uncommitted` and dirty values `clean`/`dirty` are separate.

Operation schema (common envelope above is implicit):

| Operation | Additional request fields | Exact additional reply fields and purpose |
| --- | --- | --- |
| `initialise` | `mode`=`temporary` or `owned-storage`; no operation ID | `mode`, `state`=`ready`; session/version remain required |
| Existing `stage` / `retire` | Existing bounded snapshot `text` / `delivery` | Existing stage/retire fields and outcomes; new version only |
| `status` | none | `revision`, `epoch`, `dirty`, `selections`, `dialog`, `draft`, `state`=`idle`/`busy` |
| `exportCatalogue` | `fence` empty for ordinary Save, or its current close fence | `revision`, `epoch`, `state`=`exported`, `text` |
| `acknowledgeSaved` | `revision` matching recorded export | `revision` (captured), `current_revision`, `state`=`current-saved`/`earlier-saved` |
| `savedResult` | none | Same saved result, or `state`=`not-applied` with captured/current revision |
| `prepareClose` | none | Close-loss fields as `status`, plus `state`=`fenced`; operation ID is the fence |
| `releaseClose` | none | `state`=`released`; only its matching fence can release |
| `prepareOpen` | none | Same fenced loss fields; refuses an unfinished edit/review |
| `prepareReplacement` | `candidate`, `revision`, `epoch`, bounded `text`; same Open operation | `candidate`, `revision`, `epoch`, `state`=`prepared`; no current-state mutation |
| `retireCandidate` | `candidate` | `candidate`, `state`=`retired`/`committed`; committed alternative includes exact commit fields |
| `commitReplacement` | same `candidate`, `revision`, `epoch` | `candidate`, `revision` (new), `epoch` (new), `state`=`committed`, `view`=`ready`/`blocked` |
| `replacementResult` | `candidate` | Same committed result, or `state`=`not-committed` with the candidate, current revision/epoch and `view` |
| `cancelOpen` | none | `state`=`cancelled` or `committed`; committed replies include the exact commit fields |

Exact per-state reply alternatives are separate decoder variants, not optional arbitrary fields. `initialise` remains a four-field short reply. Snapshot requests retain their existing 1-MiB preflight and short replies. Status has no filesystem authority. Native may query it only for an explicit intent or bounded lifecycle reconciliation; no event/key logging or background filesystem work is added.

WebKit completion timeout remains 10 seconds with a one-shot continuation. Timeout does not prove the page failed to apply an acknowledgement/replacement. Preserve a queryable result for the same nonce; never re-execute a replacement under a new nonce. Before beginning any mutation, reserve its replay/result record. Retain at most 128 persistence intent IDs and their terminal small results per view, separately from the existing 128 snapshot deliveries. Status queries reuse their admitted operation correlation and do not grow history. Active/uncertain records are never evicted; exhaustion refuses new intents without losing current data. Store attempts remain bounded at 256; IO retains 4,096 cooperative checks/five seconds. None is a hard kernel-call, JavaScript runtime or arbitrary-malicious-page allocation guarantee.

Preserve narrow WebKit read root, nonpersistent data store, strict CSP, content blocker and navigation/download/drop restrictions, plus separate isolated JavaScriptCore validation. Post-callback validation cannot prevent an arbitrary malicious page from allocating a large return; this contract relies on the trusted bundled controller and its pre-return bound.

## 4. Save order and same-attempt reconciliation

1. The owner admits one Save intent/nonce. Export captures revision and immutable catalogue text together. Store session/window/navigation identities, nonce, revision, epoch and admitted bytes. An already acknowledged unchanged revision is a no-op with “No catalogue changes since that saved version”; repeated active clicks do nothing. The first explicit empty-library Save is allowed.
2. Apply exact envelope bounds, run CatalogueCodec and call `LibraryStorage.save` once using that same UUID. A cancelled intent is checked before queued codec/storage invocation. After return, record the artifact outcome even if the view has retired.
3. A successful save receipt, or same-attempt `reconcile` returning published, advances to `published-awaiting-storage-ack`. Call `LibraryStorage.acknowledge(receipt)` and require its re-verification to succeed before any page operation can mark clean. Failed acknowledgement keeps the page dirty and the operation unresolved.
4. Record `storage-acknowledged` in the coordinator. Retain receipt, attempt, exported bytes/revision and view identities independently: storage acknowledgement clears the store's pending state. Then send `acknowledgeSaved` for the same export. Only equal current revision clears catalogue dirty; later edits produce `earlier-saved`. Neither temporary selections nor draft text is cleared.
5. If the page reply is lost, remain `saved-page-unresolved`. Query `savedResult`, or retry the same idempotent acknowledgement, using the same tuple. Never call storage.save again and never assume storage.reconcile is available after its acknowledgement. A recorded acknowledgement cannot clean a newer revision. Both acknowledgement and result query recompare the current revision and report `earlier-saved` after later edits; they never reuse an old `current-saved` reply as proof of current cleanliness. If the old view retires, preserve the known stored fact but never acknowledge another view with its tuple.

Required outcomes and copy:

- `rejected-before-storage`: no write attempted; retain current data.
- `not-published`: known pre-publication failure or confirmed retained pending artifact; current revision stays dirty, explain retained incomplete data. A new attempt needs another explicit user Save.
- `storage-unresolved`: publication or its acknowledgement is unconfirmed; retain same attempt, withhold Save/Open and offer “Check save result”. No saved/clean/no-file claim.
- `saved-page-unresolved`: the earlier revision is stored but view acknowledgement is unconfirmed; retain receipt/tuple, withhold automatic close/new Save and query the same page operation.
- `current-saved`: both acknowledgements confirmed; only catalogue dirty is cleared.
- `earlier-saved`: both stages confirmed for an older revision; current dirty state is untouched.
- `retired`: no current-view effect. Artifact fact remains known-stored, known-not-published or uncertain.

Uncertainty is nonterminal until resolved or explicitly abandoned. Cancellation cannot turn uncertainty into failure. Final close may abandon an unresolved in-memory operation only after explicit warning/confirmation; preserve artifacts and do not claim that the reconciliation capability survives process restart. No automatic retry, overwrite, deletion or cleanup is added.

## 5. Close/Quit fence and all temporary work

`prepareClose` synchronously installs a page mutation fence before returning loss state. Every catalogue mutator, selection handler, draft input/submit and review commit checks that fence. Disable/hold relevant form controls while retaining their previous state, text and focused element; Cancel restores them. Only operations carrying the same close fence can perform the allowed Save acknowledgement. A native sheet alone is not the fence.

Close and Quit share one single-flight decision; repeated requests reuse it. If another operation is active, retire/cancel it and wait for its classified result before enquiring, or explicitly expose its unresolved outcome. Do not call host.close or LibraryStorage.close on enquiry/Cancel. Final close retires the view generation and closes the owned store only after necessary artifact bookkeeping.

- Clean catalogue, no selections, no dialog/draft/review and no operation: close after the fenced result.
- Dirty catalogue: Save library / Discard catalogue edits / Cancel. Save completes the ordered protocol while the close fence remains held; requery the same fence before deciding no other work is lost.
- Temporary selections: disclose their exact count and that catalogue v1 does not save them. A plain Save never discards them. After a successful save remain open until explicit “Discard temporary selection and close” or Cancel. A combined action is allowed only if it explicitly says it saves the library and discards the selection.
- Unfinished label edit or review: bounded default is “Finish editing”/Cancel close, restoring that exact interaction. Do not save committed data then silently discard the draft. Any discard alternative must name the draft/review explicitly.
- Unknown page state: keep open with failure. An optional escape must explicitly say “Discard unconfirmed temporary work and close”; never infer clean or saved.

Close cancellation releases only its own page fence, preserves all data and restores focus. Late callbacks cannot reopen a closed sheet or window. Current catalogue saving never saves temporary project selections or a manual plan.

## 6. Native Open chooser and one authorised replacement

Open first acquires `prepareOpen`'s page mutation fence and exact revision/epoch/loss state, then enumerates the store. An unfinished edit/review refuses Open with a return-to-edit action. Native chooser and selected-preview pane own Replace and Cancel; there is no WebKit-to-native completion channel.

Enumerate the complete bounded metadata set before 64-row pagination. Preserve row selection by opaque entry identity, not index. Refresh retires old selections. Show completed-pattern candidate count, pending/unknown counts, total listed bytes and page position; candidate content is not verified until selected. Rows use a readable filesystem modification date with explicit timezone, byte size and stable ordinal; UUID is expert detail. Dates are not authenticated save times or claimed observation dates. Same-date rows remain distinguishable without a filename hunt.

The store limits are 256 entries and 67,108,864 logical bytes including pending/unknown data; every listed file, including pending/unknown, is limited to 4,194,304 bytes. Links/nonregular/mode/owner failures, changes or overflow refuse the whole list, clear stale Replace and preserve the current library. Explain that retained failed artifacts consume space/entries. No cleanup workaround exists.

Only explicit row selection reads its opaque SavedLibraryEntry. Run strict validation, then prepare a bounded preview containing all 0…32 location labels, record/entry counts, claimed source dates and partial/gap caveats. All fields are inert text. Zero-record replacement is deliberate. A selected-read generation and candidate UUID prevent an old row result replacing a newer preview. Row-selection actions are refused while a read/page-prepare call is active; Cancel remains available. Before another row is prepared, the previous prepared candidate is explicitly retired under the same Open owner. At most 128 candidate identities are admitted per Open operation, with no silent replay eviction; exhaustion releases through Cancel or preserves the current candidate without admitting another. Cancel during reading retires selection and releases the matching fence once outcome bookkeeping is complete.

`prepareReplacement` admits and stores the immutable candidate in the trusted page without changing current catalogue/temporary state. Bind it to operation/session, exact held revision/epoch and the candidate UUID already previewed natively. A commit must name that exact prepared candidate; a stale preparation cannot authorise replacement of the currently selected preview. Native Replace explicitly says it replaces only the current in-memory library and clears its temporary selections, search/comparison state; it never overwrites a saved file. Dirty state adds an unsaved-loss warning and Cancel so the user may save first.

`commitReplacement` checks the same operation/fence and unchanged revision/epoch. Prepare all fallible parsing/data work first, then commit logical state once, advance revision/epoch, clear the disclosed temporary state and mark catalogue clean. Record the committed result before rendering. A render failure after logical commit returns committed with view blocked; it is not rollback. Lost replies are queried with the same nonce. Repeated Replace cannot apply twice; Cancel arriving after commit reports committed, never “unchanged”. Before commit, Cancel/failed preparation retains old records, selections, search/comparison and focus exactly.

## 7. Evidence and publication gates

Preserve 123 native XCTest plus 6 differential/6 parser, 22 codec/4,102 encoding cases and existing standalone DOM/asset checks. Add tests for every state/decoder branch above, including:

1. Two examples, edited labels, Save acknowledgements, exact stored bytes, Open all-label preview and explicit Replace/Cancel.
2. Edit after export; draft/selection preservation; unchanged repeated Save; sample/Save/Open shortcut arbitration.
3. Lost publish result, failed storage acknowledgement, lost page reply before/after application, same-attempt checks from an uncancelled task and no duplicate files.
4. Clean/dirty with selections, unfinished edit, unknown state, repeated close/Quit, Cancel/focus restoration and unavailable default storage.
5. Immediate cancellation, navigation and close at every await; stale row/read/replacement; Replace/Cancel race; lost commit reply and committed-render-failed classification.
6. Complete stable 0/1/64/65/256-row paging, malformed/changed/symlink candidate, same-date rows, pending/unknown accounting, bounds, zero/32-record preview.
7. Wrong version/session/nonce/fence/revision/epoch; extra/missing/wrong-type fields; exhausted histories/counters; hostile labels and exact multibyte boundaries.

Actual hosted AppKit/WebKit tests use genuine native pointer/keyboard dispatch and original screenshots of Save result, full selected preview, Replace/Cancel, close decisions, uncertainty/failure, long labels and narrow geometry. Inspect original pixels, not opacity alone. Existing normal-executable empty startup/Quit remains required; controller/store reconstruction is never labelled a persistent application relaunch.

Before publication: independently review frozen source and bounds, then root approval. Before acceptance: actual owned macOS execution, independent source/log/original-pixel closeout, exact-final-head checks and guarded integration. The revised contract was accepted before authoring; frozen-source review is still required before publishing the interaction candidate for owned macOS checks. No test or code review grants production storage, signed entitlements, user-device/source access or release authority.

## Local implementation checkpoint (not native acceptance)

The current source introduces a fixed-operation native client with an exact v2 decoder, an injection-only interaction owner, native Save/Open controls and a complete bounded version chooser. The ordinary executable passes no storage injection and visibly disables Save/Open. A storage actor admits one interaction for its lifetime, even through distinct injection wrappers. The in-memory atomic claim is never reset; this is not a cross-process/root-wide lock or production container admission.

The shared owner reserves each native intent before an await and gates the existing sample session as well as persistence controls. Close during an unfinished sample or an unresolved operation exposes an explicit unconfirmed-work decision instead of inferring cleanliness. Close during active storage work cannot discard until that operation returns and its result is classified. A normal idle Close acquires the page mutation fence and captures draft/selection/catalogue loss. Keep restores the held page focus; an unfinished draft has only the return-to-edit action. Successful Save never silently clears temporary selections.

Layered source tests cover the strict decoder, exact UTF-8 boundary, same-attempt publication/acknowledgement uncertainty, later edits, Close/selection/draft preservation, lost Open preparation/commit replies, selected-read cancellation, native admission and complete 0/1/64/65/256-row paging. A selected candidate projects every one of up to 32 labels and historical gap/date claims into inert native text. The chooser uses 64-row pages only after complete bounded listing. Tests distinguish direct data setup from genuine AppKit pointer/keyboard journeys; no programmatic DOM click is counted as native interaction acceptance.

The authored full UI journey uses the real window and fixed examples with one fresh owned storage root. Eight new original captures are requested alongside the preserved six application and five WebKit originals, using the same actual-ancestor/raw-alpha/native-dimension criterion. No pixels have been produced or accepted for this source yet. Actions retention remains 14 days and no permanent screenshot archive is claimed.

Production storage admission and actual Save/Quit/process relaunch remain unimplemented. No normal executable argument, environment value, imported JSON or automatic Application Support lookup can activate the injected path. Real-folder selection and signed entitlements remain separate later gates.


## Frozen-source review repair checkpoint

The first 33-path freeze received an independent changes-required source review. The successor corrects actor-identity ownership (not just a wrapper bit), classifies rejected selected bytes separately from a possibly installed page candidate, and refreshes the same Close fence after saved-result reconciliation. Unconfirmed Close exposes Check/Keep instead of an inapplicable Save. Lost preparation or cancellation without a sent replacement offers Cancel rather than a no-op result query. Retained-file terminal wording is now truthful.

An additional author audit makes the 128-preview limit explicit: version buttons disable when exhausted, the final candidate remains available for Replace, and Cancel/reopen is the stated way to start a new bounded operation. No history is evicted. Eight added regression methods cover distinct-wrapper/retired-actor refusal, malformed and changed selected files, lost cancellation, lost Save acknowledgement before/after apply with/without selections, failed Close-status refresh, native recovery controls and the exact preview limit. The candidate authors 153 XCTest methods, preserving all 123 baseline identities. These Swift methods have not compiled or run; the repaired freeze requires independent recheck, then actual owned macOS and original-pixel gates.
