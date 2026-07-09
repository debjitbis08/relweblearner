"""Frozen algebras of edge values.

Architecture invariant #1: the algebra is FROZEN. This module defines
composition, identity, dagger (converse/involution) and a norm for every
carrier. No learned parameters live here or on edges — ever. Learning only
mutates the *web* (see :mod:`relweblearner.web`); it never touches an algebra.

The first (and, for phases P0–P3, only) carrier is the integers under
addition, ``IntegerGroup``. Later phases (P4) swap in finite involutive
monoids behind the exact same :class:`Algebra` interface; nothing downstream
should need to change.

Contract obeyed by every ``Algebra``:

* ``compose`` is associative with ``identity`` as a two-sided unit.
* ``dagger`` is an involution (``dagger(dagger(a)) == a``) and an
  anti-homomorphism (``dagger(compose(a, b)) == compose(dagger(b),
  dagger(a))``). For a group, ``dagger`` is the inverse.
* ``norm(a) >= 0`` with ``norm(a) == 0`` iff ``a`` is the identity. This is
  the defect magnitude that the learning signal integrates.
* Composition may be **partial**: an undefined composite is returned as
  ``None`` (needed by the inverse-monoid carriers in P4). Total algebras such
  as ``IntegerGroup`` never return ``None``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Hashable, Iterable, Optional

Element = Hashable


class Algebra(ABC):
    """Abstract frozen algebra: identity, composition, dagger, norm."""

    #: human-readable carrier name, used in results tables (e.g. "Z", "Z_4").
    name: str = "?"

    @property
    @abstractmethod
    def identity(self) -> Element:
        """The two-sided unit of :meth:`compose`."""

    @abstractmethod
    def compose(self, a: Element, b: Element) -> Optional[Element]:
        """Compose two elements. ``None`` marks an undefined (partial) result.

        ``None`` propagates: composing anything with ``None`` yields ``None``.
        """

    @abstractmethod
    def dagger(self, a: Element) -> Element:
        """The converse/involution of ``a`` (inverse, for a group)."""

    @abstractmethod
    def norm(self, a: Element) -> float:
        """Defect magnitude of ``a``: ``0`` iff ``a`` is the identity."""

    # ---- provided helpers (defined once, in terms of the primitives) ----

    def is_identity(self, a: Optional[Element]) -> bool:
        """True iff ``a`` is a defined element equal to the identity."""
        return a is not None and self.norm(a) == 0

    def compose_all(self, elements: Iterable[Element]) -> Optional[Element]:
        """Left-fold :meth:`compose` over ``elements``; ``None`` if undefined.

        Returns the transport of a path given its ordered edge values.
        """
        acc: Optional[Element] = self.identity
        for e in elements:
            if acc is None or e is None:
                return None
            acc = self.compose(acc, e)
        return acc

    def relabel_edge(
        self, phi_u: Element, value: Element, phi_v: Element
    ) -> Optional[Element]:
        """Gauge-transform one edge value under a potential.

        For an edge ``u -[value]-> v`` and a potential ``phi`` this returns
        ``phi(u) . value . phi(v)^dagger`` — the relabeled value. Relabeling
        (a "potential" / change of bookkeeping) provably changes no loop
        holonomy; that discipline is enforced by the P0 property test.

        Returns ``None`` if any composite is undefined (partial algebras).
        """
        inner = self.compose(phi_u, value)
        if inner is None:
            return None
        return self.compose(inner, self.dagger(phi_v))


class IntegerGroup(Algebra):
    """The integers under addition: ``(Z, +, 0)`` with ``dagger = negation``.

    This is the arithmetic-transport carrier. ``+k`` means "successor, k
    times"; its converse is ``-k``. Composition is total, so ``compose`` never
    returns ``None``.
    """

    name = "Z"

    @property
    def identity(self) -> int:
        return 0

    def compose(self, a: int, b: int) -> int:
        return a + b

    def dagger(self, a: int) -> int:
        return -a

    def norm(self, a: int) -> float:
        return abs(a)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "IntegerGroup(Z, +)"

    # ---- P4 diagnostic fixtures (see relweblearner.sweep) ----
    def generator(self) -> int:
        """A distinguished non-identity element (the "+1" successor step)."""
        return 1

    def partial_elements(self) -> list:
        """Representative edge values for modelling a partial relation.

        A group has no non-invertible elements, so ``g . g^dagger`` is always the
        identity — the algebra *hallucinates* a total inverse for any partial
        relation. Returning a representative generator surfaces exactly that.
        """
        return [1]


# ===================================================================== finite
# Finite involutive monoids behind the same interface (P4). The machinery
# (web, holonomy, growth, ...) is unchanged; only the algebra is swapped.


class CyclicGroup(Algebra):
    """The cyclic group ``Z_m`` under addition mod m. dagger = negation mod m."""

    def __init__(self, m: int):
        self.m = m
        self.name = f"Z_{m}"

    @property
    def identity(self) -> int:
        return 0

    def compose(self, a: int, b: int) -> int:
        return (a + b) % self.m

    def dagger(self, a: int) -> int:
        return (-a) % self.m

    def norm(self, a: int) -> float:
        return min(a % self.m, (-a) % self.m)      # Cayley distance to identity

    def generator(self) -> int:
        return 1 % self.m

    def partial_elements(self) -> list:
        return [1 % self.m]

    def units(self) -> list:
        return list(range(self.m))                  # every element is invertible


class KleinFour(Algebra):
    """``Z_2 x Z_2`` as ``({0,1,2,3}, XOR)``: every element is self-inverse."""

    name = "Z2xZ2"

    @property
    def identity(self) -> int:
        return 0

    def compose(self, a: int, b: int) -> int:
        return a ^ b

    def dagger(self, a: int) -> int:
        return a                                    # self-inverse

    def norm(self, a: int) -> float:
        return 0 if a == 0 else 1

    def generator(self) -> int:
        return 1

    def partial_elements(self) -> list:
        return [1]

    def units(self) -> list:
        return [0, 1, 2, 3]


class SymmetricInverseMonoid(Algebra):
    """Partial bijections on ``{0..n-1}`` (the symmetric inverse monoid I_n).

    An element is a ``frozenset`` of ``(a, b)`` pairs — a partial injection.
    Composition is left-to-right (``x`` then ``y``); an empty composite is
    **undefined** and returned as ``None`` (partial composition, Section 6).
    dagger inverts the partial map. Unlike a group, ``x . x^dagger`` is the
    identity only on ``x``'s domain (an idempotent) — so partial relations get
    honest pseudo-inverses, not hallucinated total ones.
    """

    def __init__(self, n: int):
        self.n = n
        self.name = f"InvMon_{n}"

    @property
    def identity(self):
        return frozenset((i, i) for i in range(self.n))

    def compose(self, a, b):
        if a is None or b is None:
            return None
        bmap = dict(b)
        out = frozenset((x, bmap[y]) for (x, y) in a if y in bmap)
        return out if out else None                 # empty composite -> undefined

    def dagger(self, a):
        return frozenset((y, x) for (x, y) in a)

    def norm(self, a) -> float:
        if a is None:
            return 1.0
        return self.n - sum(1 for (x, y) in a if x == y)   # points not fixed

    def is_identity(self, a) -> bool:
        return a is not None and a == self.identity

    def generator(self):
        """A partial shift ``0->1->...->(n-2)``; ``n-1`` has no image."""
        return frozenset((i, i + 1) for i in range(self.n - 1))

    def partial_elements(self) -> list:
        # genuinely partial maps (domain smaller than the full set)
        return [
            frozenset({(0, 1)}),                    # single partial link
            frozenset((i, i + 1) for i in range(self.n - 1)),
        ]

    def units(self) -> list:
        """The units of I_n are the full permutations of ``{0..n-1}``."""
        from itertools import permutations

        return [frozenset(zip(range(self.n), p)) for p in permutations(range(self.n))]


class GradedAlgebra(Algebra):
    """A **graded** algebra: a group core for TOTAL sectors, an inverse-monoid
    boundary for PARTIAL sectors — one carrier, two composition laws chosen per
    sector (P4′, from the frontier finding).

    The P4 sweep found the frontier is a genuine dichotomy: totality (ℤ, groups)
    is exactly what hallucinates inverses on partial relations, and partiality
    (the inverse monoid) is exactly what refuses to compose. This algebra tests
    the hypothesis that grading resolves it: use the ℤ law where the relation is
    total (number, order) and the inverse-monoid law where it is partial
    (capital-of, has-colour).

    Elements are sector-tagged: the shared identity ``("e",)``; total-sector
    ``("Z", k)`` (integers under +, dagger = negation); partial-sector
    ``("P", frozenset[(a, b)])`` (partial bijections on ``{0..n-1}``, dagger =
    inverse). Composition **within** a sector uses that sector's law; **across**
    sectors it is undefined (``None``) — you cannot compose a successor-step with
    an attribute edge. So it inherits ℤ's bloat 1.0 on the total sector and the
    inverse monoid's false-inverse 0.0 on the partial one, paying with a high
    ``undefined_fraction`` (the price of grading: cross-sector paths don't close).
    """

    _E = ("e",)   # the shared, glued identity of both sectors

    def __init__(self, n: int = 3):
        self.n = n
        self.name = f"Graded(Z|Inv_{n})"

    @property
    def identity(self):
        return self._E

    # ---- normalizers that glue each sector's own identity to the shared one
    def _total(self, k: int):
        return self._E if k == 0 else ("Z", k)

    def _partial(self, pairs):
        fs = frozenset(pairs)
        return self._E if fs == frozenset((i, i) for i in range(self.n)) else ("P", fs)

    def compose(self, a, b):
        if a is None or b is None:
            return None
        if a == self._E:
            return b
        if b == self._E:
            return a
        if a[0] == "Z" and b[0] == "Z":
            return self._total(a[1] + b[1])
        if a[0] == "P" and b[0] == "P":
            bmap = dict(b[1])
            out = frozenset((x, bmap[y]) for (x, y) in a[1] if y in bmap)
            return self._partial(out) if out else None   # empty composite undefined
        return None                                       # cross-sector: undefined

    def dagger(self, a):
        if a == self._E:
            return self._E
        if a[0] == "Z":
            return self._total(-a[1])
        return self._partial(frozenset((y, x) for (x, y) in a[1]))

    def norm(self, a) -> float:
        if a is None:
            return 1.0
        if a == self._E:
            return 0.0
        if a[0] == "Z":
            return abs(a[1])
        return self.n - sum(1 for (x, y) in a[1] if x == y)   # partial: unfixed points

    def _sector(self, x):
        return None if x == self._E else x[0]

    def relabel_edge(self, phi_u, value, phi_v):
        """A **graded** gauge acts sector-wise: each edge is relabeled only by the
        same-sector component of its endpoints' potentials (a cross-sector unit
        acts as the identity there). Same-sector loops get a proper gauge;
        cross-sector loops have undefined (non-defect) transport either way — so
        relabel-invariance (the P0 discipline) still holds for the graded carrier.
        """
        s = self._sector(value)
        if s is None:                                  # identity edge
            su, sv = self._sector(phi_u), self._sector(phi_v)
            if su is not None and sv is not None and su != sv:
                return self._E                         # cross-sector: leave identity
            s = su if su is not None else sv
            if s is None:
                return self._E
        pu = phi_u if self._sector(phi_u) in (None, s) else self._E
        pv = phi_v if self._sector(phi_v) in (None, s) else self._E
        return self.compose(self.compose(pu, value), self.dagger(pv))

    # ---- P4 diagnostic fixtures
    def generator(self):
        """The total-sector successor step — so bloat is measured on ℤ (→ 1.0)."""
        return ("Z", 1)

    def partial_elements(self) -> list:
        """Genuinely partial maps in the P sector — ``g . g† ≠ identity`` (→ 0.0)."""
        return [
            ("P", frozenset({(0, 1)})),
            ("P", frozenset((i, i + 1) for i in range(self.n - 1))),
        ]

    def units(self) -> list:
        """Units: total steps (all invertible) + full permutations of the P sector."""
        from itertools import permutations

        tot = [self._total(k) for k in range(-2, 3)]
        perms = [self._partial(frozenset(zip(range(self.n), p)))
                 for p in permutations(range(self.n))]
        out, seen = [], set()
        for u in [self._E, *tot, *perms]:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def sectors(self) -> list:
        """``[(name, element_pool, units), ...]`` — one entry per graded sector.

        A graded algebra is *used* with each relation in a single sector (a web's
        edges for one relation are all total, or all partial). This exposes the
        per-sector pools so relabel-invariance can be checked the way the carrier
        is physically deployed — unlike the default diagnostic, which mixes
        sectors on one web and so forfeits strict edge-id invariance (grading's
        third cost: identity edges bridge sectors, and relabel relocates them).
        """
        z_pool = [self._E, ("Z", 1), ("Z", -1), ("Z", 2)]
        z_units = [self._total(k) for k in range(-2, 3)]
        p_pool = [self._E, *self.partial_elements()]
        p_units = [u for u in self.units() if u == self._E or u[0] == "P"]
        return [("Z", z_pool, z_units), ("P", p_pool, p_units)]


class FreeInvolutiveMonoid(Algebra):
    """Free involutive monoid on ``k`` generators, truncated at word length ``L``.

    Elements are reduced tuples of tokens ``(gen_index, is_dagger)``; adjacent
    inverse pairs cancel. A composite longer than ``L`` is **undefined**
    (``None``) — the truncation. The control ("maximally expressive"): it can
    tell many concepts apart (low bloat) but, being group-like on its
    generators (``g . g^dagger`` reduces to the identity), it hallucinates
    inverses like a group.
    """

    def __init__(self, k: int = 2, L: int = 3):
        self.k = k
        self.L = L
        self.name = f"Free_L{L}"

    @property
    def identity(self):
        return ()

    def _reduce(self, word):
        out = []
        for tok in word:
            if out and out[-1][0] == tok[0] and out[-1][1] != tok[1]:
                out.pop()                           # g g^dagger -> identity
            else:
                out.append(tok)
        return tuple(out)

    def compose(self, a, b):
        if a is None or b is None:
            return None
        w = self._reduce(tuple(a) + tuple(b))
        return None if len(w) > self.L else w       # truncation -> undefined

    def dagger(self, a):
        return tuple((i, not d) for (i, d) in reversed(a))

    def norm(self, a) -> float:
        return 1.0 if a is None else len(a)

    def generator(self):
        return ((0, False),)

    def partial_elements(self) -> list:
        return [((0, False),)]

    def units(self) -> list:
        return [()]                                 # only the identity is a unit
