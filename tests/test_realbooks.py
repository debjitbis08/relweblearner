"""Acceptance for the real-corpus loader — turning public-domain book text into
training episodes. The parsing is pure (no I/O), so these run network-free on an
inline sample that reproduces the shape of a Project Gutenberg reader: boilerplate
markers, lesson headers, an ``[Illustration]`` block, a phonics/word-list drill
line, and real sentences.
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import realbooks as RB

SAMPLE = """\
The Project Gutenberg eBook of A Little Reader

*** START OF THE PROJECT GUTENBERG EBOOK A LITTLE READER ***

LESSON I.

dog   the   ran

a   o   n   d   g   r

[Illustration: Running dog.]

The dog.

The dog ran.

LESSON II.

The cat is on the mat.

Is the cat on the mat?

*** END OF THE PROJECT GUTENBERG EBOOK A LITTLE READER ***

Some trailing license boilerplate that must never be read as content.
"""


def test_boilerplate_and_furniture_are_stripped():
    eps = RB.episodes_from_text(SAMPLE, "A Little Reader")
    texts = [" ".join(e["tokens"]) for e in eps]
    # real sentences survive
    assert "the dog ran" in texts
    assert "the cat is on the mat" in texts
    assert "is the cat on the mat" in texts
    # furniture is gone
    assert not any("lesson" in t for t in texts)
    assert not any("illustration" in t for t in texts)
    assert not any("gutenberg" in t for t in texts)
    assert not any("license" in t or "boilerplate" in t for t in texts)
    # the phonics drill line ("a o n d g r") collapses to nothing usable
    assert not any(set(t.split()) <= {"a", "o", "n", "d", "g", "r"} for t in texts)


def test_episode_shape_matches_generators():
    eps = RB.episodes_from_text(SAMPLE, "A Little Reader")
    assert eps, "no episodes produced"
    for e in eps:
        assert set(e) == {"book", "tokens", "picture", "marks"}
        assert e["book"] == "A Little Reader"
        assert e["picture"] is None and e["marks"] is None
        assert all(isinstance(t, str) and t.islower() for t in e["tokens"])
        assert RB.MIN_TOKENS <= len(e["tokens"]) <= RB.MAX_TOKENS


# a substitution-rich primer body: a TWO-slot construction iterated over many
# fillers — repetition WITH substitution in both argument positions, the way a real
# leveled reader repeats "the <animal> sees the <thing>". Two slots so a parse is a
# committable fact (coverage counts facts, not bare frame matches).
_ANIMALS = ["dog", "cat", "hen", "rat", "pig", "cow", "fox", "owl", "bee", "ant"]
_THINGS = ["ball", "bone", "nest", "cake", "farm", "pond"]
_RICH = "*** START OF THE PROJECT GUTENBERG EBOOK RICH ***\n\n" + "\n\n".join(
    f"The {a} sees the {t}." for a in _ANIMALS for t in _THINGS
) + "\n\n*** END OF THE PROJECT GUTENBERG EBOOK RICH ***\n"


def test_real_episodes_ingest_and_induce_a_frame():
    # frame induction needs repetition WITH substitution; a real reader supplies it.
    eps = RB.episodes_from_text(_RICH, "Rich Reader")
    assert len(eps) == len(_ANIMALS) * len(_THINGS)
    c = Creature("primer", min_group=6, induction_interval=40, buffer_cap=5000)
    c.ingest(eps)
    # it recovers the "the ___ sees the ___" construction and reads real coverage
    templates = {f["template"] for f in c.snapshot()["frames"]}
    assert "the ___ sees the ___" in templates
    assert c.snapshot()["coverage"] > 0.5
