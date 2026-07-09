"""e3 — compositional holdout vs baselines (P3).

Train on ``n -(+k)-> n+k`` for ``k in {1, 2}`` (entities 0..199); hold out all
``k = 5`` facts. The web learner scores ``+5`` by transport composition —
Hits@1 = 1.0 by construction, zero parameters learned for the held-out
relation. TransE and ComplEx (dim 32) must compose their learned relation
embeddings; the gap is the headline sample-efficiency figure.

Writes results/e3_holdout.csv and results/e3_holdout.png.
Run: ``poetry run python experiments/e3_holdout.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.datasets.holdout import build_holdout
from relweblearner.holdout import complex_metrics, transe_metrics, web_metrics


def run():
    data = build_holdout(N=200, train_ks=(1, 2), test_k=5)
    print(f"entities={data.n_entities}  train={len(data.train)}  held-out +5={len(data.test)}")
    print("scoring the held-out +5 relation (never seen in training):\n")

    results = [
        web_metrics(data),
        transe_metrics(data, epochs=800, seed=0),
        complex_metrics(data, epochs=300, seed=0),
    ]
    print(f"  {'model':8}  {'Hits@1':>7}  {'Hits@10':>7}  {'MRR':>6}")
    for m in results:
        print(f"  {m.name:8}  {m.hits1:7.3f}  {m.hits10:7.3f}  {m.mrr:6.3f}")

    web = results[0]
    print("\ngap (web - best baseline):")
    for m in results[1:]:
        print(f"  vs {m.name}: Hits@1 +{web.hits1 - m.hits1:.3f}, MRR +{web.mrr - m.mrr:.3f}")
    print("\nThe web is exact with ZERO parameters for +5; the baselines train on")
    print("hundreds of triples and still cannot compose the held-out relation.")

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    base = os.path.join(os.path.dirname(__file__), "..", "results")
    with open(os.path.join(base, "e3_holdout.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "hits1", "hits10", "mrr"])
        for m in results:
            w.writerow([m.name, f"{m.hits1:.4f}", f"{m.hits10:.4f}", f"{m.mrr:.4f}"])
    _plot(results, os.path.join(base, "e3_holdout.png"))
    print(f"\nwrote {os.path.join(base, 'e3_holdout.csv')}")


def _plot(results, path):
    names = [m.name for m in results]
    x = range(len(names))
    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.27
    ax.bar([i - w for i in x], [m.hits1 for m in results], w, label="Hits@1", color="#2c3e50")
    ax.bar([i for i in x], [m.hits10 for m in results], w, label="Hits@10", color="#2980b9")
    ax.bar([i + w for i in x], [m.mrr for m in results], w, label="MRR", color="#c0392b")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("score on held-out +5")
    ax.set_title("e3: compositional holdout (+5 = +1 ∘ +2 ∘ +2)\nweb is exact by construction; KGE baselines cannot compose")
    ax.legend(loc="center right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
