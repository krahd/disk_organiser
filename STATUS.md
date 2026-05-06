# Disk Organiser - Status Report

Date: 2026-05-06

## Executive Summary

The repository is now in a phase where semantic analysis, typed reversible actions,
and conversational refinement are implemented end-to-end.

The major architecture shift has already happened:

- from duplicate-only suggestions,
- to context-driven analysis with grouped preview, selective execution, and undo.

A comprehensive test pass was executed on this date and is green.

## Implemented Capabilities

### Analysis Pipeline

Implemented:

- background context build via POST /api/analyse/start
- reasoning phase via POST /api/analyse/reason
- conversational refinement via POST /api/chat
- grouped operation preview via GET /api/ops/<op_id>/preview

Context includes:

- path/name/extension/mime/size/mtime
- stale-file heuristics
- near-duplicate signals and scores

### Near-Duplicate Detection (Content-Aware)

Current strategies in backend/context_builder.py:

- normalized filename/token similarity
- sampled content term overlap for text-like files
- PDF body extraction (pypdf with fallback parser)
- DOCX body extraction (OOXML parsing)
- image perceptual hashing (Pillow + ImageHash)
- size similarity

Exposed fields:

- near_duplicate_key
- near_duplicate_group_size
- near_duplicate_signals
- near_duplicate_score

### Safe Operation Lifecycle

Implemented and active:

- typed actions (move, delete_stale, create_symlink, reorganise_folder)
- operation preview before execute
- backup before mutate
- undo in reverse action order
- action validation constrained to scan roots

### Frontend Workflow

Organise tab now supports:

- running analysis
- grouped diff-like action preview
- per-action selection and selective execution
- chat-based refinement
- signal visibility for why items were clustered

Visualisation tab supports:

- include_insights mode
- folder-level semantic/stale summary panels

### Safety and Governance

Implemented:

- macOS backup status endpoint (GET /api/safety/backup-status)
- optional local snapshot trigger during execution
- OpenAPI route drift check (scripts/validate_openapi.py)
- CI route coverage validation against docs/openapi.json

## Comprehensive Test Results (2026-05-06)

Executed successfully:

- source venv/bin/activate && pytest -q backend/tests
  - Result: 27 passed
- source venv/bin/activate && python scripts/validate_openapi.py
  - Result: OpenAPI validation passed for 31 routes
- npm test --silent
  - Result: 1 suite passed, 2 tests passed
- npm run format:check
  - Result: all matched files use Prettier code style
- npm run test:visual (with npm run start server running)
  - Result: 2 Playwright tests passed

## Current Risks / Gaps

1. Embedding-based similarity is not implemented yet.
2. OCR is not implemented for scanned documents/images.
3. Windows-specific runtime behavior is not validated by dedicated CI.
4. Frontend test depth is still limited (modal + visual smoke vs broad unit coverage).

## Recommended Next Steps

1. Add optional embedding-based similarity for hard near-duplicate cases.
2. Add OCR-assisted extraction path for scanned PDFs/images.
3. Add a Windows CI lane to validate path and filesystem behavior.
4. Expand frontend unit tests for Organise analysis flow (selection, chat refine, execution payloads).

## Repository Documentation Alignment

This report reflects the current state and supersedes earlier planning assumptions
that marked semantic analysis, near-duplicate detection, and conversational flow
as unimplemented.
