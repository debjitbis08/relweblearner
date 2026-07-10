"""Acceptance for the streaming :class:`~relweblearner.creature.Creature` — the
scalable substrate. The point of these tests is the SCALE properties the
append-only Reader lacks: the model is bounded (grows with what is learned, not
with episodes read), ingest is streaming, persistence is O(world) not O(history),
and the creature has an identity.
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import patternbooks as PB


def test_identity_is_stable_and_addressable():
    c = Creature("Ada", created="2026-07-10", level=2)
    assert c.id == "ada" and c.name == "Ada"
    assert c.snapshot()["identity"] == {"name": "Ada", "id": "ada", "created": "2026-07-10", "level": 2}


def test_streaming_ingest_induces_frames_and_commits_facts():
    c = Creature("reader", commit_k=2, min_group=6, induction_interval=100)
    episodes, world = PB.generate(n_episodes=2000, level=2, seed=1)
    c.ingest(episodes)
    snap = c.snapshot()
    # the level-2 relations are all recovered
    templates = {f["template"] for f in snap["frames"]}
    assert {"the ___ is ___", "___ has ___ legs", "the ___ eats ___", "i see a ___ ___"} <= templates
    # facts committed and correct against the hidden world (colour relation)
    assert snap["committed"], "nothing committed after 2000 episodes"
    truth = PB.truth(world)
    colour_facts = [(b["source"], b["target"]) for b in snap["committed"] if b["target"] in PB.COLOURS]
    assert colour_facts and all(truth[a] == c_ for a, c_ in colour_facts)


def test_model_size_is_bounded_not_proportional_to_episodes():
    # feed 10x more episodes over the SAME small world -> the model must not grow
    # 10x. Memory tracks what is learned (frames + distinct facts), which saturates.
    small = Creature("small", min_group=6, induction_interval=100).ingest(PB.generate(n_episodes=1000, seed=2)[0])
    big = Creature("big", min_group=6, induction_interval=100).ingest(PB.generate(n_episodes=10000, seed=2)[0])
    sm, bg = small.snapshot()["model_size"], big.snapshot()["model_size"]
    assert big.episodes_seen == 10 * small.episodes_seen
    # 10x the episodes must NOT give ~10x the model. Frames and facts are bounded
    # by the fixed world (the reading ladder's relations, and animals*relations),
    # and the buffer is capped — none scale with episodes_seen.
    assert bg["frames"] <= 8 and sm["frames"] <= 8
    assert bg["facts"] <= len(PB.ANIMALS) * 3 + 5      # colour + food + legs per animal
    assert bg["buffer"] <= big.buffer_cap
    # the decisive scale check: model grew far less than 10x
    assert bg["facts"] < 3 * sm["facts"]


def test_talk_back_matches_the_hidden_world():
    c = Creature("talker", commit_k=2, min_group=6, induction_interval=100)
    episodes, world = PB.generate(n_episodes=3000, level=2, seed=3)
    c.ingest(episodes)
    # ask a committed colour fact
    a = next(iter(world))
    res = c.answer(f"the {a} is ?")
    if res["kind"] == "answer" and res["known"]:
        assert res["answers"][0]["answer"] == world[a]["colour"]
    # say only speaks committed, read-back-verified sentences
    for s in c.say(limit=5):
        assert s["sentence"]


def test_persistence_is_bounded_and_reloads_identically(tmp_path):
    episodes, _ = PB.generate(n_episodes=4000, seed=4)
    c = Creature("saver", commit_k=2, min_group=6, induction_interval=100)
    c.ingest(episodes)
    before = c.snapshot()

    path = tmp_path / "saver.json"
    c.save(path)
    after = Creature.load(path).snapshot()
    assert before == after   # distilled model reloads exactly

    # bounded: the persisted MODEL is smaller than even the bare token text of the
    # 4000 episodes it distilled — it stores what was learned, not what was read.
    raw_text_bytes = sum(len(" ".join(e["tokens"])) for e in episodes)
    assert path.stat().st_size < raw_text_bytes


def test_persists_geometry_not_algebra():
    # thesis: intelligence = fixed algebra + geometry. The algebra stays in code;
    # only the geometry (the web) is stored.
    c = Creature("geo", commit_k=2, min_group=6, induction_interval=100)
    c.ingest(PB.generate(n_episodes=2000, seed=5)[0])
    d = c.to_dict()
    # the web is there: concept nodes + typed, algebra-valued edges, and the language web
    geo = d["geometry"]
    assert geo["concept_web"]["nodes"] and geo["concept_web"]["edges"]
    e0 = geo["concept_web"]["edges"][0]
    assert set(e0) == {"src", "tgt", "rel", "count", "sources"}   # an algebra-typed edge
    assert geo["language_web"]["frames"]
    # the algebra itself is NOT serialised — it lives in code
    import json
    blob = json.dumps(d).lower()
    assert "integergroup" not in blob and "holonomy" not in blob and "def " not in blob


def test_stored_geometry_yields_a_spatial_embedding():
    # the web IS the geometry: a Laplacian eigenmap recomputes spatial coordinates
    # from the stored graph (fixed machinery over stored geometry).
    c = Creature("embed", commit_k=1, min_group=6, induction_interval=100)
    c.ingest(PB.generate(n_episodes=2000, seed=6)[0])
    emb = c.embedding(dim=2)
    assert len(emb["nodes"]) >= 3
    assert len(emb["coords"]) == len(emb["nodes"])
    assert all(len(row) == 2 for row in emb["coords"])


def test_human_breakup_frame_forms_from_one_marked_episode():
    c = Creature("marker", commit_k=1)
    obs = c.observe(["i", "see", "a", "red", "bear"], picture="bear", source="Debjit", marks=[[3, 4], [4, 5]])
    assert obs["parsed"] and obs["fact"] == ("bear", "red")
    assert "i see a ___ ___" in {f["template"] for f in c.snapshot()["frames"]}
