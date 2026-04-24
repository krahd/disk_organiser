#!/usr/bin/env bash
set -euo pipefail

# Activate venv if present
if [ -f "./venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . ./venv/bin/activate
fi

# Start backend in background
python -m backend.app &
backend_pid=$!

# Start frontend (runs in foreground)
npm run start

# wait for backend when frontend exits
wait ${backend_pid}
