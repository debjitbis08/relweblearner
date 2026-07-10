"""Acceptance for the new scale corpora — ``mathbooks`` (basic maths) and
``kidbooks`` (early-reader kid content). These are the numeracy and everyday
rungs of the corpus firehose (spec §4), and the properties are the same ones
:mod:`test_creature` asserts for ``patternbooks``: a streaming :class:`Creature`
INDUCES each corpus's frames from repetition-with-substitution, COMMITS facts that
match the hidden functional world, and its model stays BOUNDED as episodes scale.

Both corpora rely on the anchored-subsequence induction separating frames by their
anchor set; the disjoint-anchor design in each generator (documented there) is
what these tests guard.
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import kidbooks as KB
from relweblearner.datasets import mathbooks as MB


def _committed(c: Creature):
    return c.snapshot()["committed"]


# ------------------------------------------------------------------- mathbooks

def test_mathbooks_induces_all_frames_and_grounds_shapes():
    c = Creature("mathematician", commit_k=2, min_group=8, induction_interval=300)
    episodes, world = MB.generate(n_episodes=8000, level=2, seed=1)
    c.ingest(episodes)
    templates = {f["template"] for f in c.snapshot()["frames"]}
    assert {
        "___ comes after ___",
        "___ is before ___",
        "a ___ has ___ sides",
    } <= templates
    # shape->sides is functional; shape ids are disjoint from number words, so a
    # source in the sides map uniquely identifies a shape fact.
    sides = MB.truth(world)
    shape_facts = [(b["source"], b["target"]) for b in _committed(c) if b["source"] in sides]
    assert shape_facts, "no shape-sides facts committed"
    assert all(sides[s] == n for s, n in shape_facts)
    # every shape was learned
    assert {s for s, _ in shape_facts} == set(sides)


def test_mathbooks_recovers_number_ordering():
    c = Creature("counter", commit_k=2, min_group=8, induction_interval=300)
    episodes, _ = MB.generate(n_episodes=8000, level=1, seed=2)  # ordering only
    c.ingest(episodes)
    idx = {w: i for i, w in enumerate(MB.NUMBERS)}
    order_facts = [
        (b["source"], b["target"]) for b in _committed(c)
        if b["source"] in idx and b["target"] in idx
    ]
    assert order_facts, "no ordering facts committed"
    # each committed (n, m) pair is a true adjacency on the number line
    assert all(abs(idx[n] - idx[m]) == 1 for n, m in order_facts)


# ------------------------------------------------------------------- kidbooks

def test_kidbooks_induces_all_frames_and_grounds_worlds():
    c = Creature("storyteller", commit_k=2, min_group=8, induction_interval=300)
    episodes, world = KB.generate(n_episodes=12000, level=3, seed=1)
    c.ingest(episodes)
    templates = {f["template"] for f in c.snapshot()["frames"]}
    assert {
        "the ___ says ___",
        "a ___ is ___",
        "the ___ lives in a ___",
        "the opposite of ___ is ___",
    } <= templates
    comm = _committed(c)
    # score each relation by its TARGET class — some animals live in the sound AND
    # habitat worlds, so the target class (not the source) is what separates them.
    def clean(mp, targets):
        facts = [(b["source"], b["target"]) for b in comm if b["target"] in targets]
        return facts and all(mp.get(s) == t for s, t in facts)

    assert clean(world["sound"], KB.SOUNDS)
    assert clean(world["colour"], KB.COLOURS)
    assert clean(world["home"], KB.PLACES)
    # opposites are symmetric: both directions were taught and committed correctly
    opp = [(b["source"], b["target"]) for b in comm
           if b["source"] in world["opposite"] and b["target"] in world["opposite"]]
    assert opp and all(world["opposite"][a] == b_ for a, b_ in opp)


def test_kidbooks_talk_back_matches_world():
    c = Creature("chatty", commit_k=2, min_group=8, induction_interval=300)
    episodes, world = KB.generate(n_episodes=12000, level=1, seed=3)  # sounds only
    c.ingest(episodes)
    a = next(iter(world["sound"]))
    res = c.answer(f"the {a} says ?")
    if res["kind"] == "answer" and res.get("known"):
        assert res["answers"][0]["answer"] == world["sound"][a]


# ------------------------------------------------------------- bounded at scale

def test_new_corpora_models_are_bounded():
    # 4x the episodes over the same closed world must not give ~4x the model.
    for gen, lvl in ((MB, 2), (KB, 3)):
        small = Creature("s", min_group=8, induction_interval=300).ingest(
            gen.generate(n_episodes=5000, level=lvl, seed=4)[0])
        big = Creature("b", min_group=8, induction_interval=300).ingest(
            gen.generate(n_episodes=20000, level=lvl, seed=4)[0])
        sm, bg = small.snapshot()["model_size"], big.snapshot()["model_size"]
        assert big.episodes_seen == 4 * small.episodes_seen
        assert bg["frames"] <= 8
        assert bg["buffer"] <= big.buffer_cap
        # facts saturate on the closed world — nowhere near 4x
        assert bg["facts"] < 2 * sm["facts"] + 5
