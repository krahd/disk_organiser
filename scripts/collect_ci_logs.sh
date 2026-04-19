#!/usr/bin/env bash
set -euo pipefail
REPO="krahd/disk_organiser"
CI_RUN=24635978273
OUT_DIR="/tmp/ci_logs_${CI_RUN}"
mkdir -p "$OUT_DIR"

echo "Polling CI run $CI_RUN"
for i in $(seq 1 30); do
  C=$(gh run view "$CI_RUN" -R "$REPO" --json conclusion --jq '.conclusion' 2>/dev/null || echo null)
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) poll $i -> $C"
  if [ "$C" != "null" ] && [ -n "$C" ]; then
    break
  fi
  sleep 8
done

echo "Final conclusion: $C"
gh run view "$CI_RUN" -R "$REPO" --json status,conclusion,url --jq '{status:.status,conclusion:.conclusion,url:.url}' || true

echo "Saving CI run log to $OUT_DIR/run_${CI_RUN}.log"
if ! gh run view "$CI_RUN" -R "$REPO" --log > "$OUT_DIR/run_${CI_RUN}.log" 2>/dev/null; then
  echo "could not get log for $CI_RUN"
fi
ls -lh "$OUT_DIR/run_${CI_RUN}.log" || true

# find latest failing bottle-build run
FAIL_ID=$(gh run list -R "$REPO" --workflow ".github/workflows/bottle-build.yml" --limit 20 --json databaseId,conclusion --jq '.[] | select(.conclusion=="failure") | .databaseId' | head -n1 || true)
echo "LATEST_FAIL_ID=$FAIL_ID"
if [ -n "$FAIL_ID" ]; then
  gh run view "$FAIL_ID" -R "$REPO" --json status,conclusion,url --jq '{status:.status,conclusion:.conclusion,url:.url}' || true
  echo "Saving failing bottle-build run log to $OUT_DIR/run_${FAIL_ID}.log"
  if ! gh run view "$FAIL_ID" -R "$REPO" --log > "$OUT_DIR/run_${FAIL_ID}.log" 2>/dev/null; then
    echo "could not get log for $FAIL_ID"
  fi
  ls -lh "$OUT_DIR/run_${FAIL_ID}.log" || true
fi

echo "$CI_RUN" > "$OUT_DIR/collected_run_ids.txt"
echo "$FAIL_ID" >> "$OUT_DIR/collected_run_ids.txt"
echo "WROTE IDs to $OUT_DIR/collected_run_ids.txt"
ls -l "$OUT_DIR"
