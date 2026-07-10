"""Number sense — the creature's word chain identified with the P1b chain (P5).

The creature's number words are, by themselves, pure syntax: nodes in a word
chain whose ±1 transports were inferred from sentences (``five comes after
four``). The P1b :class:`~relweblearner.number.NumberLearner` constructs number
CLASSES from bare pairing episodes over collections of opaque objects — genuine
cardinalities, with no numeral anywhere in the stream. This module ties the two
together with the P5 interface discipline, so that "ten" can mean *the class of
piles that saturate against this pile* rather than *the token after "nine"*:

  * **Play** — bare pairing episodes feed the NumberLearner; the constructed
    chain (classes + successor) is a PROJECTION of its journal, re-derived on
    demand (invariant #5).
  * **Ostension** — a joint page presents a pile WITH a tapped number word.
    The creature COUNTS the pile itself (the P1b routine: pair against a class
    witness until saturation — the verdict is :func:`~relweblearner.number
    .derive` on the very episode the pairing forms), folds the witnessing
    MATCH into the number web, and records a candidate identification
    ``word ↔ class`` with per-source provenance. Naming is never trusted raw:
    it is a claim that accrues sources like any edge (commit at ``k``).
  * **The interface map, found by search** (P5): candidate identifications
    imply offsets between word-chain coordinates and chain positions; the
    modal offset is the map, outliers are POISON (miscounts). One extension to
    the stock P5 search, stated in the open: a Z-chain's global sign is gauge
    (``x ↦ -x`` is an algebra automorphism — see ``transport.infer``), so the
    search quantifies over orientation ``s ∈ {+1, -1}`` as well as offset.
    Identifications of words with NO word-chain coordinate (a word known only
    from ostension) cannot validate the map but ride it: committed and
    unambiguous, they name classes the word chain has never ordered.
  * **Transfer** — with a committed map, a word-order question steps along the
    CONSTRUCTED chain: word → class → ``s·t`` successor steps → class → word.
    An answer can involve a word the creature never heard in an order
    sentence — order learned from counting piles, not from sentences.

Honest seams: the members index (collection id → objects) is O(collections
seen) in RAM — the same deferred file-backing seam as the trace bus; and each
staleness re-projection replays the whole number journal — cheap at present
scale, a causal-cone candidate later.
"""

from __future__ import annotations

from collections import Counter

from .episode import world_episode
from .journal import Journal
from .number import NumberChain, NumberLearner, derive


