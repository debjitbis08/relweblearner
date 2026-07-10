"""Indexed geometry store — the web when it outgrows memory (open-world scale).

A creature's geometry has ONE unbounded part: the concept web's nodes and
algebra-valued edges (facts) with their provenance. On a closed world this
saturates, but on an open world (new concepts, relations, words) it grows without
bound — past a single JSON blob, past RAM. Everything else a creature holds
(frames, frontier census, the capped induction buffer) is bounded and stays in
memory; only the edges are externalised here.

An :class:`EdgeStore` is the seam. It is queried by NEIGHBOURHOOD — a referent's
out-edges, a filler's in-edges — never by loading the whole web, so talk-back and
commitment cost O(matches), not O(edges):

  * :class:`InMemoryEdgeStore` — the dict backing (small / interactive use);
  * :class:`SqliteEdgeStore` — B-tree-indexed tables on disk; incremental upserts,
    indexed point/neighbourhood queries, grows past RAM, IS its own persistence;
  * :class:`ShardedEdgeStore` — routes edges to N shard stores by source concept,
    so no single process or file holds the whole geometry (forward queries hit one
    shard; reverse queries fan out).

Edge info is a uniform dict ``{"count": int, "sources": set[str], "frames":
set[str]}``. ``sources`` is capped (commitment needs only >= commit_k distinct
origins), keeping per-edge provenance O(1) and the whole store O(edges).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

_SEP = "\x1f"  # unit separator for group_concat (never occurs in tokens/sources)


class EdgeStore:
    """Interface every backend implements. All names are concept strings."""

    def bump(self, src: str, tgt: str, rel: str, source: str, source_cap: int) -> None:
        raise NotImplementedError

    def put(self, src: str, tgt: str, info: dict) -> None:
        """Load an edge whole (bulk import / JSON->store migration / reload)."""
        raise NotImplementedError

    def get(self, src: str, tgt: str) -> dict | None:
        raise NotImplementedError

    def out_edges(self, src: str) -> list[tuple[str, dict]]:
        raise NotImplementedError

    def in_edges(self, tgt: str) -> list[tuple[str, dict]]:
        raise NotImplementedError

    def committed(self, commit_k: int, limit: int | None = None) -> list[tuple[str, str, dict]]:
        raise NotImplementedError

    def num_committed(self, commit_k: int) -> int:
        raise NotImplementedError

    def iter_edges(self) -> Iterator[tuple[str, str, dict]]:
        raise NotImplementedError

    def num_nodes(self) -> int:
        raise NotImplementedError

    def num_edges(self) -> int:
        raise NotImplementedError

    def close(self) -> None:
        pass


# ============================================================ in-memory backing


class InMemoryEdgeStore(EdgeStore):
    """Dict-backed edges — the original :class:`~relweblearner.creature.Creature`
    behaviour, for small worlds and the interactive session."""

    def __init__(self):
        self._e: dict[tuple, dict] = {}

    def bump(self, src, tgt, rel, source, source_cap):
        e = self._e.get((src, tgt))
        if e is None:
            e = self._e[(src, tgt)] = {"count": 0, "sources": set(), "frames": set()}
        e["count"] += 1
        e["frames"].add(rel)
        if len(e["sources"]) < source_cap:
            e["sources"].add(source)

    def put(self, src, tgt, info):
        self._e[(src, tgt)] = {"count": info["count"], "sources": set(info["sources"]), "frames": set(info["frames"])}

    def get(self, src, tgt):
        e = self._e.get((src, tgt))
        return dict(e) if e is not None else None

    def out_edges(self, src):
        return [(t, dict(e)) for (s, t), e in self._e.items() if s == src]

    def in_edges(self, tgt):
        return [(s, dict(e)) for (s, t), e in self._e.items() if t == tgt]

    def committed(self, commit_k, limit=None):
        out = [(s, t, dict(e)) for (s, t), e in self._e.items() if len(e["sources"]) >= commit_k]
        out.sort(key=lambda r: (r[0], r[1]))
        return out[:limit] if limit is not None else out

    def num_committed(self, commit_k):
        return sum(1 for e in self._e.values() if len(e["sources"]) >= commit_k)

    def iter_edges(self):
        for (s, t), e in self._e.items():
            yield s, t, dict(e)

    def num_nodes(self):
        return len({n for e in self._e for n in e})

    def num_edges(self):
        return len(self._e)


# ============================================================ SQLite backing


_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS edges (src INTEGER, tgt INTEGER, cnt INTEGER, PRIMARY KEY (src, tgt));
CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges (tgt);
CREATE TABLE IF NOT EXISTS edge_rel (src INTEGER, tgt INTEGER, rel TEXT, PRIMARY KEY (src, tgt, rel));
CREATE TABLE IF NOT EXISTS edge_src (src INTEGER, tgt INTEGER, source TEXT, PRIMARY KEY (src, tgt, source));
"""


