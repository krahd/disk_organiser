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

- `POST /api/organise/execute` — execute an operation
  - Body: `{op_id: <id>}`
  - Response: `{executed: [...]}`

- `POST /api/organise/undo` — undo executed operation
  - Body: `{op_id: <id>}`
  - Response: result object

- `GET /api/model` — get selected model
- `POST /api/model` — set model: `{model: 'ollama'|'gpt'|...'}

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

If you need a machine-readable OpenAPI spec, I can help generate one from the
current codebase.
