#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install -r backend/requirements.txt
fi
export DISK_ORGANISER_OPEN_BROWSER=${DISK_ORGANISER_OPEN_BROWSER:-1}
exec "$VENV/bin/python" -m backend.app