class NumberSense:
    """The counting substrate + naming table + interface-map search."""

    def __init__(self, commit_k: int = 2, source_cap: int = 16, name: str = "numbers"):
        self.commit_k = commit_k
        self.source_cap = source_cap
        self.learner = NumberLearner(Journal(name))
        self.members: dict[str, tuple] = {}                 # collection id -> objects (index)
        self.names: dict[str, dict[str, dict]] = {}         # word -> cid -> {source: n}
        self._chain: NumberChain | None = None              # cached projection (stale on PLAY)
        # Naming binds a pile into an EXISTING class (a MATCH merge) — it can
        # never reorder the chain — so it must not force a re-projection. The
        # match episode still enters the journal (the next projection subsumes
        # it); until then this local table carries the resolution.
        self._bound: dict[str, str] = {}                    # cid -> class rep at naming time

    # ------------------------------------------------------------ ingestion

    def feed_pairing(self, id1, members1, id2, members2, pairing=()) -> None:
        """One bare pairing episode into the number journal (numbers are never
        input; MATCH/ONEMORE are derived downstream — P1b)."""
        self.learner.ingest(world_episode(id1, members1, id2, members2, pairing))
        self.members.setdefault(id1, tuple(sorted(members1)))
        self.members.setdefault(id2, tuple(sorted(members2)))
        self._chain = None

    def chain(self) -> NumberChain:
        if self._chain is None:
            self._chain = self.learner.project()
        return self._chain

    def _witness(self, ch: NumberChain, rep) -> tuple | None:
        """One remembered pile of a class: ``(collection_id, objects)`` of any
        member collection whose objects the index still holds."""
        for cid in sorted(ch.class_members.get(rep, ())):
            if cid in self.members:
                return cid, self.members[cid]
        return None

    def count_fresh(self, members) -> tuple[int, str] | None:
        """Number a pile by the chain-pairing routine: pair it against each
        class witness in order; the class whose pairing SATURATES both sides
        (a derived MATCH — the same predicate play is built from) is the count.
        Returns ``(position, class_rep)`` or ``None`` (off the known chain)."""
        ch = self.chain()
        pile = sorted(set(members))
        for pos, rep in enumerate(ch.order, start=1):
            wit = self._witness(ch, rep)
            if wit is None:
                continue
            _wcid, wobjs = wit
            n = min(len(wobjs), len(pile))
            ep = world_episode("q:pile", pile, "q:wit", wobjs, list(zip(pile[:n], wobjs[:n])))
            f = derive(ep)
            if f is not None and f[0] == "match":
                return pos, rep
        return None

    def name(self, word: str, cid: str, members, source: str) -> tuple[int, str] | None:
        """Record an ostension: pile ``cid`` presented under ``word``.

        The pile is counted first; on success the witnessing MATCH episode is
        folded into the number web (so ``cid`` becomes a resolvable node of its
        class) and the identification accrues ``source``. A pile off the known
        chain names nothing — the number frontier."""
        self.members.setdefault(cid, tuple(sorted(members)))
        counted = self.count_fresh(members)
        if counted is None:
            return None
        pos, rep = counted
        ch = self.chain()
        wcid, wobjs = self._witness(ch, rep)
        pile = self.members[cid]
        self.learner.ingest(world_episode(cid, pile, wcid, wobjs, list(zip(pile, wobjs))))
        self._bound[cid] = rep
        cids = self.names.setdefault(word, {})
        if cid in cids or len(cids) < self.source_cap:
            srcs = cids.setdefault(cid, {})
            if source in srcs or len(srcs) < self.source_cap:
                srcs[source] = srcs.get(source, 0) + 1
        return pos, rep

    def retract_source(self, source: str) -> int:
        """Decrement-retract a source from the naming table (the fast path,
        mirroring the edge store; replay retraction remains ground truth)."""
        touched = 0
        for word in list(self.names):
            for cid in list(self.names[word]):
                if source in self.names[word][cid]:
                    del self.names[word][cid][source]
                    touched += 1
                    if not self.names[word][cid]:
                        del self.names[word][cid]
            if not self.names[word]:
                del self.names[word]
        return touched

    # ------------------------------------------------------------ identifications

    def committed_ids(self) -> dict[str, dict[str, set]]:
        """``word -> class_rep -> sources``, aggregated through the current
        merge structure (collections naming the same class pool their sources)
        and filtered at the ``k`` commitment threshold."""
        ch = self.chain()
        pooled: dict[str, dict[str, set]] = {}
        for word, cids in self.names.items():
            for cid, srcs in cids.items():
                rep = ch.web.resolve(self._bound.get(cid, cid))
                pooled.setdefault(word, {}).setdefault(rep, set()).update(srcs)
        return {
            w: {rep: srcs for rep, srcs in reps.items() if len(srcs) >= self.commit_k}
            for w, reps in pooled.items()
        }

    # ------------------------------------------------------------ the map (P5)

    def map(self, word_coords: dict) -> dict | None:
        """The mismatch-minimizing interface map between the word chain and the
        constructed chain, found by search alone (P5's ``find_interface_map``
        extended over the sign gauge).

        ``word_coords`` are the word web's holonomy potentials (per-component
        gauge; a word from a foreign component lands in poison, which is what
        poison means). Chain coordinates are order positions. Each CHECKABLE
        committed identification (its word has a coordinate) implies, per
        orientation ``s``, the offset ``pos(class) - s·coord(word)``; the modal
        ``(s, c)`` with the most agreeing identifications is the map, committed
        only at >= ``commit_k`` distinct consistent words. Returns ``{s, c,
        word_of, class_of, consistent, poison, conflicts}`` or ``None``.
        """
        ch = self.chain()
        pos = {rep: i for i, rep in enumerate(ch.order)}
        committed = [
            (w, rep, srcs)
            for w, reps in sorted(self.committed_ids().items())
            for rep, srcs in sorted(reps.items())
            if rep in pos
        ]
        checkable = [(w, rep) for w, rep, _ in committed if w in word_coords]

        best = None
        for s in (1, -1):
            offsets = Counter(pos[rep] - s * word_coords[w] for w, rep in checkable)
            if not offsets:
                break
            c, _n = max(offsets.items(), key=lambda kv: (kv[1], -abs(kv[0])))
            fit = [(w, rep) for w, rep in checkable if pos[rep] - s * word_coords[w] == c]
            if best is None or len(fit) > len(best[2]):
                best = (s, c, fit)
        if best is None or len({w for w, _ in best[2]}) < self.commit_k:
            return None
        s, c, consistent = best
        poison = [(w, rep) for w, rep in checkable if (w, rep) not in consistent]

        # word_of / class_of: the consistent checkable pairs plus the pure-
        # ostension ones (no coordinate to check — they ride the map under the
        # k discipline). An ambiguous binding — one word to two classes, or two
        # words to one class — is dropped and reported, unless coordinate
        # consistency already arbitrated it.
        keep = list(consistent) + [(w, rep) for w, rep, _ in committed if w not in word_coords]
        by_word: dict[str, set] = {}
        by_rep: dict[str, set] = {}
        for w, rep in keep:
            by_word.setdefault(w, set()).add(rep)
            by_rep.setdefault(rep, set()).add(w)
        conflicts = [w for w, reps in by_word.items() if len(reps) > 1]
        conflicts += [r for r, ws in by_rep.items() if len(ws) > 1]
        word_of = {rep: w for w, rep in keep
                   if len(by_word[w]) == 1 and len(by_rep[rep]) == 1}
        class_of = {w: rep for rep, w in word_of.items()}
        return {"s": s, "c": c, "word_of": word_of, "class_of": class_of,
                "consistent": consistent, "poison": poison,
                "conflicts": sorted(set(conflicts))}

    def word_step(self, m: dict, word_coords: dict, word: str, t: int) -> str | None:
        """Answer a word-order step THROUGH the constructed chain: word →
        class, ``s·t`` positions along the chain, class → word. ``t`` is the
        question's word-chain transport (dagger already applied by the caller).
        Returns the answer word, or ``None`` when the walk leaves the known
        chain or the target class is unnamed."""
        ch = self.chain()
        pos = {rep: i for i, rep in enumerate(ch.order)}
        rep = m["class_of"].get(word)
        if rep is None and word in word_coords:
            i = m["s"] * word_coords[word] + m["c"]
            if 0 <= i < len(ch.order):
                rep = ch.order[i]
        if rep is None or rep not in pos:
            return None
        target = pos[rep] + m["s"] * t
        if not 0 <= target < len(ch.order):
            return None
        return m["word_of"].get(ch.order[target])
