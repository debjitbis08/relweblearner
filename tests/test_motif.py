"""Acceptance for the MOTIF layer — inheritance as a word over existing edges.

The target behaviour (glossary §0, invariant #1: learned concepts are motifs,
never new algebra operations): a never-taught attribute is answered by walking
committed testimony end to end — ``hen -kind of-> bird -has legs-> two`` — so

    hen has ? legs        -> two   (derived, inherited through bird)
    a hen is a ?          -> bird / female  (committed lookups, untouched)
    bird has ? legs       -> two   (committed lookup, untouched)

The rule itself is evidence-scored (invariant #6: k witnesses + the P2
exception budget), its scoring rides the bus cf-flagged (invariants #4/#8),
nothing is ever reified into the store, and direct testimony always shadows
inheritance (the penguin discipline).
"""

from __future__ import annotations

from relweblearner import motif as MO
from relweblearner.creature import Creature
from relweblearner.datasets import patternbooks as PB
from relweblearner.datasets import sciencebooks as SB

# induction waits for a full corpus cycle: a tiny first batch can be locally
# skewed (five of six kind-of targets "bird") and would anchor a filler word
# into the construction, shadowing the true two-slot frame.
_PARAMS = dict(commit_k=2, min_group=6, induction_interval=30, seed=5)

KINDOF = [("duck", "bird"), ("owl", "bird"), ("hen", "bird"), ("hen", "female")]
LEGS = [("duck", "two"), ("owl", "two"), ("bird", "two"), ("spider", "eight")]
COLOUR = [("bird", "brown"), ("duck", "white"), ("owl", "grey")]


def _episodes(kindof=KINDOF, legs=LEGS, colours=COLOUR, books=("b1", "b2", "b3")):
    eps = []
    for book in books:
        for x, y in kindof:
            eps.append({"book": book, "tokens": ["a", x, "is", "a", y], "picture": x})
        for x, n in legs:
            eps.append({"book": book, "tokens": [x, "has", n, "legs"], "picture": x})
        for x, col in colours:
            eps.append({"book": book, "tokens": ["the", x, "is", col], "picture": x})
    return eps


def _creature(episodes, **kw):
    params = dict(_PARAMS)
    params.update(kw)
    return Creature("heir", **params).ingest(episodes * 3)


# ------------------------------------------------------------------ derivation


def test_inheritance_answers_never_taught_attribute():
    c = _creature(_episodes())
    # the direct fact really is absent: not taught, and (legs being an
    # unconstrained attribute class) not transport-derivable either
    assert c.edges.get("hen", "two") is None
    r = c.answer("hen has ? legs")
    assert r["known"] and r["answers"]
    a = r["answers"][0]
    assert (a["answer"], a["status"], a["via"]) == ("two", "derived", "motif")
    assert a["through"] == ["bird"]              # the justification, walkable
    assert a["sentence"] == "hen has two legs"   # voiced through the question's frame
    # "female" carries no legs testimony, so the second parent adds nothing
    assert len(r["answers"]) == 1


def test_taught_prerequisites_answer_from_testimony():
    c = _creature(_episodes())
    r = c.answer("a hen is a ?")
    got = {a["answer"]: a["status"] for a in r["answers"]}
    assert got == {"bird": "committed", "female": "committed"}
    r = c.answer("bird has ? legs")
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("two", "committed")


def test_non_functional_attribute_does_not_inherit():
    """Colour must NOT inherit: the children's committed colours contradict the
    class's, so the candidate rule fails the exception budget and hen's colour
    stays honestly unknown."""
    c = _creature(_episodes())
    r = c.answer("the hen is ?")
    assert not r["known"] and r["answers"] == []
    rows = {(m["rel"], m["via"]): m for m in c.snapshot()["motifs"]}
    colour_rules = [m for m in rows.values()
                    if any("the ___ is" in t for t in m["rel_templates"])]
    assert colour_rules and not any(m["committed"] for m in colour_rules)


def test_direct_testimony_shadows_inheritance():
    """The penguin discipline: an exception's own committed fact wins, and a
    sub-budget violation does not de-commit the rule for everyone else."""
    # filler variety in every slot keeps induction from anchoring a filler
    # ("bird"/"two" at >= dominance would become part of the construction)
    kindof = [("duck", "bird"), ("owl", "bird"), ("goose", "bird"),
              ("crow", "bird"), ("spider", "bird"), ("hen", "bird"),
              ("cat", "mammal"), ("dog", "mammal")]
    legs = [("duck", "two"), ("owl", "two"), ("goose", "two"), ("crow", "two"),
            ("bird", "two"), ("spider", "eight"), ("cat", "four"), ("dog", "four")]
    c = _creature(_episodes(kindof=kindof, legs=legs, colours=[]))
    # spider: 4 witnesses vs 1 violation = support 0.8, rule still committed…
    r = c.answer("spider has ? legs")
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("eight", "committed")
    # …and the exception answers from its OWN testimony while hen inherits
    r = c.answer("hen has ? legs")
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("two", "derived")


def test_multi_hop_inheritance_walks_to_the_nearest_testimony():
    kindof = [("duck", "bird"), ("owl", "bird"), ("hen", "chicken"), ("chicken", "bird")]
    legs = [("duck", "two"), ("owl", "two"), ("bird", "two"), ("spider", "eight")]
    c = _creature(_episodes(kindof=kindof, legs=legs, colours=[]))
    r = c.answer("hen has ? legs")
    a = r["answers"][0]
    assert (a["answer"], a["status"]) == ("two", "derived")
    assert a["through"] == ["chicken", "bird"]


