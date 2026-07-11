"""Continuous evaluation — the machine notices regressions, not the human.

One person cannot re-examine a continuously-learning creature by hand. This
module is the standing examiner: ``--run`` sits the creature for the ENTIRE
curriculum's worksheets (every stage, mastered or not — mastery must not decay),
runs the invariant audits, appends one row to ``data/metrics.jsonl``, and
compares it against the previous row. Any drift — a stage score falling, a
holonomy defect appearing, committed facts vanishing without a retraction to
explain them, a fabricated answer where a refusal was owed — is an ALERT:
printed, appended to ``data/alerts.log``, raised as a desktop notification
when ``notify-send`` exists, and signalled by exit code 2 so cron can see it.

    relweb-eval --run          # examine, record, compare against last time
    relweb-eval --report       # the trend: recent rows + results/eval_trend.png

Everything is local — no CI service, no network. Designed for cron via
``scripts/eval_tick.sh`` (sibling of train/wonder ticks, same lock). The exam
itself is the creature's ordinary ``answer`` path, so a question it cannot
answer mints an open wonder exactly as it would in conversation — an exam it
fails becomes something it is curious about; nothing else is written (the
checkpoint is not saved).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from .datasets import registry as R
from .datasets import syllabus as SYL
from .episodelog import creature_lock
from .train import _root, _store_path, open_creature
from .version import stamp

#: a nonsense entity in a taught construction — the answer owed is a refusal.
REFUSAL_PROBE = "the zyxxo is ?"


def _metrics_path() -> Path:
    return _root() / "data" / "metrics.jsonl"


def _alerts_path() -> Path:
    return _root() / "data" / "alerts.log"


# ============================================================= the examination


def evaluate(c) -> dict:
    """Sit the whole curriculum + audits; return one metrics row (pure read —
    apart from the wonders the creature itself mints for questions it misses)."""
    registry, stages = R.load_registry(), R.load_stages()
    per_stage: dict[str, dict] = {}
    tot_correct = tot_n = 0
    for st in stages:
        items = SYL.stage_worksheet(st, registry)
        if not items:
            continue                                  # reading-only stage: nothing gradable
        rep = SYL.run_exam(c, items)
        per_stage[st["id"]] = {"score": round(rep["score"], 4), "correct": rep["correct"],
                               "total": rep["total"], "mastered": st["id"] in c.passed_stages,
                               "missed": [{"q": q, "want": w, "got": g} for q, w, g in rep["wrong"][:4]]}
        tot_correct += rep["correct"]
        tot_n += rep["total"]

    probe = c.answer(REFUSAL_PROBE)
    snap = c.snapshot(committed_limit=1)
    from . import curiosity as CU

    led = CU.ledger(c)
    return {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "name": c.name,
        "provenance": stamp(),
        "episodes": c.episodes_seen,
        "log": {"entries": len(c.log), "position": c.log_position,
                "excluded": len(c.log.excluded())},
        "overall": {"score": round(tot_correct / tot_n, 4) if tot_n else 1.0,
                    "correct": tot_correct, "total": tot_n},
        "stages": per_stage,
        "audits": {
            "refusal_ok": not probe.get("known") and not probe.get("answers"),
            "defects": len(snap["defects"]),
            "committed": snap["committed_count"],
            "nodes": snap["model_size"]["nodes"],
            "facts": snap["model_size"]["facts"],
            "frames": snap["model_size"]["frames"],
            "trust_entries": len(snap["trust"]),
            "growth_used": snap["growth"]["count"],
            "wonders_open": len(led["open"]),
            "wonders_parked": len(led["parked"]),
        },
    }


# ============================================================= drift detection


def drift(prev: dict | None, cur: dict) -> list[str]:
    """What regressed between two metrics rows. Empty list = healthy. The rules
    are deliberately strict — a one-question slip on a worksheet is exactly the
    early signal a lone maintainer never notices by hand:

      * any stage's score falls;
      * a holonomy defect appears (or their count rises);
      * committed facts drop with no new exclusions to explain the loss
        (a deliberate retraction is not drift — a silent one is);
      * the refusal audit fails (it fabricated an answer for a nonsense entity).
    """
    alerts: list[str] = []
    a = cur["audits"]
    if not a["refusal_ok"]:
        alerts.append(f"refusal audit FAILED: answered {REFUSAL_PROBE!r} instead of refusing")
    if prev is None:
        return alerts
    for sid, r in sorted(cur["stages"].items()):
        p = prev["stages"].get(sid)
        if p and r["score"] < p["score"] - 1e-9:
            alerts.append(f"stage '{sid}' fell {p['score']:.1%} -> {r['score']:.1%} "
                          f"({r['correct']}/{r['total']})")
    pa = prev["audits"]
    if a["defects"] > pa["defects"]:
        alerts.append(f"holonomy defects rose {pa['defects']} -> {a['defects']}")
    if a["committed"] < pa["committed"] and cur["log"]["excluded"] <= prev["log"]["excluded"]:
        alerts.append(f"committed facts fell {pa['committed']} -> {a['committed']} "
                      f"with no new exclusions to explain it")
    return alerts


def _notify(summary: str) -> None:
    """Best-effort desktop notification (this is a one-machine deployment —
    the desktop IS the alerting channel). Silently absent elsewhere."""
    try:
        subprocess.run(["notify-send", "-u", "critical", "relweblearner", summary],
                       capture_output=True, timeout=5)
    except Exception:
        pass


# ============================================================= record & report


def _read_rows(limit: int | None = None) -> list[dict]:
    p = _metrics_path()
    if not p.exists():
        return []
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[-limit:] if limit else rows


def run(name: str) -> int:
    """One examination tick: evaluate under the creature lock, append the row,
    alert on drift. Exit 0 healthy, 2 on alerts (cron-visible)."""
    with creature_lock(_store_path(name).parent):
        c = open_creature(name)
        try:
            row = evaluate(c)
        finally:
            c.close()                               # no save: the exam owns no state
    rows = [r for r in _read_rows() if r.get("name") == name]
    prev = rows[-1] if rows else None
    alerts = drift(prev, row)
    row["alerts"] = alerts
    p = _metrics_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    o = row["overall"]
    print(f"[{row['time']}] '{name}': {o['correct']}/{o['total']} = {o['score']:.1%} overall, "
          f"{row['audits']['committed']} committed, {row['audits']['defects']} defect(s), "
          f"{row['audits']['wonders_open']} open wonder(s)")
    if not alerts:
        print("   no drift since last examination" if prev else "   first examination — baseline recorded")
        return 0
    stampline = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _alerts_path().open("a", encoding="utf-8") as fh:
        for msg in alerts:
            print(f"   ALERT: {msg}")
            fh.write(f"{stampline} [{name}] {msg}\n")
    _notify(f"'{name}' drifted: " + "; ".join(alerts)[:180])
    return 2


def report(name: str, limit: int = 12) -> int:
    rows = [r for r in _read_rows() if r.get("name") == name]
    if not rows:
        print(f"(no examinations recorded for '{name}' yet — run `relweb-eval --run`)")
        return 0
    print(f"EXAMINATION TREND — '{name}' ({len(rows)} recorded; last {min(limit, len(rows))}):\n")
    for r in rows[-limit:]:
        o, a = r["overall"], r["audits"]
        flag = f"  ⚠ {len(r['alerts'])} alert(s)" if r.get("alerts") else ""
        print(f"   {r['time']}  score={o['score']:.1%} ({o['correct']}/{o['total']})  "
              f"committed={a['committed']:<5d} defects={a['defects']:<2d} "
              f"wonders={a['wonders_open']:<3d} episodes={r['episodes']}{flag}")
    worst = [(sid, s) for sid, s in rows[-1]["stages"].items() if s["score"] < 1.0]
    if worst:
        print("\n   below 100% right now:")
        for sid, s in sorted(worst, key=lambda x: x[1]["score"]):
            print(f"      {sid:24s} {s['score']:.1%} ({s['correct']}/{s['total']})")
    _plot(rows)
    return 0


def _plot(rows: list[dict]) -> None:
    """The trend picture (repo convention: results/*.png), fail-soft."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        xs = range(len(rows))
        fig, ax1 = plt.subplots(figsize=(9, 4.5))
        ax1.plot(xs, [r["overall"]["score"] for r in rows], "o-", color="tab:blue", label="overall score")
        ax1.set_ylim(0, 1.05)
        ax1.set_ylabel("worksheet score", color="tab:blue")
        ax1.set_xlabel("examination #")
        ax2 = ax1.twinx()
        ax2.plot(xs, [r["audits"]["committed"] for r in rows], "s--", color="tab:green", label="committed facts")
        ax2.plot(xs, [r["audits"]["defects"] for r in rows], "x:", color="tab:red", label="defects")
        ax2.set_ylabel("committed / defects")
        fig.legend(loc="lower right")
        fig.tight_layout()
        out = _root() / "results" / "eval_trend.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"\n   trend plot: {out.relative_to(_root())}")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Examine the creature; alert on drift.")
    ap.add_argument("--name", default="scholar")
    ap.add_argument("--run", action="store_true", help="sit the full battery, record, compare")
    ap.add_argument("--report", action="store_true", help="print the trend (and plot it)")
    ap.add_argument("--limit", type=int, default=12, help="rows shown by --report")
    args = ap.parse_args()
    if args.run:
        return run(args.name)
    if args.report:
        return report(args.name, limit=args.limit)
    ap.error("give --run or --report")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
