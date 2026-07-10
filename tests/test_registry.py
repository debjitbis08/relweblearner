"""Acceptance for the corpus REGISTRY and the incremental ingestion LEDGER — the
machinery that lets ``relweb-train`` pull only NEW sources each (scheduled) run.

Network-free: only ``generated`` sources are materialised here; the ``gutenberg``
path is exercised for its no-network failure mode (missing raw file, fetch off).
"""

from __future__ import annotations

import json

from relweblearner.creature import Creature
from relweblearner.datasets import registry as R


def test_registry_is_well_formed():
    reg = R.load_registry()
    ids = [s["id"] for s in reg]
    assert len(ids) == len(set(ids)), "source ids must be unique (the ledger keys on them)"
    assert all(s["kind"] in ("generated", "gutenberg", "wordnet", "wikidata") for s in reg)
    # generated worlds are listed before books, so grounding is laid down first
    kinds = [s["kind"] for s in reg]
    assert kinds.index("generated") < kinds.index("gutenberg")
    for s in reg:
        if s["kind"] == "generated":
            assert s["generator"] in R._GENERATORS
        elif s["kind"] == "gutenberg":
            assert isinstance(s["ref"], int)
        elif s["kind"] == "wordnet":
            assert "root" in s and ("frames" in s or "frame" in s)
        elif s["kind"] == "wikidata":
            assert s["relation"] in __import__("relweblearner.datasets.factsource", fromlist=["x"]).WIKIDATA_QUERIES
        if s["kind"] in ("wordnet", "wikidata"):
            frames = R._entry_frames(s)
            # >= 2 paraphrases per relation (P9: the construction must not be a
            # label proxy), and no same-length pair ACROSS sources shares >= 2
            # anchor columns (they would merge into one degenerate cluster)
            assert len(frames) >= 2
    fact_frames = [f for s in reg if s["kind"] in ("wordnet", "wikidata")
                   for f in R._entry_frames(s)]
    for i, a in enumerate(fact_frames):
        for b in fact_frames[i + 1:]:
            if a == b or len(a) != len(b):
                continue
            shared = sum(1 for x, y in zip(a, b)
                         if x == y and x not in ("{s}", "{o}"))
            assert shared < 2, f"colliding constructions: {a} / {b}"


def test_generated_source_materialises():
    reg = R.load_registry()
    # an episode is either a caption page ({tokens, ...}) or a bare pairing
    # episode ({id1, members1, ...}) — the counting-play channel
    for world in [s for s in reg if s["kind"] == "generated"][:3]:
        eps = R.source_episodes(world)
        assert eps and all("tokens" in e or "id1" in e for e in eps)
    sized = next(s for s in reg if s["kind"] == "generated" and "n_episodes" in s["params"])
    assert len(R.source_episodes(sized)) == sized["params"]["n_episodes"]


def test_gutenberg_source_without_network_or_cache_raises(tmp_path):
    entry = {"id": "gutenberg-x", "kind": "gutenberg", "ref": 999999999, "title": "nope"}
    # fetch disabled + empty raw dir -> a clean, skippable error (train catches it)
    try:
        R.source_episodes(entry, raw=tmp_path, fetch=False)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_pending_sources_excludes_the_ledger():
    reg = R.load_registry()
    read = {reg[0]["id"], reg[2]["id"]}
    pending = R.pending_sources(reg, read)
    pending_ids = {s["id"] for s in pending}
    assert reg[0]["id"] not in pending_ids and reg[2]["id"] not in pending_ids
    assert len(pending) == len(reg) - 2
    # order is preserved (registry order == ingestion order)
    assert [s["id"] for s in pending] == [s["id"] for s in reg if s["id"] not in read]


def test_incremental_ticks_ingest_only_new_sources(tmp_path):
    # a tiny synthetic registry of two generated worlds; simulate two ticks
    reg = [
        {"id": "w-maths", "kind": "generated", "generator": "mathbooks",
         "params": {"n_episodes": 2000, "level": 2, "seed": 1}},
        {"id": "w-kids", "kind": "generated", "generator": "kidbooks",
         "params": {"n_episodes": 2000, "level": 1, "seed": 1}},
    ]
    path = tmp_path / "c.json"

    # tick 1: one new source
    c = Creature("t", min_group=8, induction_interval=400)
    for s in R.pending_sources(reg, c.read_sources)[:1]:
        c.ingest_source(s["id"], R.source_episodes(s))
    c.save(path)
    assert c.read_sources == {"w-maths"}

    # tick 2: reload; only the un-read source remains pending and gets ingested
    c2 = Creature.load(path)
    assert c2.read_sources == {"w-maths"}                 # ledger survived save/load
    pending = R.pending_sources(reg, c2.read_sources)
    assert [s["id"] for s in pending] == ["w-kids"]        # w-maths skipped
    for s in pending:
        c2.ingest_source(s["id"], R.source_episodes(s))
    c2.save(path)
    assert c2.read_sources == {"w-maths", "w-kids"}

    # tick 3: nothing new
    c3 = Creature.load(path)
    assert R.pending_sources(reg, c3.read_sources) == []
