#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="$ROOT_DIR/venv/bin/python3"
HTTP_SERVER="$ROOT_DIR/node_modules/.bin/http-server"

if [[ ! -x "$PYTHON" ]]; then
  printf 'Python environment missing. Run ./scripts/bootstrap.sh first.\n' >&2
  exit 2
fi
if [[ ! -x "$HTTP_SERVER" ]]; then
  printf 'Frontend dependencies missing. Run ./scripts/bootstrap.sh first.\n' >&2
  exit 2
fi
if ! "$PYTHON" -c 'import flask' >/dev/null 2>&1; then
  printf 'Python dependencies are incomplete. Run ./scripts/bootstrap.sh first.\n' >&2
  exit 2
fi

cleanup() {
  if [[ -n "${backend_pid:-}" ]]; then
    kill "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

"$PYTHON" -m backend.app &
backend_pid=$!

printf 'Disk Organiser: http://127.0.0.1:8000\n'
printf 'Backend API:    http://127.0.0.1:5000\n'

"$HTTP_SERVER" frontend -p 8000 -P http://127.0.0.1:5000 -c-1
