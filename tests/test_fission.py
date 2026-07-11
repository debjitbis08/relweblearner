"""Acceptance for sense fission — polysemy repaired as geometry (merge's dagger).

One surface word for two concepts welds them into one node, and a committed
reflexive fact ("the w under w" — the shape of "an orange is orange") makes the
weld visible as a SELF-LOOP whose holonomy residual is gauge-invariant: no
relabel can discharge it, and removing it would erase true testimony. The one
observation-preserving repair is FISSION: split the node, re-key the second
sense's committed edges, keep every witness — the loop itself survives as a
cross-sense bridge. Splits are evidence-gated, simulated before committed,
budgeted, logged as acts (replayable, revocable), and respected by later
testimony (commit-time sense binding).
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import mathbooks as MB
from relweblearner.store import InMemoryEdgeStore, ShardedEdgeStore, SqliteEdgeStore

_PARAMS = dict(commit_k=2, min_group=6, induction_interval=10**9, buffer_cap=64)

# a taught chain c0 < c1 < ... < c13 and a homonym "w" read at TWO positions:
# sense A between c1 and c3 (position 2), sense B between c2 and c4 (position 3).
CHAIN = [(f"c{i}", f"c{i+1}") for i in range(13)]
SENSE_A = [("c1", "w"), ("w", "c3")]
SENSE_B = [("c2", "w"), ("w", "c4")]


def _creature(*, homonym=True, loop=True):
    c = Creature("split", **_PARAMS)
    # frames by ostension marks (the scaffold path): one example each
    c.observe(["the", "c0", "under", "c1"], picture="c0", source="b1", marks=[(1, 2), (3, 4)])
    c.observe(["the", "c1", "over", "c0"], picture="c1", source="b1", marks=[(1, 2), (3, 4)])
    pairs = CHAIN + (SENSE_A + SENSE_B if homonym else [])
    for b in ("b1", "b2"):
        for s, t in pairs:
            c.observe(["the", s, "under", t], picture=s, source=b)
            c.observe(["the", t, "over", s], picture=t, source=b)
        if loop:
            c.observe(["the", "w", "under", "w"], picture="w", source=b)
    return c


def _testimony(c) -> int:
    return sum(info["count"] for _s, _t, info in c.edges.iter_edges())


def _loop_pair(c):
    """The moved loop edge — whichever way fission oriented the bridge."""
    for pair in (("w", "w#2"), ("w#2", "w")):
        if c.edges.get(*pair) is not None:
            return pair
    return None


# ------------------------------------------------------------------ the defect


def test_polysemy_self_loop_is_a_defect():
    c = _creature()
    rep = c.defects()
    assert rep["count"] >= 1 and rep["mass"] > 0
    assert any(e["edge"] == ["w", "w"] for e in rep["examples"])


# ------------------------------------------------------------------ the split


def test_fission_splits_the_word_and_keeps_every_witness():
    c = _creature()
    before = _testimony(c)
    assert c.distinguish_senses() == 1
    assert c.senses == {"w": ["w#2"]}
    assert len(c.fission_events) == 1
    # the contradiction is fully repaired...
    assert c.defects()["mass"] == 0
    # ...the loop survives as a cross-sense bridge, not an erasure
    assert c.edges.get("w", "w") is None
    assert _loop_pair(c) is not None
    # zero testimony lost: every observation still counted somewhere
    assert _testimony(c) == before


def test_both_senses_answer_at_the_surface():
    c = _creature()
    c.distinguish_senses()
    r = c.answer("the w under ?")
    assert r["known"]
    answers = {a["answer"] for a in r["answers"]}
    # sense A's target and sense B's target both answer, voiced as surface words
    assert {"c3", "c4"} <= answers
    assert all("#" not in a["answer"] for a in r["answers"])
    assert all(a["status"] == "committed" for a in r["answers"])


def test_retestimony_binds_to_the_sense_edge():
    c = _creature()
    c.distinguish_senses()
    pair = _loop_pair(c)
    n0 = c.edges.get(*pair)["count"]
    # the same reflexive sentence again must NOT re-weld the bare self-loop
    r = c.observe(["the", "w", "under", "w"], picture="w", source="b3")
    assert r["parsed"] and tuple(r["fact"]) == pair
    assert c.edges.get("w", "w") is None
    assert c.edges.get(*pair)["count"] == n0 + 1


def test_attribute_class_splits_by_role():
    # the real scholar's shape: an UNCONSTRAINED fruit->colour class where the
    # only self-loop evidence is role disjointness — every other source is a
    # fruit, every other target a colour, and "orange" alone plays both parts.
    c = Creature("kid", **_PARAMS)
    facts = [("apple", "red"), ("banana", "yellow"), ("lemon", "yellow"),
             ("lime", "green"), ("plum", "purple"), ("orange", "orange")]
    c.observe(["a", "apple", "is", "red"], picture="apple", source="b1",
              marks=[(1, 2), (3, 4)])
    for b in ("b1", "b2"):
        for s, t in facts:
            c.observe(["a", s, "is", t], picture=s, source=b)
    rep = c.defects()
    assert any(e["edge"] == ["orange", "orange"] for e in rep["examples"])
    assert c.distinguish_senses() == 1
    assert c.senses == {"orange": ["orange#2"]}
    # the loop is a cross-sense bridge: fruit keeps the word, colour is the sense
    assert c.edges.get("orange", "orange#2") is not None
    assert c.defects()["mass"] == 0
    # the sentence still voices, committed, at the surface
    r = c.answer("a orange is ?")
    assert r["known"] and r["answers"][0]["answer"] == "orange"
    assert r["answers"][0]["status"] == "committed"
    assert r["answers"][0]["sentence"] == "a orange is orange"


# ------------------------------------------------------------------ the gates


def test_bare_reflexive_lie_is_refused():
    # the loop with NO independent second-cluster evidence: a lie, not polysemy —
    # splitting would posit a concept nothing else witnesses. Refused on the
    # record; the defect stays visible (acknowledged tension, invariant #9).
    c = _creature(homonym=False)
    assert c.distinguish_senses() == 0
    assert c.senses == {}
    assert any("independent" in r["reason"] for r in c.refused_fissions)
    assert c.defects()["count"] >= 1


def test_no_defect_is_a_noop():
    c = _creature(homonym=False, loop=False)
    assert c.distinguish_senses() == 0
    assert c.senses == {} and c.refused_fissions == []


def test_reflexive_lie_on_real_corpus_stays_a_defect():
    lie = {"tokens": ["five", "comes", "after", "five"], "picture": "five", "marks": None}
    eps, _w = MB.generate(n_episodes=4000, level=1, seed=3)
    eps += [dict(lie, book="liar-1"), dict(lie, book="liar-2")]   # k-collusion commits it
    c = Creature("thinker", commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000)
    c.ingest(eps)                                    # ingest auto-runs distinguish_senses
    assert c.senses == {}
    assert any("independent" in r["reason"] for r in c.refused_fissions)
    assert c.defects()["count"] >= 1


# ------------------------------------------------------------------ replay / persistence


def test_fission_survives_rebuild():
    c = _creature()
    c.distinguish_senses()
    pair = _loop_pair(c)
    before = _testimony(c)
    c.rebuild()                                      # replay from zero re-applies the act
    assert c.senses == {"w": ["w#2"]}
    assert c.edges.get("w", "w") is None
    assert c.edges.get(*pair) is not None
    assert c.defects()["mass"] == 0
    assert _testimony(c) == before


def test_fission_is_revocable_by_replay():
    c = _creature()
    c.distinguish_senses()
    # excluding the act's log entry undoes the split on replay (invariant #6)
    act_seq = next(seq for seq, e in c.log.entries(0) if e.get("kind") == "act")
    c.retract_episodes([act_seq], reason="unsplit")
    assert c.senses == {}
    assert c.edges.get("w", "w") is not None         # the weld (and its defect) return


def test_fission_survives_save_load_roundtrip():
    c = _creature()
    c.distinguish_senses()
    pair = _loop_pair(c)
    c2 = Creature.from_dict(c.to_dict())
    assert c2.senses == {"w": ["w#2"]}
    assert c2.edges.get(*pair) is not None and c2.edges.get("w", "w") is None
    r = c2.answer("the w under ?")
    assert {"c3", "c4"} <= {a["answer"] for a in r["answers"]}
    # binding still respected after reload
    c2.observe(["the", "w", "under", "w"], picture="w", source="b3")
    assert c2.edges.get("w", "w") is None


def test_ingest_auto_splits():
    c = Creature("auto", **_PARAMS)
    eps = [
        {"tokens": ["the", "c0", "under", "c1"], "picture": "c0", "source": "b1",
         "marks": [(1, 2), (3, 4)]},
        {"tokens": ["the", "c1", "over", "c0"], "picture": "c1", "source": "b1",
         "marks": [(1, 2), (3, 4)]},
    ]
    for b in ("b1", "b2"):
        for s, t in CHAIN + SENSE_A + SENSE_B:
            eps.append({"tokens": ["the", s, "under", t], "picture": s, "source": b})
            eps.append({"tokens": ["the", t, "over", s], "picture": t, "source": b})
        eps.append({"tokens": ["the", "w", "under", "w"], "picture": "w", "source": b})
    c.ingest(eps)
    assert c.senses == {"w": ["w#2"]}
    assert c.defects()["mass"] == 0
    snap = c.snapshot()
    assert snap["senses"] == {"w": ["w#2"]}
    assert snap["fissions"]["count"] == 1


# ------------------------------------------------------------------ the store move


def test_move_edge_across_backends(tmp_path):
    stores = [InMemoryEdgeStore(), SqliteEdgeStore(tmp_path / "e.db"),
              ShardedEdgeStore([InMemoryEdgeStore(), InMemoryEdgeStore()])]
    for store in stores:
        store.bump("a", "b", "r", "s1", 16)
        store.bump("a", "b", "r", "s2", 16)
        info = store.get("a", "b")
        assert store.move_edge("a", "b", "a", "b#2")
        assert store.get("a", "b") is None
        assert store.get("a", "b#2") == info
        # a later move MERGES into the destination (replay onto accrued testimony)
        store.bump("a", "b", "r2", "s1", 16)
        assert store.move_edge("a", "b", "a", "b#2")
        m = store.get("a", "b#2")
        assert m["count"] == info["count"] + 1 and "r2" in m["frames"]
        assert m["sources"] == {"s1": 2, "s2": 1}
        # the source index followed the move: decrement-retraction still exact
        assert store.retract_source("s2") == 1
        assert store.get("a", "b#2")["sources"] == {"s1": 2}
        # moving a missing edge is a tolerated no-op (replay-with-exclusions)
        assert not store.move_edge("x", "y", "x", "y#2")
