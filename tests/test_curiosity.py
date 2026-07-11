"""Acceptance for CURIOSITY (PQ) — the wonder ledger + oracle ticks.

The creature already knows what it doesn't know: unanswered parsed questions,
provisional edges (one witness short), and standing conflicts revise() can't
settle. This phase puts those on the record as WONDERS (act entries; the open
ledger is a projection of the log, like trust) and adds a budgeted TICK that
routes them to declared ORACLES and ingests the answers as ORDINARY TESTIMONY —
k-witness gated, per-domain trusted, replay-retractable. Curiosity is a policy
layer: it may schedule observations, never edit beliefs. See
docs/spec-curiosity.md.

All offline: oracles here are inline tables. The gate below keeps the suite
green until the phase lands; delete nothing when it does.
"""

from __future__ import annotations

import json

import pytest

CU = pytest.importorskip("relweblearner.curiosity")

from relweblearner.creature import Creature
from relweblearner.episodelog import InMemoryEpisodeLog

COLOUR = {"bear": "red", "cat": "blue", "frog": "green", "duck": "yellow",
          "cow": "brown", "pig": "grey", "owl": "white", "ant": "black"}
LEGS = {"bear": "four", "cat": "four", "duck": "two", "bird": "two",
        "spider": "eight", "ant": "six", "owl": "two"}

COLOUR_FRAME = ["the", "{s}", "is", "{o}"]
LEGS_FRAME = ["{s}", "has", "{o}", "legs"]


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
    return Creature("wonderer", log=InMemoryEpisodeLog(), **params)


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


def _open(c: Creature, **match) -> list[dict]:
    return [w for w in CU.wonders(c)
            if all(w.get(k) == v for k, v in match.items())]


def _oracle(oid, table, frames, anchors, domain="test"):
    """An inline offline oracle: one relation, one lookup table."""
    return CU.Oracle(
        id=oid, anchors=frozenset(anchors), frames=frames, domain=domain,
        lookup=lambda subject: ([(subject, table[subject])] if subject in table else []),
    )


# ================================================== 1. the wonder ledger


def test_unanswered_parsed_question_mints_a_wonder():
    c = _teach(_creature())
    # spider is KNOWN (has legs) but was never taught a colour: parsed, unanswerable
    r = c.answer("the spider is ?")
    assert not r.get("known")
    ws = _open(c, qkind="unknown", subject="spider")
    assert len(ws) == 1
    w = ws[0]
    assert "is" in tuple(w["anchors"])          # the relation's stable name rides along
    assert w["sought"] == 0                     # never attempted yet


def test_reasking_dedups_and_junk_mints_nothing():
    c = _teach(_creature())
    c.answer("the spider is ?")
    c.answer("the spider is ?")                              # same question again
    assert len(_open(c, qkind="unknown", subject="spider")) == 1
    before = len(CU.wonders(c))
    c.answer("wibble wobble")                                # unparsed: no frame, no wonder
    assert len(CU.wonders(c)) == before


def test_minting_refuses_at_wonder_cap():
    c = _teach(_creature(wonder_cap=1))
    c.ingest([{"book": "x1", "tokens": ["crab", "has", "eight", "legs"], "picture": "crab"},
              {"book": "x1", "tokens": ["wasp", "has", "six", "legs"], "picture": "wasp"}] * 2)
    c.answer("the spider is ?")
    c.answer("the crab is ?")                   # over cap: refused, not minted
    assert len(_open(c, qkind="unknown")) == 1  # P7: refuse, don't flood


def test_open_ledger_survives_full_rebuild():
    c = _teach(_creature())
    c.answer("the spider is ?")
    wid = _open(c, qkind="unknown", subject="spider")[0]["wid"]
    c2 = c.rebuild()                            # replay the log from zero
    assert wid in {w["wid"] for w in _open(c2, qkind="unknown")}


