"""e6 — reflection (P6). No new machinery, only attention allocation.

The learner's own act traces (emitted by invariant 4) are fed back through the
ordinary path:
  (a) act-classes crystallize by the same type-discovery used for relations,
      at purity 1.0 vs the hidden operation kinds;
  (b) an attention budget bounds the regress (emission never stops, consumption
      is capped, backlog stays finite);
  (c) the learner counts its own defect reports with the number chain it built
      in P1b — the system measuring itself with its own ruler.

Writes results/e6_reflection.csv and results/e6_reflection.png.
Run: ``poetry run python experiments/e6_reflection.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner import reflection as R
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner
from relweblearner.web import Web

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
TAGS = {"add_edge", "rewire", "grow", "walk", "defect"}


def _workload() -> Web:
    w = Web(IntegerGroup(), name="W")
    for i in range(10):
        w.add_node(i)
    for i in range(9):
        w.add_edge(i, i + 1, "succ", 1)
    w.rewire(merge=(8, 9))
    w.rewire(merge=(6, 7))
    w.rewire(merge=(4, 5))
    w.grow(["g0", "g1"], [(3, "g0", "succ", 1), ("g0", "g1", "succ", 1)])
    for start, k in [(0, "3"), (1, "4"), (2, "5")]:
        w.walk(start, "succ~", int(k))
    return w


def _defective_web(n_defects: int) -> Web:
    w = Web(IntegerGroup(), name="D")
    N = 3 * n_defects + 1
    for i in range(N):
        w.add_node(i)
    for i in range(N - 1):
        w.add_edge(i, i + 1, "succ", 1)
    for k in range(n_defects):
        w.add_edge(3 * k, 3 * k + 2, "same", 0)
    return w


def run():
    w = _workload()
    traces = R.act_traces(w.journal, tags=TAGS)
    classes = R.discover_act_classes(traces)
    purity = R.act_class_purity(classes)
    print("(a) ACT-CLASSES over the learner's own acts (unchanged machinery)")
    rows_a = []
    for sig, eps in sorted(classes.items()):
        kind = sorted({R.operation_of(e) for e in eps})
        print(f"    signature {sig} -> {kind}  (n={len(eps)})")
        rows_a.append((sig, kind, len(eps)))
    print(f"    purity vs hidden operation kinds: {purity:.2f}")
    print(f"    act traces parse like world episodes: {R.parses_as_world(traces)}")

    budget = 5
    res = R.bounded_consume(w.journal, budget=budget)
    print(f"\n(b) ATTENTION BUDGET (={budget}): {res}")
    print("    emission never stops; consumption is capped; backlog finite.")

    L = NumberLearner()
    L.ingest_all(random_stream(make_collections(60, seed=7), 900, seed=1))
    chain = L.project()
    print("\n(c) SELF-MEASUREMENT: count own defect reports with the P1b chain")
    self_counts = []
    for n in (1, 2, 3):
        wd = _defective_web(n)
        reports = R.emit_defect_reports(wd)
        counted = R.self_count(L, chain, reports)
        print(f"    {n} defect(s) -> reported {len(reports)} -> counted {counted}")
        self_counts.append((n, counted))

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e6_reflection.csv")
    with open(csv_path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["part", "detail", "value"])
        wr.writerow(["a_purity", "act-class purity", f"{purity:.3f}"])
        for sig, kind, n in rows_a:
            wr.writerow(["a_class", str(sig), f"{kind}:{n}"])
        wr.writerow(["b_budget", "consumed/backlog", f"{res['consumed']}/{res['backlog']}"])
        for n, c in self_counts:
            wr.writerow(["c_selfcount", f"{n}_defects", c])
    _plot(classes, res, budget, self_counts, os.path.join(RESULTS, "e6_reflection.png"))
    print(f"\nwrote {csv_path}")


def _plot(classes, res, budget, self_counts, path):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12, 3.6))

    kinds = [sorted({R.operation_of(e) for e in eps})[0] for eps in classes.values()]
    sizes = [len(eps) for eps in classes.values()]
    ax1.bar(kinds, sizes, color="#2c3e50")
    ax1.set_title("(a) act-classes (purity 1.0)")
    ax1.set_ylabel("acts per class")
    ax1.tick_params(axis="x", labelrotation=20)

    ax2.bar(["budget", "consumed", "backlog"],
            [budget, res["consumed"], res["backlog"]],
            color=["#7f8c8d", "#2980b9", "#c0392b"])
    ax2.set_title("(b) attention bounds regress")
    ax2.set_ylabel("count")

    xs = [n for n, _ in self_counts]
    ys = [c for _, c in self_counts]
    ax3.plot(xs, ys, "-o", color="#c0392b")
    ax3.plot(xs, xs, "--", color="#7f8c8d", lw=1, label="ideal")
    ax3.set_title("(c) self-count = truth")
    ax3.set_xlabel("actual defects")
    ax3.set_ylabel("counted (own ruler)")
    ax3.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
