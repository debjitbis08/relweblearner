"""Graded ensemble: mechanism tests on synthetic webs (no data needed).

The substantive predictions live in docs/graded-ensemble-plan.md and are
scored by the two arm runs — these pin the coupling mechanisms they rest on.
"""

from collections import Counter

import networkx as nx
import numpy as np

from relweblearner.bench import multiweb_graded as GR


def _mirror(votes, m):
    return {(m[a], m[b]): Counter({m[c]: n for c, n in heads.items()})
            for (a, b), heads in votes.items()}


def test_token_field_finds_isomorphism():
    va = {("a1", "a2"): Counter({"a3": 5}),
          ("a3", "a1"): Counter({"a4": 4}),
          ("a2", "a4"): Counter({"a1": 3})}
    true = {"a1": "b1", "a2": "b2", "a3": "b3", "a4": "b4"}
    vb = _mirror(va, true)
    ia, ib, S = GR.token_similarity(va, vb, {"a1": "b1"})
    for x, y in true.items():
        assert int(S[ia[x]].argmax()) == ib[y]
    assert GR.hardened(ia, ib, S, {"a1": "b1"})["a4"] == "b4"


def test_graded_reduction_crosses_a_split_symbol():
    """A rule stated in B vocabulary fires on an A-symbol path at similarity
    strength — the seam-crossing that discrete translation could not do for
    unmapped symbols."""
    rules = [("b1", "b2", "b3")]
    sim = lambda p, s: 1.0 if p == s else (0.8 if (p, s) in
                                           {("b1", "a1"), ("b2", "a2")} else 0.0)
    out = GR.graded_reduce(("a1", "a2"), rules, sim, {})
    assert abs(out["b3"] - 0.64) < 1e-9


def test_unanchored_island_carries_no_mass():
    """Two webs, each with an anchored community and a dense unanchored
    island: the island's absolute mass is zero — identity flows only
    outward from co-witnessed events."""
    def web(tag, island):
        G = nx.Graph()
        com = [f"{tag}{i}" for i in range(4)]
        for i in range(4):
            for j in range(i + 1, 4):
                G.add_edge(com[i], com[j], weight=10)
        isl = [f"{tag}x{i}" for i in range(4)] if island else []
        for i in range(len(isl)):
            for j in range(i + 1, len(isl)):
                G.add_edge(isl[i], isl[j], weight=10)
        if isl:
            G.add_edge(isl[0], com[0], weight=1)     # sub-backbone attachment
        return G, com, isl

    GA, com_a, isl_a = web("a", island=True)
    GB, com_b, _ = web("b", island=False)
    anchors = {com_a[0]: com_b[0], com_a[1]: com_b[1]}
    ia, ib, M = GR.node_similarity(GA, GB, anchors)
    assert M[[ia[n] for n in isl_a]].sum() == 0.0
    assert M[ia[com_a[2]]].sum() > 0.0               # unanchored true node flows
    assert GR.soft_correspondence(frozenset(isl_a), ia, ib, M,
                                  [frozenset(com_b)]) == 0.0


def test_forgery_seed_deterministic():
    assert GR.run_forgery_seed(1001) == GR.run_forgery_seed(1001)
