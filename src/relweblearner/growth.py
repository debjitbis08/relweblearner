"""The growth engine (P1): persistence detector → minimal growth.

Invariant #9: the learning signal is *defect persistence*. A query that walks
off the web (a boundary obstruction, :class:`~relweblearner.web.WalkResult`
with ``off_web``) is the P1 obstruction. The engine's discipline:

1. **relabel is futile.** Relabeling provably changes no holonomy and no
   reachability (proven in P0), so a boundary walk-off survives it — we spend a
   round on it anyway to *demonstrate* that, matching "P rounds of
   relabel+rewire".
2. **rewire before growth.** Try to complete the walk by adding a single edge
   to an *existing* node — scored on a :meth:`~relweblearner.web.Web.fork`
   (invariant #8: simulate before committing). Accept only a rewire that lets
   the whole walk complete in-web and introduces no new defect.
3. **grow only if the obstruction persists** all ``P`` rounds. Growth is
   **minimal**: add exactly the deficit many nodes, wired with the frozen
   algebra, so the completed walk — and all arithmetic through the new nodes —
   is exact zero-shot.

`grow` is expensive (cost K); `relabel`/`rewire` are cheap. The engine embodies
"do not pay for a node until the cheap moves have demonstrably failed."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .holonomy import defect_mass
from .web import Node, WalkResult, Web


def _split(rel: str) -> tuple[str, bool]:
    """(base relation, is_converse) for a possibly-daggered relation token."""
    if rel.endswith("~"):
        return rel[:-1], True
    return rel, False


def _step_value(web: Web, rel: str):
    """The algebra value of one ``rel`` step (dagger of the base if converse)."""
    base, conv = _split(rel)
    for e in web.edges():
        if e.rel == base:
            return web.algebra.dagger(e.value) if conv else e.value
    return None


@dataclass
class GrowthEvent:
    """A committed growth: what triggered it, how big, where in the stream."""

    probe: tuple                 # (start, rel, k)
    n_nodes: int                 # nodes added (== deficit for a linear walk)
    position: int                # index in the probe stream
    new_nodes: list


@dataclass
class Answer:
    """The engine's response to one probe."""

    endpoint: Optional[Node]
    grew: Optional[GrowthEvent]
    rounds_survived: int         # rounds of relabel+rewire the obstruction survived


class GrowthEngine:
    """Persistence-gated minimal growth over a stream of query probes."""

    def __init__(self, P: int = 3, seed: int = 0):
        self.P = P
        self._relabel_tick = seed          # deterministic relabel perturbations
        self.events: list[GrowthEvent] = []

    # ------------------------------------------------------------ public
    def answer(self, web: Web, start: Node, rel: str, k: int, position: int = 0) -> Answer:
        """Answer 'walk ``rel`` ``k`` times from ``start``', growing if forced."""
        res = web.walk(start, rel, k)
        if not res.off_web:
            return Answer(endpoint=res.endpoint, grew=None, rounds_survived=0)

        # obstruction: try to discharge cheaply for P rounds before growing.
        for r in range(self.P):
            self._relabel_is_futile(web, res)            # demonstrate on a fork
            t = self._try_rewire_discharge(web, res)
            if t is not None:
                self._commit_rewire(web, res, t)
                res2 = web.walk(start, rel, k)
                return Answer(res2.endpoint, None, rounds_survived=r)

        # persisted: minimal grow.
        event = self._minimal_grow(web, res, position)
        self.events.append(event)
        res2 = web.walk(start, rel, k)
        return Answer(res2.endpoint, grew=event, rounds_survived=self.P)

    # ------------------------------------------------------------ internals
    def _relabel_is_futile(self, web: Web, res: WalkResult) -> bool:
        """Demonstrate that relabeling cannot discharge the obstruction.

        Applied to a *fork* so the committed web's values are never touched
        (relabel is gauge, but mutating live values would corrupt scoring reads
        like coordinates). Reachability is structure-only, so the walk still
        falls off — returns True, always, which is exactly the point: relabel is
        proven futile (P0), rewire/grow are the only real moves.
        """
        self._relabel_tick += 1
        f = web.fork()
        phi = {n: (hash((n, self._relabel_tick)) % 7) - 3 for n in f.nodes}
        f.relabel(phi)
        return f.walk(res.start, res.rel, res.k).off_web

    def _try_rewire_discharge(self, web: Web, res: WalkResult) -> Optional[Node]:
        """Is there an existing node a single rewire can connect so the walk
        completes in-web with no new defect? Scored on a fork (invariant #8)."""
        base, conv = _split(res.rel)
        step_val = _step_value(web, res.rel)
        if step_val is None:
            return None
        b = res.endpoint
        base_val = web.algebra.dagger(step_val) if conv else step_val
        baseline = defect_mass(web)
        for t in sorted(web.nodes, key=repr):
            if t == b:
                continue
            trial = web.fork()
            if conv:
                trial.rewire(add=(t, b, base, base_val))   # t becomes b's rel-predecessor
            else:
                trial.rewire(add=(b, t, base, base_val))
            r2 = trial.walk(res.start, res.rel, res.k)
            if not r2.off_web and defect_mass(trial) <= baseline:
                return t
        return None

    def _commit_rewire(self, web: Web, res: WalkResult, t: Node) -> None:
        base, conv = _split(res.rel)
        step_val = _step_value(web, res.rel)
        base_val = web.algebra.dagger(step_val) if conv else step_val
        if conv:
            web.rewire(add=(t, res.endpoint, base, base_val))
        else:
            web.rewire(add=(res.endpoint, t, base, base_val))

    def _fresh_names(self, web: Web, count: int) -> list[str]:
        names: list[str] = []
        i = 0
        while len(names) < count:
            cand = f"g{i}"
            i += 1
            if cand not in web.nodes and cand not in names:
                names.append(cand)
        return names

    def _minimal_grow(self, web: Web, res: WalkResult, position: int) -> GrowthEvent:
        """Add exactly ``res.remaining`` nodes extending the walk direction.

        BFS over completion candidates degenerates, for a linear walk with no
        reusable in-web node, to a chain of ``remaining`` fresh nodes wired with
        the frozen step value.
        """
        base, conv = _split(res.rel)
        step_val = _step_value(web, res.rel)
        base_val = web.algebra.dagger(step_val) if conv else step_val
        r = res.remaining
        names = self._fresh_names(web, r)

        edges = []
        prev = res.endpoint
        for name in names:
            if conv:
                edges.append((name, prev, base, base_val))   # name -[base]-> prev
            else:
                edges.append((prev, name, base, base_val))   # prev -[base]-> name
            prev = name

        web.grow(new_nodes=names, new_edges=edges)
        return GrowthEvent(
            probe=(res.start, res.rel, res.k),
            n_nodes=r,
            position=position,
            new_nodes=names,
        )
