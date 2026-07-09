"""P4 acceptance (e4): algebra sweep.

The pre-committed tradeoff axes (Section 6, declared before running):
  * bloat = C/D (weakness -> node bloat),
  * false_inverse_rate (strength -> hallucinated inverses).
The table is the finding; these tests pin its structure. The relabel-invariance
discipline (P0) must hold for every algebra.
"""

from __future__ import annotations

import pytest

from relweblearner.algebra import (
    CyclicGroup,
    FreeInvolutiveMonoid,
    IntegerGroup,
    KleinFour,
    SymmetricInverseMonoid,
)
from relweblearner.sweep import (
    bloat,
    false_inverse_rate,
    relabel_invariant,
    report,
    undefined_fraction,
)

GROUPS = [IntegerGroup(), CyclicGroup(2), CyclicGroup(4), KleinFour(), FreeInvolutiveMonoid(2, 3)]
INV_MONOID = SymmetricInverseMonoid(3)
ALL = GROUPS + [INV_MONOID]


# ------------------------------------------- relabel-invariance discipline
def test_relabel_invariance_holds_for_every_algebra():
    for a in ALL:
        assert relabel_invariant(a), f"relabel changed a defect under {a.name}"


# ------------------------------------------------------------- bloat axis
def test_integer_group_has_no_bloat_and_finite_algebras_do():
    _, bl_Z = bloat(IntegerGroup())
    assert bl_Z == 1.0                              # Z represents every concept
    for a in [CyclicGroup(2), CyclicGroup(4), KleinFour(), SymmetricInverseMonoid(3)]:
        _, bl = bloat(a)
        assert bl > 1.0                             # finite/partial -> witness bloat


def test_bloat_decreases_with_more_expressive_group():
    _, b2 = bloat(CyclicGroup(2))
    _, b4 = bloat(CyclicGroup(4))
    assert b2 > b4 > 1.0                            # Z_2 bloats more than Z_4


# --------------------------------------------------- false-inverse axis
def test_groups_hallucinate_inverses_inverse_monoid_does_not():
    for a in GROUPS:
        assert false_inverse_rate(a) == 1.0         # g.g^dagger = identity always
    assert false_inverse_rate(INV_MONOID) == 0.0    # partial -> honest pseudo-inverse


# ------------------------------------------------- partial composition
def test_partial_algebra_has_undefined_composites():
    assert undefined_fraction(SymmetricInverseMonoid(3)) > 0.0
    assert undefined_fraction(IntegerGroup()) == 0.0
    # composition is genuinely partial: returns None
    inv = SymmetricInverseMonoid(3)
    g = inv.generator()                              # 0->1->2
    assert inv.compose(g, g) is not None             # 0->2 still defined
    assert inv.compose(inv.compose(g, g), g) is None  # 0->3 undefined


# --------------------------------------------------------- the frontier
def test_pareto_frontier_is_the_finding():
    reps = {a.name: report(a) for a in ALL}
    pts = {n: (r.bloat, r.false_inverse_rate) for n, r in reps.items()}

    def dominated(p, others):
        # p is dominated if some q is <= on both axes and < on one
        return any(
            q[0] <= p[0] and q[1] <= p[1] and (q[0] < p[0] or q[1] < p[1])
            for q in others
        )

    others = list(pts.values())
    # Z (1.0, 1.0) and the inverse monoid (bloaty, 0.0) are non-dominated
    assert not dominated(pts["Z"], [v for k, v in pts.items() if k != "Z"])
    assert not dominated(pts["InvMon_3"], [v for k, v in pts.items() if k != "InvMon_3"])
    # a weak group that both bloats and hallucinates is dominated by Z
    assert dominated(pts["Z2xZ2"], [v for k, v in pts.items() if k != "Z2xZ2"])
