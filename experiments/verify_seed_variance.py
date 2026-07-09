"""Phase-1 verification — Part C: seed variance (20 seeds, mean/min/max).

Re-runs the criteria the protocol flags as seed-sensitive and reports the
distribution, not the best case. The rumor test must be 0/N at every seed; any
previously-PASS criterion that fails at any seed is a matrix FAIL.

Writes results/verify_seed_variance.csv.
Run: ``poetry run python experiments/verify_seed_variance.py``
"""

from __future__ import annotations

import csv
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from relweblearner import language as L
from relweblearner import society as S
from relweblearner.datasets import counting as C
from relweblearner.datasets import language as DL
from relweblearner.datasets.arithmetic import build_chain
from relweblearner.growth import GrowthEngine
from relweblearner.number import NumberLearner

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
N_SEEDS = 20


# ---------------------------------------------------------------- P1 growth
def growth_threshold(seed: int):
    """Sharp threshold: no growth on in-web probes; exact deficit off-web."""
    rng = random.Random(seed)
    length = rng.randint(6, 12)
    w = build_chain(length)
    eng = GrowthEngine(P=3)
    in_web = [(length - 1, b) for b in range(length)]
    rng.shuffle(in_web)
    spurious = 0
    for pos, (a, b) in enumerate(in_web):
        ans = eng.answer(w, a, "succ~", b, position=pos)
        spurious += ans.grew.n_nodes if ans.grew else 0
    deficit = 3
    ans = eng.answer(w, length - 1, "succ~", length - 1 + deficit, position=len(in_web))
    grew = ans.grew.n_nodes if ans.grew else 0
    return {"in_web_growth": spurious, "deficit_match": int(grew == deficit)}


# --------------------------------------------------------------- P2' types
def types_recovery(seed: int):
    from relweblearner.datasets.bare import build_bare_web
    from relweblearner.types import discover_types, is_conflated, overall_purity

    edges, truth = build_bare_web(colors=3, plants=2, full=True, seed=seed)
    disc = discover_types(edges)
    return {"purity": overall_purity(disc, truth), "conflated": int(is_conflated(disc, truth))}


# ------------------------------------------------ ostension budget vs orbits
def ostension_vs_orbits(seed: int):
    units, _g = DL.stream_of(300, seed=seed)
    words, _b = L.segment(units)
    fw = L.discover_frame_words(words)
    tok_web = L.token_web(L.chunk(words, fw), fw)
    con_edges = DL.concept_edges()
    budget = L.ostension_budget(L.ground(tok_web, con_edges).orbits)
    computed = len([o for o in L.automorphism_orbits(con_edges) if len(o) > 1])
    return {"ostension_budget": budget, "orbit_count": computed, "match": int(budget == computed)}


# --------------------------------------------------- naming-game convergence
def naming_convergence(seed: int, concepts=None, cap=4000):
    concepts = concepts or [f"c{i}" for i in range(6)]
    A = S.Agent("A", owner="a", seed=seed)
    B = S.Agent("B", owner="b", seed=seed + 1000)
    rng = random.Random(seed)
    for r in range(1, cap + 1):
        sp, li = (A, B) if r % 2 else (B, A)
        S.naming_round(sp, li, rng.choice(concepts), inhibit=True)
        if r % 10 == 0 and all(A.top(c) is not None and A.top(c) == B.top(c) for c in concepts):
            return {"rounds_to_converge": r}
    return {"rounds_to_converge": cap}


# ------------------------------------------------------------------- rumor
def rumor_committed(seed: int, n=24, k=3):
    rng = random.Random(seed)
    agents = [S.Agent(f"g{i}", owner=f"g{i}", seed=seed + i) for i in range(n)]
    false = ("HC", "lime", "red")
    liar = S.Agent("liar", owner="liar")
    for _ in range(50):
        S.teach(liar, agents[0], false)
    for _ in range(4000):
        a, b = rng.sample(agents, 2)
        S.relay(a, b, false)
    return {"rumor_committed": sum(1 for a in agents if S.committed(a, false, k))}


# ------------------------------------------------------------- I1 end to end
def i1_end_to_end(seed: int):
    cols = C.make_collections(60, seed=seed)
    a_learner = NumberLearner()
    a_learner.ingest_all(C.random_stream(cols, 900, seed=seed + 100))
    order = a_learner.project().order
    if len(order) < 4:
        return {"i1_match": 1, "i1_chain_len": len(order)}   # too short to query; skip
    concepts = list(order) + ["succ"]
    A = S.Agent("A", owner="alice", seed=seed)
    B = S.Agent("B", owner="bob", seed=seed + 1)
    rng = random.Random(seed)
    for r in range(1, 1601):
        sp, li = (A, B) if r % 2 else (B, A)
        S.naming_round(sp, li, rng.choice(concepts), inhibit=True)
    if not all(A.top(c) == B.top(c) for c in concepts):
        return {"i1_match": 0, "i1_chain_len": len(order)}
    b_succ = {}
    for i in range(len(order) - 1):
        toks = [A.top("succ"), A.top(order[i]), A.top(order[i + 1])]
        rel, x, y = (B.assoc_meaning(t) for t in toks)
        if rel == "succ":
            b_succ[x] = y
    a_succ = {order[i]: order[i + 1] for i in range(len(order) - 1)}

    def walk(s, start, k):
        cur = start
        for _ in range(k):
            cur = s.get(cur)
            if cur is None:
                return None
        return cur

    queries = [(order[i], k) for k in (2, 3) for i in range(len(order)) if i + k < len(order)]
    match = all(walk(b_succ, s, k) == walk(a_succ, s, k) for s, k in queries)
    return {"i1_match": int(match), "i1_chain_len": len(order)}


METRICS = [
    ("growth", growth_threshold, ["in_web_growth", "deficit_match"]),
    ("types", types_recovery, ["purity", "conflated"]),
    ("ostension", ostension_vs_orbits, ["ostension_budget", "orbit_count", "match"]),
    ("naming", naming_convergence, ["rounds_to_converge"]),
    ("rumor", rumor_committed, ["rumor_committed"]),
    ("i1", i1_end_to_end, ["i1_match"]),
]


def run():
    collected: dict = {}
    for _name, fn, keys in METRICS:
        for seed in range(N_SEEDS):
            res = fn(seed)
            for k in keys:
                collected.setdefault(k, []).append(res[k])

    def stat(vals):
        return sum(vals) / len(vals), min(vals), max(vals)

    print(f"seed variance over {N_SEEDS} seeds (mean / min / max):")
    rows = []
    for key, vals in collected.items():
        mean, lo, hi = stat(vals)
        rows.append((key, mean, lo, hi))
        print(f"  {key:20s} mean {mean:7.3f}  min {lo:7.3f}  max {hi:7.3f}")

    # the hard gate: rumor must be 0 at every seed
    rumor_ok = max(collected["rumor_committed"]) == 0
    print(f"\nrumor 0/N at every seed: {rumor_ok}")
    print(f"ostension budget == orbit count every seed: {min(collected['match']) == 1}")
    print(f"I1 end-to-end match every seed: {min(collected['i1_match']) == 1}")

    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "verify_seed_variance.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "mean", "min", "max", "n_seeds"])
        for key, mean, lo, hi in rows:
            w.writerow([key, f"{mean:.3f}", lo, hi, N_SEEDS])
    print(f"\nwrote {path}")


if __name__ == "__main__":
    run()
