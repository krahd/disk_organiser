# Disk Organiser – Project Status

Last updated: 2026-10-07 06:28

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
- Contract and precise verification boundary: [Aurora observation view](docs/drive-administration/OBSERVATION-VIEW.md). Save review is the next bounded follow-on, after this view is accepted; it is not implemented in this slice. Real-drive/native/provider, recovery and commercial-readiness gates remain held.

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

<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="180" viewBox="0 0 1000 180" role="img" aria-labelledby="demo-arch-title demo-arch-desc">
  <title id="demo-arch-title">Isolated synthetic review</title>
  <desc id="demo-arch-desc">The tab-local draft calls the loopback demo server, which calls the Harbour evaluator or Aurora observation adapter using fixed synthetic sources. No executor is connected.</desc>
  <defs><marker id="demo-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0 L10 5 L0 10 z" /></marker></defs>
  <rect x="20" y="40" width="260" height="90" rx="8" fill="none" stroke="black" />
  <text x="150" y="72" text-anchor="middle" font-size="15">Tab-local membership / home</text>
  <text x="150" y="97" text-anchor="middle" font-size="13">Review or dismiss a proposal</text>
  <line x1="280" y1="85" x2="350" y2="85" stroke="black" marker-end="url(#demo-arrow)" />
  <rect x="350" y="40" width="260" height="90" rx="8" fill="none" stroke="black" />
  <text x="480" y="72" text-anchor="middle" font-size="15">Isolated loopback Flask app</text>
  <text x="480" y="97" text-anchor="middle" font-size="13">Origin / token / bounded edits</text>
  <line x1="610" y1="85" x2="680" y2="85" stroke="black" marker-end="url(#demo-arrow)" />
  <rect x="680" y="40" width="300" height="90" rx="8" fill="none" stroke="black" />
  <text x="830" y="72" text-anchor="middle" font-size="15">Fixed sources + evaluator / adapter</text>
  <text x="830" y="97" text-anchor="middle" font-size="13">No files, providers or executor</text>
  <text x="500" y="161" text-anchor="middle" font-size="13">Returned draft: exact intent, scoped blockers and explicitly limited synthetic evidence</text>
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

- Extend malformed-input fuzzing to read/status and auxiliary endpoints (`/api/ops`, `/api/recycle/list`, `/api/maintenance/status`) to tighten contract consistency across the full API surface.

## Next steps

1. Extend malformed-input fuzzing to read/status and auxiliary endpoints.
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

Last updated: 2026-10-07 06:28
