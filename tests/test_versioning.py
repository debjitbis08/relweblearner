"""Persistent state at scale + versioning — the operational promises.

Two architectural promises got an operational layer:

  * **Durable stores in the live path.** A creature whose edges live in a
    SQLite/sharded store checkpoints an *external pointer* to the web, never a
    JSON dump of it — save is O(bounded state) — and saves are atomic
    (temp + rename), stamped with the code/curriculum that produced them, and
    honest about a lost database (the log rebuilds it).
  * **Versions of a mind.** ``relweb-version`` tags a consistent copy of
    checkpoint + log + store, diffs two states as BELIEF sets (the payoff of
    belief-as-projection), and rolls back for real — including the log, so a
    later load cannot replay the abandoned tail back on top.
"""

from __future__ import annotations

import json

import pytest

from relweblearner import version as V
from relweblearner.creature import Creature
from relweblearner.datasets import patternbooks as PB
from relweblearner.episodelog import JsonlEpisodeLog
from relweblearner.store import open_store, store_files


def _grow(c: Creature, n: int = 1500, seed: int = 3) -> Creature:
    return c.ingest(PB.generate(n_episodes=n, level=2, seed=seed)[0])


def _novel(c: Creature, facts=(("okapi", "red"), ("quoll", "blue"))) -> Creature:
    """Teach facts the pattern-book world does not contain, two witnesses each
    (so they commit at commit_k=2)."""
    return c.ingest({"book": bk, "tokens": ["the", a, "is", col], "picture": a}
                    for bk in ("bk-x", "bk-y") for a, col in facts)


def _params():
    return dict(commit_k=2, min_group=6, induction_interval=100)


# ===================================================== durable checkpoints


def test_durable_checkpoint_is_a_pointer_not_a_dump(tmp_path):
    st = open_store("sqlite", tmp_path / "ada.edges")
    c = _grow(Creature("ada", store=st, **_params()))
    want = {b["target"] for b in c.about("bear")["beliefs"]}
    c.save(tmp_path / "ada.json")
    c.close()

    d = json.loads((tmp_path / "ada.json").read_text(encoding="utf-8"))
    cw = d["geometry"]["concept_web"]
    assert cw["external"] == "sqlite"                 # a pointer + counts...
    assert isinstance(cw["edges"], int) and cw["edges"] > 0
    # ...and the reopened store carries the same beliefs
    c2 = Creature.load(tmp_path / "ada.json", store=open_store("sqlite", tmp_path / "ada.edges"))
    assert {b["target"] for b in c2.about("bear")["beliefs"]} == want
    c2.close()


def test_sharded_checkpoint_roundtrip(tmp_path):
    st = open_store("sharded:3", tmp_path / "sh.edges")
    c = _grow(Creature("sh", store=st, **_params()))
    want = {b["target"] for b in c.about("bear")["beliefs"]}
    c.save(tmp_path / "sh.json")
    c.close()
    assert json.loads((tmp_path / "sh.json").read_text())["geometry"]["concept_web"]["external"] == "sharded:3"
    c2 = Creature.load(tmp_path / "sh.json", store=open_store("sharded:3", tmp_path / "sh.edges"))
    assert {b["target"] for b in c2.about("bear")["beliefs"]} == want
    c2.close()


def test_external_checkpoint_refuses_to_load_without_its_store(tmp_path):
    c = _grow(Creature("ada", store=open_store("sqlite", tmp_path / "ada.edges"), **_params()))
    c.save(tmp_path / "ada.json")
    c.close()
    with pytest.raises(ValueError, match="external store"):
        Creature.load(tmp_path / "ada.json")


def test_inline_checkpoint_migrates_into_a_store(tmp_path):
    c = _grow(Creature("mem", **_params()))
    want = {b["target"] for b in c.about("bear")["beliefs"]}
    c.save(tmp_path / "mem.json")
    # handing a durable store to load IS the migration...
    c2 = Creature.load(tmp_path / "mem.json", store=open_store("sqlite", tmp_path / "mem.edges"))
    assert {b["target"] for b in c2.about("bear")["beliefs"]} == want
    c2.save(tmp_path / "mem.json")
    c2.close()
    # ...and from then on the checkpoint is external
    assert "external" in json.loads((tmp_path / "mem.json").read_text())["geometry"]["concept_web"]


def test_lost_database_rebuilds_from_the_log(tmp_path):
    """The log is the belief source (invariant #5): an external checkpoint whose
    database file went missing replays from zero instead of resuming amnesiac."""
    log = JsonlEpisodeLog(tmp_path / "g.episodes.jsonl")
    c = _grow(Creature("g", store=open_store("sqlite", tmp_path / "g.edges"), log=log, **_params()))
    want = {b["target"] for b in c.about("bear")["beliefs"]}
    c.save(tmp_path / "g.json")
    c.close()
    for f in tmp_path.glob("g.edges.sqlite*"):
        f.unlink()
    c2 = Creature.load(tmp_path / "g.json", log=JsonlEpisodeLog(tmp_path / "g.episodes.jsonl"),
                       store=open_store("sqlite", tmp_path / "g.edges"))
    assert {b["target"] for b in c2.about("bear")["beliefs"]} == want
    c2.close()


