# Disk Organiser – Project Status

Last updated: 2026-05-07 00:55

## Project purpose

Disk Organiser is a local-first filesystem organisation tool. It analyses user-selected folders, proposes typed organisation actions, previews them before execution, and preserves reversible operation history through backups and undo support.

## Current implementation state

The repository currently has an implemented end-to-end semantic organisation workflow:

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

The project is currently focused on hardening semantic analysis, optional OCR/embedding capability reporting, frontend analysis-flow coverage, cross-platform filesystem behaviour, and runtime safety guarantees.

## Architecture overview

The backend scans allowed roots, builds file contexts, uses provider-backed or heuristic planning to produce typed actions, stores operations, serves grouped previews, executes selected actions safely, and supports undo. The frontend drives the analysis, preview, refinement, and execution workflow.

### Architecture diagram

The diagram shows the current backend/frontend architecture and safety boundary.

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

The flow chart shows the safe analysis-to-execution lifecycle.

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

Playwright visual tests require the frontend server:

```bash
npm run start
npm run test:visual
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

## Recent changes

- Model provider selection is normalised through Modelito.
- Ollama lifecycle management is exposed through dedicated API routes and preferences UI.
- Runtime capability flags now report optional OCR and embedding availability.
- Frontend analysis UI shows optional capability state.
- Test coverage has been expanded around context building, analysis capability payloads, and frontend selection/refinement paths.
- Public project website content and visual design were refreshed in `docs/index.html` and `docs/assets/style.css` with clearer safety messaging and updated quick-start links.

## Tests and verification status

Previously recorded successful checks:

- `pytest -q backend/tests` -> 27 passed.
- `python scripts/validate_openapi.py` -> OpenAPI validation passed for 31 routes.
- `npm test --silent` -> frontend suite passed.
- `npm run format:check` -> Prettier check passed.
- `npm run test:visual` with server running -> Playwright visual tests passed.
- Focused backend and frontend capability tests were also recorded as passing.

No tests were run while producing this documentation-only status normalisation.
No tests were run for the docs website refresh in this update.

## Known issues, risks, and limitations

- OCR and embedding enhancements are optional and only active with extra dependencies installed.
- OCR quality needs broader real-world validation on scanned and low-quality documents.
- Windows-specific path and filesystem behaviour still needs dedicated CI verification.
- Frontend analysis flow has less test depth than backend safety-critical logic.
- Live Modelito planning quality depends on configured local runtime/model availability.

## Pending tasks

- Add a Windows CI lane for filesystem/path behaviour.
- Expand frontend unit tests for failed network calls and interrupted analysis/refinement flows.
- Add integration coverage for large analysis payloads and capability indicator rendering.

## Next steps

1. Add Windows CI coverage for path and filesystem operations.
2. Expand frontend analysis-flow unit coverage.
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

Last updated: 2026-05-07 00:55
