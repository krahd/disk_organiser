#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <version> [release-notes]"
  echo "Example: $0 1.2.0 'Release notes for v1.2.0'"
  exit 1
fi

VER="$1"
NOTES="${2-}" 

TAG="v${VER}"

git config user.name "release-script"
git config user.email "release@localhost"
git tag -a "$TAG" -m "Release $TAG"
git push origin "$TAG"

if command -v gh >/dev/null 2>&1; then
  if [ -n "$NOTES" ]; then
    gh release create "$TAG" -n "$NOTES" || true
  else
    gh release create "$TAG" || true
  fi
else
  echo "Note: 'gh' CLI not found; tag pushed but release was not created via gh CLI."
fi

echo "Created and pushed tag $TAG"
