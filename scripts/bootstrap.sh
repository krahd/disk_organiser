#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv --clear venv
venv/bin/python3 -m pip install --upgrade pip
venv/bin/python3 -m pip install -r backend/requirements.txt
npm ci

printf 'Disk Organiser dependencies installed. Run ./scripts/dev.sh\n'
