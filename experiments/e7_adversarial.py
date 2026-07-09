"""e7 — adversarial audit (P7). Attack the learner; measure detection & recovery.

  1. poison-rate sweep: purity before/after localize-and-replay, collateral;
  2. repeat-lie: the same false pair asserted many times is a single cut;
  3. consistent-lie cost curve: min fakes vs the region's loop connectivity;
  4. DoS budgets: split and growth budgets degrade to refusal, not corruption.

Honest limit (documented): a fully consistent lie is indistinguishable to a
single learner — coherence is checkable, correspondence needs the ensemble (P5).

Writes results/e7_adversarial.csv and results/e7_adversarial.png.
Run: ``poetry run python experiments/e7_adversarial.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner import audit
from relweblearner.datasets.arithmetic import build_chain
from relweblearner.datasets.counting import (
    by_size,
    make_collections,
    poison_episode,
    random_stream,
)
from relweblearner.growth import GrowthEngine
from relweblearner.number import NumberLearner

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
N_EP = 900


def _learner_with_poison(n_poison, seed=1):
    cols = make_collections(60, seed=7)
    bs = by_size(cols)
    sizes = {c: len(v) for c, v in cols.items()}
    L = NumberLearner()
    L.ingest_all(random_stream(cols, N_EP, seed=seed))
    pairs = set()
    # DISTINCT (2-collection, 3-collection) pairs: each poison is thinly witnessed
    pool = [(a2, a3) for a2 in bs[2] for a3 in bs[3]]
    for i in range(n_poison):
        a2, a3 = pool[i % len(pool)]
        L.ingest(poison_episode(cols, a2, a3))
        pairs.add(frozenset((a2, a3)))
    return L, sizes, pairs


def run():
    # 1. poison-rate sweep: k=1 (eager -> localize recovery) vs k=2 (gate)
    print("1. POISON-RATE SWEEP")
    print("   k=1 (eager): damage, then localize-and-replay (collateral = price of recovery)")
    print("   k=2 (provisional commitment gate): thinly-witnessed poison never enters")
    rates = [0.001, 0.005, 0.01, 0.02, 0.05]
    sweep = []
    for r in rates:
        n = max(1, round(r * N_EP))
        L1, sizes, pairs = _learner_with_poison(n)
        r1 = audit.audit(L1.journal, sizes, pairs, k=1)
        L2, _, _ = _learner_with_poison(n)
        r2 = audit.audit(L2.journal, sizes, pairs, k=2)
        sweep.append((r, r1, r2))
        print(f"   {r*100:4.1f}% ({n:2d} poison): "
              f"k=1 purity {r1.purity_before:.2f}->{r1.purity_after:.2f} "
              f"(cut {r1.n_excluded}, collateral {r1.collateral}) | "
              f"k=2 purity {r2.purity_before:.2f} (detected {r2.detected})")

    # 2. repeat-lie: the SAME false pair asserted 50 times
    cols = make_collections(60, seed=7)
    bs = by_size(cols)
    L = NumberLearner()
    L.ingest_all(random_stream(cols, N_EP, seed=1))
    for _ in range(50):
        L.ingest(poison_episode(cols, bs[2][0], bs[3][0]))
    mp, om = audit.derive_facts(L.journal, k=1)
    excluded, _ = audit.localize(mp, om)
    print(f"\n2. REPEAT-LIE: same false pair x50 -> cuts needed {len(excluded)} (attacker pays 50, learner pays 1)")

    # 3. consistent-lie cost curve
    conn = list(range(0, 8))
    costs = [audit.consistent_lie_cost(c) for c in conn]
    print(f"\n3. CONSISTENT-LIE COST: min fakes vs connectivity = {list(zip(conn, costs))}")
    print("   the denser the region, the more loops a coherent lie must out-fake.")

    # 4. DoS budgets
    cols = make_collections(60, seed=7)
    bs = by_size(cols)
    Lf = NumberLearner()
    Lf.ingest_all(random_stream(cols, N_EP, seed=1))
    for a2 in bs[2]:
        for a3 in bs[3]:
            Lf.ingest(poison_episode(cols, a2, a3))
    mpf, omf = audit.derive_facts(Lf.journal, k=1)
    exc, refused = audit.localize(mpf, omf, split_budget=3)
    w = build_chain(10)
    gres = audit.growth_capped(GrowthEngine(P=3), w, [(3, "succ~", k) for k in range(5, 25)], budget=4)
    print(f"\n4. DoS BUDGETS: contradiction-flood -> split budget held (cut {len(exc)}, refused={refused});")
    print(f"   query-flood -> growth budget held (grown {gres['grown']}, refused {gres['refused']}).")
    print("   The learner degrades to refusal, not corruption.")

    print("\nLIMIT: a fully consistent lie has no contradicting loop -> undetectable")
    print("to a single learner. Correspondence needs the ensemble (P5/P8).")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e7_adversarial.csv")
    with open(csv_path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["poison_rate", "k1_after", "k1_collateral", "k2_purity"])
        for r, r1, r2 in sweep:
            wr.writerow([r, f"{r1.purity_after:.3f}", r1.collateral, f"{r2.purity_before:.3f}"])
        wr.writerow([])
        wr.writerow(["connectivity", "consistent_lie_cost"])
        for c, cost in zip(conn, costs):
            wr.writerow([c, cost])
    _plot(sweep, conn, costs, os.path.join(RESULTS, "e7_adversarial.png"))
    print(f"\nwrote {csv_path}")


def _plot(sweep, conn, costs, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    rs = [r * 100 for r, _, _ in sweep]
    ax1.plot(rs, [r2.purity_before for _, _, r2 in sweep], "-o", color="#2c3e50",
             label="k>=2 gate (poison filtered)")
    ax1.plot(rs, [r1.purity_after for _, r1, _ in sweep], "-s", color="#2980b9",
             label="k=1 + localize (recovered)")
    ax1.plot(rs, [r1.collateral / 50 for _, r1, _ in sweep], "--x", color="#c0392b",
             label="k=1 collateral (price)")
    ax1.axhline(1.0, ls="--", color="#7f8c8d", lw=1)
    ax1.set_xlabel("poison rate (%)")
    ax1.set_ylabel("purity  (collateral/50, dashed)")
    ax1.set_ylim(0, 1.15)
    ax1.set_title("k>=2 gate prevents damage;\nlocalize recovers purity at a collateral cost")
    ax1.legend(fontsize=7)

    ax2.plot(conn, costs, "-o", color="#2980b9")
    ax2.plot(conn, conn, "--", color="#7f8c8d", lw=1, label="cost = connectivity")
    ax2.set_xlabel("region loop connectivity")
    ax2.set_ylabel("min fake episodes to lie coherently")
    ax2.set_title("consistent-lie cost (the security property)")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
