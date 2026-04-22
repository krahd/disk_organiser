#!/usr/bin/env bash
set -euo pipefail

# Remove local virtualenvs from working tree and git index (non-destructive)
dirs=(.ci-venv .pyinstaller_build_venv)
for d in "${dirs[@]}"; do
  if [ -d "$d" ]; then
    echo "Removing directory: $d"
    rm -rf "$d"
  fi
  if git ls-files --error-unmatch "$d" >/dev/null 2>&1; then
    echo "Removing $d from git index"
    git rm -r --cached "$d" || true
  fi
done

echo "Updated working tree. Please commit the updated .gitignore and changes."
exit 0
