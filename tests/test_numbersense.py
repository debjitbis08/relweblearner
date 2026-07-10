"""Acceptance for the number sense — P1b construction + the P5 interface map.

The creature's number words stop being pure syntax: bare pairing episodes (no
numeral anywhere in the stream) construct the P1b chain; joint ostension pages
name classes the creature counts itself; the interface map is found by the P5
mismatch-minimizing search (extended over the chain's sign gauge) with poison
miscounts as outliers; and word-order facts the word web never heard are then
answered THROUGH the constructed chain — grown, not memorised.
"""

from __future__ import annotations

import re

from relweblearner.creature import Creature
from relweblearner.datasets import counting as CT
from relweblearner.datasets import mathbooks as MB
from relweblearner.episodelog import JsonlEpisodeLog

_PARAMS = dict(commit_k=2, min_group=10, induction_interval=400, buffer_cap=4000, seed=5)


def _cols(max_size=6, n=90, seed=7):
    return CT.make_collections(n, max_size=max_size, seed=seed)


def _words_without_ten():
    """mathbooks level-1 order sentences with every 'ten' page dropped: the
    word chain runs zero..nine and the word 'ten' is never heard in a sentence."""
    eps, _w = MB.generate(n_episodes=4000, level=1, seed=3)
    return [e for e in eps if "ten" not in e["tokens"]]


def _schooled(max_size=6, n_cols=90, n_play=2500, pages=None, words=None, **kw):
    params = dict(_PARAMS)
    params.update(kw)
    cols = _cols(max_size=max_size, n=n_cols)
    c = Creature("counter", **params)
    c.ingest_play(CT.random_stream(cols, n_play, seed=1))
    c.ingest(words if words is not None else MB.generate(n_episodes=4000, level=1, seed=3)[0])
    c.ingest(pages if pages is not None else CT.joint_pages(cols, MB.NUMBERS, n_pages=60, seed=2))
    return c, cols


# ------------------------------------------------------------- construction


def test_chain_constructed_from_bare_play():
    cols = _cols()
    play = CT.random_stream(cols, 2500, seed=1)
    # grep-proof: no token in the play stream is a numeral or a number word
    for ep in play:
        for x in {ep.id1, ep.id2} | set(ep.members1) | set(ep.members2):
            assert not re.search(r"\d", x[1:]) or x[0] in "Ko"   # gensym ids only
            assert x.split(":")[-1] not in set(MB.NUMBERS)
    c = Creature("player", **_PARAMS).ingest_play(play)
    ch = c.numbers.chain()
    assert len(ch.order) == 6                    # one class per hidden size
    assert ch.contradictions == []
    # the chain numbers a fresh pile correctly (the counting routine)
    assert c.numbers.count_fresh(["x1", "x2", "x3", "x4"])[0] == 4
    census = c.snapshot()["numbers"]
    assert census["classes"] == 6 and census["map"] is None   # nothing named yet


# ------------------------------------------------------------- the map


def test_map_found_by_search_and_poison_detected():
    cols = _cols()
    honest = CT.joint_pages(cols, MB.NUMBERS, n_pages=60, seed=2)
    # a poisoned naming, committed at k sources: "three" said over four-piles
    four_piles = [k for k, v in cols.items() if len(v) == 4][:1]
    poison = [{"book": b, "tokens": ["here", "are", "three"], "picture": "three",
               "collection": {"id": four_piles[0], "members": sorted(cols[four_piles[0]])}}
              for b in ("liar-1", "liar-2")]
    c, _ = _schooled(pages=honest + poison)

    m = c.snapshot()["numbers"]["map"]
    assert m is not None
    # every honestly named word sits at its true position (word index == size)
    for w, p in m["named"].items():
        assert MB.NUMBERS.index(w) == p
    # the coordinated lie is an offset OUTLIER, not a believed naming
    assert m["poison"] >= 1
    assert m["named"].get("three") == 3
    # and counting speaks the right words
    assert c.how_many(["a", "b", "c", "d"])["word"] == "four"
    assert c.how_many(["a", "b"])["word"] == "two"


