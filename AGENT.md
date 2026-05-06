# AGENT.md - Disk Organiser

This guide is for coding agents working in this repository.

## Project Summary

Disk Organiser is a local-first filesystem organisation tool with:

- Python/Flask backend in backend/
- Vanilla JS frontend in frontend/
- Preview-first and reversible operations (backup + undo)
- Optional model providers via backend/model_wrappers/

The current product focus is semantic analysis of a drive and safe execution of typed actions.

## High-Level Architecture

- backend/app.py: API routes and orchestration
- backend/context_builder.py: rich file context generation and near-duplicate signals
- backend/model_client.py: provider dispatch + heuristic fallback planning
- backend/action_planner.py: normalization and validation of typed actions
- backend/fs_ops.py: action previews and execution helpers
- backend/op_store.py: SQLite operation store, backups, undo
- backend/tasks.py: background jobs for scan/analyse
- frontend/main.js: analysis workflow UI (grouped preview + chat refinement)

## Core APIs

- POST /api/analyse/start: builds contexts in background
- POST /api/analyse/reason: creates analysis-backed operation preview
- POST /api/chat: refines current operation via natural language
- GET /api/ops/<op_id>/preview: grouped action preview
- POST /api/organise/execute: execute selected action indexes
- POST /api/organise/undo: undo operation (supports dry_run)
- GET /api/safety/backup-status: macOS backup status

Full details: docs/API.md and docs/openapi.json

## Near-Duplicate Detection (Current)

Implemented in backend/context_builder.py.

Signals include:

- normalized filename/token similarity
- sampled content-term overlap (text-like files)
- PDF text extraction (pypdf with fallback parser)
- DOCX text extraction (OOXML parsing)
- image perceptual hashing (Pillow + ImageHash)
- size similarity

Output fields include:

- near_duplicate_key
- near_duplicate_group_size
- near_duplicate_signals
- near_duplicate_score

Preview actions can expose these signals via near_duplicate_signals or metadata.signals.

## Safety Contract

Do not break these invariants:

1. Preview first for destructive changes.
2. Backup before mutate.
3. Undo restores in reverse execution order.
4. Validation keeps actions inside allowed roots.

## Dependencies

When adding dependencies, update both:

- backend/requirements.txt
- backend/requirements-locked.txt

Current near-duplicate stack includes Pillow, ImageHash, pypdf.

## Testing Workflow

Backend and API spec:

```bash
source venv/bin/activate
pytest -q backend/tests
python scripts/validate_openapi.py
```

Frontend unit and formatting:

```bash
npm test --silent
npm run format:check
```

Playwright visual tests (requires running frontend server):

```bash
# terminal 1
npm run start

# terminal 2
npm run test:visual
```

## Coding Conventions

- Keep backend Python 3.12 compatible.
- Preserve dual-import fallback patterns in backend modules where present.
- Prefer additive, minimal-risk changes over broad refactors.
- Keep API docs and OpenAPI spec in sync with route changes.
- Keep STATUS.md up to date whenever implementation state, testing status, or major project direction changes.

## Current Gaps (Realistic)

- No embedding-based semantic similarity yet.
- No OCR pipeline for scanned PDFs/images.
- Windows-specific path/ops behavior needs dedicated CI verification.
- Frontend analysis flow needs deeper unit test coverage beyond modal tests.
