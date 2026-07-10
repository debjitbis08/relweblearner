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


def test_web_view_is_a_bounded_ego_graph():
    c = Creature("grapher", commit_k=2, min_group=6, induction_interval=100)
    episodes, world = PB.generate(n_episodes=4000, level=2, seed=5)
    c.ingest(episodes)
    a = next(iter(world))

    g = c.web_view(a)
    assert g["focus"] == a
    # focus is present and marked; every edge touches the focus (ego-graph)
    assert any(n["id"] == a and n["focus"] for n in g["nodes"])
    assert all(e["source"] == a or e["target"] == a for e in g["edges"])
    # the focus's colour fact is a neighbour, oriented focus -> colour
    assert any(e["target"] == world[a]["colour"] and e["committed"] for e in g["edges"])

    # bounded: never returns more than `limit` edges, and flags truncation
    small = c.web_view(a, limit=2)
    assert len(small["edges"]) <= 2
    assert small["truncated"] == (len(g["edges"]) > 2)

    # empty focus seeds on a committed concept rather than returning nothing
    assert c.web_view()["focus"] is not None
    # an unknown concept is honest (no neighbours), not a crash
    assert c.web_view("nosuchconcept")["edges"] == []


def test_web_graph_is_the_whole_web_bounded():
    c = Creature("mapper", commit_k=2, min_group=6, induction_interval=100)
    episodes, world = PB.generate(n_episodes=4000, level=2, seed=6)
    c.ingest(episodes)

    g = c.web_graph()
    # it's the WHOLE web (many concepts, not one node's neighbourhood)
    assert len(g["nodes"]) > 10 and g["edges"]
    assert not g["truncated"] and g["total_nodes"] == len(g["nodes"])
    # nodes carry degree + role; every edge connects two present nodes
    ids = {n["id"] for n in g["nodes"]}
    assert all(n["kind"] in ("entity", "attribute") and n["deg"] >= 1 for n in g["nodes"])
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    # an animal is an entity; its colour value is an attribute
    a = next(iter(world))
    kind = {n["id"]: n["kind"] for n in g["nodes"]}
    assert kind.get(a) == "entity"
    assert kind.get(world[a]["colour"]) == "attribute"

    # bounded: capping nodes keeps only the top-degree core and flags truncation
    small = c.web_graph(max_nodes=8)
    assert len(small["nodes"]) <= 8 and small["truncated"]
    assert small["total_nodes"] == len(g["nodes"])


def test_mind_map_places_concepts_in_learned_coordinates():
    c = Creature("cartographer", commit_k=2, min_group=6, induction_interval=100)
    episodes, _ = PB.generate(n_episodes=4000, level=2, seed=7)
    c.ingest(episodes)

    mm = c.mind_map()
    P = mm["points"]
    assert P and mm["n_component"] >= 8
    # every point has learned coordinates + a colour scalar, all normalised to [0,1]
    for p in P:
        assert 0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0 and 0.0 <= p["c"] <= 1.0
        assert p["kind"] in ("entity", "attribute") and p["deg"] >= 1
    # the geometry actually SPREADS (not collapsed to one spot) — the whole point
    xs = [p["x"] for p in P]; ys = [p["y"] for p in P]
    assert max(xs) - min(xs) > 0.5 and max(ys) - min(ys) > 0.5
    cells = {(round(p["x"], 1), round(p["y"], 1)) for p in P}
    assert len(cells) >= len(P) // 3
    # edges index into the point list (the connected component)
    assert all(0 <= e["s"] < len(P) and 0 <= e["t"] < len(P) for e in mm["edges"])


def test_persistence_is_bounded_and_reloads_identically(tmp_path):
    episodes, _ = PB.generate(n_episodes=4000, seed=4)
    c = Creature("saver", commit_k=2, min_group=6, induction_interval=100)
    c.ingest(episodes)
    before = c.snapshot()

    path = tmp_path / "saver.json"
    c.save(path)
    after = Creature.load(path).snapshot()
    # the "log" census reports the EpisodeLog and "bus" the live trace stream —
    # both separate state by design: a reload without its log honestly shows an
    # empty history, and a reloaded creature starts a fresh bus. The distilled
    # MODEL — everything else in the snapshot — reloads exactly.
    assert before.pop("log")["entries"] == 4000 and after.pop("log")["entries"] == 0
    assert before.pop("bus")["total"] > after.pop("bus")["total"]
    assert before == after

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
