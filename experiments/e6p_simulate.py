"""e6' — simulation & lookahead (P6'). Imagine, then act.

A seam over parts already built: fork + apply + score by holonomy. Shows
imagine-then-commit, rehearsal-refusal, lookahead, counterfactual provenance,
and the documented limit (coherence != correspondence).

Writes results/e6p_simulate.csv and results/e6p_simulate.png.
Run: ``poetry run python experiments/e6p_simulate.py``
"""

from __future__ import annotations

import csv
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.algebra import IntegerGroup
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner
from relweblearner.simulate import Simulator, cf_trace_ids, committed_has_no_cf
from relweblearner.web import Web

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def _scenario(seed: int):
    rng = random.Random(seed)
    L = 6
    w = Web(IntegerGroup(), name="play")
    for i in range(L):
        w.add_node(f"n{i}")
    for i in range(L - 1):
        w.add_edge(f"n{i}", f"n{i + 1}", "succ", 1)
    r = rng.randint(1, L - 2)
    w.add_node("p")
    w.add_edge(f"n{r}", "p", "same", 0)
    targets = rng.sample([f"n{i}" for i in range(L)], 3)
    if f"n{r}" not in targets:
        targets[0] = f"n{r}"
    return w, [("merge", "p", t) for t in targets], ("merge", "p", f"n{r}")


def run():
    # 1+2. imagine-then-commit / rehearsal-refusal
    w, candidates, clean = _scenario(0)
    sim = Simulator(w)
    print("1+2. IMAGINE-THEN-COMMIT")
    for c in candidates:
        out = sim.imagine_then_commit(c) if c == clean else sim.imagine_then_commit(c)
        tag = "COMMIT" if out.committed else "REFUSE"
        print(f"    {c}: {tag}  ({out.reason})")

    # 3. lookahead over 20 seeds
    hits = 0
    example = None
    for seed in range(20):
        w, cands, cln = _scenario(seed)
        best, scores = Simulator(w).lookahead(cands)
        hits += best == cln
        if seed == 0:
            example = {tuple(m): s.defect for m, s in scores.items()}
    print(f"\n3. LOOKAHEAD: picked the min-defect candidate {hits}/20 seeds")
    print(f"    (seed 0 simulated defects: {example})")

    # 4. counterfactual provenance
    w, cands, _ = _scenario(1)
    sim = Simulator(w)
    for c in cands:
        sim.simulate(c)
    L = NumberLearner()
    L.ingest_all(random_stream(make_collections(60, seed=7), 900, seed=1))
    chain = L.project()
    reports = cf_trace_ids(w)
    counted = L.count(chain, set(reports))
    print(f"\n4. CF PROVENANCE: {len(reports)} simulated acts, none in committed "
          f"({committed_has_no_cf(w)}); counted with own chain -> {counted}")

    # limit: a consistent lie is not caught
    w2 = Web(IntegerGroup(), name="play")
    for i in range(3):
        w2.add_node(f"n{i}")
    for i in range(2):
        w2.add_edge(f"n{i}", f"n{i + 1}", "succ", 1)
    w2.add_node("x")
    lie = Simulator(w2).imagine_then_commit(("merge", "n0", "x"))
    print(f"\nLIMIT (coherence != correspondence): a consistent-but-false merge "
          f"commits = {lie.committed}. Simulation checks coherence; correspondence")
    print("    needs an independent source (the ensemble, P5/P7).")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e6p_simulate.csv")
    with open(csv_path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["metric", "value"])
        wr.writerow(["lookahead_hits_of_20", hits])
        wr.writerow(["cf_simulations", len(reports)])
        wr.writerow(["cf_in_committed", not committed_has_no_cf(w)])
        wr.writerow(["self_counted_simulations", counted])
        wr.writerow(["consistent_lie_committed", lie.committed])
    _plot(example, hits, os.path.join(RESULTS, "e6p_simulate.png"))
    print(f"\nwrote {csv_path}")


def _plot(seed0_scores, hits, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    labels = [f"{m[2]}" for m in seed0_scores]
    vals = list(seed0_scores.values())
    colors = ["#2c3e50" if v == 0 else "#c0392b" for v in vals]
    ax1.bar(labels, vals, color=colors)
    ax1.set_title("lookahead: simulated defect per candidate\n(seed 0; dark = chosen)")
    ax1.set_ylabel("defect mass on the fork")
    ax1.set_xlabel("merge p with …")

    ax2.bar(["lookahead\ncorrect"], [hits], color="#2980b9")
    ax2.axhline(20, ls="--", color="#7f8c8d")
    ax2.set_ylim(0, 21)
    ax2.set_title("lookahead picks min-defect (of 20 seeds)")
    ax2.text(0, hits + 0.3, f"{hits}/20", ha="center")

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
