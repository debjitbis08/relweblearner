#!/usr/bin/env bash
# One scheduled CURIOSITY TICK: batch-answer the creature's open questions from
# the declared oracles (corpus/oracles.json), then exit. The sibling of
# train_tick.sh — same lock, same cron pattern:
#
#   15,45 * * * * /path/to/relweblearner/scripts/wonder_tick.sh >> /path/to/relweblearner/data/wonder.log 2>&1
#
# Idempotent — with nothing open (or everything parked) the run is a no-op —
# and `flock` ensures a slow tick never overlaps the next one, or a training
# run. Answers arrive as ordinary testimony: one oracle is one witness, so
# nothing here can commit a belief on a single source's word.
set -euo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
mkdir -p "$REPO/data"

CREATURE="${RELWEB_CREATURE:-scholar}"
BUDGET="${RELWEB_WONDER_BUDGET:-8}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] wonder tick: up to $BUDGET questions for '$CREATURE'"
exec flock -n "$REPO/data/.train.lock" \
  poetry run relweb-wonder --name "$CREATURE" --tick --budget "$BUDGET"
