API
===

This is a concise reference for the backend endpoints. All endpoints are
served under the root host (default `http://127.0.0.1:5000`). The examples use
`curl` and `application/json` payloads.

- `GET /` — health-check. Returns `{message: "Disk Organiser API running"}`.

- `POST /api/duplicates` — find duplicates
  - Body: `{paths: [...], min_size: int, max_files: int}`
  - Response: `{duplicates: [...], count: N}`

- `POST /api/visualisation` — lightweight folder visualisation
  - Body: `{path: str, depth: int}`
  - Response: `{visualisation: {...}}`

- `POST /api/organise` — deterministic heuristic suggestions
  - Body: `{duplicates: [...]}`
  - Response: `{suggestions: [...]}`

- `POST /api/organise/suggest` — AI-assisted suggestions (if configured)
  - Body: `{duplicates: [...]}`
  - Response: `{suggestions: [...]}`

- `POST /api/organise/preview` — create an operation (preview)
  - Body: `{suggestions: [...]}`
  - Response: `{op: {...}}` (contains `id` and `backup_dir`)

- `POST /api/organise/remove-preview` — create a remove-preview operation
  - Body: `{duplicates: [...]}`
  - Response: `{op: {...}}`

- `POST /api/organise/execute` — execute an operation
  - Body: `{op_id: <id>}`
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

Recycle / ops endpoints

- `GET /api/recycle/list` — list recycle/backups
- `POST /api/recycle/cleanup` — cleanup old backups
- `GET /api/ops` — list ops
- `GET /api/op/<op_id>` — get op
- `POST /api/recycle/delete_op` — delete an op

Scan index endpoints (optional, if scan index module is enabled)

- `GET /api/scan_index/stats` — current index stats
- `POST /api/scan_index/rebuild` — synchronous index rebuild
- `POST /api/scan_index/rebuild_async` — async index rebuild
- `POST /api/scan_index/prune` — prune missing entries

Maintenance endpoints

- `GET /api/maintenance/status` — get maintenance mode status
- `POST /api/maintenance/run` — run maintenance workflow

Validation notes

- Integer fields like `min_size` and `depth` must be `>= 0`; invalid values
  return HTTP `400`.
- `POST /api/scan/start` accepts either `paths: [...]` or `path: "..."`;
  each path must be a non-empty string.

If you need a machine-readable OpenAPI spec, I can help generate one from the
current codebase.
