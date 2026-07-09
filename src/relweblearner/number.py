"""Constructing number from counting (P1b) — on the holonomy substrate.

Numbers are never input. The learner ingests bare pairing episodes, derives two
predicates itself, and **projects** them onto a web in the frozen algebra Z:

* ``MATCH(A, B)`` — the pairing saturates both sides → the collections have the
  same (hidden) size → **merge** them (a rewire; the union-find quotient *is*
  the merge projection). The emergent class nodes ARE the numbers.
* ``ONEMORE(A, B)`` — one side saturated, exactly one object left over on the
  other → B is one more than A → a ``succ`` edge carrying ``+1``.

This is the reconciliation from ``docs/design-log.md`` §1 made concrete. Its
payoff: a **"class ONEMORE of itself"** — the contradiction a double-tagged
poison creates — is exactly a ``+1`` **self-loop**, i.e. a holonomy defect. So
invariant 9 (defect mass) literally detects counting contradictions; there is
no separate contradiction machinery.

The web is a *projection* of the episode log (invariant 5): :meth:`project`
replays the (non-excluded) world episodes, so retracting a poison is just
excluding its episode and re-projecting — the P7 hook.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

from .algebra import IntegerGroup
from .episode import Episode
from .holonomy import defects
from .journal import EpisodeId, Journal
from .web import Web


def derive(ep: Episode) -> Optional[tuple]:
    """Derive MATCH / ONEMORE from a bare episode's leftovers (learner-computed).

    ``("match", A, B)`` — both sides saturated.
    ``("onemore", X, Y)`` — X saturated, exactly one left over on Y (Y is one
    more than X). Anything else (a gap of ≥2, or an unsaturated pairing) yields
    ``None``.
    """
    la, lb = ep.leftovers()
    if not la and not lb:
        return ("match", ep.id1, ep.id2)
    if not la and len(lb) == 1:
        return ("onemore", ep.id1, ep.id2)
    if not lb and len(la) == 1:
        return ("onemore", ep.id2, ep.id1)
    return None


@dataclass
class NumberChain:
    """The projected number web plus its read-off structure."""

    web: Web
    order: list          # class reps, smallest-first (the count list)
    successor: dict      # class rep -> successor class rep
    class_members: dict  # class rep -> set of collection ids
    contradictions: list  # ("class ONEMORE of itself", rep) defects


class NumberLearner:
    """Builds a number chain from bare pairing episodes."""

    def __init__(self, journal: Optional[Journal] = None):
        self.journal = journal if journal is not None else Journal("number")

    # ------------------------------------------------------------ ingestion
    def ingest(self, ep: Episode) -> EpisodeId:
        """Append one world episode to the log (belief is derived, not stored)."""
        return self.journal.append(ep)

    def ingest_all(self, episodes: Iterable[Episode]) -> None:
        for ep in episodes:
            self.ingest(ep)

    def _members_of(self, cid) -> set:
        """Recover a collection's objects from the log (learner knows only episodes)."""
        for _eid, ep in self.journal.committed():
            if ep.id1 == cid:
                return set(ep.members1)
            if ep.id2 == cid:
                return set(ep.members2)
        return set()

    # ------------------------------------------------------------ projection
    def project(self, exclude: frozenset = frozenset(), repair: bool = True) -> NumberChain:
        """Replay the log into a number web (invariant 5).

        MATCH → merge; ONEMORE → ``+1`` succ edge; then guarded
        successor-injectivity repair. Excluded episode ids are skipped, so this
        doubles as replay-with-exclusions.
        """
        web = Web(IntegerGroup(), name="number")
        matches, onemores = [], []
        for eid, ep in self.journal.committed(extra_exclude=exclude):
            f = derive(ep)
            if f is None:
                continue
            (matches if f[0] == "match" else onemores).append((f[1], f[2], eid))

        # nodes
        for a, b, _ in matches + onemores:
            web.add_node(a)
            web.add_node(b)

        # quotient: merge matched collections (the union-find, on the web)
        for a, b, eid in matches:
            ra, rb = web.resolve(a), web.resolve(b)
            if ra != rb:
                web.rewire(merge=(ra, rb), provenance=[eid])

        # successor: one +1 edge per ONEMORE class-pair (deduped by final reps)
        seen = set()
        for a, b, eid in onemores:
            ra, rb = web.resolve(a), web.resolve(b)
            if (ra, rb) not in seen:
                seen.add((ra, rb))
                web.add_edge(ra, rb, "succ", 1, provenance=[eid])

        if repair:
            self._injectivity_repair(web)

        order, successor = self._chain(web)
        return NumberChain(
            web=web,
            order=order,
            successor=successor,
            class_members=self.classes(web),
            contradictions=self._self_loops(web),
        )

    # ------------------------------------------------------------ inference
    def _successor_map(self, web: Web) -> dict:
        """class rep -> set of successor class reps (self-loops excluded)."""
        succ = defaultdict(set)
        for e in web.edges():
            if e.rel != "succ":
                continue
            ra, rb = web.resolve(e.u), web.resolve(e.v)
            if ra != rb:
                succ[ra].add(rb)
        return succ

    def _has_edge_between(self, web: Web, x, y) -> bool:
        rx, ry = web.resolve(x), web.resolve(y)
        for e in web.edges():
            if e.rel != "succ":
                continue
            a, b = web.resolve(e.u), web.resolve(e.v)
            if {a, b} == {rx, ry}:
                return True
        return False

    def _injectivity_repair(self, web: Web) -> None:
        """Successor injectivity as an inference rule (sleep-phase compression).

        A class with two successor-classes forces those targets to merge — they
        sit at equal potential, a 0-holonomy redundancy. **Guarded:** never merge
        two classes that have ONEMORE evidence between them; that would weld a
        class ONEMORE of itself (a genuine contradiction to report, not repair).
        """
        changed = True
        while changed:
            changed = False
            for c, targets in self._successor_map(web).items():
                ts = sorted({web.resolve(t) for t in targets}, key=repr)
                if len(ts) < 2:
                    continue
                t1, t2 = ts[0], ts[1]
                if self._has_edge_between(web, t1, t2):
                    continue                       # guarded: refuse (contradiction)
                web.rewire(merge=(t1, t2))
                changed = True
                break

    def _chain(self, web: Web) -> tuple[list, dict]:
        """Order the classes into the count list (smallest-first)."""
        succ = self._successor_map(web)
        nxt = {c: next(iter(ts)) for c, ts in succ.items() if len(ts) == 1}
        preds = set(nxt.values())
        starts = [c for c in nxt if c not in preds]
        order: list = []
        if starts:
            c = sorted(starts, key=repr)[0]
            seen = set()
            while c is not None and c not in seen:
                order.append(c)
                seen.add(c)
                c = nxt.get(c)
        return order, nxt

    def _self_loops(self, web: Web) -> list:
        """'class ONEMORE of itself' contradictions = ``+1`` self-loop defects."""
        return [
            ("class ONEMORE of itself", d.edge.u)
            for d in defects(web)
            if d.edge.u == d.edge.v
        ]

    # ------------------------------------------------------------ read-out
    def classes(self, web: Web) -> dict:
        # iterate ALL node ids (incl. merged-away ones) so class membership is
        # recovered even though a merge collapses the graph to representatives.
        cls = defaultdict(set)
        for n in web.all_node_ids():
            cls[web.resolve(n)].add(n)
        return cls

    def count(self, chain: NumberChain, k_members: set) -> Optional[int]:
        """Number a fresh collection by pairing it along the chain (routine c).

        Pairs ``k_members`` against a representative of each class in order until
        the pairing saturates both sides (MATCH); the position (1-based) is the
        number. Returns ``None`` if larger than every known class.
        """
        kl = list(k_members)
        for position, rep in enumerate(chain.order, start=1):
            members = list(self._members_of(rep))
            n = min(len(members), len(kl))
            pairing = list(zip(members[:n], kl[:n]))
            left = set(members) - {a for a, _ in pairing}
            right = set(kl) - {b for _, b in pairing}
            if not left and not right:            # MATCH by saturation → number
                return position
        return None
