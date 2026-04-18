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

Frontend
--------

Open `frontend/index.html` in a browser. The UI is intentionally minimal and
targets local development and quick inspections. It assumes the API runs on
`http://127.0.0.1:5000`.
