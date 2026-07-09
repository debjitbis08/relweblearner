"""P2' acceptance: unlabeled-relation type discovery.

Accepts iff a mixed unlabeled web (one chain + >=2 attribute partitions)
recovers ground-truth types at purity 1.0 under generic coverage, and the
conflation-vs-coverage curve behaves as predicted (conflation falls as crossing
observations increase). The sparse-coverage conflation is a logged failure mode,
not a bug.
"""

from __future__ import annotations

from relweblearner.datasets.bare import build_bare_web
from relweblearner.types import (
    discover_types,
    is_conflated,
    n_attribute_types,
    naive_degree_typing,
    overall_purity,
)


def _frac_conflated(n_crossing, seeds=40):
    c = 0
    for s in range(seeds):
        edges, truth = build_bare_web(3, 2, n_crossing=n_crossing, seed=s)
        c += is_conflated(discover_types(edges), truth)
    return c / seeds


# ------------------------------------------------------- generic coverage
def test_generic_coverage_recovers_types_at_purity_1():
    edges, truth = build_bare_web(colors=3, plants=2, full=True)
    disc = discover_types(edges)
    assert overall_purity(disc, truth) == 1.0
    assert not is_conflated(disc, truth)
    # one chain type + exactly two attribute types (colors, plants)
    assert n_attribute_types(disc) == 2


def test_naive_refinement_over_refines():
    # the WL/degree-pair baseline splits 3 true types into more classes.
    edges, _ = build_bare_web(colors=3, plants=2, full=True)
    assert len(naive_degree_typing(edges)) > 3


# ------------------------------------------------------- sparse failure mode
def test_sparse_coverage_conflates():
    # no crossing observations: a color hub and a plant hub are accidentally
    # disjoint and get merged into one type.
    edges, truth = build_bare_web(3, 2, n_crossing=0, seed=0)
    disc = discover_types(edges)
    assert is_conflated(disc, truth)
    assert n_attribute_types(disc) == 1        # colors + plants welded into one
    assert overall_purity(disc, truth) < 1.0


# ------------------------------------------------------- coverage curve
def test_conflation_falls_as_crossing_observations_increase():
    low = _frac_conflated(0)
    high = _frac_conflated(20)
    assert low >= 0.9                          # sparse -> almost always conflates
    assert high <= 0.3                         # well-covered -> rarely conflates
    assert high < low
    # monotone-ish: the trend decreases across the sweep
    fracs = [_frac_conflated(nc) for nc in (0, 4, 8, 16)]
    assert all(b <= a + 0.1 for a, b in zip(fracs, fracs[1:]))
