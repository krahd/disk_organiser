# Ordinary application persistence: implementation contract v2

10 October 2026. Revises plan `10129bd755ed28b4e9cdbe0e87e9327734e872afe6080694258e5a9823f4daa7` after independent OP-1–OP-4 review. Proposed source work only until separately approved. PR26 is merged at `26f6e67194af2ec10bac31b6594ac89a79bc8380`; its actual-main verification is being tracked separately.

## Product outcome and authority

Wire the ordinary preview application's native Save/Open controls to one fixed app-data home, lazily on an explicit Save/Open action. A person can save versions and find them again without looking for JSON files. Empty startup performs no library read/create. Save/Open copy says “Saved library versions on this Mac”; sample sources and unauthenticated historical records stay clearly identified. No separate technical enable-storage form is required.

This is an unsandboxed development app's Application Support data, **not** a signed container. Source authoring/compilation and owned temporary tests do not authorise running this path on the user's Mac. No user source folder, picker, bookmark, entitlement, signing, migration, provider or destructive operation is added.

## OP-1: fixed namespace and initialized-root admission

The production resolver calls Foundation's per-user Application Support lookup with creation disabled. It supplies no argv/environment/document/URL/JavaScript/picker override. If that standard parent is absent or unsupported, report storage unavailable without creating unrelated ancestors. Tests inject an internal already-open fresh owned parent capability, below this resolver and above the same namespace factory implementation.

Under that single parent descriptor, the only names are:

- Final directory: `Disk Organiser Preview`.
- Fixed setup directory: `.disk-organiser-preview-setup-v1`.
- Inside either recognized directory: `home.json`, `library.lock`, and `versions` only.
- `home.json`: at most 512 UTF-8 bytes, exact schema `disk-organiser/app-library-home/v1`, a canonical instance UUID, and canonical decimal device/inode strings identifying the created home directory. No extra fields, BOM, duplicate keys or unsupported versions.
- `library.lock`: fixed empty regular file; no payload and no truncation.
- `versions`: the existing actor's bounded version directory, not a new file format. Keep 4-MiB catalogue, 256-entry and 64-MiB aggregate limits.

Open each path component using no-follow directory descriptors. Distinguish normal OS/user ancestors from the app-owned subtree: ancestors need legitimate directory/address/ownership admission, not a blanket0700 check. The app-owned directories require owner UID matching the process, exact private mode0700 and expected types; metadata leaves require0600, regular type, one link and their byte bounds. Unsupported ACL/privacy metadata must fail closed if it prevents the claimed private-root admission; do not silently repair permissions, ownership or ACLs. The implementation review must bind those platform checks to actual APIs. No signed-container or protection-from-every-same-user-process claim is made.

A pre-existing final directory is admitted only if all three fixed entries, the strict initialized marker, expected root identity and lease validate. An unmarked/malformed/unexpected app-named directory is preserved and refused. The marker recognizes this format/initialization, not cryptographic authenticity of imported catalogue data or immunity from another same-user process. Inspect at most four root entries to detect unexpected content; never traverse unrelated children.

### Initialization and interruption table

Missing-library **Open creates nothing**, including no setup directory, marker, versions root or lock. If setup exists without a final home, report incomplete setup and leave it untouched; only an explicit Save may initialize or recover recognized setup.

For first Save:

1. Confirm final and setup address states under the held parent. Create the one fixed setup directory exclusively. Retain its identity and a same-attempt capability; no UUID staging namespaces.
2. Create `library.lock` exclusively with close-on-exec and acquire the nonblocking lease. Create `versions` exclusively. Create the complete bounded `home.json` exclusively, read it back, then flush the marker and setup directory. No catalogue save has occurred.
3. Publish the whole setup directory at the final name with no-replace rename, then flush/revalidate the parent and final named identity. Admit the actor only after this succeeds and all guard checks hold.
4. If final appears concurrently, never replace it. Preserve the current setup object and report conflict/in-use. If both final and setup exist, refuse ambiguous initialization rather than silently choosing or removing one.

| Observed state after interruption | Allowed next action |
| --- | --- |
| Neither namespace exists | Explicit Save may create the fixed setup; Open stays non-creating. |
| Same-process freshly created setup, incomplete marker | Its retained same-attempt capability may resume only its known exclusive files after identity checks, or preserve/refuse; never overwrite an unexpected leaf. |
| Pre-existing setup without a valid complete marker | Preserve/refuse with an incomplete-setup message. Do not adopt because its name/mode looks right. No automatic cleanup. |
| Valid complete setup, empty versions, final absent | Explicit Save may acquire the exact existing lease, revalidate and finish the same no-replace publication. |
| Valid final only | Open existing exact lease/home/versions identities; no initialization write. |
| Both namespaces, malformed marker, extra root entries, address replacement or foreign permissions | Preserve/refuse. No second namespace, deletion, migration, chmod or fallback. |

