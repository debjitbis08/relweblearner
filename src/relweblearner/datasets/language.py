"""Synthetic language corpus — the PL read/write data source.

A hidden world of concepts with two typed relations (``HC`` = has-colour,
``GO`` = grows-on) over six fruit concepts (the same fruit domain as
``experiment0b_fruits.py`` and the dev-doc motif glossary). Every concept and
relation has an opaque **surface form** (a gensym word) split into syllables;
the learner receives only the raw syllable stream — no word/utterance
boundaries, no vocabulary, and **no identifier shared with the concept web**.

The concept ids (``mango``, ``yellow``, ``HC`` …) and the surface forms
(``bavu``, ``dima`` …) are drawn from disjoint namespaces: nothing a learner
recovers from the stream string-matches a concept id (spec §1; CI test in
``test_pl_language``). Sizes/colours are hidden ground truth used only for
scoring.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden world
# HC: fruit -> colour     GO: fruit -> substrate     (both functional relations)
HC = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
GO = {
    "mango": "tree",
    "banana": "herb",
    "lemon": "tree",
    "apple": "tree",
    "cherry": "tree",
    "lime": "tree",
}
CONCEPT_RELATIONS = {"HC": HC, "GO": GO}

# opaque surface forms (gensyms); disjoint from every concept id string
WORD = {
    "mango": "bavu",
    "banana": "kide",
    "lemon": "mopa",
    "apple": "runi",
    "cherry": "tela",
    "lime": "zogi",
    "yellow": "dima",
    "red": "felo",
    "green": "gusa",
    "tree": "hepo",
    "herb": "wiju",
    "HC": "xuqo",
    "GO": "ceny",
}


def syllabify(word: dict[str, str]) -> dict[str, list[str]]:
    """Split every surface form into its two syllables (the sensor's atoms)."""
    return {w: [w[:2], w[2:]] for w in word.values()}


SYL = syllabify(WORD)
FACTS = [("HC", f, c) for f, c in HC.items()] + [("GO", f, p) for f, p in GO.items()]


def concept_edges(relations: dict = CONCEPT_RELATIONS) -> dict[str, set]:
    """The concept web as its typed-edge projection: ``{rel: {(x, y), ...}}``."""
    return {r: set(t.items()) for r, t in relations.items()}


def concept_ids(relations: dict = CONCEPT_RELATIONS) -> set[str]:
    """Every id the concept web uses (relation names, arguments, values)."""
    ids: set[str] = set(relations)
    for table in relations.values():
        ids |= set(table) | set(table.values())
    return ids


def surface_forms(word: dict = WORD) -> set[str]:
    """Every surface form a learner can recover from the stream."""
    return set(word.values())


def stream_of(n_utt: int, facts=FACTS, word=WORD, syl=None, seed: int = 3):
    """A raw syllable stream of ``n_utt`` random utterances.

    Each utterance realises one fact as ``[marker, arg1, arg2]``; the words are
    concatenated into syllables with **no boundaries**. Returns
    ``(units, gold_boundaries)`` where ``gold_boundaries`` is the hidden set of
    word-end positions (for scoring only).
    """
    if syl is None:
        syl = syllabify(word)
    rng = random.Random(seed)
    units: list[str] = []
    gold: set[int] = set()
    for _ in range(n_utt):
        r, x, y = rng.choice(facts)
        for w in (word[r], word[x], word[y]):
            units += syl[w]
            gold.add(len(units))
    return units, gold


# syllable collisions used to stress segmentation (each shares one syllable with
# an existing fruit word: ba~bavu, ki~kide, ru~runi, te~tela)
_STRESS_SWAPS = [
    ("yellow", "bama"),
    ("green", "kiqo"),
    ("red", "ruso"),
    ("herb", "telu"),
]


def stress_words(shared: int) -> dict[str, str]:
    """A ``WORD`` variant where ``shared`` value-words are made to reuse fruit
    syllables — the knob that drives the segmentation degradation curve.

    ``shared == 0`` is the clean lexicon (unique syllables per word);
    ``shared == 2`` reproduces the reference stress run (``bama``/``kiqo``).
    """
    w = dict(WORD)
    for name, form in _STRESS_SWAPS[:shared]:
        w[name] = form
    return w
