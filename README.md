# Disk Organiser

Small prototype to visualise and help organise a filesystem. Backend is a Flask API and frontend is a minimal static UI.

Quick start (macOS / Linux):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
python backend/app.py
```

Open `frontend/index.html` in a browser and use the UI. The frontend uses `http://127.0.0.1:5000` as the API host.

Background jobs (optional):

- Install Redis and run it locally or via docker-compose:

```bash
docker-compose up -d redis
```

- Start a worker:

```bash
python backend/worker.py
```

Deployment with Docker:

```bash
docker-compose up --build
```