A failed flush/publication with an uncertain address retains the same setup attempt and checks its exact identities before Retry. Factory setup success never clears page dirty state or produces a catalogue-save acknowledgement. A pre-marker crash can leave a fixed refused directory that requires a separately authorised recovery action; the UI must disclose that rather than silently claim recovery. Repeated retries cannot accumulate more namespaces.

## OP-2: lease ownership and retirement

The factory owns the exact empty lock-file descriptor. Validate owner/type/mode/link count/zero size/CLOEXEC and the named identity before `flock(LOCK_EX | LOCK_NB)`. Never unlink, recreate, truncate, duplicate or hand the lease descriptor to another process to resolve contention. Keep its descriptor in one reference-owned lease object transferred with the storage capability, not in each injection wrapper.

Before actor operations, validate the retained parent/final/versions address identities and the named lock identity against their held descriptors. Replacement fails closed. Hold the lease throughout listing, preview, Save, retained uncertain results and reconciliation, including when UI errors occur. Secondary wrappers cannot claim the same actor; a second independently opened actor/process gets a useful in-use error with Retry/Keep working and no page loss.

Retirement synchronously fences the UI generation, prevents new storage calls and schedules actor closure after already-enqueued operations. Release the lease only after no owned actor operation can issue more filesystem work. Close must not create a successor owner until that retirement completes. OS process exit releases its descriptors; actual child-process tests must establish later re-admission. Advisory flock coordinates cooperating instances only. [Apple's flock reference](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html) also documents shared references across fork/dup, which this capability avoids.

## OP-3: lazy bootstrap and visible recovery

Keep storage availability separate from Save outcome. The provider states are `unresolved`, `resolving(intent, generation)`, `missing`, `ready(actor)`, `blockedBeforeSave(reason)`, `retiring`, and `retired`. Reserve the existing native interaction flight synchronously before awaiting the factory. Only a matching window/session/operation generation may install its result. A stale result is closed, never attached to a successor window.

| Intent/state | Page and native behaviour |
| --- | --- |
| Empty launch/unresolved | Save and Open are discoverable. Explain app-local versions. No disk resolution or claim that anything is saved. |
| Save bootstrap | Show brief “Opening saved library storage”; prevent another native operation. Preserve the live page and edits. Capture the current revision only after actor admission, using the existing Save protocol. |
| Open bootstrap | Install the existing Open mutation fence before factory work; preserve its exact loss/selection/draft/focus snapshot. Missing or failed admission cancels that fence without discarding current work. |
| Missing Open | Show “No saved library versions yet”; offer Cancel/Save later. It performs zero creations. |
| Pre-save refusal or in-use | No Check-saved action, no clean-state acknowledgement. Retry repeats bounded admission; Keep working preserves the page. |
| Cancel before factory creation | Fence the generation; create nothing. Return after the outstanding bounded bootstrap retires. |
| Cancel after setup metadata/actor admission but before Save invocation | Retain permitted metadata, retire any returned capability/lease and preserve page state. Do not begin catalogue Save. |
| Close during bootstrap | Request cancellation, finish bounded retirement, then run the normal fresh Close-loss decision. Do not turn Close into an implicit retry or leave an endless spinner. |
| Save invoked or publication outcome uncertain | Enter the existing PR26 Save outcome/reconciliation states. Same-attempt Check applies; no new factory/save attempt, false Cancel success or forced clean close. |
| Window retired | Late factory/page results close unused capabilities and cannot resume work or acquire a successor lease. |

Use bounded cancellation checkpoints before metadata creation and publication. Bootstrap failure retains only the known fixed app-data objects, never a selected source. Do not evict an uncertain Save to make a new operation possible. Draft/selection/focus preservation and later-revision dirtiness remain inherited requirements.

## OP-4: owned-only process and UI proof

The ordinary executable gets **no** root override in argv, environment, document open, JavaScript or URL handling. Default-path resolution remains lazy and unexecuted during its existing empty-startup/normal-Quit CI test.

Add a dedicated **test-only process probe**, compiled from test resources by the owned macOS validation lane and absent from the ordinary application entry point/product. It may receive only a parent-test-owned inherited directory capability and fixed operation/receipt pipes; it has no arbitrary path resolver or source-folder command. Parent tests create that root freshly, bind expected descriptor identity/nonce and preserve adjacent sentinels. The exact build/link/resource separation and inherited-descriptor handshake must receive frozen-source review before publication.

The probe exercises the same app-data factory and storage actor below the OS resolver. One child creates/saves a fixed two-location fixture and holds the lease; a second child must be refused without changing bytes. After normal first-child exit, a fresh child must reopen the same version bytes. A separately isolated forced child exit must release the lease, after which another fresh process re-admits the unchanged owned data. Verify exact child identities, bounded receipts/timeouts and outcomes; a launch/quit request or actor reconstruction is insufficient.

The existing real AppKit/WebKit harness uses the same lazy ordinary-app wiring with the internal fresh-parent provider. It tests native Save/Open/Replace/Cancel/Close, missing Open, pre-save in-use/error controls, edits during bootstrap, cancellation at each checkpoint, stale completion, lost Save acknowledgements and explicit loss. The process probe proves owned storage lifetime, not a default-path UI relaunch. Do not merge those two claims.

Required fixture matrix also includes every initialization-table state; zero creations for absent Open; marker/lock/versions symlink or replacement; malformed/oversized marker; extra entries; wrong owner/mode/unsupported ACL state; exclusive-create/flush/no-replace failures; held-lock contention; duplicate wrapper/lifetime refusal; size/entry exhaustion; and unchanged adjacent sentinels. Where wrong-owner or ACL states cannot be created by the unprivileged owned fixture, label injected-metadata refusal tests as synthetic rather than claiming native filesystem coverage. Do not acquire privileges or change permissions outside owned fixtures. Preserve the 153 existing native methods and six differential/six parser gates.

## Gates and source mapping

Freeze and independently review factory/admission, bootstrap state transitions, process-probe separation and all tests before publication. Require actual macOS source compilation, owned process/UI tests and original error/recovery pixels; then root evidence review, normal guarded PR integration and actual-main checks. No default user Application Support or external drive is touched during development tests.

At current source, `PreviewApplication.swift` supplies no storage injection; `LibraryInteraction.swift` has a one-use owned lease; `LibraryStorage.swift` admits only `.ownedFixture`. Change that ordinary-product absence deliberately with distinct app-data admission, not an enum relabelling shortcut. Use the existing descriptor storage engine and strict catalogue codec. The native observer and legacy backend remain untouched.

After this tranche, permissible claims are: ordinary Save/Open source wired and compiled, ordinary empty process startup/Quit exercised, owned-root UI and actual process persistence verified. Actual default-path user-device relaunch, signed-container/distribution and real folder/drive use require their own authority and verification.


## Approved authoring and current implementation candidate

The independently reviewed v2 contract was approved for source authoring on 10 October 2026. Its original approved bytes remain identified by SHA-256 `cbf464f49b3837ff9e7e859e7ac708ae813e92dac80b26da854f66bc5aec20bf`. PR26 actual-main `26f6e671` has since passed all six workflows with 153 native methods plus six differential/six parser cases. The ordinary preview and separate process probe have since compiled at `4a11d4f2`; XCTest compilation remains blocked as recorded below. Contract review is not runtime acceptance.

- `ApplicationLibraryIO` and `ApplicationLibraryFactory` implement the fixed namespace. Exact marker bytes, no-follow descriptors, private modes/UID/links, ACL inspection, same-object checks and a retained advisory lease precede actor admission. An absent Open creates nothing. The only setup namespace is fixed; complete empty setup can resume explicit Save, while unrecognised partial setup is preserved/refused without repair or cleanup.
- `LibraryStorageBootstrap` separates availability from Save outcome. Native operations reserve their flight before suspension. Save captures after storage admission; Cancel before invocation retires a newly prepared actor and retains setup metadata. Open fences before admission and releases that fence on absence/failure/cancellation. Close during bootstrap cancels and then obtains fresh loss state. Existing uncertain Save still uses same-attempt Check, never a factory retry.
- `PreviewApplication` selects `application-data` presentation and supplies the lazy factory. The fixed bridge mode is only UI/data configuration. It carries no native command interface, path or permission and does not authenticate imported records. Existing `owned-storage` tests and `temporary` mode remain distinct. All saved v1 schemas are unchanged.
- The separate `Validation/OwnedApplicationProbe` executable is compiled by `build_owned_application_probe.py` from its test-only source, linked against the exact debug desktop objects. It is absent from `Package.swift` products and ordinary application argument handling. `posix_spawn` maps only the parent's fresh directory capability to descriptor 3 and private command/receipt pipes; `POSIX_SPAWN_CLOEXEC_DEFAULT` closes other inherited descriptors. The child checks a nonce and expected device/inode, restores CLOEXEC on its root, and rejects a deliberately non-inherited high-numbered owned sentinel descriptor. The lease is acquired afresh inside each child and is never inherited or duplicated.
- The child accepts only fixed save/hold/open/close operations and its fixed two-location owned fixture. Receipts are bounded to 512 bytes each and 2 KiB total, waits are bounded, and tests address only their own unreaped PIDs. Normal exit, a contending second process, fresh-process byte equality and forced owned-child exit have distinct assertions. None proves default-path UI relaunch.
- New native UI capture names 90–96 cover ordinary-app wording, missing library, in-use refusal, cancellation, Save and reopened content. They remain original named native regions/WebKit viewports under the existing alpha, geometry and trusted-event gates, with no compositing or screen permission. No new pixels exist yet.

### Platform API basis and honest limits

The private-subtree ACL check uses successful `fstatx_np` plus `filesec_query_property`, so absence of an ACL is distinguished from unsupported/failed inspection. Apple's [extended stat implementation](https://github.com/apple-oss-distributions/Libc/blob/71bbe350ab79eef58113991d817ccc6165061a64/sys/statx_np.c) and [filesec property implementation](https://github.com/apple-oss-distributions/Libc/blob/71bbe350ab79eef58113991d817ccc6165061a64/gen/filesec.c) establish that distinction. A returned ACL must be valid and empty; Darwin's [ACL iterator](https://github.com/apple-oss-distributions/Libc/blob/71bbe350ab79eef58113991d817ccc6165061a64/posix1e/acl_entry.c) reports no first entry as `-1/EINVAL`. Wrong-owner and unsupported-ACL fault tests are explicitly synthetic; they do not claim an unprivileged test created those actual platform states.

Apple's [spawn implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exec.c) marks only explicit destination descriptors for inheritance under `POSIX_SPAWN_CLOEXEC_DEFAULT`; its [public flag definition](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/spawn.h) is used without an alternative fallback. These source checks were made on 10 October 2026; actual SDK compile/runtime assertions remain required.

[Apple's fsync reference](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html) cautions that OS flush is not a guarantee against device power loss. This preview does not claim transactional power-loss durability, universal same-user hostile-writer defence, signed-container protection or backups. Cooperative cancellation checks syscall admission; it does not interrupt an already-entered filesystem call. No user Application Support path or source drive may be exercised by these tests.


### First source-review corrections, before execution

The first 30-path source freeze preserved all 153 baseline identities and authored 36 additional methods. Independent review requested four fixes before publication: treat filesec ACL presence as zero/nonzero rather than exactly one; prove second-window reopening after the real first-window native Close without directly releasing its actor; bound failure cleanup and record reaping only after observing the exact PID; and repair the unified patch's missing final-newline marker. The original source/invalid patch remain separately preserved in the review packet.

The successor adds four actual Darwin API tests using in-memory ACL/filesec objects and fresh-owned descriptor absence/error, plus one bounded cleanup test: **194 authored methods**, with native compilation/execution still pending. The memory tests do not alter filesystem ACLs or claim actual on-disk present-empty/nonempty ACL coverage. The native UI acceptance path now drives Close and observes a successful ordinary Open; direct actor closure remains outside that proof. Child failure cleanup polls only its own PID with a three-second deadline, treats ECHILD/error as unconfirmed rather than a fabricated reap, and is never counted as normal exit. No other permission or source capability is added.

### First hosted compilation and narrow test correction

Both [push 38046430643](https://github.com/krahd/disk_organiser/actions/runs/38046430643) and [PR 38046449751](https://github.com/krahd/disk_organiser/actions/runs/38046449751) compile the preview and separate owned-capability process probe at source `4a11d4f249a5c7f5a6832022e0bc9bfcf69bef5a`. XCTest compilation fails because `ApplicationLibraryUITests.swift` calls `assertFirstVersionAtTop`, declared private in a different test extension file. No XCTest methods or process/UI flows execute, no new original captures are produced, and downstream six differential/six parser checks are skipped. The successor makes this test-only helper internal without changing its assertions or any runtime, asset, workflow or process-probe byte. Native effectiveness is still unverified.
