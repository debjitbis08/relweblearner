"""P0 acceptance tests — the core-substrate correctness discipline.

From the dev doc, P0 accepts iff:
  1. a consistent web has zero defects;
  2. a single false-identity edge yields exactly one independent defect class;
  3. relabeling provably changes no defect (property test, 1000 random trials).

Test (3) is the relabel-invariance property test that Section 6 mandates
stays in CI and is run against every later phase.
"""

from __future__ import annotations

import random

import pytest

from relweblearner import (
    IntegerGroup,
    Web,
    cycle_basis_defects,
    defect_mass,
    defects,
    holonomy,
    potential,
)


def _chain(n: int) -> Web:
    """The naturals 0..n-1 with successor (+1) edges. A tree: no defects."""
    w = Web(IntegerGroup())
    for k in range(n):
        w.add_node(k)
    for k in range(n - 1):
        w.add_edge(k, k + 1, "succ", 1)
    return w


# --------------------------------------------------------------- accept (1)
def test_consistent_web_has_zero_defects():
    w = _chain(10)
    assert defects(w) == []
    assert defect_mass(w) == 0
    assert cycle_basis_defects(w) == []


def test_consistent_web_with_a_true_loop_has_zero_defects():
    # add a genuinely consistent chord: 0 -[+3]-> 3 agrees with succ^3.
    w = _chain(10)
    w.add_edge(0, 3, "plus3", 3)
    assert defects(w) == []
    assert defect_mass(w) == 0


# --------------------------------------------------------------- accept (2)
def test_single_false_identity_edge_is_exactly_one_defect_class():
    # a wrong belief: |node4| 'same' as |node7| (holonomy 0) on the +1 chain.
    w = _chain(10)
    w.add_edge(4, 7, "same", 0)

    ds = defects(w)
    assert len(ds) == 1                       # exactly one independent class
    # the fundamental cycle 4->5->6->7 has transport +3 against the false 0.
    assert ds[0].residual in (3, -3)
    assert defect_mass(w) == 3

    cb = cycle_basis_defects(w)
    assert len(cb) == 1                       # independent cross-check
    _, h = cb[0]
    assert abs(h) == 3


def test_two_independent_false_edges_are_two_defect_classes():
    w = _chain(10)
    w.add_edge(4, 7, "same", 0)               # cycle 4..7, transport 3
    w.add_edge(1, 5, "same", 0)               # cycle 1..5, transport 4
    ds = defects(w)
    assert len(ds) == 2
    assert sorted(abs(d.residual) for d in ds) == [3, 4]
    assert defect_mass(w) == 7


def test_parallel_contradictory_edges_are_a_defect_bigon():
    # two direct edges 0->1 that disagree: a length-2 defect the simple-graph
    # cycle basis cannot see, but the fundamental-cycle scan does.
    w = Web(IntegerGroup())
    w.add_edge(0, 1, "succ", 1)
    w.add_edge(0, 1, "succ", 2)
    ds = defects(w)
    assert len(ds) == 1
    assert abs(ds[0].residual) == 1


# --------------------------------------------------------------- accept (3)
def _random_web(rng: random.Random) -> Web:
    """A random connected-ish web with random integer edge values."""
    n = rng.randint(3, 12)
    w = Web(IntegerGroup())
    for k in range(n):
        w.add_node(k)
    # spanning path guarantees connectivity, then random extra chords
    for k in range(n - 1):
        w.add_edge(k, k + 1, "e", rng.randint(-9, 9))
    for _ in range(rng.randint(0, n)):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            w.add_edge(u, v, "e", rng.randint(-9, 9))
    return w


def test_relabel_changes_no_holonomy_1000_trials():
    rng = random.Random(0xC0FFEE)
    for _ in range(1000):
        w = _random_web(rng)

        before = {d.edge.eid: d.residual for d in defects(w)}
        mass_before = defect_mass(w)
        # a fixed random loop to check pointwise, too
        loop = [0, 1, 2, 0] if len(w.nodes) >= 3 else [0]
        h_before = holonomy(w, loop)

        phi = {node: rng.randint(-20, 20) for node in w.nodes}
        w.relabel(phi)

        after = {d.edge.eid: d.residual for d in defects(w)}
        assert after == before, "relabel changed a fundamental-cycle holonomy"
        assert defect_mass(w) == mass_before
        assert holonomy(w, loop) == h_before
        assert w.total_cost == 0, "relabel must be free"


def test_relabel_is_a_gauge_transform_potential_defined_edgewise():
    # sanity: relabeling by phi rewrites each edge exactly per the formula.
    w = _chain(5)
    phi = {0: 3, 1: -1, 2: 7, 3: 0, 4: 2}
    a = IntegerGroup()
    expected = [a.relabel_edge(phi[e.u], e.value, phi[e.v]) for e in w.edges()]
    w.relabel(phi)
    assert [e.value for e in w.edges()] == expected
