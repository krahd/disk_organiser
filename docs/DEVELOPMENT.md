Development
===========

Setup
-----

Recommended Python workflow (macOS / Linux):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Run the API for local development:

```bash
python backend/app.py
```

Run the background worker (optional - required for RQ/Redis setups):

```bash
python backend/worker.py
```

Testing
-------

Run the test-suite with `pytest`:

```bash
pytest -q backend/tests
```

Linting
-------

The project uses `flake8` as configured at the repository root. Run it with:

```bash
flake8
```

Model provider development
--------------------------

Provider implementations live under `backend/model_wrappers/`. A provider is
expected to expose a `suggest_organise(duplicates)` function that accepts the
duplicate groups and returns a list of suggestions in the same form the
backend expects (see `backend/model_client.py`). See
`docs/MODEL_INTEGRATION.md` for details and an example provider.

Notes
-----

- Many modules attempt to import optional dependencies dynamically so the
  codebase remains usable in minimal environments.
- When editing critical file operations, prefer small, well-tested changes to
  avoid data-loss risk.
