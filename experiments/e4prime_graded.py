"""e4′ — the graded-algebra hypothesis (P4′), from the P4 frontier finding.

P4 found a genuine dichotomy: totality (ℤ, groups) hallucinates inverses on
partial relations (false-inverse 1.0); partiality (the inverse monoid) refuses to
compose (undefined 0.31) to avoid it. The frontier {ℤ, InvMon} had no dominating
point. This tests whether *grading* resolves it: a group core for total sectors,
an inverse-monoid boundary for partial ones — one carrier, two composition laws.

Result: ``Graded(Z|Inv_3)`` inherits ℤ's **bloat 1.0** AND the inverse monoid's
**false-inverse 0.0**, Pareto-dominating the old frontier on the two headline
axes. It pays two costs: **undefined 0.65** (cross-sector paths don't close —
correct, a number-step and a colour-edge genuinely don't compose) and a subtler
one — strict relabel-invariance holds **per sector** (how it is deployed) but not
on artificially sector-mixed webs (identity edges bridge sectors; relabel
relocates them). Grading's third cost.

Writes results/e4prime_graded.csv.
Run: ``poetry run python experiments/e4prime_graded.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from relweblearner import sweep
from relweblearner.algebra import GradedAlgebra, IntegerGroup, SymmetricInverseMonoid

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def run():
    algebras = [IntegerGroup(), SymmetricInverseMonoid(3), GradedAlgebra(3)]
    rows = []
    for alg in algebras:
        r = sweep.report(alg)
        per_sector = sweep.per_sector_relabel_invariant(alg)
        rows.append({
            "algebra": r.name,
            "bloat": r.bloat,
            "false_inverse": r.false_inverse_rate,
            "undefined": r.undefined_fraction,
            "relabel_mixed": r.relabel_invariant,
            "relabel_per_sector": per_sector,
        })

    print("=" * 78)
    print("P4′ — GRADED ALGEBRA vs THE FRONTIER")
    print("=" * 78)
    print(f"{'algebra':18s} {'bloat':>6s} {'false_inv':>9s} {'undefined':>9s} "
          f"{'relabel(mix)':>12s} {'relabel(sector)':>15s}")
    for r in rows:
        print(f"{r['algebra']:18s} {r['bloat']:6.2f} {r['false_inverse']:9.2f} "
              f"{r['undefined']:9.2f} {str(r['relabel_mixed']):>12s} "
              f"{str(r['relabel_per_sector']):>15s}")

    graded = next(r for r in rows if r["algebra"].startswith("Graded"))
    z = next(r for r in rows if r["algebra"] == "Z")
    inv = next(r for r in rows if r["algebra"].startswith("InvMon"))
    dominates_z = graded["bloat"] <= z["bloat"] and graded["false_inverse"] < z["false_inverse"]
    dominates_inv = graded["bloat"] < inv["bloat"] and graded["false_inverse"] <= inv["false_inverse"]
    print("\nHypothesis: grading is the best of both on (bloat, false-inverse).")
    print(f"  Graded Pareto-dominates Z:      {dominates_z}  "
          f"(bloat {graded['bloat']:.0f}≤{z['bloat']:.0f}, false-inv {graded['false_inverse']:.0f}<{z['false_inverse']:.0f})")
    print(f"  Graded Pareto-dominates InvMon: {dominates_inv}  "
          f"(bloat {graded['bloat']:.0f}<{inv['bloat']:.0f}, false-inv {graded['false_inverse']:.0f}≤{inv['false_inverse']:.0f})")
    print(f"  Price: undefined_fraction {graded['undefined']:.2f}; strict relabel-invariance "
          f"per-sector {graded['relabel_per_sector']}, mixed-web {graded['relabel_mixed']}.")

    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "e4prime_graded.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algebra", "bloat", "false_inverse", "undefined",
                    "relabel_mixed", "relabel_per_sector"])
        for r in rows:
            w.writerow([r["algebra"], f"{r['bloat']:.3f}", f"{r['false_inverse']:.3f}",
                        f"{r['undefined']:.3f}", int(r["relabel_mixed"]),
                        int(r["relabel_per_sector"])])
    print(f"\nwrote {path}")


if __name__ == "__main__":
    run()
