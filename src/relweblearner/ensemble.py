"""N-web interference and dynamic ensembles (P5).

Many webs work together. The union of the webs plus their cross-web
*identifications* is one graph, and an **interface defect** is a holonomy defect
on that union — a loop crossing web boundaries that fails to close. Because
`holonomy.py` is graph-agnostic, everything below works for any number of webs.

* An **identification** ``a ↔ b`` asserts a node of one web *is* a node of
  another (same-count ↔ same-generation); it is an ``iface`` edge carrying the
  identity transport. Consistency ⇔ all identified pairs share one coordinate
  offset; the modal offset is the **interface map**, outliers are poison.
* **Transfer with zero shared parameters**: the union's coordinates extend one
  web's reach through the others — no weights are shared, only graph edges over
  the frozen algebra.
* **Dynamic ensemble**: the *number of webs* is learned. Identifications that
  persist with support ``k`` merge web-groups; a contradiction that persists
  ``P`` rounds splits one — the count evolves over the stimulus stream.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .algebra import IntegerGroup
from .holonomy import defect_mass, defects, potential
from .journal import Journal
from .web import Web


@dataclass
class Identification:
    node_a: str
    node_b: str
    value: object = 0            # identity transport for "same"
    support: int = 1


PROJECT, SPLIT, SUPERPOSE = "project", "split", "superpose"


class Ensemble:
    """A collection of webs plus an interface of cross-web identifications."""

    def __init__(self, algebra=None, journal: Journal | None = None):
        self.algebra = algebra or IntegerGroup()
        self.journal = journal or Journal("ensemble")
        self.webs: dict[str, Web] = {}
        self.identifications: list[Identification] = []

    # ------------------------------------------------------------ webs
    def add_web(self, web: Web) -> None:
        self.webs[web.name] = web

    def coords(self, web_name: str) -> dict:
        """Coordinate (holonomy potential) of each node within a web."""
        return potential(self.webs[web_name])

    def all_coords(self) -> dict:
        out = {}
        for name in self.webs:
            out.update(self.coords(name))
        return out

    # ------------------------------------------------------------ interface
    def identify(self, node_a: str, node_b: str, value=0) -> Identification:
        idn = Identification(node_a, node_b, value)
        self.identifications.append(idn)
        return idn

    def union_web(self, ids: list | None = None) -> Web:
        """The union graph: every web's edges plus the interface edges."""
        ids = self.identifications if ids is None else ids
        u = Web(self.algebra, name="union")
        for w in self.webs.values():
            for e in w.edges():
                u.add_edge(e.u, e.v, e.rel, e.value)
        for idn in ids:
            if idn.node_a in u.nodes and idn.node_b in u.nodes:
                u.add_edge(idn.node_a, idn.node_b, "iface", idn.value)
        return u

    def interface_defect_mass(self, ids: list | None = None) -> float:
        """Defect mass contributed by the interface (webs are internally consistent)."""
        u = self.union_web(ids)
        internal = sum(defect_mass(w) for w in self.webs.values())
        return defect_mass(u) - internal

    def interface_defects(self, ids: list | None = None) -> list:
        """The individual interface defects (holonomy on the union)."""
        return defects(self.union_web(ids))

    # ---------------------------------------- mismatch-minimizing map search
    def find_interface_map(self, candidates: list) -> tuple:
        """Pick the alignment that minimizes interface mismatch.

        For each candidate ``(a, b)`` the implied offset is ``coord(b) -
        coord(a)``; the modal offset is the map. Returns ``(offset, consistent,
        poison)`` — the consistent identifications agree with the mode, the
        poison ones are outliers.
        """
        coord = self.all_coords()
        pairs = [(a, b) for (a, b) in candidates if a in coord and b in coord]
        offsets = [coord[b] - coord[a] for (a, b) in pairs]
        if not offsets:
            return None, [], []
        best = Counter(offsets).most_common(1)[0][0]
        consistent = [(a, b) for (a, b) in pairs if coord[b] - coord[a] == best]
        poison = [(a, b) for (a, b) in pairs if coord[b] - coord[a] != best]
        return best, consistent, poison

    # ------------------------------------------------------------ resolutions
    def resolve(self, identification: Identification, how: str):
        """Discharge an interface defect by one of the three resolutions."""
        if how == SPLIT:
            # the webs meant different things: sever the identification
            self.identifications = [i for i in self.identifications if i is not identification]
        elif how == PROJECT:
            # trust the coordinate reading: reinterpret as a +offset translation
            coord = self.all_coords()
            identification.value = coord[identification.node_b] - coord[identification.node_a]
        elif how == SUPERPOSE:
            # keep both readings, weighted (evidence-proportional); recorded, not merged
            identification.value = ("superpose", identification.value)
        else:
            raise ValueError(how)

    # ------------------------------------------------------------ transfer
    def answerable(self, facts: list, use_interface: bool) -> float:
        """Fraction of ``(start, k)`` queries answerable (target node exists).

        With the interface, the union's coordinates extend one web's reach
        through the others — transfer, with zero shared parameters. Without it,
        only the start's own web is available.
        """
        if use_interface:
            coord = self.all_coords()
            targets = set(coord.values())
            ok = sum(1 for (start, k) in facts if start in coord and coord[start] + k in targets)
        else:
            ok = 0
            for (start, k) in facts:
                for name, w in self.webs.items():
                    if start in w.nodes:
                        c = potential(w)
                        if c[start] + k in set(c.values()):
                            ok += 1
                        break
        return ok / len(facts) if facts else 0.0

    # ------------------------------------------------------ dynamic ensemble
    def stream_dynamics(self, events: list, k: int = 2, P: int = 3) -> list:
        """Process a stimulus stream; return the web-group count over time.

        Events (persistence-gated, per ``scaling.md §6``):
          * ``("identify", x, y)`` — evidence that web-groups x and y are one;
            at ``k`` supporting events with a consistent map they **merge**.
          * ``("contradict", x)`` — evidence of an internal contradiction; at
            ``P`` persistent rounds the group **splits** in two.
        The number of web-groups (distinct concepts-at-the-web-level) evolves.
        """
        groups: list[set] = [{name} for name in self.webs]
        support: Counter = Counter()
        contra: Counter = Counter()
        history: list[int] = []

        def group_of(name):
            for i, g in enumerate(groups):
                if name in g:
                    return i
            return None

        for ev in events:
            if ev[0] == "identify":
                _, x, y = ev
                gx, gy = group_of(x), group_of(y)
                if gx is not None and gy is not None and gx != gy:
                    support[frozenset((gx, gy))] += 1
                    if support[frozenset((gx, gy))] >= k:
                        merged = groups[gx] | groups[gy]
                        groups = [g for i, g in enumerate(groups) if i not in (gx, gy)]
                        groups.append(merged)
                        support.clear()
            elif ev[0] == "contradict":
                _, x = ev
                gx = group_of(x)
                if gx is not None and len(groups[gx]) >= 2:
                    contra[gx] += 1
                    if contra[gx] >= P:
                        members = sorted(groups[gx])
                        half = len(members) // 2 or 1
                        a, b = set(members[:half]), set(members[half:])
                        groups = [g for i, g in enumerate(groups) if i != gx]
                        groups += [a, b]
                        contra.clear()
            history.append(len(groups))
        return history
