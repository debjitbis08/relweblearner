"""A CREATURE — a named identity with a bounded, incrementally-distilled model.

The interactive :class:`~relweblearner.reader.Reader` keeps every episode in an
append-only log and recomputes the whole model on each read. That is correct but
does not scale: the log grows with everything READ, and re-derivation is
from-scratch. A learner's WORKING memory should instead grow only with what it
has LEARNED — a small world's frames and facts SATURATE — while episodes are a
stream to be distilled. The stream is not discarded: every episode (and every
committed act) is appended to an :class:`~relweblearner.episodelog.EpisodeLog`
first — file-backed at scale, streamed rather than loaded — so RAM stays
O(world) while the model remains a replayable PROJECTION of the log
(invariant #5): reproducible by :meth:`rebuild`, revocable at episode
granularity by :meth:`retract_episodes`, resumable by checkpoint + tail replay
(:meth:`load` / :meth:`catch_up`).

This module is that scalable substrate:

  * **Identity.** A creature has a stable ``id`` and ``name`` (and optional
    ``created``/``level`` metadata). It is an addressable entity, not an anonymous
    file at a path — the handle for its persistent, distilled model.
  * **Bounded model.** The state is ``frames`` + per-fact ``evidence`` (a count
    and a capped set of provenance sources) + a ``frontier`` census + a small
    rolling induction ``buffer``. Every part is bounded by what is learned, not by
    ``episodes_seen``; persisting it is O(world), not O(experience).
  * **Streaming ingest.** :meth:`observe` distils one episode in ~O(1): parse
    against current frames, bump the fact's evidence, or summarise it to the
    frontier and buffer it for the next re-induction. No replay.
  * **The algebra underneath.** Answering is lookup THEN transport
    (:meth:`_think`): relation classes get fixed-algebra transports inferred
    from converse-pair loops (P2, :mod:`~relweblearner.transport`), eligible
    facts project to algebra-valued group webs
    (:class:`~relweblearner.web.Web`), a never-taught question is answered by
    transport composition (P3, status ``derived``), a committed contradiction
    is a nonzero-holonomy defect (invariant #9, :meth:`defects`), and a
    persistent walk-off pays for growth through the stock P1 engine (status
    ``grown``), budgeted against query floods (P7). Where transport cannot
    reach — the attribute classes with no converse loops — committed MOTIF
    rules (:mod:`~relweblearner.motif`, glossary §0: words over existing
    edges) derive by inheritance: ``hen -kind of-> bird -has legs-> two``.

The scale tradeoff, stated honestly: in ROUTINE operation a frame induced late
applies to the ongoing stream and to whatever is still in the bounded buffer —
not retroactively to episodes already distilled out of working memory. At scale
the stream dwarfs the buffer, so missing a frame's first few hundred exposures
is negligible. Full retroactivity is not lost, though — it is PAID FOR: a
deliberate :meth:`rebuild` replays the whole log through the current frames.
Only a :class:`~relweblearner.episodelog.NullEpisodeLog` (the explicit opt-out)
trades retroactivity away entirely.

No silent operations (invariant #4): every epistemic act — observing, inducing
a frame, merging relations, growing, retracting, answering, even taking a
snapshot — emits a bare trace episode onto one shared
:class:`~relweblearner.journal.Journal` bus via the single :meth:`_trace` seam,
so the P6 reflection machinery consumes the creature's own acts unchanged; and
consequential merges are SIMULATED before committing (invariant #8) —
:meth:`unify_relations` runs each candidate through
:func:`~relweblearner.transport.simulate_merge` (cf-flagged on the same bus)
and records rehearsal-refusals with reasons.

Number sense (P1b + P5): bare pairing episodes (:meth:`observe_pairing` /
:meth:`ingest_play`) build a CONSTRUCTED number chain — classes of piles, no
numeral ever input — and joint ostension pages (:meth:`observe` with a
``collection``) name classes the creature counts itself. The P5 interface map,
found by mismatch-minimizing search (:mod:`~relweblearner.numbersense`),
identifies the word chain with the constructed chain; word-order questions the
word web cannot answer then step along the constructed chain (``via:
"counting"``), and :meth:`how_many` numbers a fresh pile and speaks its word —
the system measuring the world with its own ruler.

Talk-back (:meth:`about` / :meth:`answer` / :meth:`say`) runs through the shared
:mod:`~relweblearner.talk` layer, so a streamed creature speaks identically to a
hand-trained one.
"""

from __future__ import annotations

import json
import os
import random
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from . import curriculum as C
from . import motif as MO
from . import talk as T
from . import transport as TR
from . import trust as TU
from .episodelog import EpisodeLog, InMemoryEpisodeLog
from .holonomy import defects as web_defects
from .holonomy import potential
from .journal import Journal
from .numbersense import NumberSense
from .store import EdgeStore, InMemoryEdgeStore


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "creature"