class SqliteEdgeStore(EdgeStore):
    """B-tree-indexed edges on disk. The database file IS the persisted geometry —
    no whole-web load, no full rewrite; ``observe`` upserts one edge at a time."""

    def __init__(self, path: str | Path = ":memory:", node_cache_cap: int = 100_000):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
        self.db.executescript(_SCHEMA)
        self._nid: dict[str, int] = {}          # name -> id cache (capped)
        self._cap = node_cache_cap

    # -- node interning
    def _node_id(self, name: str) -> int:
        cached = self._nid.get(name)
        if cached is not None:
            return cached
        cur = self.db.execute("SELECT id FROM nodes WHERE name=?", (name,))
        row = cur.fetchone()
        if row is None:
            cur = self.db.execute("INSERT INTO nodes(name) VALUES(?)", (name,))
            nid = cur.lastrowid
        else:
            nid = row[0]
        if len(self._nid) >= self._cap:         # bounded cache — never grows past cap
            self._nid.clear()
        self._nid[name] = nid
        return nid

    def _name(self, nid: int) -> str:
        return self.db.execute("SELECT name FROM nodes WHERE id=?", (nid,)).fetchone()[0]

    def bump(self, src, tgt, rel, source, source_cap):
        s, t = self._node_id(src), self._node_id(tgt)
        self.db.execute(
            "INSERT INTO edges(src,tgt,cnt) VALUES(?,?,1) "
            "ON CONFLICT(src,tgt) DO UPDATE SET cnt=cnt+1",
            (s, t),
        )
        self.db.execute("INSERT OR IGNORE INTO edge_rel(src,tgt,rel) VALUES(?,?,?)", (s, t, rel))
        n = self.db.execute("SELECT COUNT(*) FROM edge_src WHERE src=? AND tgt=?", (s, t)).fetchone()[0]
        if n < source_cap:
            self.db.execute("INSERT OR IGNORE INTO edge_src(src,tgt,source) VALUES(?,?,?)", (s, t, source))

    def put(self, src, tgt, info):
        s, t = self._node_id(src), self._node_id(tgt)
        self.db.execute("INSERT INTO edges(src,tgt,cnt) VALUES(?,?,?) "
                        "ON CONFLICT(src,tgt) DO UPDATE SET cnt=?", (s, t, info["count"], info["count"]))
        self.db.executemany("INSERT OR IGNORE INTO edge_rel(src,tgt,rel) VALUES(?,?,?)",
                            [(s, t, r) for r in info["frames"]])
        self.db.executemany("INSERT OR IGNORE INTO edge_src(src,tgt,source) VALUES(?,?,?)",
                            [(s, t, so) for so in info["sources"]])

    def _info(self, s: int, t: int, cnt: int) -> dict:
        rels = self.db.execute(
            "SELECT group_concat(rel,?) FROM edge_rel WHERE src=? AND tgt=?", (_SEP, s, t)
        ).fetchone()[0]
        srcs = self.db.execute(
            "SELECT group_concat(source,?) FROM edge_src WHERE src=? AND tgt=?", (_SEP, s, t)
        ).fetchone()[0]
        return {
            "count": cnt,
            "frames": set(rels.split(_SEP)) if rels else set(),
            "sources": set(srcs.split(_SEP)) if srcs else set(),
        }

    def get(self, src, tgt):
        s = self.db.execute("SELECT id FROM nodes WHERE name=?", (src,)).fetchone()
        t = self.db.execute("SELECT id FROM nodes WHERE name=?", (tgt,)).fetchone()
        if not s or not t:
            return None
        row = self.db.execute("SELECT cnt FROM edges WHERE src=? AND tgt=?", (s[0], t[0])).fetchone()
        return self._info(s[0], t[0], row[0]) if row else None

    def out_edges(self, src):
        s = self.db.execute("SELECT id FROM nodes WHERE name=?", (src,)).fetchone()
        if not s:
            return []
        rows = self.db.execute(
            "SELECT n.name, e.tgt, e.cnt FROM edges e JOIN nodes n ON n.id=e.tgt WHERE e.src=?", (s[0],)
        ).fetchall()
        return [(name, self._info(s[0], t, cnt)) for name, t, cnt in rows]

    def in_edges(self, tgt):
        t = self.db.execute("SELECT id FROM nodes WHERE name=?", (tgt,)).fetchone()
        if not t:
            return []
        rows = self.db.execute(
            "SELECT n.name, e.src, e.cnt FROM edges e JOIN nodes n ON n.id=e.src WHERE e.tgt=?", (t[0],)
        ).fetchall()
        return [(name, self._info(s, t[0], cnt)) for name, s, cnt in rows]

    def committed(self, commit_k, limit=None):
        q = (
            "SELECT ns.name, nt.name, e.src, e.tgt, e.cnt FROM edges e "
            "JOIN nodes ns ON ns.id=e.src JOIN nodes nt ON nt.id=e.tgt "
            "WHERE (SELECT COUNT(*) FROM edge_src x WHERE x.src=e.src AND x.tgt=e.tgt) >= ? "
            "ORDER BY ns.name, nt.name"
        )
        params: tuple = (commit_k,)
        if limit is not None:
            q += " LIMIT ?"
            params += (limit,)
        return [(sn, tn, self._info(s, t, cnt)) for sn, tn, s, t, cnt in self.db.execute(q, params)]

    def num_committed(self, commit_k):
        return self.db.execute(
            "SELECT COUNT(*) FROM edges e WHERE "
            "(SELECT COUNT(*) FROM edge_src x WHERE x.src=e.src AND x.tgt=e.tgt) >= ?", (commit_k,)
        ).fetchone()[0]

    def iter_edges(self):
        for sn, tn, s, t, cnt in self.db.execute(
            "SELECT ns.name, nt.name, e.src, e.tgt, e.cnt FROM edges e "
            "JOIN nodes ns ON ns.id=e.src JOIN nodes nt ON nt.id=e.tgt"
        ):
            yield sn, tn, self._info(s, t, cnt)

    def num_nodes(self):
        return self.db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    def num_edges(self):
        return self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    def commit(self) -> None:
        self.db.commit()

    def close(self):
        self.db.commit()
        self.db.close()


