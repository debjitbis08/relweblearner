"""Acceptance for the transport layer — the algebra put back under the creature.

The creature must THINK, not just recall: transports inferred from converse-pair
loops (P2), never-taught facts answered by transport composition (P3), committed
contradictions visible as nonzero holonomy (invariant #9), and a persistent
walk-off paying for growth through the stock P1 engine — the learner positing a
concept no episode ever named (P1b's "negative numbers"), under a budget (P7).
"""

from __future__ import annotations

import pytest

from relweblearner import transport as TR
from relweblearner.creature import Creature
from relweblearner.datasets import mathbooks as MB

_PARAMS = dict(commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000)


def _creature(episodes, **kw):
    params = dict(_PARAMS)
    params.update(kw)
    c = Creature("thinker", **params)
    c.ingest(episodes)
    return c


def _maths_creature(drop_tokens=(), n_episodes=4000, level=1, **kw):
    eps, _w = MB.generate(n_episodes=n_episodes, level=level, seed=3)
    drop = {tuple(t) for t in drop_tokens}
    eps = [e for e in eps if tuple(e["tokens"]) not in drop]
    return _creature(eps, **kw)


def _class_of(c, *anchors):
    """The relation-class root whose frames carry exactly these anchor words."""
    for fid, f in c.frames.items():
        if f.anchors == tuple(anchors):
            return c._rel_find(fid)
    raise AssertionError(f"no frame with anchors {anchors}")


def _ask(c, q):
    r = c.answer(q)
    if not (r.get("known") and r.get("answers")):
        return None, None
    return r["answers"][0]["answer"], r["answers"][0]["status"]


# ------------------------------------------------------------------ inference


def test_converse_pair_transports_inferred():
    c = _maths_creature()
    c._ensure_transports()
    after = _class_of(c, "comes", "after")
    before = _class_of(c, "is", "before")
    sa, sb = c._sectors[after], c._sectors[before]
    # converse-linked chain generators: antisymmetric, opposite nonzero transports
    assert sa.sector == TR.ANTISYMMETRIC and sb.sector == TR.ANTISYMMETRIC
    assert sa.transport == -sb.transport and sa.transport != 0
    # one constraint group, whose web holds the whole taught number line
    assert c._rel_groups[after] == c._rel_groups[before]
    web = c._group_webs[c._rel_groups[after]]
    assert set(MB.NUMBERS) <= set(web.nodes)
    # a clean chain has no defects
    assert c.defects()["count"] == 0


def test_unlinked_attribute_class_is_unconstrained():
    c = _maths_creature(level=2, n_episodes=6000)
    c._ensure_transports()
    sides = _class_of(c, "a", "has", "sides")
    assert c._sectors[sides].sector == TR.UNCONSTRAINED
    # its gauge group is its own: never merged with the number-order group
    assert c._rel_groups[sides] != c._rel_groups[_class_of(c, "is", "before")]


def test_symmetric_relation_forced_zero():
    # a hand-built symmetric world: every pair taught in BOTH directions.
    # Enough distinct pairs that no filler crosses the relative anchor floor,
    # and enough repetition that the induction interval is reached.
    pairs = [("red", "rose"), ("blue", "sky"), ("green", "leaf"),
             ("black", "coal"), ("white", "snow"), ("grey", "stone"),
             ("gold", "sun"), ("silver", "moon"), ("brown", "soil"),
             ("pink", "shell"), ("purple", "plum"), ("orange", "fire")]
    eps = []
    for b in range(4):                                  # >= commit_k books
        for x, y in pairs:
            for s, t in ((x, y), (y, x)):
                eps.append({"book": f"m-{b}", "tokens": ["the", s, "matches", t],
                            "picture": s, "marks": None})
    eps = eps * 5                                       # past the induction interval
    c = _creature(eps)
    c._ensure_transports()
    matches = _class_of(c, "the", "matches")
    assert c._sectors[matches].sector == TR.SYMMETRIC
    assert c._sectors[matches].transport == 0