def test_reverse_blank_answers_from_holders_not_enumeration():
    """The reverse question is already answered by committed direct holders;
    inheritors are deliberately NOT enumerated (P7 boundedness)."""
    c = _creature(_episodes())
    r = c.answer("? has two legs")
    got = {a["answer"] for a in r["answers"]}
    assert {"bird", "duck", "owl"} <= got and "hen" not in got
    assert all(a["status"] == "committed" for a in r["answers"])


# ------------------------------------------------------------------ the rule set


def test_rule_commitment_discipline():
    c = _creature(_episodes())
    c._ensure_transports()
    committed = [m for m in c._motifs if m.committed]
    assert committed, "the legs-through-kind-of rule must commit"
    rule = committed[0]
    assert rule.witnesses >= 2 and rule.violations == 0 and rule.support == 1.0
    # snapshot voices the rule through its constructions
    rows = [m for m in c.snapshot()["motifs"] if m["committed"]]
    assert any("legs" in t for t in rows[0]["rel_templates"])
    assert any("is a" in t for t in rows[0]["via_templates"])


def test_single_witness_does_not_commit():
    """Invariant #6: one supporting composite path is provisional, never acted on."""
    kindof = [("owl", "bird"), ("hen", "bird"), ("cat", "mammal")]
    legs = [("owl", "two"), ("bird", "two"), ("spider", "eight"), ("cat", "four")]
    c = _creature(_episodes(kindof=kindof, legs=legs, colours=[]))
    r = c.answer("hen has ? legs")
    assert not r["known"]
    c._ensure_transports()
    assert not any(m.committed for m in c._motifs)


def test_nothing_reified_and_projection_replayable():
    """Inheritance derives at query time: no entailed edge enters the store or
    the log, and a rebuild reproduces the same derived answer (invariant #5)."""
    c = _creature(_episodes())
    before = c.edges.num_edges()
    r1 = c.answer("hen has ? legs")
    assert c.edges.num_edges() == before
    assert c.edges.get("hen", "two") is None
    c.rebuild()
    r2 = c.answer("hen has ? legs")
    assert r2["answers"][0]["answer"] == r1["answers"][0]["answer"] == "two"


def test_scoring_rides_the_bus_cf_flagged():
    c = _creature(_episodes())
    c.answer("hen has ? legs")
    eps = [ep for _eid, ep in c.bus.all_entries()]
    scored = [ep for ep in eps if ".motif-score" in ep.id1]
    assert scored and all(ep.cf for ep in scored)      # imagined, on the record
    inherited = [ep for ep in eps if ".inherit" in ep.id1]
    assert inherited and not any(ep.cf for ep in inherited)


# ------------------------------------------------------------------ pure layer


def test_derive_is_pure_and_bounded():
    cmaps = {"kindof": {("hen", "bird"), ("bird", "animal")},
             "legs": {("bird", "two")}}
    rules = [MO.MotifRule("legs", "kindof", 2, 0, 1.0, True)]
    hits = MO.derive(rules, cmaps, "legs", "hen", max_depth=6)
    assert hits == [{"answer": "two", "via": "kindof", "through": ["bird"]}]
    # depth bound respected: the answer sits past the horizon
    assert MO.derive(rules, cmaps, "legs", "hen", max_depth=0) == []
    # an uncommitted rule derives nothing
    assert MO.derive([MO.MotifRule("legs", "kindof", 1, 0, 1.0, False)],
                     cmaps, "legs", "hen") == []


def test_induce_silent_cases_carry_no_vote():
    # hen has NO direct legs testimony: it may not witness the rule that would
    # answer for it (the rule voting for itself), nor count against it.
    cmaps = {"kindof": {("duck", "bird"), ("owl", "bird"), ("hen", "bird")},
             "legs": {("duck", "two"), ("owl", "two"), ("bird", "two")}}
    rules = {(r.rel, r.via): r for r in MO.induce(cmaps, commit_k=2)}
    rule = rules[("legs", "kindof")]
    assert (rule.witnesses, rule.violations, rule.committed) == (2, 0, True)


# ------------------------------------------------------------------ integration


def test_hen_inherits_legs_across_the_curriculum():
    """The whole transcript, on the real generators: pattern books teach legs
    (biological, so ``bird has two legs``), science books teach the taxonomy
    (``a hen is a bird``), and hen — given no legs fact anywhere — inherits."""
    eps_p, _ = PB.generate(n_episodes=6000, level=2, seed=0)
    eps_s, _ = SB.generate(n_episodes=3000, level=1, seed=0)
    c = Creature("scholar", commit_k=2, min_group=10,
                 induction_interval=400, buffer_cap=4000)
    c.ingest(eps_p)
    c.ingest(eps_s)

    r = c.answer("a hen is a ?")
    assert {a["answer"] for a in r["answers"] if a["status"] == "committed"} == {"bird"}
    r = c.answer("bird has ? legs")
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("two", "committed")

    assert c.edges.get("hen", "two") is None
    r = c.answer("hen has ? legs")
    a = r["answers"][0]
    assert (a["answer"], a["status"], a["via"], a["through"]) == \
        ("two", "derived", "motif", ["bird"])
