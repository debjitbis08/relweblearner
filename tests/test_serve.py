"""Acceptance for the SERVED creature — the last CI guardrail of the plan.

The dev doc's headline claim (P3) must hold at the product surface, not just in
unit tests: a trained creature behind the API answers held-out compositions
EXACTLY (Hits@1 = 1.0) by transport, the study surface (sectors, defects,
growth, numbers, bus) is visible through the API, and the trainer/server
concurrency seams (log counter refresh, cross-process lock) behave. Endpoints
are called as plain functions — the guardrail is about the served creature's
behaviour, not HTTP plumbing.
"""

from __future__ import annotations

import importlib

import pytest

from relweblearner.creature import Creature
from relweblearner.datasets import mathbooks as MB
from relweblearner.episodelog import JsonlEpisodeLog, creature_lock

_PARAMS = dict(commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000, seed=5)

# hold out the "is before" direction for these adjacent pairs; the converse
# ("Y comes after X") is still taught, so the answers exist only by transport
_HELD = [(MB.NUMBERS[i], MB.NUMBERS[i + 1]) for i in (1, 3, 5, 7)]


@pytest.fixture()
def served(tmp_path, monkeypatch):
    cpath = tmp_path / "scholar.json"
    drop = {(a, "is", "before", b) for a, b in _HELD}
    eps = [e for e in MB.generate(n_episodes=4000, level=1, seed=3)[0]
           if tuple(e["tokens"]) not in drop]
    c = Creature("scholar", log=JsonlEpisodeLog(cpath.with_suffix(".episodes.jsonl")), **_PARAMS)
    c.ingest(eps)
    c.save(cpath)
    c.close()

    monkeypatch.setenv("RELWEB_CREATURE", "scholar")
    monkeypatch.setenv("RELWEB_DATA", str(cpath))
    # the module, not the FastAPI instance serve/__init__ re-exports as `.app`
    app_mod = importlib.import_module("relweblearner.serve.app")
    return importlib.reload(app_mod)


def test_served_creature_holdout_hits_at_1(served):
    # sanity: the held-out facts truly have no stored edge
    c = served._fresh_creature()
    for a, b in _HELD:
        assert c.edges.get(a, b) is None

    hits = 0
    for a, b in _HELD:
        r = served.ask(served.AskIn(text=f"{a} is before ?"))
        top = r["answers"][0]
        assert top["status"] == "derived"          # transport, not recall
        hits += top["answer"] == b
    assert hits / len(_HELD) == 1.0                # the P3 guarantee, at the API

    # taught facts still answer from testimony, exactly
    r = served.ask(served.AskIn(text="eight comes after ?"))
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("seven", "committed")


def test_api_exposes_the_study_surface(served):
    snap = served.status()
    for key in ("sectors", "defects", "growth", "numbers", "bus", "log", "relations_refused"):
        assert key in snap, f"snapshot lacks {key} — the UI cannot study the system"
    assert any(s["sector"] == "antisymmetric" for s in snap["sectors"])
    assert snap["log"]["entries"] > 0


def test_feed_persists_and_replays(served):
    r = served.feed(served.FeedIn(text="zeta comes after epsilon", picture="zeta", book="hand-1"))
    assert r["observation"]["parsed"] and r["observation"]["fact"] == ("zeta", "epsilon")
    served.feed(served.FeedIn(text="zeta comes after epsilon", picture="zeta", book="hand-2"))
    # committed at two books, and the write-ahead log holds both entries
    r2 = served.ask(served.AskIn(text="zeta comes after ?"))
    assert (r2["answers"][0]["answer"], r2["answers"][0]["status"]) == ("epsilon", "committed")
    assert len(served._LOG) == served._fresh_creature().log_position


def test_feed_refuses_while_the_trainer_holds_the_lock(served):
    with creature_lock(served.DATA.parent):        # simulate a running training tick
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            served.feed(served.FeedIn(text="one comes after zero", picture="one", book="x"))
        assert exc.value.status_code == 409
    # lock released: the same feed goes through
    r = served.feed(served.FeedIn(text="one comes after zero", picture="one", book="x"))
    assert r["observation"]["parsed"]


def test_api_corrects_a_mistake_in_place(served):
    """A wrong fact taught through the app is fixed without a retrain: retract
    the claim, or correct it, through the API — durable, claim-granular."""
    # teach a deliberate mistake (twice, so it commits)
    served.feed(served.FeedIn(text="theta comes after eta", picture="theta", book="oops-1"))
    served.feed(served.FeedIn(text="theta comes after eta", picture="theta", book="oops-2"))
    assert served.ask(served.AskIn(text="theta comes after ?"))["answers"][0]["status"] == "committed"

    # correct it: theta comes after ZETA, not eta
    out = served.correct(served.CorrectIn(source="theta", wrong="eta", right="zeta"))
    assert out["correction"]["matched"] >= 2 and out["correction"]["status"] == "committed"
    r = served.ask(served.AskIn(text="theta comes after ?"))
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("zeta", "committed")

    # and the fix is durable — the served creature reloads from the checkpoint
    c = served._fresh_creature()
    c.rebuild()
    assert c.edges.get("theta", "eta") is None


def test_api_retract_refuses_while_the_trainer_holds_the_lock(served):
    served.feed(served.FeedIn(text="iota comes after theta", picture="iota", book="h1"))
    served.feed(served.FeedIn(text="iota comes after theta", picture="iota", book="h2"))
    with creature_lock(served.DATA.parent):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            served.retract(served.RetractIn(source="iota", target="theta"))
        assert exc.value.status_code == 409


def test_api_exposes_the_trust_ledger(served):
    """A correction teaches the served creature whom to doubt: the books that
    taught the lie turn up distrusted in /api/trust, in that relation class."""
    served.feed(served.FeedIn(text="kappa comes after mu", picture="kappa", book="oops-1"))
    served.feed(served.FeedIn(text="kappa comes after mu", picture="kappa", book="oops-2"))
    served.correct(served.CorrectIn(source="kappa", wrong="mu", right="iota"))

    rows = served.trust()["trust"]
    dinged = {r["source"] for r in rows if r["standing"] == "distrusted"}
    assert {"oops-1", "oops-2"} <= dinged
    for r in rows:
        if r["source"] in ("oops-1", "oops-2") and r["standing"] == "distrusted":
            assert r["bad"] >= 1 and r["weight"] < 1.0
            assert "after" in r["class"]           # the class is named, legibly
    # fiat voices carry no reputation
    assert not any(r["source"].startswith("correction") for r in rows)