# ------------------------------------------------------------------ derivation


def test_derives_never_taught_fact_by_transport():
    held_out = ["nine", "is", "before", "ten"]
    c = _maths_creature(drop_tokens=[held_out])
    # sanity: the direct fact really is absent from the store
    assert c.edges.get("nine", "ten") is None
    # taught facts answer from testimony...
    assert _ask(c, "eight is before ?") == ("nine", "committed")
    # ...the held-out fact is DERIVED: the converse-taught "ten comes after
    # nine" composes, via the dagger, to the never-heard "nine is before ten"
    ans, status = _ask(c, "nine is before ?")
    assert (ans, status) == ("ten", "derived")
    # read-back voiced it through the question's own relation
    r = c.answer("nine is before ?")
    assert r["answers"][0]["sentence"] == "nine is before ten"
    # and the reverse blank derives with the daggered transport
    assert _ask(c, "? comes after nine") in (("ten", "committed"), ("ten", "derived"))


def test_no_cross_relation_hallucination():
    # "triangle is before ?" must stay unknown: triangle is not in the number
    # order's gauge group, and the sides class supports no derivation.
    c = _maths_creature(level=2, n_episodes=6000)
    r = c.answer("triangle is before ?")
    assert not r["known"] and not r["answers"]
    assert c.growth_events == []


# ------------------------------------------------------------------ growth


def test_walkoff_grows_posited_concept():
    c = _maths_creature()
    # "ten is before ?" has no witnessing node — the query walks off the web.
    ans, status = _ask(c, "ten is before ?")
    assert status == "grown" and ans.startswith("new-")
    ev = c.growth_events[-1]
    assert ev["move"] == "grow" and ev["new_nodes"] == [ans]
    # asking again returns the SAME posit — no duplicate growth
    ans2, status2 = _ask(c, "ten is before ?")
    assert ans2 == ans and status2 == "grown"
    assert len([e for e in c.growth_events if e["move"] == "grow"]) == 1
    # the learner's negative number: nothing comes-after zero was ever taught
    ans3, status3 = _ask(c, "zero comes after ?")
    assert status3 == "grown" and ans3.startswith("new-") and ans3 != ans


def test_growth_budget_degrades_to_refusal():
    c = _maths_creature(growth_budget=1)
    ans, status = _ask(c, "ten is before ?")
    assert status == "grown"
    r = c.answer("zero comes after ?")
    assert not r["known"] and r.get("refused") == "growth budget exhausted"
    assert len(c.growth_events) == 1


def test_act_namespace_is_reserved():
    c = Creature("guarded", **_PARAMS)
    with pytest.raises(ValueError):
        c.observe(["the", "cat", "matches", "dog"], picture="cat", source="act:grow")


# ------------------------------------------------------------------ defects


def test_committed_contradiction_is_a_defect():
    lie = {"tokens": ["four", "comes", "after", "five"], "picture": "four", "marks": None}
    eps, _w = MB.generate(n_episodes=4000, level=1, seed=3)
    eps += [dict(lie, book="liar-1"), dict(lie, book="liar-2")]   # k-collusion commits it
    c = _creature(eps)
    c._ensure_transports()
    # the poisoned converse pair is a sub-budget exception: the chain stays
    # antisymmetric, and the lie surfaces as a nonzero-holonomy loop
    after = _class_of(c, "comes", "after")
    assert c._sectors[after].sector == TR.ANTISYMMETRIC
    rep = c.defects()
    assert rep["count"] >= 1 and rep["mass"] > 0
    assert any(sorted(e["edge"]) == ["five", "four"] or sorted(e["edge"]) == ["four", "five"]
               for e in rep["examples"])


# ------------------------------------------------------------------ persistence