# ============================================================ sharded backing


def _default_route(src: str, n: int) -> int:
    """Route by a stable hash of the SOURCE concept, so all of a concept's
    out-edges (its forward relations) live on one shard."""
    h = 0
    for ch in src:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h % n


class ShardedEdgeStore(EdgeStore):
    """Fan a web across N shard stores by source concept. Forward queries
    (``out_edges``, ``get``, ``bump``) hit exactly one shard; reverse queries
    (``in_edges``) and global scans fan out. No single shard holds the whole web —
    the geometry can exceed any one process or file."""

    def __init__(self, shards: list[EdgeStore], route=_default_route):
        self.shards = shards
        self._route = route

    def _shard(self, src: str) -> EdgeStore:
        return self.shards[self._route(src, len(self.shards))]

    def bump(self, src, tgt, rel, source, source_cap):
        self._shard(src).bump(src, tgt, rel, source, source_cap)

    def put(self, src, tgt, info):
        self._shard(src).put(src, tgt, info)

    def get(self, src, tgt):
        return self._shard(src).get(src, tgt)

    def out_edges(self, src):
        return self._shard(src).out_edges(src)

    def in_edges(self, tgt):
        out: list = []
        for sh in self.shards:
            out.extend(sh.in_edges(tgt))
        return out

    def committed(self, commit_k, limit=None):
        out: list = []
        for sh in self.shards:
            out.extend(sh.committed(commit_k, limit))
        out.sort(key=lambda r: (r[0], r[1]))
        return out[:limit] if limit is not None else out

    def num_committed(self, commit_k):
        return sum(sh.num_committed(commit_k) for sh in self.shards)

    def iter_edges(self):
        for sh in self.shards:
            yield from sh.iter_edges()

    def num_nodes(self):
        return sum(sh.num_nodes() for sh in self.shards)   # approx (shared concepts recur per shard)

    def num_edges(self):
        return sum(sh.num_edges() for sh in self.shards)

    def commit(self) -> None:
        for sh in self.shards:
            if hasattr(sh, "commit"):
                sh.commit()

    def close(self):
        for sh in self.shards:
            sh.close()