def test_save_is_atomic_and_stamped(tmp_path):
    c = _grow(Creature("mem", **_params()), n=800)
    c.save(tmp_path / "mem.json")
    c.save(tmp_path / "mem.json")                      # overwrite goes through replace too
    assert not (tmp_path / "mem.json.tmp").exists()    # no temp residue
    d = json.loads((tmp_path / "mem.json").read_text())
    assert set(d["provenance"]) == {"saved", "code", "curriculum"}
    assert d["provenance"]["saved"]                    # code/curriculum may be None off-repo


def test_open_store_specs(tmp_path):
    assert open_store(None, tmp_path / "x").spec == "memory"
    assert open_store("memory", tmp_path / "x").durable is False
    assert store_files("memory", tmp_path / "x") == []
    st = open_store("sqlite", tmp_path / "x")
    st.bump("a", "b", "r", "src", 16)
    st.close()
    assert any(p.name == "x.sqlite" for p in store_files("sqlite", tmp_path / "x"))
    sh = open_store("sharded:2", tmp_path / "y")
    assert sh.durable and len(sh.shards) == 2
    sh.close()
    assert len([p for p in store_files("sharded:2", tmp_path / "y") if p.suffix == ".sqlite"]) == 2
    with pytest.raises(ValueError):
        open_store("bogus", tmp_path / "z")


# ===================================================== versions of a mind


@pytest.fixture()
def creature_home(tmp_path, monkeypatch):
    """Point the whole path layout (train + version) at a scratch repo root."""
    from relweblearner import train as T

    monkeypatch.setattr(T, "_root", lambda: tmp_path)
    monkeypatch.setattr(V, "_root", lambda: tmp_path)
    monkeypatch.delenv("RELWEB_STORE", raising=False)
    (tmp_path / "data" / "creatures").mkdir(parents=True)
    return tmp_path


def _raise_kit(store_spec="sqlite"):
    from relweblearner import train as T

    c = T.load_or_create("kit", store_spec=store_spec, **_params())
    _grow(c)
    c.save(T._store_path("kit"))
    return c


def test_tag_diff_rollback_round_trip(creature_home):
    from relweblearner import train as T

    c = _raise_kit()
    episodes_at_tag = c.episodes_seen
    c.close()
    V.tag("kit", "phase1", note="before the novel facts")

    # no RELWEB_STORE set: the checkpoint's own recorded spec (sqlite) is
    # honoured, so a migrated creature keeps working with zero configuration
    c = T.open_creature("kit")
    assert c.edges.durable
    _novel(c)
    c.save(T._store_path("kit"))
    c.close()

    # the belief diff is a fact-set delta, not a byte delta
    d = V.diff("kit", "phase1")
    gained = {(r["src"], r["tgt"]) for r in d["gained"]}
    assert {("okapi", "red"), ("quoll", "blue")} <= gained
    assert not d["lost"]
    assert d["episodes_seen"]["to"] == episodes_at_tag + 4

    # rollback restores checkpoint AND log AND store — and rotates, never deletes
    r = V.rollback("kit", "phase1")
    assert "kit.episodes.jsonl" in r["rotated_aside"]
    baks = list((creature_home / "data" / "creatures").glob("*.bak"))
    assert baks, "current state must be rotated aside, not deleted"
    c = T.open_creature("kit")
    assert c.episodes_seen == episodes_at_tag       # the tail did NOT replay back
    assert c.about("okapi")["beliefs"] == []
    c.close()
    # after rollback the two states agree again
    d2 = V.diff("kit", "phase1")
    assert not d2["gained"] and not d2["lost"]


def test_tag_refuses_duplicates_and_bad_labels(creature_home):
    _raise_kit().close()
    V.tag("kit", "v1")
    with pytest.raises(FileExistsError):
        V.tag("kit", "v1")
    with pytest.raises(ValueError):
        V.tag("kit", "../escape")


def test_autosnap_prunes_oldest_first_and_spares_manual_tags(creature_home):
    _raise_kit().close()
    V.tag("kit", "keeper")
    for pos in (10, 20, 30, 40):                     # same-second snaps: order still holds
        V.autosnap("kit", pos, keep=2)
    tags = [r["tag"] for r in V._manifests("kit")]
    assert "keeper" in tags
    assert [t for t in tags if t.startswith("auto-")] == ["auto-30", "auto-40"]


def test_diff_between_two_tags_inline_store(creature_home):
    """Versioning works for the default in-memory store too — the checkpoint's
    inline geometry is the whole state, diffed the same way."""
    from relweblearner import train as T

    c = _raise_kit(store_spec="memory")
    c.close()
    V.tag("kit", "a")
    c = T.open_creature("kit")
    _novel(c, facts=(("numbat", "green"),))
    c.save(T._store_path("kit"))
    c.close()
    V.tag("kit", "b")
    d = V.diff("kit", "a", "b")
    assert {(r["src"], r["tgt"]) for r in d["gained"]} == {("numbat", "green")}
