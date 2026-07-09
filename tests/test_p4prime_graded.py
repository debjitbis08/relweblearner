"""P4′ acceptance — the graded-algebra hypothesis.

A graded algebra (group core for total sectors, inverse-monoid boundary for
partial ones) should inherit ℤ's bloat and the inverse monoid's honesty about
partial inverses, Pareto-dominating the P4 frontier {ℤ, InvMon} on
(bloat, false-inverse) — at the cost of undefined cross-sector composition and
per-sector-only relabel invariance.
"""

from __future__ import annotations

import random

from relweblearner import sweep
from relweblearner.algebra import GradedAlgebra, IntegerGroup, SymmetricInverseMonoid


def test_graded_algebra_obeys_the_frozen_contract():
    A = GradedAlgebra(3)
    e = A.identity
    pool = [e, ("Z", 1), ("Z", -2), A._partial(frozenset({(0, 1)})),
            A._partial(frozenset({(0, 1), (1, 2)})), ("P", frozenset({(0, 2)}))]
    # dagger is an involution; identity is a two-sided unit; norm 0 iff identity
    assert all(A.dagger(A.dagger(x)) == x for x in pool)
    assert all(A.compose(e, x) == x and A.compose(x, e) == x for x in pool)
    assert all((A.norm(x) == 0) == (x == e) for x in pool)

    rng = random.Random(0)
    for _ in range(3000):
        a, b, c = (rng.choice(pool) for _ in range(3))
        ab, bc = A.compose(a, b), A.compose(b, c)
        left = A.compose(ab, c) if ab is not None else None
        right = A.compose(a, bc) if bc is not None else None
        assert left == right                                   # associativity
        if ab is not None:
            assert A.dagger(ab) == A.compose(A.dagger(b), A.dagger(a))   # anti-homomorphism


def test_graded_inherits_bloat_of_Z_and_honesty_of_the_inverse_monoid():
    r = sweep.report(GradedAlgebra(3))
    assert r.bloat == 1.0                     # ℤ's bloat: total sector never bloats
    assert r.false_inverse_rate == 0.0        # InvMon's honesty: no hallucinated inverse
    assert r.undefined_fraction > 0.0         # cross-sector paths refuse (see decomposition)


def test_undefined_is_all_legitimate_refusal_emergent_type_checking():
    # the high undefined fraction is NOT a cost: it decomposes into cross-sector
    # category errors (deserve refusal) + intrinsic partiality, with ZERO
    # illegitimate refusals in the total sector — undefined == q exactly.
    d = sweep.undefined_decomposition(GradedAlgebra(3))
    assert d["within_total"] == 0.0                        # ℤ never refuses a legit compose
    assert d["cross_sector"] > d["within_partial"]        # bulk is emergent type checking
    assert abs((d["cross_sector"] + d["within_partial"]) - d["total"]) < 1e-9
    # and total == the raw undefined_fraction it decomposes
    assert abs(d["total"] - sweep.undefined_fraction(GradedAlgebra(3))) < 1e-9


def test_graded_pareto_dominates_the_old_frontier():
    g = sweep.report(GradedAlgebra(3))
    z = sweep.report(IntegerGroup())
    inv = sweep.report(SymmetricInverseMonoid(3))
    # dominates Z on (bloat, false-inverse)
    assert g.bloat <= z.bloat and g.false_inverse_rate < z.false_inverse_rate
    # dominates InvMon on (bloat, false-inverse)
    assert g.bloat < inv.bloat and g.false_inverse_rate <= inv.false_inverse_rate


def test_graded_relabel_invariance_over_the_sector_preserving_gauge_group():
    # P0 relabel-invariance, AMENDED for a graded carrier: the legal gauge group
    # is the sector-preserving relabelings, and the invariant holds over it. The
    # default diagnostic mixes sectors — not a legal gauge move — so it reports
    # False: a restricted symmetry group, not a violated invariant.
    assert sweep.per_sector_relabel_invariant(GradedAlgebra(3)) is True   # the real invariant
    assert sweep.report(GradedAlgebra(3)).relabel_invariant is False      # mixed = not a gauge
