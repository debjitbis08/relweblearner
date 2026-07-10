"""Indexed geometry store — open-world scale, sharding, persistence.

The store externalises the ONE unbounded part of a creature's geometry (concept
nodes + algebra-valued edges + provenance) to indexed, incrementally-upserted
tables, queried by neighbourhood. These tests pin: parity with the in-memory
backing, on-disk persistence (the DB *is* the store — reopen without re-ingest),
indexed point/neighbourhood queries that never load the whole web, sharding across
files, and JSON->store migration.
"""

from __future__ import annotations

import random

from relweblearner.creature import Creature
from relweblearner.store import InMemoryEdgeStore, ShardedEdgeStore, SqliteEdgeStore
from relweblearner.datasets import patternbooks as PB


def _open_world(n_animals: int, reps: int, seed: int = 0):
    """A GROWING world: n distinct animals, each with a colour, seen `reps` times
    across distinct books (so facts commit). Exercises unbounded node growth."""
    rng = random.Random(seed)
    cols = ["red", "blue", "green", "yellow"]
    eps = []
    for i in range(n_animals):
        a, c = f"ax{i}", cols[i % 4]
        for r in range(reps):
            eps.append({"book": f"bk{r}", "tokens": ["the", a, "is", c], "picture": a})
    rng.shuffle(eps)
    return eps


def test_sqlite_backend_matches_in_memory():
    eps, world = PB.generate(n_episodes=3000, level=2, seed=1)
    mem = Creature("mem", commit_k=2, min_group=6, induction_interval=100).ingest(eps)
    sql = Creature("sql", commit_k=2, min_group=6, induction_interval=100,
                   store=SqliteEdgeStore(":memory:")).ingest(eps)
    ms, ss = mem.snapshot(), sql.snapshot()
    assert ms["model_size"]["facts"] == ss["model_size"]["facts"]
    assert ms["committed_count"] == ss["committed_count"]
    # same beliefs, answered identically
    a = next(iter(world))
    assert mem.about(a)["beliefs"][0]["target"] == sql.about(a)["beliefs"][0]["target"]
    assert mem.answer(f"the {a} is ?") == sql.answer(f"the {a} is ?")


def test_database_file_is_the_persistence(tmp_path):
    db = tmp_path / "ada.db"
    c = Creature("Ada", commit_k=2, min_group=6, induction_interval=100, store=SqliteEdgeStore(db))
    c.ingest(PB.generate(n_episodes=2000, seed=2)[0])
    edges, bear = c.edges.num_edges(), c.about("bear")["beliefs"][0]["target"]
    c.close()
    # reopen the SAME file — geometry intact, no re-ingest
    c2 = Creature("Ada", commit_k=2, store=SqliteEdgeStore(db))
    assert c2.edges.num_edges() == edges
    assert c2.about("bear")["beliefs"][0]["target"] == bear
    c2.close()


def test_open_world_geometry_grows_and_stays_queryable():
    # 2000 distinct animals -> ~2000 edges; the point is that a POINT query hits
    # only that concept's neighbourhood, never the whole (large) web.
    eps = _open_world(n_animals=2000, reps=3, seed=3)
    c = Creature("open", commit_k=2, min_group=6, induction_interval=200, store=SqliteEdgeStore(":memory:"))
    c.ingest(eps)
    assert c.edges.num_edges() == 2000              # geometry grew with distinct structure
    assert c.edges.num_nodes() >= 2000 + 4          # animals + the 4 colours
    # indexed neighbourhood query returns exactly one concept's edges
    out = c.edges.out_edges("ax1234")
    assert len(out) == 1 and out[0][0] == c.about("ax1234")["beliefs"][0]["target"]
    # and it is answered correctly without materialising the web
    assert c.answer("the ax1777 is ?")["answers"][0]["answer"] == "blue"  # 1777 % 4 == 1 -> "blue"


def test_reverse_query_uses_the_index():
    # "the __ is blue" — a reverse lookup by target; must find all blue animals.
    eps = _open_world(n_animals=40, reps=3, seed=4)
    c = Creature("rev", commit_k=2, min_group=6, induction_interval=100, store=SqliteEdgeStore(":memory:"))
    c.ingest(eps)
    ins = c.edges.in_edges("blue")
    assert ins and all(i % 4 == 1 for i in [int(s[2:]) for s, _ in ins])


def test_sharding_distributes_the_web_and_answers_correctly():
    eps, world = PB.generate(n_episodes=3000, level=2, seed=5)
    shards = [InMemoryEdgeStore() for _ in range(4)]
    c = Creature("shard", commit_k=2, min_group=6, induction_interval=100, store=ShardedEdgeStore(shards))
    c.ingest(eps)
    per = [s.num_edges() for s in shards]
    assert sum(per) == c.edges.num_edges() and all(p > 0 for p in per)   # spread across shards
    assert min(per) > 0 and max(per) < sum(per)                          # no single shard holds all
    a = next(iter(world))
    assert c.about(a)["beliefs"][0]["target"] == world[a]["colour"]


def test_json_geometry_migrates_into_the_store():
    # a creature's exported geometry (JSON) loads whole into a fresh store via put()
    src = Creature("src", commit_k=1, min_group=6, induction_interval=100).ingest(
        PB.generate(n_episodes=1500, seed=6)[0])
    geo = src.geometry()["concept_web"]["edges"]
    store = SqliteEdgeStore(":memory:")
    for e in geo:
        store.put(e["src"], e["tgt"], {"count": e["count"], "sources": e["sources"], "frames": e["rel"]})
    assert store.num_edges() == len(geo)
    s, t = geo[0]["src"], geo[0]["tgt"]
    assert store.get(s, t)["count"] == geo[0]["count"]
