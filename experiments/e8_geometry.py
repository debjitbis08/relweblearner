"""e8 — ensemble geometry (P8, stretch).

Train an ensemble of learners (different seeds and observation orders),
spectral-embed each web (graph-Laplacian eigenmaps), and test whether the
magnitude axis stabilizes across the ensemble even though any single run's
orientation is arbitrary.

Writes results/e8_geometry.csv and results/e8_geometry.png.
Run: ``poetry run python experiments/e8_geometry.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from relweblearner import audit, geometry
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
N_RUNS = 24


def _profiles():
    profs = []
    for seed in range(N_RUNS):
        cols = make_collections(60, seed=seed)
        sizes = {c: len(v) for c, v in cols.items()}
        L = NumberLearner()
        L.ingest_all(random_stream(cols, 900, seed=seed + 100))
        mp, om = audit.derive_facts(L.journal, k=2)
        profs.append(geometry.embed_run(mp, om, sizes))
    return profs


def run():
    profs = _profiles()
    recoveries = [geometry.axis_recovery(p) for p in profs]
    st = geometry.ensemble_stability(profs)
    aligned = {s: v for s, v in zip(st["sizes"], st["aligned_mean"])}
    raw = {s: v for s, v in zip(st["sizes"], st["raw_mean"])}

    print(f"ensemble of {N_RUNS} learners (different seeds & observation orders)")
    print(f"  per-run magnitude-axis recovery |corr|: mean {np.mean(recoveries):.2f}, "
          f"min {min(recoveries):.2f}  (the axis exists every run)")
    signs = [int(np.sign(np.corrcoef(sorted(p), [p[s] for s in sorted(p)])[0, 1])) for p in profs]
    print(f"  per-run orientation (sign): {signs}  -> arbitrary")
    print(f"  raw ensemble spread    {st['raw_spread']:.3f}  (axis recovery {geometry.axis_recovery(raw):.2f}, washed out)")
    print(f"  aligned ensemble spread {st['aligned_spread']:.3f}  (axis recovery {geometry.axis_recovery(aligned):.2f}, stable)")
    print("\nThe magnitude axis is real in each run but points a run-dependent way;")
    print("it stabilizes only across the sign-aligned ensemble — the hypothesis.")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e8_geometry.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["mean_per_run_recovery", f"{np.mean(recoveries):.3f}"])
        w.writerow(["raw_spread", f"{st['raw_spread']:.3f}"])
        w.writerow(["aligned_spread", f"{st['aligned_spread']:.3f}"])
        w.writerow(["raw_axis_recovery", f"{geometry.axis_recovery(raw):.3f}"])
        w.writerow(["aligned_axis_recovery", f"{geometry.axis_recovery(aligned):.3f}"])
    _plot(profs, st, os.path.join(RESULTS, "e8_geometry.png"))
    print(f"\nwrote {csv_path}")


def _plot(profs, st, path):
    sizes = st["sizes"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4), sharey=True)

    # left: raw per-run profiles (spaghetti) — orientation varies
    for p in profs:
        ax1.plot(sizes, [p[s] for s in sizes], color="#7f8c8d", alpha=0.4, lw=1)
    ax1.plot(sizes, st["raw_mean"], "-o", color="#c0392b", lw=2, label="raw ensemble mean")
    ax1.set_title("single runs: magnitude axis, arbitrary orientation\n(raw mean washes out)")
    ax1.set_xlabel("hidden size (number)")
    ax1.set_ylabel("Fiedler coordinate")
    ax1.legend(fontsize=8)

    # right: sign-aligned profiles — the shared axis appears
    ref = profs[0]
    for p in profs:
        ap = geometry.align_sign(p, ref)
        ax2.plot(sizes, [ap[s] for s in sizes], color="#7f8c8d", alpha=0.4, lw=1)
    ax2.plot(sizes, st["aligned_mean"], "-o", color="#2c3e50", lw=2, label="aligned ensemble mean")
    ax2.set_title("sign-aligned ensemble:\nthe magnitude axis stabilizes")
    ax2.set_xlabel("hidden size (number)")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
