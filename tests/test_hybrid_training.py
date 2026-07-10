"""Acceptance for HYBRID training — the union that makes the creature both READ and
KNOW: grounded (picture-tapped) worlds supply clean facts, real prose supplies
constructions, and the slot-width cap keeps real prose's clause-wide slots out of
the concept web. Mirrors what ``relweblearner.train`` does, at test scale and
network-free (real text is an inline sample, not the fetched corpus).
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import kidbooks as KB
from relweblearner.datasets import mathbooks as MB
from relweblearner.datasets import realbooks as RB

# a real-prose sample whose only "the _ is _"-shaped line has a wide (3-token)
# subject — the kind of clause a general frame would otherwise swallow into a
# fragment fact.
_REAL = "*** START OF THE PROJECT GUTENBERG EBOOK T ***\n\n" + "\n\n".join(
    ["The man in the boat is here."] * 30 + ["He ran to the sea."] * 30
) + "\n\n*** END OF THE PROJECT GUTENBERG EBOOK T ***\n"


def _train_hybrid(max_slot_tokens):
    grounded = (MB.generate(n_episodes=6000, level=2, seed=1)[0]
                + KB.generate(n_episodes=8000, level=3, seed=1)[0])
    real = RB.episodes_from_text(_REAL, "T") * 5
    c = Creature("hybrid", commit_k=2, min_group=10, induction_interval=800,
                 buffer_cap=30000, max_slot_tokens=max_slot_tokens)
    c.ingest(grounded)
    c.ingest(real)
    return c


def test_hybrid_creature_knows_grounded_facts():
    c = _train_hybrid(max_slot_tokens=2)

    def ask(q):
        r = c.answer(q)
        return r["answers"][0]["answer"] if r.get("known") and r.get("answers") else None

    # it KNOWS things — across maths and kid worlds, grounded by the picture channel
    assert ask("a triangle has ? sides") == "three"
    assert ask("the dog says ?") == KB.ANIMAL_SOUND["dog"]
    assert ask("the opposite of big is ?") == KB.OPPOSITE["big"]


def test_hybrid_also_induces_real_constructions():
    c = _train_hybrid(max_slot_tokens=2)
    templates = {f["template"] for f in c.snapshot()["frames"]}
    # a real English construction from the prose sample was induced alongside the
    # grounded frames
    assert any(t.count("___") >= 1 and "the" in t for t in templates)


def test_slot_cap_keeps_concept_web_clean():
    # with the cap, no committed fact has a multi-word argument (the wide-slot real
    # clause "the man in the boat is here" is held in the frontier, not committed).
    c = _train_hybrid(max_slot_tokens=2)
    for b in c.snapshot(committed_limit=2000)["committed"]:
        assert b["source"].count(" ") == 0 and b["target"].count(" ") == 0
