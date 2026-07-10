"""Bare pairing episodes — the P1b data source, and the counting CURRICULUM.

The stream the number learner sees is *only* pairing episodes over collections
of opaque objects (glossary "collection / pairing episode"). **No token is ever
a numeral** and no relation is named; sizes are hidden ground truth used only
for scoring. See ``experiment0e_number.py`` for the reference.

Object ids (``o0, o1, ...``) and collection ids (``K0, K1, ...``) are gensyms —
letter-prefixed so a numeral grep over the stream finds nothing (e1b accept a).

As a registry generator (:func:`generate`) this is the curriculum's numeracy
ground floor, in two rungs:

  * **level 1 — play, then naming.** A long wordless pairing stream (the
    constructed chain crystallises from MATCH/ONEMORE alone), followed by
    joint ostension pages ("here are three" over a pile the creature must
    COUNT itself). No worksheet: naming candidates accrue here, but the
    word↔class interface map cannot commit until order sentences (mathbooks)
    give the words coordinates — grading before that would hold the stage
    forever on an impossibility.
  * **level 2 — the how-many exam.** More ostension pages, and a worksheet of
    FRESH piles (object ids never seen in play): the creature must number
    each with its own chain-pairing routine and speak the mapped word —
    :meth:`~relweblearner.creature.Creature.how_many`, graded. This is the
    stage where "the system measures the world with its own ruler" is a
    report-card line.
"""

from __future__ import annotations

import random
from collections import defaultdict

from ..episode import Episode, world_episode
from .mathbooks import NUMBERS

# the fixed counting world (module constants so `_world(seed)` and `generate`
# agree — the registry reconstructs the world from the seed alone)
N_COLS = 140
MAX_SIZE = 10


def make_collections(n: int, max_size: int = 5, seed: int = 7) -> dict[str, list[str]]:
    """``n`` collections of opaque objects, sizes drawn small-heavy (``~1/s``).

    Returns ``{collection_id: [object_id, ...]}``. Object ids are globally
    unique so no two collections share an object.
    """
    rng = random.Random(seed)
    cols: dict[str, list[str]] = {}
    oid = 0
    for i in range(n):
        size = rng.choices(range(1, max_size + 1), weights=[1.0 / s for s in range(1, max_size + 1)])[0]
        cols[f"K{i}"] = [f"o{oid + j}" for j in range(size)]
        oid += size
    return cols


