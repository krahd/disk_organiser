# Model Integration Guide

This document describes the provider contract, loading rules, configuration, and testing guidance
for integrating external model providers into Disk Organiser.

Purpose
-------

- Explain how `ModelClient` discovers and loads providers.
- Define the minimal provider contract (`suggest_organise`) expected by the application.
- Show how to configure and test providers locally and in CI.

Provider contract
-----------------

Providers must expose a callable named `suggest_organise` with the following behaviour:

- Signature: `suggest_organise(duplicates: List[dict]) -> List[dict]`
- Input: `duplicates` is a list of groups produced by `backend.utils.find_duplicates()`; each
  group is a mapping with a `files` list where each file is a mapping containing at least `path` and `size`.
- Output: a list of suggestion objects. Each suggestion should be a dict with at minimum:
  - `keep`: path to the file to keep
  - `moves`: a list of operations: `[{"from": <src_path>, "to": <dst_path>}, ...]`

Example suggestion (JSON-friendly):

```json
[
  {
    "keep": "/path/to/keep/file.txt",
    "moves": [
      {"from": "/path/to/dup1.txt", "to": "/path/to/Duplicates/dup1.txt"}
    ]
  }
]
```

Provider resolution and naming
-------------------------------

`ModelClient` looks up providers using the following resolution order (see `backend/model_client.py`):

1. If a `provider_name` is supplied when constructing `ModelClient` or passed to `reload()`, it is tried as a
   direct import (e.g. `import <provider_name>`).
2. `backend.model_wrappers.<provider_name>` is attempted.
3. `model_wrappers.<provider_name>` is attempted.
4. If no provider is specified, `ModelClient` tries to import a top-level `model_wrapper` module.

The environment variable `MODEL_PROVIDER` may be used to choose a provider at runtime.

Built-in/dev provider
----------------------

A CI/dev provider is included at `backend/model_wrappers/ci_dummy.py`. It implements the same contract and
returns deterministic suggestions (it places moved files in an `AI_Duplicates` folder). This provider is useful
for development and CI to avoid relying on external APIs or keys.

How to add a provider
---------------------

1. Create a module implementing `suggest_organise(duplicates)`.
   - Preferred location for repository providers: `backend/model_wrappers/<your_provider>.py`.
2. Ensure the module is importable by Python (add an `__init__.py` if packaging or place it on `PYTHONPATH`).
3. You can reference it by name (e.g. `ci_dummy`) or by full module path `backend.model_wrappers.ci_dummy`.
4. Prefer fast, deterministic responses and handle transient API errors internally. `ModelClient` will fall back
   to a safe heuristic if the provider raises an exception.

Example minimal provider
```python
def suggest_organise(duplicates):
    suggestions = []
    for group in duplicates:
        files = group.get('files', [])
        if len(files) <= 1:
            continue
        keep = files[0]['path'] if isinstance(files[0], dict) else files[0]
        moves = []
        for f in files[1:]:
            src = f['path'] if isinstance(f, dict) else f
            dst = os.path.join(os.path.dirname(keep), 'AI_Duplicates', os.path.basename(src))
            moves.append({'from': src, 'to': dst})
        suggestions.append({'keep': keep, 'moves': moves})
    return suggestions
```

Configuration (runtime and API)
-------------------------------

- To set the provider at runtime you can export the environment variable:

```bash
export MODEL_PROVIDER=ci_dummy
```

- Or set it via the API (this calls `ModelClient.reload` under the hood):

  - `POST /api/model` with JSON `{ "model": "ci_dummy" }` — the server saves the selection and attempts to reload
    the provider immediately.

Endpoints and usage
-------------------

- Use the AI-assisted endpoint `POST /api/organise/suggest` to request model-driven suggestions.
- The original heuristic endpoint `POST /api/organise` remains available as a safe fallback.
- After receiving suggestions, call `POST /api/organise/preview` to create an operation, then
  `POST /api/organise/execute` and `POST /api/organise/undo` as part of the preview/execute/undo lifecycle.

Files of interest
-----------------

- `backend/model_client.py` — provider loading and `ModelClient` implementation.
- `backend/model_wrappers/ci_dummy.py` — CI/dev provider implementation.
- `backend/app.py` — endpoints: `/api/organise/suggest`, `/api/organise`, and `/api/model`.
- `frontend/main.js` — frontend calls `POST /api/organise` by default; switch to `/api/organise/suggest` to use AI.
- `backend/tests/` — unit and integration tests include examples for using the `ci_dummy` provider.

Testing and CI
--------------

- The repository contains tests that run with the `ci_dummy` provider; no external keys are required.
- Run the test-suite locally:

```bash
source venv/bin/activate
pip install -r backend/requirements.txt
python -m pytest -q
```

- To specifically run provider tests:

```bash
python -m pytest backend/tests/test_model_client.py -q
python -m pytest backend/tests/test_integration_ai_flow.py -q
```

Safety and performance notes
----------------------------

- Providers should avoid long synchronous calls. If calls may be slow, consider running model-driven
  work in a background task and returning job IDs to the UI.
- `ModelClient` contains a deterministic heuristic fallback; if a provider raises an exception or is missing,
  the fallback is used to ensure the app remains functional and safe.

Change log
----------

- `ci_dummy` added as a local provider for development and CI (see `backend/model_wrappers/ci_dummy.py`).
- `ModelClient` now supports runtime `reload()` and provider selection via `MODEL_PROVIDER` or `/api/model`.

Contact/next steps
------------------

If you want, I can:

- Add an example `model_wrapper` for Ollama or another provider.
- Update `frontend/main.js` to optionally call `/api/organise/suggest` when the user toggles AI suggestions.
- Add a short CONTRIBUTING section about adding new providers.
