"""The journal: one append-only bus, one parser (invariants 4–7).

The journal is the single event stream. World observations and the learner's
own act traces are both :class:`~relweblearner.episode.Episode`s living here;
there is no second log and no branching on origin. It is **append-only**:
nothing is ever deleted. A belief that must be retracted is *excluded* — the
episode stays, flagged — and the projection is rebuilt by replaying the log
without it (invariants 5 & 6).

Responsibilities:

* **Bus / homoiconicity (inv 4):** :meth:`emit` appends an act trace in the
  bare episode format; :meth:`append` ingests a world episode. Same store.
* **Provenance (inv 7):** act ids are minted only here, in the reserved
  :data:`~relweblearner.episode.ACT_NAMESPACE`. :meth:`append` rejects any
  external episode whose ids intrude on that namespace.
* **Event sourcing (inv 5):** :meth:`record_justification` binds a committed
  inference to the episodes that justify it (the seed of the provenance DAG,
  see ``docs/scaling.md``); :meth:`committed` replays the world stream minus an
  exclusion set.
* **Commitment policy (inv 6):** :meth:`exclude` flags an episode out (never
  deletes it).
* **Counterfactual isolation (inv 8):** cf episodes ride the same bus, flagged;
  they never appear in :meth:`committed`, so they cannot enter belief.

Episode ids are **opaque, position-independent handles** — an ``EpisodeId
(source, seq)`` pair, not a list index. This is the cheap anti-corner move from
``docs/scaling.md`` §3–4: it survives log compaction (front-truncation) and
multi-source merge (volunteer computing) without touching callers, which treat
the id as a black box.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable, Iterator, NamedTuple, Optional

from .episode import ACT_NAMESPACE, Episode


class NamespaceViolation(Exception):
    """An external episode tried to claim the reserved act namespace (inv 7)."""


class EpisodeId(NamedTuple):
    """Opaque, position-independent, coordination-free episode handle.

    ``source`` identifies the emitter (a journal name today; a machine/volunteer
    id under distribution). ``seq`` is a per-source monotonic counter. Callers
    must treat this as an opaque token — do NOT rely on ordering across sources
    or on ``seq`` being a global position.
    """

    source: str
    seq: int


@dataclass(frozen=True)
class Counts:
    total: int
    world: int
    act: int
    cf: int
    excluded: int


class Journal:
    """Append-only stream of bare episodes; the learner's whole memory."""

    def __init__(self, name: str = "J"):
        self.name = name
        self._order: list[EpisodeId] = []           # append order (for replay)
        self._by_id: dict[EpisodeId, Episode] = {}   # stable id -> episode
        self._excluded: set[EpisodeId] = set()       # flagged out, never removed
        self._justif: dict[Hashable, tuple] = {}     # inference key -> episode ids
        self._seq: dict[str, int] = defaultdict(int)  # per-source counters

    def _new_id(self, source: str) -> EpisodeId:
        eid = EpisodeId(source, self._seq[source])
        self._seq[source] += 1
        return eid

    # ------------------------------------------------------------ ingestion
    def append(self, ep: Episode, source: Optional[str] = None) -> EpisodeId:
        """Ingest a world episode; return its stable id (provenance handle).

        Rejects cf episodes (imagined events are emitted, not ingested) and any
        episode whose ids squat on the reserved act namespace (invariant 7).
        ``source`` identifies the emitter (defaults to this journal); distinct
        sources are how multi-machine / volunteer logs stay collision-free.
        """
        if ep.cf:
            raise ValueError("cf episodes are emitted via emit(), not appended")
        if ep.touches_act_namespace():
            raise NamespaceViolation(
                f"external episode claims reserved namespace {ACT_NAMESPACE!r}"
            )
        return self._store(ep, source or self.name)

    def emit(
        self,
        members1: Iterable,
        members2: Iterable,
        pairing: Iterable = (),
        *,
        cf: bool = False,
        tag: str = "act",
    ) -> EpisodeId:
        """Append an act trace in the bare format; mint its act-namespaced ids.

        This is how invariant 4's "no silent operations" is realized: every act
        calls :meth:`emit`. Set ``cf=True`` for a simulated (counterfactual)
        act (invariant 8). Emission is funnelled through this single seam so the
        learned attention/gating policy of ``docs/scaling.md`` §6 has exactly
        one place to hook later.
        """
        seq = self._seq[self.name]
        aid = f"{ACT_NAMESPACE}:{self.name}.{tag}{seq}"
        ep = Episode(
            f"{aid}.in", frozenset(members1),
            f"{aid}.out", frozenset(members2),
            tuple(pairing), cf=cf,
        )
        return self._store(ep, self.name)

    def _store(self, ep: Episode, source: str) -> EpisodeId:
        eid = self._new_id(source)
        self._order.append(eid)
        self._by_id[eid] = ep
        return eid

    # ------------------------------------------------------------ exclusion
    def exclude(self, eid: EpisodeId, reason: str = "") -> None:
        """Flag an episode out of belief (invariant 6). Never deletes it."""
        if eid not in self._by_id:
            raise KeyError(eid)
        self._excluded.add(eid)

    def is_excluded(self, eid: EpisodeId) -> bool:
        return eid in self._excluded

    @property
    def excluded(self) -> frozenset:
        return frozenset(self._excluded)

    # ------------------------------------------------------------ provenance
    def record_justification(self, key: Hashable, episode_ids: Iterable[EpisodeId]) -> None:
        """Bind a committed inference to its justifying episodes (invariant 5).

        This is the first-class provenance edge that the causal-cone retraction
        of ``docs/scaling.md`` §3 walks; keep it populated for every commit.
        """
        self._justif[key] = tuple(episode_ids)

    def justification(self, key: Hashable) -> tuple:
        return self._justif.get(key, ())

    # ------------------------------------------------------------ replay views
    def __len__(self) -> int:
        return len(self._order)

    def __getitem__(self, eid: EpisodeId) -> Episode:
        return self._by_id[eid]

    def all_entries(self) -> Iterator[tuple[EpisodeId, Episode]]:
        """Every episode with its id, in append order (world, act, cf)."""
        for eid in self._order:
            yield eid, self._by_id[eid]

    def committed(
        self, extra_exclude: Optional[Iterable[EpisodeId]] = None
    ) -> Iterator[tuple[EpisodeId, Episode]]:
        """Replay the belief-bearing world stream: non-act, non-cf, non-excluded.

        Pass ``extra_exclude`` to simulate a retraction without mutating the
        journal (localize-and-replay, invariant 6).
        """
        drop = set(self._excluded)
        if extra_exclude:
            drop |= set(extra_exclude)
        for eid in self._order:
            ep = self._by_id[eid]
            if eid in drop or ep.cf or ep.is_act_trace():
                continue
            yield eid, ep

    def act_stream(self) -> Iterator[tuple[EpisodeId, Episode]]:
        """The learner's own act traces (reflection fodder, invariant 4/P6)."""
        for eid in self._order:
            ep = self._by_id[eid]
            if ep.is_act_trace() and not ep.cf:
                yield eid, ep

    # ------------------------------------------------------------ metrics
    def counts(self) -> Counts:
        entries = list(self._by_id.values())
        act = sum(1 for e in entries if e.is_act_trace())
        cf = sum(1 for e in entries if e.cf)
        world = sum(1 for e in entries if not e.is_act_trace() and not e.cf)
        return Counts(
            total=len(entries),
            world=world,
            act=act,
            cf=cf,
            excluded=len(self._excluded),
        )
