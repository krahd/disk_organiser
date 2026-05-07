#!/usr/bin/env bash
set -euo pipefail

REPO="krahd/disk_organiser"
WORKFLOW="bottle-build.yml"
OUT="/tmp/gh_poll_$(date +%s)"
mkdir -p "$OUT"

echo "Started poll at $(date -u). OUT=$OUT"
echo "Initial run info:" > "$OUT/log.txt"

LAST_KNOWN=$(gh run list -R "$REPO" --workflow="$WORKFLOW" --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)
if [ -z "$LAST_KNOWN" ] || [ "$LAST_KNOWN" = "null" ]; then
  LAST_KNOWN=0
fi
echo "Initial top run id: $LAST_KNOWN" >> "$OUT/log.txt"

DURATION_MINUTES=${1:-30}
END_TIME=$(( $(date +%s) + DURATION_MINUTES*60 ))
POLL=15

while [ $(date +%s) -lt $END_TIME ]; do
  echo "$(date -u) - polling..." >> "$OUT/log.txt"
  TOP_ID=$(gh run list -R "$REPO" --workflow="$WORKFLOW" --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)
  echo "top id: ${TOP_ID}" >> "$OUT/log.txt"
  if [ -n "$TOP_ID" ] && [ "$TOP_ID" != "$LAST_KNOWN" ] && [ "$TOP_ID" != "null" ]; then
    echo "Detected new run: $TOP_ID" >> "$OUT/log.txt"
    RUN_ID=$TOP_ID
    gh api repos/$REPO/actions/runs/$RUN_ID --jq '{id:.id,status:.status,conclusion:.conclusion,created_at:.created_at,head_branch:.head_branch,html_url:.html_url}' >> "$OUT/log.txt" 2>&1 || true

    # Attempt consolidated zip
    if gh api repos/$REPO/actions/runs/$RUN_ID/logs -o "$OUT/logs_${RUN_ID}.zip" 2>/dev/null; then
      echo "Downloaded logs zip to $OUT/logs_${RUN_ID}.zip" >> "$OUT/log.txt"
      mkdir -p "$OUT/extracted"
      unzip -o "$OUT/logs_${RUN_ID}.zip" -d "$OUT/extracted" >/dev/null 2>&1 || true
      ls -lh "$OUT/extracted" >> "$OUT/log.txt" 2>&1 || true
    else
      echo "No consolidated logs zip available" >> "$OUT/log.txt"
    fi

    # Save jobs JSON and job-level logs
    gh api repos/$REPO/actions/runs/$RUN_ID/jobs -q '.jobs | map({id:.id,name:.name,conclusion:.conclusion})' > "$OUT/jobs_${RUN_ID}.json" 2>/dev/null || true
    if [ -f "$OUT/jobs_${RUN_ID}.json" ]; then
      JOB_COUNT=$(jq 'length' "$OUT/jobs_${RUN_ID}.json" 2>/dev/null || echo 0)
      echo "job_count: $JOB_COUNT" >> "$OUT/log.txt"
      if [ "$JOB_COUNT" -gt 0 ]; then
        for jobid in $(jq -r '.[].id' "$OUT/jobs_${RUN_ID}.json"); do
          if gh api repos/$REPO/actions/jobs/$jobid/logs -o "$OUT/job_${jobid}.zip" 2>/dev/null; then
            mkdir -p "$OUT/job_${jobid}"
            unzip -o "$OUT/job_${jobid}.zip" -d "$OUT/job_${jobid}" >/dev/null 2>&1 || true
            ls -lh "$OUT/job_${jobid}" >> "$OUT/log.txt" 2>&1 || true
          else
            echo "Failed to download job logs for $jobid" >> "$OUT/log.txt"
          fi
        done
      fi
    fi

    if gh run view $RUN_ID -R "$REPO" --log > "$OUT/run_${RUN_ID}.log" 2>/dev/null; then
      echo "Saved consolidated run log to $OUT/run_${RUN_ID}.log" >> "$OUT/log.txt"
    else
      echo "No consolidated run log available" >> "$OUT/log.txt"
    fi

    echo "Saved all candidate logs to: $OUT" >> "$OUT/log.txt"
    echo "$OUT"
    exit 0
  fi
  sleep $POLL
done

echo "Timeout reached after ${DURATION_MINUTES} minutes. OUT=$OUT" >> "$OUT/log.txt"
echo "$OUT"
exit 1
