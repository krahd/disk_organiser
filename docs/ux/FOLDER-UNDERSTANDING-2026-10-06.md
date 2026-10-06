# Folder understanding: audit and first experience slice

## Sources and product intent

Read before design:

- [Vertinant Disk Organiser vision](https://github.com/krahd/vertinant/blob/main/projects/revenue-engine/DISK-ORGANISER-LAUNCH.md): private, low-effort understanding, organisation and meta-organisation; optional AI; explanation, preview and meaningful recovery. Current architecture is a foundation, not the product definition.
- [2026-10-05 market audit](https://github.com/krahd/vertinant/blob/main/projects/revenue-engine/MARKET-KILL-AUDIT-2026-10-05.md), section 2: generic AI sorting and duplicate cleanup are insufficient differentiation. Trust and comprehensibility precede a paid test.
- PR 11's exact candidate `7ff5390a5401a674c77ccff743212b2297e1ca9d`, `frontend/guided.*`, workflow tests and final desktop/mobile screenshot pixels from CI run `37498120176` / artifact `11428193219`.
- Current safety-owner repair contract: saved journal data is not ownership proof; automatic recovery deletion is unavailable. Only `can_apply: true` from a fresh in-process validated preview permits an approval control. Invalid records remain retained and counted. The old candidate is not certified safe by this document.

## Focused audit

The existing guided screen already has useful plain-language original retention, an explicit approval checkbox and local-only implementation. Its final mobile screenshot correctly stacks path rows and displays small byte values.

Observed gaps:

1. It jumps from a technical path field to an exhaustive path table. It does not first explain what was found or help decide whether a copy layout is useful.
2. A scan is implicitly a commitment to sorting. There is no equally visible choice to understand and stop, or to keep the existing layout.
3. All exact paths appear at once. At the 500-entry limit, meaningful summary and approval are separated by a very long list.
4. Saved previews are presented as if current. Restart, incomplete coverage and uncertain request results need distinct explanations.
5. A failed apply can leave an approved control available. An unconfirmed result requires a history read before a further request, not another click on the same approval.
6. Recovery language promised removal which the new safety design cannot justify. This is a safety boundary, not a copy-editing detail.

## Slice implemented

A bounded journey using the current deterministic scan and copy-plan capability. The ordinary build is read-only: copy execution is disabled, and rescanning does not enable it. The optional copy path is explicitly labelled synthetic development mode and is tested only with disposable synthetic fixtures:

1. **Choose an intent:** understand what is here (default) or explore an organised copy. These only change presentation, never backend policy or transmitted data.
2. **Understand:** file-type counts and byte totals, included/left-out counts, with explicit limits. The screen states that filename extensions are evidence; contents, projects, duplicates and nested folders are not interpreted.
3. **Compare:** leave the current layout as it is, or review a separate file-type layout. The copy choice quantifies additional data and the required space reserve. Keeping the layout does not issue a file operation.
4. **Inspect exact effects:** all original and destination paths remain available, with text-safe rendering, a 25-row page size and a search filter. Filtering is explicitly display-only. Approval and the action label retain the full plan count; browsing revokes prior approval.
5. **Synthetic development only, approve and observe:** strict session and plan capability checks, complete-plan acknowledgement, no invented progress percentage and no claimed safe in-flight cancellation. A connection failure hides the old approval and blocks new scans/operations until a successful history refresh.
6. **Revisit:** saved snapshots are clearly historical. Restarted/expired/untrusted previews have no approval control and offer a deliberate new scan. Completed/interrupted output remains retained; there is no recovery request or removal control.

No filesystem/API/schema change, new dependency, telemetry, model request, remote data sharing, paywall, deployment or release belongs to this slice.

## Acceptance criteria and verification

| Criterion | Evidence |
| --- | --- |
| A beginner can choose understanding without copying | Default intent, summary-first comparison; unit test and scripted browser path |
| Every unsupported/unknown entry is distinguishable from an empty folder | Skipped reasons + explicit partial-coverage empty state |
| Copy scope stays exact under search/paging | 500-entry fixture; apply count unchanged; browse clears approval |
| A close/cancel decision cannot submit or preserve approval | Close and keep-layout tests; focus returns to folder field |
| Recovery is never implied available | No recover endpoint call/control; prominent retention notice; completed-state test |
| Saved/restarted records cannot supply approval | Strict `can_apply === true`; real process restart browser test |
| Uncertain submission cannot be automatically retried | Failed apply clears preview; scan locked until successful history read |
| Paths cannot become executable markup | `<script>.txt` text-node test |
| Keyboard and mobile flow remain usable | Native radio/fieldset controls, labelled search, focus transitions, skip link, 390 px no-horizontal-overflow assertions |
| Large lists do not bury the full scope | 25 rows, search, counts, full-plan warning, no implicit selection |
| External services remain off | Browser request allowlist observes only the synthetic localhost server |

Local executed checks: 4 Jest suites, 35 tests passed; full frontend Prettier check passed. Browser specifications are added but must pass on the final published commit; this document does not convert a build or unit test into a visual test. The restricted local runtime was not bypassed.

Browser evidence specification: real Flask + Chromium, freshly generated synthetic files only. Captures desktop overview/exact preview, 390 px preview, retained results, closed preview, no supported entries, 500-file filtered preview, loading, uncertain result, restarted read-only plan and a final default-mode read-only build. Nine scenarios are specified, including a read-only backend restart without page reload and an unsupported-scan capability response. Images must be inspected after the exact-head CI run. These scripted walkthroughs do not constitute observed beginner-user or assistive-technology research.

## Durable backlog, ordered by dependency

### Next reviewable UX slices

- Independently review this slice, inspect exact-head screenshot pixels and repair any contradictions or clipping before adding features.
- Add a safe, bounded asynchronous scan with genuine progress and cancellation; keep abandonment distinct from cancellation of filesystem work. This needs an API capability, not a simulated UI timer.
- Design a native folder-selection adapter with explicit local/cloud/network limits; do not disguise a web upload picker as local folder access.
- Improve history triage by grouping source folders and explaining interrupted versus completed results without 50 equally weighted cards.
- Add user-directed layouts (for example preserve project groupings or separate active work from archives) only after a deterministic policy and exact preview contract exist. Do not market the current extension grouping as intelligence.
- Explore read-only drive-level maps that preserve existing folder relationships, provenance and user exclusions. Recursive inspection needs independent safety and performance review.

### Safety-dependent product work

- Recovery/remove-generated-copies remains unavailable until an independently reviewed ownership design exists; an inode, hash or saved record alone is not proof.
- Moves, renaming, deduplication and ongoing automation are separate actions with separate approval/recovery acceptance, not a next-button extension of copy mode.
- No storage-reclamation or source-safe-to-erase claim follows from copy verification.
- Model-assisted interpretations, if later justified, need local/private defaults, explicit provider/data disclosure and no silent fallback to cloud calls.

### Research and platform coverage

- Observe beginner comprehension: ask what will change, what stays, which files are unknown, how much extra space is required and whether they can undo before letting them proceed. No such participant session has yet occurred.
- Screen-reader and physical macOS/Linux acceptance, Safari/Firefox, long translated labels, high zoom and broad volume fixtures remain unverified.
- The mobile browser view is useful for layout/accessibility checks; it does not claim supported mobile filesystem execution.
- Product readiness, commercial packaging, signing, monetisation and distribution remain separate gates. No paid test is justified by this UX checkpoint.

## Product direction added from supplied comments

The user supplied further product comments on 2026-10-06. Their central proposal is adopted as product direction, not as evidence that any capability is implemented: **a read-only Disk Map is the main product path**. This checkpoint is only a top-level extension overview and restricted copy-review foundation. It does not implement a Disk Model, semantic understanding, project discovery, version relationships or cross-drive accounting. The competitor page check below distinguishes advertised capabilities from tested behaviour. Platform-policy assertions in the comments are not treated as verified implementation requirements.

The next read-only model/UX contract must include:

- An explicit authorised root/scope, scan time and coverage boundary. Inaccessible folders, nested exclusions, mount boundaries and unsupported sources remain visible; incomplete inventory cannot become a complete-space claim.
- Stable references for observed files/folders, logical byte totals and relationships, separate from any proposed organisation. Apparent duplicate/version/export/backup relationships are not automatic removal candidates.
- Observations separated from inferences. Every project/archive/inbox/cache classification carries its supporting paths, signals, counter-evidence, confidence/uncertainty and limitations. The UI opens that evidence from the conclusion itself.
- Storage views organised around meaningful groups and unanswered questions, with an ordinary directory/path view retained as supporting evidence. Avoid a chart whose apparent precision exceeds the scan's coverage.
- Read-only coherent plan comparisons with typed steps, dependencies, reasons, uncertain files left unchanged and expected consequences. No Apply button is implied by rendering such a plan.
- User corrections that refine the interpretation without immediately mutating files. A rejected inference remains distinguishable from a deleted file or dismissed warning.
- No guessed recoverable space, safe-to-erase status or backup redundancy based on similarity, filename patterns or a local copy. Logical size is not physically reclaimable size.
- Optional later semantic models behind explicit data/provider disclosure. No direct LLM filesystem authority, content upload, broad disk-access request or silent cloud fallback.

Sequence: bounded read-only inventory/model → deterministic evidence-backed relationships → Disk Map and evidence drill-down → read-only coherent plans → independently reviewed transaction/recovery semantics → separately gated application on synthetic fixtures. Existing copy mode is a restricted experiment alongside this path, not a reason to skip it. A new model owner and UX owner should agree on the structured schema before implementing relationship-specific views.


## Review repair checkpoint

Independent source and ordinary read-only review found five gaps: a stale API test blocked CI before screenshots; three core errors invited unavailable recovery; history refresh kept a restarted backend's stale token; scan capability was ignored; and several read-only messages implied copying. All are repaired in this checkpoint. Explicit refresh now renews session/capabilities and reads history before unlocking work, with no automatic retry. Missing/unsupported scan capability is fail-closed while history stays usable. The engine changes are only three message strings (AST structure verified unchanged); no mutation policy or recovery implementation changed.

Local repair verification: 34 UI tests, frontend formatting, JavaScript syntax, one focused default-UI API test and focused backend lint passed. The initial exact-head CI run `37502869039` failed the former “Guided copies” content assertion and produced no browser artifact. New exact-head CI and image review are still required. Reviewer testing remains ordinary read-only behaviour; no prohibited probe or experimental operation is required for confirmation.


## First-party competitor check, 6 October 2026

These are advertised capabilities and asking prices, not measured reliability, sales or retention. No competing software was purchased, installed or tested.

- [Cosmos US listing](https://apps.apple.com/us/app/cosmos-ai-files-assistant/id6759027625?mt=12): $24.99; advertises local organisation, approval/undo, search and learning. Recent releases include project grouping and broader document analysis, so project-oriented organisation is already represented.
- [Gather US listing](https://apps.apple.com/us/app/gather-smart-file-manager/id6786433086?mt=12): free tier and $9.99 one-time Pro purchase; advertises on-device analysis, rules, simulation, history and individual/batch/session undo.
- [MintFolder Local](https://app.mintfolder.ai/local?lang=en): advertises review, collision checks, batch journalling and interrupted-operation recovery. Its stated last-batch undo is not evidence of arbitrary historical recovery.
- [Tidium listing](https://apps.apple.com/pl/app/tidium-ai-file-organizer/id6788663430?mt=12): advertises content-aware organisation, renaming/search, duplicate cleanup and previews, with local processing by default and optional cloud processing. This Polish listing is not a US price source.

The read-only Disk Model/Map is a coherent direction, not an uncontested feature gap. Differentiation must be demonstrated through useful project/version relationships, transparent uncertainty and trustworthy handling of messy storage. A feature checklist or an “AI organiser” label does not establish that value.


## Rendered review evidence

[Repair CI 37505119893](https://github.com/krahd/disk_organiser/actions/runs/37505119893) passed at `e7fb60a90e12c3156135708f9339695b1be52c17`: Linux 171 tests; Windows 151 passed / 20 unsupported skipped; 34 UI tests; 12 Chromium tests (nine guided scenarios plus three retained browser tests). Both audits, formatting and OpenAPI checks passed. [Artifact 11431556871](https://github.com/krahd/disk_organiser/actions/runs/37505119893/artifacts/11431556871) was downloaded and SHA-256 verified (`ab7a7db31b386c4495d0362e3b8e1fe99bc5b649ee5133f77515736b3b6d938f`); all 13 screenshot files were visually inspected.

The rendered states show legible desktop comparisons, stacked 390 px exact-path cards, preserved focus, visible full-plan scope under filtering, unavailable copy controls in default mode, explanatory unsupported-platform and session-reconnected states, and retained history without removal controls. No clipping or horizontal overflow was observed in these fixture views. Long history remains vertically verbose and belongs to the backlog; this is not a beginner participant study, screen-reader certification or physical-device acceptance.

That pixel review prompted a final wording pass: singular copy/folder counts, a neutral “Inspect exact paths” step, and no instruction to start a scan in unsupported empty history. Local UI coverage is now 35 tests. The exact final-head rerun and screenshot evidence are recorded on [draft PR 12](https://github.com/krahd/disk_organiser/pull/12), rather than attributing the predecessor's green run to later source. Independent confirmation is still required.


### Screenshot capture synchronisation

The wording revision `b1c3f2e` passed [CI 37506088067](https://github.com/krahd/disk_organiser/actions/runs/37506088067), including 35 UI and 12 Chromium tests. Its artifact was checksum-verified and inspected, which revealed one full-page capture racing the history response: the document grew after screenshot dimensions were measured. The screenshot helper now waits for the completed UI state (except intentionally paused loading), checks the PNG height against document height, and verifies the height stays stable through capture. This changes test evidence collection only. Review should use the latest exact-head artifact linked in PR 12.
