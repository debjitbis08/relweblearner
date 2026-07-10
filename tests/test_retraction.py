"""Graph-native retraction — the Referee's compression prescription (parts 1 & 2)
run inside a real :class:`~relweblearner.creature.Creature`, not a toy store.

Part 1 — belief is a monotone join of per-(edge, source) summands, so a source is
retracted by DECREMENT over the edge aggregates: no episode log is consulted, a
k-source collusion un-commits the moment one colluder is removed, and every
honestly multiply-sourced fact survives untouched. See ``experiments/
experiment0p_compress.py`` for the standalone demonstration.

Part 2 — the induction buffer is a uniform RESERVOIR sample of the unparsed stream
(Algorithm R), not a recency window; it retains episodes a FIFO window of the same
cap would have long since evicted.
"""

from __future__ import annotations

import random

from relweblearner.creature import Creature
from relweblearner.store import InMemoryEdgeStore, SqliteEdgeStore


def _honest_world(n_animals=20, reps=3, seed=0):
    """Each animal has ONE colour, taught ``reps`` times across distinct books
    (distinct sources), so every fact commits at commit_k=2."""
    rng = random.Random(seed)
    cols = ["red", "blue", "green", "gold"]
    eps = []
    for i in range(n_animals):
        a, c = f"a{i}", cols[i % 4]
        for r in range(reps):
            eps.append({"source": f"book{r}", "tokens": ["the", a, "is", c], "picture": a})
    rng.shuffle(eps)
    return eps


_COLS = ["red", "blue", "green", "gold"]


def _color(i: int) -> str:
    return _COLS[i % 4]


def _committed_facts(c: Creature) -> set:
    return {(s, t) for s, t, _ in c.edges.committed(c.commit_k)}


def _make(store=None) -> Creature:
    # induction_interval below the corpus size so the "the _ is _" frame induces
    # and the honest facts parse and commit before we start retracting sources.
    c = Creature("subject", commit_k=2, min_group=6, induction_interval=20, store=store)
    c.ingest(_honest_world())
    return c


def test_collusion_uncommits_on_decrement_and_honest_facts_survive():
    c = _make()
    honest = _committed_facts(c)
    assert len(honest) == 20 and ("a0", _color(0)) in honest      # a0 -> red, honestly committed

    # a k=2 collusion fabricates a fresh lie edge a0 -> black
    for liar in ("liar1", "liar2"):
        c.observe(["the", "a0", "is", "black"], picture="a0", source=liar)
    assert ("a0", "black") in _committed_facts(c)                 # the lie committed

    # retract ONE colluder — a decrement-join over aggregates, no episode replay
    report = c.retract_source("liar1")

    assert ("a0", "black") not in _committed_facts(c)            # the lie un-committed
    assert report["uncommitted"] == 1
    assert report["committed_after"] == report["committed_before"] - 1
    assert _committed_facts(c) == honest                         # every honest fact untouched
    assert c.about("a0")["beliefs"][0]["target"] == _color(0)   # a0 still believed red


def test_retraction_is_exact_over_a_real_sqlite_store():
    # the same contract on the on-disk backend: retraction is a source-indexed
    # decrement there too, not a scan of an episode log.
    c = _make(store=SqliteEdgeStore(":memory:"))
    honest = _committed_facts(c)
    for liar in ("liar1", "liar2"):
        c.observe(["the", "a5", "is", "black"], picture="a5", source=liar)
    assert ("a5", "black") in _committed_facts(c)
    c.retract_source("liar2")
    assert ("a5", "black") not in _committed_facts(c)
    assert _committed_facts(c) == honest
    c.close()


def test_retracting_an_honest_source_only_weakens_over_committed_facts():
    # dropping one of three honest books leaves every fact still at >= 2 sources,
    # so nothing un-commits: retraction removes exactly that source's summand.
    c = _make()
    before = _committed_facts(c)
    report = c.retract_source("book0")
    assert report["uncommitted"] == 0
    assert _committed_facts(c) == before
    # and its per-source summand is genuinely gone from the aggregates
    e = c.edges.get("a0", _color(0))
    assert "book0" not in e["sources"] and len(e["sources"]) == 2


def test_per_source_counts_survive_save_load(tmp_path):
    c = _make()
    red = _color(0)
    for _ in range(4):                                            # book1 taught a0->red once already -> 5 total
        c.observe(["the", "a0", "is", red], picture="a0", source="book1")
    assert c.edges.get("a0", red)["sources"]["book1"] == 5
    path = tmp_path / "subject.json"
    c.save(path)
    d = Creature.load(path)
    assert d.edges.get("a0", red)["sources"]["book1"] == 5        # per-source tally round-tripped
    # and retraction still works after a reload (the inverse index was rebuilt)
    d.observe(["the", "a1", "is", "black"], picture="a1", source="liarX")
    d.observe(["the", "a1", "is", "black"], picture="a1", source="liarY")
    assert ("a1", "black") in _committed_facts(d)
    d.retract_source("liarX")
    assert ("a1", "black") not in _committed_facts(d)


def test_buffer_is_a_reservoir_not_a_recency_window():
    # stream many DISTINCT unparsed episodes past a small cap with induction off;
    # a FIFO window would hold only the tail, a reservoir holds a sample spanning
    # the whole stream — including episodes a same-size FIFO would have evicted.
    c = Creature("res", buffer_cap=50, induction_interval=10**9, min_group=10**9, seed=7)
    n = 2000
    for i in range(n):
        c.observe(["qqq", f"u{i}"], source="stream")             # never parses -> buffered
    assert len(c._buffer) == 50
    idx = sorted(int(ep["tokens"][1][1:]) for ep in c._buffer)
    # a FIFO of cap 50 would hold exactly u1950..u1999 (all idx >= 1950).
    assert idx[0] < 1950                                          # retained something a FIFO evicted
    assert min(idx) < n // 4 or sum(1 for i in idx if i < n // 2) >= 10   # sample spans the stream
