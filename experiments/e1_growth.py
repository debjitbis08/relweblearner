"""e1 — forced-growth threshold (P1).

Feeds a subtraction-probe stream at a chain web ``0..9``: in-web probes first,
then probes that walk off the bottom boundary. Logs growth events vs stream
position to ``results/e1_growth.csv`` and plots the sharp threshold to
``results/e1_growth.png`` — growth is zero while probes stay inside the web and
turns on only once a probe leaves it (a threshold, not a drift).

Run: ``poetry run python experiments/e1_growth.py``
"""

from __future__ import annotations

import csv
import os
import sys

# make the src package importable when run as a plain script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

from relweblearner.datasets.arithmetic import build_chain, coordinates
from relweblearner.growth import GrowthEngine

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def run():
    w = build_chain(10)
    eng = GrowthEngine(P=3)

    # in-web probes (a - b in 0..9), then off-web probes crossing the boundary
    stream = [(9, b) for b in range(10)] + [(9, 10), (9, 11), (9, 12), (9, 13)]

    rows = []
    cumulative = 0
    for pos, (a, b) in enumerate(stream):
        ans = eng.answer(w, a, "succ~", b, position=pos)
        grown = ans.grew.n_nodes if ans.grew else 0
        cumulative += grown
        co = coordinates(w)
        rows.append(
            {
                "position": pos,
                "probe": f"{a}-{b}",
                "result": co[ans.endpoint],
                "off_web": b > a,
                "rounds_survived": ans.rounds_survived,
                "nodes_grown": grown,
                "cumulative_grown": cumulative,
                "web_size": len(w.nodes),
            }
        )

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e1_growth.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    _plot(rows, os.path.join(RESULTS, "e1_growth.png"))

    print(f"wrote {csv_path}")
    for r in rows:
        flag = "off-web" if r["off_web"] else "in-web "
        print(
            f"  pos {r['position']:2d} | {r['probe']:>5} = {r['result']:>3} | {flag} "
            f"| rounds {r['rounds_survived']} | grew {r['nodes_grown']} "
            f"| web {r['web_size']}"
        )
    threshold = next(r["position"] for r in rows if r["nodes_grown"] > 0)
    print(f"growth threshold at stream position {threshold} (first off-web probe)")


def _plot(rows, path):
    pos = [r["position"] for r in rows]
    grown = [r["nodes_grown"] for r in rows]
    cum = [r["cumulative_grown"] for r in rows]
    threshold = next(r["position"] for r in rows if r["nodes_grown"] > 0)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(pos, grown, color="#c0392b", alpha=0.8, label="nodes grown (per probe)")
    ax.step(pos, cum, where="mid", color="#2c3e50", label="cumulative nodes grown")
    ax.axvline(threshold - 0.5, ls="--", color="#7f8c8d", lw=1)
    ax.text(threshold - 0.4, max(cum) * 0.9, "boundary\ncrossed", fontsize=8, color="#7f8c8d")
    ax.set_xlabel("probe-stream position")
    ax.set_ylabel("nodes grown")
    ax.set_title("e1: forced-growth threshold (growth off until the web boundary)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