def test_posits_and_transports_survive_reload():
    c = _maths_creature()
    ans, status = _ask(c, "ten is before ?")
    assert status == "grown"
    c2 = Creature.from_dict(c.to_dict())
    # the posited node and its edge survive, still act-sourced (never testimony)
    ans2, status2 = _ask(c2, "ten is before ?")
    assert (ans2, status2) == (ans, "grown")
    # the id allocator resumes past the posit — no collision on the next growth
    ans3, _ = _ask(c2, "zero comes after ?")
    assert ans3 != ans
    # derived answers recompute identically from the reloaded geometry
    held = _maths_creature(drop_tokens=[["nine", "is", "before", "ten"]])
    held2 = Creature.from_dict(held.to_dict())
    assert _ask(held2, "nine is before ?") == ("ten", "derived")


# ------------------------------------------------- adversarial classification


def test_one_lying_pair_cannot_weld_two_gauge_groups():
    """A single committed pair whose converse lands in another class is not
    2-cycle evidence enough to union their gauge groups (the floor the
    infer() docstring promises). Welding on a lie is catastrophic: the
    groups' magnitudes are mutually gauged, so a weld poisons every transport
    in both. (``compositions=False`` isolates the 2-cycle floor — with
    composition mining ON these groups legitimately merge, with the RIGHT
    relative magnitudes; that is the next test.)"""
    step_f = {(f"n{i + 1}", f"n{i}") for i in range(8)}
    step_r = {(f"n{i}", f"n{i + 1}") for i in range(8)}
    skip_f = {(f"n{i + 2}", f"n{i}") for i in range(7)}
    skip_r = {(f"n{i}", f"n{i + 2}") for i in range(7)}
    # the lie: one step edge over a true skip pair — its converse is in skip+
    cmaps = {"step+": step_f | {("n3", "n1")}, "step-": step_r,
             "skip+": skip_f, "skip-": skip_r}
    sectors, groups = TR.infer(cmaps, compositions=False)
    assert groups["step+"] == groups["step-"]
    assert groups["skip+"] == groups["skip-"]
    assert groups["step+"] != groups["skip+"]        # ONE pair must not weld
    assert all(s.sector == TR.ANTISYMMETRIC for s in sectors.values())


# ------------------------------------- composition (3-cycle) discovery


def test_composition_discovered_with_relative_magnitude():
    """Committed triangles are 3-cycle loop evidence: skip = step∘step is
    DISCOVERED, the groups merge, and the solved transports carry the right
    relative magnitude (step ±1, skip ±2 in ONE gauge group) — the constraint
    the 2-cycle story could never fix. A held-out skip fact then derives by
    composing two step edges in the merged web."""
    step_f = {(f"n{i + 1}", f"n{i}") for i in range(8)}
    step_r = {(f"n{i}", f"n{i + 1}") for i in range(8)}
    skip_f = {(f"n{i + 2}", f"n{i}") for i in range(7) if i != 3}   # (n5, n3) held out
    skip_r = {(f"n{i}", f"n{i + 2}") for i in range(7) if i != 3}
    cmaps = {"step+": step_f, "step-": step_r, "skip+": skip_f, "skip-": skip_r}
    sectors, groups = TR.infer(cmaps)
    assert groups["step+"] == groups["skip+"] == groups["skip-"]
    assert abs(sectors["skip+"].transport) == 2 * abs(sectors["step+"].transport)
    assert sectors["skip+"].transport == -sectors["skip-"].transport
    webs = TR.build_group_webs(cmaps, sectors, groups)
    web = webs[groups["skip+"]]
    hits = TR.derive(web, "n5", sectors["skip+"].transport, max_depth=4)
    assert hits == ["n3"]                            # the held-out skip, by two steps


