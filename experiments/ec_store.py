"""Open-world geometry at scale — the indexed store.

Streams an OPEN world (ever-new concepts) into an on-disk SQLite geometry store
and a sharded store. Unlike the closed-world soak (`ec_scale.py`), the web GROWS
without bound — this shows it (a) grows with distinct structure, (b) lives on disk
past RAM, (c) stays queryable in ~constant time per point query however large it
gets, and (d) shards across files so no single store holds the whole geometry.

Run: poetry run python experiments/ec_store.py
"""

import os
import tempfile
import time

from relweblearner.creature import Creature
from relweblearner.store import ShardedEdgeStore, SqliteEdgeStore

COLS = ["red", "blue", "green", "yellow", "brown", "grey"]


def open_world_stream(n_animals, reps):
    """Ever-new animals; each colour fact seen `reps` times across distinct books."""
    for i in range(n_animals):
        a, c = f"ax{i}", COLS[i % len(COLS)]
        for r in range(reps):
            yield {"book": f"bk{r}", "tokens": ["the", a, "is", c], "picture": a}


print("=" * 78)
print("OPEN-WORLD GEOMETRY ON DISK (SQLite store) — web grows, queries stay flat")
print("=" * 78)
print(f"{'animals':>9} {'episodes':>9} {'nodes':>8} {'edges':>8} {'db_MB':>7} "
      f"{'ingest_s':>9} {'query_us':>9}")

for n in (5_000, 50_000, 200_000):
    db = tempfile.mktemp(suffix=".db")
    c = Creature(f"scholar-{n}", commit_k=2, min_group=6, induction_interval=400,
                 store=SqliteEdgeStore(db))
    t0 = time.perf_counter()
    c.ingest(open_world_stream(n, reps=2))
    dt = time.perf_counter() - t0

    # point-query latency at this web size (indexed neighbourhood lookup)
    t1 = time.perf_counter()
    for i in range(0, n, max(1, n // 500)):
        c.about(f"ax{i}")
    q_us = (time.perf_counter() - t1) / 500 * 1e6

    mb = os.path.getsize(db) / 1e6
    s = c.snapshot()
    print(f"{n:>9} {c.episodes_seen:>9} {s['model_size']['nodes']:>8} "
          f"{s['model_size']['facts']:>8} {mb:>6.1f}M {dt:>9.2f} {q_us:>8.1f}u")
    c.close()
    os.unlink(db)

print("\n" + "=" * 78)
print("SHARDED ACROSS FILES — no single store holds the whole web")
print("=" * 78)
paths = [tempfile.mktemp(suffix=f".s{i}.db") for i in range(6)]
shards = [SqliteEdgeStore(p) for p in paths]
c = Creature("sharded", commit_k=2, min_group=6, induction_interval=400,
             store=ShardedEdgeStore(shards))
c.ingest(open_world_stream(60_000, reps=2))
c.commit()
per = [sh.num_edges() for sh in shards]
print(f"total edges: {c.edges.num_edges()}  across 6 shards: {per}")
print(f"forward query ax42 -> {c.about('ax42')['beliefs'][0]['target']} "
      f"(one shard); reverse 'blue' fans out to {len(c.edges.in_edges('blue'))} animals")
for sh in shards:
    sh.close()
for p in paths:
    os.unlink(p)
print("\n-> geometry on disk, grows with the world, O(neighbourhood) per query, shardable.")