class Creature:
    def __init__(
        self,
        name: str,
        *,
        commit_k: int = 2,
        min_group: int = 6,
        dominance: float = 0.8,
        min_anchors: int = 2,
        induction_interval: int = 500,
        buffer_cap: int = 500,
        max_slot_tokens: int | None = None,
        source_cap: int = 16,
        exemplar_cap: int = 5,
        min_shared: int = 3,
        agree_threshold: float = 0.8,
        authority_k: int = 10,
        distrust_penalty: float = 3.0,
        exception_fraction: float = 0.2,
        derive_depth: int = 6,
        growth_persistence: int = 3,
        growth_budget: int = 16,
        fission_budget: int = 8,
        wonder_cap: int = 64,
        seed: int = 0,
        reservoir_stratify: bool = True,
        created: str | None = None,
        level: int | None = None,
        store: EdgeStore | None = None,
        log: EpisodeLog | None = None,
        bus: Journal | None = None,
    ):
        self.name = name
        self.id = _slug(name)
        self.created = created
        self.level = level
        self.commit_k = commit_k
        self.min_group = min_group
        self.dominance = dominance
        self.min_anchors = min_anchors
        self.induction_interval = induction_interval
        self.buffer_cap = buffer_cap
        # A concept fact's arguments are SHORT phrases. On real open prose the
        # highest-frequency frames are function-word constructions ("the _ and _")
        # whose variable-width slots would otherwise swallow whole clauses into a
        # "fact". Capping each filler's width keeps the clean short-argument parses
        # (``the cat and dog`` -> ``(cat, dog)``) and rejects clause-swallowers to
        # the frontier. ``None`` = no cap (exact legacy behaviour for synthetic,
        # single-token-slot corpora).
        self.max_slot_tokens = max_slot_tokens
        self.source_cap = source_cap
        self.exemplar_cap = exemplar_cap
        self.min_shared = min_shared
        self.agree_threshold = agree_threshold
        self.authority_k = authority_k
        self.distrust_penalty = distrust_penalty
        self.exception_fraction = exception_fraction
        self.derive_depth = derive_depth
        self.growth_persistence = growth_persistence
        self.growth_budget = growth_budget
        self.fission_budget = fission_budget
        self.wonder_cap = wonder_cap
        self.seed = seed
        self.reservoir_stratify = reservoir_stratify
        self._rng = random.Random(seed)

        # The concept web's edges are the ONE unbounded part of the geometry — they
        # live behind an indexed EdgeStore (in-memory by default; SQLite / sharded
        # for open-world scale). Everything else a creature holds is bounded and
        # stays in memory: the language web (frames), the frontier census, and the
        # capped rolling induction buffer.
        self.edges: EdgeStore = store if store is not None else InMemoryEdgeStore()
        # The episode LOG (invariant #5): everything that mutates the creature —
        # world episodes and committed acts — is appended here before it is
        # distilled, so the distilled state below is a replayable CHECKPOINT
        # (``log_position`` = entries distilled so far). File-backed at scale
        # (JsonlEpisodeLog); NullEpisodeLog is the explicit distill-and-discard
        # opt-out with decrement-only retraction.
        self.log: EpisodeLog = log if log is not None else InMemoryEpisodeLog()
        self.log_position = 0
        # The trace BUS (invariant #4): every epistemic operation emits a bare
        # episode here — the core :class:`~relweblearner.journal.Journal`, so
        # reflection (P6) runs over the creature's acts with the machinery
        # unchanged and simulations ride it cf-flagged (invariant #8). The bus
        # is the LIVE event stream, not checkpoint state: it is deliberately
        # not serialised (a reloaded creature starts a fresh bus — its durable
        # history is the episode LOG above). Honest limit: the bus is in-RAM
        # and unbounded, O(experience); at open-world scale it needs the same
        # file-backed treatment the episode log got. A stated seam, deferred.
        self.bus: Journal = bus if bus is not None else Journal(self.id)
        self.refused_merges: list[dict] = []                   # bounded rehearsal-refusal record
        # NUMBER SENSE (P1b + P5): the constructed chain and its naming table.
        # Like the group webs, this is a PROJECTION — of the pairing/ostension
        # entries in the episode log — so it is not checkpointed; load()
        # re-projects it from the log (`_reproject_numbers`). Under a
        # NullEpisodeLog it lives only as long as the process — the honest
        # price of the opt-out.
        self.numbers = NumberSense(commit_k=commit_k, source_cap=source_cap)
        self.frames: dict[str, C.Frame] = {}
        self.source_slot: dict[str, int] = {}                  # frame -> picture slot index
        self._rel_parent: dict[str, str] = {}                  # union-find: frame -> relation class
        self.frontier: dict[int, dict] = {}                    # length -> {count, exemplars}
        self.read_sources: set[str] = set()                    # ingestion ledger: registry source ids already read
        self.passed_stages: set[str] = set()                   # curriculum stages whose worksheet it has passed
        self._buffer: list[dict] = []                          # reservoir sample of unparsed episodes
        self._buffer_seen = 0                                  # unparsed episodes offered to the reservoir
        self._since_induction = 0
        # ------- the algebra layer (derived; rebuilt lazily when facts change) -------
        self._sectors: dict[str, TR.RelationSector] | None = None   # None = stale
        # TRUST (:mod:`~relweblearner.trust`) is likewise a derived cache, never
        # checkpoint state: per-(source, relation class) track records read off
        # the store and the log's exclusions. ``None`` = stale. Deliberately NOT
        # invalidated per observation (`_bump_fact`): new corroboration can only
        # raise a weight above its default, so a batch's lag is conservative;
        # every path that changes classes or exclusions does invalidate.
        self._trust: dict[tuple[str, str], tuple[int, int]] | None = None
        self._revising = False                                 # re-entrancy guard for revise()
        self._rel_groups: dict[str, str] = {}                  # class -> constraint-group root
        self._group_webs: dict[str, TR.Web] = {}               # group -> valued Web projection
        self._cmaps: dict[str, set] = {}                       # class -> eligible (src, tgt) pairs
        self._motifs: list[MO.MotifRule] = []                  # scored inheritance rules (projection)
        self.growth_events: list[dict] = []                    # committed P1 moves (budgeted, P7)
        self.grown_seq = 0                                     # allocator for posited concept ids
        # SENSES (fission, the dagger of merge): one surface word can name two
        # concepts, and the weld surfaces as a self-loop defect. A committed
        # split re-keys the second sense's edges to a ``word#n`` node and is an
        # act entry in the log (replayable, revocable); the lexicon below is
        # the durable record of the distinction — commit-time binding respects
        # it, so a split is never silently re-welded by fresh testimony.
        self.senses: dict[str, list[str]] = {}                 # surface word -> sense node ids
        self._sense_ids: set[str] = set()                      # every minted sense node id
        self.fission_events: list[dict] = []                   # committed splits (budgeted, P7)
        self.refused_fissions: list[dict] = []                 # bounded rehearsal-refusal record
        # CURIOSITY (PQ, docs/spec-curiosity.md): the creature's open questions.
        # A parsed-but-unanswerable question is a WONDER act on the episode log;
        # these four are the ledger's distilled state, a projection of those
        # acts (rebuilt by replay like everything else). The standing question
        # kinds — confirm (provisional edges) and arbitrate (unsettled
        # conflicts) — are computed fresh by :mod:`~relweblearner.curiosity`
        # and never stored.
        self.wonder_events: dict[str, dict] = {}               # wid -> birth act (insertion = age order)
        self.sought_counts: dict[str, int] = {}                # wid -> tick attempts so far
        self.parked_wonders: set[str] = set()                  # wids a tick gave up on (recorded, P7)
        self.resolved_wonders: dict[str, str] = {}             # wid -> how; a resolved wid never reopens
        # ------- counters (scalars, not history) -------
        self.episodes_seen = 0
        self.parsed = 0
        self.unparsed = 0

    # ============================================================= tracing (invariant #4)

    def _trace(self, tag: str, members1, members2, pairing=(), *, cf: bool = False):
        """The single emission seam, mirroring :meth:`Web._trace`: every
        epistemic act — ingest, induction, merge, growth, retraction, query —
        puts a bare episode on the shared bus. Members are small sets of
        opaque marker strings, never payloads: an ``observe`` trace REFERENCES
        its log entry (``log:<seq>``) rather than duplicating it, so the bus
        indexes the streams it unifies. Excluded on purpose: ``commit`` /
        ``close`` / ``save`` / ``load`` / ``to_dict`` / ``from_dict`` — pure
        persistence plumbing that moves bytes, not beliefs."""
        return self.bus.emit(members1, members2, pairing, cf=cf, tag=tag)

    # ============================================================= streaming ingest

    def observe(self, tokens, picture: str | None = None, source: str = "stream",
                marks=None, collection: dict | None = None) -> dict:
        """Log one episode, then distil it into the model (write-ahead: the log
        is the belief source, the model its projection — invariant #5).

        ``collection`` (optional) makes this a JOINT ostension page: a pile of
        opaque objects (``{"id", "members"}``) presented alongside the caption,
        whose tapped ``picture`` word names the pile's count. The creature
        counts the pile itself (P1b routine) — the word is never told which
        class it means — and the naming accrues as a candidate identification
        for the P5 interface map (:mod:`~relweblearner.numbersense`)."""
        if source.startswith("act:"):
            # invariant #7: the act namespace belongs to the learner's own moves;
            # external testimony may never claim it.
            raise ValueError("source namespace 'act:' is reserved for the learner's own moves")
        entry = {"kind": "world", "tokens": list(tokens), "picture": picture,
                 "source": source, "marks": [list(m) for m in marks] if marks else None}
        if collection is not None:
            entry["collection"] = {"id": collection["id"],
                                   "members": sorted(collection["members"])}
        seq = self.log.append(entry)
        self.log_position = seq + 1
        r = self._distill(entry)
        outcome = ({f"fact:{r['fact'][0]}:{r['fact'][1]}"} if r.get("parsed")
                   else {f"frontier:{len(entry['tokens'])}"})
        self._trace("observe", {f"log:{seq}"}, outcome)
        if collection is not None:
            counted = r.get("counted")
            self._trace("count", {entry["collection"]["id"]},
                        {f"position:{counted[0]}"} if counted else {"off-chain"})
        return r

    def observe_pairing(self, id1, members1, id2, members2, pairing=(),
                        source: str = "play") -> dict:
        """Log one BARE pairing episode — two collections of opaque objects and
        a pairing between them (the P1b stream; no token is ever a numeral) —
        and feed it to the number sense. MATCH/ONEMORE are derived, never given."""
        if source.startswith("act:"):
            raise ValueError("source namespace 'act:' is reserved for the learner's own moves")
        entry = {"kind": "pairing", "id1": id1, "members1": sorted(members1),
                 "id2": id2, "members2": sorted(members2),
                 "pairing": [list(p) for p in pairing], "source": source}
        seq = self.log.append(entry)
        self.log_position = seq + 1
        self._feed_pairing(entry)
        self._trace("pair", {id1}, {id2})
        return {"logged": seq}

    def ingest_play(self, episodes) -> "Creature":
        """Stream bare :class:`~relweblearner.episode.Episode` pairings (as the
        counting dataset emits) through :meth:`observe_pairing`."""
        n = 0
        for ep in episodes:
            self.observe_pairing(ep.id1, ep.members1, ep.id2, ep.members2, ep.pairing)
            n += 1
        self.commit()
        self._trace("ingest", {f"pairings:{n}"}, {"play"})
        return self

    def _feed_pairing(self, entry: dict) -> None:
        self.numbers.feed_pairing(entry["id1"], entry["members1"],
                                  entry["id2"], entry["members2"],
                                  [tuple(p) for p in entry["pairing"]])

    def _distill(self, entry: dict) -> dict:
        """Fold one WORLD log entry into the model (shared by live observation
        and replay — the projection is the same function of the log either way)."""
        self.episodes_seen += 1
        tokens = list(entry["tokens"])
        pic = (entry["picture"] or "").strip().lower() or None
        if entry.get("marks"):
            self._add_human_frame(tokens, entry["marks"])
        r = self._absorb({"tokens": tokens, "picture": pic, "source": entry["source"]})
        col = entry.get("collection")
        if col is not None and pic is not None:
            r["counted"] = self.numbers.name(pic, col["id"], col["members"], entry["source"])
        return r

    def ingest(self, episodes: Iterable[dict]) -> "Creature":
        """Stream a corpus through :meth:`observe` (episodes are ``{book/source,
        tokens, picture, marks}`` dicts, as the generator emits). A dict with
        ``id1`` is a BARE PAIRING episode (the counting-play channel) and is
        routed through :meth:`observe_pairing` — one stream, two senses."""
        n = 0
        for e in episodes:
            if "id1" in e:
                self.observe_pairing(e["id1"], e["members1"], e["id2"], e["members2"],
                                     e.get("pairing", ()),
                                     source=e.get("source") or e.get("book", "play"))
            else:
                self.observe(
                    e["tokens"],
                    picture=e.get("picture"),
                    source=e.get("source") or e.get("book", "stream"),
                    marks=e.get("marks"),
                    collection=e.get("collection"),
                )
            n += 1
        merges = self.unify_relations()   # recognise synonymous frames once evidence has accrued
        self.revise()                     # adjudicate contradictory corroborated testimony (its own trace)
        self.distinguish_senses()         # split words the geometry proves over-merged (its own trace)
        self.commit()
        self._trace("ingest", {f"episodes:{n}"}, {f"merges:{merges}"})
        return self

    def ingest_source(self, source_id: str, episodes: Iterable[dict]) -> "Creature":
        """Ingest one registry source and record its id in the ledger, so a later
        incremental run skips what has already been read."""
        self.ingest(episodes)
        self.read_sources.add(source_id)
        self._trace("ingest-source", {source_id}, {"read"})
        return self

    def commit(self) -> None:
        """Flush pending store and log writes (no-ops for in-memory backends)."""
        if hasattr(self.edges, "commit"):
            self.edges.commit()
        self.log.commit()

    # ============================================================= replay (invariant #5)
    #
    # The distilled state is a CHECKPOINT of a replay of the episode log. These
    # methods are the other half of the invariant: any belief is reproducible by
    # replaying the log (``rebuild``), revocable by replaying with an exclusion
    # set (``retract_episodes``), and a stale checkpoint catches up by replaying
    # the tail (``catch_up`` — what ``load`` does when the log has grown past
    # the save). World entries re-DISTIL (the projection is a function of the
    # stream); act entries re-APPLY as recorded (they are commitments, like the
    # core web's commit log — never re-derived).

    def _apply_entry(self, entry: dict) -> None:
        if entry["kind"] == "world":
            self._distill(entry)
        elif entry["kind"] == "pairing":
            self._feed_pairing(entry)
        elif entry["kind"] == "act":
            self._apply_act(entry)

    def _apply_act(self, event: dict) -> None:
        """Fold one committed act into the projection (live commit and replay
        share this path). Restores the posit-id allocator past every replayed
        posit so a later growth can never collide. A FISSION act re-keys the
        recorded edges to the sense node and registers the sense — as
        recorded, tolerant of edges a replay-with-exclusions never formed.
        The curiosity ledger acts (wonder/sought/resolved, spec-curiosity §1)
        fold into the ledger projection and touch no belief structure."""
        move = event.get("move")
        if move == "wonder":
            self.wonder_events[event["wid"]] = dict(event)
            return
        if move == "sought":
            self.sought_counts[event["wid"]] = self.sought_counts.get(event["wid"], 0) + 1
            if event.get("parked"):
                self.parked_wonders.add(event["wid"])
            return
        if move == "resolved":
            self.resolved_wonders[event["wid"]] = event.get("how", "")
            return
        if move == "fission":
            for s, t, s2, t2 in event["moved"]:
                self.edges.move_edge(s, t, s2, t2)
            senses = self.senses.setdefault(event["word"], [])
            if event["sense"] not in senses:
                senses.append(event["sense"])
            self._sense_ids.add(event["sense"])
            self.fission_events.append({k: event[k] for k in ("move", "word", "sense", "moved")})
            self._sectors = None
            self._trust = None
            return
        qclass = event["class"]
        if qclass not in self.frames:
            # a replay renumbered the induced frames: re-resolve the relation
            # by its anchor words (its stable name), falling back to the id.
            anchors = tuple(event.get("anchors", ()))
            match = next((fid for fid, f in sorted(self.frames.items())
                          if f.anchors == anchors), None)
            if match is not None:
                qclass = self._rel_find(match)
        fact = ((event["given"], event["answer"]) if event["forward"]
                else (event["answer"], event["given"]))
        self.edges.bump(fact[0], fact[1], qclass, f"act:{event['move']}", self.source_cap)
        self.growth_events.append(dict(event))
        for n in event.get("new_nodes", []):
            try:
                self.grown_seq = max(self.grown_seq, int(n.rsplit("-", 1)[1]) + 1)
            except (IndexError, ValueError):
                pass
        self._sectors = None
        self._trust = None

    def catch_up(self) -> int:
        """Replay log entries past the checkpoint position (skipping excluded
        ones); returns how many were applied. Idempotent when nothing is new."""
        start = self.log_position
        excluded = self.log.excluded()
        applied = 0
        for seq, entry in self.log.entries(self.log_position):
            if seq not in excluded:
                self._apply_entry(entry)
                applied += 1
            self.log_position = seq + 1
        if applied:
            self.unify_relations()
            self.commit()
        self._trace("catch-up", {f"from:{start}"}, {f"applied:{applied}"})
        return applied

    def _reset_model(self) -> None:
        """Clear every DERIVED belief structure, keeping identity, params, the
        read/stage ledger (bookkeeping, not belief) and the log itself. Only
        ever a prelude to a replay — the log remains the source of truth."""
        self.edges.clear()
        self.frames = {}
        self.source_slot = {}
        self._rel_parent = {}
        self.frontier = {}
        self._buffer = []
        self._buffer_seen = 0
        self._since_induction = 0
        self._rng = random.Random(self.seed)
        self._sectors = None
        self._trust = None
        self._rel_groups, self._group_webs, self._cmaps = {}, {}, {}
        self._motifs = []
        self.growth_events = []
        self.refused_merges = []
        self.senses = {}
        self._sense_ids = set()
        self.fission_events = []
        self.refused_fissions = []
        self.wonder_events = {}
        self.sought_counts = {}
        self.parked_wonders = set()
        self.resolved_wonders = {}
        self.numbers = NumberSense(commit_k=self.commit_k, source_cap=self.source_cap)
        self.grown_seq = 0
        self.episodes_seen = self.parsed = self.unparsed = 0

    def rebuild(self) -> "Creature":
        """Re-derive the whole model by replaying the log from zero under the
        current exclusion set (the reproducibility half of invariant #5)."""
        self._reset_model()
        self.log_position = 0
        self.catch_up()
        self._trace("rebuild", {f"entries:{len(self.log)}"},
                    {f"excluded:{len(self.log.excluded())}"})
        return self

    def _reproject_numbers(self) -> None:
        """Re-derive the number sense from the log's pairing/ostension entries
        up to the checkpoint position (the tail is :meth:`catch_up`'s job).

        The number web and naming table are projections, not checkpoint state
        — the word geometry is checkpointed because distilling it is lossy
        (episodes drop from the buffer), while the number projection is exact
        replay, so storing it would duplicate the log (invariant #5). Word
        distillation is NOT re-run here: those entries already shaped the
        checkpoint."""
        excluded = self.log.excluded()
        for seq, entry in self.log.entries(0):
            if seq >= self.log_position:
                break
            if seq in excluded:
                continue
            if entry["kind"] == "pairing":
                self._feed_pairing(entry)
            elif entry["kind"] == "world" and entry.get("collection"):
                pic = (entry.get("picture") or "").strip().lower() or None
                if pic is not None:
                    col = entry["collection"]
                    self.numbers.name(pic, col["id"], col["members"], entry["source"])

    def retract_episodes(self, seqs, reason: str = "") -> dict:
        """Invariant #6 retraction at EPISODE granularity: flag the entries
        excluded (never deleted) and rebuild by replay-with-exclusions. This is
        the retraction decrement cannot express — "this one page of an
        otherwise-good source was wrong" — and it reports collateral (committed
        facts lost beyond the lie) as the price of recovery. Requires a
        retaining log; a NullEpisodeLog raises."""
        seqs = sorted(set(seqs))
        before = self._num_committed()
        for s in seqs:
            self.log.exclude(s, reason)
        self.rebuild()
        after = self._num_committed()
        self._trace("retract-episodes", {f"excluded:{len(seqs)}"},
                    {f"uncommitted:{before - after}"})
        return {"excluded": seqs, "reason": reason,
                "committed_before": before, "committed_after": after,
                "uncommitted": before - after}

    def _episodes_for_facts(self, facts: set[tuple[str, str]]) -> dict[tuple, list[int]]:
        """Log sequences of the WORLD entries that distil to each oriented fact
        in ``facts`` under the CURRENT frames — the bridge from human-meaningful
        claims ("owl has four legs") to the episode ids invariant #6 excludes.
        A read-only replay-parse over ONE log pass however many facts are asked;
        it mutates nothing, so it is safe to run before deciding to retract.
        Episodes speak SURFACE words, so a fact whose endpoint a fission moved
        to a sense node is matched by its surface form."""
        want: dict[tuple, list[tuple]] = {}
        for f in facts:
            want.setdefault((self._desense(f[0]), self._desense(f[1])), []).append(f)
        seqs: dict[tuple, list[int]] = {}
        excluded = self.log.excluded()
        for seq, entry in self.log.entries(0):
            if seq in excluded or entry.get("kind") != "world":
                continue
            r = C.parse(list(entry["tokens"]), self.frames)
            if r is None or len(r[1]) != 2 or not self._fact_ok(r[1]):
                continue
            pic = (entry.get("picture") or "").strip().lower() or None
            fact = C._orient(r[1], pic) if pic else tuple(r[1])
            for orig in want.get(fact, ()):
                seqs.setdefault(orig, []).append(seq)
        return seqs

    def _episodes_for_fact(self, src: str, tgt: str) -> list[int]:
        fact = (src.strip().lower(), tgt.strip().lower())
        return self._episodes_for_facts({fact}).get(fact, [])

    def retract_claim(self, src: str, tgt: str, reason: str = "") -> dict:
        """Un-teach ONE specific wrong fact without a from-scratch retrain
        (invariant #6, claim granularity). Finds every log episode that taught
        ``src -> tgt``, flags them excluded (never deleted), and rebuilds by
        replay-with-exclusions, so the correction is durable — it survives a
        later :meth:`rebuild`, unlike the in-place decrement of
        :meth:`retract_source`. Reports collateral (other committed facts lost
        with the lie) as invariant #6 requires. A claim with no witnessing
        episode is a no-op, reported as ``matched: 0`` rather than an error."""
        src, tgt = src.strip().lower(), tgt.strip().lower()
        seqs = self._episodes_for_fact(src, tgt)
        if not seqs:
            self._trace("retract-claim", {f"{src}->{tgt}"}, {"no-match"})
            n = self._num_committed()
            return {"fact": [src, tgt], "matched": 0, "excluded": [],
                    "reason": reason, "committed_before": n,
                    "committed_after": n, "uncommitted": 0}
        rep = self.retract_episodes(seqs, reason or f"claim '{src} -> {tgt}' retracted")
        self._trace("retract-claim", {f"{src}->{tgt}"}, {f"episodes:{len(seqs)}"})
        return {"fact": [src, tgt], "matched": len(seqs), **rep}

    # ============================================================= belief revision

    def _belief_conflicts(self, rel_of: dict[str, str] | None = None) -> list[tuple[str, str, dict]]:
        """The web's standing belief conflicts, READ-ONLY: ``(class, source
        node, {target: edge info})`` for every source node holding two-plus
        committed targets in an otherwise-functional relation class. Extracted
        from :meth:`revise` (which adjudicates them where a decree is party)
        so the curiosity ledger can list the unsettled ones as ``arbitrate``
        wonders without touching anything."""
        if rel_of is None:
            rel_of = self._rel_of()
        raw: dict[str, dict[str, set]] = {}
        by_class: dict[str, dict[str, dict[str, dict]]] = {}
        for s, t, info in self.edges.iter_edges():
            classes = {rel_of.get(fid, fid) for fid in info.get("frames", ())}
            for cl in classes:
                raw.setdefault(cl, {}).setdefault(s, set()).add(t)
            if not self._committed_info(info, rel_of):
                continue
            for cl in classes:
                by_class.setdefault(cl, {}).setdefault(s, {})[t] = info
        conflicts = []
        for cl, m in by_class.items():
            contested = [s for s in m if len(m[s]) > 1]
            if not contested:
                continue
            # Functionality is judged on ALL testimony, never on committed
            # coverage: a hen is a kind of bird AND a kind of female even while
            # sparse corroboration commits only one kind for most other
            # animals, and a many-valued relation must not look single-valued
            # just because commitment is thin. A class whose raw testimony
            # tolerates fan-out is content; only a class that is single-valued
            # in everyone's mouth makes a second value a contradiction.
            rawm = raw.get(cl, m)
            n_multi = sum(1 for s in rawm if len(rawm[s]) > 1)
            if n_multi / max(1, len(rawm)) > (1.0 - self.agree_threshold):
                continue                    # a genuinely multi-valued relation: content, not error
            conflicts += [(cl, s, m[s]) for s in contested]
        return conflicts

    def _beats(self, a: dict, b: dict) -> bool:
        """Does candidate ``a`` decisively outrank candidate ``b`` in a belief
        conflict? Decree outranks testimony however corroborated; between two
        decrees the LATER one stands (a newer correction supersedes an older —
        the log's order is the tiebreak). Testimony NEVER outranks testimony:
        two corroborated camps disagreeing is either genuine dissent (a defect
        to keep visible until taught) or complementary truth the statistics
        cannot tell apart — the real scholar's 'a hen is a bird' vs 'a hen is
        a female' came from disjoint corpora with a decisive margin, and a
        margin rule erased 414 true episodes. Erosion, not erasure, is how
        testimony loses to testimony: distrusted sources' facts fall below the
        commitment weight on their own."""
        if a["fiat"] != b["fiat"]:
            return a["fiat"]
        if a["fiat"]:
            return a["latest"] > b["latest"]
        return False

    def revise(self) -> dict:
        """Notice and resolve the web's own belief conflicts — the teaching-
        shaped half of invariant #6, where :meth:`retract_claim` is the surgical
        half. A conflict is a source concept holding TWO+ committed targets in a
        relation class that is otherwise functional (single-valued for at least
        ``agree_threshold`` of its sources in RAW testimony, so thin committed
        coverage can never make a many-valued relation look single-valued — a
        class where fan-out is normal is content, not contradiction). A
        conflict is ADJUDICATED only when a decree is party to it
        (:meth:`_beats`: fiat over testimony, later fiat over earlier): the
        losing side's episodes are flagged excluded with the verdict as reason
        and the web rebuilt by replay-with-exclusions, so the creature itself
        retracts what it was taught better than — and the trust projection then
        holds the losing sources' bad marks, in that class only (the
        discrimination is learned, not decreed). Because this runs in every
        :meth:`ingest`, corrections DEFEND themselves: testimony re-teaching a
        corrected lie is re-excluded, and its sources dinged, with no owner in
        the loop. Testimony-only conflicts are KEPT (``corroborated-dissent``),
        reported, and stay visible as defects (invariant #9): the creature
        prefers acknowledged tension to a guess, and a distrusted camp's facts
        decommit by weight erosion rather than erasure. No-ops under a
        NullEpisodeLog (nothing replayable can be excluded)."""
        empty = {"conflicts": 0, "resolved": [], "unresolved": [],
                 "excluded": 0, "uncommitted": 0}
        if self._revising:
            return empty
        rel_of = self._rel_of()
        conflicts = self._belief_conflicts(rel_of)
        if not conflicts:
            self._trace("revise", {"conflicts:0"}, {"clean"})
            return empty
        # one log pass for every contested fact: witnesses for exclusion, log
        # order for the decree tiebreak
        fact_seqs = self._episodes_for_facts(
            {(s, t) for _cl, s, tm in conflicts for t in tm})
        before = self._num_committed()
        resolved, unresolved, exclusions = [], [], []
        for cl, s, tm in conflicts:
            cand = []
            for t, info in tm.items():
                cand.append({"target": t,
                             "fiat": any(TU.is_fiat(so) for so in info.get("sources", ())),
                             "support": self._edge_support(info, rel_of),
                             "latest": max(fact_seqs.get((s, t), [-1]))})
            if not any(a["fiat"] for a in cand):
                # corroborated camps disagreeing: acknowledged tension, kept
                # visible as a defect until teaching or trust erosion settles it
                unresolved.append({"class": cl, "source_node": s,
                                   "targets": sorted(tm), "reason": "corroborated-dissent"})
                continue
            winners = [a for a in cand
                       if all(self._beats(a, b) for b in cand if b is not a)]
            if not winners:
                unresolved.append({"class": cl, "source_node": s,
                                   "targets": sorted(tm), "reason": "indecisive"})
                continue
            win = winners[0]
            for lose in cand:
                if lose is win:
                    continue
                lseqs = fact_seqs.get((s, lose["target"]), [])
                if not lseqs:               # nothing replayable witnesses it (Null log)
                    unresolved.append({"class": cl, "source_node": s,
                                       "targets": sorted(tm), "reason": "no-episodes"})
                    continue
                exclusions += [(q, f"revision: '{s} -> {lose['target']}' outweighed by "
                                   f"'{s} -> {win['target']}' in {self._class_label(cl)!r}")
                               for q in lseqs]
                resolved.append({"class": cl, "source_node": s, "kept": win["target"],
                                 "dropped": lose["target"], "episodes": len(lseqs)})
        rep = {"conflicts": len(conflicts), "resolved": resolved,
               "unresolved": unresolved, "excluded": len(exclusions), "uncommitted": 0}
        if exclusions:
            self._revising = True
            try:
                for seq, reason in exclusions:
                    self.log.exclude(seq, reason)
                self.rebuild()
            finally:
                self._revising = False
            rep["uncommitted"] = before - self._num_committed()
        self._trace("revise", {f"conflicts:{len(conflicts)}"},
                    {f"resolved:{len(resolved)}", f"unresolved:{len(unresolved)}"})
        return rep

    def _draft_fact(self, frame_id: str, src: str, tgt: str) -> list[str] | None:
        """Tokens that express ``(src, tgt)`` through ``frame_id`` — the inverse
        of parsing, read back before returning (the L6 discipline) so a
        correction only ever teaches a phrase that re-parses to the fact it
        means. The picture is the source word (the frame's oriented slot)."""
        f = self.frames.get(frame_id)
        if f is None or f.n_slots != 2:
            return None
        slot = self.source_slot.get(frame_id)
        if slot is None:
            return None
        draft, i = [], 0
        for e in f.pattern:
            if e[0] == C.LIT:
                draft.append(e[1])
            else:
                draft.append(src if i == slot else tgt)
                i += 1
        r = C.parse(draft, self.frames)
        if r is None or C._orient(r[1], src) != (src, tgt):
            return None
        return draft

    def _relation_frames(self, src: str, wrong: str) -> list[str]:
        """The frames a correction of ``src -> wrong`` may be voiced through:
        the wrong fact's OWN frames, which name its relation. The replacement
        must be re-taught as that same relation — a wrong colour fixed to
        another colour stays colour, never leaks into ``has _ legs`` — and a
        value shared across relations (``four`` is both legs and sides) makes
        any guess from the value alone unsafe. So a correction requires the
        mistaken fact to actually exist; absent it, there is no relation to
        speak and nothing to correct (the caller is told to teach directly)."""
        info = self.edges.get(src.strip().lower(), wrong.strip().lower())
        return sorted(info["frames"]) if info and info.get("frames") else []

    def correct(self, src: str, wrong: str, right: str, *,
                source: str = "correction") -> dict:
        """Fix a mistake by TEACHING, not surgery: assert ``src -> right`` as ONE
        honest episode in the owner's fiat voice (``correction`` — a reserved
        namespace that carries commit strength by decree, never ``commit_k``
        counterfeit witnesses), voiced through a frame of the wrong fact's OWN
        relation (:meth:`_relation_frames`) so no other relation is polluted.
        Then :meth:`revise` runs: the creature itself notices the resulting
        committed conflict, prefers the decree, excludes the outweighed episodes
        — and the sources that taught the lie lose trust in that relation class
        (:meth:`trust_report`), so their future word there is taken with a grain
        of salt. Testimony that never rose to belief (a provisional wrong fact
        makes no committed conflict) is disqualified directly instead
        (:meth:`retract_claim`) — evidence cleanup, not belief revision.

        The correction stays fully auditable and reversible: it is an ordinary
        log episode, itself retractable, and a LATER correction outranks it
        (:meth:`_beats`). Returns what was taught, its status, the revision
        verdicts, and the usual retraction metrics."""
        src, wrong, right = src.strip().lower(), wrong.strip().lower(), right.strip().lower()
        existed = self.edges.get(src, wrong) is not None
        before = self._num_committed()
        frames = self._relation_frames(src, wrong)
        draft = next((d for fid in frames if (d := self._draft_fact(fid, src, right))), None)
        taught, revision, matched = None, None, 0
        if draft is not None:
            self.observe(draft, picture=src, source=source)
            self.unify_relations()
            revision = self.revise()
            self.commit()
            taught = " ".join(draft)
            matched = sum(r["episodes"] for r in revision["resolved"]
                          if r["source_node"] == src and r["dropped"] == wrong)
        if self.edges.get(src, wrong) is not None:
            ret = self.retract_claim(src, wrong, reason=f"corrected to '{right}'")
            matched += ret["matched"]
        note = None
        if draft is None:
            note = ("no believed fact '{}' -> '{}' to correct — teach the right fact directly"
                    .format(src, wrong) if not existed else
                    "could not voice the correction in the fact's own relation — teach it directly")
        after = self._num_committed()
        self._trace("correct", {f"{src}->{wrong}"}, {f"{src}->{right}"})
        return {"fact": [src, wrong], "matched": matched, "corrected_to": right,
                "taught": taught, "status": self._status((src, right)),
                "revision": revision, "note": note,
                "committed_before": before, "committed_after": after,
                "uncommitted": before - after}

    def close(self) -> None:
        self.edges.close()
        self.log.close()

    def _fact_ok(self, fillers) -> bool:
        """A parse yields a committable fact only if both slot fillers are short
        enough to be concept arguments (see ``max_slot_tokens``)."""
        if self.max_slot_tokens is None:
            return True
        return all(len(f.split()) <= self.max_slot_tokens for f in fillers)

    def _absorb(self, ep: dict) -> dict:
        r = C.parse(ep["tokens"], self.frames)
        if r is not None and len(r[1]) == 2 and self._fact_ok(r[1]):
            fid, fillers = r
            fact = C._orient(fillers, ep["picture"]) if ep["picture"] else tuple(fillers)
            fact = self._bump_fact(fact, ep["source"], fid, fillers, ep["picture"])
            self.parsed += 1
            return {"parsed": True, "frontier": False, "frame": fid, "fact": fact, "status": self._status(fact)}
        self.unparsed += 1
        self._bump_frontier(ep["tokens"])
        self._reservoir_add(ep)
        self._since_induction += 1
        if self._since_induction >= self.induction_interval:
            self._induce()
        return {"parsed": False, "frontier": True, "fact": None}

    def _bump_fact(self, fact, source, fid, fillers, picture) -> tuple:
        fact = self._sense_bind(*fact)                         # respect committed splits
        self.edges.bump(fact[0], fact[1], fid, source, self.source_cap)   # indexed, incremental
        self._sectors = None                                   # transports are stale
        if picture is not None and fid not in self.source_slot:
            for i, fill in enumerate(fillers):
                if fill == picture:
                    self.source_slot[fid] = i
                    break
        return fact

    def _cluster_key(self, ep: dict):
        """The retention cluster an unparsed episode belongs to. Frame induction
        blocks strictly by length (:func:`curriculum._mergeable` merges only
        equal-length signatures), so length is the principled key: fairness across
        lengths guarantees no length can monopolise. The natural refinement — a
        length-AND-anchor signature (the Referee's note) — would sub-divide a
        length once anchors are known; deferred because anchors are exactly what
        induction has yet to find for a still-frontier pattern."""
        return len(ep["tokens"])

    def _reservoir_add(self, ep: dict) -> None:
        """Retain a sample of the UN-ASSIMILATED stream, fairly across clusters.

        Only unparsed (frontier) episodes ever reach here — parsed ones are already
        distilled into geometry (``_absorb``), so this buffer is *structurally*
        frontier-priority: memory keeps what it could not yet understand, the only
        text that is irreplaceable (parsed text regenerates via ``write``; distilled
        facts do not need it). The reservoir is the retroactivity budget: a frame
        induced late can only ever re-parse what the buffer still holds.

        Within the frontier, retention is CLUSTER-FAIR (Zeigarnik with an anti-
        monopoly guard): a firehose of one kind of noise must not evict a rare but
        learnable pattern below its induction threshold. An under-represented
        cluster is never displaced — a newcomer under its fair share steals a slot
        from whichever cluster is over share; a cluster already at share churns only
        within itself. With a single cluster this reduces to Vitter's Algorithm R
        (uniform), so the common case is unbiased.

        Not load-bearing for retraction (that lives in the edge aggregates); purely
        the induction/audit substrate."""
        self._buffer_seen += 1
        if len(self._buffer) < self.buffer_cap:
            self._buffer.append(ep)
            return
        if not self.reservoir_stratify:                    # pure Algorithm R (uniform)
            j = self._rng.randrange(self._buffer_seen)
            if j < self.buffer_cap:
                self._buffer[j] = ep
            return

        key = self._cluster_key(ep)
        counts = Counter(self._cluster_key(e) for e in self._buffer)
        n_clusters = len(counts) + (0 if key in counts else 1)
        fair = max(1, self.buffer_cap // n_clusters)
        if counts.get(key, 0) < fair:
            # under fair share: protect it — take a slot from an over-share cluster
            # (never from another under-share one); else fall back to Algorithm R.
            over = [k for k in counts if counts[k] > fair]
            if over:
                hog = max(over, key=lambda k: counts[k])
                pool = [i for i, e in enumerate(self._buffer) if self._cluster_key(e) == hog]
                self._buffer[self._rng.choice(pool)] = ep
            else:
                j = self._rng.randrange(self._buffer_seen)
                if j < self.buffer_cap:
                    self._buffer[j] = ep
        else:
            # ep's cluster is already at/over fair share: churn WITHIN it only, so it
            # can never evict a different (possibly rarer) cluster.
            j = self._rng.randrange(self._buffer_seen)
            if j < self.buffer_cap:
                pool = [i for i, e in enumerate(self._buffer) if self._cluster_key(e) == key]
                self._buffer[self._rng.choice(pool)] = ep

    def _bump_frontier(self, tokens) -> None:
        k = len(tokens)
        f = self.frontier.setdefault(k, {"count": 0, "exemplars": []})
        f["count"] += 1
        ex = " ".join(tokens)
        if ex not in f["exemplars"] and len(f["exemplars"]) < self.exemplar_cap:
            f["exemplars"].append(ex)

    def _add_human_frame(self, tokens, marks) -> None:
        pat = C.pattern_from_marks(tokens, [list(m) for m in marks])
        n_anchors = sum(1 for e in pat if e[0] == C.LIT)
        n_slots = sum(1 for e in pat if e[0] == C.SLOT)
        if n_anchors < 1 or n_slots < 1 or any(f.pattern == pat for f in self.frames.values()):
            return
        fid = f"H{len(self.frames)}_{'_'.join(e[1] for e in pat if e[0] == C.LIT)}"
        self.frames[fid] = C.Frame(fid, pat)
        self._trace("induce", {"human"}, {fid})   # scaffolded frame growth is an act too
        self._rescan_buffer()

    def _induce(self) -> None:
        """Frontier-triggered growth over the bounded buffer (not the whole log)."""
        self._since_induction = 0
        if not self._buffer:
            return
        new = C.induce_frames(
            [ep["tokens"] for ep in self._buffer],
            min_group=self.min_group,
            dominance=self.dominance,
            min_anchors=self.min_anchors,
            prefix=f"S{self.episodes_seen}_",
        )
        existing = {f.anchors for f in self.frames.values()}
        added: list[str] = []
        for f in new.values():
            if f.anchors not in existing:
                self.frames[f.id] = f
                existing.add(f.anchors)
                added.append(f.id)
        if added:
            self._trace("induce", {f"buffer:{len(self._buffer)}"}, set(added))
            self._rescan_buffer()

    def _rescan_buffer(self) -> None:
        """Fold buffered episodes that now parse into evidence; keep the rest.
        This is the bounded, non-retroactive analogue of the Reader's full replay."""
        kept = []
        for ep in self._buffer:
            r = C.parse(ep["tokens"], self.frames)
            if r is not None and len(r[1]) == 2 and self._fact_ok(r[1]):
                fid, fillers = r
                fact = C._orient(fillers, ep["picture"]) if ep["picture"] else tuple(fillers)
                self._bump_fact(fact, ep["source"], fid, fillers, ep["picture"])
                self.parsed += 1
                self.unparsed -= 1
                f = self.frontier.get(len(ep["tokens"]))
                if f and f["count"] > 0:
                    f["count"] -= 1
            else:
                kept.append(ep)
        # episodes that now parse have left the unparsed stream; drop them from the
        # reservoir and its stream counter so it stays a sample of the STILL-unparsed
        # tail (approximate under deletion — the honest caveat of a bounded sample).
        self._buffer_seen = max(len(kept), self._buffer_seen - (len(self._buffer) - len(kept)))
        self._buffer = kept

    # ============================================================= relation unification

    def _rel_find(self, fid: str) -> str:
        p = self._rel_parent
        p.setdefault(fid, fid)
        while p[fid] != fid:
            p[fid] = p[p[fid]]
            fid = p[fid]
        return fid

    def _rel_union(self, a: str, b: str) -> None:
        ra, rb = self._rel_find(a), self._rel_find(b)
        if ra != rb:
            self._rel_parent[ra] = rb
            self._trust = None                     # class roots changed under the trust keys

    def _rel_of(self) -> dict[str, str]:
        return {fid: self._rel_find(fid) for fid in self.frames}

    def unify_relations(self) -> int:
        """Merge frames that express the SAME concept-web relation.

        Relation identity is the edge set a frame induces: two frames are the same
        relation iff their committed edge sets AGREE. So ``the X is Y`` and ``i see
        a Y X`` (both animal->colour) unify, while ``the X is Y`` and ``the X eats
        Y`` (colour vs food, disagreeing on every shared animal) never do. The
        merge is:

          * **evidence-gated** — needs >= ``min_shared`` shared committed arguments
            agreeing at >= ``agree_threshold`` (the commitment discipline, in the
            relation dimension);
          * **functionality-guarded** — refused if it makes the relation
            non-functional (:meth:`_merge_consistent`). Kept ALONGSIDE the
            simulation below because a functional fan-out is not a holonomy
            loop — the defect score alone cannot see it; and
          * **simulated before committed** (invariant #8) — each surviving
            candidate is IMAGINED on a counterfactual projection
            (:func:`~relweblearner.transport.simulate_merge`): the class maps
            are re-inferred with and without the merge, cf-flagged traces ride
            the shared bus, and the union is committed only if it neither
            raises defect mass nor demotes a composable class to a motif.
            A refused merge is logged with its reason (rehearsal-refusal),
            bounded in :attr:`refused_merges`.

        After unification, talk-back filters by relation CLASS, so synonymous frames
        answer each other. Returns the number of merges performed.
        """
        fids = [fid for fid, f in self.frames.items() if f.n_slots == 2]
        rel_of = self._rel_of()
        maps: dict[str, dict[str, set]] = {}      # frame -> {source: {committed targets}}
        for fid in fids:
            m: dict[str, set] = {}
            for s, t, info in self.edges.edges_by_rel(fid):
                if self._committed_info(info, rel_of):
                    m.setdefault(s, set()).add(t)
            maps[fid] = m
        merges = refused = 0
        cmaps: dict[str, set] | None = None       # class maps, valid until a union changes the roots
        for i, a in enumerate(fids):
            for b in fids[i + 1:]:
                if self._rel_find(a) == self._rel_find(b):
                    continue
                shared = set(maps[a]) & set(maps[b])
                if len(shared) < self.min_shared:
                    continue
                agree = sum(1 for s in shared if maps[a][s] == maps[b][s]) / len(shared)
                if agree < self.agree_threshold:
                    continue
                if not self._merge_consistent(maps[a], maps[b]):
                    self._refuse_merge(a, b, "functional fan-out conflict")
                    refused += 1
                    continue
                if cmaps is None:
                    cmaps = self._class_maps()
                verdict = TR.simulate_merge(
                    cmaps, self._rel_find(a), self._rel_find(b),
                    self.exception_fraction, journal=self.bus, name=self.id,
                )
                if verdict["commit"]:
                    self._rel_union(a, b)
                    self._trace("merge", {a, b}, {self._rel_find(a)})
                    merges += 1
                    cmaps = None
                else:
                    self._refuse_merge(a, b, verdict["reason"])
                    refused += 1
        if merges:
            self._sectors = None                    # classes changed; transports are stale
        self._trust = None                          # trust is keyed by class; refresh at the batch boundary
        self._trace("unify", {f"frames:{len(fids)}"},
                    {f"merges:{merges}", f"refused:{refused}"})
        return merges

    def _refuse_merge(self, a: str, b: str, reason: str) -> None:
        """Rehearsal-refusal (invariant #8): the move is declined with a logged
        reason, never silently skipped. Bounded diagnostic state — newest kept."""
        self.refused_merges = (self.refused_merges + [{"a": a, "b": b, "reason": reason}])[-32:]
        self._trace("refuse-merge", {a, b}, {reason})

    def _relation_classes(self) -> list[list[str]]:
        """Frames grouped by unified relation class (templates), for display."""
        classes: dict[str, list[str]] = {}
        for fid, f in self.frames.items():
            classes.setdefault(self._rel_find(fid), []).append(f.template)
        return sorted(sorted(v) for v in classes.values())

    def _merge_consistent(self, ma: dict, mb: dict) -> bool:
        """The combined relation stays (mostly) functional — only a tolerated few
        sources may gain a second target; more than that is a real contradiction and
        the merge is refused (the defect guard)."""
        union = set(ma) | set(mb)
        if not union:
            return False
        conflicts = sum(1 for s in union if len(ma.get(s, set()) | mb.get(s, set())) > 1)
        return conflicts / len(union) <= (1 - self.agree_threshold)

    # ============================================================= sense fission (merge's dagger)
    #
    # One surface word can name two concepts ("an orange is orange"), and under
    # one-node-per-word the weld surfaces as GEOMETRY: a committed reflexive
    # fact is a self-loop whose holonomy residual no relabel can change (it is
    # gauge-invariant, P0) and whose removal would erase true testimony. The
    # one observation-preserving repair left is FISSION — split the node — the
    # exact dagger of the rewire merge, run under the same disciplines:
    # evidence-gated, simulated before committed (invariant #8), budgeted (P7),
    # and logged as an act so replay reproduces it (invariant #5).

    def _desense(self, node: str) -> str:
        """The surface word behind a node id (a sense id voices as its word)."""
        return node.rsplit("#", 1)[0] if node in self._sense_ids else node

    def _sense_variants(self, word: str) -> list[str]:
        """The nodes a surface word may denote: itself plus its split senses."""
        return [word, *self.senses.get(word, ())]

    def _sense_bind(self, s: str, t: str) -> tuple[str, str]:
        """Route new testimony onto a committed sense split. A pair whose bare
        key still exists (or was never split) lands as spoken; a pair the
        fission moved accrues to the moved edge, so a split is never silently
        re-welded by repetition. A never-seen pair of an ambiguous word stays
        on the bare word — the conservative default; if that welds two senses
        again the defect returns and fission re-adjudicates."""
        if not self.senses or self.edges.get(s, t) is not None:
            return s, t
        for s2 in self._sense_variants(s):
            for t2 in self._sense_variants(t):
                if (s2, t2) != (s, t) and self.edges.get(s2, t2) is not None:
                    return s2, t2
        return s, t

    def _surface_edges(self, rows: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
        """Collapse sense ids to their surface words for talk-back, merging the
        collisions — the creature SPEAKS words; the sense distinction stays
        internal (and visible in the web views and snapshot geometry)."""
        merged: dict[tuple, dict] = {}
        for s, t, info in rows:
            key = (self._desense(s), self._desense(t))
            cur = merged.get(key)
            if cur is None:
                merged[key] = {"count": info["count"], "sources": dict(info["sources"]),
                               "frames": set(info["frames"])}
            else:
                cur["count"] += info["count"]
                for so, n in info["sources"].items():
                    cur["sources"][so] = cur["sources"].get(so, 0) + n
                cur["frames"] |= set(info["frames"])
        return [(s, t, info) for (s, t), info in merged.items()]

    def _fresh_sense(self, node: str) -> str:
        """A durable sense id for a split word: ``word#2``, ``word#3``, … —
        ``#`` never appears in a tokenised surface word, so a sense can no
        more collide with testimony vocabulary than a ``new-*`` posit can."""
        base = self._desense(node)
        n = len(self.senses.get(base, [])) + 2
        while f"{base}#{n}" in self._sense_ids:
            n += 1
        return f"{base}#{n}"

    def _refuse_fission(self, word: str, reason: str) -> None:
        """Rehearsal-refusal (invariant #8), mirroring :meth:`_refuse_merge`."""
        self.refused_fissions = (self.refused_fissions + [{"word": word, "reason": reason}])[-32:]
        self._trace("refuse-fission", {word}, {reason})

    def distinguish_senses(self) -> int:
        """Split words the geometry proves over-merged — merge's dagger.

        The trigger is the pinned, provably-unrepairable case: a committed
        SELF-LOOP with nonzero residual in a valued group web. Two partition
        plans, by the shape of the evidence: in a CHAIN-like group the node's
        incident committed edges cluster by the coordinate each implies for it
        under the spanning-forest potential (the strongest cluster keeps the
        word, the runner-up becomes the sense); in an ATTRIBUTE-like group
        with no second coordinate the evidence is role disjointness
        (:meth:`_role_plan` — sources and targets are otherwise disjoint
        populations and only this word plays both parts). Either way the loop
        itself becomes a cross-sense bridge — the sentence that exposed the
        weld survives verbatim, as do all its witnesses. The move is:

          * **evidence-gated** — refused unless the second cluster holds at
            least one committed non-loop edge (a bare reflexive lie posits no
            second concept; it stays a visible defect);
          * **simulated before committed** — each plan runs through
            :func:`~relweblearner.transport.simulate_fission` (cf-flagged on
            the shared bus): commit only if defect mass strictly drops and no
            composable class demotes to a motif;
          * **budgeted** (P7) and **replayable** — a committed split is an
            act entry in the episode log, re-applied as recorded.

        Provenance granularity is per-(src, tgt) pair, so a pair whose frames
        straddle both senses splits imperfectly — the leftover stays a visible
        defect rather than being guessed away. Returns the number of splits.
        """
        done = 0
        tried: set[str] = set()
        while True:
            self._ensure_transports()
            plan = self._fission_candidate(tried)
            if plan is None:
                break
            tried.add(plan["node"])
            if len(self.fission_events) >= self.fission_budget:
                self._refuse_fission(plan["word"], "fission budget exhausted")   # P7: refusal, not corruption
                break
            moves = {(s, t): (s2, t2) for s, t, s2, t2 in plan["moved"]}
            verdict = TR.simulate_fission(self._cmaps, moves, self.exception_fraction,
                                          journal=self.bus, name=self.id)
            if not verdict["commit"]:
                self._refuse_fission(plan["word"], verdict["reason"])
                continue
            event = {"move": "fission", "word": plan["word"], "sense": plan["sense"],
                     "moved": [list(m) for m in plan["moved"]]}
            # a committed move is a log entry like any episode (invariant #5)
            self.log_position = self.log.append({"kind": "act", **event}) + 1
            self._apply_act(event)
            self._trace("fission", {plan["word"]}, {plan["sense"]})
            done += 1
        self._trace("senses", {f"tried:{len(tried)}"}, {f"split:{done}"})
        return done

    def _fission_candidate(self, tried: set) -> dict | None:
        """The first self-loop defect (deterministic scan order) whose node
        admits a partition plan; loops with no independent second-cluster
        evidence are refused on the record and skipped."""
        for _gid, web in sorted(self._group_webs.items()):
            phi = potential(web)
            for d in sorted(web_defects(web, phi), key=lambda d: d.edge.eid):
                w = d.edge.u
                if d.edge.v != w or w in tried:
                    continue
                plan = self._fission_plan(web, phi, w)
                if plan is not None:
                    return plan
                tried.add(w)
                self._refuse_fission(w, "no independent evidence for a second sense")
        return None

    @staticmethod
    def _potential_without(web: TR.Web, w: str) -> tuple[dict, dict]:
        """Spanning-forest potential of the web WITH ``w`` REMOVED, plus each
        node's component root. The full-web potential routes THROUGH ``w``, so
        a wrong-sense edge can contaminate its neighbours' coordinates and
        hide the second cluster; excluding ``w`` makes every incident edge's
        implied coordinate independent testimony about where ``w`` sits."""
        from collections import deque
        algebra = web.algebra
        phi: dict = {}
        comp: dict = {}
        for root in sorted(web.nodes, key=repr):
            if root == w or root in phi:
                continue
            phi[root] = algebra.identity
            comp[root] = root
            dq = deque([root])
            while dq:
                u = dq.popleft()
                for v, value, _eid in web.neighbors(u):
                    if v == w or v in phi:
                        continue
                    p = algebra.compose(phi[u], value)
                    if p is None:
                        continue
                    phi[v] = p
                    comp[v] = root
                    dq.append(v)
        return phi, comp

    def _fission_plan(self, web: TR.Web, phi: dict, w: str) -> dict | None:
        """Partition ``w``'s incident committed edges by the coordinate each
        implies for ``w`` under the potential-without-``w``. Coordinates only
        compare within one connected component (across components they are
        separate gauges — and two senses bridged ONLY by ``w`` bend the
        potential freely, so they are not in contradiction and must not
        split). The strongest cluster keeps the word, the runner-up in the
        SAME component becomes the sense; a pair moves only when every edge
        it carries in this group agrees (a multi-class pair must not be
        torn). The loop pair is oriented so its transport points from the
        kept coordinate to the moved one when that closes, and bridges by
        default otherwise (the simulation arbitrates)."""
        phi2, comp = self._potential_without(web, w)
        implied: dict[tuple, set] = {}       # non-loop (u, v) pair -> (comp, coord) implied for w
        loops = []
        for e in web.edges():
            if e.u == w and e.v == w:
                loops.append(e)
            elif e.u == w and e.v in phi2:
                implied.setdefault((e.u, e.v), set()).add((comp[e.v], phi2[e.v] - e.value))
            elif e.v == w and e.u in phi2:
                implied.setdefault((e.u, e.v), set()).add((comp[e.u], phi2[e.u] + e.value))
        if not loops:
            return None
        coord_of = {p: next(iter(cs)) for p, cs in implied.items() if len(cs) == 1}
        votes = Counter(coord_of.values())
        gauge = phi.get(w)                   # the full-web coordinate, for the tie-break
        ranked = sorted(votes, key=lambda cc: (-votes[cc], cc[1] != gauge, cc))
        second = next((cc for cc in ranked[1:] if cc[0] == ranked[0][0]), None)
        if second is None:
            return self._role_plan(web, w)   # no second coordinate: try the attribute-class variant
        base = ranked[0]
        sense = self._fresh_sense(w)
        moved = [(s, t, sense if s == w else s, sense if t == w else t)
                 for (s, t), cc in sorted(coord_of.items()) if cc == second]
        g = loops[0].value
        if second[1] + g == base[1] and base[1] + g != second[1]:
            moved.append((w, w, sense, w))   # the moved sense sits one step BELOW the kept one
        else:
            moved.append((w, w, w, sense))
        return {"node": w, "word": self._desense(w), "sense": sense, "moved": moved}

    def _role_plan(self, web: TR.Web, w: str) -> dict | None:
        """The attribute-class variant of the partition, where coordinates
        carry no evidence (unconstrained classes — the fruit→colour shape of
        ``a orange is orange``). There the second-sense evidence is ROLE
        DISJOINTNESS: the group's committed sources and targets are otherwise
        disjoint populations (fruits vs colours), and only ``w`` plays both
        parts. Split by role — the source occurrence keeps the word (the
        pictured referent side), every target occurrence becomes the sense.
        A group whose roles genuinely overlap (a chain: numbers on both
        sides) yields no plan, so a bare reflexive lie stays a defect."""
        src: set = set()
        tgt: set = set()
        pairs: set = set()
        for e in web.edges():
            if e.u == e.v:
                continue
            pairs.add((e.u, e.v))
            src.add(e.u)
            tgt.add(e.v)
        if len(pairs) < self.min_shared:     # the evidence bar, in the role dimension
            return None
        if not (src - {w}) or not (tgt - {w}) or (src - {w}) & (tgt - {w}):
            return None
        sense = self._fresh_sense(w)
        moved = [(u, w, u, sense) for (u, v) in sorted(pairs) if v == w]
        moved.append((w, w, w, sense))
        return {"node": w, "word": self._desense(w), "sense": sense, "moved": moved}

    # ============================================================= transport / algebra
    #
    # The algebra layer: the SAME frozen machinery the phase experiments run on
    # (:mod:`~relweblearner.transport` wraps sectors/web/holonomy/growth), fed by
    # the streamed store. Everything here is DERIVED from the geometry — rebuilt
    # lazily whenever a fact, class or retraction changes it — never stored.

    # ============================================================= trust (invariant #6, weighted)
    #
    # Commitment stops counting witnesses and starts WEIGHING them. Each source
    # carries a learned, per-relation-class weight (:mod:`~relweblearner.trust`):
    # 1.0 fresh, below 1.0 once caught wrong there (its word needs more
    # corroboration), ``commit_k`` after a long clean corroborated record there
    # (earned authority — sole-witness commitment in that class only). With no
    # track record anywhere this reduces exactly to the old k-distinct-sources
    # rule. The record is a PROJECTION of store + log exclusions — reproducible
    # by replay, revised by rebuild, never checkpointed.

    def _ensure_trust(self) -> None:
        """(Re)build the per-(source, relation class) track records when stale:
        good = distinct standing facts independently corroborated (raw distinct-
        source count — trust is EARNED against the uncorroded rule, so the weights
        never feed their own definition); bad = distinct facts among the log's
        excluded episodes, parsed under current frames. The log is scanned only
        when exclusions exist; fiat namespaces are decree, not reputation, and
        stay out of the ledger."""
        if self._trust is not None:
            return
        rel_of = self._rel_of()
        good: dict[tuple[str, str], set] = {}
        for s, t, info in self.edges.iter_edges():
            srcs = info.get("sources", {})
            if len(srcs) < self.commit_k:
                continue
            classes = {rel_of.get(fid, fid) for fid in info.get("frames", ())}
            for so in srcs:
                if TU.is_fiat(so):
                    continue
                for cl in classes:
                    good.setdefault((so, cl), set()).add((s, t))
        bad: dict[tuple[str, str], set] = {}
        excluded = self.log.excluded()
        if excluded:
            for seq, entry in self.log.entries(0):
                if seq not in excluded or entry.get("kind") != "world":
                    continue
                so = entry.get("source", "stream")
                if TU.is_fiat(so):
                    continue
                r = C.parse(list(entry.get("tokens", ())), self.frames)
                if r is None or len(r[1]) != 2 or not self._fact_ok(r[1]):
                    continue
                fid, fillers = r
                pic = (entry.get("picture") or "").strip().lower() or None
                fact = C._orient(fillers, pic) if pic else tuple(fillers)
                bad.setdefault((so, rel_of.get(fid, fid)), set()).add(fact)
        self._trust = {k: (len(good.get(k, ())), len(bad.get(k, ())))
                       for k in set(good) | set(bad)}

    def source_weight(self, source: str, relclass: str | None) -> float:
        """The witness weight ``source``'s testimony carries in ``relclass``."""
        if TU.is_fiat(source):
            return float(self.commit_k)
        self._ensure_trust()
        g, b = self._trust.get((source, relclass), (0, 0))
        return TU.weight(g, b, commit_k=self.commit_k,
                         authority_k=self.authority_k, penalty=self.distrust_penalty)

    def _edge_support(self, info: dict, rel_of: dict[str, str]) -> float:
        """Trust-weighted support for one edge: the sum over its sources of each
        source's best weight across the edge's relation classes (provenance is
        per-(edge, source), not per-frame — the store's stated granularity)."""
        classes = [rel_of.get(fid, fid) for fid in info.get("frames", ())] or [None]
        return sum(max(self.source_weight(so, cl) for cl in classes)
                   for so in info.get("sources", ()))

    def _committed_info(self, info: dict, rel_of: dict[str, str] | None = None) -> bool:
        """The commitment predicate (invariant #6, trust-weighted): believed iff
        the weighted support reaches ``commit_k``. Fiat sources (``act:*`` posits
        gated by the growth discipline; ``correction*`` decrees) carry
        ``commit_k`` each, so any one of them suffices — as before."""
        if rel_of is None:
            rel_of = self._rel_of()
        return self._edge_support(info, rel_of) >= self.commit_k - 1e-9

    def _num_committed(self) -> int:
        """Weighted-committed census (the metric retraction reports move by)."""
        rel_of = self._rel_of()
        return sum(1 for _s, _t, info in self.edges.iter_edges()
                   if self._committed_info(info, rel_of))

    def _committed_edges(self, limit: int | None = None) -> list[tuple[str, str, dict]]:
        """The weighted-committed edges, sorted — the creature-level counterpart
        of ``EdgeStore.committed`` (which pre-dates trust and counts raw distinct
        sources; that remains the store-level fast path where weights cannot
        matter). O(edges) scan, honestly: weighting is a creature-level judgment."""
        rel_of = self._rel_of()
        out = [(s, t, info) for s, t, info in self.edges.iter_edges()
               if self._committed_info(info, rel_of)]
        out.sort(key=lambda r: (r[0], r[1]))
        return out[:limit] if limit is not None else out

    def _class_label(self, relclass: str) -> str:
        """A human-readable name for a relation class: its first template."""
        tpl = sorted(f.template for fid, f in self.frames.items()
                     if self._rel_find(fid) == relclass)
        return tpl[0] if tpl else relclass

    def trust_report(self, limit: int | None = 60) -> list[dict]:
        """The learned discrimination, legible: every (source, relation class)
        with a track record — good/bad marks, weight, standing — most deviant
        from ordinary first. This is what "taking a source with a grain of
        salt" looks like from outside."""
        self._ensure_trust()
        rows = []
        for (so, cl), (g, b) in self._trust.items():
            w = self.source_weight(so, cl)
            standing = ("authoritative" if w >= self.commit_k - 1e-9
                        else "distrusted" if w < 1.0 - 1e-9 else "ordinary")
            rows.append({"source": so, "class": self._class_label(cl),
                         "class_id": cl, "good": g, "bad": b,
                         "weight": round(w, 3), "standing": standing})
        rows.sort(key=lambda r: (-abs(1.0 - r["weight"]), r["source"], r["class_id"]))
        rows = rows[:limit] if limit is not None else rows
        self._trace("trust", {"trust"}, {f"records:{len(rows)}"})
        return rows

    def _web_eligible(self, info: dict, rel_of: dict[str, str] | None = None) -> bool:
        """An edge enters the valued web if it is committed testimony under the
        trust-weighted rule above, which subsumes the two old gates: >= commit_k
        ordinary witnesses, or one of the learner's own act-sourced posits
        (structure committed by the growth discipline needs no corroboration —
        the fork-scored search already gated it)."""
        return self._committed_info(info, rel_of)

    def _class_maps(self) -> dict[str, set]:
        """Relation class → eligible ``(source, target)`` pairs, via the frames
        each edge was expressed in. One full-store scan, O(facts) = O(world)."""
        rel_of = self._rel_of()
        two_slot = {fid for fid, f in self.frames.items() if f.n_slots == 2}
        out: dict[str, set] = {}
        for s, t, info in self.edges.iter_edges():
            if not self._web_eligible(info, rel_of):
                continue
            for fid in info.get("frames", ()):
                if fid in two_slot:
                    out.setdefault(rel_of.get(fid, fid), set()).add((s, t))
        return out

    def _ensure_transports(self) -> None:
        """(Re)infer class transports and rebuild the group webs if stale."""
        if self._sectors is not None:
            return
        cmaps = self._class_maps()
        sectors, groups = TR.infer(cmaps, self.exception_fraction)
        webs = TR.build_group_webs(cmaps, sectors, groups, name=self.id)
        bad = TR.non_homogeneous_by_defect(cmaps, webs, self.exception_fraction)
        if bad:                                   # the P2 `double` verdict: demote to motif
            for r in bad:
                old = sectors[r]
                sectors[r] = TR.RelationSector(r, TR.NON_HOMOGENEOUS, None, old.support, old.n_samples)
            webs = TR.build_group_webs(cmaps, sectors, groups, name=self.id)
        self._cmaps, self._rel_groups, self._group_webs = cmaps, groups, webs
        # the motif layer shares the projection's staleness: inheritance rules
        # are re-scored off the same committed class maps, each candidate
        # verdict cf-flagged on the shared bus (imagined, on the record).
        self._motifs = MO.induce(cmaps, self.commit_k, self.exception_fraction,
                                 journal=self.bus)
        self._sectors = sectors

    def concept_webs(self) -> dict[str, TR.Web]:
        """The algebra-valued concept web: one :class:`~relweblearner.web.Web`
        per constraint group (groups are mutually ungauged — P4′)."""
        self._ensure_transports()
        self._trace("webs", {"concept-webs"}, {f"groups:{len(self._group_webs)}"})
        return dict(self._group_webs)

    def defects(self) -> dict:
        """Nonzero-holonomy census over the concept webs — invariant #9's
        learning signal, visible again: a committed contradiction is a loop
        that fails to close, not just a lookup anomaly."""
        self._ensure_transports()
        rep = TR.defect_report(self._group_webs)
        self._trace("defects", {"defects"}, {f"count:{rep['count']}", f"mass:{rep['mass']}"})
        return rep

    def _sector_rows(self) -> list[dict]:
        """Per-relation-class sector report for the snapshot."""
        self._ensure_transports()
        by_class: dict[str, list[str]] = {}
        for fid, f in self.frames.items():
            by_class.setdefault(self._rel_find(fid), []).append(f.template)
        return [
            {"class": r, "sector": s.sector, "transport": s.transport,
             "support": round(s.support, 3), "edges": s.n_samples,
             "templates": sorted(by_class.get(r, []))}
            for r, s in sorted((self._sectors or {}).items())
        ]

    def _motif_rows(self) -> list[dict]:
        """Scored inheritance rules for the snapshot, committed first, voiced
        through each class's constructions so the display reads as language."""
        self._ensure_transports()
        by_class: dict[str, list[str]] = {}
        for fid, f in self.frames.items():
            by_class.setdefault(self._rel_find(fid), []).append(f.template)
        return [
            {"rel": r.rel, "via": r.via,
             "rel_templates": sorted(by_class.get(r.rel, [])),
             "via_templates": sorted(by_class.get(r.via, [])),
             "witnesses": r.witnesses, "violations": r.violations,
             "support": round(r.support, 3), "committed": r.committed}
            for r in self._motifs
        ]

    def _numbers_census(self) -> dict:
        """The number sense, reported: chain length, named positions, map
        status, and its defects (contradiction self-loops, poison namings)."""
        ch = self.numbers.chain()
        maps = self._number_maps() if ch.order else []
        m = maps[0] if maps else None
        pos = {rep: i + 1 for i, rep in enumerate(ch.order)}
        return {
            "classes": len(ch.order),
            "contradictions": [list(x) for x in ch.contradictions],
            "map": None if m is None else {
                "orientation": m["s"], "offset": m["c"],
                "named": {w: pos[rep] for w, rep in sorted(m["class_of"].items())
                          if rep in pos},
                "poison": len(m["poison"]), "conflicts": m["conflicts"],
            },
        }

    def _fresh_concept(self) -> str:
        """A durable opaque id for a posited concept. Hyphenated, so it can
        never collide with a tokenised surface word."""
        name = f"new-{self.grown_seq}"
        self.grown_seq += 1
        return name

    def _render_via(self, fact: tuple, frame_id: str) -> str | None:
        """Voice a fact that has no stored edge (derived/posited) through the
        question's own relation class, read back before returning."""
        st = self._state_for([])
        st["fact_frames"] = {fact: {frame_id}}
        return T.render_fact(fact[0], fact[1], st)

    def _think(self, res: dict) -> dict:
        """Push a parsed question through the ALGEBRA when lookup is not enough.

        The talk layer only returns facts the creature was told. Thinking is
        transport: compose committed edge values through the question's
        constraint group; a node at the class transport is a DERIVED answer —
        believed because the structure entails it, not because anyone said it
        (P3, zero shot). A derivable question with no witnessing node is the
        P1 walk-off obstruction: relabel is demonstrated futile, a fork-scored
        rewire is tried, and only a persistent obstruction pays for growth —
        the posited ``new-*`` node is the learner's own negative-number move
        (P1b), budgeted against query floods (P7: degrade to refusal).
        TRANSPORT derivation runs only on ANTISYMMETRIC classes: an
        unconstrained class's transport is pure gauge, and deriving along it
        would be the P4 "algebra too strong" hallucinated inverse. A question
        transport cannot touch may still be entailed by a committed MOTIF
        (:mod:`~relweblearner.motif`): the inheritance word ``rel ⊇ via ∘
        rel`` walks taught edges end to end (``hen -kind of-> bird -has
        legs-> two``), carrying testimony the whole way, so it needs no
        transport and answers on ANY sector — the layer for the attribute
        classes that never accrue converse loops."""
        qclass, given, forward = res.get("rel_class"), res.get("given"), res.get("forward", True)
        if qclass is None or given is None:
            return res
        for a in res["answers"]:                  # posited structure is not testimony
            fact = (given, a["answer"]) if forward else (a["answer"], given)
            info = self.edges.get(*fact)
            if info and info["sources"] and all(str(s).startswith("act:") for s in info["sources"]):
                a["status"] = "grown"
        if any(a["status"] == "committed" for a in res["answers"]):
            return res
        self._ensure_transports()
        sector = (self._sectors or {}).get(qclass)
        web = self._group_webs.get(self._rel_groups.get(qclass)) if sector else None
        antisym = sector is not None and sector.sector == TR.ANTISYMMETRIC and web is not None
        if antisym:
            target = sector.transport if forward else web.algebra.dagger(sector.transport)
            seen = {self._desense(a["answer"]) for a in res["answers"]}
            for start in self._sense_variants(given):
                for n in TR.derive(web, start, target, max_depth=self.derive_depth):
                    n = self._desense(n)                # a derived sense voices as its word
                    if n in seen:
                        continue
                    seen.add(n)
                    fact = (given, n) if forward else (n, given)
                    res["answers"].append({"answer": n, "status": "derived",
                                           "sentence": self._render_via(fact, res["frame"])})
            if not res["answers"]:
                # the word web cannot answer: try the P5 interface — step along
                # the CONSTRUCTED number chain instead (order learned from
                # counting piles, not from sentences), voicing through the
                # question's frame.
                w = self._interface_answer(qclass, given, forward, sector, web)
                if w is not None:
                    fact = (given, w) if forward else (w, given)
                    res["answers"].append({"answer": w, "status": "derived", "via": "counting",
                                           "sentence": self._render_via(fact, res["frame"])})
        if not res["answers"]:
            self._motif_answers(res, qclass, given, forward)
        if not res["answers"] and antisym and given in web.nodes:
            self._probe_growth(res, web, qclass, given, forward)
        rank = {"committed": 0, "derived": 1, "provisional": 2, "grown": 3, "rewired": 3}
        res["answers"].sort(key=lambda a: rank.get(a["status"], 4))
        res["known"] = bool(res["answers"])
        return res

    def _interface_answer(self, qclass, given, forward, sector, web) -> str | None:
        """One word-order step routed through the constructed chain: word →
        class (the committed interface map) → ``s·t`` successor steps → class →
        word. Answers exist here that the word web cannot reach — a word known
        only from ostension has no order edge, but its CLASS has a position."""
        m = self.numbers.map(potential(web))
        if m is None:
            return None
        t = sector.transport if forward else web.algebra.dagger(sector.transport)
        return self.numbers.word_step(m, potential(web), given, t)

    def _motif_answers(self, res: dict, qclass: str, given: str, forward: bool) -> None:
        """Inheritance along committed motif rules (:mod:`~relweblearner.motif`):
        a learned concept is a WORD over existing edges, never a new algebra
        operation (invariant #1), so ``hen -kind of-> bird -has legs-> two``
        answers the never-taught ``hen has ? legs`` with committed testimony
        carried end to end. Nothing is reified — the answer is derived at query
        time and voiced through the question's own frame, with the walked chain
        attached as its justification. Forward questions only: a reverse blank
        is already answered by its committed direct holders, and enumerating
        every inheritor below them is an unbounded scan (P7: refuse)."""
        if not forward:
            return
        for h in MO.derive(self._motifs, self._cmaps, qclass, given,
                           max_depth=self.derive_depth):
            a = self._desense(h["answer"])              # an inherited sense voices as its word
            fact = (given, a)
            res["answers"].append({"answer": a, "status": "derived",
                                   "via": "motif", "through": h["through"],
                                   "sentence": self._render_via(fact, res["frame"])})
            self._trace("inherit", {given, *h["through"]}, {a})

    def _number_maps(self) -> list[dict]:
        """Every committed interface map across the gauge groups, BEST first —
        ranked by coordinate-consistent identifications. Number words recur as
        fillers of unrelated relations (``a triangle has three sides``), whose
        group can accidentally commit a k-word map; ranking keeps the real
        chain's map (all words consistent, no poison) ahead of coincidences."""
        self._ensure_transports()
        maps = [m for _gid, web in sorted(self._group_webs.items())
                if (m := self.numbers.map(potential(web))) is not None]
        maps.sort(key=lambda m: (-len(m["consistent"]), -len(m["word_of"])))
        return maps

    def how_many(self, members) -> dict:
        """Number a pile of opaque objects with the creature's own ruler: the
        P1b counting routine gives the class, the P5 interface map gives the
        word. Answerable exactly as far as the chain is built and named."""
        counted = self.numbers.count_fresh(members)
        word = None
        if counted is not None:
            for m in self._number_maps():
                word = m["word_of"].get(counted[1])
                if word is not None:
                    break
        self._trace("how-many",
                    {f"position:{counted[0]}"} if counted else {"off-chain"},
                    {word or "unnamed"})
        return {"known": word is not None, "word": word,
                "position": counted[0] if counted else None}

    def _probe_growth(self, res: dict, web: TR.Web, qclass: str, given: str, forward: bool) -> None:
        """The P1 engine on the question's group web; a committed move is
        persisted to the store under the reserved ``act:`` namespace. The
        engine's micro-moves (fork relabels, trial rewires, walks) ride the
        group web's own journal; the creature-level probe and outcome are what
        land on the shared bus."""
        self._trace("probe", {given}, {qclass})
        if len(self.growth_events) >= self.growth_budget:
            res["refused"] = "growth budget exhausted"        # P7: refusal, not corruption
            self._trace("refuse", {given}, {"budget"})
            return
        engine = TR.SectorGrowth(self.growth_persistence, self._fresh_concept)
        a = engine.answer(web, given, qclass if forward else qclass + "~", 1)
        if a.endpoint is None or a.endpoint == given:
            return
        fact = (given, a.endpoint) if forward else (a.endpoint, given)
        move = "grow" if a.grew else "rewire"
        event = {
            "move": move, "class": qclass, "given": given, "forward": forward,
            "answer": a.endpoint, "rounds": a.rounds_survived,
            "new_nodes": list(a.grew.new_nodes) if a.grew else [],
            # frame IDS are induction-order-dependent, so a replay under a
            # different exclusion set may renumber them; the anchor words are
            # the stable name of the relation and let replay re-resolve it.
            "anchors": list(self.frames[qclass].anchors) if qclass in self.frames else [],
        }
        # a committed move is a log entry like any episode (invariant #5): replay
        # re-APPLIES it as recorded — a commitment, not a re-derivation.
        self.log_position = self.log.append({"kind": "act", **event}) + 1
        self._apply_act(event)
        self._trace(move, {given}, {a.endpoint})
        res["answers"].append({"answer": a.endpoint,
                               "status": "grown" if a.grew else "rewired",
                               "sentence": self._render_via(fact, res["frame"])})

    # ============================================================= belief / queries

    def _status(self, fact: tuple) -> str:
        e = self.edges.get(*fact)
        if e is None:
            return "unknown"
        if e["sources"] and all(str(s).startswith("act:") for s in e["sources"]):
            return "grown"
        return "committed" if self._committed_info(e) else "provisional"

    def _state_for(self, edges: list) -> dict:
        """A talk-back state (see :mod:`~relweblearner.talk`) over ONLY the given
        edges ``(src, tgt, info)`` — a neighbourhood, never the whole web. Frames
        and slot orientation are bounded and always in memory."""
        rel_of = self._rel_of()
        facts, committed, fact_frames = {}, set(), {}
        for s, t, info in edges:
            facts[(s, t)] = info["sources"]
            fact_frames[(s, t)] = info["frames"]
            if self._committed_info(info, rel_of):
                committed.add((s, t))
        return {"frames": self.frames, "facts": facts, "committed": committed,
                "source_slot": self.source_slot, "fact_frames": fact_frames,
                "rel_of": rel_of}

    def about(self, referent: str) -> dict:
        r = referent.strip().lower()
        rows = [(v, t, i) for v in self._sense_variants(r) for t, i in self.edges.out_edges(v)]
        res = T.about(self._state_for(self._surface_edges(rows)), r)
        self._trace("about", {r}, {f"beliefs:{len(res['beliefs'])}"})
        return res

    def answer(self, phrase: str) -> dict:
        from .reader import tokenize
        tokens = tokenize(phrase)
        # load the neighbourhood of each content token (the given filler is among
        # them) — indexed lookups, not a full-web scan. A split word's senses are
        # part of its neighbourhood, collapsed back to the surface for talk-back:
        # both senses answer, distinction kept internal.
        content = [t for t in tokens if t not in ("?", "_") and not self._is_anchor(t)]
        edges = []
        for tok in content:
            for v in self._sense_variants(tok):
                edges += [(v, t, i) for t, i in self.edges.out_edges(v)]
                edges += [(s, v, i) for s, i in self.edges.in_edges(v)]
        res = T.answer(self._state_for(self._surface_edges(edges)), tokens)
        if res.get("kind") == "answer":
            res = self._think(res)                # lookup first, then transport (P3/P1)
            marks = ({f"{a['status']}:{a['answer']}" for a in res["answers"][:3]}
                     or {"unknown"})
            self._trace("answer", {res.get("given") or "?"}, marks)
            if not res.get("known"):
                self._mint_wonder(res, tokens)    # a parsed miss goes on the record (PQ)
        else:
            self._trace("answer", {"?"}, {res.get("kind", "unparsed")})
        return res

    def _mint_wonder(self, res: dict, tokens: list[str]) -> None:
        """A parsed question the creature could not answer becomes an open
        WONDER on the episode log (spec-curiosity §1a) — the seed of the
        curiosity ledger, which :mod:`~relweblearner.curiosity` projects and a
        wonder tick batch-answers. Only parsed misses mint (junk that matches
        no frame never reaches here); the wid is stable across replays (built
        from the given filler + the frame's anchor words, never a frame id);
        re-asking dedups; a resolved wid never reopens; and past ``wonder_cap``
        open unknowns, minting is refused on the record (P7: refusal, not a
        flood)."""
        given, fid = res.get("given"), res.get("frame")
        if given is None or fid not in self.frames:
            return
        anchors = list(self.frames[fid].anchors)
        wid = f"u:{given}:{'-'.join(anchors)}"
        if wid in self.wonder_events or wid in self.resolved_wonders:
            return
        n_open = sum(1 for w in self.wonder_events if w not in self.resolved_wonders)
        if n_open >= self.wonder_cap:
            self._trace("refuse", {given}, {"wonder-cap"})
            return
        event = {"move": "wonder", "wid": wid, "qkind": "unknown", "subject": given,
                 "anchors": anchors, "phrase": " ".join(tokens)}
        self.log_position = self.log.append({"kind": "act", **event}) + 1
        self._apply_act(event)
        self._trace("wonder", {given}, {wid})


    def _is_anchor(self, tok: str) -> bool:
        return any(tok in f.anchors for f in self.frames.values())

    def say(self, referent: str | None = None, limit: int = 20) -> list[dict]:
        if referent is not None:
            r = referent.strip().lower()
            edges = [(v, t, i) for v in self._sense_variants(r) for t, i in self.edges.out_edges(v)]
        else:
            edges = self._committed_edges(limit=max(limit * 3, limit))
        out = T.say(self._state_for(self._surface_edges(edges)), referent, limit)
        self._trace("say", {referent or "*"}, {f"sentences:{len(out)}"})
        return out

    # ============================================================= retraction

    def retract_source(self, source: str) -> dict:
        """Un-observe everything ``source`` taught — a decrement-join over the
        edge aggregates, no episode log consulted. This is the FAST PATH (and
        the only path under a NullEpisodeLog); within the source cap it agrees
        with replay-with-exclusions over the source's episodes, which remains
        the ground truth (:meth:`retract_episodes`).

        Belief here is a monotone join of per-source summands, so retraction is
        subtraction: remove ``source``'s tally from each edge it touched, and drop
        any edge left with no provenance. A k-source collusion un-commits the
        moment one colluder is retracted (its distinct-source count falls below
        ``commit_k``); every honestly-multiply-sourced fact is untouched.

        Granularity is (source, claim), not per-episode — that WAS an episode's
        whole epistemic content — so "this source was wrong" retracts cleanly,
        while "this one page of an otherwise-good source was wrong" does not."""
        before = self._num_committed()
        touched = self.edges.retract_source(source)
        namings = self.numbers.retract_source(source)   # the naming table decrements too
        after = self._num_committed()
        self._sectors = None                        # geometry changed; transports are stale
        self._trust = None
        self._trace("retract-source", {source}, {f"touched:{touched + namings}"})
        return {"source": source, "edges_touched": touched, "namings_touched": namings,
                "committed_before": before, "committed_after": after,
                "uncommitted": before - after}

    # ============================================================= metrics / snapshot

    def snapshot(self, committed_limit: int = 200) -> dict:
        self._trace("snapshot", {"snapshot"}, {f"episodes:{self.episodes_seen}"})
        total = self.parsed + self.unparsed
        n_edges = self.edges.num_edges()
        rel_of = self._rel_of()
        all_edges = sorted(self.edges.iter_edges(), key=lambda r: (r[0], r[1]))
        commed = [e for e in all_edges if self._committed_info(e[2], rel_of)]
        n_committed = len(commed)
        committed_edges = commed[:committed_limit]
        st = self._state_for(committed_edges)   # render only the shown committed facts
        # provisional = edges seen but below the (trust-weighted) commitment
        # threshold; the creature reports its own uncommitted geometry (bounded)
        prov_edges = [e for e in all_edges
                      if not self._committed_info(e[2], rel_of)][:committed_limit]
        prov_st = self._state_for(prov_edges)
        return {
            "identity": {"name": self.name, "id": self.id, "created": self.created, "level": self.level},
            "episodes_seen": self.episodes_seen,
            "log": {"entries": len(self.log), "position": self.log_position,
                    "excluded": len(self.log.excluded())},
            "model_size": {
                "nodes": self.edges.num_nodes(),
                "frames": len(self.frames),
                "facts": n_edges,
                "frontier_clusters": len(self.frontier),
                "buffer": len(self._buffer),
            },
            "coverage": round(self.parsed / total, 3) if total else 0.0,
            "assimilation_rate": round(n_committed / self.episodes_seen, 4) if self.episodes_seen else 0.0,
            "frames": [
                {"id": f.id, "template": f.template, "anchors": list(f.anchors), "n_slots": f.n_slots}
                for f in sorted(self.frames.values(), key=lambda fr: fr.id)
            ],
            "relations": self._relation_classes(),
            "relations_refused": self.refused_merges[-8:],
            "sectors": self._sector_rows(),
            "motifs": self._motif_rows(),
            "trust": self.trust_report(limit=40),
            "defects": self.defects(),
            "growth": {"count": len(self.growth_events), "budget": self.growth_budget,
                       "events": self.growth_events[-10:]},
            "senses": {w: list(v) for w, v in sorted(self.senses.items())},
            "senses_refused": self.refused_fissions[-8:],
            "fissions": {"count": len(self.fission_events), "budget": self.fission_budget,
                         "events": [{"word": e["word"], "sense": e["sense"],
                                     "moved": len(e["moved"])}
                                    for e in self.fission_events[-10:]]},
            "numbers": self._numbers_census(),
            "bus": vars(self.bus.counts()).copy(),
            "ledger": {"read_sources": sorted(self.read_sources),
                       "passed_stages": sorted(self.passed_stages)},

            "committed": [
                {"source": s, "target": t, "sources": sorted(info["sources"]), "sentence": T.render_fact(s, t, st)}
                for (s, t, info) in committed_edges
            ],
            "committed_count": n_committed,
            "provisional": [
                {"source": s, "target": t, "sources": sorted(info.get("sources", [])),
                 "sentence": T.render_fact(s, t, prov_st)}
                for (s, t, info) in prov_edges
            ],
            "provisional_count": n_edges - n_committed,
            "frontier": {str(k): v for k, v in sorted(self.frontier.items())},
        }

    def web_view(self, focus: str | None = None, limit: int = 24) -> dict:
        """A BOUNDED ego-graph of the concept web, for visualisation: the focus
        concept plus its immediate neighbours via the INDEXED out/in edges, capped
        at ``limit``. Scales to any web size because it only ever touches one node's
        neighbourhood — never the whole graph. ``focus=None`` seeds on a committed
        concept so the view is never empty once anything is learned.
        """
        focus = (focus or "").strip().lower() or None
        if focus is None:
            seed = self._committed_edges(limit=1)
            focus = seed[0][0] if seed else None
        self._trace("web-view", {focus or "*"}, {"ego-graph"})
        if focus is None:
            return {"focus": None, "nodes": [], "edges": [], "truncated": False}

        def _rel(info) -> str:
            for fid in sorted(info.get("frames", [])):
                f = self.frames.get(fid)
                if f:
                    return " ".join(f.anchors) or fid
            return "relates"

        out = self.edges.out_edges(focus)
        inn = self.edges.in_edges(focus)
        truncated = len(out) + len(inn) > limit

        rel_of = self._rel_of()
        edges = [{"source": focus, "target": t, "rel": _rel(info),
                  "committed": self._committed_info(info, rel_of)}
                 for (t, info) in out[:limit]]
        room = max(0, limit - len(edges))
        edges += [{"source": s, "target": focus, "rel": _rel(info),
                   "committed": self._committed_info(info, rel_of)}
                  for (s, info) in inn[:room]]

        concepts = {focus}
        for e in edges:
            concepts.update((e["source"], e["target"]))
        nodes = [{"id": c, "focus": c == focus} for c in sorted(concepts)]
        return {"focus": focus, "nodes": nodes, "edges": edges, "truncated": truncated}

    def web_graph(self, max_nodes: int = 240, max_edges: int = 640) -> dict:
        """A view of the WHOLE concept web for visualisation — every concept and
        fact, so the graph shows the mind's actual structure (entities orbiting the
        attribute hubs they share). Bounded for render cost: past ``max_nodes`` it
        keeps the highest-degree CORE (the most-connected concepts) and the edges
        among them, and reports ``truncated`` — "part of the mind" at large scale,
        the full thing while it fits. Each node carries its degree (for sizing) and
        whether it acts mostly as an entity (a source) or an attribute (a target).
        """
        all_edges = list(self.edges.iter_edges())
        outd, ind, deg = Counter(), Counter(), Counter()
        for s, t, _info in all_edges:
            outd[s] += 1
            ind[t] += 1
            deg[s] += 1
            deg[t] += 1
        total_nodes = len(deg)
        self._trace("web-graph", {f"nodes:{total_nodes}"}, {f"edges:{len(all_edges)}"})

        keep = {n for n, _ in deg.most_common(max_nodes)}
        rel_of = self._rel_of()
        edges = []
        for s, t, info in all_edges:
            if s in keep and t in keep:
                edges.append({"source": s, "target": t,
                              "committed": self._committed_info(info, rel_of)})
                if len(edges) >= max_edges:
                    break

        used = set()
        for e in edges:
            used.update((e["source"], e["target"]))
        nodes = [{"id": n, "deg": deg[n],
                  "kind": "entity" if outd[n] >= ind[n] else "attribute"}
                 for n in sorted(used, key=lambda n: -deg[n])]
        return {"nodes": nodes, "edges": edges,
                "truncated": len(nodes) < total_nodes,
                "total_nodes": total_nodes, "total_edges": len(all_edges)}

    def mind_map(self, dim: int = 3) -> dict:
        """The mind's LEARNED GEOMETRY, for visualisation — every concept placed at
        the coordinates the fixed machinery computes for it (a graph-Laplacian
        eigenmap of the concept web), not at a cosmetic layout. Position is meaning:
        relationally-close concepts sit close; a third eigen-coordinate gives each a
        colour along a learned semantic axis. This is the project's thesis made
        visible — *geometry is the data* — and it is why the picture is a latent
        space, not a node-link diagram.

        Embeds the largest CONNECTED component (the coherent core), because the
        Laplacian spectrum is degenerate across disconnected pieces; isolated facts
        drop out rather than scatter noise. Returns normalised points plus the
        within-component edges (drawn only faintly / on hover)."""
        import numpy as np
        from collections import deque

        all_edges = list(self.edges.iter_edges())
        self._trace("mind-map", {f"edges:{len(all_edges)}"}, {f"dim:{dim}"})
        if not all_edges:
            return {"points": [], "edges": [], "note": "nothing learned yet"}

        adj: dict[str, set] = {}
        for s, t, _ev in all_edges:
            adj.setdefault(s, set()).add(t)
            adj.setdefault(t, set()).add(s)

        # largest connected component (BFS)
        seen: set[str] = set()
        best: list[str] = []
        for start in adj:
            if start in seen:
                continue
            comp, stack = [], [start]
            seen.add(start)
            while stack:
                u = stack.pop()
                comp.append(u)
                for v in adj[u]:
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            if len(comp) > len(best):
                best = comp
        if len(best) <= dim + 1:
            return {"points": [], "edges": [], "note": "too small to embed yet"}

        nodes = sorted(best)
        idx = {n: i for i, n in enumerate(nodes)}
        A = np.zeros((len(nodes), len(nodes)))
        outd, ind, deg = Counter(), Counter(), Counter()
        rel_of = self._rel_of()
        comp_edges = []
        for s, t, ev in all_edges:
            if s in idx and t in idx:
                A[idx[s]][idx[t]] += ev["count"]
                A[idx[t]][idx[s]] += ev["count"]
                outd[s] += 1
                ind[t] += 1
                deg[s] += 1
                deg[t] += 1
                comp_edges.append({"s": idx[s], "t": idx[t],
                                   "committed": self._committed_info(ev, rel_of)})

        # Classical MDS on RELATIONAL distance (shortest paths in the web): plot-
        # distance approximates how far apart two concepts are in the creature's
        # relational structure. Unlike the raw Laplacian eigenmap (which localises
        # on this hub-and-spoke web and collapses the core), this spreads the mind
        # into a metric map — the geometry you can actually read.
        n = len(nodes)
        nbr: dict[int, set] = {i: set() for i in range(n)}
        for e in comp_edges:
            nbr[e["s"]].add(e["t"])
            nbr[e["t"]].add(e["s"])
        D = np.full((n, n), float(n))
        for src in range(n):
            dist = [-1] * n
            dist[src] = 0
            dq = deque([src])
            while dq:
                u = dq.popleft()
                for v in nbr[u]:
                    if dist[v] < 0:
                        dist[v] = dist[u] + 1
                        dq.append(v)
            for j in range(n):
                if dist[j] >= 0:
                    D[src][j] = dist[j]

        J = np.eye(n) - np.ones((n, n)) / n
        B = -0.5 * J @ (D ** 2) @ J
        vals, vecs = np.linalg.eigh(B)
        order = np.argsort(vals)[::-1][:3]
        coords = vecs[:, order] * np.sqrt(np.maximum(vals[order], 1e-9))

        def _norm(col):
            lo, hi = float(np.percentile(col, 2)), float(np.percentile(col, 98))
            r = (hi - lo) or 1.0
            return np.clip((col - lo) / r, 0.0, 1.0).tolist()

        xs, ys = _norm(coords[:, 0]), _norm(coords[:, 1])
        cs = _norm(coords[:, 2]) if coords.shape[1] >= 3 else xs
        points = [{"id": nd, "x": xs[i], "y": ys[i], "c": cs[i], "deg": deg[nd],
                   "kind": "entity" if outd[nd] >= ind[nd] else "attribute"}
                  for i, nd in enumerate(nodes)]
        return {"points": points, "edges": comp_edges,
                "n_component": len(nodes), "total_nodes": len(adj),
                "eigenvalues": [float(v) for v in vals[order]]}

    # ============================================================= geometry

    def geometry(self) -> dict:
        """The creature's GEOMETRY — the web, and the whole of what is learned.

        The project's thesis is *intelligence = fixed algebra + geometry*: the
        algebra (composition, holonomy, the three costed moves) is frozen in code;
        the only learned degree of freedom is the WEB — "a graph with fixed-algebra
        edge values" (:mod:`~relweblearner.web`). So the durable state is exactly
        this geometry, never the algebra:

          * **concept web** — nodes (the concepts) and typed, algebra-valued edges
            (the facts): ``src -[rel]-> tgt`` with the frames that express it (the
            relation marker) and its provenance/evidence;
          * **language web** — the induced frames (constructions over the sequence
            web) and each frame's picture-slot orientation.
        """
        edges, node_set = [], set()
        for s, t, ev in sorted(self.edges.iter_edges()):
            node_set.update((s, t))
            edges.append({"src": s, "tgt": t, "rel": sorted(ev["frames"]),
                          "count": ev["count"], "sources": dict(sorted(ev["sources"].items()))})
        self._trace("geometry", {f"nodes:{len(node_set)}"}, {f"edges:{len(edges)}"})
        return {
            "concept_web": {"nodes": sorted(node_set), "edges": edges},
            "language_web": self._language_web(),
        }

    def _language_web(self) -> dict:
        return {
            "frames": {fid: [list(e) for e in f.pattern] for fid, f in self.frames.items()},
            "source_slot": self.source_slot,
            "relations": self._rel_of(),   # frame -> unified relation class
        }

    def embedding(self, dim: int = 2) -> dict:
        """Recover the SPATIAL geometry — graph-Laplacian eigenmap coordinates per
        concept node — from the stored web. The web is stored; this embedding is
        recomputed from it by the fixed machinery (:mod:`~relweblearner.geometry`),
        making concrete that geometry is the data and the algebra is the code."""
        import numpy as np

        from . import geometry as Geo

        all_edges = list(self.edges.iter_edges())
        nodes = sorted({n for s, t, _ in all_edges for n in (s, t)})
        self._trace("embedding", {f"nodes:{len(nodes)}"}, {f"dim:{dim}"})
        if len(nodes) <= dim:
            return {"nodes": nodes, "coords": [], "note": "too few nodes to embed"}
        idx = {n: i for i, n in enumerate(nodes)}
        A = np.zeros((len(nodes), len(nodes)))
        for s, t, ev in all_edges:
            A[idx[s]][idx[t]] += ev["count"]
            A[idx[t]][idx[s]] += ev["count"]
        try:
            emb, vals = Geo.laplacian_eigenmaps(A, dim=dim)
        except Exception as exc:  # disconnected / degenerate spectra
            return {"nodes": nodes, "coords": [], "note": f"not embeddable: {exc}"}
        return {"nodes": nodes, "coords": emb.tolist(), "eigenvalues": vals.tolist()}

    # ============================================================= persistence

    def to_dict(self) -> dict:
        """Serialise identity + GEOMETRY (never the algebra, never the episode
        history). The algebra stays in code; reload rebuilds the web and the fixed
        machinery operates on it again.

        When the edges live in a DURABLE store (SQLite / sharded), the concept
        web is NOT dumped here — its database files are their own persistence,
        and re-serialising O(web) edges into JSON on every save is exactly what
        the store exists to avoid. The checkpoint then records an ``external``
        pointer (the store spec) plus counts, and ``load`` must be handed the
        reopened store."""
        if self.edges.durable:
            geometry = {
                "concept_web": {"external": self.edges.spec or "external",
                                "nodes": self.edges.num_nodes(),
                                "edges": self.edges.num_edges()},
                "language_web": self._language_web(),
            }
        else:
            geometry = self.geometry()
        return {
            "identity": {"name": self.name, "id": self.id, "created": self.created, "level": self.level},
            "algebra": "frozen in code (not stored) — only geometry is persisted",
            "params": {
                "commit_k": self.commit_k, "min_group": self.min_group, "dominance": self.dominance,
                "min_anchors": self.min_anchors, "induction_interval": self.induction_interval,
                "buffer_cap": self.buffer_cap, "max_slot_tokens": self.max_slot_tokens,
                "source_cap": self.source_cap, "exemplar_cap": self.exemplar_cap,
                "authority_k": self.authority_k, "distrust_penalty": self.distrust_penalty,
                "exception_fraction": self.exception_fraction, "derive_depth": self.derive_depth,
                "growth_persistence": self.growth_persistence, "growth_budget": self.growth_budget,
                "fission_budget": self.fission_budget, "wonder_cap": self.wonder_cap,
                "seed": self.seed, "reservoir_stratify": self.reservoir_stratify,
            },
            "counters": {"episodes_seen": self.episodes_seen, "parsed": self.parsed,
                         "unparsed": self.unparsed, "grown_seq": self.grown_seq},
            "growth_events": self.growth_events,
            "fission_events": self.fission_events,
            # the curiosity ledger's distilled state (acts up to log_position;
            # the tail replays through _apply_act like every other act)
            "wonders": {"events": list(self.wonder_events.values()),
                        "sought": dict(self.sought_counts),
                        "parked": sorted(self.parked_wonders),
                        "resolved": dict(self.resolved_wonders)},
            "senses": {w: list(v) for w, v in sorted(self.senses.items())},
            # checkpoint marker (invariant #5): how far into the episode log this
            # state has distilled — load() replays whatever tail lies beyond it.
            "log_position": self.log_position,
            "ledger": {"read_sources": sorted(self.read_sources),    # registry ids already ingested (incremental training)
                       "passed_stages": sorted(self.passed_stages)}, # curriculum stages mastered (worksheet passed)
            "geometry": geometry,
            "frontier": {str(k): v for k, v in self.frontier.items()},
            # induction reservoir + stream counter + RNG state, so a checkpoint
            # resumed with a tail replay is identical to the uninterrupted run
            "working": {"buffer": self._buffer, "buffer_seen": self._buffer_seen,
                        "rng": self._rng_state()},
        }

    def _rng_state(self) -> list:
        st = self._rng.getstate()
        return [st[0], list(st[1]), st[2]]

    def save(self, path: str | Path) -> None:
        """Checkpoint atomically: flush the store and log first (a checkpoint
        must never point past durable state), write a sibling temp file, then
        ``os.replace`` — a crash mid-save leaves the previous checkpoint whole.
        Each save is stamped with when/what produced it (git SHA, curriculum
        hash) so any state file is traceable to the code and syllabus behind it."""
        self.commit()
        d = self.to_dict()
        from .version import stamp  # local import: version imports this module
        d["provenance"] = stamp()
        path = Path(path)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, path)

    @classmethod
    def from_dict(cls, d: dict, log: EpisodeLog | None = None,
                  store: EdgeStore | None = None) -> "Creature":
        idy, p = d["identity"], d["params"]
        c = cls(idy["name"], created=idy.get("created"), level=idy.get("level"),
                log=log, store=store, **p)
        cnt = d["counters"]
        c.episodes_seen, c.parsed, c.unparsed = cnt["episodes_seen"], cnt["parsed"], cnt["unparsed"]
        c.grown_seq = cnt.get("grown_seq", 0)
        c.growth_events = list(d.get("growth_events", []))
        c.fission_events = list(d.get("fission_events", []))
        wo = d.get("wonders", {})
        c.wonder_events = {e["wid"]: dict(e) for e in wo.get("events", [])}
        c.sought_counts = {k: int(v) for k, v in wo.get("sought", {}).items()}
        c.parked_wonders = set(wo.get("parked", []))
        c.resolved_wonders = dict(wo.get("resolved", {}))
        c.senses = {w: list(v) for w, v in d.get("senses", {}).items()}
        c._sense_ids = {sid for v in c.senses.values() for sid in v}
        geo = d["geometry"]
        lang = geo["language_web"]
        c.frames = {fid: C.Frame(fid, tuple(tuple(e) for e in pat)) for fid, pat in lang["frames"].items()}
        c.source_slot = {k: int(v) for k, v in lang["source_slot"].items()}
        c._rel_parent = {fid: root for fid, root in lang.get("relations", {}).items()}
        cw = geo["concept_web"]
        if "external" in cw:
            # the concept web lives in a durable store's own files; the caller
            # must hand us that store reopened — there is nothing to re-put.
            if store is None:
                raise ValueError(
                    f"checkpoint for '{idy['name']}' keeps its concept web in an "
                    f"external store (spec {cw['external']!r}); pass store= "
                    f"(set RELWEB_STORE / --store to match)")
        else:
            # inline edges load into whatever store the creature holds — handing
            # a durable store here IS the JSON->store migration: the next save
            # writes the external form and never dumps the web again.
            for e in cw["edges"]:
                c.edges.put(e["src"], e["tgt"], {"count": e["count"], "sources": e["sources"], "frames": e["rel"]})
        c.frontier = {int(k): v for k, v in d["frontier"].items()}
        c.read_sources = set(d.get("ledger", {}).get("read_sources", []))
        c.passed_stages = set(d.get("ledger", {}).get("passed_stages", []))
        working = d.get("working", {})
        c._buffer = list(working.get("buffer", []))
        c._buffer_seen = working.get("buffer_seen", len(c._buffer))
        rng = working.get("rng")
        if rng:
            c._rng.setstate((rng[0], tuple(rng[1]), rng[2]))
        c.log_position = d.get("log_position", 0)
        return c

    @classmethod
    def load(cls, path: str | Path, log: EpisodeLog | None = None,
             store: EdgeStore | None = None) -> "Creature":
        """Restore the checkpoint; if the given log has grown past it (another
        writer appended, or a crash lost a save), replay the tail (invariant #5:
        the log is the belief source, the file just a checkpoint of it). The
        number sense — a pure projection — re-derives from the log's pairing
        and ostension entries.

        A checkpoint whose concept web is EXTERNAL needs its ``store`` passed
        in. If that store turns out empty while the checkpoint says the web had
        edges (a deleted/misplaced database file), the log is still the source
        of truth: rebuild the whole projection by replay rather than resume
        silently amnesiac."""
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        c = cls.from_dict(d, log=log, store=store)
        cw = d["geometry"]["concept_web"]
        if "external" in cw and cw.get("edges", 0) and c.edges.num_edges() == 0 and len(c.log):
            c._trace("store-lost", {f"expected:{cw['edges']}"}, {"rebuild:full-replay"})
            return c.rebuild()   # replays everything, pairings included
        c._reproject_numbers()
        if len(c.log) > c.log_position:
            c.catch_up()
        return c
