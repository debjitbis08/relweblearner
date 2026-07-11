"""Acceptance for the episode log — invariant #5 restored under the creature.

Beliefs must be reproducible by replaying the log, revocable by replaying with
an exclusion set (invariant #6, at EPISODE granularity — the retraction the
decrement path cannot express), and a persisted creature must behave as a
checkpoint of a replay: a save that lags the log catches up by tail replay.
The opt-out (NullEpisodeLog) must be explicit and honest about what it loses.
"""

from __future__ import annotations

import pytest

from relweblearner.creature import Creature
from relweblearner.datasets import mathbooks as MB
from relweblearner.episodelog import InMemoryEpisodeLog, JsonlEpisodeLog, NullEpisodeLog

_PARAMS = dict(commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000, seed=5)


def _episodes(n=3000, level=1, seed=3):
    return MB.generate(n_episodes=n, level=level, seed=seed)[0]


def _committed(c):
    return {(s, t) for s, t, _ in c.edges.committed(c.commit_k)}


def _frames(c):
    return {f.template for f in c.frames.values()}


# --------------------------------------------------------------- reproducibility


def test_beliefs_reproducible_by_replay():
    c1 = Creature("original", **_PARAMS)
    c1.ingest(_episodes())
    # a second creature replaying the SAME log derives the same beliefs
    c2 = Creature("replayed", log=c1.log, **_PARAMS)
    c2.catch_up()
    assert _committed(c2) == _committed(c1)
    assert _frames(c2) == _frames(c1)
    assert (c2.parsed, c2.unparsed) == (c1.parsed, c1.unparsed)
    # and an in-place rebuild is a fixed point
    before = _committed(c1)
    c1.rebuild()
    assert _committed(c1) == before


def test_checkpoint_plus_tail_replay_equals_live_run():
    stream = _episodes()
    cut = len(stream) // 2

    live = Creature("live", **_PARAMS)
    live.ingest(stream)                                  # the uninterrupted run

    half = Creature("halted", **_PARAMS)
    half.ingest(stream[:cut])
    snap = half.to_dict()                                # checkpoint mid-stream
    for e in stream[cut:]:                               # the log grows past it
        half.observe(e["tokens"], picture=e.get("picture"), source=e.get("book"))

    resumed = Creature.from_dict(snap, log=half.log)     # stale checkpoint + full log
    assert len(resumed.log) > resumed.log_position
    resumed.catch_up()                                   # what load() does
    assert _committed(resumed) == _committed(live)
    assert _frames(resumed) == _frames(live)
    assert resumed.episodes_seen == live.episodes_seen


# --------------------------------------------------------------- retraction


def test_single_episode_retraction_by_replay():
    # non-adjacent numbers, so the lying edge shares no key with an honest fact.
    # The lie is planted via observe(), not ingest(): batch ingest now ends in
    # belief revision (Creature.revise, exercised in test_trust.py), which
    # adjudicates this outvoted collusion away by itself — this test is about
    # the MANUAL episode-granular tool, so it holds the creature's own judgment
    # at bay while planting.
    lie = {"tokens": ["nine", "comes", "after", "two"], "picture": "nine", "marks": None}
    c = Creature("audited", **_PARAMS)
    c.ingest(_episodes())
    for book in ("good-book-page-9", "other-book-page-3"):
        c.observe(lie["tokens"], picture=lie["picture"], source=book)
    c.commit()
    assert c.edges.get("nine", "two") is not None        # the k-collusion committed
    assert c.defects()["count"] >= 1                     # and shows as holonomy

    seqs = [seq for seq, e in c.log.entries()
            if e["kind"] == "world" and e["tokens"] == lie["tokens"]]
    honest_before = _committed(c) - {("nine", "two")}
    report = c.retract_episodes(seqs, reason="poisoned pages")

    # the lie is gone root and branch — not decremented, never replayed
    assert c.edges.get("nine", "two") is None
    assert c.defects()["count"] == 0
    # zero collateral: every honest belief survived (invariant #6's metric)
    assert _committed(c) == honest_before
    assert ("nine", "eight") in _committed(c)            # nine's true predecessor intact
    assert report["uncommitted"] == 1
    # the log still HOLDS the excluded entries — flagged, not deleted
    assert set(seqs) <= c.log.excluded()
    assert all(any(s == seq for seq, _ in c.log.entries()) for s in seqs)


def test_acts_survive_unrelated_retraction():
    c = Creature("poser", **_PARAMS)
    c.ingest(_episodes())
    r = c.answer("ten is before ?")                      # walk-off → committed grow act
    posit = r["answers"][0]["answer"]
    assert r["answers"][0]["status"] == "grown"
    first_world = next(seq for seq, e in c.log.entries() if e["kind"] == "world")
    c.retract_episodes([first_world], reason="unrelated")
    # the recorded act re-applied on replay; the posit and its allocator survive
    assert c.edges.get("ten", posit) is not None
    assert c.grown_seq >= 1
    r2 = c.answer("ten is before ?")
    assert r2["answers"][0]["answer"] == posit


# --------------------------------------------------------------- the file log


def test_jsonl_log_roundtrip_and_exclusions(tmp_path):
    path = tmp_path / "c.episodes.jsonl"
    log = JsonlEpisodeLog(path)
    a = log.append({"kind": "world", "tokens": ["a"], "picture": None, "source": "x", "marks": None})
    b = log.append({"kind": "world", "tokens": ["b"], "picture": None, "source": "y", "marks": None})
    log.exclude(a, "bad")
    log.close()

    re = JsonlEpisodeLog(path)                           # reopen: count + exclusions recovered
    assert len(re) == 2 and re.excluded() == {a}
    assert [seq for seq, _ in re.entries()] == [a, b]    # excluded entries still stream
    with pytest.raises(LookupError):
        re.exclude(99)
    re.close()


def test_jsonl_backed_creature_resumes_from_disk(tmp_path):
    lpath, cpath = tmp_path / "d.episodes.jsonl", tmp_path / "d.json"
    stream = _episodes(n=1500)
    c = Creature("durable", log=JsonlEpisodeLog(lpath), **_PARAMS)
    c.ingest(stream[:1000])
    c.save(cpath)
    for e in stream[1000:]:                              # appended after the save
        c.observe(e["tokens"], picture=e.get("picture"), source=e.get("book"))
    facts = _committed(c)
    c.close()

    c2 = Creature.load(cpath, log=JsonlEpisodeLog(lpath))   # auto tail replay
    assert c2.log_position == len(c2.log) == len(stream)
    assert _committed(c2) == facts
    c2.close()


# --------------------------------------------------------------- the opt-out


def test_null_log_is_explicit_and_decrement_only():
    c = Creature("forgetful", log=NullEpisodeLog(), **_PARAMS)
    c.ingest(_episodes(n=1500))
    assert _committed(c)                                  # it still learns...
    assert len(c.log) == 0                                # ...but retains nothing
    with pytest.raises(LookupError):
        c.retract_episodes([0])                           # replay retraction impossible
    assert c.retract_source("maths-00000")["edges_touched"] >= 0   # decrement path remains
