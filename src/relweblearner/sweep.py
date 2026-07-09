"""Algebra sweep diagnostics (P4).

Fixed machinery, swept algebra. The **pre-committed** tradeoff axes (declared
before running, per Section 6 — do not tune post hoc):

* ``bloat = C / D`` — *weakness*. For a length-``C`` successor chain, ``D`` is
  the number of distinct transport signatures the algebra assigns. A too-weak
  algebra gives ``D < C``, so the web must add witness nodes to keep concepts
  distinct: ``bloat > 1``.
* ``false_inverse_rate`` — *strength*. Fraction of a partial relation's edges
  for which the algebra certifies ``g . g^dagger == identity`` (a hallucinated
  total inverse). A group scores 1.0; an inverse monoid, 0.0.

Neither is minimized alone; the ``(bloat, false_inverse)`` frontier is the
finding. ``undefined_fraction`` (partial algebras) and ``relabel_invariant``
(the P0 correctness discipline, extended to each algebra) are reported too.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .algebra import Algebra
from .web import Web


@dataclass
class AlgebraReport:
    name: str
    distinct: int           # D: distinct transport signatures over the chain
    bloat: float            # C / D
    false_inverse_rate: float
    undefined_fraction: float
    relabel_invariant: bool


def _key(x):
    return x                # algebra elements are already hashable


def bloat(algebra: Algebra, C: int = 12) -> tuple[int, float]:
    """(distinct signatures D, bloat = C/D) over a length-C successor chain."""
    g = algebra.generator()
    acc = algebra.identity
    seen = set()
    for _ in range(C):
        seen.add(_key(acc))
        acc = algebra.compose(acc, g)
        if acc is None:      # generator exhausted (truncation / partiality)
            break
    D = len(seen)
    return D, C / D


def false_inverse_rate(algebra: Algebra) -> float:
    """Fraction of partial-relation edges the algebra wrongly certifies as
    invertible (``g . g^dagger == identity``)."""
    probes = algebra.partial_elements()
    if not probes:
        return 1.0
    hallucinated = sum(
        1 for x in probes if algebra.compose(x, algebra.dagger(x)) == algebra.identity
    )
    return hallucinated / len(probes)


def undefined_fraction(algebra: Algebra, trials: int = 400, seed: int = 0) -> float:
    """Fraction of random 3-step composites that are undefined (``None``).

    Section 6: log the fraction of undefined loops as its own signal.
    """
    rng = random.Random(seed)
    pool = _element_pool(algebra)
    if len(pool) < 2:
        return 0.0
    undef = 0
    for _ in range(trials):
        acc = algebra.identity
        for _ in range(3):
            acc = algebra.compose(acc, rng.choice(pool))
            if acc is None:
                undef += 1
                break
    return undef / trials


def relabel_invariant(algebra: Algebra, trials: int = 200, seed: int = 0) -> bool:
    """Extend the P0 relabel-invariance discipline to this algebra.

    Relabeling by *units* (invertible elements) must not change which loops are
    defects. Abelian group algebras additionally preserve exact residuals; here
    we check the robust, universal invariant: defect *status* is unchanged.
    """
    from .holonomy import defects

    units = getattr(algebra, "units", lambda: [algebra.identity])()
    pool = _element_pool(algebra)
    if not units or len(pool) < 2:
        return True
    rng = random.Random(seed)
    for _ in range(trials):
        w = _random_web(algebra, pool, rng)
        before = {d.edge.eid for d in defects(w)}
        phi = {n: rng.choice(units) for n in w.nodes}
        w.relabel(phi)
        after = {d.edge.eid for d in defects(w)}
        if before != after:
            return False
    return True


def report(algebra: Algebra, C: int = 12) -> AlgebraReport:
    D, bl = bloat(algebra, C)
    return AlgebraReport(
        name=algebra.name,
        distinct=D,
        bloat=bl,
        false_inverse_rate=false_inverse_rate(algebra),
        undefined_fraction=undefined_fraction(algebra),
        relabel_invariant=relabel_invariant(algebra),
    )


# ------------------------------------------------------------------ helpers
def _element_pool(algebra: Algebra) -> list:
    """A small pool of algebra elements to build random webs / composites."""
    g = algebra.generator()
    pool = [algebra.identity, g, algebra.dagger(g)]
    pool += algebra.partial_elements()
    # dedup preserving hashability
    seen, out = set(), []
    for x in pool:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _random_web(algebra: Algebra, pool: list, rng: random.Random) -> Web:
    n = rng.randint(3, 7)
    w = Web(algebra)
    for k in range(n):
        w.add_node(k)
    for k in range(n - 1):
        w.add_edge(k, k + 1, "e", rng.choice(pool))
    for _ in range(rng.randint(0, n)):
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v:
            w.add_edge(u, v, "e", rng.choice(pool))
    return w
