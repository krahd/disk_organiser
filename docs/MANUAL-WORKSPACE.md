# Guided manual planning workspace

## Status and launch

`frontend/manual-workspace.html` is a separate local planning workspace for real user-entered names and inert path notes. Open that file with its sibling `manual-workspace.css`, `manual-workspace.js` and `manual-planning-model.js` present. No backend is needed. It does not replace the existing application or Aurora's synthetic project-review page.

The prototype starts with an empty plan. It contains no sample records unless the user explicitly opens one of the clearly labelled illustrative JSON fixtures. No default navigation, execution/recovery flag, backend route, provider integration or deployment is changed.

Independent source/DOM review accepted the frozen runtime with no remaining source/DOM blockers. All 43 integration checks and separate guided-only, import-race, history and failure-path probes passed. Local browser execution is blocked by process-socket restrictions; no local screenshot, real keyboard-focus trap, responsive geometry, browser-zoom or screen-reader acceptance is claimed. Repaired source `eb5f226ece95b70dd0d3e85de6c7cc026b574c73` passed the dedicated hosted workflow and independent inspection of all eleven original screenshots; these establish bounded Chromium and visual acceptance for that source.

Published source `4b681288` passed seven hosted Chromium flows, but original pixels exposed narrow-screen Close/Rename wrapping and count wording that needed correction. The focused repair has new 320-pixel/200% CSS-zoom single-line, 44-pixel-control and title-separation assertions. The regenerated exact-source screenshots and CI passed, closing those findings. The initial passing runs are not used as evidence for the repaired version.

## A useful first journey

1. Name a project, such as Family photos.
2. Add a folder or file and name its current location. An exact path is optional. The short dialogue can create the named drive at the same time.
3. Compare **Locations you recorded** with the dashed **Intended arrangement**. Set or correct the intended home without changing a recorded source.
4. Name planned backup targets and, if useful, choose scope exclusions, frequency or retention. Every target remains planned and backup coverage remains unknown.
5. Prepare a restore checklist: choose a target, selected scopes and sample description. Default check descriptions can be edited; custom checks can be added. Any actual restore happens in the user's own tool.
6. Save a private plaintext plan file, confirm the download in the browser, and explicitly reopen it to resume the same records.

The same four-step canvas works without Show details. Show details exposes record keys, precise paths, full JSON, archived/unselected target records and historical context. It is only a presentation preference; toggling it does not change the plan or permissions.

## Corrections and historical records

Names, recorded locations, intended homes, project membership and target choices are editable. Archive is reference-preserving: it does not silently remove a project member, planned target, exclusion or result. There is no file-operation undo control and no delete action in this UI. An archived record can be made active again.

Before the first self-report, require a chosen target, nonempty scope selection, decided scope intent and a meaningful sample description. At the first report, the model saves immutable descriptions of the target, project, selected items and relevant named locations. The UI renders that saved context for the exercise, so correcting a current drive/target/item cannot rename an old report. It explains current-versus-recorded drift. Imported context is an unverified claim, not authenticated evidence.

Results-bearing exercise target, scope, snapshot, destination and check definitions are frozen. “Prepare a new exercise” creates new exercise/check keys and no inherited reports. Existing failures stay visible beside later passes; there is no whole-project success score. A deliberate submit records one report; repeated submit events after closure cannot duplicate it.

## Save/open boundary

- The only file read is one explicitly selected planning JSON artifact. The UI checks its size before allocation and decodes UTF-8 with fatal errors and BOM preservation; the strict model parser then enforces bounds, duplicate-key rejection, exact schema version, references and lifecycle invariants.
- Import shows title/count/privacy/caution preview before explicit replacement. Cancellation, malformed content, oversized input, unreadable input and obsolete asynchronous reads preserve the current workspace. Starting a newer picker, editing, cancelling or changing model state invalidates pending reads.
- Export is the complete model representation. A successful click says “Plan download requested; confirm it in Downloads”. The tab keeps its unsaved-warning state until the user acknowledges saving that revision or reopens a document.
- No browser storage, accounts, telemetry, external fonts/scripts, provider requests or arbitrary path access. A restrictive CSP denies network connections and form submissions. User/imported strings are text nodes. The exported artifact is plaintext, not encrypted, and includes manually entered private path/notes categories.

## Verification

With the existing locked Node dependencies installed:

```sh
npx jest --config jest.config.js --runInBand frontend/__tests__/manual-planning-model.test.js
node scripts/test_manual_workspace.cjs
npx playwright test --config playwright.manual-workspace.config.js
```

The DOM runner uses only owned fixtures, denies unexpected resource loads and covers the complete guided journey, unknown coverage, current/intent separation, safe text, same-state detail toggling, private export/reopen, malformed UTF-8/BOM/JSON/future versions, cancellation, asynchronous import races, nonblank/whole-drive prerequisites, archiving/reference retention, custom checklist edits, repeat-submit protection and mixed immutable report history.

All seven Chromium specifications passed on the hosted repaired-source run; they were not locally executed: they cover a guided real-manual journey with actual download/reopen; mixed reports/import-preview cancellation and an intercepted empty file-chooser selection; 320 CSS-pixel mobile and dialogues; 200% CSS zoom; keyboard entry/cancellation/focus; long hostile-looking inert labels; and direct `file://` launch. The last two deliberately use owned test text only. The intercepted empty selection is not automation of an OS-native Cancel button. CSS zoom is not a claim of native browser-UI zoom or screen-reader acceptance.

The workflow `manual-planning-workspace.yml` uses existing locked dependencies on Linux and Windows for model/DOM checks, then Chromium on Linux for a hash-manifested original-screenshot-only ZIP whose complete measured size, including the manifest and ZIP headers, must be at most 30 MiB, in the `manual-planning-workspace-screens` artifact. Only the successfully measured ZIP is uploaded; failed collection cannot upload an earlier packet. Browser failure extras are uploaded separately. It has read-only repository permissions and does not deploy. Model, UI and screenshot results refer to the same repaired source. Future changes require fresh exact-source execution and original screenshot inspection.

### Exact-source evidence

The repaired source has all eight push/PR workflows green. Its [manual workspace run](https://github.com/krahd/disk_organiser/actions/runs/37891910411) confirms 199 model tests and 43 DOM checks on Linux and Windows, plus all seven Chromium flows. The guided browser journey asserts no external requests, performs a real browser download/reopen and preserves recorded/intended distinctions. Additional geometry assertions check one-line controls, minimum 44-pixel dimensions and title separation at 320 CSS pixels and 200% CSS zoom.

Original artifact `11598499076` is 2,252,150 bytes with SHA-256 `d3c3cd88507519bb4d5e54501954b4098c36477e9f636dc5c0488163bfad622a`. All eleven PNG hashes/lengths and the inner ZIP were verified. Independent visual review confirms the Close/Rename defects are fixed, the zoomed dialogue is clear, counts read naturally, and recorded/intended separation, unknown coverage and distinct self-reported pass/fail remain legible. No new clipping, overlap or unsafe success signal was found in those originals.

This documentation-only closeout preserves all runtime, tests, schema, fixtures and workflows from the tested source. Its cited runs and screenshots are not attributed to a later documentation head.

## Remaining product gates

Native OS file-dialog Cancel controls, native browser-UI zoom, screen-reader/forced-colour and reduced-motion usability, nontechnical participant success, representative additional browsers and any future scanner/provider/backup integration remain separate gates. Automated Chromium keyboard flows and inspected CSS-zoom pixels do not establish those broader claims. This local-only planning workspace supplies no live filesystem, backup or recovery evidence and no authority to erase data.
