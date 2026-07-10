"""Acceptance for FACT SOURCES — turning real ``(subject, object)`` triples into
grounded episodes + auto-worksheets, and the registry caching that makes WordNet /
Wikidata sources expand the curriculum. Mostly offline; the live WordNet corpus and
Wikidata network are exercised only where available (skipped otherwise).
"""

from __future__ import annotations

import json

import pytest

from relweblearner.creature import Creature
from relweblearner.datasets import factsource as FS
from relweblearner.datasets import registry as R

_TRIPLES = [("pug", "dog"), ("corgi", "dog"), ("robin", "bird"), ("wren", "bird")]
_FRAME = ["a", "{s}", "is", "a", "{o}"]


def test_clean_triples_keeps_only_single_token_pairs():
    raw = [("Pug", "dog"), ("great dane", "dog"), ("x1", "dog"), ("cat", "cat"), ("owl", "bird")]
    cleaned = FS.clean_triples(raw)
    assert ("pug", "dog") in cleaned            # lower-cased single tokens kept
    assert all(" " not in s and " " not in o for s, o in cleaned)   # no multi-word
    assert all(s != o for s, o in cleaned)      # no self-loops
    assert not any(s == "x1" for s, _ in cleaned)   # numerics dropped


def test_episodes_and_worksheet_are_consistent():
    eps = FS.episodes_from_triples(_TRIPLES, _FRAME, "wn-test", n_episodes=200, seed=1)
    assert eps and all(set(e) == {"book", "tokens", "picture", "marks"} for e in eps)
    # the picture is the subject (grounds the fact); the frame is rendered
    e = eps[0]
    assert e["picture"] == e["tokens"][1] and e["tokens"][0] == "a" and e["tokens"][2] == "is"
    ws = FS.worksheet_from_triples(_TRIPLES, _FRAME)
    assert ("a pug is a ?", "dog") in ws          # object blanked, object is the key


def test_creature_learns_triples_and_passes_the_auto_worksheet():
    eps = FS.episodes_from_triples(_TRIPLES * 1, _FRAME, "wn", n_episodes=4000, seed=2)
    c = Creature("t", commit_k=2, min_group=6, induction_interval=200, max_slot_tokens=2).ingest(eps)
    ws = FS.worksheet_from_triples(_TRIPLES, _FRAME)
    ok = sum(1 for q, a in ws
             if (lambda r: r.get("known") and r.get("answers") and r["answers"][0]["answer"] == a)(c.answer(q)))
    assert ok == len(ws)


def test_registry_fact_source_via_cache(tmp_path):
    # a wordnet-style entry whose triples are already cached -> no network needed
    entry = {"id": "wn-x", "kind": "wordnet", "root": "dog.n.01", "frame": _FRAME, "domain": "science"}
    (tmp_path / "wn-x.triples.json").write_text(json.dumps({"triples": [list(t) for t in _TRIPLES]}))
    eps = R.source_episodes(entry, raw=tmp_path, fetch=False)
    assert eps and eps[0]["picture"] in {"pug", "corgi", "robin", "wren"}
    ws = R.source_worksheet(entry, raw=tmp_path)
    assert ("a corgi is a ?", "dog") in ws
    # no cache + fetch disabled -> a clean, skippable error (the trainer holds the stage)
    with pytest.raises(FileNotFoundError):
        R.cached_triples({"id": "nope", "kind": "wordnet", "root": "x"}, raw=tmp_path, fetch=False)


def test_wordnet_hypernyms_are_real_when_available():
    pytest.importorskip("nltk")
    try:
        triples = FS.wordnet_triples("dog.n.01", max_n=20)
    except LookupError:
        pytest.skip("wordnet corpus not downloaded")
    assert triples and all(o == "dog" for _s, o in triples[:5])   # breeds are dogs
