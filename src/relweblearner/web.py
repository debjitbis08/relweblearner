"""The web: the only thing that ever changes.

Architecture invariant #2: only the web mutates, and only via three moves
with a fixed cost schedule:

* :meth:`Web.relabel` — cost ``0``. A potential ``phi: V -> algebra`` that
  rewrites every edge value ``g(u, v) -> phi(u) . g . phi(v)^dagger``. Pure
  bookkeeping: it changes no loop holonomy (enforced by the P0 property test).
* :meth:`Web.rewire` — cost ``1``. Add/remove/merge edges among *existing*
  nodes. May never contradict an observation (invariant #2).
* :meth:`Web.grow` — cost ``K >> 1``. Add new node(s) and their edges.

Architecture invariant #3: observations are loop-closure and distinctness
assertions only — no coordinates, no node attributes. They are immutable
(invariant, Section 6): no code path here deletes or down-weights one to
reduce defect mass.

Nodes are opaque hashable ids. Each directed edge carries an algebra element;
its converse (opposite direction, ``dagger`` value) is maintained
automatically, so callers only ever add the forward edge.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Hashable, Iterator, Optional

import networkx as nx

from .algebra import Algebra, Element

Node = Hashable


@dataclass
class Edge:
    """A primary directed edge ``u -[value:rel]-> v`` with a stable id.

    ``value`` is mutated only by :meth:`Web.relabel` (a gauge transform); the
    converse edge is derived on the fly as ``dagger(value)`` and never stored
    separately, so the two can never drift apart.
    """

    eid: int
    u: Node
    v: Node
    rel: str
    value: Element


@dataclass(frozen=True)
class Observation:
    """An immutable assertion from the data stream.

    * ``kind == "loop_closes"``: ``data`` is a tuple of nodes forming a closed
      loop whose holonomy is asserted to be the identity.
    * ``kind == "distinct"``: ``data`` is a pair ``(a, b)`` of nodes asserted
      to be different concepts (they may never be merged).
    """

    kind: str
    data: tuple

    def __post_init__(self) -> None:
        if self.kind not in ("loop_closes", "distinct"):
            raise ValueError(f"unknown observation kind: {self.kind!r}")


class ObservationViolation(Exception):
    """Raised when a rewire/grow move would contradict an observation."""


# cost schedule (invariant #2). GROW is a hyperparameter K >> 1 (default here).
COST_RELABEL = 0
COST_REWIRE = 1
DEFAULT_GROW_COST = 10


class Web:
    """A graph with fixed-algebra edge values and the three learning moves."""

    def __init__(self, algebra: Algebra, name: str = "W", grow_cost: int = DEFAULT_GROW_COST):
        self.algebra = algebra
        self.name = name
        self.grow_cost = grow_cost

        self.nodes: set[Node] = set()
        self._edges: list[Edge] = []                      # primary edges only
        self._adj: dict[Node, list[tuple[Edge, bool]]] = defaultdict(list)
        self._alias: dict[Node, Node] = {}                # merged-away -> keeper
        self.observations: list[Observation] = []
        self.growth_log: list[tuple] = []
        self.total_cost: int = 0
        self._next_eid: int = 0

    def resolve(self, x: Node) -> Node:
        """Follow the merge chain to the surviving representative of ``x``."""
        while x in self._alias:
            x = self._alias[x]
        return x

    # ------------------------------------------------------------------ build
    def add_node(self, v: Node, *, grown: bool = False) -> None:
        if v not in self.nodes:
            self.nodes.add(v)
            self._adj.setdefault(v, [])
            if grown:
                self.growth_log.append(("node", v))

    def _install_edge(self, u: Node, v: Node, rel: str, value: Element) -> Edge:
        edge = Edge(self._next_eid, u, v, rel, value)
        self._next_eid += 1
        self._edges.append(edge)
        self._adj[u].append((edge, True))    # traverse forward: value as-is
        self._adj[v].append((edge, False))   # traverse backward: dagger(value)
        return edge

    def add_edge(self, u: Node, v: Node, rel: str, value: Element) -> Edge:
        """Add a forward edge (and its implicit converse). Cost-free build move.

        Use during initial construction / data ingestion. The cost-bearing
        learning moves are :meth:`rewire` and :meth:`grow`.
        """
        self.add_node(u)
        self.add_node(v)
        return self._install_edge(u, v, rel, value)

    # ---------------------------------------------------------- accessors
    def edges(self) -> list[Edge]:
        """The primary (forward) edges. Converses are implicit."""
        return list(self._edges)

    def neighbors(self, u: Node) -> Iterator[tuple[Node, Element, int]]:
        """Yield ``(neighbor, transport_value, eid)`` for every incident edge.

        Includes converse traversals: a stored edge ``u -[g]-> v`` yields
        ``(v, g, eid)`` from ``u`` and ``(u, dagger(g), eid)`` from ``v``.
        """
        for edge, forward in self._adj[u]:
            if forward:
                yield edge.v, edge.value, edge.eid
            else:
                yield edge.u, self.algebra.dagger(edge.value), edge.eid

    def edge_value(self, u: Node, v: Node) -> Optional[Element]:
        """Transport of a *single* direct edge ``u -> v`` (or its converse).

        Returns ``None`` if no direct edge connects them. If several parallel
        edges exist with differing values (itself a defect), the first found is
        returned; callers walking a cycle basis never traverse parallels.
        """
        for w, value, _ in self.neighbors(u):
            if w == v:
                return value
        return None

    def transport(self, path: list[Node]) -> Optional[Element]:
        """Compose edge values along a node sequence; ``None`` if it walks off
        the web or hits an undefined composite (boundary / partial algebra)."""
        values: list[Element] = []
        for u, v in zip(path, path[1:]):
            g = self.edge_value(u, v)
            if g is None:
                return None
            values.append(g)
        return self.algebra.compose_all(values)

    def underlying_graph(self) -> nx.MultiGraph:
        """Undirected multigraph of primary edges (for cycle-basis extraction).

        Edge keys are edge ids so a holonomy walk can recover the value.
        """
        g = nx.MultiGraph()
        g.add_nodes_from(self.nodes)
        for e in self._edges:
            g.add_edge(e.u, e.v, key=e.eid, value=e.value)
        return g

    # ---------------------------------------------------------- observations
    def observe(self, obs: Observation) -> None:
        """Record an immutable observation. Observations are never deleted."""
        self.observations.append(obs)

    def observe_loop_closes(self, loop: list[Node]) -> None:
        self.observe(Observation("loop_closes", tuple(loop)))

    def observe_distinct(self, a: Node, b: Node) -> None:
        self.observe(Observation("distinct", (a, b)))

    def _check_observations(self) -> None:
        """Assert every observation still holds; raise otherwise.

        Called after a rewire/grow to enforce invariant #2 (moves may never
        contradict data). Deferred import avoids a module cycle with holonomy.

        Distinctness is checked exactly (via the merge alias map). Loop-closure
        is checked by node-path holonomy, which is well defined only when the
        loop traverses a simple (parallel-edge-free) region; under parallel or
        merged edges a node path is ambiguous, so this guard is best-effort
        there. Robust loop-closure contradiction detection over the cycle basis
        is built in P1 alongside the growth/rewire search.
        """
        from .holonomy import holonomy

        for obs in self.observations:
            if obs.kind == "loop_closes":
                loop = [self.resolve(x) for x in obs.data]
                h = holonomy(self, loop)
                if h is not None and not self.algebra.is_identity(h):
                    raise ObservationViolation(
                        f"move breaks loop-closure observation {obs.data}: "
                        f"holonomy {h!r} != identity"
                    )
            elif obs.kind == "distinct":
                a, b = obs.data
                if self.resolve(a) == self.resolve(b):
                    raise ObservationViolation(
                        f"move merged nodes asserted distinct: {obs.data}"
                    )

    # ------------------------------------------------------------- move: relabel
    def relabel(self, phi: dict[Node, Element]) -> None:
        """Apply a potential (cost 0). Rewrites values, preserves all holonomy.

        Nodes absent from ``phi`` are treated as carrying the identity.
        """
        ident = self.algebra.identity
        for e in self._edges:
            e.value = self.algebra.relabel_edge(
                phi.get(e.u, ident), e.value, phi.get(e.v, ident)
            )
        self.total_cost += COST_RELABEL

    # -------------------------------------------------------------- move: rewire
    def rewire(
        self,
        *,
        add: Optional[tuple] = None,
        remove: Optional[int] = None,
        merge: Optional[tuple] = None,
    ) -> None:
        """A cost-1 edit among existing nodes. Exactly one of ``add`` /
        ``remove`` / ``merge`` must be given; the result may not contradict any
        observation (rolled back and raised if it does).

        * ``add=(u, v, rel, value)`` — add an edge between existing nodes.
        * ``remove=eid`` — remove the primary edge with that id.
        * ``merge=(a, b)`` — identify node ``b`` into node ``a``.
        """
        given = [x is not None for x in (add, remove, merge)]
        if sum(given) != 1:
            raise ValueError("rewire takes exactly one of add/remove/merge")

        snapshot = self._snapshot()
        try:
            if add is not None:
                u, v, rel, value = add
                if u not in self.nodes or v not in self.nodes:
                    raise ValueError("rewire.add requires existing nodes; use grow")
                self._install_edge(u, v, rel, value)
            elif remove is not None:
                self._remove_edge(remove)
            else:
                self._merge_nodes(*merge)
            self._check_observations()
        except Exception:
            self._restore(snapshot)
            raise
        self.total_cost += COST_REWIRE

    def _remove_edge(self, eid: int) -> None:
        self._edges = [e for e in self._edges if e.eid != eid]
        for node, incident in self._adj.items():
            self._adj[node] = [(e, f) for (e, f) in incident if e.eid != eid]

    def _merge_nodes(self, a: Node, b: Node) -> None:
        """Identify ``b`` into ``a``: rewrite endpoints, drop ``b``."""
        if a not in self.nodes or b not in self.nodes:
            raise ValueError("merge requires two existing nodes")
        for e in self._edges:
            if e.u == b:
                e.u = a
            if e.v == b:
                e.v = a
        self.nodes.discard(b)
        self._alias[b] = a          # b is now identified with a
        # rebuild adjacency from the primary edge list (endpoints changed)
        self._rebuild_adjacency()

    def _rebuild_adjacency(self) -> None:
        self._adj = defaultdict(list)
        for v in self.nodes:
            self._adj[v] = []
        for e in self._edges:
            self._adj[e.u].append((e, True))
            self._adj[e.v].append((e, False))

    # ---------------------------------------------------------------- move: grow
    def grow(self, new_nodes: list[Node], new_edges: list[tuple]) -> None:
        """Add fresh nodes and edges (cost ``K``). Each new edge is
        ``(u, v, rel, value)`` and may reference the new nodes or existing ones.
        The result may not contradict an observation.
        """
        snapshot = self._snapshot()
        try:
            for v in new_nodes:
                self.add_node(v, grown=True)
            for (u, v, rel, value) in new_edges:
                e = self._install_edge(u, v, rel, value)
                self.growth_log.append(("edge", e.u, e.v, e.rel, e.value))
            self._check_observations()
        except Exception:
            self._restore(snapshot)
            raise
        self.total_cost += self.grow_cost

    def fresh_node(self, prefix: str = "g") -> str:
        """A never-before-used node id for growth moves."""
        i = 0
        while f"{prefix}{i}" in self.nodes:
            i += 1
        return f"{prefix}{i}"

    # -------------------------------------------------------- snapshot / restore
    def _snapshot(self) -> tuple:
        return (
            set(self.nodes),
            [Edge(e.eid, e.u, e.v, e.rel, e.value) for e in self._edges],
            self._next_eid,
            list(self.growth_log),
            dict(self._alias),
        )

    def _restore(self, snap: tuple) -> None:
        nodes, edges, next_eid, growth_log, alias = snap
        self.nodes = nodes
        self._edges = edges
        self._next_eid = next_eid
        self.growth_log = growth_log
        self._alias = alias
        self._rebuild_adjacency()
