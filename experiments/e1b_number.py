"""e1b — constructing number from counting (P1b), on the holonomy substrate.

Reproduces experiment0e's result routed through web.py / holonomy.py: the
number chain is a projection of bare pairing episodes, and a poisoned episode
surfaces as a genuine holonomy self-loop defect ('class ONEMORE of itself').

Runs:
  1. full data      -> pure classes, single naturals chain
  2. counting       -> a fresh collection numbered by chain-pairing
  3. staged data    -> small numbers crystallize first (a "two-knower")
  4. poison         -> class-ONEMORE-of-itself defect; retract by replay

Writes results/e1b_number.csv and results/e1b_number.png.
Run: ``poetry run python experiments/e1b_number.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.datasets.counting import (
    by_size,
    make_collections,
    poison_episode,
    random_stream,
    staged_stream,
)
from relweblearner.number import NumberLearner

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def sizes_along(cols, chain):
    return [sorted({len(cols[m]) for m in chain.class_members[c]}) for c in chain.order]


def run():
    cols = make_collections(60, max_size=5, seed=7)
    bs = by_size(cols)
    rows = []

    # 1. full data
    L = NumberLearner()
    L.ingest_all(random_stream(cols, 900, seed=1))
    chain = L.project()
    print("1. FULL DATA")
    print(f"   chain (hidden sizes): {sizes_along(cols, chain)}")
    print(f"   contradictions: {chain.contradictions}")
    rows.append({"run": "full", "chain": sizes_along(cols, chain), "contradictions": len(chain.contradictions)})

    # 2. counting a fresh collection of each size
    print("2. COUNTING a fresh collection")
    for size in range(1, max(bs) + 1):
        fresh = {f"z{i}" for i in range(size)}
        pos = L.count(chain, fresh)
        print(f"   fresh size-{size} collection -> number {pos}  {'OK' if pos == size else 'FAIL'}")

    # 3. staged crystallization
    Ls = NumberLearner()
    stage_a, stage_b = staged_stream(cols, small_max=2, n_small=150, n_full=800, seed=1)
    Ls.ingest_all(stage_a)
    early = Ls.project()
    early_multi = sorted({len(cols[m]) for mem in early.class_members.values() if len(mem) > 1 for m in mem})
    print("3. STAGED DATA")
    print(f"   after stage A, crystallized sizes: {early_multi}  (a '{max(early_multi)}-knower')")
    Ls.ingest_all(stage_b)
    full = Ls.project()
    print(f"   after stage B, chain: {sizes_along(cols, full)}")
    rows.append({"run": "staged_A", "chain": [early_multi], "contradictions": 0})

    # 4. poison + retraction
    a2, a3 = bs[2][0], bs[3][0]
    pid = L.ingest(poison_episode(cols, a2, a3))
    poisoned = L.project()
    restored = L.project(exclude=frozenset({pid}))
    print("4. POISON")
    print(f"   poisoned chain: {sizes_along(cols, poisoned)}")
    print(f"   contradictions: {poisoned.contradictions}")
    print(f"   after replay-with-exclusion: chain {sizes_along(cols, restored)}, contradictions {restored.contradictions}")
    rows.append({"run": "poisoned", "chain": sizes_along(cols, poisoned), "contradictions": len(poisoned.contradictions)})
    rows.append({"run": "retracted", "chain": sizes_along(cols, restored), "contradictions": len(restored.contradictions)})

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e1b_number.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "chain", "contradictions"])
        w.writeheader()
        w.writerows(rows)
    _plot(cols, chain, poisoned, restored, os.path.join(RESULTS, "e1b_number.png"))
    print(f"wrote {csv_path}")


def _plot(cols, clean, poisoned, restored, path):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True)
    for ax, (title, chain) in zip(
        axes, [("clean", clean), ("poisoned", poisoned), ("retracted", restored)]
    ):
        sizes = [min(len(cols[m]) for m in chain.class_members[c]) for c in chain.order]
        widths = [len({len(cols[m]) for m in chain.class_members[c]}) for c in chain.order]
        colors = ["#c0392b" if w > 1 else "#2c3e50" for w in widths]
        ax.bar(range(len(sizes)), sizes, color=colors)
        ax.set_title(f"{title}\n({len(chain.contradictions)} defects)", fontsize=9)
        ax.set_xlabel("chain position")
    axes[0].set_ylabel("class size (hidden)")
    fig.suptitle("e1b: number chain as a projection (red = impure/defective class)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