def test_naming_below_k_does_not_commit():
    cols = _cols()
    pages = CT.joint_pages(cols, MB.NUMBERS, n_pages=60, books=("only-book",), seed=2)
    c, _ = _schooled(pages=pages)
    # one book = one source per naming: nothing commits, no map
    assert c.snapshot()["numbers"]["map"] is None
    assert c.how_many(["a", "b"])["word"] is None


# ------------------------------------------------------------- transfer


def test_word_order_learned_from_counting_not_sentences():
    # 'ten' is NEVER heard in an order sentence — the word web's chain ends at
    # nine — but piles of ten are played with and named. The order of 'ten' is
    # then answered through the CONSTRUCTED chain: grown, not memorised.
    cols = _cols(max_size=10, n=140)
    pages = CT.joint_pages(cols, MB.NUMBERS, n_pages=100, seed=2)
    assert any(p["picture"] == "ten" for p in pages)
    c, _ = _schooled(max_size=10, n_cols=140, n_play=5000,
                     words=_words_without_ten(), pages=pages)

    # the word web genuinely cannot reach 'ten'
    assert c.edges.get("nine", "ten") is None and c.edges.get("ten", "nine") is None
    r = c.answer("nine is before ?")
    a = r["answers"][0]
    assert (a["answer"], a["status"], a.get("via")) == ("ten", "derived", "counting")
    assert a["sentence"] == "nine is before ten"
    # the converse direction steps the chain the other way
    r2 = c.answer("? comes after nine")
    assert r2["answers"][0]["answer"] == "ten"
    # no growth was spent where counting already knew the answer
    assert c.growth_events == []


def test_word_web_answers_still_win_over_the_interface():
    c, _ = _schooled()
    # a taught fact answers from testimony, not the chain
    r = c.answer("eight is before ?")
    assert (r["answers"][0]["answer"], r["answers"][0]["status"]) == ("nine", "committed")
    assert "via" not in r["answers"][0]


# ------------------------------------------------------------- persistence


def test_number_sense_reprojects_on_load(tmp_path):
    lpath, cpath = tmp_path / "n.episodes.jsonl", tmp_path / "n.json"
    cols = _cols(max_size=10, n=140)
    c = Creature("counter", log=JsonlEpisodeLog(lpath), **_PARAMS)
    c.ingest_play(CT.random_stream(cols, 5000, seed=1))
    c.ingest(_words_without_ten())
    c.ingest(CT.joint_pages(cols, MB.NUMBERS, n_pages=100, seed=2))
    want = c.answer("nine is before ?")["answers"][0]["answer"]
    assert want == "ten"
    c.save(cpath)
    c.close()

    c2 = Creature.load(cpath, log=JsonlEpisodeLog(lpath))
    assert c2.answer("nine is before ?")["answers"][0]["answer"] == "ten"
    assert c2.how_many(["p1", "p2", "p3"])["word"] == "three"
    c2.close()


def test_poisoned_naming_retracts_by_replay():
    cols = _cols()
    four_piles = [k for k, v in cols.items() if len(v) == 4][:1]
    poison = [{"book": b, "tokens": ["here", "are", "three"], "picture": "three",
               "collection": {"id": four_piles[0], "members": sorted(cols[four_piles[0]])}}
              for b in ("liar-1", "liar-2")]
    c, _ = _schooled(pages=CT.joint_pages(cols, MB.NUMBERS, n_pages=60, seed=2) + poison)
    assert c.snapshot()["numbers"]["map"]["poison"] >= 1

    seqs = [seq for seq, e in c.log.entries()
            if e["kind"] == "world" and e["source"].startswith("liar-")]
    c.retract_episodes(seqs, reason="miscounted pages")
    m = c.snapshot()["numbers"]["map"]
    assert m is not None and m["poison"] == 0    # the outliers are gone, the map stands
    assert m["named"].get("three") == 3
