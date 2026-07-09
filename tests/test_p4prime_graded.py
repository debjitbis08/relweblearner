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
    assert r.undefined_fraction > 0.0         # the price: cross-sector paths don't close


def test_graded_pareto_dominates_the_old_frontier():
    g = sweep.report(GradedAlgebra(3))
    z = sweep.report(IntegerGroup())
    inv = sweep.report(SymmetricInverseMonoid(3))
    # dominates Z on (bloat, false-inverse)
    assert g.bloat <= z.bloat and g.false_inverse_rate < z.false_inverse_rate
    # dominates InvMon on (bloat, false-inverse)
    assert g.bloat < inv.bloat and g.false_inverse_rate <= inv.false_inverse_rate


def test_graded_relabel_invariance_holds_per_sector():
    # the discipline holds the way a graded carrier is deployed (single-sector
    # webs); the default mixed-web diagnostic forfeits it (documented third cost)
    assert sweep.per_sector_relabel_invariant(GradedAlgebra(3)) is True
    assert sweep.report(GradedAlgebra(3)).relabel_invariant is False
