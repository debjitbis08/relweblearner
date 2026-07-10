"""A stateful reading SESSION — the hand-training application layer (R2).

Everything under :mod:`~relweblearner.curriculum` is BATCH and pure-functional:
each experiment rebuilds frames, facts and metrics from a fixed corpus in one
shot. Hand-training a creature by feeding it phrases from books is the same
machinery run INCREMENTALLY and STATEFULLY — a phrase arrives, frames re-induce,
picture-oriented facts re-accrue provenance, and the ones with enough origins
commit. This module is that wrapper; it adds no new learning, only the session,
the persistence and the talk-back the product needs.

Faithful to the architecture on three points:

  * **The referent tag IS the ostension.** A page carries the pictured referent
    (spec §0's tap); it orients every fact (:func:`curriculum._orient`) exactly
    as ``fast_map_page`` does, so the tag directly breaks the symmetry the
    grounding layer would otherwise stall on. No image pipeline is needed for
    that job — a tapped word suffices.
  * **The concept web is BOOTSTRAPPED from the reading.** In a pure reader there
    is no prior concept web to align to; the committed facts ARE the concept web.
    So grounding-through-frames collapses to picture orientation, and the facts
    the session commits are its beliefs.
  * **State is a projection of an append-only log.** As everywhere else in the
    repo, the derived state (frames, facts, beliefs) is a pure function of the
    page log; :meth:`Reader.feed` appends, and :classmethod:`Reader.load` replays
    a JSONL log to reconstruct the session exactly.

Talk-back is the L6 writing discipline in the frame world: :meth:`Reader.say`
fills an induced frame from a committed fact and READS THE DRAFT BACK
(re-parses it) before offering it — an ambiguous draft is never emitted.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from . import curriculum as C
from . import talk as T

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens; punctuation dropped, ``?``/``_`` preserved as their
    own tokens so a question phrase can carry an explicit blank."""
    out: list[str] = []
    for raw in text.strip().split():
        if raw in ("?", "_"):
            out.append(raw)
            continue
        out.extend(m.group(0).lower() for m in _WORD.finditer(raw))
    return out


