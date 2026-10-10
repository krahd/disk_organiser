# Disk Organiser – Project Status

Last updated: 2026-10-10 03:40

## Native application slice 1: development/sample source checkpoint

- PR23 is merged at `2952fa64db55944096cc80777964e24a187857c0`, tree `1e25f6784d8060ce3111f9b2d4c5f2e2f88da768`. All twelve final-head checks and all six actual-main workflows passed. Native [38017300172](https://github.com/krahd/disk_organiser/actions/runs/38017300172) verifies the actual merged checkout and 64 XCTest + six differential + six parser cases; catalogue [38017300212](https://github.com/krahd/disk_organiser/actions/runs/38017300212) verifies ten Chromium journeys. Aggregate [38017300327](https://github.com/krahd/disk_organiser/actions/runs/38017300327) retains 709 Linux backend, Windows 607 passed/102 existing skips, 665 Jest and 27 existing browser journeys. Its original source/pixel attribution and 14-day artifact limitation remain below.
- First hosted source `66bed5675a6cbc0782d8a827e009d792df69ff7f` compiles the sample executable and all tests with pinned Xcode 16.4. Both native runs execute 82 cases: 81 pass; one separate-process readiness case fails with two assertions after its 20-second bound. The 59 core, five original WebKit, 16 new native window/lifecycle cases and unknown-argument rejection pass. Normal Quit is not reached; downstream six differential/six parser checks are skipped. All ten non-native workflows pass. The preserved failure does not identify which child-startup phase stopped. A narrow fixed-phase/boolean diagnostic is prepared; readiness, timing and normal-Quit requirements are unchanged.
- Diagnostic source `32c88e958af8cd5394f4cbbf9e1044dcd2ad3ece` preserves the same failure in the push run: the exact owned child is registered, finished launching and active, but the test collects zero bytes, including the synchronous entry receipt. This suggests a receipt-collection problem; it does not prove the child window is ready. A test-only successor uses one 1-KiB nonblocking read on its own pipe, retains the 4-KiB aggregate bound and adds short-write-before-EOF and overflow regressions. It does not alter application activation, readiness, timing or normal-Quit requirements. All prior 82 tests remain; 84 are now required. This repair is not yet run.
- Approved next scope is a coherent native library window, explicit owned-sample selection/scope/progress/cancel, then separately reviewed bounded app-owned Save/Open/relaunch. The [canonical source plan](docs/drive-administration/NATIVE-APPLICATION.md) preserves the later signed-picker and user-device gates. The failed process gate prevents application acceptance despite the successful compile and other native cases.
- Added `DiskInventoryDesktop` and the explicit `DiskOrganiserPreview` sample executable. The app entry rejects external arguments/document/URL requests; its only provider reads two fixed bundled owned-example JSON resources. It does not depend on the observer core. Real directory reads still use private fresh-fixture constructors in tests only. The core’s five source files, all prior 59 core tests, strict v1 formats and authority rules remain unchanged.
- Extracted the data-only WebKit host/resources into that shared desktop module. Existing five native WebKit tests retain their event/lifecycle/security assertions; acknowledgement barriers, event injection and screenshot writers remain in tests. The narrow asset allowlist now checks seven frontend assets plus two fixed example files outside the WebKit read root. Shared embedded copy says development preview without claiming a live connection.
- The native shell starts with an empty library and prominent sample/real-folder/Save/Open limits. Native sample selection and scope review precede preparation; Cancel, repeated actions, late completion and window close have generation fences. Records remain temporary, with explicit discard confirmation on dirty close. No fake scan percentage or real source permission is shown. “Choose my folder” is disabled with its unavailable reason.
- The application’s fixed WebKit blocker uses a newly created private temporary framework-cache directory. This cache is not a saved catalogue or source grant; OS/framework persistence is disclosed. No source traversal, content reads, catalogue persistence, arbitrary file opening, provider, native operation interface or entitlement is connected.
- Independent initial source review found a pre-provider cancellation gap and synchronous Quit re-entry; both are repaired locally. The new pre-call/current-generation fence prevents provider invocation after immediate Cancel/Close, and the final termination request is deferred until the current delegate returns. Native focus restoration waits for sheets and does not steal an active close question. Eighteen new native application cases are authored, including those regressions, delayed-stage/Add races, actual Keep/Discard and focus paths, startup gating and bounded separate-process startup/normal Quit/unknown-argument rejection. Together with the prior 64 cases, 82 XCTest cases are required. The Linux workspace cannot execute native cases; actual hosted results are recorded above.
- The process test launches only the package’s just-built sample executable, proves actual empty-view/window readiness via fixed non-sensitive receipts and requests normal quit only for its verified live child. Bounded failure cleanup is never counted as a pass. No global app enumeration, source argument or OS permission is introduced. Six original named-view/viewport captures are planned, including the native discard confirmation; there is no whole-screen/composite claim. Tests use fresh owned sources or fixed public examples.
- Local unchanged frontend checks pass 665 Jest, 39 catalogue DOM, 16 bridge DOM and formatting; seven canonical view assets and two example files match. Independent source review accepted the exact candidate before publication. The unresolved process gate, downstream differential/parser checks, hosted evidence closeout and original visual inspection remain required before acceptance. This source is a development/sample preview, not a usable real-folder application. Complete slice 1, then bounded Save/Open and signed-picker feasibility rather than indefinite sample-only polishing.

The application source has no observer dependency. Only tests can construct and read owned source folders; the shipped sample provider supplies fixed bytes to the same presentation.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1020 175" role="img" aria-labelledby="app-title app-desc">
  <title id="app-title">Development library application boundary</title>
  <desc id="app-desc">A native sample selector and scope review chooses a fixed example. Generation fencing passes bounded bytes to the shared catalogue. A separate owned test provider exercises actual core metadata. No production source picker or save is connected.</desc>
  <defs><marker id="app-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52657a"/></marker></defs>
  <rect x="15" y="30" width="230" height="110" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="130" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Native library window</text>
  <text x="130" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Sample selector + scope</text>
  <text x="130" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">No live folder picker</text>
  <line x1="245" y1="85" x2="280" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#app-arrow)"/>
  <rect x="280" y="30" width="205" height="110" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="382" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Fixed example bytes</text>
  <text x="382" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Tests: owned sources only</text>
  <text x="382" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">No source capability</text>
  <line x1="485" y1="85" x2="520" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#app-arrow)"/>
  <rect x="520" y="30" width="205" height="110" rx="10" fill="#f3f1fb" stroke="#52657a"/>
  <text x="622" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Session generation</text>
  <text x="622" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Prepare / Cancel / Review</text>
  <text x="622" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">Retire late completion</text>
  <line x1="725" y1="85" x2="760" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#app-arrow)"/>
  <rect x="760" y="30" width="245" height="110" rx="10" fill="#f1f8f2" stroke="#52657a"/>
  <text x="882" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Shared visual catalogue</text>
  <text x="882" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Preview + separate Add</text>
  <text x="882" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">Temporary unsaved library</text>
</svg>

## Previous owned native visual handoff checkpoint

- Successful source `356ff01aa663d8cd3504f98bcc4f110364d6a089` passes all twelve push/PR workflow runs. Native [push](https://github.com/krahd/disk_organiser/actions/runs/38013732010) checks out that exact source; native [PR](https://github.com/krahd/disk_organiser/actions/runs/38013734331) checks out `f096b7a82a86b742ab635ab039a9ed9e03c12c2a`, with the same tree `245dce0ca035faa0353bdd710ef71c8aaeebd2ba`. Both pass all 64 XCTest cases (59 core + five WebKit), six independent native/Python differential and six unchanged-parser/catalogue cases. Pinned Xcode 16.4/16F6, SDK 15.5 and Swift 6.1.2 are verified; APFS invalid-name refusal remains an explicit limitation.
- The bounded own-app event drain establishes active/key/visible readiness after three queued events. Genuine in-process AppKit pointer Add/comparison/close and Escape cancellation then pass with trusted WebKit event traces, checked native/DOM hit coordinates, preserved retirement fences and focus return. Earlier failed logs/partial images remain failure evidence. No JS-click substitution, forced interaction, physical-mouse or user-device claim is made.
- Both native artifacts contain five byte-identical original PNGs (468,477 image bytes) with all hashes verified. Actual viewports are 1024×656 and 390×656 after runner window clamping; no larger/full-page capture is claimed. Implementation inspection covers all five views; root evidence review covers desktop comparison/narrow uncertainty. Independent final evidence review accepts the exact source, both native logs and all five originals, with no blocking implementation or visual defect. This is an evidence review, not another hardware test. [Detailed evidence, original artifact links, hashes and limits](native/DiskInventoryCore/OWNED-PREVIEW.md#hosted-owned-preview-validation--10-october-2026).
- Catalogue CI passes 115 model + 39 DOM + 16 bridge groups on Linux and Windows and ten browser journeys. Aggregate CI passes Linux 709 backend, Windows 607 passed/102 existing skips, 665 Jest, OpenAPI 44, audits/formatting and 27 existing browser journeys. This closeout changes documentation only; all successful runtime, test, asset and workflow blobs remain unchanged. Final-head checks and guarded actual-main verification remain open. No picker, grant, entitlement, application product, user-drive read, native save or file operation is added.

### Historical diagnostic checkpoints (superseded)

- Source `9d55bd54` also compiled and confirmed that the bootstrap executed, but the owned XCTest window remained inactive/non-key, so three pointer cases stopped before dispatch. The bounded own-application queue diagnostic was then prepared without weakening readiness or input assertions. That checkpoint did not establish native visual acceptance; the successful result above supersedes it.

- Diagnostic source `447380fe` compiled; its PR native run retained 59 core and two WebKit passes, while all three pointer flows failed the new pre-dispatch guard with `active=false`, `key=false`, `visible=true`. No pointer success was established. A test-only AppKit launch bootstrap was then prepared with launch-file/default and delegate refusal guards; it was unverified at that checkpoint.

- First hosted source `f60ad3b9a949b5ed308ffc1ade4a2c60c525ea1f` compiled on the pinned Xcode/SDK. All 59 core and two new WebKit security/lifecycle cases passed, but three native pointer Add flows failed; downstream differential/parser checks were skipped and are not counted. The failed logs and partial original preview PNGs remain preserved. The harness-only event-routing/activation repair was prepared next; its result was unknown at that checkpoint.

### Implementation and prior validation context

- Added a test-only AppKit/WebKit catalogue host under `DiskInventoryPreviewTests`. It receives only fresh owned-core snapshot bytes after descriptor release and renders the exact bundled catalogue through fixed structured arguments. There is no app product/executable, picker, source grant, entitlement, persistent access, native save, file operation or JavaScript-to-native command handler. Existing core production source and all v1 formats are unchanged.
- The standalone catalogue remains empty-first with no bridge exposed. Embedded presentation explicitly hides/disables unsupported Open/Save/manual export and marks edits temporary. Native delivery shares the strict parser and existing Add/Cancel admission; wrong version/session, oversized/wrong-schema input, busy edits and replay reject. A bounded 128-ID view session and matching retirement fence preserve prior records and newer edits. Native session ownership never makes imported JSON trusted.
- The seven bundled assets have exact canonical parity and an explicit update command. The nonpersistent view has a narrow resource read root, a fixed network blocker, unchanged CSP and fail-closed navigation/window/upload/drop rules. The test harness prepares WebKit's compiled-rule cache in a fresh owned temporary directory; the host has no filesystem writer. Framework/OS internal file activity is not claimed absent.
- Initial local source checks passed 16 new bridge DOM groups, 39 existing catalogue DOM checks, 665 Jest and frontend formatting. Nine supported local HTTP Chromium journeys also pass; the unchanged direct-file case remains locally administrator-blocked and is not counted. All five new macOS UI/lifecycle tests compile and run at `f60ad3b9`; two pass and three pointer-driven flows fail as recorded above. The existing 59 native core tests and six differential/parser cases remain required. Independent boundary review and actual hosted WebKit event/pixel evidence were still open at that initial checkpoint; the successful source and evidence above supersede that state. Final-head/main integration checks remain open. Local JavaScript tests alone establish no native success. [Owned preview boundary and evidence plan](native/DiskInventoryCore/OWNED-PREVIEW.md).
- Previous comparison PR22 is now merged at `9f890d83bb25e2d5f23496dc687d4a54acc4ed3e`; all six actual-main workflows passed. Native [38008947846](https://github.com/krahd/disk_organiser/actions/runs/38008947846) confirms that exact checkout and 59 + 6 + 6 results; catalogue [38008947834](https://github.com/krahd/disk_organiser/actions/runs/38008947834) confirms ten browser journeys. Its final documentation head `b99bf700b4c53e5a97b33ed302471dc8ec873fa4` passed all twelve push/PR runs, and the merged tree equals the reviewed final tree `f5947d6a3de4834ed08d9a96e416eb5319c47098`.

The prototype host adds a data-only view after the existing core diagram's snapshot output. No source-access or execution arrow is added; product picker/sandbox/save gates remain separate.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1020 175" role="img" aria-labelledby="preview-title preview-desc">
  <title id="preview-title">Owned native visual handoff</title>
  <desc id="preview-desc">A test creates fresh temporary sources. The existing core releases all source descriptors and returns metadata bytes. A test-only native host stages those bytes in the exact bundled catalogue. The user-visible Add or Cancel preview retains untrusted history and has no native command channel.</desc>
  <defs><marker id="preview-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52657a"/></marker></defs>
  <rect x="15" y="30" width="200" height="110" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="115" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Owned test sources</text>
  <text x="115" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Temporary fixtures</text>
  <text x="115" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">No user folder picker</text>
  <line x1="215" y1="85" x2="250" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#preview-arrow)"/>
  <rect x="250" y="30" width="205" height="110" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="352" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Existing Swift core</text>
  <text x="352" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Release before return</text>
  <text x="352" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">Bounded v1 bytes</text>
  <line x1="455" y1="85" x2="490" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#preview-arrow)"/>
  <rect x="490" y="30" width="230" height="110" rx="10" fill="#f3f1fb" stroke="#52657a"/>
  <text x="605" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Test-only native host</text>
  <text x="605" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Session + retirement fence</text>
  <text x="605" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">Structured data arguments</text>
  <line x1="720" y1="85" x2="755" y2="85" stroke="#52657a" stroke-width="2" marker-end="url(#preview-arrow)"/>
  <rect x="755" y="30" width="250" height="110" rx="10" fill="#f1f8f2" stroke="#52657a"/>
  <text x="880" y="60" text-anchor="middle" font-family="sans-serif" font-size="15">Bundled visual catalogue</text>
  <text x="880" y="88" text-anchor="middle" font-family="sans-serif" font-size="14">Untrusted preview: Add / Cancel</text>
  <text x="880" y="114" text-anchor="middle" font-family="sans-serif" font-size="14">No native command channel</text>
</svg>

## Historical location comparison checkpoint

- Added an explicit two-record comparison to the existing visual catalogue. Users choose the pair, see recorded overlap/differences and decide which labelled location to reconnect and check. The default view leads with plain descriptions and source context; raw source dates, gap reasons and exact decimal sizes remain available in details.
- The pure bounded model groups all exact relative child paths into one-sided listings, matching listed details, differing recorded details or uncertain/unsupported records. Uncertain ancestors keep descendants uncertain. Same names or logical sizes never imply identical contents, physical-drive identity, verified copies, deletion, live presence or backup protection. Folder-kind agreement does not claim matching contents.
- Inputs pass the unchanged v1 catalogue validator. The full union (at most 3,998 children) is counted before 50-row pagination. Record numbers disambiguate duplicate labels; left/right do not infer chronology. Cancelling/closing preserves records and project selection; confirmed catalogue replacement retires comparison state. No schema, source/provenance, native-runtime, provider, drive-read or operation authority changes.
- Local checks pass 665 Jest cases (27 new comparison cases), 39 catalogue DOM checks and full frontend formatting. The first aggregate local attempt lacked unchanged manual-planning fixtures; fetching the pinned baseline fixtures restored all 665 passes. Initial local Chromium launch stopped because the locked browser was absent. After installing the existing locked version in the owned workspace, nine Chromium journeys pass, including both comparison flows; twenty original PNGs are preserved. The unchanged direct `file:` launch case is blocked by the browser administrator and remains unverified locally. No security workaround, test change or full local browser pass is claimed. The full hosted result and independent review are recorded below. [Comparison contract](docs/INVENTORY-CATALOGUE.md#compare-two-saved-locations).


- Independent source review accepts the frozen eleven-file candidate after rerunning 665 Jest cases, 39 DOM checks, formatting, eleven additional adversarial groups and both new HTTP browser journeys. The additional checks include exact Unicode/case paths, invalid/unknown dates, stale reads, cancelled replacement, byte-identical exports, stable record IDs and all 3,998 possible children across 80 pages. It found no remaining blocking defect. This is source/browser evidence review, not a user-drive or assistive-technology test.
- Accepted source `ce3b8442aff0bc1fc6d361100147ed0e9ae96079` passes all twelve push/PR workflow runs (six workflows across both events). The [catalogue run](https://github.com/krahd/disk_organiser/actions/runs/38007040810) passes 115 model tests and 39 DOM checks on both Linux and Windows, plus all ten hosted Chromium journeys, including the unchanged direct-file case blocked locally. Its actual checkout is GitHub merge ref `cc4f65a0b1b2a59bc546cef5454b27f28408a98f`; that ref and the source head share exact tree `c2ff7705d2cea07740213bc8562a7abb279e0d77`.
- [Aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/38007040778) passes Linux 709 backend tests, Windows 607 passed/102 skipped, 665 Jest, OpenAPI44 on each OS, dependency audits, formatting and 27 existing Chromium journeys. The unchanged planner, manual workspace and synthetic UI workflows pass. Native [push](https://github.com/krahd/disk_organiser/actions/runs/38007016947) and [PR](https://github.com/krahd/disk_organiser/actions/runs/38007040796) both pass 59 XCTest, six native/Python differential and six JavaScript parser/catalogue cases. The APFS invalid-name refusal remains an explicit limitation; no skipped or unsupported case is counted as native coverage.
- Artifact `11651837465` contains 21 original PNGs (7,301,211 image bytes) with a fully verified length/hash manifest. The outer ZIP is 6,914,434 bytes, SHA-256 `0273f122c2fca399b55e4d86f4c9dd20dd0175954c9f335ce75393253dfb8c1e`. Original hosted comparison desktop, difference, expert-details, mobile, uncertainty and CSS-zoom views were inspected, along with direct-file output. Independent hosted pixel review accepts desktop, mobile uncertainty and CSS zoom; earlier independent local pixel review covered all six new views. The final plain wording, claimed dates, policy qualification, inert hostile labels, focus and readable alignment are visible. Native browser-UI zoom, OS dialogues, participant usability and assistive technology remain untested.
- This acceptance closeout changes documentation only. All runtime, fixtures, tests and workflow blobs remain exactly those of `ce3b8442`; the cited source evidence is not attributed to a later documentation head. Exact-final-head checks, current-main preservation and actual merged-main checks remain the integration gates.

The existing source/intent and native diagrams remain accurate: comparison is a second read-only presentation of admitted historical records. It adds no authority-bearing path or storage connection.

## Isolated owned native core checkpoint

- Native source `07b93c5e2f0f09746d024884681259aaf513903d` now passes all twelve push/PR workflow runs. The [native push run](https://github.com/krahd/disk_organiser/actions/runs/38003620756) checked out that exact source. The [native PR run](https://github.com/krahd/disk_organiser/actions/runs/38003624967) checked out GitHub merge ref `eebe7971a9bc0c21cde4c6a1231d32c3752a94aa`; its tree is exactly the same `a0c13a1737790f8bf2e7971da76195d16ab1f5ca`. Both compiled and passed all 59 XCTest cases with zero failures, six native/Python differential cases and six unchanged-JavaScript parser/catalogue cases. The later documentation head is not relabelled as the source of this evidence.
- Actual native toolchain: Xcode 16.4 build 16F6, macOS SDK 15.5, Apple Swift 6.1.2 (`swiftlang-6.1.2.1.2`), macOS 15.7.9 build 24G830, arm64 runner image `macos-15-arm64` / `20260907.0337.1`. The filesystem refused the deliberately invalid UTF-8 name with errno 92; synthetic invalid-UTF-8 rejection passed unconditionally. That refusal is an explicit native-case limitation, not successful invalid-name-path coverage. No native XCTest was silently skipped or substituted with a Linux walker.
- Independent source review and subsequent log/artifact evidence review found no remaining blocking Phase A defect. Evidence review is not an additional hardware test. The [six original generated fixture outputs and hash manifest](native/DiskInventoryCore/Validation/accepted-fixtures/README.md) preserve the push result in source control; they are evidence only and are never reused as oracle expectations. Original artifact `11650306815` is 2,518 bytes, SHA-256 `6314bbb58f899672cfe70976b37b75a2e58113c5d33332600bb7a614680001db`.
- Existing [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/38003624975) passes Linux 709 backend, Windows 607 passed/102 skipped, 638 Jest, OpenAPI44, dependency audits, formatting and 27 Chromium journeys. [Catalogue CI](https://github.com/krahd/disk_organiser/actions/runs/38003624976) passes its unchanged model/DOM and eight browser journeys. The existing Windows skips are not native coverage. All 244 non-STATUS baseline blobs and all native source/test/workflow blobs from the accepted source remain unchanged in this documentation/evidence closeout.
- First hosted validation at `4487071bdd40bf71ffa630c46c8009889d4058da` failed before scheduling a native job ([run 38003436006](https://github.com/krahd/disk_organiser/actions/runs/38003436006)). The workflow referenced `runner.temp` in job-level `env`, where [GitHub context rules](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability) do not allow `runner`. The fixed fixture-output value is now declared only in the four consuming steps. Native source, fixed path validation, toolchain pins and all test assertions remained unchanged. No native job ran at that initial checkpoint.
- Recovery checkpoint: all 20 originally reviewed candidate files were restored and verified against their retained per-file SHA-256 and Git blob hashes before this documentation update. The six owned Python-oracle cases and unchanged-JavaScript parser/catalogue self-checks pass again. Native compilation and all 59 XCTest methods were unexecuted at that recovery checkpoint; recovery and source review alone did not establish native runtime acceptance. The subsequent hosted results are recorded above.
- The next bridge towards native selected-folder onboarding is an isolated Swift/Darwin core and one-shot controller under `native/DiskInventoryCore/`. It has no package product, public scanner API, executable, production selection factory, AppKit/WebKit wiring, entitlement or application entry point. Only a test-target constructor creates leases from fresh owned temporary directories. Existing Python/frontend runtimes, synthetic-only adapter and all v1 formats remain unchanged.
- The bounded descriptor reader records metadata without file-content reads, hashes, writes to source or filesystem crossing. It preserves exact UTF-8 spelling, explicit partial/error evidence, root/ancestor checks, hard-link conflict invalidation and cooperative cancellation. Immutable v1 bytes are available only after source-descriptor release. No physical-drive identity, current presence, atomic snapshot, backup protection or real hardware acceptance is inferred.
- The [native onboarding contract](docs/drive-administration/NATIVE-ONBOARDING.md) records source admission, transient scope ownership, volume ambiguity, source/intent provenance and the later native catalogue handoff. Signed picker/WebKit/container save and real user-drive stages remain separate unimplemented gates. The core's injected owned-fixture class is not a production local/cloud/provider classifier.
- The dedicated read-only macOS workflow pins Xcode 16.4 build 16F6 and SDK 15.5, records actual compiler/OS/runner identity and fails if the reviewed toolchain is absent. Six independently created native/Python fixtures and the unchanged browser parser check v1 compatibility; generated fixture metadata is the only workflow artifact. No production dependency is added.
- The candidate contains 59 native XCTest methods covering owned filesystem observations, limits, syscall-result failures, exact projection, hard-link conflicts and lifecycle races. Pre-publication review found and repaired a post-guard callback race, late deadline classification, shared-lease ownership and exact errno/pointer-lifetime handling. The subsequent hosted runs above provide actual native execution evidence; source/static review alone was not counted as a compiler pass.
- Local validation currently passes six Python-oracle self-checks, the parser-harness self-check using Python-owned output, 160 unchanged disk-model/scoped-observer/snapshot tests, 88 unchanged catalogue model tests and 32 catalogue DOM checks. The assigned Linux workspace has no Swift compiler; the native compilation/test evidence comes from the separate hosted runs above. PR21 subsequently merged at `e8e9b1da43068d65a25d1caa473837fc3a39912c`; all six actual-main workflows passed, including [native run 38004698957](https://github.com/krahd/disk_organiser/actions/runs/38004698957), whose log confirms that exact checkout and the same 59 + 6 + 6 results. [Native scope and test instructions](native/DiskInventoryCore/README.md).

The native prototype is reachable only from the owned test target. The app still opens empty historical/manual workspaces; this slice creates no live user-storage connection.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 180" role="img" aria-labelledby="native-core-title native-core-desc">
  <title id="native-core-title">Isolated owned native verification flow</title>
  <desc id="native-core-desc">A test creates a temporary source and a process-local lease. The internal Swift controller observes bounded metadata, releases descriptors and returns historical JSON to independent Python and browser parser checks. No production picker is connected.</desc>
  <defs><marker id="native-core-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52657a"/></marker></defs>
  <rect x="15" y="40" width="200" height="95" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="115" y="68" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#172b40">Owned test fixture</text>
  <text x="115" y="94" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Temporary source</text>
  <text x="115" y="116" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Test-only lease factory</text>
  <line x1="215" y1="87" x2="250" y2="87" stroke="#52657a" stroke-width="2" marker-end="url(#native-core-arrow)"/>
  <rect x="250" y="25" width="240" height="125" rx="10" fill="#f3f1fb" stroke="#52657a"/>
  <text x="370" y="56" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#172b40">Internal Swift controller</text>
  <text x="370" y="83" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Bounded metadata reader</text>
  <text x="370" y="107" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">One attempt; explicit gaps</text>
  <text x="370" y="131" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Release before returning</text>
  <line x1="490" y1="87" x2="525" y2="87" stroke="#52657a" stroke-width="2" marker-end="url(#native-core-arrow)"/>
  <rect x="525" y="40" width="180" height="95" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="615" y="68" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#172b40">Snapshot v1 JSON</text>
  <text x="615" y="94" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Historical metadata</text>
  <text x="615" y="116" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">No access authority</text>
  <line x1="705" y1="87" x2="740" y2="87" stroke="#52657a" stroke-width="2" marker-end="url(#native-core-arrow)"/>
  <rect x="740" y="40" width="205" height="95" rx="10" fill="#f1f8f2" stroke="#52657a"/>
  <text x="842" y="68" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#172b40">Independent checks</text>
  <text x="842" y="94" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Python fixture oracle</text>
  <text x="842" y="116" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Unchanged JS parser</text>
</svg>

## Catalogue readability checkpoint

- A focused display-only follow-on to merged catalogue PR19 (`e08692fe05858debef3a10e3d0d40eb875ebb3ee`, all five main workflows green) replaces dense timestamps with a readable day/month/year and minute-level time. It retains the recorded offset without browser-timezone conversion; `-00:00` explicitly reports an unknown local offset. Original ISO strings, seconds, fractional seconds and offsets remain unchanged in source details, semantic time attributes, catalogue files and manual-plan notes. The same strict date validator still rejects incomplete or invalid imports; the standalone formatter returns “Date unavailable” for unsupported input.
- Project selection counts now distinguish actual files and folders in empty, singular, plural and mixed selections. Selecting a folder counts that chosen folder once, not its descendants. Internal source keys, imported claims, selection limits and overlap rules are unchanged.
- Local checks pass all 638 frontend Jest tests (88 catalogue model cases), 32 catalogue DOM checks, 43 unchanged manual-workspace DOM checks and full frontend formatting. Independent source/model/DOM review adds 11,859 calendar/offset/precision oracle cases with unchanged admission parity and 53 DOM checkpoints, without a blocking defect. No local browser execution is claimed; the existing locked-browser/process-socket limits remain.
- Accepted source `6dedfe051c6055bc481e9b0fa4158d8ada1e09db` has all ten push/PR workflow runs green. The [catalogue run](https://github.com/krahd/disk_organiser/actions/runs/37905173948) passes 88 model and 32 DOM checks on each OS plus eight Chromium journeys, including recorded offsets under a different host timezone and exact-date save/reopen. [Aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37905173983) passes Linux 709 backend, Windows 607 passed/102 skipped, 638 Jest, OpenAPI44, audits, formatting and 27 existing Chromium journeys. Existing planner, manual workspace and synthetic UI workflows pass. All 237 unaffected baseline blobs remain identical.
- Original artifact `11604460803` is 5,931,301 bytes, SHA-256 `4ebd6cf2bcd8d5615e02dd9ad6fb2e711a880ba3350ef28980b570e5ed9eef15`. All fifteen original PNG lengths and hashes verify. Independent exact-source pixel review accepts readable dates, unknown/recorded offsets, file/folder counts, raw ISO details, selected states, mobile/zoom/focus, no-match and hostile-text views. Eleven originals are byte-identical to earlier inspected passes; the remaining four were freshly inspected.
- Initial `ff84f331` passed all workflows/eight browser journeys but its full-page no-match PNG had missing offscreen text. Intermediate `faeb4c94` then failed the new full-sidebar viewport assertion because nearest scrolling clipped roughly one pixel at the image edge. Both failed evidence stages remain preserved. A test-only framing repair uses explicit top-aligned scrolling and retains strict full-visibility assertions. The accepted log records sidebar top 24.40625/bottom 771.84375 in a 1000-pixel viewport; separate real viewports fully paint both no-match/sidebar and source details. No production/CSS change or weakened assertion was used for this repair.
- Producer, snapshot/catalogue/manual schemas, fixtures, dependencies, permissions, save/export authority and all native-drive/provider/mutation/recovery gates are unchanged. [Catalogue date presentation and selection wording](docs/INVENTORY-CATALOGUE.md#readable-dates-and-selection-counts) describes the display contract. Existing diagrams remain structurally accurate and unchanged. This closeout changes documentation only and preserves every tested runtime/test/workflow blob; cited evidence is not relabelled as a later documentation head. Native browser-UI zoom, OS dialogues, assistive technology, participant usability and real-drive/backup/restore remain separate gates.

## Historical inventory catalogue and scoped overview checkpoint

- Added a separate empty-first `frontend/inventory-catalogue.html` page for historical selected-folder snapshots. Up to 32 independently labelled records share a 10,000-entry/4 MiB aggregate budget. Cards show source dates, scoped top-level groups and listed observed logical-file sizes; paginated search across saved records works without connected storage. Physical-drive identity, current presence, whole-drive capacity and protection stay unknown. Partial and missing-record states never imply empty or complete drives.
- A display-only backend bridge consumes the existing one-shot process-local selection and projects minimal metadata. Only newly created owned temporary fixtures are observed in this work. Absolute roots, device/inode identity, hashes, allocation and operation authority are omitted. There is no route, native user-folder selector, arbitrary inventory conversion, provider, persistent access or mutation/recovery connection; the synthetic-only adapter remains unchanged.
- Every imported snapshot remains an unauthenticated historical claim. Renaming a card preserves embedded source labels/dates/paths; duplicate visible labels never merge records. Exact bounded parsing, fatal UTF-8, duplicate-key rejection, hierarchy/gap consistency, upfront canonical byte budgets, staged imports and generation checks preserve existing state on rejection, interruption or navigation. All text is inert; no browser storage or network is added.
- Users explicitly select observed plain files/folders across records without ancestor/descendant overlap inside one record, then download a manual project plan for the unchanged planning workspace. Full historical origin stays in ordinary editable per-item notes; current labels and membership are manual decisions. Intended homes remain unset and targets empty. Catalogue download/reopen retains source history; temporary project selections require separate plan export. Download requests and revision-specific save acknowledgement remain distinct.
- Local verification passes 91 focused backend/scoped tests, all 615 frontend Jest tests (65 new model cases), 28 catalogue DOM checks, all 43 existing manual-workspace DOM checks, 44-route OpenAPI, scoped YAML compatibility and frontend formatting. Independent source/model/DOM review adds 633 model assertions, 19 interruption/focus/download-failure assertions and ten fresh owned-producer checks. The locked local Chromium is absent; an existing system Chromium attempt stops before a journey because process sockets are prohibited. No local browser pass is claimed.
- Accepted source `797377b66389342c3175396d63984cbd7661e912` has all ten push/PR workflow runs green (five workflows across two events). The [catalogue workflow](https://github.com/krahd/disk_organiser/actions/runs/37900937335) passes 65 model/28 DOM checks on both Linux and Windows plus all seven Chromium journeys. [Aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37900937299) passes Linux 709 backend, Windows 607 passed/102 skipped, 615 Jest, 44 OpenAPI routes, audits, formatting and 27 existing Chromium flows. The unchanged manual workspace, synthetic UI and planner workflows also pass. Source checks preserve all 230 non-status baseline blobs; no dependency or default-navigation change is included.
- Original artifact `11602121970` is 5,445,764 bytes with SHA-256 `803997d6a1a5eaaada9b2df5a3926a896bbf06037ae5252f94139e4643e0f13d`. Its complete outer ZIP and all twelve original PNG lengths/hashes verify. Independent inspection accepts the overview, offline search, fully painted selected-scope/selected-file viewports, 320-pixel layouts/dialogue, keyboard focus, hostile text, maximum decimal sizes and enlarged source details. Pagination word breaks and focus-ring/helper overlap found in initial pixels are closed. An incomplete intermediate full-page selection PNG is explicitly superseded by real viewport evidence after settled paint; it is not counted as accepted visual evidence.
- The locked browser's CSS-zoom locator issue is diagnosed rather than hidden: the CDP/rectangle centre `(505.62, 94.89)` hits the header, while the correctly scaled `(1011.24, 189.78)` point natively hits the details button. A real mouse event activates that control, then keyboard toggles both ways. Intrinsic work/search wrapping keeps the zoomed input at least 240 CSS pixels wide. Normal pointer flows, source/geometry checks and original pixels are independently reviewed; no forced/DOM click is substituted. Native browser-UI zoom, OS dialogue controls, screen-reader/participant usability, native volume identity/reconnection and real user-drive/backup/restore acceptance remain separate gates.
- [Catalogue contract, usage, limits and verification](docs/INVENTORY-CATALOGUE.md). This documentation-only closeout preserves every runtime/test/workflow blob from the accepted source; the cited evidence is not attributed to its later documentation commit. No deployment, provider offer or sale-readiness claim is made.

The new read-only bridge separates process-local observation, imported display claims and explicit manual intent. No arrow grants physical identity, protection or execution authority.

<svg xmlns="http://www.w3.org/2000/svg" width="920" height="210" viewBox="0 0 920 210" font-family="DejaVu Sans, sans-serif" role="img" aria-labelledby="catalogue-flow-title catalogue-flow-desc">
<title id="catalogue-flow-title">Historical catalogue to manual plan boundary</title>
<desc id="catalogue-flow-desc">Owned selected-folder observation produces a display snapshot. Explicit import creates untrusted historical catalogue records. User selection creates a manual plan with source notes. No execution is available.</desc>
<defs><marker id="catalogue-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z" fill="#53685b"/></marker></defs>
<rect x="15" y="35" width="190" height="100" rx="8" fill="#eef3e9" stroke="#53685b"/>
<text x="110" y="65" text-anchor="middle" font-size="15">Owned selected folder</text><text x="110" y="92" text-anchor="middle" font-size="13">Metadata-only one-shot</text><text x="110" y="114" text-anchor="middle" font-size="13">No user-drive surface</text>
<line x1="205" y1="85" x2="245" y2="85" stroke="#53685b" marker-end="url(#catalogue-arrow)"/>
<rect x="250" y="35" width="185" height="100" rx="8" fill="#fff5df" stroke="#53685b"/>
<text x="342" y="65" text-anchor="middle" font-size="15">Snapshot JSON</text><text x="342" y="92" text-anchor="middle" font-size="13">Historical display claim</text><text x="342" y="114" text-anchor="middle" font-size="13">Not authenticated</text>
<line x1="435" y1="85" x2="475" y2="85" stroke="#53685b" marker-end="url(#catalogue-arrow)"/>
<rect x="480" y="35" width="190" height="100" rx="8" fill="#fff5df" stroke="#53685b"/>
<text x="575" y="65" text-anchor="middle" font-size="15">Saved catalogue</text><text x="575" y="92" text-anchor="middle" font-size="13">Label, overview, search</text><text x="575" y="114" text-anchor="middle" font-size="13">Presence unknown</text>
<line x1="670" y1="85" x2="710" y2="85" stroke="#53685b" marker-end="url(#catalogue-arrow)"/>
<rect x="715" y="35" width="190" height="100" rx="8" fill="#eef3e9" stroke="#53685b"/>
<text x="810" y="65" text-anchor="middle" font-size="15">Manual project plan</text><text x="810" y="92" text-anchor="middle" font-size="13">Explicit chosen scopes</text><text x="810" y="114" text-anchor="middle" font-size="13">Source notes retained</text>
<text x="460" y="166" text-anchor="middle" font-size="14">Paths stay text. Physical identity and protection remain unknown.</text>
<text x="460" y="191" text-anchor="middle" font-size="14">No file operations.</text>
</svg>

## Guided manual planning workspace checkpoint

- Added a separate static `frontend/manual-workspace.html` interface for real manually entered projects, named drives/scopes, recorded locations, intended homes, planned backup targets, desired policies, exclusions and restore checklists. It starts empty and does not replace default navigation or Aurora. Project cards, labelled location lanes, a recorded/intended comparison and planned-target cards support the four-step guided journey; Show details reveals exact paths, keys, JSON and history without changing saved state.
- The same independent model handles every edit and import. Archived references remain present; changes to current names/locations/targets cannot relabel historical results. Report rendering uses frozen context and shows drift, mixed outcomes, explicit sample descriptions and dates. Everything remains manual intent with unknown backup coverage; no scanner, provider, account, model service or file-operation authority is present.
- Explicit local artifact export/import preserves all decisions and history. The UI checks size before reading, decodes UTF-8 fatally with BOM preservation, previews before replacement and rejects obsolete asynchronous reads. Cancelling, editing during a pending read, malformed/unreadable input and save failure preserve the draft. Download feedback distinguishes a requested download from confirmed saving; unsaved-state acknowledgement is revision-specific. All untrusted text is text-rendered and CSP denies connections/forms; no browser autosave or telemetry was introduced.
- Local combined verification passes 43 DOM integration checks, all 550 frontend Jest tests after preserving the accepted Aurora integration and seven Chromium spec discovery cases. The DOM checks cover the real guided authoring journey, generated Blob export/reopen, details parity, immutable history/drift, hostile text, nonblank/whole-drive requirements, reference-preserving archival, malformed UTF-8/BOM/JSON, stale picker/import races and repeated report submit. DOM simulation is not native browser/pixel or hardware acceptance.
- The dedicated read-only workflow uses existing locked dependencies for model/DOM checks on Linux and Windows, plus Chromium journeys, mobile/zoom, keyboard, save/reopen, cancellation and direct-file launch. Original numbered screenshots and their manifest enter a measured ZIP of at most 30 MiB, including metadata and ZIP headers; full failure artifacts remain separate. Local Chromium execution remains blocked by process-socket restrictions; hosted execution and original screenshot inspection now provide the bounded visual evidence described below. Empty intercepted filechooser selection does not establish OS-native dialog-button automation; screen-reader/nontechnical-participant acceptance also remains open.
- Initial published source `4b681288bada73abf334fe815143818a3aca08b2` passes all eight push/PR workflows, including 199 model cases and 41 DOM checks on Linux/Windows and seven Chromium flows. Original screenshot review found a 320-pixel Close-label wrap defect, awkward Rename-plan wrapping and singular/plural count wording. A focused display-only repair adds nonshrinking 44-pixel/no-wrap Close, wrapping title rows, plain item counts and rendered-line/geometry regressions. Local checks pass 43 DOM cases and 550 Jest tests. Repaired source `eb5f226ece95b70dd0d3e85de6c7cc026b574c73` then passed all eight exact-head push/PR workflows and independent inspection of all eleven regenerated original screenshots; the Close/Rename and count findings are closed. Model, schema, report history and provider/filesystem boundaries remain unchanged.
- Exact repaired-source evidence: [manual planning workflow](https://github.com/krahd/disk_organiser/actions/runs/37891910411), [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37891910399), [synthetic UI](https://github.com/krahd/disk_organiser/actions/runs/37891910405) and [planner](https://github.com/krahd/disk_organiser/actions/runs/37891910402). Hosted logs establish 199 model/43 DOM on both OS; seven new Chromium flows; 550 aggregate Jest; Linux 691 backend; Windows 596 passed/95 skipped; 44 OpenAPI routes on both; 140 planner and 39 isolated HTTP cases on both; 23 focused Jest, 36 existing isolated Chromium and 27 existing aggregate Chromium flows. Artifact `11598499076` has outer ZIP SHA-256 `d3c3cd88507519bb4d5e54501954b4098c36477e9f636dc5c0488163bfad622a` and 2,252,150 bytes. All eleven original PNG hashes/lengths were verified; desktop, 320-pixel mobile, long-title dialogues, 200% CSS zoom, visible keyboard focus and inert long-text layouts were inspected. This documentation-only closeout preserves every tested runtime/test/workflow blob from `eb5f226e`; these runs are not attributed to its later documentation commit.
- [Workspace usage and verification](docs/MANUAL-WORKSPACE.md). Independent source/DOM review accepts the frozen runtime after separate guided-only, delayed-import, history and failure-path probes. The repaired source has bounded source/DOM/browser/pixel acceptance. Native OS Cancel-button automation, screen-reader and participant-usability acceptance remain open; no deployment or real backup/restore action is included.

## Independent manual planning model checkpoint

- Added a standalone browser/CommonJS model for user-authored named drives, file/folder/whole-drive scopes, projects, intended backup targets, desired policies and restore checklists. It is separate from Aurora/synthetic evaluation and the Flask app. Paths remain inert text; coverage, authenticated versions, capacity and physical independence remain unknown. No app/provider/filesystem/network/storage operations or runtime dependencies were introduced.
- Strict JSON admission rejects duplicate keys, unknown fields, future versions, unsafe/non-integer numeric representations, unsupported Unicode/control characters, dangling/wrong-type references and malformed lifecycle claims. Explicit bounds are 1 MiB UTF-8, 24 nested containers, 100,000 JSON nodes/keys and schema-sized collections. Canonical export size is checked before serialisation; a failed edit/import keeps the existing document.
- Immutable revision-checked edits support atomic batches, full record replacement, explicit archive/reference handling and one-use staged import confirmation. No hidden cascading deletion, import merge or migration occurs. Unknown optional facts remain absent; no-op edits preserve revision.
- Report history is append-only. First reporting freezes a bounded context containing the historical target/item/project/destination names, locations, provider and user-described versions. Current records remain editable; drift is shown without rewriting old context. Earlier failures and same-time contradictory reports stay separate. Imported snapshots are untrusted claims, not verified recovery. This pre-publication schema extension deliberately updates the illustrative reported example; older result artifacts without historical context reject instead of fabricating it.
- Local verification passes 199 new model tests plus all 351 existing frontend tests (550 total after additive rebase), full frontend formatting, JavaScript syntax, 44-route OpenAPI and all three examples against the extended schema. The earlier independent design harness passes 39 cases but does not establish the new snapshot contract. No Flask/application/database runtime was started for this model work.
- Independent adversarial review accepts model SHA-256 `45d714de3a18f902e9e7329bd62d19ac12786be4ed70356688a1380f52dc6154` after fixes for prototype-name action dispatch, C1/Unicode line separators and historical context rebinding. It includes parser/UTF-8 accounting oracles, exact resource edges, malformed actions, frozen context mutation attempts, subsequent edits plus append/export/reopen, 5,000 retained reports and atomic snapshot-overflow rejection. Browser rendering/keyboard/mobile/accessibility acceptance remains a separate UI integration gate; no physical backup/restore or hardware acceptance is claimed.
- Contract, representation policies, public API and boundaries: [manual planning model](docs/manual-planning/MODEL.md). The additive candidate preserves accepted main `17fdaf203de5e5a5062f9d864f1eaa7bb922eafe` and all 214 non-status upstream blobs exactly. The latest upstream `STATUS.md` content is retained with this checkpoint and refreshed timestamps. The repaired source has passed exact-head hosted verification and original screenshot review as recorded above. This closeout changes only documentation and makes no deployment or release claim.

The independent model validates manual metadata and returns private JSON text. The UI owns deliberate file selection, import confirmation and save-request feedback; none of these connections represents a file operation on a named drive.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 190" role="img" aria-labelledby="manual-model-title manual-model-desc">
  <title id="manual-model-title">Independent manual planning data flow</title>
  <desc id="manual-model-desc">User-authored edit actions and chosen JSON text pass through bounded validation and an immutable model. The model returns private JSON text, warnings and planning summaries without accessing named drives.</desc>
  <defs><marker id="manual-model-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52657a"/></marker></defs>
  <rect x="20" y="55" width="220" height="80" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="130" y="84" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#172b40">Manual edit actions</text>
  <text x="130" y="110" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">or chosen JSON text</text>
  <line x1="240" y1="95" x2="320" y2="95" stroke="#52657a" stroke-width="2" marker-end="url(#manual-model-arrow)"/>
  <rect x="320" y="40" width="280" height="110" rx="10" fill="#f3f1fb" stroke="#52657a"/>
  <text x="460" y="70" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#172b40">Bounded immutable model</text>
  <text x="460" y="98" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">References and retained history</text>
  <text x="460" y="124" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">Manual claims; coverage unknown</text>
  <line x1="600" y1="95" x2="680" y2="95" stroke="#52657a" stroke-width="2" marker-end="url(#manual-model-arrow)"/>
  <rect x="680" y="55" width="220" height="80" rx="10" fill="#eef4fb" stroke="#52657a"/>
  <text x="790" y="84" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#172b40">JSON text and summaries</text>
  <text x="790" y="110" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#172b40">No drive/provider access</text>
</svg>

## Aurora project choices checkpoint

- The isolated Aurora example now saves editable project choices before Review and stages a deliberately selected choices file for explicit replacement. Current/saved destination cards, membership and edited-path counts give a concise comparison; exact member paths and file limits are optional detail. Cancel preserves current edits and review. Successful replacement clears the prior review/report export and requires a fresh explicit Review. [Contract and boundaries](docs/drive-administration/PROJECT-CHOICES.md).
- The new `disk-administration-project-intent/v1` contract is separate from the unchanged non-replayable report. It holds all eight membership choices and edited paths, including unchecked edits, plus the intended destination and exact packaged-source identity. Admission caps bytes at 8 KiB, depth at eight, parsed nodes at 256 and the existing review-request projection at 4 KiB. Strict UTF-8, duplicate decoded keys, exact field allowlists, canonical safe integer revisions, relative paths, Unicode and exact source matching are enforced. Imported strings never grant native access or supply observation, backup, recovery or execution evidence.
- A separate import epoch and full-control/source snapshots prevent delayed reads, edits, repeated opens, dismissal, reload, page exit or back/forward restoration from reviving obsolete choices. Saving rechecks source, generation and controls before download activation/status and releases temporary object URLs. No upload, autosave or browser persistence is added. The only server change is one fixed static asset: ten isolated routes and six assets; the default 44-route API is unchanged.
- Fresh local checks pass 351 Jest tests (77 pure intent, 36 choices-flow and 238 existing tests), 691 backend tests in fresh owned app state, 140 pure planner tests, 39 isolated HTTP contracts, 44 OpenAPI routes, frontend formatting, YAML compatibility, Python compilation and whitespace checks. Both npm and pinned Python dependency audits report no known vulnerabilities. Broad flake8 retains pre-existing diagnostics in the three touched Python files; baseline comparison establishes zero new diagnostics. All 36 isolated browser specifications parse, including eleven new project-choices flows. The retained pre-implementation admission failure and earlier independent numeric/download lifecycle regressions are preserved as evidence; fresh independent source review finds no blocker after 109 focused Jest tests and 1,700 additional assertions covering all 510 nonempty membership/root combinations, independent request projections, strict admission and real asynchronous FileReader lifecycle flows.
- Initial published source `9086a9a27162933172f710a1c63d7d13e13972e6` passes aggregate CI and planner workflows, but both isolated UI runs expose intermittent keyboard file-picker waits (35/36 push and 34/36 PR flows pass). Failure pixels keep Open visible, enabled and focused. Independent inspection of the locked Playwright 1.37 subscription code identifies asynchronous first/last-listener interception toggles as the supported cause. A persistent observer is now installed before navigation; all actual chooser waits, keyboard/pointer activations, file selections, assertions and zero retries remain. This harness-only repair changes no application bytes and requires fresh hosted verification; the failed runs are not acceptance evidence.
- Independent initial pixels pass the desktop, 320-pixel collapsed/expanded and 390-pixel staged comparisons with readable controls, focus and wrapped paths; all 48 artefact files match their manifest. Zoom staging was not accepted from that incomplete run; final rendered acceptance is recorded below. Root visual inspection requested a small copy repair: singular/plural summary and included-member labels now match their count, with four new failing-before-fix Jest cases and the desktop browser expectation corrected. No import, review or persistence behaviour changes. The complete 351-test Jest suite and 1,700-assertion independent probe pass after the copy repair.
- Repaired source `7dc442b79b660abadd8adfa15f54741b8c79dfda` passes all 36 isolated Chromium flows in both push and PR runs, including repeated keyboard Open and 200% CSS zoom. The complete screenshot ZIP exceeds the available 32 MiB local-transfer limit. One additive `if: always()` upload step now preserves project-choices PNGs as a smaller focused artefact; the original complete evidence upload, every test, selectors, permissions and failure evidence remain unchanged. The packaging-only adjustment and final rendered acceptance are verified below.
- Local Chromium launch is blocked by sandbox process-socket restrictions, so no local browser/pixel pass is claimed. The documentation-only closeout must pass its own head checks before normal expected-head integration. Dependency files, real-drive/provider access, mutation/recovery gates and manual-only documentation publication are unchanged. Representative hardware, native browser zoom, assistive technology, real-data and release acceptance remain separate.
- Accepted source `855e89e83e4ff6fd2cc18e1e5bdb1269df545b87` passes all six exact-head push/PR workflows: [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37888897915), [planner CI](https://github.com/krahd/disk_organiser/actions/runs/37888897910) and [isolated UI CI](https://github.com/krahd/disk_organiser/actions/runs/37888897923). Hosted logs establish Linux 691 backend; Windows 596 passed/95 skipped; OpenAPI44 on both; 351 Jest; 27 existing Chromium flows; both audits, formatting and YAML compatibility; 140 planner and 39 HTTP contracts on each OS; 23 focused Jest and all 36 isolated Chromium flows. Independent review accepts the final source after 113 focused tests and 1,700 adversarial assertions, with no runtime/safety blocker.
- Focused artefact `11597411945` has ZIP SHA-256 `b7a3a0b2d00e64df9d0526595f7fb6a69e74550f77aeb03963479568054be6fa`. All six original PNG hashes are verified and independently inspected, including 200% CSS-zoom collapsed/expanded paths, warnings, focus and Replace/Cancel controls. All three narrow screenshots are byte-identical to the earlier accepted views; desktop differs only in the requested singular-label region. No clipping or overlap is found. The complete evidence artefact `11597576128` is retained unchanged. This documentation-only closeout preserves every tested runtime, test and workflow blob; cited source results are not attributed to a later commit. No native-browser-zoom, assistive-technology, real-data, hardware or release acceptance is inferred.
- The next useful product boundary is a person's bounded declared or imported inventory, with source-bound intent and explicit reconciliation. This is documented as a proposal only; the current slice remains the packaged synthetic Aurora example.

## Maintenance status payload-bound checkpoint

- The existing maintenance status reader now requests 65,537 binary bytes once and admits at most 65,536 UTF-8 bytes, 32 nested JSON containers and 4,096 retained parsed nodes. These are new documented product limits. Root/containers/scalar values/retained object keys each count once; duplicate keys retain last-value semantics. A string/escape-aware preflight runs before JSON parsing, followed by iterative node counting.
- The separately importable standard-library helper has no app, database, provider, thread or filesystem side effects on import. Success and missing-file response structures remain; failure stays HTTP 500 with a fixed bounded error string. Files are never truncated, rewritten, repaired or retried. Request arguments remain inert. [API contract](docs/API.md).
- Both hosted backend-test steps now create a fresh owned directory under `RUNNER_TEMP` and set `DISK_ORGANISER_DATA_DIR` before app import. This strengthens test isolation only; production storage semantics, existing test selectors/assertions, jobs, dependencies, permissions and publication remain unchanged.
- Local focused verification currently passes 378 cases: 72 pure payload tests, 29 owned-file route tests and the original 277 request-contract cases. PR #14's request corpus/assertions are retained except for its two legitimate binary-open expectations. Boundary coverage includes byte cap minus one/exact/plus one, UTF-8 edges/errors, nested containers at 31/32/33, strings/escapes, node limits, malformed/truncated JSON, unchanged bytes and no rewrite. Full local verification passes 691 backend tests in fresh owned app state, 238 Jest tests, 44 OpenAPI routes, 140 planner tests, 37 isolated HTTP contracts, formatting, YAML compatibility, focused flake8 and Python compilation. Independent review accepts the bounded source/harness after a fresh 378-case run, 5,029 inert-stream oracle probes and four additional owned-route failure probes. Published source `1b548cd7df03d2c1a29619a41292e394159a2922` passes all exact-head push and PR workflows: [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37876105864), [planner CI](https://github.com/krahd/disk_organiser/actions/runs/37876105831) and [isolated UI CI](https://github.com/krahd/disk_organiser/actions/runs/37876105802). Hosted logs establish Linux 691; Windows 596 passed/95 skipped; 44 OpenAPI routes on both; 238 Jest; 27 existing Chromium flows; both audits, formatting and YAML compatibility; 140 planner and 37 HTTP contracts on each OS; 23 focused Jest and 25 isolated Chromium flows. Both fresh-state shell forms executed successfully. This documentation-only closeout preserves all tested runtime/test/workflow blobs; the cited runs are not attributed to a later commit. No new pixel or hardware acceptance is claimed.
- This is payload resource hardening only. Path provenance, no-follow and blocking-open guarantees, schema validation, app-import writes and legacy backup/storage safety remain separate gates. Embedded paths gain no interpretation or authority. Dependencies, mutation/recovery flags, PR #15's display repair and manual publication stay unchanged; no real-folder, provider, hardware or release acceptance is claimed.

## Operation history text-rendering checkpoint

- Legacy operation/recycle titles and operation detail responses now render stored strings through text nodes and `textContent`. The existing `strong`, `em` and `pre` structure, classes, labels, action ordering, accessibility state and fetch/JSON contracts are preserved.
- Added 34 isolated Jest regressions and five synthetic Chromium scenarios. Fixtures contain inert markup, quotes, entities and Unicode only; fetch is mocked and no backend, provider, saved operation or user directory is used by the new tests. The Jest corpus gives nine assertion failures against the unchanged renderer and passes after the repair.
- Local verification passes: 238 Jest tests, 590 existing backend tests in fresh owned app state, 44 OpenAPI routes, 140 pure planner tests, 37 isolated HTTP contracts, frontend formatting and YAML dependency compatibility. Independent review accepts the bounded repair after a separate 34-test run and 47 owned-DOM probes, including exact normal-page equality. Local Chromium cannot start because process sockets are unavailable; no local browser/pixel pass is claimed.
- Published source `c9c388288f1014b826e432050da10e88328b12f2` passes all exact-head push and PR workflows: [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37873935082), [planner CI](https://github.com/krahd/disk_organiser/actions/runs/37873935117) and [isolated UI CI](https://github.com/krahd/disk_organiser/actions/runs/37873935085). Hosted aggregate logs establish Linux 590; Windows 495 passed/95 skipped; 44 OpenAPI routes on both OS; 238 Jest; 27 Chromium flows including all five new history scenarios; audits, formatting and YAML compatibility. Matching hosted normal-history screenshots were inspected. This documentation-only closeout preserves those runtime/test blobs; the cited runs are not attributed to a later commit.
- This is a display-only repair. Backend storage/path handling, permissions, dependencies, execution/recovery flags, default navigation and manual-only documentation publishing are unchanged. Other stored-result and backup-traversal safety work, representative hardware and release acceptance remain separate.

## Read/status malformed-input checkpoint

- The explicit backlog for `/api/ops`, `/api/recycle/list` and `/api/maintenance/status` now has 276 deterministic request cases in a separate test file. Inert operation/recycle mocks and owned temporary maintenance data cover malformed/large/encoded/duplicate query values, JSON type/encoding/body cases, interrupted input, repeated response closure, unsupported methods, local-origin boundaries and preserved failure responses.
- All new cases pass against unchanged runtime source from accepted main `33e74a23`. No production bug or failing-before-fix claim is made. These endpoints have no query/body parameters; unsupported pagination, path, action and cancellation arguments remain inert. Malformed maintenance fixtures remain byte-identical.
- Runtime/UI/dependencies/workflows, execution/recovery flags and manual-only documentation publishing are unchanged. The slice does not establish bounded legacy stored-result sizes, safe legacy backup traversal, read-only SQLite access, live transport cancellation or real-drive acceptance. See [the request-contract checkpoint](docs/READ-STATUS-INPUT-FUZZ.md).
- Local verification passes: 277 focused tests (276 request cases plus a collection-name bound), 590 full backend tests, 44-route OpenAPI, 204 Jest tests, frontend formatting, YAML consumer compatibility, 140 pure planner tests and 37 isolated HTTP contracts. Focused flake8, diff whitespace checks and both dependency audits pass. No new local browser/pixel result is claimed. Independent review accepts the bounded tranche after repairing two test-oracle weaknesses (shared mutable expected data and permissive provider-method mocks), six adversarial in-memory checks, and an explicit fresh app-state-directory prerequisite. Initial published source `5b1409ca` passes Linux and both planner/demo workflows, but Windows reports six setup/teardown errors because default expanded large-body parameter IDs exceed its environment-variable limit. Short body/file-case labels and a failing-before-fix collection-name regression repair the harness without changing request bytes or assertions. Independent repair review accepts the unchanged corpus and name-bound fix after a fresh 277-test run. Repaired source `0ae3d6b54cd47f674f087bb41105fef6847b6e3b` passes [aggregate CI](https://github.com/krahd/disk_organiser/actions/runs/37871477246), [planner CI](https://github.com/krahd/disk_organiser/actions/runs/37871477241) and [isolated UI CI](https://github.com/krahd/disk_organiser/actions/runs/37871477132). Exact logs establish Linux 590; Windows 495 passed/95 skipped; 44 OpenAPI routes on both; 204 Jest; 22 existing Chromium flows; 140 planner tests and 37 HTTP contracts on each OS; 23 focused Jest and 25 isolated Chromium flows; both audits and formatting. Earlier failed-source results are not extended to the repair. This documentation-only closeout preserves the tested runtime/test blobs; no new pixel, hardware or release acceptance is inferred.

## Project purpose

Disk Organiser is intended to help people understand and administer their drives, organise projects without breaking their dependencies, maintain storage policies, and control backup targets, coverage and recovery. Optional provider integrations and resale are part of the longer-term commercial direction. The current prototypes implement only bounded parts of this vision; real-drive mutation, automatic recovery deletion and sale readiness remain held.

## Source integration and publication boundary

- This integration preserves accepted source `8ecab6e04e3d1efb52771611b1e43b8cf9e03f06` and joins the separate PR #13 history at `96c58ba41a0bc0a61196c490e60cdc551164f7a7`. All nine model, test, fixture, specification and documentation blobs match; the older PR #13 status report is not replayed. PR #11 and PR #12 are already ancestors of the accepted source.
- The only additional changes are this status note and the removal of the automatic `main` push trigger from `.github/workflows/publish-docs.yml`. Documentation publication remains available through explicit `workflow_dispatch`; its job and permissions are unchanged. Main integration does not authorise a public-site update, release, tag or store submission.
- The accepted source has three successful exact-head workflows: aggregate CI `37557058025`, project administration `37557058069` and synthetic review UI `37557058028`. The integration candidate is checked independently before main advances; these historical runs are not attributed to a later commit.
- Runtime, tests, dependencies and safety gates are unchanged. Real-drive mutation, automatic recovery deletion, live providers and sale readiness remain held. Separate in-progress keep-current/no-op work is excluded from this integration.

## Current implementation state

The default `/ui/` entry serves a bounded local-only file-type overview and read-only comparison of the existing layout with an exact copy plan. Copy execution is disabled by default; explicit synthetic-development opt-in and a fresh approved plan are required for fixture testing. Automatic recovery removal is unavailable. See [GUIDED-COPIES.md](docs/GUIDED-COPIES.md) for the safety boundary and [the UX audit and contract](docs/ux/FOLDER-UNDERSTANDING-2026-10-06.md) for scope, acceptance criteria and staged product work.

The previous experimental interface remains available at `/ui/index.html`, outside default navigation, with:

- Flask backend under `backend/`
- vanilla JavaScript frontend under `frontend/`
- background analysis jobs
- context-driven reasoning and chat refinement
- grouped operation previews
- selective execution
- backup-before-mutate behaviour
- reverse-order undo
- Modelito-backed provider selection and Ollama lifecycle routes
- OpenAPI documentation and route drift validation

Near-duplicate detection is content-aware and includes filename/token similarity, sampled text overlap, PDF text extraction, DOCX parsing, image perceptual hashing, size similarity, and optional OCR/embedding paths when dependencies are installed.

## Active focus

The main product direction is drive/project administration, organisation and backup control. A map, duplicate detector or observation model may support those jobs, but does not define the product. The next bounded capability is an editable project-organisation and protection review: intended membership and destination, dependency/collision checks, exact proposed effects, version-scoped backup evidence, restore scope and cost/capacity implications. See [the roadmap](docs/DRIVE-ADMINISTRATION-ROADMAP.md). This direction supersedes the map-as-main-product interpretation in historical UX notes without revoking the independently accepted read-only checkpoint. The new local pure-data prototype is synthetic-only and non-executable; it is not a complete organiser, integrated backup service or commercial release. Dedicated Windows guided support, hostile concurrent-write protection, cloud/network handling and representative hardware acceptance remain open. Remote inference is never used by the guided surface.

## Project administration planning checkpoint

- Source-only prototype under `prototypes/drive_administration/`: explicit user correction of project membership/destination, revision checks, structure-preserving proposals, source/destination uncertainty, dependency and collision blockers, capacity and backup/restore evidence review.
- Configuration, provider reports, snapshot manifests, content verification and restore exercises stay distinct. Sample restoration never establishes whole-project restoration; stale or contradictory evidence cannot authorise action. All supplied evidence is fabricated.
- Every result is non-executable: no operation authority, no live backup/restore verification, no undo support or safe-to-erase claim. No existing app route, frontend/default navigation, observation model or execution/recovery flag changes.
- Dated official-provider research recommends software plus customer-owned storage first, optional referral revenue second, and qualified reseller/white-label service later. No provider account, secret, agreement, purchase or live integration is introduced.
- Verification for the exact prototype and independent-review boundary is recorded in [the slice verification](docs/drive-administration/VERIFICATION.md). A separate two-OS standard-library workflow tests the isolated source; publication does not imply that its remote run has passed.
- Independent review accepts the bounded v3 synthetic contract after source-identity, Unicode and restore-history repairs. Local and independent verification are detailed in the slice verification document.
- A separate synthetic review UI now implements editable membership/destination and the three-step Harbour decision loop. Its source and validation boundary are described below. Native observation, authenticated backup evidence, execution/recovery design, representative hardware and commercial-readiness gates remain distinct.

## Declared dependency-layout correctness checkpoint

- The pure-data planner now blocks changed declared parent-relative dependency addresses. Cross-volume dependencies and unknown source/destination naming semantics receive an explicit unknown-layout blocker. Dependency IDs, unchanged content versions and historical restore labels cannot clear either blocker.
- The check compares declared strings only. It does not parse application references, approve relocation, authenticate restored layout or establish real application usability. Authenticated layout/restore evidence remains open. The later declared keep-current extension is recorded below.
- Local verification: all 68 original evaluator/cost tests remain unchanged and pass; 14 added layout regressions bring the suite to 82. The new regressions fail against the original planner (15 failing assertions, no errors). All 20 original isolated HTTP tests and 119 original frontend Jest tests pass; exact packaged-reference equality, frontend formatting and Python compilation pass. Existing local test dependencies supply Flask; no dependency was installed or changed.
- Independent review accepts the five-file bounded repair, including a 10,000-case lexical-path oracle and a fresh 82-test run. Published source `27bce28350d7e83a443f1f0788748cbf5259a480` has exact blob/diff readback and all three workflows green: aggregate `37556460692`, planner `37556461031` and isolated interaction `37556460867`.
- Fresh remote results: Linux 230 backend tests; Windows 181 passed/49 skipped; 119 Jest; 22 existing Chromium flows; 44 OpenAPI routes; both dependency audits; 82 planner tests and 20 HTTP contracts on each OS; 19 focused Jest and seven isolated Chromium flows. Hosted Windows preinstalled `pipx` dependency conflicts are reported during installation, without failing the install or tests. No dependency changed.
- The accepted UI, HTTP code, packaged scenarios, original tests and safety boundaries are unchanged. No native hardware, real-drive, restore or sale-readiness acceptance is claimed. The documentation closeout preserves every runtime/test blob from the tested source. Integration lineage, PR #13 blob parity and the separate main-triggered docs-publication gate are recorded in the checkpoint below.
- Behaviour, evidence limits and reproducible checks: [dependency-layout checkpoint](docs/drive-administration/DEPENDENCY-LAYOUT.md).

## Declared keep-current correctness checkpoint

- Exact same-volume, same-spelling current addresses now receive `keep_current` only with fresh, complete, online, known-semantics plain-file/version/single-link identity and no declared source ancestry conflict. Only the member's own occupied check is exempted. Same-address uncertainty is `unresolved_current_location`, retains its blockers and leaves required capacity null.
- Entirely kept scope needs zero logical copy bytes, zero applied reserve and zero additional required space. Mixed plans count only proposed copies plus one policy reserve; zero-byte copies still need reserve. Unknown physical allocation, dependency/backup/restore uncertainty and every safety flag remain unchanged.
- The isolated UI conditionally labels kept/unresolved paths and explains capacity. CSS, routes, reference fixtures and ordinary copy-result output are unchanged. One static HTML help paragraph now explains conditional keep-current. The old same-home self-collision assertion intentionally becomes an explicit no-op assertion; negative different-target collision coverage remains.
- Local checks: 100 pure-data tests (82 original unchanged plus 18 new), 22 HTTP contracts, 123 Jest tests, frontend formatting and Python compilation pass. Eighteen new specifications reproduce 28 failing assertions on the accepted original planner, with no errors. Seven browser specifications parse/list; a fresh local launch cannot find the locked Chromium executable. No download or alternate browser was attempted and no local browser/pixel pass is claimed.
- Independent review accepts the bounded source and tested HTTP/Jest behaviour: all 12 changed and 49 unchanged supplied files verified; a fresh full test run and 3,356 additional adversarial cases pass; ordinary packaged outputs exactly match the baseline. Initial saved source `f509dd7e` passed aggregate `37567434040`, planner `37567434093` and isolated UI `37567434092`. Actual pixels then exposed a stale static HTML helper saying current-layout preservation was unimplemented. A narrow paragraph repair adds a failing-before-fix Jest regression and explicit browser wording assertions; planner/runtime JavaScript are unchanged. The repaired source `9d3502751b4d725f960757878b163b34eb8ea056` is independently accepted after exact tree verification and inspection of all seven replacement screenshots, including 320-pixel reflow and 200% CSS zoom. The static-help finding is closed. The initial green runs are not attributed to this repair. Main integration and the documentation-publication trigger are coordinated separately; this candidate changes neither the publication workflow nor deployment authority. No real-drive action, provider access, credential use, historical dangerous reproducer, mutation/recovery change or deployment is included.
- Exact repaired-source CI: aggregate `37568117611` passed Linux 230 backend, Windows 181 passed/49 skipped, 123 Jest, 22 existing Chromium flows, 44-route OpenAPI, audits and formatting; planner `37568117563` passed 100 on each OS; isolated UI `37568117598` passed 22 HTTP on each OS, 23 focused Jest and seven Chromium flows. The documentation-only closeout preserves every runtime/test blob from the tested source rather than relabelling those runs.
- Artifact `11458909865` has ZIP SHA-256 `fadb1e3fd20440b51c3cb3fa51275c6640ca2f58f365c1d4c45a6ba16020efc8`; all 16 screenshot/geometry file hashes were verified. Corrected guidance, three kept paths and zero additional copy/reserve/required bytes are readable and consistent. No clipping or overlap was found. This is synthetic interaction acceptance, not native browser-UI zoom, screen-reader, real-drive or backup/restore acceptance.
- Contract, intentional behaviour change and verification limits: [keep-current checkpoint](docs/drive-administration/KEEP-CURRENT.md).

## Synthetic observation-draft adapter checkpoint

- `prototypes/drive_administration/observation_adapter.py` bridges canonical synthetic Disk Model exports and explicit member/path intent into a separate incomplete observation draft. Observed roots, fingerprints, hashes and aliases never become physical volumes, authenticated versions, independent backups or a successful copy/no-op.
- Current/intended root-relative addresses, recorded observations, coverage, source changes and uncertainty are preserved. Missing identity, name semantics, live availability, capacity, dependencies and protection evidence remain blocking; copy/required space and protection counts remain null. Every authority, recovery and live-verification flag remains false/null.
- Admission reuses the pure canonical validator and adds bounded used-observation consistency checks. Real or missing synthetic flags reject without conversion. Untrusted paths stay strings. Evaluation makes no file, scanner, network, provider or existing-planner call.
- Local checks: 140 standard-library tests (100 accepted tests unchanged plus 40 adapter tests), the exact existing workflow cwd command, 22 unchanged HTTP contracts, 123 unchanged Jest tests, formatting and compilation pass. The oversized external-clock and dense-collision resource bounds found during independent pre-freeze inspection are repaired and covered. Collision comparisons and issue output have explicit fail-closed budgets; no detail is silently truncated.
- Independent frozen-source review reran the checks and passed 11 additional methods covering 86 synthetic cases, with no remaining runtime blocker. The two bounds findings are closed, and documentation now distinguishes sorted member rows from deterministic evaluation-order blockers. Initial source `bd812633` passed CI `37572443984`, planner `37572443945` and isolated UI `37572443997`. A further pre-integration resource check found that the byte limit followed full serialisation; upfront exact JSON-byte accounting and three regressions now prevent oversized whole-document allocation. Independent repair review passes 2,342 exact JSON-byte/bounds cases with unchanged valid canonical bytes/digests. Repaired source `f7e33aaf41efe92976bcede9106108daa6ebc678` has exact tree verification and all three hosted workflows green. The earlier runs are not attributed to this repair. UI, routes, canonical producer/schema/fixture, execution/recovery code, dependencies and workflows are unchanged. This source-only bridge introduces no arbitrary import, native scan, account/provider access, real-file operation or public deployment.
- Exact repaired-source results: planner `37573413212` passed 140 tests on each OS; aggregate `37573413173` passed Linux 230 backend, Windows 181 passed/49 skipped, 123 Jest, 22 existing Chromium flows, OpenAPI/audits/formatting; isolated UI `37573413176` passed 22 HTTP on each OS, 23 focused Jest and seven existing Chromium flows. No new rendering or native-hardware acceptance is claimed; the existing UI blobs are unchanged. The documentation-only closeout preserves every runtime/test blob from this tested source.
- Interface, evidence limits and next boundary: [observation draft adapter](docs/drive-administration/OBSERVATION-DRAFT-ADAPTER.md).

## Aurora observation-backed interaction checkpoint

- The isolated `/observation-draft` view connects the unchanged observation adapter to one fixed canonical-derived scenario: two recorded roots, 32 records and eight selectable examples. Explicit membership, intended project-relative paths and destination are reviewed against a revision/digest-bound source; nothing is inferred from hashes or folder roles. Harbour is unchanged apart from a link.
- All physical identity, current-version, dependency, capacity and protection gaps stay Unknown. Same-address intent never establishes a no-op; recorded aliases/stale sizes are not independent protection or required copy space. Conflicts name actual root/path participants, including unselectable occupants.
- Four allowlisted routes extend the separate demo to nine paths and five startup-loaded frontend assets. Existing exact loopback/host/origin/token/CSP controls remain. No arbitrary import, request-time files/network, native scan, provider, real observation conversion, default-app change, execution/recovery, autosave or deployment is introduced. Manual-only documentation publishing is unchanged.
- Local checks: 140 pure-data tests in both cwd modes, 37 HTTP contracts and 176 Jest tests pass, along with formatting, compilation and parsing all 18 browser specifications. The original exact allowlist assertion expands intentionally; 15 new HTTP and 53 new Jest cases preserve adversarial scope and safety coverage. Independent pre-freeze inspection exposed duplicate/altered response rows a count-based collision-scope label and duplicate reference choices; explicit failing-before-fix regressions now pass with all three repaired.
- A fresh local browser attempt reaches the isolated server but cannot find the locked Chromium executable. No local browser/pixel success is claimed. Independent source/API review accepts the 15-file source freeze after 587 additional HTTP and 36 JSDOM cases. Saved source `e6961bc74bff10633a162d182ca06308365f88d9` passed aggregate `37579859328`, planner `37579859269` and isolated UI `37579859355`, including 18 Chromium flows. Actual pixels exposed narrow member-label columns at 200% CSS zoom despite passing overflow checks. A scoped Aurora-only intrinsic grid rule, pre-fix Jest regression and explicit browser column/label-width checks repair that readability issue without changing Harbour styling. Repaired source `57e06d1460ee689ffc8a0fda4ef85d394f6d88b5` is independently accepted after exact tree verification, fresh CI and replacement pixel inspection; earlier runs are not extended to this repair.
- Exact repaired-head results: planner `37580973081` passes 140 on each OS; aggregate `37580973068` passes Linux 230 backend, Windows 181/49 skipped, 176 Jest, 22 existing Chromium, OpenAPI44/audits/formatting; isolated UI `37580973070` passes 37 HTTP on each OS, 23 existing focused Jest and all 18 Chromium flows. Artifact `11464836743` ZIP SHA-256 is `b9e3cd6a77580157165354d595ac4600983c28604fa6bd2214197e4b7cd43e33`; all 32 file hashes and 13 distinct screenshots are verified. The zoom repair provides one-column member cards with 332.672–358.281 CSS-pixel label widths. All other twelve screenshots, including every Harbour image, are byte-identical. Independent review closes all four findings with no clipping, overlap or evidence-label regression. This documentation-only closeout preserves the tested runtime/test blobs; no later-commit, native-browser-zoom, screen-reader or real-hardware acceptance is inferred.
- Contract and precise verification boundary: [Aurora observation view](docs/drive-administration/OBSERVATION-VIEW.md). Save review is a separately verified follow-on described below; it is not part of this observation-view acceptance. Real-drive/native/provider, recovery and commercial-readiness gates remain held.

## Aurora Save review checkpoint

- Aurora adds one user-initiated JSON download for the exact current successful explicit review. Reference-only, edited, pending, errored, dismissed, reloaded and navigated-away states cannot export. Generation and exact-current-intent checks prevent stale responses or unannounced control changes from reviving an old report.
- The versioned synthetic display-report allowlist preserves source/decision digests as strings, exact decisions, shown addresses/statuses, unresolved identity, Unknown capacity/protection, blockers and limitations. It explicitly says canonical observation export false and replayable false. Tokens, headers, unrelated state and undisplayed large fingerprint integers are excluded; no rounded identity is manufactured.
- Blob/object URLs are local and user-initiated, with fixed safe ASCII filenames, temporary-anchor removal, deferred/idempotent URL revocation, repeated-click and interruption checks. Status reports a download request, never confirmed local saving. Browser cancellation may arrive after a small file completes and must be recorded honestly.
- Local checks: 140 pure, 37 HTTP and 204 Jest tests pass, with formatting/syntax and all 25 browser specifications parsed. One pre-feature failing assertion, two activation/cleanup pre-fix failures and one silent-control-change regression are retained; the export snapshot binds directly to the echoed accepted decision. Local Chromium is still absent; hosted acceptance is separate. Independent source review passes 57 additional cases including 27 actual-response exports and nested metadata exclusion. Accepted source `c6ffb62ebddee564af597b6732027cbf028e3e87` has exact tree verification and all three hosted workflows green. The silent pending-intent finding is closed; prior Aurora-only runs are not extended to this download action.
- Exact source results: planner `37584999433` passes 140 on each OS; aggregate `37584999415` passes Linux 230 backend, Windows 181/49 skipped, 204 Jest, 22 existing Chromium, OpenAPI44/audits/formatting; isolated UI `37584999457` passes 37 HTTP on each OS, 23 existing focused Jest and 25 Chromium flows. Artifact `11465879693` ZIP SHA-256 is `7f086b8787e53bbf0a2b20955a57c1e3aa47e1df2b501e4d66bc7904c3202d3d`; all 38 files are verified. The 12,899-byte actual JSON matches fresh Python-review/accepted-JavaScript projection bytes, SHA-256 `835af08ae9b21096f828f5ca941b3f319816f2bc07c9ccb306e77ba4a6f8f165`. Independent inspection accepts desktop/mobile/320px/CSS-zoom download controls and disclosures. Seven Harbour PNGs are byte-identical; prior Aurora differences are confined to appended Save content. Cancellation was requested after this small download had completed (`failure: null`); early cancellation remains unverified. The docs-only closeout preserves accepted runtime/test/style blobs without relabelling CI as testing a later commit.
- Harbour, CSS, server/adapter, fixtures, HTTP routes and workflows are unchanged. No import/replay, upload, autosave, provider, native scanning, execution/recovery, default-app change or public deployment is added. Manual-only documentation publication and all real-drive holds remain intact. Contract: [Save review](docs/drive-administration/SAVE-REVIEW.md).

## One-shot scoped observation checkpoint

- New `backend/observation_session.py` wraps the existing read-only scanner with one explicit process-local selected directory, a held non-inheritable descriptor and a one-shot revocable lifecycle. Only owned temporary fixtures are exercised. No route, CLI, arbitrary import, persistent grant, token usable outside the process, native user-folder surface or GuidedStore is added.
- The optional scanner root guard runs before descendant enumeration/metadata/content access. The session re-walks the selected address without following links at the guard and before final admission; it forces metadata-only, no-cross-filesystem and fixed entry/directory/depth/cooperative-time limits. Scanner defaults and canonical output remain unchanged when no guard is supplied.
- State/result admission is lock-protected; caller callbacks run outside locks. Cancellation is latched, final progress cancellation is polled, revocation invalidates late candidates, and held descriptors cannot be closed/recycled during active comparison. Copy/pickle and changed-PID misuse reject without touching inherited locks. This is a cooperative lifecycle API, not an OS grant or protection against hostile Python already in the process.
- Descriptor/device/inode comparisons enforce only the short-lived selected scope. They never become durable volume/file identity, planner no-op evidence or independent protection. All operation/undo/erasure/live-verification flags remain false/null; missing identity, versions, dependencies, capacity and protection remain Unknown. Invalidated attempts return no admitted inventory rather than a false empty drive. In-flight syscalls and already-admitted callbacks are not claimed to stop instantly; post-check concurrent-writer/mount races and native hardware remain unqualified.
- Local checks: 142 scanner/session tests (59 original, ten guard and 73 session), 140 unchanged planner/adapter tests in both cwd modes, 37 HTTP, 204 Jest, formatting and compilation pass. Root-guard absence, stale guard admission after re-entrant revocation, and malformed canonical-result admission have failing-before-fix regressions. Native allowed spellings stay literal data. Independent source review accepts the frozen six-file implementation, including 111 additional owned-fixture cases and exact verification of all 88 supplied files. Fresh local reruns repeat these results. No new UI or pixel acceptance is claimed.
- Saved source [`4f1cfee67527cdc68fce3c19997e934aca9edda7`](https://github.com/krahd/disk_organiser/commit/4f1cfee67527cdc68fce3c19997e934aca9edda7) has exact tree/blob readback and three successful exact-head workflows: aggregate [`37685415783`](https://github.com/krahd/disk_organiser/actions/runs/37685415783), planner [`37685415780`](https://github.com/krahd/disk_organiser/actions/runs/37685415780) and isolated UI [`37685415788`](https://github.com/krahd/disk_organiser/actions/runs/37685415788). Independent publication review accepts the bounded source and hosted results.
- Hosted source checks: Linux 313 backend tests; Windows 218 passed/95 skipped; 204 Jest; 22 existing Chromium flows; 44 OpenAPI routes on each OS; both dependency audits, formatting and scoped YAML compatibility. Planner contracts pass 140 on each OS; isolated HTTP contracts pass 37 on each OS, with 23 focused Jest and 25 isolated Chromium flows. Descriptor-relative cases skip on unsupported Windows; this is fail-closed/unsupported-platform coverage, not native Windows traversal acceptance. The runner reports existing `pipx` resolver conflicts without failing dependency installation or tests.
- This documentation-only closeout preserves every runtime/test/workflow blob from the tested source. The three source runs above are not attributed to a later documentation commit; final-main readback and exact-head check attribution remain separate integration gates. Manual-only docs publication, user-folder access and all execution/provider/recovery holds are unchanged.
- Contract, exact limits and remaining user-folder gate: [read-only scope](docs/drive-administration/READONLY-SCOPE.md). Frontend, demo routes, synthetic adapter/planner, schema, provider, execution/recovery code, dependencies and workflows are unchanged; manual-only publication remains intact.

## Synthetic project interaction checkpoint

- Standalone `frontend/project-review-demo.html`, `.js`, `.css` and `prototypes/drive_administration/demo_server.py` implement the simulated “Organise and protect Harbour” decision loop. The permanent banner identifies the simulation and disconnected drives/providers.
- Membership suggestions/corrections and declared dependencies, a proposed volume/relative folder, side-by-side exact current/proposed paths, readable blockers, logical capacity/reserve, per-target/version backup evidence, scoped restore results and unresolved alerts are exposed. Dates, methods, fixture clock and uncertainty remain visible.
- Review calls the accepted Python evaluator; there is no JavaScript rule clone. Dismiss returns the immutable reference decision and focus. The original interaction checkpoint kept the same-home occupied-path blocker. The later declared keep-current extension below explicitly addresses that separate gap.
- The original Harbour checkpoint had exactly two packaged scenarios and five allowlisted HTTP paths. The later Aurora extension above adds a separate fixed observation scenario and four paths. Loopback address/exact host, same-origin checks, ephemeral process token, bounded strict decision JSON and restrictive CSP protect the isolated server. There are no arbitrary imports, uploads, filesystem/provider operations or editable backup evidence. The original checkpoint read three fixed frontend assets at app creation; Aurora adds two fixed assets.
- Drafts remain in tab memory. Every review uses the immutable fixture revision/digest; successive projected reviews do not advance a hidden server state. Edits, scenario changes, reload and dismissal invalidate pending success/error responses and previous results.
- All results remain non-executable, with null authority, unavailable undo, no source-erasure permission and false live backup/restore verification. No existing default app, navigation, execution, recovery, observation or provider code changes.
- Local verification: 68 unchanged evaluator tests, 20 new HTTP contract tests, 119 copied-frontend Jest tests (19 new UI tests), full copied-frontend Prettier check and Python compilation passed. Seven isolated browser specifications parse and list successfully. No aggregate backend or native hardware claim is made for this local partial checkout.
- Local Chromium launch is blocked by the environment's socket permission (`Operation not permitted`); no alternate local bypass was attempted. Actual local screens and browser passes are not claimed. A separate isolated demo CI workflow runs the HTTP tests on Linux/Windows and Chromium screenshots using only the synthetic server. On source `63150c5`, remote HTTP contracts passed on Linux and Windows; six of seven Chromium flows passed. The 200% CSS-zoom pointer locator failed before overflow/320-pixel checks. Actual failure pixels show the Review button unobstructed. A narrow browser-harness revision now records DOM hit coordinates and requires an unforced pointer click on the verified visible target; runtime/evaluator source is unchanged. On source `74e5dde`, isolated UI CI run `37545358916` passed both OS HTTP jobs and all seven Chromium flows, including the zoom pointer action, overflow and 320-pixel checks. A final evidence-only harness edit writes the numeric hit-coordinate JSON into the uploaded artifact rather than retaining it only as an in-memory test attachment. Runtime/evaluator source remains unchanged. Accepted source/evidence checkpoint: `83b42ffc947cfef5e9717c82047531a4f18ee96a`. All three exact-head workflows are terminal green: aggregate `37545756445`, evaluator `37545756447` and isolated UI `37545756460`. Independent review qualifies this bounded synthetic interaction with no unresolved blocker. Durable numeric hit-coordinate JSON and all six actual screenshots were verified; the documentation-only closeout preserves every runtime/test blob from that tested source.
- Verified browser coverage includes keyboard flow, desktop/mobile, 320-pixel reflow and actual rendered 200% CSS zoom; the latter is not native browser-UI zoom. Accepted-source aggregate logs establish Linux 230 backend tests, 119 Jest tests and 22 existing browser tests; Windows 181 backend tests passed with 49 skips; OpenAPI covers 44 routes. The isolated demo adds 20 HTTP tests on each OS and seven Chromium flows. Native zoom, screen-reader behaviour and representative hardware remain unverified.
- Run commands, API contract, revision semantics, test boundaries and remaining gates: [interaction demo](docs/drive-administration/INTERACTION-DEMO.md). No new dependency, merge, deployment, provider account, release or store submission.

## Architecture overview

The backend scans allowed roots, builds file contexts, uses provider-backed or heuristic planning to produce typed actions, stores operations, serves grouped previews, executes selected actions safely, and supports undo. The frontend drives the analysis, preview, refinement, and execution workflow.

### Isolated synthetic interaction architecture

The standalone demo has no connection to the default or legacy execution paths below. A tab-local decision reviews a packaged Harbour fixture or the fixed Aurora observation source; all results return as non-executable evidence. The planner and observation adapter remain distinct, and neither connects to an executor.

<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="260" viewBox="0 0 1000 260" role="img" aria-labelledby="demo-arch-title demo-arch-desc">
  <title id="demo-arch-title">Isolated synthetic review</title>
  <desc id="demo-arch-desc">The tab-local draft calls the loopback demo server, which calls the Harbour evaluator or Aurora observation adapter using fixed synthetic sources. A current Aurora review can be downloaded locally as synthetic display JSON. No executor is connected.</desc>
  <defs><marker id="demo-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0 L10 5 L0 10 z" /></marker></defs>
  <rect x="20" y="40" width="260" height="90" rx="8" fill="none" stroke="black" />
  <text x="150" y="72" text-anchor="middle" font-size="15">Tab-local membership / home</text>
  <text x="150" y="97" text-anchor="middle" font-size="13">Review / dismiss / save report</text>
  <line x1="280" y1="85" x2="350" y2="85" stroke="black" marker-end="url(#demo-arrow)" />
  <rect x="350" y="40" width="260" height="90" rx="8" fill="none" stroke="black" />
  <text x="480" y="72" text-anchor="middle" font-size="15">Isolated loopback Flask app</text>
  <text x="480" y="97" text-anchor="middle" font-size="13">Origin / token / bounded edits</text>
  <line x1="610" y1="85" x2="680" y2="85" stroke="black" marker-end="url(#demo-arrow)" />
  <rect x="680" y="40" width="300" height="90" rx="8" fill="none" stroke="black" />
  <text x="830" y="72" text-anchor="middle" font-size="15">Fixed sources + evaluator / adapter</text>
  <text x="830" y="97" text-anchor="middle" font-size="13">No drives, providers or executor</text>
  <text x="500" y="161" text-anchor="middle" font-size="13">Returned draft: exact intent, scoped blockers and explicitly limited synthetic evidence</text>
  <line x1="150" y1="130" x2="150" y2="182" stroke="black" marker-end="url(#demo-arrow)" />
  <rect x="20" y="185" width="260" height="55" rx="8" fill="none" stroke="black" />
  <text x="150" y="208" text-anchor="middle" font-size="13">User-initiated local JSON</text>
  <text x="150" y="229" text-anchor="middle" font-size="12">Synthetic display report only</text>
</svg>

Only the current successful explicit Aurora review can follow the local-download branch. It is not an import/replay path and grants no filesystem authority.

### Owned-fixture scoped observation boundary

This separate in-process path is exercised only by owned temporary fixture tests. It does not connect the default app or the synthetic demo to real user folders. A returned inventory is observation data with missing-evidence limits, never operation authority.

<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="190" viewBox="0 0 1000 190" role="img" aria-labelledby="scope-arch-title scope-arch-desc">
  <title id="scope-arch-title">One-shot read-only observation scope</title>
  <desc id="scope-arch-desc">An owned fixture selection supplies a revocable descriptor-bound session to the guarded metadata scanner. Final admission returns limited observations or no inventory. No user-folder route or executor is connected.</desc>
  <defs><marker id="scope-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0 L10 5 L0 10 z" /></marker></defs>
  <rect x="20" y="45" width="210" height="80" rx="8" fill="none" stroke="black" />
  <text x="125" y="76" text-anchor="middle" font-size="14">Owned fixture selection</text>
  <text x="125" y="100" text-anchor="middle" font-size="12">Explicit single directory</text>
  <line x1="230" y1="85" x2="270" y2="85" stroke="black" marker-end="url(#scope-arrow)" />
  <rect x="270" y="45" width="210" height="80" rx="8" fill="none" stroke="black" />
  <text x="375" y="76" text-anchor="middle" font-size="14">Revocable one-shot session</text>
  <text x="375" y="100" text-anchor="middle" font-size="12">Process-local descriptor</text>
  <line x1="480" y1="85" x2="520" y2="85" stroke="black" marker-end="url(#scope-arrow)" />
  <rect x="520" y="45" width="210" height="80" rx="8" fill="none" stroke="black" />
  <text x="625" y="76" text-anchor="middle" font-size="14">Guarded metadata scanner</text>
  <text x="625" y="100" text-anchor="middle" font-size="12">No-follow / bounded / read-only</text>
  <line x1="730" y1="85" x2="770" y2="85" stroke="black" marker-end="url(#scope-arrow)" />
  <rect x="770" y="45" width="210" height="80" rx="8" fill="none" stroke="black" />
  <text x="875" y="76" text-anchor="middle" font-size="14">Final state admission</text>
  <text x="875" y="100" text-anchor="middle" font-size="12">Observation or no inventory</text>
  <text x="500" y="158" text-anchor="middle" font-size="13">Identity / capacity / protection remain Unknown; no operation or recovery authority</text>
</svg>

### Architecture diagram

The diagram below describes the retained legacy analysis architecture. The new default guided path is `frontend/guided.js` → local token/origin-checked Flask API → `backend/guided.py` → SQLite journal and descriptor-relative copy/verification. It does not call the model, legacy executor or legacy backup store.

<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="500" viewBox="0 0 1020 500" role="img" aria-labelledby="disk-arch-title disk-arch-desc">
  <title id="disk-arch-title">Disk Organiser architecture</title>
  <desc id="disk-arch-desc">The frontend calls Flask API routes; backend modules build context, plan actions, store operations, and execute filesystem changes with backup and undo safeguards.</desc>
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0 L10 5 L0 10 z" /></marker></defs>
  <rect x="40" y="170" width="190" height="90" rx="10" fill="none" stroke="black" />
  <text x="135" y="205" text-anchor="middle" font-size="14">frontend/main.js</text>
  <text x="135" y="228" text-anchor="middle" font-size="12">analysis UI, preview,</text>
  <text x="135" y="246" text-anchor="middle" font-size="12">chat refinement</text>
  <rect x="300" y="170" width="190" height="90" rx="10" fill="none" stroke="black" />
  <text x="395" y="205" text-anchor="middle" font-size="14">backend/app.py</text>
  <text x="395" y="228" text-anchor="middle" font-size="12">Flask API routes</text>
  <text x="395" y="246" text-anchor="middle" font-size="12">and orchestration</text>
  <rect x="570" y="40" width="190" height="80" rx="10" fill="none" stroke="black" />
  <text x="665" y="72" text-anchor="middle" font-size="14">context_builder.py</text>
  <text x="665" y="94" text-anchor="middle" font-size="12">metadata and signals</text>
  <rect x="570" y="150" width="190" height="80" rx="10" fill="none" stroke="black" />
  <text x="665" y="182" text-anchor="middle" font-size="14">model_client.py</text>
  <text x="665" y="204" text-anchor="middle" font-size="12">Modelito / fallback</text>
  <rect x="570" y="260" width="190" height="80" rx="10" fill="none" stroke="black" />
  <text x="665" y="292" text-anchor="middle" font-size="14">action_planner.py</text>
  <text x="665" y="314" text-anchor="middle" font-size="12">typed actions</text>
  <rect x="800" y="95" width="180" height="80" rx="10" fill="none" stroke="black" />
  <text x="890" y="126" text-anchor="middle" font-size="14">op_store.py</text>
  <text x="890" y="148" text-anchor="middle" font-size="12">operations, backups, undo</text>
  <rect x="800" y="245" width="180" height="80" rx="10" fill="none" stroke="black" />
  <text x="890" y="276" text-anchor="middle" font-size="14">fs_ops.py</text>
  <text x="890" y="298" text-anchor="middle" font-size="12">preview and execution</text>
  <rect x="570" y="385" width="190" height="70" rx="10" fill="none" stroke="black" />
  <text x="665" y="414" text-anchor="middle" font-size="14">tasks.py</text>
  <text x="665" y="434" text-anchor="middle" font-size="12">background jobs</text>
  <line x1="230" y1="215" x2="300" y2="215" stroke="black" marker-end="url(#arrow)" />
  <line x1="490" y1="195" x2="570" y2="85" stroke="black" marker-end="url(#arrow)" />
  <line x1="490" y1="215" x2="570" y2="190" stroke="black" marker-end="url(#arrow)" />
  <line x1="490" y1="235" x2="570" y2="300" stroke="black" marker-end="url(#arrow)" />
  <line x1="490" y1="250" x2="570" y2="420" stroke="black" marker-end="url(#arrow)" />
  <line x1="760" y1="300" x2="800" y2="285" stroke="black" marker-end="url(#arrow)" />
  <line x1="760" y1="190" x2="800" y2="135" stroke="black" marker-end="url(#arrow)" />
  <line x1="890" y1="175" x2="890" y2="245" stroke="black" marker-end="url(#arrow)" />
</svg>

### Flow chart

The flow chart below describes the legacy analysis lifecycle, not a certification of its filesystem safety. The default guided lifecycle is scan → file-type overview → compare current layout with read-only copy plan → inspect exact paths. Synthetic-development copy testing additionally requires fresh explicit approval and verification. Automatic recovery removal is unavailable.

<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="360" viewBox="0 0 1040 360" role="img" aria-labelledby="disk-flow-title disk-flow-desc">
  <title id="disk-flow-title">Disk Organiser safe operation flow</title>
  <desc id="disk-flow-desc">The user selects a root, analysis builds context, reasoning creates a preview, the user refines and selects actions, backups are created, actions execute, and undo can restore changes.</desc>
  <defs><marker id="flowarrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0 L10 5 L0 10 z" /></marker></defs>
  <rect x="25" y="135" width="125" height="65" rx="10" fill="none" stroke="black" /><text x="87" y="164" text-anchor="middle" font-size="12">Select scan</text><text x="87" y="182" text-anchor="middle" font-size="12">root</text>
  <rect x="190" y="135" width="130" height="65" rx="10" fill="none" stroke="black" /><text x="255" y="164" text-anchor="middle" font-size="12">Build file</text><text x="255" y="182" text-anchor="middle" font-size="12">contexts</text>
  <rect x="360" y="135" width="130" height="65" rx="10" fill="none" stroke="black" /><text x="425" y="164" text-anchor="middle" font-size="12">Reason and</text><text x="425" y="182" text-anchor="middle" font-size="12">plan actions</text>
  <rect x="530" y="135" width="130" height="65" rx="10" fill="none" stroke="black" /><text x="595" y="164" text-anchor="middle" font-size="12">Preview and</text><text x="595" y="182" text-anchor="middle" font-size="12">refine</text>
  <rect x="700" y="135" width="130" height="65" rx="10" fill="none" stroke="black" /><text x="765" y="164" text-anchor="middle" font-size="12">Back up then</text><text x="765" y="182" text-anchor="middle" font-size="12">execute</text>
  <rect x="870" y="135" width="130" height="65" rx="10" fill="none" stroke="black" /><text x="935" y="164" text-anchor="middle" font-size="12">Undo if</text><text x="935" y="182" text-anchor="middle" font-size="12">needed</text>
  <line x1="150" y1="167" x2="190" y2="167" stroke="black" marker-end="url(#flowarrow)" /><line x1="320" y1="167" x2="360" y2="167" stroke="black" marker-end="url(#flowarrow)" /><line x1="490" y1="167" x2="530" y2="167" stroke="black" marker-end="url(#flowarrow)" /><line x1="660" y1="167" x2="700" y2="167" stroke="black" marker-end="url(#flowarrow)" /><line x1="830" y1="167" x2="870" y2="167" stroke="black" marker-end="url(#flowarrow)" />
  <path d="M 595 135 L 595 80 L 425 80 L 425 135" fill="none" stroke="black" marker-end="url(#flowarrow)" />
</svg>

## Setup and run instructions

Backend and API validation:

```bash
source venv/bin/activate
pytest -q backend/tests
python scripts/validate_openapi.py
```

Frontend unit and formatting checks:

```bash
npm test --silent
npm run format:check
```

Playwright visual tests:

```bash
npx playwright test frontend/visual
```

## Configuration and environment variables

- `DISK_ORGANISER_EMBEDDING_MODEL`: embedding model name; default is `all-MiniLM-L6-v2`. Empty or invalid values disable embeddings for the session.
- OCR optional dependencies: `pytesseract`, `pdf2image`, Tesseract binary, and Poppler.
- Embedding optional dependencies: `sentence-transformers` and `numpy`.
- Model provider configuration is routed through Modelito-backed provider selection.

## Important files and directories

- `backend/app.py`: API routes and orchestration.
- `backend/context_builder.py`: file-context generation and near-duplicate signals.
- `backend/model_client.py`: provider dispatch and heuristic fallback planning.
- `backend/action_planner.py`: typed-action normalisation and validation.
- `backend/fs_ops.py`: previews and execution helpers.
- `backend/op_store.py`: operation storage, backups, and undo.
- `backend/tasks.py`: background scan/analyse jobs.
- `frontend/main.js`: analysis workflow UI.
- `docs/API.md`: API documentation.
- `docs/openapi.json`: OpenAPI specification.
- `scripts/validate_openapi.py`: route/spec drift check.

## Current safety hold and sustained development

- Independent review found a critical persisted-journal trust flaw in candidate `7ff5390`. Earlier green CI is not safety acceptance. Do not treat that candidate as safe for user data.
- `backend/guided_schema.py` now validates the complete versioned journal without filesystem I/O; derived names, field types, states, byte totals and identity relationships must all agree. Malformed and old records are retained and counted as blocked.
- Read-only is now the default. Capabilities explicitly distinguish current scan scope, disabled mutation/recovery, missing structured Disk Model and uncertainty. Copy fixture testing needs operator opt-in; legacy execute/undo/backup-removal APIs are separately disabled by default.
- Copy application additionally requires an unchanged canonical preview digest held in process memory from the user's current scan. Saved JSON cannot restore authority after restart, alteration, expiry or cache eviction. Rescan is required.
- Automatic recovery removal is disabled. The endpoint validates the record and stops without selected-folder I/O, unlink/rmdir or journal mutation. All originals, output and recovery data remain. Journal assertions alone cannot prove app ownership.
- Local defensive-core verification: 171 backend tests passed, guided schema/engine/test lint passed, 44 OpenAPI routes passed. Frontend contract integration and permitted independent confirmation remain pending.
- Backend corruption checks are benign data-only or mock selected-folder I/O. The previously blocked review operation is not reproduced. Permitted independent confirmation is required before acceptance.
- The guided experience now consumes strict session and per-plan capabilities, retains blocked-record notices, has no recovery controls and locks unconfirmed submissions until a successful history refresh. Exact-head browser validation and independent review remain gates.
- Sustained core safety, organisation logic, UX and reliability work is tracked in `docs/SAFETY-ACCEPTANCE-BACKLOG.md`; file ownership and contracts are in `docs/ARCHITECTURE-AND-OWNERSHIP.md`.
- MIT and commercial-wrapper holds remain unchanged. No merge, release, deployment or Apple Store upload.

## Guided understanding UX checkpoint

- Intent-first overview: understand what is here or explore a copy layout. Counts, logical copy data, exclusions and extension-only inference limits precede paths. Keeping the existing layout sends no file operation.
- Exact effects are searchable and paged at 25 rows. Filters never select a subset, and browsing revokes previous approval. Synthetic-development approval names the complete plan count and unavailable recovery.
- Saved snapshots are historical; read-only mode never suggests rescanning enables copying. Restarted or stale synthetic-development plans require a new scan. Default builds show no approval control.
- Native keyboard controls, focus return on closing, mobile action cards, loading/error/empty states and the 500-entry limit are covered in the test specifications.
- Local verification: 4 Jest suites / 35 tests passed, full frontend formatting and JavaScript syntax checks passed. Nine real Flask/Chromium scenarios are prepared for ordinary CI with disposable synthetic files only; exact final-head evidence is recorded on PR 12; independent confirmation remains required. No restricted local runtime was bypassed.
- Read the product audit, acceptance criteria, Disk Map evidence contract and durable backlog in `docs/ux/FOLDER-UNDERSTANDING-2026-10-06.md`. Scripted comprehension checks are not a participant study or assistive-technology acceptance.

## Read-only UX review repairs

- Initial PR 12 CI at `e91b526d` failed a stale default-UI assertion before browser stages. No screenshots exist for that run, and no visual acceptance is inferred from it.
- The default-UI API test now checks meaningful read-only/overview content while retaining no-remote-font/no-legacy-navigation assertions. One focused read-only API test passes locally.
- Explicit refresh reloads session token and capabilities before history, clears prior previews, and never resubmits the failed request. Initial load and failed refresh stay blocked until both reads succeed. History refresh remains available after a connection failure.
- Unsupported or missing scan capability disables scanning and explains the platform limit while preserving history. Read-only rescans and proposed effects no longer imply that copying becomes enabled.
- Three core error strings now direct users to retain all data and inspect the saved result manually; automatic removal remains unavailable. AST comparison verifies no engine change except string contents. Focused backend lint passes.
- README and guided UI distinguish the current read-only experience from retained disabled legacy actions and optional synthetic development copy tests. Repair CI at `e7fb60a` passed: Linux 171, Windows 151 passed / 20 skipped, UI 34 and real Chromium 12 tests. Its 13 screenshot files were checksum-verified and visually inspected. Screenshot review led to singular-count, neutral step-label and unsupported-empty-history wording refinements, with 35 local UI tests passing. Final-head CI and image evidence are recorded on PR 12; independent confirmation remains required.

- Final wording CI at `b1c3f2e` passed the same backend/browser checks and 35 UI tests. Image inspection then identified an evidence-capture race with asynchronous history expansion. Screenshot helpers now wait for idle except the deliberately held loading state, and assert PNG height matches stable document height. This is a test-only capture correction; current exact-head evidence is recorded on PR 12.

## Read-only Disk Map import integration

- Separate source-only integration based on accepted guided PR 12 `27b3c676` and the model-owned files from published `96c58ba4`. The accepted PR/source is unchanged; the producer has its own separately approved draft PR 13. This checkpoint creates no PR and enables no mutation or recovery.
- Nine model-owned source/test/schema/fixture/document files are copied byte-for-byte. Existing shared guided STATUS/documentation is retained and extended rather than replaced by the model branch's older copies.
- `frontend/disk-map.html`, `disk-map.js`, `disk-map-model.js` and `disk-map.css` add an import-only model viewer linked from the existing guided page. No backend routes, scanner hooks, root-scope capabilities, copy flags or recovery semantics change.
- The viewer exposes evidence-backed findings, possible folder roles, version/content relationships, neutral entries, qualified logical/allocation measures and non-executable review alternatives. It does not invent project understanding, backup health or coherent organisation plans.
- Imports are bounded, validated and kept only in tab memory. Invalid/oversized/interrupted imports preserve the accepted view; Clear invalidates pending results and removes rendered private labels. Text is never interpreted as HTML or used as a URL.
- Canonical schema/fixture browser assets and a reproducible parity checker are included. Strict contract validation plus reference/accounting checks precede display. Unsupported schema vocabulary fails closed.
- Verification is checkpointed explicitly: the previously cancelled chain was approved and passed at local baseline `b79b807` (83 tests, asset parity, formatting). Source-review repairs have 100 tests plus 59 unchanged producer tests passing. The published `e0cb4e1` CI run passed Linux 230, Windows 181 with 49 skipped, 100 frontend tests, dependency audits, formatting and OpenAPI checks; Chromium passed 20 of 22 scenarios. Both browser failures were ambiguous nested-summary test selectors, not an acceptance pass. The selector repair and final-head browser/pixel gates are recorded below.
- Read `docs/ux/DISK-MAP-IMPORT-CHECKPOINT.md` for precise import/privacy limits, acceptance criteria, provenance and the next review boundary. This is a bounded export viewer, not an integrated live-drive scanner or release.

## Disk Map source-review repair boundary

- The partial local integration was preserved as `b79b807`; the cancelled helper/format/test chain was rerun only after explicit approval and completed successfully. Historical passes are not attributed to later source.
- Imports now decode/parse/validate in a fixed local Web Worker; cancellation terminates it. Text, collection, reference and rendered-DOM budgets reject unmanageable inputs before replacement. The accepted model is retained while a new view is prepared off-DOM and committed atomically.
- Unique-path search avoids repeated member-path expansion. Lists, evidence and member pages expose display limits and omitted counts. Long labels wrap, and paging preserves keyboard focus when Next disappears.
- Recursive directory accounting and coverage reconcile with the parent graph and recorded gaps. Scan completion, change categories and hash-state summaries are checked for contradictions.
- Same-object aliases are checked for consistent size/allocation/fingerprints before totals, independent of order. Exact large integer observations are retained without deriving authority from inode/device numbers.
- Producer source/schema/fixtures remain byte-identical to `96c58ba4`; backend routes and all mutation/root-scope guards remain identical to accepted PR 12. No new PR, deployment or real-user operation belongs to this source-only checkpoint.

## Recent changes

### Disk Map browser-selector checkpoint, 2026-10-06

- Two test selectors now target `#scope-details > summary`, excluding the nested exclusions/error disclosure. No production UI, model, backend, dependency or safety boundary changed.
- The earlier local-only selector repair was reconstructed from published source and the failing CI trace after its checkout became unavailable. The repaired test blob is `d02124f643113f63cd6987f14381da77b4e3429f`, matching its recorded prefix. The former local commit/tree were not present remotely; the documentation here records the current verification rather than claiming byte-identical recovery of those documents.
- Fresh local checks on the reconstructed source: 100 frontend tests across six suites, full frontend formatting, canonical asset parity, YAML consumer compatibility and JavaScript syntax passed. A local Chromium attempt could not launch because the execution sandbox denied socket creation; no browser scenario or pixel pass is attributed to that attempt, and it was not bypassed.
- The bounded read-only checkpoint is independently accepted at tested head `fd9d2c11933eee88b424524709fcbabe0ddcb259`. [Ordinary CI run 37535618344](https://github.com/krahd/disk_organiser/actions/runs/37535618344) passed Linux 230, Windows 181 with 49 skipped, 100 frontend tests and all 22 Chromium scenarios, plus audits, formatting and both 44-route OpenAPI checks. The unchanged CI command excludes the existing preview-modal baseline test.
- The [synthetic browser artifact](https://github.com/krahd/disk_organiser/actions/runs/37535618344/artifacts/11445849175) contains 28 PNGs, including 15 Disk Map screenshots. Its ZIP SHA-256 is `1100851dedbcfabf1833b5e23cb71e49d2032f85a7802467de6534012a1150b1`. Independent review verified artifact identity and all PNG bytes/hashes/dimensions, then inspected all 15 Disk Map images at readable scale. Unknown allocation/future-clock freshness, observed zero, long labels and enlarged text are established without a blocking source, CI or pixel finding.
- This documentation-only acceptance update records the tested source head above; it does not relabel that run as testing a later commit. Separate read-only polish is proposed for enlarged-text metric columns and long evidence disclosure. The current extreme fixture produces 15,122px/53,604px pages at normal/enlarged text. This remains outside participant, assistive-technology or release acceptance. Mutations and automatic recovery removal remain disabled; PR 12 and draft PR 13 are unchanged.

- Backend Python dependencies now pin `modelito==1.4.1` in both `backend/requirements.txt` and `backend/requirements-locked.txt` (from `1.2.2`) to align with the latest upstream release.
- Backend Python dependencies were then advanced to `modelito==1.4.3` in both dependency pin files to track the new upstream latest version.
- Model provider selection is normalised through Modelito.
- Ollama lifecycle management is exposed through dedicated API routes and preferences UI.
- Runtime capability flags now report optional OCR and embedding availability.
- Frontend analysis UI shows optional capability state.
- Test coverage has been expanded around context building, analysis capability payloads, and frontend selection/refinement paths.
- Organise analysis flow now supports explicit cancellation while a background analysis job is running, with visible cancelled/failed state handling in the UI.
- Organise analysis flow now surfaces API-level start/reason/chat errors to users instead of silently assuming successful JSON responses.
- Backend `POST /api/analyse/reason` now returns lifecycle-specific errors for `job_id` lookups (`not_found`, `job_not_ready`, `job_cancelled`, `analysis_failed`) instead of collapsing all non-finished states.
- Frontend tests now cover interrupted analysis and failed network/API paths for start, reason, and chat refinement flows.
- Frontend analysis cancellation now validates API response status before confirming cancellation.
- Frontend reasoning failures now map lifecycle error codes to actionable guidance (cancelled, still running, missing job).
- Backend tests now cover analysis-reason behaviour for missing, cancelled, failed, and in-progress analysis jobs.
- Frontend tests now cover cancel-request API failures, reasoning `job_cancelled` responses, and reasoning `job_not_ready` responses.
- Local Node/Homebrew runtime linkage was repaired (node reinstall), restoring frontend verification execution.
- Integration interruption test suite added (`backend/tests/test_analysis_interruption.py`, 11 tests) covering cancelled, failed, in-progress, missing-job, and happy-path lifecycle states using real job files on disk and the Flask test client.
- Windows CI coverage was added via a dedicated `windows-backend` workflow job to validate backend tests and OpenAPI route coverage on `windows-2022`.
- Backend payload and malformed-input coverage was expanded in `backend/tests/test_analysis_payloads.py`, including a large-context `analyse/reason` integration path and fuzzed validation checks for `analyse/start` and `scan/cancel`.
- Frontend integration-style coverage now includes large analysis payload rendering with capability banner assertions (120 rendered action cards).
- Playwright interruption coverage was added in `frontend/visual/analysis-interruption.spec.js` with cancelled/failed state assertions for progress and alert visibility.
- Visual Playwright specs now default to local `frontend/index.html` file URLs and intercept API calls generically, removing reliance on whatever process is bound to port 8000.
- Frontend visual side-panel duplicate actions now honour `API_BASE`, improving testability and deployment flexibility for non-root API hosts.
- Non-analysis malformed-input fuzzing was expanded in `backend/tests/test_non_analysis_input_fuzz.py` (14 tests) across organise, chat, model, recycle, scan-index, and maintenance routes.
- Numeric validation hardening was added for `/api/recycle/cleanup`, `/api/scan_index/rebuild`, and `/api/scan_index/rebuild_async`, returning explicit `400` errors for malformed numeric payloads instead of implicit server errors.
- Malformed-input fuzzing now covers lower-traffic write paths in Ollama lifecycle and preferences writes, including explicit timeout validation for `/api/ollama/start`, `/api/ollama/pull`, and `/api/ollama/serve`, and object-shape validation for `POST /api/preferences`.
- `backend/tests/test_non_analysis_input_fuzz.py` now includes 19 route-level malformed-input cases spanning organise/recycle/scan-index/maintenance plus Ollama and preferences writes.
- Public project website content and visual design were refreshed in `docs/index.html` and `docs/assets/style.css` with clearer safety messaging and updated quick-start links.

## Tests and verification status

Current guided-copy results: see `docs/IMPLEMENTATION-CHECKPOINT.md`. Older results below remain historical evidence and do not establish current release readiness.


Previously recorded successful checks:

- `pytest -q backend/tests` -> 27 passed.
- `python scripts/validate_openapi.py` -> OpenAPI validation passed for 31 routes.
- `npm test --silent` -> frontend suite passed.
- `npm run format:check` -> Prettier check passed.
- `npm run test:visual` with server running -> Playwright visual tests passed.
- Focused backend and frontend capability tests were also recorded as passing.

Current session verification:

- `python -c "import modelito; print(modelito.__version__)"` -> `1.4.1`.
- `source venv/bin/activate && pip index versions modelito` -> latest `1.4.3`, installed `1.4.1` before migration.
- `npm test --silent` -> frontend suite passed (3 suites, 19 tests).
- `npm test -- --runInBand frontend/__tests__/organise.analysis.test.js` -> passed (15 tests).
- `npm run format:check` -> passed.
- `pytest -q backend/tests/test_analysis_api.py` -> passed (8 tests).
- `pytest -q backend/tests/test_analysis_interruption.py` -> passed (11 tests).
- `pytest -q backend/tests/test_analysis_payloads.py` -> passed (6 tests).
- `pytest -q backend/tests/test_non_analysis_input_fuzz.py` -> passed (19 tests).
- `pytest -q backend/tests` -> passed (80 tests).
- `python scripts/validate_openapi.py` -> passed (38 routes).
- `npm test -- --runInBand frontend/__tests__/organise.analysis.test.js` -> passed (16 tests).
- `npx playwright test frontend/visual/analysis-interruption.spec.js` -> passed (2 tests).
- `npx playwright test frontend/visual` -> passed (4 tests).

## Known issues, risks, and limitations

- OCR and embedding enhancements are optional and only active with extra dependencies installed.
- OCR quality needs broader real-world validation on scanned and low-quality documents.
- Frontend analysis flow has less test depth than backend safety-critical logic.
- Live Modelito planning quality depends on configured local runtime/model availability.

## Recurring tasks

- Keep hygiene checks current as packaging and release scripts evolve.
- Keep browser and macOS client expectations aligned with backend response contracts.

## Pending tasks

- Scope legacy stored-result bounds and backup traversal as a separate data-only audit; the accepted read/status request-contract coverage does not establish these storage-layer safety properties.

## Next steps

1. Define a bounded data-only legacy stored-result and backup-traversal audit with explicit zero selected-folder I/O and no migration or execution authority.
2. Keep visual tests deterministic as new UI/API paths are introduced.
3. Keep OpenAPI documentation in sync with route changes.

## Longer-term steps

1. Improve real-world OCR validation and tuning.
2. Expand semantic similarity safely as optional dependencies mature.
3. Preserve preview-first, backup-before-mutate, and undo invariants as the action set grows.

## Decisions and rationale

- Destructive filesystem changes must remain preview-first, backed up, and undoable.
- Optional analysis enhancements must degrade gracefully when dependencies are absent.
- Modelito is the normalised model-provider layer.

---

Last updated: 2026-10-10 03:40
