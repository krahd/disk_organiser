# Guided manual planning workspace

## Status and launch

`frontend/manual-workspace.html` is a separate local planning workspace for real user-entered names and inert path notes. Open that file with its sibling `manual-workspace.css`, `manual-workspace.js` and `manual-planning-model.js` present. No backend is needed. It does not replace the existing application or Aurora's synthetic project-review page.

The prototype starts with an empty plan. It contains no sample records unless the user explicitly opens one of the clearly labelled illustrative JSON fixtures. No default navigation, execution/recovery flag, backend route, provider integration or deployment is changed.

Independent source/DOM review accepted the frozen runtime with no remaining source/DOM blockers. All 43 integration checks and separate guided-only, import-race, history and failure-path probes passed. Local browser execution is blocked by process-socket restrictions; no local screenshot, real keyboard-focus trap, responsive geometry, browser-zoom or screen-reader acceptance is claimed. The dedicated hosted workflow must pass on the exact combined source, and a reviewer must inspect the original screenshots before visual acceptance or merge.

Published source `4b681288` passed seven hosted Chromium flows, but original pixels exposed narrow-screen Close/Rename wrapping and count wording that needed correction. The focused repair has new 320-pixel/200% CSS-zoom single-line, 44-pixel-control and title-separation assertions. Its regenerated exact-source screenshots and CI remain required; earlier passing runs do not establish the repair.

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

Seven Chromium specifications are supplied and list successfully. They are not locally executed: they cover a guided real-manual journey with actual download/reopen; mixed reports/import-preview cancellation and an intercepted empty file-chooser selection; 320 CSS-pixel mobile and dialogues; 200% CSS zoom; keyboard entry/cancellation/focus; long hostile-looking inert labels; and direct `file://` launch. The last two deliberately use owned test text only. The intercepted empty selection is not automation of an OS-native Cancel button. CSS zoom is not a claim of native browser-UI zoom or screen-reader acceptance.

The workflow `manual-planning-workspace.yml` uses existing locked dependencies on Linux and Windows for model/DOM checks, then Chromium on Linux for a hash-manifested original-screenshot-only ZIP whose complete measured size, including the manifest and ZIP headers, must be at most 30 MiB, in the `manual-planning-workspace-screens` artifact. Only the successfully measured ZIP is uploaded; failed collection cannot upload an earlier packet. Browser failure extras are uploaded separately. It has read-only repository permissions and does not deploy. Model, UI and screenshot results must refer to the same candidate; a listed test is not a passed test.

## Remaining product gates

Independent visual inspection of the original hosted screenshots; representative keyboard and screen-reader usability; nontechnical participant success on the first-project journey; representative browser download/reopen behaviour; and any future scanner/provider/backup integration remain separate gates. This local-only planning workspace supplies no live filesystem, backup or recovery evidence and no authority to erase data.
