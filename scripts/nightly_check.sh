#!/usr/bin/env bash
# Nightly HEALTH CHECK: run the full acceptance suite on this machine and keep
# the verdict on the record — local-only CI (no cloud runner, no credits).
#
#   20 3 * * * /path/to/relweblearner/scripts/nightly_check.sh >> /path/to/relweblearner/data/nightly.log 2>&1
#
# Appends one JSON row per night to data/health.jsonl (pass/fail, counts,
# duration, git commit); full pytest output lands in data/nightly-<date>.log
# (last 7 kept). A failure also writes data/alerts.log and raises a desktop
# notification when notify-send exists.
set -uo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
mkdir -p "$REPO/data"

DATE="$(date -u +%Y%m%d)"
OUT="$REPO/data/nightly-$DATE.log"
SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

START=$(date +%s)
poetry run pytest -q >"$OUT" 2>&1
STATUS=$?
SECS=$(( $(date +%s) - START ))

SUMMARY="$(tail -1 "$OUT" | tr -d '\r')"
echo "{\"time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"passed\": $([ $STATUS -eq 0 ] && echo true || echo false), \"code\": \"$SHA\", \"seconds\": $SECS, \"summary\": $(printf '%s' "$SUMMARY" | sed 's/\x1b\[[0-9;]*m//g' | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')}" >> "$REPO/data/health.jsonl"

# keep only the last 7 nightly logs
ls -1t "$REPO"/data/nightly-*.log 2>/dev/null | tail -n +8 | xargs -r rm --

if [ $STATUS -ne 0 ]; then
  MSG="nightly suite FAILED at $SHA — see data/nightly-$DATE.log"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [suite] $MSG" >> "$REPO/data/alerts.log"
  notify-send -u critical relweblearner "$MSG" 2>/dev/null || true
  echo "$MSG"
  exit 1
fi
echo "nightly suite passed at $SHA (${SECS}s): $SUMMARY"
