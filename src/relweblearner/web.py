"""The web: a projection of an append-only log of commitments.

Architecture invariants realized here:

* **#2 Only the web mutates**, via three costed moves — ``relabel`` (0),
  ``rewire`` (1), ``grow`` (K). ``relabel`` is a gauge transform (bookkeeping);
  the structural moves are recorded as **commitments**.
* **#4 No silent operations.** Every act funnels through :meth:`_trace`, which
  emits a bare episode onto the shared :class:`~relweblearner.journal.Journal`.
  Emission is the single seam that a future attention policy will gate
  (``docs/scaling.md`` §6).
* **#5 Belief is a projection.** The live graph (nodes/edges/alias) is rebuilt
  by replaying the commitment list; every commitment carries the episode ids
  that justify it (provenance). Retraction = exclude a commitment (or its
  justifying episodes) and re-derive — never mutate-in-place-irreversibly.
* **#8 Simulate before committing.** :meth:`fork` returns a cheap copy sharing
  the journal but with an independent commitment list and ``cf``-flagged
  emission, so simulated moves never touch the real projection.

"Bare web is the standard": the low-level ``add_edge`` / ``observe_*`` /
algebra-valued API here is the *pre-derivation* substrate. In P1b the labeled,
valued web is itself derived from bare pairing episodes (MATCH → merge,
ONEMORE → ``+1`` edge, self-loop → holonomy defect); these direct constructors
remain for unit tests and dataset scaffolding.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterator, Optional

import networkx as nx

from .algebra import Algebra, Element
from .journal import EpisodeId, Journal

Node = Hashable

# cost schedule (invariant #2). GROW is a hyperparameter K >> 1.
COST_RELABEL = 0
COST_REWIRE = 1
DEFAULT_GROW_COST = 10


@dataclass
class Edge:
    """A primary directed edge ``u -[value:rel]-> v``.

    ``eid`` equals the id of the commitment that created it, so edge identity is
    stable across rebuilds. ``value`` is mutated only by :meth:`Web.relabel`
    (a gauge transform); the converse edge is derived on the fly.
    """

    eid: int
    u: Node
    v: Node
    rel: str
    value: Element


@dataclass(frozen=True)
class WalkResult:
    """The outcome of a query walk (:meth:`Web.walk`).

    ``off_web`` is True iff the walk fell off a boundary before completing;
    ``remaining`` is then the deficit — how many steps could not be taken. This
    deficit is the obstruction the growth engine discharges (P1).
    """

    start: Node
    rel: str
    k: int
    endpoint: Node
    taken: int
    remaining: int
    off_web: bool


@dataclass(frozen=True)
class Commit:
    """One structural move in the append-only commitment log (invariant #5)."""

    cid: int
    kind: str                       # 'node' | 'edge' | 'remove' | 'merge'
    payload: tuple
    move: str                       # 'init' | 'rewire' | 'grow' (cost class)
    provenance: tuple = ()          # EpisodeIds justifying this commit
    target: Optional[int] = None    # for 'remove': the edge cid it tombstones


@dataclass(frozen=True)
class Observation:
    """An immutable loop-closure or distinctness assertion (invariant #3).

    Pre-derivation constraint form; P1b derives these from bare episodes.
    """

    kind: str
    data: tuple

    def __post_init__(self) -> None:
        if self.kind not in ("loop_closes", "distinct"):
            raise ValueError(f"unknown observation kind: {self.kind!r}")


class ObservationViolation(Exception):
    """Raised when a rewire/grow move would contradict an observation."""


class Web:
    """A graph with fixed-algebra edge values, projected from a commit log."""

    #: public methods that are "acts" and MUST emit a trace (invariant #4 CI).
    ACT_METHODS = ("add_node", "add_edge", "relabel", "rewire", "grow", "walk")

    def __init__(
        self,
        algebra: Algebra,
        name: str = "W",
        grow_cost: int = DEFAULT_GROW_COST,
        journal: Optional[Journal] = None,
        cf: bool = False,
    ):
        self.algebra = algebra
        self.name = name
        self.grow_cost = grow_cost
        self.journal = journal if journal is not None else Journal(name)
        self._cf = cf                       # fork/simulate mode (invariant #8)

        # the log (belief source, invariant #5)
        self._commits: list[Commit] = []
        self._excluded_commits: set[int] = set()
        self._next_cid = 0

        # the live projection (rebuildable from the log)
        self.nodes: set[Node] = set()
        self._edges: list[Edge] = []
        self._adj: dict[Node, list[tuple[Edge, bool]]] = defaultdict(list)
        self._alias: dict[Node, Node] = {}

        self.observations: list[Observation] = []
        self.growth_log: list[tuple] = []
        self.total_cost = 0

    # ================================================================ tracing
    def _trace(self, members1, members2, pairing=(), *, tag: str) -> EpisodeId:
        """The single emission seam (invariant #4). cf-flagged inside a fork."""
        return self.journal.emit(members1, members2, pairing, cf=self._cf, tag=tag)

    # ============================================================= projection
    def _new_cid(self) -> int:
        cid = self._next_cid
        self._next_cid += 1
        return cid

    def _apply(self, c: Commit) -> Optional[Edge]:
        """Fold one commit into the live projection (incremental)."""
        if c.kind == "node":
            (v,) = c.payload
            self.nodes.add(v)
            self._adj.setdefault(v, [])
        elif c.kind == "edge":
            u, v, rel, value = c.payload
            self.nodes.add(u)
            self.nodes.add(v)
            self._adj.setdefault(u, [])
            self._adj.setdefault(v, [])
            e = Edge(c.cid, u, v, rel, value)
            self._edges.append(e)
            self._adj[u].append((e, True))
            self._adj[v].append((e, False))
            return e
        elif c.kind == "merge":
            a, b = c.payload
            self._alias[b] = a
        # 'remove' commits act only via tombstones during a full rebuild
        return None

    def _rebuild(
        self,
        extra_exclude_commits=frozenset(),
        exclude_episodes=frozenset(),
    ) -> None:
        """Recompute the live projection from the commit log (invariant #5).

        Excludes ``self._excluded_commits`` plus any extra commits, plus any
        commit whose provenance intersects ``exclude_episodes`` (episode-level
        retraction, invariant #6). Removals tombstone their target edge commit.
        """
        excl = set(self._excluded_commits) | set(extra_exclude_commits)
        if exclude_episodes:
            ex = set(exclude_episodes)
            excl |= {c.cid for c in self._commits if set(c.provenance) & ex}

        tomb = {
            c.target
            for c in self._commits
            if c.kind == "remove" and c.cid not in excl and c.target is not None
        }

        self.nodes = set()
        self._edges = []
        self._adj = defaultdict(list)
        self._alias = {}
        for c in self._commits:
            if c.cid in excl or c.kind == "remove":
                continue
            if c.kind == "edge" and c.cid in tomb:
                continue
            self._apply(c)

    def resolve(self, x: Node) -> Node:
        """Follow the merge chain to the surviving representative of ``x``."""
        while x in self._alias:
            x = self._alias[x]
        return x

    # ---- retraction (invariant #6) ----
    def retract(self, cid: int, reason: str = "") -> None:
        """Exclude a commitment and re-derive the projection. Never deletes it."""
        self._excluded_commits.add(cid)
        self._rebuild()

    def projected(self, exclude_commits=frozenset(), exclude_episodes=frozenset()):
        """A read-only sibling web rebuilt under extra exclusions (no mutation).

        Used to preview a retraction (the causal-cone re-derivation of
        ``docs/scaling.md`` §3, whole-log at this scale).
        """
        sib = Web(self.algebra, self.name, self.grow_cost, journal=self.journal, cf=True)
        sib._commits = list(self._commits)
        sib._excluded_commits = set(self._excluded_commits)
        sib._next_cid = self._next_cid
        sib.observations = list(self.observations)
        sib._rebuild(extra_exclude_commits=exclude_commits, exclude_episodes=exclude_episodes)
        return sib

    # ================================================================ accessors
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def neighbors(self, u: Node) -> Iterator[tuple[Node, Element, int]]:
        """Yield ``(neighbor, transport_value, eid)`` including converses."""
        for edge, forward in self._adj[u]:
            if forward:
                yield edge.v, edge.value, edge.eid
            else:
                yield edge.u, self.algebra.dagger(edge.value), edge.eid

    def edge_value(self, u: Node, v: Node) -> Optional[Element]:
        for w, value, _ in self.neighbors(u):
            if w == v:
                return value
        return None

    def transport(self, path: list[Node]) -> Optional[Element]:
        """Compose edge values along a node sequence (pure; does not emit)."""
        values = []
        for u, v in zip(path, path[1:]):
            g = self.edge_value(u, v)
            if g is None:
                return None
            values.append(g)
        return self.algebra.compose_all(values)

    def steps(self, u: Node, rel: str) -> list[tuple[Node, Element]]:
        """All ``(neighbor, value)`` reachable from ``u`` by relation ``rel``.

        A converse relation is written ``rel~`` (e.g. ``succ~`` = predecessor).
        Multi-valued: a partial/attribute relation may return zero, one, or many.
        """
        out = []
        for edge, forward in self._adj[u]:
            if forward and edge.rel == rel:
                out.append((edge.v, edge.value))
            elif (not forward) and rel.endswith("~") and edge.rel == rel[:-1]:
                out.append((edge.u, self.algebra.dagger(edge.value)))
        return out

    def step(self, u: Node, rel: str) -> Optional[tuple[Node, Element]]:
        """Follow ``rel`` one hop from ``u`` (first match); ``None`` at a boundary."""
        s = self.steps(u, rel)
        return s[0] if s else None

    def walk(self, start: Node, rel: str, k: int) -> WalkResult:
        """Query walk: follow ``rel`` ``k`` times from ``start`` (an act, #4).

        Stops early at a boundary; the trace records the endpoint and, when it
        fell off, a ``deficit:`` witness token (the unpaired leftover of a query
        that could not close).
        """
        cur = start
        taken = 0
        for _ in range(k):
            nxt = self.step(cur, rel)
            if nxt is None:
                break
            cur = nxt[0]
            taken += 1
        off_web = taken < k
        remaining = k - taken
        witness = {cur} if not off_web else {cur, f"deficit:{remaining}"}
        self._trace({start}, witness, tag="walk")
        return WalkResult(start, rel, k, cur, taken, remaining, off_web)

    def underlying_graph(self) -> nx.MultiGraph:
        g = nx.MultiGraph()
        g.add_nodes_from(self.nodes)
        for e in self._edges:
            g.add_edge(e.u, e.v, key=e.eid, value=e.value)
        return g

    # ================================================================ build moves
    def add_node(self, v: Node, *, grown: bool = False, provenance=()) -> None:
        """Add a node (cost-free build move). Emits a trace (invariant #4)."""
        if v not in self.nodes:
            c = Commit(self._new_cid(), "node", (v,), "grow" if grown else "init", tuple(provenance))
            self._commits.append(c)
            self._apply(c)
            if grown:
                self.growth_log.append(("node", v))
        self._trace({v}, {f"node:{v}"}, tag="add_node")

    def add_edge(self, u: Node, v: Node, rel: str, value: Element, *, provenance=()) -> Edge:
        """Add a forward edge (converse implicit). Cost-free build move."""
        c = Commit(self._new_cid(), "edge", (u, v, rel, value), "init", tuple(provenance))
        self._commits.append(c)
        edge = self._apply(c)
        self._trace({u}, {v}, [(u, v)], tag="add_edge")
        return edge  # type: ignore[return-value]

    # ================================================================ move: relabel
    def relabel(self, phi: dict[Node, Element]) -> None:
        """Apply a potential (cost 0). Rewrites values, preserves holonomy.

        Ephemeral gauge: not a commitment, so a later :meth:`_rebuild` resets
        values (relabeling is meaningless bookkeeping, glossary).
        """
        ident = self.algebra.identity
        for e in self._edges:
            e.value = self.algebra.relabel_edge(phi.get(e.u, ident), e.value, phi.get(e.v, ident))
        self._trace(set(phi.keys()) or {"phi"}, {f"phi:{n}" for n in phi}, tag="relabel")
        self.total_cost += COST_RELABEL

    # ================================================================ move: rewire
    def rewire(self, *, add=None, remove=None, merge=None, provenance=()) -> None:
        """A cost-1 edit among existing nodes (exactly one of add/remove/merge).

        Rolled back and raised if it would contradict an observation (#2).
        """
        if sum(x is not None for x in (add, remove, merge)) != 1:
            raise ValueError("rewire takes exactly one of add/remove/merge")

        snap = self._snapshot()
        try:
            if add is not None:
                u, v, rel, value = add
                if u not in self.nodes or v not in self.nodes:
                    raise ValueError("rewire.add requires existing nodes; use grow")
                c = Commit(self._new_cid(), "edge", (u, v, rel, value), "rewire", tuple(provenance))
                self._commits.append(c)
                self._apply(c)
                self._trace({u}, {v}, [(u, v)], tag="rewire")
            elif remove is not None:
                c = Commit(self._new_cid(), "remove", (remove,), "rewire", tuple(provenance), target=remove)
                self._commits.append(c)
                self._rebuild()
                self._trace({f"e{remove}"}, set(), tag="rewire")
            else:
                a, b = merge
                if a not in self.nodes or b not in self.nodes:
                    raise ValueError("merge requires two existing nodes")
                c = Commit(self._new_cid(), "merge", (a, b), "rewire", tuple(provenance))
                self._commits.append(c)
                self._rebuild()
                self._trace({a, b}, {a}, [(a, a)], tag="rewire")
            self._check_observations()
        except Exception:
            self._restore(snap)
            raise
        self.total_cost += COST_REWIRE

    # ================================================================ move: grow
    def grow(self, new_nodes: list[Node], new_edges: list[tuple], *, provenance=()) -> None:
        """Add fresh nodes and edges (cost K). Rolled back if it contradicts data."""
        snap = self._snapshot()
        try:
            for v in new_nodes:
                c = Commit(self._new_cid(), "node", (v,), "grow", tuple(provenance))
                self._commits.append(c)
                self._apply(c)
                self.growth_log.append(("node", v))
            for (u, v, rel, value) in new_edges:
                c = Commit(self._new_cid(), "edge", (u, v, rel, value), "grow", tuple(provenance))
                self._commits.append(c)
                self._apply(c)
                self.growth_log.append(("edge", u, v, rel, value))
            self._check_observations()
        except Exception:
            self._restore(snap)
            raise
        self._trace(set(new_nodes) or {"grow"}, {f"grow{len(new_nodes)}"}, tag="grow")
        self.total_cost += self.grow_cost

    def fresh_node(self, prefix: str = "g") -> str:
        i = 0
        while f"{prefix}{i}" in self.nodes:
            i += 1
        return f"{prefix}{i}"

    # ================================================================ simulate (#8)
    def fork(self) -> "Web":
        """A cheap copy sharing the journal, for scoring a move before commit.

        Emits ``cf``-flagged traces; its own commitment list is independent, so
        moves on the fork never touch this web's projection.
        """
        f = Web(self.algebra, f"{self.name}~cf", self.grow_cost, journal=self.journal, cf=True)
        f._commits = list(self._commits)
        f._excluded_commits = set(self._excluded_commits)
        f._next_cid = self._next_cid
        f.observations = list(self.observations)
        f.total_cost = self.total_cost
        f._rebuild()
        return f

    # ================================================================ observations
    def observe(self, obs: Observation) -> None:
        self.observations.append(obs)

    def observe_loop_closes(self, loop: list[Node]) -> None:
        self.observe(Observation("loop_closes", tuple(loop)))

    def observe_distinct(self, a: Node, b: Node) -> None:
        self.observe(Observation("distinct", (a, b)))

    def _check_observations(self) -> None:
        """Assert every observation still holds; raise otherwise (invariant #2).

        Distinctness is checked exactly via the merge alias map. Loop-closure is
        checked by node-path holonomy, well defined only on a simple (parallel-
        edge-free) region; under parallel/merged edges a node path is ambiguous,
        so this guard is best-effort there. Robust cycle-basis loop-closure
        checking arrives with the P1 growth/rewire search.
        """
        from .holonomy import holonomy

        for obs in self.observations:
            if obs.kind == "loop_closes":
                loop = [self.resolve(x) for x in obs.data]
                h = holonomy(self, loop)
                if h is not None and not self.algebra.is_identity(h):
                    raise ObservationViolation(
                        f"move breaks loop-closure observation {obs.data}: holonomy {h!r}"
                    )
            elif obs.kind == "distinct":
                a, b = obs.data
                if self.resolve(a) == self.resolve(b):
                    raise ObservationViolation(
                        f"move merged nodes asserted distinct: {obs.data}"
                    )

    # ================================================================ snapshot
    def _snapshot(self) -> tuple:
        return (list(self._commits), set(self._excluded_commits), self._next_cid, list(self.growth_log))

    def _restore(self, snap: tuple) -> None:
        self._commits, self._excluded_commits, self._next_cid, self.growth_log = (
            snap[0], snap[1], snap[2], snap[3]
        )
        self._rebuild()
