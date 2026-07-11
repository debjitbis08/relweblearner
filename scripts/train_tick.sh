#!/usr/bin/env bash
# One scheduled TRAINING TICK: ingest the next few un-read sources from the
# registry (corpus/sources.json) into the creature, then exit. Designed for cron:
#
#   */30 * * * * /path/to/relweblearner/scripts/train_tick.sh >> /path/to/relweblearner/data/train.log 2>&1
#
# Idempotent — when the registry has nothing new the run is a no-op — and `flock`
# ensures a slow tick never overlaps the next one. Tune per-tick size and target
# with env vars (defaults shown). Portable: when you outgrow the laptop, run the
# same script (or `poetry run relweb-train`) wherever the repo and data volume live.
# RELWEB_STORE=sqlite (or sharded:N) moves the concept web to an on-disk store;
# each tick that advances auto-snapshots the state (RELWEB_AUTOSNAP=0 disables,
# RELWEB_AUTOSNAP_KEEP tunes retention) — inspect and roll back with `relweb-version`.
set -euo pipefail

# cron runs with a bare environment, so make sure poetry (~/.local/bin) and flock
# (/usr/bin) resolve regardless of how this is invoked.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
mkdir -p "$REPO/data"

CREATURE="${RELWEB_CREATURE:-scholar}"
MAX_STAGES="${RELWEB_MAX_STAGES:-1}"

# Teach + grade the next curriculum stage(s). Mastery-gated: holds on a stage until
# its worksheet passes; a no-op once the whole curriculum is mastered.
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] tick: advance up to $MAX_STAGES stage(s) for '$CREATURE'"
exec flock -n "$REPO/data/.train.lock" \
  poetry run relweb-train --name "$CREATURE" --max-stages "$MAX_STAGES"