class Reader:
    """An incremental, persistable reading session over the R2 pipeline.

    Parameters mirror :func:`curriculum.grow_frames` with hand-training defaults:
    ``min_group`` is lower than the batch spec's 10 because a human feeds a
    handful of examples per frame, not sixty. ``commit_k`` is the number of
    distinct book/source origins a fact needs before it is believed (spec §0.3 /
    §6 commitment policy); provisional (seen-but-uncommitted) facts are surfaced
    separately so learning is visible immediately.
    """

    def __init__(
        self,
        *,
        min_group: int = 3,
        dominance: float = 0.8,
        min_anchors: int = 2,
        commit_k: int = 2,
        relation: str = "relates",
        log_path: str | Path | None = None,
    ):
        self.pages: list[dict] = []
        self.min_group = min_group
        self.dominance = dominance
        self.min_anchors = min_anchors
        self.commit_k = commit_k
        self.relation = relation
        self.log_path = Path(log_path) if log_path else None
        self._cache: dict | None = None

    # ------------------------------------------------------------------ ingest

    def feed(
        self,
        text: str,
        picture: str | None = None,
        book: str = "reading",
        marks: list | None = None,
    ) -> dict:
        """Read one phrase into the session.

        ``picture`` is the tapped referent (a word in the phrase); it orients the
        fact and is the session's ostension event. ``book`` is the provenance
        source — feeding the same fact from a *second* book is what commits it.

        ``marks`` is the optional human BREAKUP — a list of ``[start, end]`` token
        spans the reader marked as slot fillers (the varying parts). When given, it
        defines a frame from this single example and can separate adjacent fillers
        the auto-inducer would merge (the scaffold path, until the model segments on
        its own). Every other token is an anchor. Returns :meth:`observe`.
        """
        tokens = tokenize(text)
        if not tokens:
            raise ValueError("empty phrase")
        pic = (picture or "").strip().lower() or None
        if pic is not None and pic not in tokens:
            raise ValueError(f"referent {pic!r} is not a word in the phrase {tokens}")
        norm_marks = None
        if marks:
            norm_marks = [[int(a), int(b)] for a, b in marks]
            for a, b in norm_marks:
                if not (0 <= a < b <= len(tokens)):
                    raise ValueError(f"slot span [{a}, {b}] out of range for {tokens}")
            C.pattern_from_marks(tokens, norm_marks)  # validates non-overlap
        page = {"book": book, "tokens": tokens, "picture": pic, "marks": norm_marks}
        self.pages.append(page)
        self._cache = None
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(page, ensure_ascii=False) + "\n")
        return self.observe(page)

    def feed_many(self, pages: Iterable[dict]) -> None:
        """Replay pages verbatim (used by :meth:`load`); no logging, no validation
        beyond shape — the log is the source of truth."""
        for p in pages:
            self.pages.append(
                {
                    "book": p["book"],
                    "tokens": list(p["tokens"]),
                    "picture": p.get("picture"),
                    "marks": p.get("marks"),
                }
            )
        self._cache = None

    # --------------------------------------------------------------- derived state

    def _derive(self) -> dict:
        """Recompute frames, facts and beliefs from the page log (memoised until
        the next :meth:`feed`)."""
        if self._cache is not None:
            return self._cache
        human = self._human_frames()
        auto, residual = C.grow_frames(
            self.pages,
            min_group=self.min_group,
            dominance=self.dominance,
            min_anchors=self.min_anchors,
        )
        # human breakups win: drop any auto frame with the same anchor set (the
        # human's finer slotting supersedes the coarse auto-merged one).
        human_anchors = {f.anchors for f in human.values()}
        frames = dict(human)
        for fid, f in auto.items():
            if f.anchors not in human_anchors:
                frames[fid] = f
        facts = C.collect_facts(self.pages, frames)
        committed = C.committed_facts(facts, self.commit_k)
        fact_frames: dict[tuple, set] = defaultdict(set)
        for p, r in C.parse_pages(self.pages, frames):
            if r is not None and len(r[1]) == 2:
                fid, fillers = r
                fact = C._orient(fillers, p["picture"]) if p["picture"] else tuple(fillers)
                fact_frames[fact].add(fid)
        self._cache = {
            "frames": frames,
            "frontier": C.frontier(self.pages, frames),  # combined human + auto
            "facts": facts,
            "committed": committed,
            "source_slot": self._source_slots(frames),
            "fact_frames": dict(fact_frames),
        }
        return self._cache

    def _human_frames(self) -> dict:
        """Frames defined by the reader's explicit breakups (:meth:`feed`
        ``marks``). One marked example is enough — the reader is the authority on
        its own template — and adjacent fillers stay separate slots. Distinct
        patterns become distinct frames; a degenerate all-slot or no-slot mark is
        ignored."""
        frames: dict = {}
        by_pattern: dict = {}
        for p in self.pages:
            if not p.get("marks"):
                continue
            pat = C.pattern_from_marks(p["tokens"], p["marks"])
            n_anchors = sum(1 for e in pat if e[0] == C.LIT)
            n_slots = sum(1 for e in pat if e[0] == C.SLOT)
            if n_anchors < 1 or n_slots < 1 or pat in by_pattern:
                continue
            fid = f"H{len(by_pattern)}_{'_'.join(e[1] for e in pat if e[0] == C.LIT)}"
            by_pattern[pat] = fid
            frames[fid] = C.Frame(fid, pat)
        return frames

    def _source_slots(self, frames: dict) -> dict[str, int]:
        """For each frame, which slot INDEX tends to hold the pictured referent
        (the fact's SOURCE). Learned by majority vote over parsed pages; needed to
        run a frame *backwards* when writing a sentence (:meth:`say`)."""
        votes: dict[str, Counter] = defaultdict(Counter)
        for p, r in C.parse_pages(self.pages, frames):
            if r is None or p["picture"] is None:
                continue
            fid, fillers = r
            for i, fill in enumerate(fillers):
                if fill == p["picture"]:
                    votes[fid][i] += 1
        return {fid: c.most_common(1)[0][0] for fid, c in votes.items() if c}

    # ------------------------------------------------------------------ observe

    def observe(self, page: dict) -> dict:
        """What reading ``page`` produced: the frame it parsed under (or that it
        landed on the frontier), and the fact it contributed with its belief
        status."""
        st = self._derive()
        r = C.parse(page["tokens"], st["frames"])
        if r is None:
            return {"parsed": False, "frontier": True, "fact": None}
        fid, fillers = r
        fact = None
        if len(fillers) == 2:
            fact = C._orient(fillers, page["picture"]) if page["picture"] else tuple(fillers)
        return {
            "parsed": True,
            "frontier": False,
            "frame": fid,
            "fact": fact,
            "status": T._status(fact, st) if fact else None,
        }

    # ------------------------------------------------------------------ talk back

    # The interactive session speaks through the shared :mod:`~relweblearner.talk`
    # layer, exactly as the streaming Creature does — its derived state IS the
    # ``state`` view those functions consume.

    def about(self, referent: str) -> dict:
        return T.about(self._derive(), referent)

    def answer(self, phrase: str) -> dict:
        return T.answer(self._derive(), tokenize(phrase))

    def say(self, referent: str | None = None, limit: int = 20) -> list[dict]:
        return T.say(self._derive(), referent, limit)

    def _render(self, src: str, tgt: str, st: dict, *, verify: bool = True) -> str | None:
        return T.render_fact(src, tgt, st, verify=verify)

    # ------------------------------------------------------------------ snapshot

    def snapshot(self) -> dict:
        """A JSON-serialisable view of the whole session — frames, beliefs,
        frontier and the spec §6 path metrics — for the app's status view."""
        st = self._derive()
        frames = [
            {
                "id": f.id,
                "skeleton": list(f.skeleton),
                "template": f.template,
                "slots": list(f.slots),
                "anchors": list(f.anchors),
            }
            for f in sorted(st["frames"].values(), key=lambda fr: fr.id)
        ]
        committed = [
            {"source": s, "target": t, "sources": sorted(st["facts"][(s, t)]), "sentence": self._render(s, t, st)}
            for (s, t) in sorted(st["committed"])
        ]
        provisional = [
            {"source": s, "target": t, "sources": sorted(bks), "sentence": self._render(s, t, st)}
            for (s, t), bks in sorted(st["facts"].items())
            if (s, t) not in st["committed"]
        ]
        cov, _fr = C.coverage(self.pages, st["frames"]) if self.pages else (0.0, [])
        rate = len(st["committed"]) / len(self.pages) if self.pages else 0.0
        return {
            "pages_read": len(self.pages),
            "coverage": round(cov, 3),
            "assimilation_rate": round(rate, 3),
            "frames": frames,
            "committed": committed,
            "provisional": provisional,
            "frontier": [list(p["tokens"]) for p in st["frontier"]],
            "frontier_census": {
                str(k): [list(t) for t in v] for k, v in C.frontier_census(st["frontier"]).items()
            },
        }

    # ------------------------------------------------------------------ persistence

    @classmethod
    def load(cls, log_path: str | Path, **kwargs) -> "Reader":
        """Reconstruct a session by replaying its append-only JSONL page log. The
        log is the source of truth; derived state is recomputed, not stored."""
        log_path = Path(log_path)
        r = cls(log_path=log_path, **kwargs)
        if log_path.exists():
            pages = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            r.feed_many(pages)
        return r
