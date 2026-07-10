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
    ``grown``), budgeted against query floods (P7).

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

Talk-back (:meth:`about` / :meth:`answer` / :meth:`say`) runs through the shared
:mod:`~relweblearner.talk` layer, so a streamed creature speaks identically to a
hand-trained one.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from . import curriculum as C
from . import talk as T
from . import transport as TR
from .episodelog import EpisodeLog, InMemoryEpisodeLog
from .journal import Journal
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
        exception_fraction: float = 0.2,
        derive_depth: int = 6,
        growth_persistence: int = 3,
        growth_budget: int = 16,
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
        self.exception_fraction = exception_fraction
        self.derive_depth = derive_depth
        self.growth_persistence = growth_persistence
        self.growth_budget = growth_budget
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
        self._rel_groups: dict[str, str] = {}                  # class -> constraint-group root
        self._group_webs: dict[str, TR.Web] = {}               # group -> valued Web projection
        self._cmaps: dict[str, set] = {}                       # class -> eligible (src, tgt) pairs
        self.growth_events: list[dict] = []                    # committed P1 moves (budgeted, P7)
        self.grown_seq = 0                                     # allocator for posited concept ids
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

    def observe(self, tokens, picture: str | None = None, source: str = "stream", marks=None) -> dict:
        """Log one episode, then distil it into the model (write-ahead: the log
        is the belief source, the model its projection — invariant #5)."""
        if source.startswith("act:"):
            # invariant #7: the act namespace belongs to the learner's own moves;
            # external testimony may never claim it.
            raise ValueError("source namespace 'act:' is reserved for the learner's own moves")
        entry = {"kind": "world", "tokens": list(tokens), "picture": picture,
                 "source": source, "marks": [list(m) for m in marks] if marks else None}
        seq = self.log.append(entry)
        self.log_position = seq + 1
        r = self._distill(entry)
        outcome = ({f"fact:{r['fact'][0]}:{r['fact'][1]}"} if r.get("parsed")
                   else {f"frontier:{len(entry['tokens'])}"})
        self._trace("observe", {f"log:{seq}"}, outcome)
        return r

    def _distill(self, entry: dict) -> dict:
        """Fold one WORLD log entry into the model (shared by live observation
        and replay — the projection is the same function of the log either way)."""
        self.episodes_seen += 1
        tokens = list(entry["tokens"])
        pic = (entry["picture"] or "").strip().lower() or None
        if entry.get("marks"):
            self._add_human_frame(tokens, entry["marks"])
        return self._absorb({"tokens": tokens, "picture": pic, "source": entry["source"]})

    def ingest(self, episodes: Iterable[dict]) -> "Creature":
        """Stream a corpus through :meth:`observe` (episodes are ``{book/source,
        tokens, picture, marks}`` dicts, as the generator emits)."""
        n = 0
        for e in episodes:
            self.observe(
                e["tokens"],
                picture=e.get("picture"),
                source=e.get("source") or e.get("book", "stream"),
                marks=e.get("marks"),
            )
            n += 1
        merges = self.unify_relations()   # recognise synonymous frames once evidence has accrued
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
        elif entry["kind"] == "act":
            self._apply_act(entry)

    def _apply_act(self, event: dict) -> None:
        """Fold one committed act into the projection (live commit and replay
        share this path). Restores the posit-id allocator past every replayed
        posit so a later growth can never collide."""
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
        self._rel_groups, self._group_webs, self._cmaps = {}, {}, {}
        self.growth_events = []
        self.refused_merges = []
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

    def retract_episodes(self, seqs, reason: str = "") -> dict:
        """Invariant #6 retraction at EPISODE granularity: flag the entries
        excluded (never deleted) and rebuild by replay-with-exclusions. This is
        the retraction decrement cannot express — "this one page of an
        otherwise-good source was wrong" — and it reports collateral (committed
        facts lost beyond the lie) as the price of recovery. Requires a
        retaining log; a NullEpisodeLog raises."""
        seqs = sorted(set(seqs))
        before = self.edges.num_committed(self.commit_k)
        for s in seqs:
            self.log.exclude(s, reason)
        self.rebuild()
        after = self.edges.num_committed(self.commit_k)
        self._trace("retract-episodes", {f"excluded:{len(seqs)}"},
                    {f"uncommitted:{before - after}"})
        return {"excluded": seqs, "reason": reason,
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
            self._bump_fact(fact, ep["source"], fid, fillers, ep["picture"])
            self.parsed += 1
            return {"parsed": True, "frontier": False, "frame": fid, "fact": fact, "status": self._status(fact)}
        self.unparsed += 1
        self._bump_frontier(ep["tokens"])
        self._reservoir_add(ep)
        self._since_induction += 1
        if self._since_induction >= self.induction_interval:
            self._induce()
        return {"parsed": False, "frontier": True, "fact": None}

    def _bump_fact(self, fact, source, fid, fillers, picture) -> None:
        self.edges.bump(fact[0], fact[1], fid, source, self.source_cap)   # indexed, incremental
        self._sectors = None                                   # transports are stale
        if picture is not None and fid not in self.source_slot:
            for i, fill in enumerate(fillers):
                if fill == picture:
                    self.source_slot[fid] = i
                    break

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
        maps: dict[str, dict[str, set]] = {}      # frame -> {source: {committed targets}}
        for fid in fids:
            m: dict[str, set] = {}
            for s, t, info in self.edges.edges_by_rel(fid):
                if len(info["sources"]) >= self.commit_k:
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

    # ============================================================= transport / algebra
    #
    # The algebra layer: the SAME frozen machinery the phase experiments run on
    # (:mod:`~relweblearner.transport` wraps sectors/web/holonomy/growth), fed by
    # the streamed store. Everything here is DERIVED from the geometry — rebuilt
    # lazily whenever a fact, class or retraction changes it — never stored.

    def _web_eligible(self, info: dict) -> bool:
        """An edge enters the valued web if it is committed testimony (>=
        ``commit_k`` independent sources) or one of the learner's own act-sourced
        posits (structure committed by the growth discipline needs no
        corroboration — the fork-scored search already gated it)."""
        srcs = info.get("sources", {})
        return len(srcs) >= self.commit_k or any(str(s).startswith("act:") for s in srcs)

    def _class_maps(self) -> dict[str, set]:
        """Relation class → eligible ``(source, target)`` pairs, via the frames
        each edge was expressed in. One full-store scan, O(facts) = O(world)."""
        rel_of = self._rel_of()
        two_slot = {fid for fid, f in self.frames.items() if f.n_slots == 2}
        out: dict[str, set] = {}
        for s, t, info in self.edges.iter_edges():
            if not self._web_eligible(info):
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
        Derivation runs only on ANTISYMMETRIC classes: an unconstrained
        class's transport is pure gauge, and deriving along it would be the
        P4 "algebra too strong" hallucinated inverse."""
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
        if sector is None or sector.sector != TR.ANTISYMMETRIC:
            return res
        web = self._group_webs.get(self._rel_groups.get(qclass))
        if web is None:
            return res
        target = sector.transport if forward else web.algebra.dagger(sector.transport)
        seen = {a["answer"] for a in res["answers"]}
        for n in TR.derive(web, given, target, max_depth=self.derive_depth):
            if n in seen:
                continue
            fact = (given, n) if forward else (n, given)
            res["answers"].append({"answer": n, "status": "derived",
                                   "sentence": self._render_via(fact, res["frame"])})
        if not res["answers"] and given in web.nodes:
            self._probe_growth(res, web, qclass, given, forward)
        rank = {"committed": 0, "derived": 1, "provisional": 2, "grown": 3, "rewired": 3}
        res["answers"].sort(key=lambda a: rank.get(a["status"], 4))
        res["known"] = bool(res["answers"])
        return res

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
        return "committed" if len(e["sources"]) >= self.commit_k else "provisional"

    def _state_for(self, edges: list) -> dict:
        """A talk-back state (see :mod:`~relweblearner.talk`) over ONLY the given
        edges ``(src, tgt, info)`` — a neighbourhood, never the whole web. Frames
        and slot orientation are bounded and always in memory."""
        facts, committed, fact_frames = {}, set(), {}
        for s, t, info in edges:
            facts[(s, t)] = info["sources"]
            fact_frames[(s, t)] = info["frames"]
            if len(info["sources"]) >= self.commit_k:
                committed.add((s, t))
        return {"frames": self.frames, "facts": facts, "committed": committed,
                "source_slot": self.source_slot, "fact_frames": fact_frames,
                "rel_of": self._rel_of()}

    def about(self, referent: str) -> dict:
        r = referent.strip().lower()
        res = T.about(self._state_for([(r, t, i) for t, i in self.edges.out_edges(r)]), r)
        self._trace("about", {r}, {f"beliefs:{len(res['beliefs'])}"})
        return res

    def answer(self, phrase: str) -> dict:
        from .reader import tokenize
        tokens = tokenize(phrase)
        # load the neighbourhood of each content token (the given filler is among
        # them) — indexed lookups, not a full-web scan.
        content = [t for t in tokens if t not in ("?", "_") and not self._is_anchor(t)]
        edges = []
        for tok in content:
            edges += [(tok, t, i) for t, i in self.edges.out_edges(tok)]
            edges += [(s, tok, i) for s, i in self.edges.in_edges(tok)]
        res = T.answer(self._state_for(edges), tokens)
        if res.get("kind") == "answer":
            res = self._think(res)                # lookup first, then transport (P3/P1)
            marks = ({f"{a['status']}:{a['answer']}" for a in res["answers"][:3]}
                     or {"unknown"})
            self._trace("answer", {res.get("given") or "?"}, marks)
        else:
            self._trace("answer", {"?"}, {res.get("kind", "unparsed")})
        return res


    def _is_anchor(self, tok: str) -> bool:
        return any(tok in f.anchors for f in self.frames.values())

    def say(self, referent: str | None = None, limit: int = 20) -> list[dict]:
        if referent is not None:
            r = referent.strip().lower()
            edges = [(r, t, i) for t, i in self.edges.out_edges(r)]
        else:
            edges = self.edges.committed(self.commit_k, limit=max(limit * 3, limit))
        out = T.say(self._state_for(edges), referent, limit)
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
        before = self.edges.num_committed(self.commit_k)
        touched = self.edges.retract_source(source)
        after = self.edges.num_committed(self.commit_k)
        self._sectors = None                        # geometry changed; transports are stale
        self._trace("retract-source", {source}, {f"touched:{touched}"})
        return {"source": source, "edges_touched": touched,
                "committed_before": before, "committed_after": after,
                "uncommitted": before - after}

    # ============================================================= metrics / snapshot

    def snapshot(self, committed_limit: int = 200) -> dict:
        self._trace("snapshot", {"snapshot"}, {f"episodes:{self.episodes_seen}"})
        total = self.parsed + self.unparsed
        n_edges = self.edges.num_edges()
        n_committed = self.edges.num_committed(self.commit_k)
        committed_edges = self.edges.committed(self.commit_k, limit=committed_limit)
        st = self._state_for(committed_edges)   # render only the shown committed facts
        # provisional = edges seen but below the commitment threshold; the creature
        # reports its own uncommitted geometry (bounded to committed_limit for the view)
        prov_edges = sorted(
            ((s, t, info) for (s, t, info) in self.edges.iter_edges()
             if len(info.get("sources", [])) < self.commit_k),
            key=lambda r: (r[0], r[1]))[:committed_limit]
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
            "defects": self.defects(),
            "growth": {"count": len(self.growth_events), "budget": self.growth_budget,
                       "events": self.growth_events[-10:]},
            "bus": vars(self.bus.counts()).copy(),

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
            seed = self.edges.committed(self.commit_k, limit=1)
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

        edges = [{"source": focus, "target": t, "rel": _rel(info),
                  "committed": len(info["sources"]) >= self.commit_k}
                 for (t, info) in out[:limit]]
        room = max(0, limit - len(edges))
        edges += [{"source": s, "target": focus, "rel": _rel(info),
                   "committed": len(info["sources"]) >= self.commit_k}
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
        edges = []
        for s, t, info in all_edges:
            if s in keep and t in keep:
                edges.append({"source": s, "target": t,
                              "committed": len(info["sources"]) >= self.commit_k})
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
                                   "committed": len(ev["sources"]) >= self.commit_k})

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
            "language_web": {
                "frames": {fid: [list(e) for e in f.pattern] for fid, f in self.frames.items()},
                "source_slot": self.source_slot,
                "relations": self._rel_of(),   # frame -> unified relation class
            },
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
        machinery operates on it again."""
        return {
            "identity": {"name": self.name, "id": self.id, "created": self.created, "level": self.level},
            "algebra": "frozen in code (not stored) — only geometry is persisted",
            "params": {
                "commit_k": self.commit_k, "min_group": self.min_group, "dominance": self.dominance,
                "min_anchors": self.min_anchors, "induction_interval": self.induction_interval,
                "buffer_cap": self.buffer_cap, "max_slot_tokens": self.max_slot_tokens,
                "source_cap": self.source_cap, "exemplar_cap": self.exemplar_cap,
                "exception_fraction": self.exception_fraction, "derive_depth": self.derive_depth,
                "growth_persistence": self.growth_persistence, "growth_budget": self.growth_budget,
                "seed": self.seed, "reservoir_stratify": self.reservoir_stratify,
            },
            "counters": {"episodes_seen": self.episodes_seen, "parsed": self.parsed,
                         "unparsed": self.unparsed, "grown_seq": self.grown_seq},
            "growth_events": self.growth_events,
            # checkpoint marker (invariant #5): how far into the episode log this
            # state has distilled — load() replays whatever tail lies beyond it.
            "log_position": self.log_position,
            "ledger": {"read_sources": sorted(self.read_sources),    # registry ids already ingested (incremental training)
                       "passed_stages": sorted(self.passed_stages)}, # curriculum stages mastered (worksheet passed)
            "geometry": self.geometry(),
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
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: dict, log: EpisodeLog | None = None) -> "Creature":
        idy, p = d["identity"], d["params"]
        c = cls(idy["name"], created=idy.get("created"), level=idy.get("level"), log=log, **p)
        cnt = d["counters"]
        c.episodes_seen, c.parsed, c.unparsed = cnt["episodes_seen"], cnt["parsed"], cnt["unparsed"]
        c.grown_seq = cnt.get("grown_seq", 0)
        c.growth_events = list(d.get("growth_events", []))
        geo = d["geometry"]
        lang = geo["language_web"]
        c.frames = {fid: C.Frame(fid, tuple(tuple(e) for e in pat)) for fid, pat in lang["frames"].items()}
        c.source_slot = {k: int(v) for k, v in lang["source_slot"].items()}
        c._rel_parent = {fid: root for fid, root in lang.get("relations", {}).items()}
        for e in geo["concept_web"]["edges"]:
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
    def load(cls, path: str | Path, log: EpisodeLog | None = None) -> "Creature":
        """Restore the checkpoint; if the given log has grown past it (another
        writer appended, or a crash lost a save), replay the tail (invariant #5:
        the log is the belief source, the file just a checkpoint of it)."""
        c = cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")), log=log)
        if len(c.log) > c.log_position:
            c.catch_up()
        return c
