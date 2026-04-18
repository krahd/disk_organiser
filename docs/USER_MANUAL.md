# User Manual

This user manual describes how to install, run and use Disk Organiser.

## Overview

Disk Organiser is a small prototype for visualising and safely organising files on
a local filesystem. The application ships with a Flask backend and a minimal
static frontend for interactive use.

## Requirements

- Python 3.8+ (3.11 recommended)
- Optional: Docker/Docker Compose for containerised runs

## Quick start (local)

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies and run the API:

```bash
pip install -r backend/requirements.txt
python backend/app.py
```

3. Open the frontend by opening `frontend/index.html` in a browser. The frontend
   expects the API at `http://127.0.0.1:5000` by default.

## Docker

Build and run with docker-compose:

```bash
docker-compose up --build
```

For background jobs with Redis and RQ, start Redis first and run the worker:

```bash
docker-compose up -d redis
python backend/worker.py
```

## Usage

- Use the frontend to scan folders, preview suggested moves and perform safe
  organise operations.
- The backend creates automatic backups before applying any file operations.
- Model integrations (AI suggestions) are optional and pluggable — see
  `backend/model_wrappers/` and `docs/MODEL_INTEGRATION.md` for details.

## API

See `docs/API.md` for a description of the REST endpoints, request/response
examples and error codes.

## Safety & Backups

All destructive operations performed by Disk Organiser create backup snapshots
so changes can be reverted. Review preview lists carefully before applying
operations.

## Troubleshooting

- If scans fail on large trees, increase available memory or run scans on
  smaller subdirectories.
- Check backend logs for stack traces and ensure the environment matches the
  `backend/requirements.txt` Python package versions.

## License and Disclaimer

This project is licensed under the MIT License (see the top-level LICENSE
file). The software is provided "AS IS" without warranty; use at your own risk.
