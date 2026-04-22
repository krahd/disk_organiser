#!/usr/bin/env bash
set -euo pipefail

REPO=${1:-krahd/disk_organiser}
TAG=${2:-}
OUTDIR=${3:-/tmp}

if [ -z "$TAG" ]; then
  echo "Usage: $0 <repo> <tag> [outdir]"
  exit 1
fi

echo "Searching for run for tag '$TAG' in repo '$REPO'..."
# produce tab-separated lines: databaseId<TAB>headBranch<TAB>displayTitle
RUN_LINE=$(gh run list -R "$REPO" --limit 200 --json databaseId,headBranch,displayTitle --jq '.[] | [.databaseId, (.headBranch // ""), (.displayTitle // "")] | @tsv' 2>/dev/null | grep -F "$TAG" | head -n1 || true)
if [ -z "$RUN_LINE" ]; then
  echo "No run found for tag $TAG"
  exit 1
fi

RUN_ID=$(echo "$RUN_LINE" | awk -F"\t" '{print $1}')
echo "Found run ID: $RUN_ID"

OUT="$OUTDIR/gh_run_$RUN_ID"
mkdir -p "$OUT"

echo "Downloading artifacts to $OUT"
gh run download "$RUN_ID" -R "$REPO" -D "$OUT" || echo "artifact download failed"

echo "Downloading consolidated logs zip via API"
# gh api writes binary to stdout; redirect to file
gh api repos/$REPO/actions/runs/$RUN_ID/logs --silent > "$OUT/logs_${RUN_ID}.zip" || echo "logs zip failed"

if [ -f "$OUT/logs_${RUN_ID}.zip" ]; then
  mkdir -p "$OUT/logs"
  unzip -o "$OUT/logs_${RUN_ID}.zip" -d "$OUT/logs" || true
fi

echo "Saved artifacts/logs to $OUT"
echo "$OUT"
exit 0