def test_provisional_edge_is_a_confirm_wonder_and_ranks_before_unknown():
    c = _teach(_creature())
    # one book alone (even repeating itself) is one witness: provisional
    c.ingest([{"book": "b9", "tokens": ["the", "fox", "is", "red"], "picture": "fox"}] * 2)
    assert _ans(c, "the fox is ?") == ("red", "provisional")
    c.answer("the spider is ?")                 # an unknown, to rank against
    ws = CU.wonders(c)
    kinds = [w["qkind"] for w in ws]
    fox = _open(c, qkind="confirm", subject="fox")
    assert fox and fox[0].get("object") == "red"
    assert kinds.index("confirm") < kinds.index("unknown")   # cheapest commits first


# ================================================== 2. oracles (declared)


def test_oracles_from_json_builds_all_kinds_offline(tmp_path):
    path = tmp_path / "oracles.json"
    path.write_text(json.dumps({"oracles": [
        {"id": "toy-colours", "kind": "triples", "anchors": ["is"], "domain": "colours",
         "frames": [COLOUR_FRAME], "triples": [["fox", "red"]]},
        {"id": "wd-capital", "kind": "wikidata-lookup", "anchors": ["capital"],
         "property": "P36", "frames": [["{s}", "has", "capital", "{o}"]],
         "domain": "geography"},
        {"id": "wn-isa", "kind": "wordnet-lookup", "anchors": ["kind"],
         "frames": [["a", "{s}", "is", "a", "{o}"]], "domain": "taxonomy"},
    ]}))
    oracles = CU.oracles_from_json(path)        # lookups are lazy: no network here
    assert {o.id for o in oracles} == {"toy-colours", "wd-capital", "wn-isa"}
    toy = next(o for o in oracles if o.id == "toy-colours")
    assert toy.lookup("fox") == [("fox", "red")]
    assert toy.lookup("owl") == []


# ================================================== 3. the tick


def test_tick_confirms_a_provisional_fact_via_one_corroborating_oracle():
    c = _teach(_creature())
    c.ingest([{"book": "b9", "tokens": ["the", "fox", "is", "red"], "picture": "fox"}] * 2)
    wid = _open(c, qkind="confirm", subject="fox")[0]["wid"]
    out = CU.tick(c, [_oracle("orc-colours", {"fox": "red"}, [COLOUR_FRAME], {"is"})])
    assert wid in out["resolved"]
    assert _ans(c, "the fox is ?") == ("red", "committed")   # second independent witness
    assert not _open(c, qkind="confirm", subject="fox")


def test_single_oracle_answers_provisionally_and_chains_a_confirm():
    c = _teach(_creature())
    c.answer("the spider is ?")
    out = CU.tick(c, [_oracle("orc-colours", {"spider": "black"}, [COLOUR_FRAME], {"is"})])
    # no longer ignorant -> the unknown resolves; but ONE oracle can never commit
    assert _ans(c, "the spider is ?") == ("black", "provisional")
    assert not _open(c, qkind="unknown", subject="spider")
    assert out["resolved"]
    # ...and the thin edge immediately re-surfaces as a standing confirm wonder
    assert _open(c, qkind="confirm", subject="spider")


def test_two_independent_oracles_commit():
    c = _teach(_creature())
    c.answer("the spider is ?")
    CU.tick(c, [_oracle("orc-a", {"spider": "black"}, [COLOUR_FRAME], {"is"}),
                _oracle("orc-b", {"spider": "black"}, [COLOUR_FRAME], {"is"})],
            corroborate=2)
    assert _ans(c, "the spider is ?") == ("black", "committed")


def test_budget_attempts_exactly_that_many():
    c = _teach(_creature())
    c.ingest([{"book": "x1", "tokens": [s, "has", n, "legs"], "picture": s}
              for s, n in (("crab", "eight"), ("wasp", "six"))] * 2)
    for s in ("spider", "bird", "crab", "wasp"):             # four unknown colours
        c.answer(f"the {s} is ?")
    assert len(_open(c, qkind="unknown")) == 4
    out = CU.tick(c, [_oracle("orc-empty", {}, [COLOUR_FRAME], {"is"})], budget=2)
    assert len(out["attempted"]) == 2                        # refuse the rest this tick
    assert len(_open(c, qkind="unknown")) == 4               # empty oracle resolved nothing
    assert sum(1 for w in _open(c, qkind="unknown") if w["sought"] > 0) == 2


