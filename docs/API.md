API
===

This is a concise reference for the backend endpoints. All endpoints are
served under the root host (default `http://127.0.0.1:5000`). The examples use
`curl` and `application/json` payloads.

The machine-readable spec lives in `docs/openapi.json` and is validated in CI by
`scripts/validate_openapi.py`.

- `GET /` — health-check. Returns `{message: "Disk Organiser API running"}`.

- `POST /api/duplicates` — find duplicates
  - Body: `{paths: [...], min_size: int, max_files: int}`
  - Response: `{duplicates: [...], count: N}`

- `POST /api/visualisation` — lightweight folder visualisation
  - Body: `{path: str, depth: int, include_insights?: bool}`
  - Response: `{visualisation: {...}, insights?: {...}, analysis_summary?: {...}}`

- `POST /api/organise` — deterministic heuristic suggestions
  - Body: `{duplicates: [...]}`
  - Response: `{suggestions: [...]}`

- `POST /api/organise/suggest` — AI-assisted suggestions (if configured)
  - Body: `{duplicates: [...]}`
  - Response: `{suggestions: [...]}`

- `POST /api/organise/preview` — create an operation (preview)
  - Body: `{suggestions: [...]}` or `{actions: [...]}`
  - Response: grouped preview payload with `op`, `actions`, `summary`, `grouped`

- `POST /api/organise/remove-preview` — create a remove-preview operation
  - Body: `{duplicates: [...]}`
  - Response: `{op: {...}}`

- `POST /api/organise/execute` — execute an operation
  - Body: `{op_id: <id>, selected_actions?: [int], create_snapshot?: bool}`
  - Response: `{executed: [...]}`

- `POST /api/organise/undo` — undo executed operation
  - Body: `{op_id: <id>}`
  - Response: result object

- `GET /api/model` — get selected model
- `POST /api/model` — set model: `{model: 'ollama'|'gpt'|...'}
- `GET /api/preferences` — get saved user preferences
- `POST /api/preferences` — set preferences: `{preferences: {...}}`

Background scan endpoints

- `POST /api/scan/start` — start a background scan (returns job_id)
- `GET /api/scan/status/<job_id>` — check job status
- `GET /api/scan/events/<job_id>` — SSE stream for incremental job updates
- `POST /api/scan/cancel` — cancel a job: `{job_id: <id>}`

Analysis endpoints

- `POST /api/analyse/start` — build rich file contexts in the background
  - Body: `{paths: [...], min_size?: int, max_files?: int}`
  - Response: `{job_id: <id>, backend: "thread"}`

- `POST /api/analyse/reason` — ask the model layer to plan reversible actions
  - Body: `{job_id: <id>}` or `{paths: [...], preferences?: {...}}`
  - Response: grouped preview payload with `op`, `actions`, `summary`, `grouped`, `backup_status`, `rejected`
  - Notes:
    - Contexts include content-aware near-duplicate signals.
    - Current strategies include:
      - sampled text-term overlap for text/code files,
      - PDF body extraction (`pypdf` with fallback parser),
      - DOCX body extraction (OOXML parsing),
      - image perceptual hashing (`Pillow` + `ImageHash`).

- `POST /api/chat` — refine an analysis operation conversationally
  - Body: `{op_id: <id>, message: "..."}`
  - Response: same grouped preview payload as `/api/analyse/reason`

Recycle / ops endpoints

- `GET /api/recycle/list` — list recycle/backups
- `POST /api/recycle/cleanup` — cleanup old backups
- `GET /api/ops` — list ops
- `GET /api/op/<op_id>` — get op
- `GET /api/ops/<op_id>/preview` — grouped diff-style preview for an op
  - Each action may include `near_duplicate_signals` (or `metadata.signals`) so
    the frontend can explain why files were clustered.
- `POST /api/recycle/delete_op` — delete an op

Scan index endpoints (optional, if scan index module is enabled)

- `GET /api/scan_index/stats` — current index stats
- `POST /api/scan_index/rebuild` — synchronous index rebuild
- `POST /api/scan_index/rebuild_async` — async index rebuild
- `POST /api/scan_index/prune` — prune missing entries

Maintenance endpoints

- `GET /api/maintenance/status` — get maintenance mode status
- `POST /api/maintenance/run` — run maintenance workflow
- `GET /api/safety/backup-status` — get macOS Time Machine / backup status

Validation notes

- Integer fields like `min_size` and `depth` must be `>= 0`; invalid values
  return HTTP `400`.
- `POST /api/scan/start` accepts either `paths: [...]` or `path: "..."`;
  each path must be a non-empty string.
- Analysis deletes are gated by confidence; low-confidence deletes are rejected
  before an operation preview is created.

OpenAPI drift is guarded in CI. If you add or rename a Flask route, update both
`docs/openapi.json` and this file in the same change.

Comprehensive verification commands

- `source venv/bin/activate && pytest -q backend/tests`
- `source venv/bin/activate && python scripts/validate_openapi.py`
- `npm test --silent`
- `npm run format:check`
- `npm run start` (in one terminal) and `npm run test:visual` (in another)
