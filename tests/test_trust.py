"""Learned source trust + belief revision — teaching changes beliefs.

A creature must learn WHICH sources to believe, per domain: a source caught
wrong about legs is taken with a grain of salt about legs (its word alone no
longer commits, and it needs more corroboration), while its colour testimony
stays ordinary; a source with a long clean corroborated record in one class
earns sole-witness authority there and nowhere else. And a correction is
TEACHING, not surgery: the owner asserts the right fact once, the creature
notices the contradiction itself (``revise``), prefers the decree, excludes the
outweighed episodes by its own judgment, and dings the lying sources' trust.
Trust is a projection of store + log (invariant #5): it survives rebuild
because it is recomputed from the record, not stored.
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.episodelog import InMemoryEpisodeLog

COLOUR = {"bear": "red", "cat": "blue", "frog": "green", "duck": "yellow",
          "cow": "brown", "pig": "grey", "owl": "white", "ant": "black"}
LEGS = {"bear": "four", "cat": "four", "duck": "two", "bird": "two",
        "spider": "eight", "ant": "six", "owl": "two"}


def _book_eps(book: str, colour=COLOUR, legs=LEGS) -> list[dict]:
    eps = []
    for a, col in colour.items():
        eps.append({"book": book, "tokens": ["the", a, "is", col], "picture": a})
    for a, n in legs.items():
        eps.append({"book": book, "tokens": [a, "has", n, "legs"], "picture": a})
    return eps


def _creature(**kw) -> Creature:
    params = dict(commit_k=2, min_group=6, induction_interval=20, seed=5)
    params.update(kw)
    return Creature("judge", log=InMemoryEpisodeLog(), **params)


def _teach(c: Creature, books=("b1", "b2", "b3")) -> Creature:
    eps = []
    for b in books:
        eps += _book_eps(b)
    c.ingest(eps * 2)
    return c


def _ans(c: Creature, q: str):
    r = c.answer(q)
    a = r["answers"][0] if r.get("known") and r.get("answers") else None
    return (a["answer"], a["status"]) if a else (None, None)


def _legs_class(c: Creature) -> str:
    fid = next(fid for fid, f in c.frames.items() if "legs" in f.anchors)
    return c._rel_find(fid)


def _colour_class(c: Creature) -> str:
    fid = next(fid for fid, f in c.frames.items() if "is" in f.anchors)
    return c._rel_find(fid)


def _trust_row(c: Creature, source: str, relclass: str):
    return next((r for r in c.trust_report(limit=None)
                 if r["source"] == source and r["class_id"] == relclass), None)


# ------------------------------------------------------- distrust is learned


def test_a_caught_source_loses_trust_in_that_class():
    c = _teach(_creature())
    # liarbook teaches one false leg count, twice (still sub-commitment alone)
    c.ingest([{"book": "liarbook", "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}] * 2)
    assert c.source_weight("liarbook", _legs_class(c)) == 1.0     # innocent until adjudicated
    c.retract_claim("cat", "six")                                 # the lie is disqualified
    w = c.source_weight("liarbook", _legs_class(c))
    assert w < 1.0                                                # a grain of salt, learned
    row = _trust_row(c, "liarbook", _legs_class(c))
    assert row["bad"] >= 1 and row["standing"] == "distrusted"


def test_distrusted_testimony_needs_more_corroboration():
    c = _teach(_creature())
    c.ingest([{"book": "liarbook", "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}] * 2)
    c.retract_claim("cat", "six")
    # a NEW claim backed by the liar plus ONE ordinary book: raw distinct-source
    # count reaches commit_k, but the weighted support does not — provisional
    crab = [{"book": b, "tokens": ["crab", "has", "ten", "legs"], "picture": "crab"}
            for b in ("liarbook", "b1")]
    c.ingest(crab * 2)
    assert _ans(c, "crab has ? legs") == ("ten", "provisional")
    # the same shape from two ordinary books commits — the discrimination is
    # about WHO, not what
    worm = [{"book": b, "tokens": ["worm", "has", "zero", "legs"], "picture": "worm"}
            for b in ("b1", "b2")]
    c.ingest(worm * 2)
    assert _ans(c, "worm has ? legs") == ("zero", "committed")


def test_trust_is_per_domain_not_global():
    c = _teach(_creature())
    c.ingest([{"book": "liarbook", "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}] * 2)
    c.retract_claim("cat", "six")
    legs, colour = _legs_class(c), _colour_class(c)
    assert c.source_weight("liarbook", legs) < 1.0        # burnt where it lied…
    assert c.source_weight("liarbook", colour) == 1.0     # …ordinary where it didn't
    # its colour testimony still corroborates normally
    crow = [{"book": b, "tokens": ["the", "crow", "is", "purple"], "picture": "crow"}
            for b in ("liarbook", "b1")]
    c.ingest(crow * 2)
    assert _ans(c, "the crow is ?") == ("purple", "committed")


def test_trust_is_a_projection_it_survives_rebuild():
    c = _teach(_creature())
    c.ingest([{"book": "liarbook", "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}] * 2)
    c.retract_claim("cat", "six")
    w = c.source_weight("liarbook", _legs_class(c))
    assert w < 1.0
    c.rebuild()                                           # replay from zero
    assert c.source_weight("liarbook", _legs_class(c)) == w


# ------------------------------------------------------- authority is earned


def test_clean_corroborated_record_earns_authority_in_class_only():
    c = _teach(_creature(authority_k=5), books=("b1", "b2", "expert"))
    legs, colour = _legs_class(c), _colour_class(c)
    assert c.source_weight("expert", legs) == float(c.commit_k)   # 7 clean corroborated leg facts
    # its lone word now commits a NEW legs fact…
    c.ingest([{"book": "expert", "tokens": ["crab", "has", "ten", "legs"], "picture": "crab"}] * 2)
    assert _ans(c, "crab has ? legs") == ("ten", "committed")
    # …but only in the class where the record was earned: with a lower
    # authority bar it would hold in colour too, so pin the mechanism —
    c2 = _teach(_creature(authority_k=9), books=("b1", "b2", "expert"))
    assert c2.source_weight("expert", _legs_class(c2)) == 1.0     # 7 < 9: still ordinary
    c2.ingest([{"book": "expert", "tokens": ["crab", "has", "ten", "legs"], "picture": "crab"}] * 2)
    assert _ans(c2, "crab has ? legs") == ("ten", "provisional")


def test_one_lie_forfeits_authority():
    c = _teach(_creature(authority_k=5), books=("b1", "b2", "expert"))
    legs = _legs_class(c)
    assert c.source_weight("expert", legs) == float(c.commit_k)
    c.ingest([{"book": "expert", "tokens": ["cat", "has", "nine", "legs"], "picture": "cat"}] * 2)
    c.retract_claim("cat", "nine")                        # caught
    assert c.source_weight("expert", legs) < 1.0          # the cliff, not a dent


# ------------------------------------------------------- revision: teaching wins


def test_corroborated_dissent_is_kept_not_guessed():
    """Testimony never erases testimony: three books against two is either
    genuine dissent or complementary truth, and the statistics cannot tell
    (on the real scholar, 'a hen is a bird' vs 'a hen is a female' came from
    disjoint corpora WITH a decisive margin — both true). The creature keeps
    both, visibly, until it is taught or the losing camp erodes."""
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b)
    wrong_legs = dict(LEGS, owl="six")                    # two books disagree about the owl
    for b in ("m1", "m2"):
        eps += _book_eps(b, legs=wrong_legs)
    c.ingest(eps * 2)
    rep = c.revise()
    assert rep["resolved"] == []                          # no guessing, however lopsided
    assert c.edges.get("owl", "two") is not None          # both testimonies stand…
    assert c.edges.get("owl", "six") is not None
    assert any(u["reason"] == "corroborated-dissent" for u in rep["unresolved"])
    assert c.source_weight("m1", _legs_class(c)) == 1.0   # nobody blamed on a hunch


def test_teaching_settles_dissent_and_blames_the_dissenters():
    """The dissent above is settled the human way — someone TEACHES the right
    answer — and only then does the losing camp pay: episodes excluded, trust
    dinged in that class, colours untouched."""
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b)
    wrong_legs = dict(LEGS, owl="six")
    for b in ("m1", "m2"):
        eps += _book_eps(b, legs=wrong_legs)
    c.ingest(eps * 2)
    rep = c.correct("owl", "six", "two")
    assert rep["status"] == "committed" and rep["matched"] > 0
    assert c.edges.get("owl", "six") is None
    assert _ans(c, "owl has ? legs") == ("two", "committed")
    legs = _legs_class(c)
    assert c.source_weight("m1", legs) < 1.0              # dissenters marked, in class
    assert c.source_weight("m2", legs) < 1.0
    assert c.source_weight("m1", _colour_class(c)) == 1.0  # not globally
    assert c.source_weight("b1", legs) == 1.0             # the right camp untouched
    assert len(c.log.excluded()) > 0                      # flagged, never deleted


def test_a_correction_defends_itself_against_recidivist_testimony():
    """Revision runs in every ingest and a decree is durable: books re-teaching
    a corrected lie get re-excluded and dinged with no owner in the loop."""
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b, legs=dict(LEGS, owl="four"))
    c.ingest(eps * 2)
    c.correct("owl", "four", "two")
    assert _ans(c, "owl has ? legs") == ("two", "committed")
    # two NEW books re-teach the corrected lie, enough to commit it
    c.ingest([{"book": b, "tokens": ["owl", "has", "four", "legs"], "picture": "owl"}
              for b in ("r1", "r2")] * 2)
    assert c.edges.get("owl", "four") is None             # re-excluded on ingest
    assert _ans(c, "owl has ? legs") == ("two", "committed")
    assert c.source_weight("r1", _legs_class(c)) < 1.0    # the recidivists pay


def test_correction_blames_the_sources_that_taught_the_lie():
    """The full teaching loop: owner corrects one fact; the creature drops the
    old belief itself and learns to distrust the books that taught it — in the
    legs class only."""
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b, legs=dict(LEGS, owl="four"))  # everyone printed the wrong owl
    c.ingest(eps * 2)
    assert _ans(c, "owl has ? legs") == ("four", "committed")
    rep = c.correct("owl", "four", "two")
    assert rep["taught"] == "owl has two legs"
    assert rep["status"] == "committed"
    assert rep["matched"] > 0                             # the creature excluded the lie itself
    assert rep["revision"]["resolved"]                    # …via revision, not surgery
    assert _ans(c, "owl has ? legs") == ("two", "committed")
    legs, colour = _legs_class(c), _colour_class(c)
    for b in ("b1", "b2", "b3"):
        assert c.source_weight(b, legs) < 1.0             # they printed the lie
        assert c.source_weight(b, colour) == 1.0          # their colours are untainted
    # the softened books still carry cat -> four together (3 × ~0.7 ≥ 2)
    assert _ans(c, "cat has ? legs") == ("four", "committed")


def test_a_later_correction_supersedes_an_earlier_one():
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b, legs=dict(LEGS, owl="four"))
    c.ingest(eps * 2)
    c.correct("owl", "four", "six")                       # a hasty decree…
    assert _ans(c, "owl has ? legs") == ("six", "committed")
    c.correct("owl", "six", "two")                        # …outranked by a later one
    assert _ans(c, "owl has ? legs") == ("two", "committed")
    assert c.edges.get("owl", "six") is None


def test_fiat_sources_have_no_reputation():
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b, legs=dict(LEGS, owl="four"))
    c.ingest(eps * 2)
    c.correct("owl", "four", "six")
    c.correct("owl", "six", "two")                        # the first decree got excluded…
    rows = c.trust_report(limit=None)
    assert not any(r["source"].startswith("correction") for r in rows)  # …but earns no bad marks
    assert c.source_weight("correction", _legs_class(c)) == float(c.commit_k)


def test_revision_emits_traces_and_reports_collateral_shape():
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b)
    wrong_legs = dict(LEGS, owl="six")
    for b in ("m1", "m2"):
        eps += _book_eps(b, legs=wrong_legs)
    n = len(c.bus)
    c.ingest(eps * 2)
    tags = [ep.id1 for _eid, ep in c.bus.all_entries()][n:]
    assert any(".revise" in t for t in tags)              # invariant #4: adjudication on the record
    rep = c.revise()                                      # idempotent: nothing left to adjudicate
    assert rep["resolved"] == [] and rep["excluded"] == 0


def test_legitimate_multivalue_is_content_not_conflict():
    """The hen is a kind of bird AND a kind of female — a many-valued relation
    must never be adjudicated like a contradiction, even when the COMMITTED
    coverage makes it look single-valued (every other animal here has exactly
    one committed kind; only scattered single-witness testimony betrays the
    fan-out). Functionality is judged on raw testimony, so both kinds stand.
    Caught live on the real scholar: an early revision draft dropped
    'hen -> bird' (414 episodes) for 'hen -> female'."""
    c = _creature()
    kinds = {"bear": "mammal", "cat": "mammal", "duck": "bird", "cow": "mammal",
             "pig": "mammal", "ant": "insect", "frog": "amphibian"}
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b)
        for a, k in kinds.items():
            eps.append({"book": b, "tokens": ["a", a, "is", "a", k], "picture": a})
        # every book teaches the hen is a bird; only two mention it is female —
        # ASYMMETRIC support, so a wrongly-adjudicated "conflict" would have a
        # decisive winner and 'female' would actually be dropped
        eps.append({"book": b, "tokens": ["a", "hen", "is", "a", "bird"], "picture": "hen"})
        if b != "b3":
            eps.append({"book": b, "tokens": ["a", "hen", "is", "a", "female"], "picture": "hen"})
    eps = eps * 2
    # …plus scattered single-witness second kinds — the raw fan-out a real
    # corpus has, invisible to commitment but decisive about the relation
    eps.append({"book": "b1", "tokens": ["a", "duck", "is", "a", "animal"], "picture": "duck"})
    eps.append({"book": "b2", "tokens": ["a", "cow", "is", "a", "female"], "picture": "cow"})
    c.ingest(eps)
    assert c.edges.get("hen", "bird") is not None      # both kinds committed…
    assert c.edges.get("hen", "female") is not None
    rep = c.revise()
    assert rep["resolved"] == []                       # …and revision leaves them be
    assert c.edges.get("hen", "bird") is not None
    # while a decreed value conflict in the FUNCTIONAL legs class still resolves
    c.ingest([{"book": m, "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}
              for m in ("m1", "m2")] * 2)
    assert c.edges.get("cat", "six") is not None       # dissent stands until taught
    rep = c.correct("cat", "six", "four")
    assert c.edges.get("cat", "six") is None           # decree adjudicated, excluded
    assert _ans(c, "cat has ? legs") == ("four", "committed")
    assert c.edges.get("hen", "female") is not None    # the hen untouched throughout
