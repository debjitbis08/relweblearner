"""Webs for N-web interference (P5): arithmetic, kinship, and a third domain.

Each web is an internally-consistent chain over the frozen algebra ``Z``:

* **arithmetic** — numbers ``0..n`` with ``succ`` (+1);
* **kinship** — a lineage ``gen0 -> gen1 -> ...`` with ``genshift`` (+1 per
  generation); same-generation ↔ same-count;
* **steps** — a third ``+1`` chain (time-steps), to exercise the N-web (>2) case.

Interface identifications propose that a node in one web *is* a node in another
(``same-count ↔ same-generation``). A poisoned identification points at the
wrong node — its implied offset disagrees with the rest.
"""

from __future__ import annotations

from ..algebra import IntegerGroup
from ..web import Web


def chain_web(name: str, n: int, rel: str, journal=None) -> Web:
    """A ``+1`` chain ``0..n-1`` (nodes prefixed by ``name``)."""
    w = Web(IntegerGroup(), name=name, journal=journal)
    nodes = [f"{name}{i}" for i in range(n)]
    for v in nodes:
        w.add_node(v)
    for i in range(n - 1):
        w.add_edge(nodes[i], nodes[i + 1], rel, 1)
    return w


def arithmetic_web(n: int = 8, journal=None) -> Web:
    return chain_web("a", n, "succ", journal)


def kinship_web(n: int = 12, journal=None) -> Web:
    return chain_web("k", n, "genshift", journal)


def steps_web(n: int = 10, journal=None) -> Web:
    return chain_web("s", n, "step", journal)


def true_identifications(web_a: str, web_b: str, n: int, offset: int = 0) -> list:
    """Correct same-position identifications ``A:i ↔ B:(i+offset)``."""
    return [(f"{web_a}{i}", f"{web_b}{i + offset}") for i in range(n)]


def poison_identification(web_a: str, web_b: str, i: int, wrong_offset: int) -> tuple:
    """A single wrong identification ``A:i ↔ B:(i+wrong_offset)``."""
    return (f"{web_a}{i}", f"{web_b}{i + wrong_offset}")
