"""P6' acceptance (e6'): simulation & lookahead.

  * honest moves commit, incoherent moves are refused with reasons;
  * lookahead picks the min-defect candidate, 20/20 seeds;
  * the fork never mutates the real projection (1000 random move sequences);
  * no cf act ever appears in the committed projection, and simulations are
    countable with the P1b number chain.
Known limit (documented): simulation catches inconsistent lies, not consistent
ones — coherence != correspondence.
"""

from __future__ import annotations

import random

from relweblearner.algebra import IntegerGroup
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner
from relweblearner.simulate import Simulator, cf_trace_ids, committed_has_no_cf
from relweblearner.web import Web


def _scenario(seed: int):
    """A chain plus a floating node ``p`` at a random coordinate; candidate
    merges pair ``p`` with chain nodes. The min-defect merge aligns coordinates.
    """
    rng = random.Random(seed)
    L = 6
    w = Web(IntegerGroup(), name="play")
    for i in range(L):
        w.add_node(f"n{i}")
    for i in range(L - 1):
        w.add_edge(f"n{i}", f"n{i + 1}", "succ", 1)
    r = rng.randint(1, L - 2)
    w.add_node("p")
    w.add_edge(f"n{r}", "p", "same", 0)                # p sits at coord r
    targets = rng.sample([f"n{i}" for i in range(L)], 3)
    if f"n{r}" not in targets:
        targets[0] = f"n{r}"
    return w, [("merge", "p", t) for t in targets], ("merge", "p", f"n{r}")


# ------------------------------------------------- imagine-then-commit
def test_honest_commits_incoherent_refused_with_reason():
    w, candidates, clean = _scenario(0)
    sim = Simulator(w)
    incoherent = next(c for c in candidates if c != clean)

    out_bad = sim.imagine_then_commit(incoherent)
    assert not out_bad.committed
    assert "refused" in out_bad.reason and out_bad.delta_defect > 0

    out_good = sim.imagine_then_commit(clean)
    assert out_good.committed
    from relweblearner.holonomy import defect_mass
    assert defect_mass(w) == 0                          # real projection stays clean


# ---------------------------------------------------------- lookahead
def test_lookahead_picks_min_defect_20_seeds():
    for seed in range(20):
        w, candidates, clean = _scenario(seed)
        best, scores = Simulator(w).lookahead(candidates)
        assert best == clean, f"seed {seed}: {best} != {clean}"
        assert scores[tuple(clean)].defect == 0


# ---------------------------------------------- fork never mutates real
def test_fork_never_mutates_the_real_projection_1000_sequences():
    rng = random.Random(0x5)
    for _ in range(1000):
        w, candidates, _ = _scenario(rng.randint(0, 10_000))
        before_nodes = set(w.nodes)
        before_edges = {(e.u, e.v, e.value) for e in w.edges()}
        before_commits = list(w._commits)
        sim = Simulator(w)
        for _ in range(rng.randint(1, 4)):
            sim.simulate(rng.choice(candidates))       # simulate only, never commit
        assert set(w.nodes) == before_nodes
        assert {(e.u, e.v, e.value) for e in w.edges()} == before_edges
        assert w._commits == before_commits


# ------------------------------------------- cf provenance / counting
def test_no_cf_in_committed_and_simulations_are_countable():
    w, candidates, _ = _scenario(1)
    sim = Simulator(w)
    for c in candidates:
        sim.simulate(c)                                # 3 simulations -> 3 cf traces
    assert committed_has_no_cf(w)
    reports = cf_trace_ids(w)
    assert len(reports) == 3

    L = NumberLearner()
    L.ingest_all(random_stream(make_collections(60, seed=7), 900, seed=1))
    chain = L.project()
    assert L.count(chain, set(reports)) == 3           # count own simulations


# ------------------------------------ coherence != correspondence (limit)
def test_a_consistent_but_false_merge_is_not_caught_by_simulation():
    # p and a node in a DIFFERENT component: merging creates no cycle, so no
    # defect -> simulation says "clean" even if they are factually different.
    w = Web(IntegerGroup(), name="play")
    for i in range(3):
        w.add_node(f"n{i}")
    for i in range(2):
        w.add_edge(f"n{i}", f"n{i + 1}", "succ", 1)
    w.add_node("x")                                     # isolated, no distinguishing edge
    out = Simulator(w).imagine_then_commit(("merge", "n0", "x"))
    assert out.committed                                # simulation cannot refuse it
    # only an independent source (the ensemble, P5/P7) could catch this lie.
