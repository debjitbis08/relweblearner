"""e4 — algebra sweep (P4). Fixed machinery, swept algebra.

PRE-COMMITTED TRADEOFF METRIC (declared before running, per Section 6):
  * bloat = C / D            — weakness: witness nodes per concept (>= 1).
  * false_inverse_rate       — strength: hallucinated total inverses (0..1).
No scalar winner is prescribed. The (bloat, false_inverse) frontier is the
finding: the table IS the result. undefined_fraction (partial composition) and
relabel_invariant (the P0 discipline, per algebra) are reported alongside.

Writes results/e4_sweep.csv and results/e4_sweep.png.
Run: ``poetry run python experiments/e4_sweep.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.algebra import (
    CyclicGroup,
    FreeInvolutiveMonoid,
    IntegerGroup,
    KleinFour,
    SymmetricInverseMonoid,
)
from relweblearner.sweep import report

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")

ALGEBRAS = [
    IntegerGroup(),
    CyclicGroup(2),
    CyclicGroup(4),
    KleinFour(),
    SymmetricInverseMonoid(3),
    FreeInvolutiveMonoid(2, 3),
]


def _dominated(p, others):
    return any(
        q[0] <= p[0] and q[1] <= p[1] and (q[0] < p[0] or q[1] < p[1])
        for q in others
    )


def run():
    reps = [report(a) for a in ALGEBRAS]

    print("PRE-COMMITTED axes: bloat = C/D (weakness), false_inverse_rate (strength)\n")
    print(f"  {'algebra':10} {'D':>3} {'bloat':>6} {'false_inv':>9} {'undef':>6} {'relabel_ok':>10}")
    for r in reps:
        print(f"  {r.name:10} {r.distinct:3d} {r.bloat:6.2f} {r.false_inverse_rate:9.2f} "
              f"{r.undefined_fraction:6.2f} {str(r.relabel_invariant):>10}")

    pts = {r.name: (r.bloat, r.false_inverse_rate) for r in reps}
    frontier = [n for n in pts if not _dominated(pts[n], [v for k, v in pts.items() if k != n])]
    print(f"\nnon-dominated (the tradeoff frontier): {sorted(frontier)}")
    print("Z: no bloat but hallucinates inverses.  InvMon_3: honest partial")
    print("inverses (0 false + undefined loops flagged) at a bloat cost.  The")
    print("small groups (Z_2, Z2xZ2) are dominated: they bloat AND hallucinate.")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e4_sweep.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algebra", "distinct_D", "bloat", "false_inverse_rate",
                    "undefined_fraction", "relabel_invariant"])
        for r in reps:
            w.writerow([r.name, r.distinct, f"{r.bloat:.3f}", f"{r.false_inverse_rate:.3f}",
                        f"{r.undefined_fraction:.3f}", r.relabel_invariant])
    _plot(reps, frontier, os.path.join(RESULTS, "e4_sweep.png"))
    print(f"\nwrote {csv_path}")


def _plot(reps, frontier, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for r in reps:
        on = r.name in frontier
        ax.scatter(r.bloat, r.false_inverse_rate, s=130 if on else 80,
                   color="#c0392b" if on else "#7f8c8d",
                   edgecolor="black" if on else "none", zorder=3,
                   marker="o" if on else "s")
        ax.annotate(r.name, (r.bloat, r.false_inverse_rate),
                    textcoords="offset points", xytext=(8, 6), fontsize=8)
    ax.set_xlabel("bloat  (C / D)  —  weaker algebra →")
    ax.set_ylabel("false-inverse rate  —  stronger algebra ↑")
    ax.set_title("e4: weak/strong tradeoff frontier (red = non-dominated)\n"
                 "no winner prescribed — the frontier is the finding")
    ax.set_xlim(0.5, max(r.bloat for r in reps) + 1)
    ax.set_ylim(-0.1, 1.15)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
