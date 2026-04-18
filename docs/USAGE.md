Usage
=====

This document covers common user workflows for Disk Organiser.

Quick scan and duplicates
-------------------------

1. Start the backend API (see README for quick start):

```bash
source venv/bin/activate
python backend/app.py
```

2. Scan a folder for duplicates using the API (example with `curl`):

```bash
curl -s -X POST http://127.0.0.1:5000/api/duplicates \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/path/to/scan"], "min_size": 1}'
```

The endpoint returns a JSON object with `duplicates` (list of groups) and
`count`.

Preview organise suggestions
----------------------------

You can preview suggested organise actions locally without applying them:

```bash
curl -s -X POST http://127.0.0.1:5000/api/organise \
  -H "Content-Type: application/json" \
  -d '{"duplicates": [{"files": ["/a/1.txt","/a/2.txt"]}]}'
```

AI-assisted suggestions
-----------------------

If a model provider is configured via the UI or `MODEL_PROVIDER`/saved config,
you can request AI-assisted suggestions:

```bash
curl -s -X POST http://127.0.0.1:5000/api/organise/suggest \
  -H "Content-Type: application/json" \
  -d '{"duplicates": [{"files": ["/a/1.txt","/a/2.txt"]}]}'
```

Executing and undoing operations
--------------------------------

- Use `/api/organise/preview` to create a preview operation (this creates a
  backup directory and returns an `op.id`).
- Use `/api/organise/execute` with the `op_id` to apply moves. Originals are
  backed up automatically.
- If needed, `/api/organise/undo` will attempt to restore backups for the
  given operation id.

Safe mode / Dry-run
--------------------

Many destructive endpoints support a non-destructive preview mode via the
`dry_run` boolean parameter. When `dry_run` is `true` the server will compute
and return the actions it would take without modifying files on disk. This is
useful to inspect moves, backups and cleanup operations before applying them.

Supported endpoints (examples):

- `/api/organise/execute` — POST JSON: `{"op_id": "<id>", "dry_run": true}`
- `/api/organise/undo` — POST JSON: `{"op_id": "<id>", "dry_run": true}`
- `/api/scan/start` — POST JSON: `{"paths": [...], "dry_run": true}` (scan runs but job-status files are not written)
- `/api/recycle/cleanup` — POST JSON: `{"retention_days": 30, "dry_run": true}`
- `/api/recycle/delete_op` — POST JSON: `{"op_id": "<id>", "dry_run": true}`
- `/api/scan_index/prune` — POST JSON: `{"retention_days": 30, "max_entries": 10000, "dry_run": true}`
- `/api/maintenance/run` — POST JSON: same as `prune` and supports `dry_run`
- `/api/model` and `/api/preferences` — POST JSON may include `"dry_run": true` to preview config changes without saving

Example: preview an organise operation without moving files

```bash
curl -s -X POST http://127.0.0.1:5000/api/organise/execute \
  -H "Content-Type: application/json" \
  -d '{"op_id": "abc123", "dry_run": true}'
```

The response will include a `preview` array describing each planned action
and a `summary` with counts and byte estimates.

Frontend
--------

Open `frontend/index.html` in a browser. The UI is intentionally minimal and
targets local development and quick inspections. It assumes the API runs on
`http://127.0.0.1:5000`.

Screenshots
-----------

Here are a couple of screenshots showing the main visualisation and the
duplicate-finder UI (placeholders). When browsing on GitHub the images are
served from the `frontend/images/` folder:

![](../frontend/images/screenshot-1.svg)

![](../frontend/images/screenshot-2.svg)