def test_junk_composition_refused_by_the_defect_gate():
    """A coincidental triangle overlap must not constrain a class: 'likes'
    chains over their own entities propose step = likes∘likes (two committed
    step edges happen to span likes chains), whose acceptance would zero the
    step group (g = 0 + 0). The gate sees the degradation and refuses; step
    stays a live ±1 generator."""
    step_f = {(f"n{i + 1}", f"n{i}") for i in range(6)}
    step_r = {(f"n{i}", f"n{i + 1}") for i in range(6)}
    likes = {("m0", "m1"), ("m1", "m0"), ("m1", "m2"), ("m2", "m1"),
             ("m3", "m4"), ("m4", "m3"), ("m4", "m5"), ("m5", "m4")}
    # the junk-shaped support: two step+ edges spanning the likes chains, so
    # the candidate step+ = likes∘likes mines — and must be refused
    cmaps = {"step+": step_f | {("m2", "m0"), ("m5", "m3")},
             "step-": step_r, "likes": likes}
    sectors, groups = TR.infer(cmaps)
    assert sectors["step+"].sector == TR.ANTISYMMETRIC
    assert sectors["step+"].transport != 0           # not zeroed by likes∘likes
    assert groups["likes"] != groups["step+"]


def test_sub_budget_lie_does_not_veto_a_true_composition():
    """One committed lie among the head's edges must not block the discovery
    (the standing P2 rule: sub-budget contradiction is reported noise). The
    composition is accepted, the merged group keeps step ±1 / skip ±2, and
    the lie stays VISIBLE as a defect instead of silently vetoing structure."""
    step_f = {(f"n{i + 1:02d}", f"n{i:02d}") for i in range(11)}
    step_r = {(f"n{i:02d}", f"n{i + 1:02d}") for i in range(11)}
    skip_f = {(f"n{i + 2:02d}", f"n{i:02d}") for i in range(10)}
    skip_r = {(f"n{i:02d}", f"n{i + 2:02d}") for i in range(10)}
    cmaps = {"step+": step_f | {("n09", "n02")},     # the lie: +1 over a span of 7
             "step-": step_r, "skip+": skip_f, "skip-": skip_r}
    sectors, groups = TR.infer(cmaps)
    assert groups["skip+"] == groups["step+"]        # discovery survived the lie
    assert abs(sectors["skip+"].transport) == 2 * abs(sectors["step+"].transport)
    webs = TR.build_group_webs(cmaps, sectors, groups)
    assert TR.defect_report(webs)["count"] >= 1      # and the lie is on display


def test_one_lie_does_not_demote_a_true_class_to_motif():
    """One committed lie can smear residuals over several fundamental cycles
    (whenever the BFS tree routes through it), so counting raw defects can
    read a single adversarial page as class-wide incoherence. The demotion
    check must attribute defects to culprits first: a true class survives one
    lie (which stays VISIBLE as a defect), while a genuinely non-homogeneous
    class still demotes."""
    step_f = {(f"n{i + 1:02d}", f"n{i:02d}") for i in range(11) if i != 3}
    step_r = {(f"n{i:02d}", f"n{i + 1:02d}") for i in range(11) if i not in (1, 6, 8)}
    cmaps = {"step+": step_f | {("n04", "n09")}, "step-": step_r}
    sectors, groups = TR.infer(cmaps)
    assert sectors["step+"].sector == TR.ANTISYMMETRIC
    webs = TR.build_group_webs(cmaps, sectors, groups)
    assert TR.non_homogeneous_by_defect(cmaps, webs) == set()
    assert TR.defect_report(webs)["count"] >= 1     # the lie is still on display

    # control: a class whose OWN edges disagree everywhere (three disjoint
    # triangles, all transports forced to the same gauge value) has no single
    # culprit and is demoted as before.
    tri = set()
    for t in range(3):
        a, b, c = f"t{t}a", f"t{t}b", f"t{t}c"
        tri |= {(a, b), (b, c), (a, c)}
    cmaps2 = {"double": tri}
    s2, g2 = TR.infer(cmaps2)
    webs2 = TR.build_group_webs(cmaps2, s2, g2)
    assert TR.non_homogeneous_by_defect(cmaps2, webs2) == {"double"}
