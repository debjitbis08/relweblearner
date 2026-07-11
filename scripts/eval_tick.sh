#!/usr/bin/env bash
# One scheduled EXAMINATION TICK: sit the creature for every stage's worksheet,
# run the invariant audits, append a metrics row, and alert on any drift since
# the last examination. The third sibling of train_tick.sh / wonder_tick.sh —
# same lock, same cron pattern (examine a little after training has settled):
#
#   50 */2 * * * /path/to/relweblearner/scripts/eval_tick.sh >> /path/to/relweblearner/data/eval.log 2>&1
#
# Exit code 2 (and a line in data/alerts.log, plus a desktop notification when
# notify-send exists) means DRIFT: a worksheet score fell, a defect appeared,
# committed facts vanished unexplained, or a refusal audit failed. The trend is
# `relweb-eval --report` (plot in results/eval_trend.png).
set -euo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
mkdir -p "$REPO/data"

CREATURE="${RELWEB_CREATURE:-scholar}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] examination tick for '$CREATURE'"
exec flock -n "$REPO/data/.train.lock" \
  poetry run relweb-eval --name "$CREATURE" --run
