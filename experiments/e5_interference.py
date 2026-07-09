"""e5 — N-web interference and the dynamic ensemble (P5).

Three webs (arithmetic, kinship, steps) share a journal. The learner:
  1. finds the mismatch-minimizing interface map over N webs by search;
  2. transfers through the interface fabric with zero shared parameters;
  3. resolves a poisoned identification by split;
  4. runs a stimulus stream where the number of webs evolves (merge / split).

Writes results/e5_interference.csv and results/e5_interference.png.
Run: ``poetry run python experiments/e5_interference.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner.datasets.kinship import (
    arithmetic_web,
    kinship_web,
    poison_identification,
    steps_web,
    true_identifications,
)
from relweblearner.ensemble import SPLIT, Ensemble

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def run():
    E = Ensemble()
    E.add_web(arithmetic_web(6))
    E.add_web(kinship_web(12))
    E.add_web(steps_web(10))
    print(f"ensemble of {len(E.webs)} webs: {sorted(E.webs)}")

    # 1. mismatch-minimizing interface map over N webs
    candidates = (
        true_identifications("a", "k", 6)
        + true_identifications("k", "s", 10)
        + [poison_identification("a", "k", 2, 2)]
    )
    offset, consistent, poison = E.find_interface_map(candidates)
    print(f"\n1. interface map: modal offset {offset}, "
          f"{len(consistent)} consistent, poison {poison}")
    for a, b in consistent:
        E.identify(a, b)
    print(f"   interface defect mass (map committed): {E.interface_defect_mass()}")

    # 2. transfer through the fabric (zero shared parameters)
    facts = [("a3", k) for k in range(1, 7)]
    without = E.answerable(facts, use_interface=False)
    with_iface = E.answerable(facts, use_interface=True)
    print(f"\n2. transfer: answerable without interface {without:.2f}, "
          f"with interface {with_iface:.2f}  (zero shared parameters)")

    # 3. poison -> split
    pz = E.identify(*poison[0])
    poisoned_mass = E.interface_defect_mass()
    E.resolve(pz, SPLIT)
    healed_mass = E.interface_defect_mass()
    print(f"\n3. poison identification: defect {poisoned_mass} -> split -> {healed_mass}")

    # 4. dynamic ensemble: the web count evolves over the stream
    events = (
        [("identify", "a", "k")] * 2
        + [("identify", "k", "s")] * 2
        + [("contradict", "a")] * 3
    )
    history = E.stream_dynamics(events, k=2, P=3)
    print(f"\n4. dynamic web-group count over the stream: {history}")
    print("   merges pull the count down (webs found to be one system); a")
    print("   persistent contradiction splits it back up — structure over time.")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "e5_interference.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["interface_map_offset", offset])
        w.writerow(["poison_detected", poison])
        w.writerow(["transfer_without", f"{without:.3f}"])
        w.writerow(["transfer_with", f"{with_iface:.3f}"])
        w.writerow(["poison_defect_mass", poisoned_mass])
        w.writerow(["after_split_mass", healed_mass])
        w.writerow(["web_count_history", history])
    _plot(events, history, without, with_iface, os.path.join(RESULTS, "e5_interference.png"))
    print(f"\nwrote {csv_path}")


def _plot(events, history, without, with_iface, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    ax1.step(range(len(history)), history, where="post", color="#2c3e50", lw=2)
    ax1.scatter(range(len(history)), history, color="#c0392b", zorder=3, s=30)
    ax1.set_xlabel("stimulus-stream position")
    ax1.set_ylabel("number of web-groups")
    ax1.set_yticks(range(0, max(history) + 2))
    ax1.set_title("dynamic ensemble: the web count is learned\n(merge pulls down, split pushes up)")
    ax1.grid(alpha=0.25)

    ax2.bar(["no interface", "interface"], [without, with_iface],
            color=["#7f8c8d", "#2980b9"])
    ax2.set_ylim(0, 1.1)
    ax2.set_ylabel("fraction of holdout facts answerable")
    ax2.set_title("transfer through the fabric\n(zero shared parameters)")
    for i, v in enumerate([without, with_iface]):
        ax2.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
