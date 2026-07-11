"""Fixing mistakes WITHOUT retraining from scratch (invariant #6, claim-granular).

A wrong fact is corrected by flagging the episodes that taught it excluded
(never deleted) and rebuilding by replay-with-exclusions — durable (survives a
later rebuild), claim-granular (the good facts around the lie are untouched),
and reproducible. This is the primitive the served creature and `relweb-correct`
expose so a mistake never forces a `--reset --all`.
"""

from __future__ import annotations

import pytest

from relweblearner.creature import Creature
from relweblearner.episodelog import InMemoryEpisodeLog

COLOUR = {"bear": "red", "cat": "blue", "frog": "green", "duck": "yellow",
          "cow": "brown", "pig": "grey", "owl": "white", "ant": "black"}
# a leg world with real spread (so no single value dominates the slot and gets
# anchored into the construction) — owl's "four" is the planted mistake.
LEGS = {"bear": "four", "cat": "four", "duck": "two", "bird": "two",
        "spider": "eight", "ant": "six", "owl": "four"}


def _teach(c: Creature, books=("b1", "b2", "b3")):
    eps = []
    for book in books:
        for a, col in COLOUR.items():
            eps.append({"book": book, "tokens": ["the", a, "is", col], "picture": a})
        for a, n in LEGS.items():
            eps.append({"book": book, "tokens": [a, "has", n, "legs"], "picture": a})
    c.ingest(eps * 2)
    return c


def _creature(**kw):
    params = dict(commit_k=2, min_group=6, induction_interval=20, seed=5)
    params.update(kw)
    return _teach(Creature("fixer", log=InMemoryEpisodeLog(), **params))


def _ans(c, q):
    r = c.answer(q)
    a = r["answers"][0] if r.get("known") and r.get("answers") else None
    return (a["answer"], a["status"]) if a else (None, None)


# ------------------------------------------------------------------ retraction


def test_retract_claim_un_teaches_one_fact():
    c = _creature()
    assert _ans(c, "owl has ? legs") == ("four", "committed")
    rep = c.retract_claim("owl", "four")
    assert rep["matched"] > 0
    # the lie is gone…
    assert _ans(c, "owl has ? legs") == (None, None)
    assert c.edges.get("owl", "four") is None
    # …and every OTHER fact is untouched (claim-granular, not source-granular)
    assert _ans(c, "cat has ? legs") == ("four", "committed")
    assert _ans(c, "the owl is ?") == ("white", "committed")   # owl's colour survives


def test_retraction_is_durable_across_rebuild():
    """The decrement of retract_source is lost on a rebuild; a claim retraction
    excludes the LOG episodes, so replay-from-zero keeps the fix."""
    c = _creature()
    c.retract_claim("owl", "four")
    c.rebuild()                                    # the reproducibility path
    assert c.edges.get("owl", "four") is None
    assert _ans(c, "cat has ? legs") == ("four", "committed")


def test_retract_unknown_claim_is_a_noop():
    c = _creature()
    rep = c.retract_claim("owl", "eight")          # never taught
    assert rep["matched"] == 0 and rep["uncommitted"] == 0
    assert _ans(c, "owl has ? legs") == ("four", "committed")


def test_collateral_is_reported():
    c = _creature()
    before = c.edges.num_committed(c.commit_k)
    rep = c.retract_claim("owl", "four")
    assert rep["committed_before"] == before
    assert rep["uncommitted"] == before - rep["committed_after"] >= 1


# ------------------------------------------------------------------ correction


def test_correct_retracts_and_reteaches_in_one_move():
    c = _creature()
    rep = c.correct("owl", "four", "two")
    assert rep["matched"] > 0
    assert rep["taught"] == "owl has two legs"
    assert rep["status"] == "committed"            # a correction commits authoritatively
    assert _ans(c, "owl has ? legs") == ("two", "committed")


def test_correction_provenance_is_auditable_and_reversible():
    c = _creature()
    c.correct("owl", "four", "two")
    info = c.edges.get("owl", "two")
    assert info and all(str(s).startswith("correction") for s in info["sources"])
    # the correction is itself an ordinary set of log episodes — retractable
    rep = c.retract_claim("owl", "two")
    assert rep["matched"] > 0
    assert c.edges.get("owl", "two") is None


def test_correction_survives_replay():
    c = _creature()
    c.correct("owl", "four", "two")
    c.rebuild()
    assert _ans(c, "owl has ? legs") == ("two", "committed")


def test_correct_emits_traces():
    c = _creature()
    n = len(c.bus)
    c.correct("owl", "four", "two")
    tags = [ep.id1 for _eid, ep in c.bus.all_entries()][n:]
    # teaching, then the creature's own adjudication — no surgical retract-claim
    assert any(".observe" in t for t in tags)
    assert any(".revise" in t for t in tags)
    assert any(".correct" in t for t in tags)


# ------------------------------------------------------------------ the mistake motivating this


def test_fixing_a_mistake_does_not_need_a_full_retrain():
    """The scenario from the motif work: a plainly-false leg count poisons the
    web. It is fixed in place, claim-granular, with the log intact — no
    reset-and-replay-the-whole-corpus."""
    c = _creature()
    log_len_before = len(c.log)
    c.correct("owl", "four", "two")
    # the log GREW (append-only: the lie stays flagged, the fix is new episodes)
    assert len(c.log) > log_len_before
    assert len(c.log.excluded()) > 0
    assert _ans(c, "owl has ? legs") == ("two", "committed")
