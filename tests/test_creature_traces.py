"""Acceptance for the creature's trace bus and simulated merges.

Invariant #4: no silent operations — every epistemic creature method emits a
well-formed bare episode onto ONE shared journal, so reflection (P6) runs over
the creature's own acts with the machinery unchanged. Invariant #8: a relation
merge is imagined on a counterfactual projection before it is committed —
cf-flagged traces ride the same bus, never enter belief, and a bad merge is
refused with a logged reason (rehearsal-refusal). Invariant #7: the act
namespace on the bus rejects external squatters.
"""

from __future__ import annotations

import pytest

from relweblearner import reflection as RF
from relweblearner.creature import Creature
from relweblearner.datasets import mathbooks as MB
from relweblearner.episode import Episode
from relweblearner.journal import NamespaceViolation

_PARAMS = dict(commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000, seed=5)

COLOUR = {"bear": "red", "cat": "blue", "frog": "green",
          "duck": "yellow", "cow": "brown", "pig": "grey"}


def _maths_creature(**kw):
    params = dict(_PARAMS)
    params.update(kw)
    c = Creature("tracer", **params)
    c.ingest(MB.generate(n_episodes=3000, level=1, seed=3)[0])
    return c


def _synonym_creature():
    """`the X is Y` and `i see a Y X` over the same hidden colour map — the
    honest-merge corpus (mirrors tests/test_relations.py)."""
    eps = []
    for book in ("b1", "b2", "b3"):
        for a, col in COLOUR.items():
            eps.append({"book": book, "tokens": ["the", a, "is", col], "picture": a})
            eps.append({"book": book, "tokens": ["i", "see", "a", col, a], "picture": a,
                        "marks": [[3, 4], [4, 5]]})
    return Creature("syn", commit_k=2, min_group=6, induction_interval=10).ingest(eps * 3)


# ------------------------------------------------------- invariant #4: emission


def test_every_epistemic_method_emits():
    c = _maths_creature()

    def emits(fn):
        n = len(c.bus)
        fn()
        new = [(eid, ep) for i, (eid, ep) in enumerate(c.bus.all_entries()) if i >= n]
        assert new, "operation emitted no trace (invariant #4)"
        for _eid, ep in new:
            assert isinstance(ep, Episode)
            assert ep.is_act_trace()          # act-namespaced ids, minted by the bus

    emits(lambda: c.observe(["one", "comes", "after", "zero"], picture="one", source="probe"))
    emits(lambda: c.ingest([{"book": "b", "tokens": ["two", "comes", "after", "one"], "picture": "two"}]))
    emits(lambda: c.ingest_source("src-x", []))
    emits(lambda: c.about("five"))
    emits(lambda: c.answer("eight is before ?"))
    emits(lambda: c.answer("gibberish"))       # even a refused parse is an act
    emits(lambda: c.say("five"))
    emits(lambda: c.snapshot())
    emits(lambda: c.defects())
    emits(lambda: c.concept_webs())
    emits(lambda: c.geometry())
    emits(lambda: c.web_view("five"))
    emits(lambda: c.web_graph())
    emits(lambda: c.mind_map())
    emits(lambda: c.embedding())
    emits(lambda: c.unify_relations())
    emits(lambda: c.retract_source("probe"))
    emits(lambda: c.catch_up())
    emits(lambda: c.rebuild())
    emits(lambda: c.retract_episodes([0], reason="test"))


def test_act_namespace_rejected_on_the_bus():
    c = _maths_creature()
    squatter = Episode("@act:evil.in", {"@act:evil.in"}, "w", {"w"}, ())
    with pytest.raises(NamespaceViolation):
        c.bus.append(squatter)                 # invariant #7 holds on the bus


def test_reflection_runs_over_creature_acts():
    c = _maths_creature()
    c.answer("eight is before ?")
    acts = RF.act_traces(c.bus)
    assert acts                                 # P6: the act stream is consumable as-is
    tags = {RF.operation_of(ep) for ep in acts}
    assert {"observe", "answer", "unify", "ingest"} <= tags
    # acts of one kind share a structural signature (the refinement key)
    observes = [ep for ep in acts if RF.operation_of(ep) == "observe"]
    assert len({RF.act_signature(ep) for ep in observes}) == 1


