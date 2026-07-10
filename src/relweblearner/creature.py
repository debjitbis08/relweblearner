"""A CREATURE — a named identity with a bounded, incrementally-distilled model.

The interactive :class:`~relweblearner.reader.Reader` keeps every episode in an
append-only log and recomputes the whole model on each read. That is correct but
does not scale: the log grows with everything READ, and re-derivation is
from-scratch. A learner's memory should instead grow only with what it has
LEARNED — a small world's frames and facts SATURATE — while episodes are a
stream to be distilled and discarded.

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

The scale tradeoff, stated honestly: a frame induced late applies to the ongoing
stream and to whatever is still in the bounded buffer — NOT retroactively to
episodes already distilled and dropped. At scale the stream dwarfs the buffer, so
missing a frame's first few hundred exposures is negligible; perfect
retroactivity is a small-corpus luxury the append-only Reader keeps and this
trades away for bounded memory.

Talk-back (:meth:`about` / :meth:`answer` / :meth:`say`) runs through the shared
:mod:`~relweblearner.talk` layer, so a streamed creature speaks identically to a
hand-trained one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from . import curriculum as C
from . import talk as T
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
        source_cap: int = 16,
        exemplar_cap: int = 5,
        min_shared: int = 3,
        agree_threshold: float = 0.8,
        created: str | None = None,
        level: int | None = None,
        store: EdgeStore | None = None,
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
        self.source_cap = source_cap
        self.exemplar_cap = exemplar_cap
        self.min_shared = min_shared
        self.agree_threshold = agree_threshold

        # The concept web's edges are the ONE unbounded part of the geometry — they
        # live behind an indexed EdgeStore (in-memory by default; SQLite / sharded
        # for open-world scale). Everything else a creature holds is bounded and
        # stays in memory: the language web (frames), the frontier census, and the
        # capped rolling induction buffer.
        self.edges: EdgeStore = store if store is not None else InMemoryEdgeStore()
        self.frames: dict[str, C.Frame] = {}
        self.source_slot: dict[str, int] = {}                  # frame -> picture slot index
        self._rel_parent: dict[str, str] = {}                  # union-find: frame -> relation class
        self.frontier: dict[int, dict] = {}                    # length -> {count, exemplars}
        self._buffer: list[dict] = []                          # rolling unparsed episodes
        self._since_induction = 0
        # ------- counters (scalars, not history) -------
        self.episodes_seen = 0
        self.parsed = 0
        self.unparsed = 0

    # ============================================================= streaming ingest

    def observe(self, tokens, picture: str | None = None, source: str = "stream", marks=None) -> dict:
        """Distil one episode into the model and return what it produced."""
        self.episodes_seen += 1
        tokens = list(tokens)
        pic = (picture or "").strip().lower() or None
        if marks:
            self._add_human_frame(tokens, marks)
        return self._absorb({"tokens": tokens, "picture": pic, "source": source})

    def ingest(self, episodes: Iterable[dict]) -> "Creature":
        """Stream a corpus through :meth:`observe` (episodes are ``{book/source,
        tokens, picture, marks}`` dicts, as the generator emits)."""
        for e in episodes:
            self.observe(
                e["tokens"],
                picture=e.get("picture"),
                source=e.get("source") or e.get("book", "stream"),
                marks=e.get("marks"),
            )
        self.unify_relations()   # recognise synonymous frames once evidence has accrued
        self.commit()
        return self

    def commit(self) -> None:
        """Flush pending store writes (a no-op for the in-memory backend)."""
        if hasattr(self.edges, "commit"):
            self.edges.commit()

    def close(self) -> None:
        self.edges.close()

    def _absorb(self, ep: dict) -> dict:
        r = C.parse(ep["tokens"], self.frames)
        if r is not None and len(r[1]) == 2:
            fid, fillers = r
            fact = C._orient(fillers, ep["picture"]) if ep["picture"] else tuple(fillers)
            self._bump_fact(fact, ep["source"], fid, fillers, ep["picture"])
            self.parsed += 1
            return {"parsed": True, "frontier": False, "frame": fid, "fact": fact, "status": self._status(fact)}
        self.unparsed += 1
        self._bump_frontier(ep["tokens"])
        self._buffer.append(ep)
        if len(self._buffer) > self.buffer_cap:
            self._buffer.pop(0)
        self._since_induction += 1
        if self._since_induction >= self.induction_interval:
            self._induce()
        return {"parsed": False, "frontier": True, "fact": None}

    def _bump_fact(self, fact, source, fid, fillers, picture) -> None:
        self.edges.bump(fact[0], fact[1], fid, source, self.source_cap)   # indexed, incremental
        if picture is not None and fid not in self.source_slot:
            for i, fill in enumerate(fillers):
                if fill == picture:
                    self.source_slot[fid] = i
                    break

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
        added = False
        for f in new.values():
            if f.anchors not in existing:
                self.frames[f.id] = f
                existing.add(f.anchors)
                added = True
        if added:
            self._rescan_buffer()

    def _rescan_buffer(self) -> None:
        """Fold buffered episodes that now parse into evidence; keep the rest.
        This is the bounded, non-retroactive analogue of the Reader's full replay."""
        kept = []
        for ep in self._buffer:
            r = C.parse(ep["tokens"], self.frames)
            if r is not None and len(r[1]) == 2:
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
            relation dimension), and
          * **defect-guarded** — refused if it makes the relation non-functional (a
            source with two committed targets is a holonomy self-loop defect; the
            fixed algebra rejects a bad merge just as it does a false MATCH).

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
        merges = 0
        for i, a in enumerate(fids):
            for b in fids[i + 1:]:
                if self._rel_find(a) == self._rel_find(b):
                    continue
                shared = set(maps[a]) & set(maps[b])
                if len(shared) < self.min_shared:
                    continue
                agree = sum(1 for s in shared if maps[a][s] == maps[b][s]) / len(shared)
                if agree >= self.agree_threshold and self._merge_consistent(maps[a], maps[b]):
                    self._rel_union(a, b)
                    merges += 1
        return merges

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

    # ============================================================= belief / queries

    def _status(self, fact: tuple) -> str:
        e = self.edges.get(*fact)
        if e is None:
            return "unknown"
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
        return T.about(self._state_for([(r, t, i) for t, i in self.edges.out_edges(r)]), r)

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
        return T.answer(self._state_for(edges), tokens)

    def _is_anchor(self, tok: str) -> bool:
        return any(tok in f.anchors for f in self.frames.values())

    def say(self, referent: str | None = None, limit: int = 20) -> list[dict]:
        if referent is not None:
            r = referent.strip().lower()
            edges = [(r, t, i) for t, i in self.edges.out_edges(r)]
        else:
            edges = self.edges.committed(self.commit_k, limit=max(limit * 3, limit))
        return T.say(self._state_for(edges), referent, limit)

    # ============================================================= metrics / snapshot

    def snapshot(self, committed_limit: int = 200) -> dict:
        total = self.parsed + self.unparsed
        n_edges = self.edges.num_edges()
        n_committed = self.edges.num_committed(self.commit_k)
        committed_edges = self.edges.committed(self.commit_k, limit=committed_limit)
        st = self._state_for(committed_edges)   # render only the shown committed facts
        return {
            "identity": {"name": self.name, "id": self.id, "created": self.created, "level": self.level},
            "episodes_seen": self.episodes_seen,
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

            "committed": [
                {"source": s, "target": t, "sources": sorted(info["sources"]), "sentence": T.render_fact(s, t, st)}
                for (s, t, info) in committed_edges
            ],
            "committed_count": n_committed,
            "provisional_count": n_edges - n_committed,
            "frontier": {str(k): v for k, v in sorted(self.frontier.items())},
        }

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
                          "count": ev["count"], "sources": sorted(ev["sources"])})
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
                "buffer_cap": self.buffer_cap, "source_cap": self.source_cap, "exemplar_cap": self.exemplar_cap,
            },
            "counters": {"episodes_seen": self.episodes_seen, "parsed": self.parsed, "unparsed": self.unparsed},
            "geometry": self.geometry(),
            "frontier": {str(k): v for k, v in self.frontier.items()},
            "working": {"buffer": self._buffer},   # ephemeral induction reservoir
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: dict) -> "Creature":
        idy, p = d["identity"], d["params"]
        c = cls(idy["name"], created=idy.get("created"), level=idy.get("level"), **p)
        cnt = d["counters"]
        c.episodes_seen, c.parsed, c.unparsed = cnt["episodes_seen"], cnt["parsed"], cnt["unparsed"]
        geo = d["geometry"]
        lang = geo["language_web"]
        c.frames = {fid: C.Frame(fid, tuple(tuple(e) for e in pat)) for fid, pat in lang["frames"].items()}
        c.source_slot = {k: int(v) for k, v in lang["source_slot"].items()}
        c._rel_parent = {fid: root for fid, root in lang.get("relations", {}).items()}
        for e in geo["concept_web"]["edges"]:
            c.edges.put(e["src"], e["tgt"], {"count": e["count"], "sources": e["sources"], "frames": e["rel"]})
        c.frontier = {int(k): v for k, v in d["frontier"].items()}
        c._buffer = list(d.get("working", {}).get("buffer", []))
        return c

    @classmethod
    def load(cls, path: str | Path) -> "Creature":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
