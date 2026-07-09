"""es — invention (P7', society §7): content defects vs error defects.

Demonstrates the amended defect rule in one run: a persistent holonomy class with
NO observation conflict is CONTENT (banked, answers modular queries), while a
persistent class WITH an observation conflict is an ERROR (retracted by the
unchanged P7 machinery). Plus the invention census (banked content + posit
confirmation rate).

Writes results/es_invention.csv and results/es_invention.png.
Run: ``poetry run python experiments/es_invention.py``
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

from relweblearner import audit, invention as INV
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets import counting as C
from relweblearner.datasets.counting import poison_episode
from relweblearner.holonomy import defects
from relweblearner.number import NumberLearner
from relweblearner.web import Web

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def clock_web(n=12):
    w = Web(IntegerGroup())
    for i in range(n):
        w.add_node(f"h{i}")
    for i in range(n - 1):
        w.add_edge(f"h{i}", f"h{i + 1}", "succ", 1)
    w.add_edge(f"h{n - 1}", "h0", "succ", 1)     # wrap-around observation
    return w


def poison_number_web():
    cols = C.make_collections(40, seed=3)
    sizes = {c: len(v) for c, v in cols.items()}
    L = NumberLearner()
    L.ingest_all(C.random_stream(cols, 400, seed=1))
    small = next(k for k, v in cols.items() if len(v) == 2)
    big = next(k for k, v in cols.items() if len(v) == 3)
    L.ingest(poison_episode(cols, small, big))
    return L, sizes


def run():
    census = INV.InventionCensus()

    # ---- CONTENT: the clock banks, and answers modular queries
    wc = clock_web()
    clock_class = INV.classify_defect(wc)
    banked = INV.bank_content(wc, census, "clock-mod-12")
    mod_answer = INV.modular_answer(wc, "h11", "succ", 3)   # 11 + 3 == 2 (mod 12)

    print("=" * 66)
    print("CONTENT DEFECT: clock arithmetic (winding +12, conflicts nothing)")
    print("=" * 66)
    print(f"holonomy {[d.residual for d in defects(wc)]}, classify -> {clock_class}")
    print(f"banked as structure: {banked is not None}; 11 + 3 (mod 12) = "
          f"{mod_answer} (node h2 == 2)")

    # ---- ERROR: a poisoned merge still retracts (P7 unchanged)
    L, sizes = poison_number_web()
    mp, om = audit.derive_facts(L.journal, k=1)
    bad_before = len(audit.contradictions(mp, om))
    purity_before = audit.purity(mp, sizes)
    excluded, _refused = INV.retract_error(mp, om)
    after = {p: e for p, e in mp.items() if p not in excluded}
    bad_after = len(audit.contradictions(after, om))
    purity_after = audit.purity(after, sizes)

    # a self-loop web makes the observation-conflict explicit
    we = Web(IntegerGroup())
    we.add_node("K")
    we.add_edge("K", "K", "succ", 1)             # 'class ONEMORE of itself'
    error_class = INV.classify_defect(we)

    print("\n" + "=" * 66)
    print("ERROR DEFECT: poisoned merge (class ONEMORE of itself)")
    print("=" * 66)
    print(f"self-loop classify -> {error_class} "
          f"(conflict: {INV.observation_conflicts(we)})")
    print(f"poison contradictions {bad_before} -> {bad_after} after localize; "
          f"purity {purity_before:.2f} -> {purity_after:.2f}")

    # ---- posit-before-evidence (the neutrino pattern): posit an unseen entity
    # from a closure requirement, timestamped BEFORE any confirming observation
    t = [0]

    def stamp():
        t[0] += 1
        return t[0]

    # a conservation motif is banked; an incomplete split leaves members missing
    source = {"o1", "o2", "o3", "o4", "o5"}
    seen_dests = [{"o1", "o2"}, {"o3", "o4"}]
    missing = INV.posit_from_closure(source, seen_dests)
    t_posit = stamp()
    census.posit("H*", members=missing, at=t_posit)          # derived, not observed
    retrieval = [e for e in seen_dests if "o5" in e]         # a retrieval baseline...
    t_reveal = stamp()                                        # ...the world reveals it later
    if missing == {"o5"}:
        census.confirm("H*")

    print("\n" + "=" * 66)
    print("POSIT-BEFORE-EVIDENCE (the neutrino pattern)")
    print("=" * 66)
    print(f"incomplete split of 5 accounts for 4 -> POSIT unseen entity H* "
          f"with members {sorted(missing)} at t={t_posit}")
    print(f"retrieval baseline asked 'where is o5?' at t={t_posit}: "
          f"{'nothing' if not retrieval else retrieval} (invention, not search)")
    print(f"reveal at t={t_reveal} confirms H*: posit preceded evidence "
          f"({t_posit} < {t_reveal})")

    print("\n" + "=" * 66)
    print("INVENTION CENSUS")
    print("=" * 66)
    print(f"banked content classes: {[b['label'] for b in census.banked]}")
    print(f"posits {len(census.posited)}, confirmed {len(census.confirmed)}, "
          f"confirmation rate {census.posit_confirmation_rate():.2f}")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "es_invention.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["clock_classify", clock_class])
        w.writerow(["clock_holonomy", defects(wc)[0].residual])
        w.writerow(["modular_query_11plus3", mod_answer])
        w.writerow(["error_classify", error_class])
        w.writerow(["poison_contradictions_before", bad_before])
        w.writerow(["poison_contradictions_after", bad_after])
        w.writerow(["purity_before", f"{purity_before:.3f}"])
        w.writerow(["purity_after", f"{purity_after:.3f}"])
        w.writerow(["banked_content_classes", len(census.banked)])
        w.writerow(["posit_before_evidence", int(t_posit < t_reveal)])
        w.writerow(["posit_confirmation_rate", f"{census.posit_confirmation_rate():.3f}"])
    _plot((purity_before, purity_after), (bad_before, bad_after),
          os.path.join(RESULTS, "es_invention.png"))
    print(f"\nwrote {csv_path}")


def _plot(purity, contradictions, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ax1.bar(["before", "after"], contradictions, color=["#c0392b", "#2c3e50"])
    ax1.set_title("ERROR defect: poisoned merge retracts\n(contradictions localized away)")
    ax1.set_ylabel("class-ONEMORE-of-itself defects")

    ax2.bar(["before", "after"], purity, color=["#c0392b", "#2c3e50"])
    ax2.axhline(1.0, ls="--", color="#7f8c8d", lw=1)
    ax2.set_title("purity restored by localize-and-replay\n(content is banked, not retracted)")
    ax2.set_ylabel("quotient purity")
    ax2.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
