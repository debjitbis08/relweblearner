"""P1 acceptance (e1): forced-growth threshold.

From the dev-doc, e1 accepts iff the system:
  (a) refuses growth while probes stay inside the web,
  (b) grows exactly |deficit| nodes on the probe 3-5,
  (c) zero-shot: after growth, unseen arithmetic through the new nodes is exact.
Plus: growth is persistence-gated (survives P rounds first), and an obstruction
that an existing node can complete is discharged by rewire, not growth.
"""

from __future__ import annotations

import pytest

from relweblearner.datasets.arithmetic import build_chain, coordinates
from relweblearner.growth import GrowthEngine


# ------------------------------------------------------------- accept (a)
def test_refuses_growth_while_probes_stay_inside_the_web():
    w = build_chain(10)
    eng = GrowthEngine(P=3)
    co = coordinates(w)
    for a, b in [(5, 3), (9, 9), (7, 0), (4, 4), (8, 2)]:   # all a-b in 0..9
        ans = eng.answer(w, a, "succ~", b, position=0)
        assert ans.grew is None, f"{a}-{b} should not grow"
        assert co[ans.endpoint] == a - b
    assert eng.events == []
    assert w.total_cost == 0                                # no cost paid at all


# ------------------------------------------------------------- accept (b)
def test_grows_exactly_deficit_on_3_minus_5():
    w = build_chain(10)
    eng = GrowthEngine(P=3)
    ans = eng.answer(w, 3, "succ~", 5, position=0)

    assert ans.grew is not None
    assert ans.grew.n_nodes == 2                            # |3 - 5| deficit
    assert ans.rounds_survived == 3                          # survived P rounds first
    co = coordinates(w)
    assert co[ans.endpoint] == -2                            # 3 - 5
    assert sorted(co.values()) == list(range(-2, 10))        # exactly two new nodes


# ------------------------------------------------------------- accept (c)
def test_zero_shot_arithmetic_through_new_nodes_is_exact():
    w = build_chain(10)
    eng = GrowthEngine(P=3)
    eng.answer(w, 3, "succ~", 5, position=0)                 # invents -1, -2

    co = coordinates(w)
    by_coord = {c: n for n, c in co.items()}
    facts = 0
    # every ordered pair whose path crosses a grown (negative-coord) node
    for a in range(-2, 10):
        for b in range(a + 1, 10):
            if a >= 0:
                continue                                     # must involve a new node
            start, delta = by_coord[a], b - a
            res = w.walk(start, "succ", delta)               # a + delta
            assert not res.off_web
            assert co[res.endpoint] == b, f"{a}+{delta} != {b}"
            facts += 1
    assert facts >= 20                                       # >= 20 unseen facts, all exact


# --------------------------------------------------- persistence / rewire
def test_obstruction_completable_in_web_is_discharged_by_rewire_not_growth():
    # remove a middle edge; the walk stalls but the target nodes already exist,
    # so a single rewire completes it and growth is refused.
    w = build_chain(10)
    # find and remove the 4->5 edge
    e45 = next(e for e in w.edges() if e.u == 4 and e.v == 5)
    w.rewire(remove=e45.eid)
    n_nodes = len(w.nodes)

    eng = GrowthEngine(P=3)
    ans = eng.answer(w, 3, "succ", 4, position=0)            # 3 -> 4 -> [gap] -> 7
    assert ans.grew is None                                  # discharged, not grown
    assert eng.events == []
    assert len(w.nodes) == n_nodes                           # no new nodes
    co = coordinates(w)
    assert co[ans.endpoint] == 7                             # 3 + 4, completed in-web


# ------------------------------------------------------------- threshold
def test_growth_is_a_sharp_threshold_not_a_drift():
    # in-web probes first (positions 0..9), then off-web. Growth must be zero
    # for every in-web probe and only turn on once a probe leaves the web.
    w = build_chain(10)
    eng = GrowthEngine(P=3)
    stream = [(9, b) for b in range(10)] + [(9, 10), (9, 11), (9, 12)]

    grown_per_pos = []
    for pos, (a, b) in enumerate(stream):
        ans = eng.answer(w, a, "succ~", b, position=pos)
        grown_per_pos.append(ans.grew.n_nodes if ans.grew else 0)

    in_web = grown_per_pos[:10]
    off_web = grown_per_pos[10:]
    assert in_web == [0] * 10                                # flat zero inside
    assert all(g > 0 for g in off_web)                       # onset at the boundary
    # first growth is exactly at the first off-web probe: a threshold, not a ramp
    assert grown_per_pos.index(next(g for g in grown_per_pos if g)) == 10