def test_fruitless_wonder_parks_after_max_attempts_with_zero_belief_change():
    c = _teach(_creature())
    c.answer("the spider is ?")
    wid = _open(c, qkind="unknown", subject="spider")[0]["wid"]
    empty = [_oracle("orc-empty", {}, [COLOUR_FRAME], {"is"})]
    out1 = CU.tick(c, empty, max_attempts=2)
    assert wid in out1["attempted"]
    out2 = CU.tick(c, empty, max_attempts=2)
    assert wid in out2["parked"]                             # refusal, not fabrication
    out3 = CU.tick(c, empty, max_attempts=2)
    assert wid not in out3["attempted"]                      # parked stays parked
    assert any(w["wid"] == wid for w in CU.ledger(c)["parked"])
    assert not c.answer("the spider is ?")["known"]          # beliefs untouched


def test_unroutable_wonder_is_skipped_untouched():
    c = _teach(_creature())
    c.answer("the spider is ?")
    world_before = c.log_position
    out = CU.tick(c, [_oracle("orc-legs", {}, [LEGS_FRAME], {"legs"})])   # wrong relation
    assert out["attempted"] == []                            # no routable oracle: skip
    w = _open(c, qkind="unknown", subject="spider")[0]
    assert w["sought"] == 0                                  # must not creep toward parked
    assert not c.answer("the spider is ?")["known"]
    # nothing was taught: any new log entries are ledger acts, never world episodes
    assert all(e["kind"] != "world" for _s, e in c.log.entries(world_before))


def test_tied_conflict_is_an_arbitrate_wonder_a_third_source_informs():
    # legs taught by TWO books only -> a two-source truth a two-source lie can tie
    c = _creature()
    eps = []
    for b in ("b1", "b2", "b3"):
        eps += _book_eps(b, legs={})                         # colours from three books
    for b in ("b1", "b2"):
        eps += _book_eps(b, colour={})                       # legs from two
    c.ingest(eps * 2)
    c.ingest([{"book": lb, "tokens": ["cat", "has", "six", "legs"], "picture": "cat"}
              for lb in ("l1", "l2")] * 2)                   # committed counter-claim: 2 vs 2
    ws = _open(c, qkind="arbitrate", subject="cat")
    assert ws, "a standing conflict revise() cannot settle must be on the ledger"
    out = CU.tick(c, [_oracle("orc-legs", {"cat": "four"}, [LEGS_FRAME], {"legs"})])
    assert ws[0]["wid"] in out["resolved"]                   # informed: no longer tied
    # testimony NEVER erases testimony (the hen->bird lesson): the dissent stays
    # committed and visible -- curiosity's job was only to gather the decisive
    # margin, on the record, for a decree or trust erosion to settle later.
    ans = c.answer("cat has ? legs")
    committed = {a["answer"] for a in ans["answers"] if a["status"] == "committed"}
    assert committed == {"four", "six"}
    rel_of = c._rel_of()
    sup = lambda t: c._edge_support(c.edges.get("cat", t), rel_of)
    assert sup("four") > sup("six")                          # the tie is broken by evidence
    assert not _open(c, qkind="arbitrate", subject="cat")    # a resolved wid never reopens


# ================================================== 4. epistemic guarantees


def test_a_lying_oracle_rides_the_standard_trust_ledger():
    c = _teach(_creature())
    c.answer("the spider is ?")
    CU.tick(c, [_oracle("orc-liar", {"spider": "purple"}, [COLOUR_FRAME], {"is"})])
    assert _ans(c, "the spider is ?") == ("purple", "provisional")
    c.retract_claim("spider", "purple")                      # adjudicated wrong
    colour_class = c._rel_find(next(fid for fid, f in c.frames.items()
                                    if "is" in f.anchors))
    assert c.source_weight("orc-liar", colour_class) < 1.0   # a grain of salt, that class only


def test_tick_is_policy_only_no_oracles_means_no_change():
    c = _teach(_creature())
    c.answer("the spider is ?")
    pos = c.log_position
    out = CU.tick(c, [])
    assert out["attempted"] == [] and out["resolved"] == []
    assert c.log_position == pos                             # not even a ledger act
    assert not c.answer("the spider is ?")["known"]
