"""Acceptance for the hand-training session (:mod:`relweblearner.reader`).

The Reader adds no learning — it runs the R2 pipeline INCREMENTALLY and adds
session, persistence and talk-back. These tests pin that wrapper: feeding phrases
one at a time induces the same frames the batch path does, facts commit only at
the ``commit_k`` origin threshold, the referent tag orients facts, talk-back
answers from committed beliefs and refuses honestly, and a replayed log
reconstructs the session exactly.
"""

from __future__ import annotations

import pytest

from relweblearner.reader import Reader, tokenize


def _teach(r: Reader, book: str):
    """Read one small pattern book: the same six colour facts, both frames."""
    facts = [("bear", "red"), ("cat", "blue"), ("frog", "green"), ("duck", "yellow")]
    for a, c in facts:
        r.feed(f"the {a} is {c}", picture=a, book=book)
        r.feed(f"i see a {c} {a}", picture=a, book=book)


def test_tokenize_keeps_blanks_drops_punctuation():
    assert tokenize("The bear is RED.") == ["the", "bear", "is", "red"]
    assert tokenize("the bear is ?") == ["the", "bear", "is", "?"]


def test_incremental_feed_induces_both_frames():
    r = Reader()
    _teach(r, "B1")
    templates = {f["template"] for f in r.snapshot()["frames"]}
    # "the __ is __" keeps two slots (the anchor "is" separates the fillers);
    # "i see a red bear" has no anchor between "red" and "bear", so they collapse
    # into one variable-width slot (a human breakup would separate them).
    assert templates == {"the ___ is ___", "i see a ___"}


def test_referent_must_be_a_word_in_the_phrase():
    r = Reader()
    with pytest.raises(ValueError):
        r.feed("the bear is red", picture="zebu")


def test_facts_commit_only_at_the_origin_threshold():
    r = Reader(commit_k=2)
    _teach(r, "B1")
    snap = r.snapshot()
    # one book -> nothing committed yet; facts are provisional
    assert snap["committed"] == []
    assert {(f["source"], f["target"]) for f in snap["provisional"]} >= {
        ("bear", "red"), ("cat", "blue"), ("frog", "green"), ("duck", "yellow")
    }
    # a second book supplies the second origin -> the facts commit
    _teach(r, "B2")
    committed = {(f["source"], f["target"]) for f in r.snapshot()["committed"]}
    assert committed == {("bear", "red"), ("cat", "blue"), ("frog", "green"), ("duck", "yellow")}


def test_referent_tag_orients_the_fact():
    r = Reader(commit_k=1)
    _teach(r, "B1")  # induce the frames first (one page alone cannot)
    obs = r.feed("the horse is red", picture="horse", book="B1")
    assert obs["parsed"] and obs["fact"] == ("horse", "red")  # source=picture, not (red,horse)


def test_fast_map_a_novel_word_from_one_page():
    r = Reader(commit_k=1)
    _teach(r, "B1")  # establishes the frames
    obs = r.feed("the zebu is red", picture="zebu", book="B2")
    assert obs["parsed"] and obs["fact"] == ("zebu", "red")


def test_off_frame_phrase_lands_on_the_frontier():
    r = Reader()
    _teach(r, "B1")
    obs = r.feed("where is the cat", picture="cat")
    assert obs["frontier"] and not obs["parsed"]
    assert ["where", "is", "the", "cat"] in r.snapshot()["frontier"]


def test_ask_about_a_committed_referent():
    r = Reader()
    _teach(r, "B1")
    _teach(r, "B2")
    ans = r.about("bear")
    assert ans["known"]
    top = ans["beliefs"][0]
    assert top["target"] == "red" and top["status"] == "committed"


def test_ask_unheard_referent_is_honest():
    r = Reader()
    _teach(r, "B1")
    assert r.about("dragon") == {"referent": "dragon", "beliefs": [], "known": False}


def test_answer_a_blank_question_forward():
    r = Reader()
    _teach(r, "B1")
    _teach(r, "B2")
    res = r.answer("the bear is ?")
    assert res["kind"] == "answer" and res["known"]
    assert res["answers"][0]["answer"] == "red"


def test_answer_refuses_an_unparseable_question():
    r = Reader()
    _teach(r, "B1")
    res = r.answer("why is the ? blue")
    assert res["kind"] == "unparsed"


def test_say_states_committed_facts_and_reads_them_back():
    r = Reader()
    _teach(r, "B1")
    _teach(r, "B2")
    said = r.say()
    sentences = {s["sentence"] for s in said}
    # every uttered sentence must re-parse to the fact it was drawn from
    assert "the bear is red" in sentences or "i see a red bear" in sentences
    for s in said:
        toks = tokenize(s["sentence"])
        import relweblearner.curriculum as C
        st = r._derive()
        rp = C.parse(toks, st["frames"])
        assert rp is not None and C._orient(rp[1], s["fact"][0]) == tuple(s["fact"])


def test_say_about_one_referent_filters():
    r = Reader()
    _teach(r, "B1")
    _teach(r, "B2")
    said = r.say("frog")
    assert said and all(s["fact"][0] == "frog" for s in said)


def test_human_breakup_separates_adjacent_fillers():
    # the scaffold path: "i see a red bear" has no anchor between "red" and "bear",
    # so auto-induction merges them into one slot. A human breakup marking the two
    # words as separate spans defines a two-slot frame from a SINGLE example.
    r = Reader(commit_k=1)
    # marks: token 3 ("red") and token 4 ("bear") are two distinct slot fillers
    obs = r.feed("i see a red bear", picture="bear", book="Debjit", marks=[[3, 4], [4, 5]])
    assert obs["parsed"] and obs["fact"] == ("bear", "red")  # oriented by the tap
    templates = {f["template"] for f in r.snapshot()["frames"]}
    assert "i see a ___ ___" in templates  # two slots, from one marked example
    # and it now parses future same-frame phrases with no marks needed
    obs2 = r.feed("i see a blue cat", picture="cat", book="Debjit")
    assert obs2["fact"] == ("cat", "blue")


def test_human_breakup_survives_persistence(tmp_path):
    log = tmp_path / "s.jsonl"
    r = Reader(commit_k=1, log_path=log)
    r.feed("i see a red bear", picture="bear", book="Debjit", marks=[[3, 4], [4, 5]])
    r2 = Reader.load(log, commit_k=1)
    assert "i see a ___ ___" in {f["template"] for f in r2.snapshot()["frames"]}
    assert r2.about("bear")["beliefs"][0]["target"] == "red"


def test_persistence_roundtrip_reconstructs_the_session(tmp_path):
    log = tmp_path / "session.jsonl"
    r = Reader(log_path=log)
    _teach(r, "B1")
    _teach(r, "B2")
    before = r.snapshot()

    r2 = Reader.load(log)
    after = r2.snapshot()
    assert before == after
    assert r2.about("cat")["beliefs"][0]["target"] == "blue"
