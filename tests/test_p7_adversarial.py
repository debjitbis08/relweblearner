"""P7 acceptance (e7): adversarial audit.

  * poison-rate: purity restored to 1.0 at <= 1% poison; detection 100% for
    contradictions reachable by observed loops;
  * repeat-lie: the same false pair asserted many times is a single cut;
  * k>=2 provisional commitment blocks a lone-episode poison outright;
  * consistent-lie cost grows with the region's loop connectivity;
  * DoS: split and growth budgets hold — the learner degrades to refusal.
"""

from __future__ import annotations

from relweblearner import audit
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets.arithmetic import build_chain
from relweblearner.datasets.counting import (
    by_size,
    make_collections,
    poison_episode,
    random_stream,
)
from relweblearner.growth import GrowthEngine
from relweblearner.number import NumberLearner


def _poisoned_learner(n_poison: int, seed: int = 1):
    cols = make_collections(60, seed=7)
    bs = by_size(cols)
    sizes = {c: len(v) for c, v in cols.items()}
    L = NumberLearner()
    L.ingest_all(random_stream(cols, 900, seed=seed))
    pairs = set()
    for _ in range(n_poison):
        a2, a3 = bs[2][0], bs[3][0]
        L.ingest(poison_episode(cols, a2, a3))
        pairs.add(frozenset((a2, a3)))
    return L, sizes, pairs


# ------------------------------------------------------- poison-rate / detect
def test_poison_purity_restored_and_detection_100pct():
    # ~1% of 900 episodes = ~9 poison
    L, sizes, pairs = _poisoned_learner(n_poison=9)
    res = audit.audit(L.journal, sizes, pairs, k=1)
    assert res.detected                                # contradiction reachable
    assert res.purity_before < 1.0                     # damage before recovery
    assert res.purity_after == 1.0                     # restored by localize-replay


def test_no_poison_no_detection_no_change():
    L, sizes, _ = _poisoned_learner(n_poison=0)
    res = audit.audit(L.journal, sizes, set(), k=1)
    assert not res.detected
    assert res.purity_after == 1.0


# --------------------------------------------------------------- repeat-lie
def test_repeat_lie_is_a_single_cut():
    L, sizes, pairs = _poisoned_learner(n_poison=50)   # same false pair x50
    match_pairs, onemores = audit.derive_facts(L.journal, k=1)
    excluded, refused = audit.localize(match_pairs, onemores)
    assert len(excluded) == 1                           # one cut, not fifty
    assert not refused


# --------------------------------------------------- k>=2 provisional gate
def test_k2_gate_blocks_a_lone_episode_poison():
    L, sizes, _ = _poisoned_learner(n_poison=1)         # a single poison episode
    weak = audit.audit(L.journal, sizes, set(), k=1)
    gated = audit.audit(L.journal, sizes, set(), k=2)
    assert weak.detected and weak.purity_before < 1.0   # k=1 lets it in (then repairs)
    assert not gated.detected                           # k=2 never commits it
    assert gated.purity_before == 1.0                   # no damage at all


# ---------------------------------------------------- consistent-lie curve
def test_consistent_lie_cost_grows_with_connectivity():
    costs = [audit.consistent_lie_cost(c) for c in range(0, 6)]
    assert costs == [0, 1, 2, 3, 4, 5]                  # one fake per loop
    assert all(b > a for a, b in zip(costs, costs[1:]))  # strictly increasing


# ------------------------------------------------------------ DoS budgets
def test_split_budget_degrades_to_refusal():
    # a contradiction flood: many distinct poisoned pairs
    cols = make_collections(60, seed=7)
    bs = by_size(cols)
    sizes = {c: len(v) for c, v in cols.items()}
    L = NumberLearner()
    L.ingest_all(random_stream(cols, 900, seed=1))
    # poison many distinct 2<->3 pairs
    for a2 in bs[2]:
        for a3 in bs[3]:
            L.ingest(poison_episode(cols, a2, a3))
    match_pairs, onemores = audit.derive_facts(L.journal, k=1)
    excluded, refused = audit.localize(match_pairs, onemores, split_budget=3)
    assert len(excluded) <= 3                            # budget held
    assert refused                                       # degraded to refusal


def test_growth_budget_bounds_growth():
    w = build_chain(10)
    eng = GrowthEngine(P=3)
    # unclosable-query flood: many off-web subtraction probes
    probes = [(3, "succ~", k) for k in range(5, 25)]     # all fall off the bottom
    res = audit.growth_capped(eng, w, probes, budget=4)
    assert res["within_budget"]
    assert res["grown"] <= 4
    assert res["refused"] > 0                            # excess queries refused
