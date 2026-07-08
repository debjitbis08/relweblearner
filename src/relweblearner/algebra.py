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
        """
        return self.compose(self.compose(phi_u, value), self.dagger(phi_v))


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
