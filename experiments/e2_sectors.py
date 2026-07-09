"""e2 — symmetry-sector inference (P2).

Two parts:
  1. Headline: over 20 seeds, classify same / succ / double from >= 30 random
     loop observations, with and without one adversarial mislabel.
  2. End-to-end: coordinates come from the P1b constructed number chain (not
     given) — P2 consumes the class chain, as the dev-doc mandates.

Writes results/e2_sectors.csv and results/e2_sectors.png.
Run: ``poetry run python experiments/e2_sectors.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.datasets.sectors import (
    inject_mislabel,
    loop_observations,
    make_entities,
)
from relweblearner.number import NumberLearner
from relweblearner.sectors import ANTISYMMETRIC, NON_HOMOGENEOUS, SYMMETRIC, infer_sectors

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def headline(n_seeds=20):
    by_count, coord = make_entities(max_count=8, per_count=3)
    clean_ok = 0
    noise_ok = 0
    supports = {"same": [], "succ": [], "double": []}
    for seed in range(n_seeds):
        obs = loop_observations(by_count, 30, seed)
        sec = infer_sectors(obs, coord)
        for r in supports:
            supports[r].append(sec[r].support)
        clean_ok += (
            sec["same"].sector == SYMMETRIC
            and sec["succ"].sector == ANTISYMMETRIC
            and sec["double"].sector == NON_HOMOGENEOUS
        )
        sec2 = infer_sectors(inject_mislabel(obs, "succ", seed), coord)
        noise_ok += sec2["succ"].sector == ANTISYMMETRIC and sec2["succ"].transport == 1
    return clean_ok, noise_ok, supports


def end_to_end():
    """Coordinates from the P1b chain, then classify relations over collections."""
    cols = make_collections(60, max_size=5, seed=7)
    L = NumberLearner()
    L.ingest_all(random_stream(cols, 900, seed=1))
    chain = L.project()

    # coordinate of a collection = its class position in the constructed chain
    coord = {}
    by_count = {}
    for pos, rep in enumerate(chain.order, start=1):
        for m in chain.class_members[rep]:
            coord[m] = pos
            by_count.setdefault(pos, []).append(m)

    obs = loop_observations(by_count, 60, seed=1)
    return infer_sectors(obs, coord)


def run():
    clean_ok, noise_ok, supports = headline()
    print("HEADLINE (entities with chain coordinates)")
    print(f"  clean classification correct: {clean_ok}/20 seeds")
    print(f"  succ rule survives 1 mislabel: {noise_ok}/20 seeds")
    for r, ss in supports.items():
        print(f"  {r:8} mean support of best transport: {sum(ss) / len(ss):.2f}")

    sec = end_to_end()
    print("\nEND-TO-END (coordinates from the P1b constructed chain)")
    for r in ("same", "succ", "double"):
        if r in sec:
            s = sec[r]
            print(f"  {r:8} -> {s.sector:16} g={s.transport} support={s.support:.2f}")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e2_sectors.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["relation", "mean_support", "expected_sector"])
        expected = {"same": SYMMETRIC, "succ": ANTISYMMETRIC, "double": NON_HOMOGENEOUS}
        for r, ss in supports.items():
            w.writerow([r, f"{sum(ss) / len(ss):.3f}", expected[r]])
    _plot(supports, os.path.join(RESULTS, "e2_sectors.png"))
    print(f"\nwrote {csv_path}")


def _plot(supports, path):
    rels = ["same", "succ", "double"]
    colors = {"same": "#2c3e50", "succ": "#2980b9", "double": "#c0392b"}
    means = [sum(supports[r]) / len(supports[r]) for r in rels]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(rels, means, color=[colors[r] for r in rels])
    ax.axhline(0.8, ls="--", color="#7f8c8d", lw=1)
    ax.text(2.4, 0.82, "homogeneity\nthreshold", fontsize=8, color="#7f8c8d", ha="right")
    for i, (r, m) in enumerate(zip(rels, means)):
        label = {"same": "symmetric (g=0)", "succ": "antisym. (g=1)", "double": "motif"}[r]
        ax.text(i, m + 0.02, label, ha="center", fontsize=8)
    ax.set_ylabel("mean support of best single transport")
    ax.set_ylim(0, 1.15)
    ax.set_title("e2: a single transport fits same/succ, not double (-> motif)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
