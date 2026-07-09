"""e2' — unlabeled-relation type discovery (P2').

Edges carry no labels. Naive degree-role refinement over-refines; disjointness
compression (mutual exclusivity) recovers the true types. Under generic coverage
the mixed web (chain + colors + plants) is recovered at purity 1.0; under sparse
coverage a color hub and a plant hub are accidentally disjoint and conflate —
logged as the conflation-vs-coverage curve.

Writes results/e2p_types.csv and results/e2p_types.png.
Run: ``poetry run python experiments/e2p_types.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.datasets.bare import build_bare_web
from relweblearner.types import (
    discover_types,
    is_conflated,
    n_attribute_types,
    naive_degree_typing,
    overall_purity,
)

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def run():
    # generic coverage
    edges, truth = build_bare_web(colors=3, plants=2, full=True)
    disc = discover_types(edges)
    print("GENERIC COVERAGE")
    print(f"  naive degree-pair typing: {len(naive_degree_typing(edges))} classes (over-refined; truth has 3)")
    print(f"  discovered types: {n_attribute_types(disc)} attribute + 1 chain")
    print(f"  overall purity: {overall_purity(disc, truth):.2f}  conflated: {is_conflated(disc, truth)}")

    # conflation-vs-coverage curve
    xs = list(range(0, 21))
    seeds = 60
    fracs = []
    for nc in xs:
        c = sum(
            is_conflated(discover_types(build_bare_web(3, 2, n_crossing=nc, seed=s)[0]),
                         build_bare_web(3, 2, n_crossing=nc, seed=s)[1])
            for s in range(seeds)
        )
        fracs.append(c / seeds)

    print("\nCONFLATION vs CROSSING OBSERVATIONS")
    for nc, fr in zip(xs, fracs):
        if nc % 4 == 0:
            print(f"  crossings {nc:2d}: fraction conflated {fr:.2f}")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e2p_types.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n_crossing", "fraction_conflated"])
        for nc, fr in zip(xs, fracs):
            w.writerow([nc, f"{fr:.4f}"])
    _plot(xs, fracs, os.path.join(RESULTS, "e2p_types.png"))
    print(f"\nwrote {csv_path}")


def _plot(xs, fracs, path):
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(xs, fracs, "-o", color="#c0392b", ms=4)
    ax.set_xlabel("crossing observations (fruits bridging color × plant)")
    ax.set_ylabel("fraction of runs conflated")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("e2': type individuation requires coverage\n(conflation falls as crossings arrive)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
