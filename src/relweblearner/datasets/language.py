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


# ---------------------------------------------------------------- richer world
# The 6-fruit world above is too small for P2' type discovery (its value nodes
# green/herb are degree-1 singletons). This richer world (9 fruits, each colour
# and substrate a degree-3 hub, every colour overlapping every substrate) is one
# P2' discovers cleanly at purity 1.0 — used to ground words on *discovered*
# relation types instead of given labels (closes the I3 traceability gap).
RICH_HC = {
    "mango": "yellow", "lemon": "yellow", "banana": "yellow",
    "apple": "red", "cherry": "red", "tomato": "red",
    "lime": "green", "kiwi": "green", "pea": "green",
}
RICH_GO = {
    "mango": "tree", "lemon": "tree", "apple": "tree", "cherry": "tree", "lime": "tree",
    "banana": "herb", "tomato": "herb", "kiwi": "herb", "pea": "herb",
}
RICH_RELATIONS = {"HC": RICH_HC, "GO": RICH_GO}


def make_surface_forms(relations: dict = RICH_RELATIONS, seed: int = 7) -> dict[str, str]:
    """Assign each concept a distinct 2-syllable gensym, disjoint from concept ids."""
    concepts = sorted(concept_ids(relations))
    pool = [c + v for c in "bcdfghjklmnpqrstvwxz" for v in "aeiou"]
    rng = random.Random(seed)
    rng.shuffle(pool)
    word = {c: pool[2 * i] + pool[2 * i + 1] for i, c in enumerate(concepts)}
    assert set(word.values()).isdisjoint(concepts), "surface forms must be a disjoint namespace"
    return word


def rich_facts(relations: dict = RICH_RELATIONS) -> list:
    return [(r, f, v) for r, tbl in relations.items() for f, v in tbl.items()]


def unlabeled_edges(relations: dict = RICH_RELATIONS) -> list:
    """The concept web with its relation labels stripped — a flat edge list, the
    input a structuralist learner is actually given (P2' recovers the types)."""
    return [pair for tbl in relations.values() for pair in tbl.items()]


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
