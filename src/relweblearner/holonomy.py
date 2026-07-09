"""Holonomy: gauge-fix a potential, read off the defects.

The learning signal (architecture invariant #4) is defect persistence, and a
defect is a loop whose holonomy is not the identity. This module turns a web
into that signal:

* :func:`potential` — assign ``phi: V -> algebra`` by BFS per connected
  component (a spanning-forest gauge fix).
* :func:`defects` — the residual mismatch on every non-tree edge. Because each
  non-tree edge closes exactly one fundamental cycle, its residual *is* that
  cycle's holonomy; the nonzero ones are the independent defect classes.
* :func:`holonomy` — transport around an arbitrary loop.
* :func:`defect_mass` — the scalar objective: total ``norm`` of holonomy over
  a set of loops (default: the fundamental cycle basis).
* :func:`cycle_basis_defects` — the same signal read from a networkx cycle
  basis, for cross-checking and reporting.

Key fact this module leans on: relabeling (a change of ``phi``) provably
changes no holonomy, so every quantity here is gauge-invariant. That is the
correctness discipline for the whole codebase (Section 6) and is pinned by the
P0 property test.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

import networkx as nx

from .algebra import Element
from .web import Edge, Web


@dataclass(frozen=True)
class Defect:
    """A non-tree edge whose fundamental-cycle holonomy is not the identity."""

    edge: Edge
    residual: Element

    @property
    def magnitude(self) -> float:  # convenience for sorting / reporting
        return abs(self.residual) if isinstance(self.residual, (int, float)) else 1.0


def potential(web: Web) -> dict:
    """BFS spanning-forest potential: ``phi(root) = identity`` per component,
    ``phi(v) = phi(u) . g`` along each tree edge ``u -[g]-> v``.

    Node visitation is deterministic (sorted by ``repr``) so results are
    reproducible across runs.
    """
    algebra = web.algebra
    phi: dict = {}
    for root in sorted(web.nodes, key=repr):
        if root in phi:
            continue
        phi[root] = algebra.identity
        dq = deque([root])
        while dq:
            u = dq.popleft()
            for v, value, _eid in web.neighbors(u):
                if v not in phi:
                    p = algebra.compose(phi[u], value)
                    if p is None:            # undefined transport (partial algebra)
                        continue             # reach v by another defined path, or leave it
                    phi[v] = p
                    dq.append(v)
    return phi


def defects(web: Web, phi: Optional[dict] = None) -> list[Defect]:
    """Independent defect classes: non-tree edges with nonzero residual.

    For each primary edge ``u -[g]-> v`` the residual is
    ``phi(u) . g . phi(v)^dagger`` — the holonomy of the fundamental cycle that
    edge closes against the spanning tree. Tree edges give the identity (and
    are dropped); the survivors are a cycle basis of the *defective* loops, one
    per independent obstruction.
    """
    algebra = web.algebra
    if phi is None:
        phi = potential(web)
    out: list[Defect] = []
    for e in web.edges():
        if e.u not in phi or e.v not in phi:
            continue                         # endpoint unreachable by a defined path
        residual = algebra.relabel_edge(phi[e.u], e.value, phi[e.v])
        if residual is None:
            continue                         # undefined loop (Section 6): not a defect
        if not algebra.is_identity(residual):
            out.append(Defect(edge=e, residual=residual))
    return out


def holonomy(web: Web, loop: list) -> Optional[Element]:
    """Transport around a loop given as an ordered node sequence.

    If the loop is given open (last != first) the closing edge is appended.
    Returns ``None`` if any step is missing an edge or the composite is
    undefined (partial algebra).
    """
    if not loop:
        return web.algebra.identity
    closed = loop if loop[0] == loop[-1] else list(loop) + [loop[0]]
    return web.transport(closed)


def defect_mass(web: Web, loops: Optional[list[list]] = None) -> float:
    """Scalar objective (invariant #4): total ``norm`` of holonomy.

    Over the fundamental cycle basis by default; over an explicit list of
    observed ``loops`` when given (undefined composites contribute nothing).
    """
    algebra = web.algebra
    if loops is None:
        return sum(algebra.norm(d.residual) for d in defects(web))
    total = 0.0
    for loop in loops:
        h = holonomy(web, loop)
        if h is not None:
            total += algebra.norm(h)
    return total


def cycle_basis_defects(web: Web) -> list[tuple[list, Element]]:
    """Defects read from a networkx cycle basis (simple-graph view).

    Returns ``(ordered_cycle, holonomy)`` for each basis cycle whose holonomy
    is not the identity. This is an independent cross-check of :func:`defects`
    that also yields human-readable minimal loops; parallel edges (bigons) are
    invisible to the simple-graph basis, so :func:`defects` remains the
    authoritative count.
    """
    simple = nx.Graph()
    simple.add_nodes_from(web.nodes)
    for e in web.edges():
        simple.add_edge(e.u, e.v)
    out: list[tuple[list, Element]] = []
    for cycle in nx.cycle_basis(simple):
        h = holonomy(web, cycle)
        if h is not None and not web.algebra.is_identity(h):
            out.append((cycle, h))
    return out
