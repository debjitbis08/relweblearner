"""Synthetic arithmetic webs — **unit-test scaffold for the growth engine**.

Per the dev-doc, ``arithmetic.py`` exists ONLY to exercise P1's growth engine
with a clean, labeled successor chain; it is superseded as a *data source* by
the number classes constructed from bare pairing episodes in P1b. Numbers here
are node ids for convenience of testing — not a claim that the learner is given
numbers.
"""

from __future__ import annotations

from ..algebra import IntegerGroup
from ..holonomy import potential
from ..web import Web


def build_chain(n: int, journal=None) -> Web:
    """The naturals ``0..n-1`` with successor (+1) edges. A defect-free tree."""
    w = Web(IntegerGroup(), name="arith", journal=journal)
    for k in range(n):
        w.add_node(k)
    for k in range(n - 1):
        w.add_edge(k, k + 1, "succ", 1)
    return w


def subtraction_probes(pairs: list[tuple[int, int]]) -> list[tuple[int, str, int]]:
    """Turn ``a - b`` requests into query walks ``walk(a, 'succ~', b)``.

    Walking the converse of successor ``b`` times from ``a`` computes ``a - b``;
    it falls off the bottom boundary exactly when ``b > a`` (given a ``0..``
    chain), which is the growth trigger.
    """
    return [(a, "succ~", b) for (a, b) in pairs]


def coordinates(web: Web) -> dict:
    """Ground-truth integer coordinate per node (SCORING ONLY).

    Equals the holonomy potential normalized so node ``0`` maps to ``0``. After
    growth, invented predecessor nodes receive their exact negative coordinates
    — the check that arithmetic through grown nodes is correct by construction.
    """
    phi = potential(web)
    base = phi.get(0, 0)
    return {node: phi[node] - base for node in web.nodes}