def by_size(cols: dict[str, list[str]]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = defaultdict(list)
    for k, v in cols.items():
        out[len(v)].append(k)
    return out


def pairing_episode(cols, a: str, b: str, rng: random.Random) -> Episode:
    """Present collections ``a`` and ``b`` with a maximal random pairing.

    The pairing covers ``min(|a|, |b|)`` objects on each side. The learner reads
    only the leftovers; whether this is a MATCH or ONEMORE is derived, not given.
    """
    A, B = cols[a], cols[b]
    k = min(len(A), len(B))
    pairing = list(zip(rng.sample(A, k), rng.sample(B, k)))
    return world_episode(a, set(A), b, set(B), pairing)


def poison_episode(cols, a: str, b: str) -> Episode:
    """A corrupt episode: double-tag one object of ``a`` so a smaller collection
    falsely *saturates* (MATCHes) a larger one.

    ``|a| < |b|``; pairing ``zip(A + [A[0]], B)`` uses ``A``'s objects to cover
    all of ``B`` by reusing ``A[0]`` twice. Both sides read as saturated (a false
    MATCH), yet the episode is non-injective — the lie surfaces downstream as a
    'class ONEMORE of itself' holonomy defect.
    """
    A, B = cols[a], cols[b]
    assert len(A) < len(B), "poison double-tags the smaller collection"
    pairing = list(zip(A + [A[0]] * (len(B) - len(A)), B))
    return world_episode(a, set(A), b, set(B), pairing)


def random_stream(cols, n_episodes: int, seed: int = 0) -> list[Episode]:
    """A stream of ``n_episodes`` random pairings over all collections."""
    rng = random.Random(seed)
    keys = list(cols)
    return [pairing_episode(cols, *rng.sample(keys, 2), rng=rng) for _ in range(n_episodes)]


def joint_pages(
    cols: dict[str, list[str]],
    number_words: list[str],
    *,
    n_pages: int = 60,
    books: tuple = ("cb1", "cb2", "cb3"),
    seed: int = 0,
) -> list[dict]:
    """JOINT ostension pages: a pile of opaque objects presented with a caption
    whose tapped word names its count — ``{book, tokens, picture, collection}``.

    ``number_words[s]`` is the word for size ``s`` — the DATASET knows sizes
    (it is the world); the learner is never told which class a word means and
    must count the pile itself. The pile is the collection verbatim (ids shared
    with the play stream — cross-episode identity is the one given)."""
    rng = random.Random(seed)
    sizes = {s: ks for s, ks in by_size(cols).items() if s < len(number_words)}
    order = sorted(sizes)
    pages = []
    for i in range(n_pages):
        s = order[i % len(order)]       # leveled: every size it teaches recurs
        k = rng.choice(sizes[s])
        w = number_words[s]
        pages.append({
            "book": rng.choice(list(books)),
            "tokens": ["here", "are", w],
            "picture": w,
            "collection": {"id": k, "members": sorted(cols[k])},
        })
    return pages


# ===================================================== the registry generator


def _world(seed: int = 0) -> dict:
    """The hidden counting world: the collections (sizes are ground truth used
    only for page words and grading — never surfaced to the learner)."""
    return {"cols": make_collections(N_COLS, max_size=MAX_SIZE, seed=seed),
            "max_size": MAX_SIZE}


def _play_dicts(cols, n_episodes: int, seed: int) -> list[dict]:
    """The wordless play stream as ingest dicts (kind: bare pairing)."""
    out = []
    for i, ep in enumerate(random_stream(cols, n_episodes, seed=seed)):
        out.append({"book": f"play-{i // 40:05d}", "id1": ep.id1,
                    "members1": sorted(ep.members1), "id2": ep.id2,
                    "members2": sorted(ep.members2),
                    "pairing": [list(p) for p in ep.pairing]})
    return out


def generate(
    *,
    level: int = 1,
    n_play: int = 5000,
    n_pages: int = 100,
    seed: int = 0,
):
    """Stream the counting curriculum at the given ``level``.

    Level 1: ``n_play`` bare pairing episodes (play first — the chain must
    exist before a pile can be counted) then ``n_pages`` ostension pages.
    Level 2: ostension pages only (reinforcement under fresh books; the
    worksheet lives here). Returns ``(episodes, world)``.
    """
    w = _world(seed)
    if level <= 1:
        eps = _play_dicts(w["cols"], n_play, seed) + \
            joint_pages(w["cols"], NUMBERS, n_pages=n_pages,
                        books=("count-a", "count-b", "count-c"), seed=seed)
    else:
        eps = joint_pages(w["cols"], NUMBERS, n_pages=n_pages,
                          books=("count-d", "count-e", "count-f"), seed=seed + 1)
    return eps, w


def quiz(world: dict, level: int = 2) -> list[tuple]:
    """The how-many WORKSHEET (level 2 only): fresh piles — object ids no play
    episode ever contained — each to be numbered by the creature's own routine
    and answered with the mapped word. Item format ``({"kind": "count",
    "members": [...]}, word)``; :func:`syllabus.run_exam` dispatches on it."""
    if level < 2:
        return []
    items: list[tuple] = []
    for s in range(1, world["max_size"] + 1):
        for j in ("x", "y"):
            members = [f"exam-{j}{s}-thing{k}" for k in range(s)]
            items.append(({"kind": "count", "members": members}, NUMBERS[s]))
    return items


def staged_stream(cols, small_max: int, n_small: int, n_full: int, seed: int = 0):
    """A small-collections-first schedule (e1b accept d).

    Returns ``(stage_a, stage_b)``: ``stage_a`` pairs only collections of size
    ``<= small_max`` (so only small numbers can crystallize); ``stage_b`` is full
    experience over everything.
    """
    rng = random.Random(seed)
    sizes = by_size(cols)
    small = [k for s, ks in sizes.items() if s <= small_max for k in ks]
    allk = list(cols)
    stage_a = [pairing_episode(cols, *rng.sample(small, 2), rng=rng) for _ in range(n_small)]
    stage_b = [pairing_episode(cols, *rng.sample(allk, 2), rng=rng) for _ in range(n_full)]
    return stage_a, stage_b
