"""Relation unification — recognising that different frames express the SAME
concept-web relation, so synonymous constructions answer each other.

Relation identity is the edge set a frame induces: two frames unify iff their
committed edge sets agree (evidence-gated), and a merge that would make the
relation non-functional is refused (the defect guard — the algebra's holonomy
discipline in the relation dimension).
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import patternbooks as PB

COLOUR = {"bear": "red", "cat": "blue", "frog": "green",
          "duck": "yellow", "cow": "brown", "pig": "grey"}


def _both_frames(extra=()):
    """`the X is Y` and `i see a Y X` for six animals across three books (so facts
    commit and both frames induce), plus any `extra` episodes."""
    eps = []
    for book in ("b1", "b2", "b3"):
        for a, c in COLOUR.items():
            eps.append({"book": book, "tokens": ["the", a, "is", c], "picture": a})
            eps.append({"book": book, "tokens": ["i", "see", "a", c, a], "picture": a, "marks": [[3, 4], [4, 5]]})
    return eps + list(extra)


def test_synonymous_frames_unify_distinct_ones_do_not():
    c = Creature("u", commit_k=2, min_group=6, induction_interval=100).ingest(
        PB.generate(n_episodes=3000, level=2, seed=1)[0])
    classes = {frozenset(cls) for cls in c.snapshot()["relations"]}
    # the two colour frames share a class; eats and legs are their own relations
    assert frozenset({"the ___ is ___", "i see a ___ ___"}) in classes
    assert frozenset({"the ___ eats ___"}) in classes
    assert frozenset({"___ has ___ legs"}) in classes


def test_fact_learned_in_one_frame_is_answered_in_its_synonym():
    # "moose" is taught ONLY via `i see a red moose` — never via the `is` frame.
    moose = [{"book": b, "tokens": ["i", "see", "a", "red", "moose"], "picture": "moose",
              "marks": [[3, 4], [4, 5]]} for b in ("b1", "b2")]
    c = Creature("u", commit_k=2, min_group=6, induction_interval=10).ingest(_both_frames(moose))
    # after unification, the `is` frame answers a `see`-learned fact
    res = c.answer("the moose is ?")
    assert res["kind"] == "answer" and res["known"] and res["answers"][0]["answer"] == "red"


def test_without_unification_the_synonym_cannot_answer():
    # same data, but unification disabled (needs an impossible amount of evidence):
    # the `is` frame no longer answers a fact only the `see` frame recorded.
    moose = [{"book": b, "tokens": ["i", "see", "a", "red", "moose"], "picture": "moose",
              "marks": [[3, 4], [4, 5]]} for b in ("b1", "b2")]
    c = Creature("nu", commit_k=2, min_group=6, induction_interval=10, min_shared=10_000).ingest(
        _both_frames(moose))
    assert c.snapshot()["relations"].count(["the ___ is ___"]) == 1  # is-frame stands alone
    res = c.answer("the moose is ?")
    assert not res.get("known")   # moose was never taught in the `is` relation


def test_defect_guard_refuses_a_contradicting_merge():
    c = Creature("g", agree_threshold=0.8)
    # consistent: combined map is functional -> allowed
    assert c._merge_consistent({"a": {"x"}, "b": {"y"}, "c": {"z"}}, {"a": {"x"}, "b": {"y"}})
    # contradiction: 'b' would gain two committed targets -> refused (non-functional)
    assert not c._merge_consistent({"a": {"x"}, "b": {"y"}}, {"a": {"x"}, "b": {"z"}})


def test_unification_survives_persistence(tmp_path):
    c = Creature("p", commit_k=2, min_group=6, induction_interval=100).ingest(
        PB.generate(n_episodes=3000, level=2, seed=2)[0])
    before = c.snapshot()["relations"]
    path = tmp_path / "p.json"
    c.save(path)
    c2 = Creature.load(path)
    assert c2.snapshot()["relations"] == before
    # and the reloaded creature still answers the SAME colour through both unified
    # frames (cross-frame consistency survived the round-trip)
    a = "bear"
    assert c2.answer(f"i see a ? {a}")["answers"][0]["answer"] == c2.answer(f"the {a} is ?")["answers"][0]["answer"]