# ------------------------------------------------- invariant #8: simulated merges


def test_honest_merge_still_commits_with_a_trace():
    c = _synonym_creature()
    classes = {frozenset(cls) for cls in c._relation_classes()}
    assert frozenset({"the ___ is ___", "i see a ___ ___"}) in classes
    tags = [RF.operation_of(ep) for ep in RF.act_traces(c.bus)]
    assert "merge" in tags
    # the simulation itself rode the bus, cf-flagged
    assert c.bus.counts().cf > 0
    # and answers still cross frames
    assert c.answer("the bear is ?")["answers"][0]["answer"] == "red"


def test_cf_never_enters_belief():
    c = _synonym_creature()                    # ran >= 1 simulation
    c.answer("ten is before ?")                # and (in maths) growth probes elsewhere
    assert c.bus.counts().cf > 0
    assert all(not ep.cf for _eid, ep in c.bus.committed())


def test_composability_destroying_merge_is_refused():
    # Frames A and B pass every evidence gate (11 shared sources with full
    # agreement, no functional fan-out) but each also teaches the CONVERSES of
    # the other's two extra pairs. Separately the classes are clean (the 4
    # cross-converse witnesses stay under infer's link floor of 3, so no gauge
    # group welds and the baseline carries no defect); MERGED, those 4 edges
    # become self-converse inside one 15-edge class — a fraction of 0.27,
    # inside the motif band — so the merged relation loses composability.
    # Only the simulation (re-inference on the counterfactual class map) can
    # see that; every evidence gate is blind to it.
    shared = [("bear", "red"), ("cat", "blue"), ("frog", "green"),
              ("duck", "gold"), ("cow", "pink"), ("pig", "grey"),
              ("owl", "teal"), ("bee", "plum"), ("ant", "rust"),
              ("elk", "jade"), ("bat", "onyx")]
    extra_a = [("sun", "moon"), ("fox", "hen")]
    extra_b = [(t, s) for (s, t) in extra_a]
    eps = []
    for book in ("b1", "b2", "b3"):
        for s, t in shared + extra_a:
            eps.append({"book": book, "tokens": ["the", s, "likes", t], "picture": s})
        for s, t in shared + extra_b:
            eps.append({"book": book, "tokens": ["my", s, "wants", t], "picture": s})
    # min_group=10 keeps the recurring fillers under the relative anchor floor
    # (each appears in ~4 of the 50-sentence induction window; see
    # curriculum.induce_frames on why the floor scales)
    c = Creature("guard", commit_k=2, min_group=10, induction_interval=50).ingest(eps * 4)

    fa = next(fid for fid, f in c.frames.items() if "likes" in f.anchors)
    fb = next(fid for fid, f in c.frames.items() if "wants" in f.anchors)
    # refused: the classes stay separate, with a reason on the record
    assert c._rel_find(fa) != c._rel_find(fb)
    assert any(r["reason"].startswith("merged class loses homogeneity")
               for r in c.refused_merges)
    assert "refuse-merge" in {RF.operation_of(ep) for ep in RF.act_traces(c.bus)}
    # the real projection was never touched by the imagining: both classes are
    # still composable (not motifs) and the web carries no defect
    c._ensure_transports()
    assert c._sectors[c._rel_find(fa)].sector != "non-homogeneous"
    assert c._sectors[c._rel_find(fb)].sector != "non-homogeneous"
    assert c.defects()["count"] == 0
    # surfaced to the observer
    assert c.snapshot()["relations_refused"]


# ------------------------------------------------------- bus vs checkpoint


def test_bus_is_live_stream_not_checkpoint():
    c = _maths_creature()
    assert len(c.bus) > 0
    c2 = Creature.from_dict(c.to_dict())
    # a reloaded creature starts a fresh bus; its durable history is the LOG
    assert len(c2.bus) == 0
    # and replay determinism is unaffected by tracing
    c.rebuild()
    assert {(s, t) for s, t, _ in c.edges.committed(2)} \
        == {(s, t) for s, t, _ in Creature("twin", log=c.log, **_PARAMS).rebuild().edges.committed(2)}
