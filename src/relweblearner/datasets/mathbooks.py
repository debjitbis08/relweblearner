"""Basic-maths pattern-book generator — the numeracy rung of the scale firehose.

Same machine as :mod:`patternbooks` (one template iterated with slot
substitution, emitted as joint ``{book, tokens, picture, marks}`` episodes) but
the hidden world is a small **number line** and a handful of **shapes**, and the
frames express *basic-maths* relations rather than animal attributes:

    comes-after   ``<n> comes after <m>``          (functional: m = n - 1)
    comes-before  ``<n> comes before <m>``         (functional: m = n + 1)
    shape-sides   ``a <shape> has <n> sides``       (functional: triangle -> three …)

This teaches the number line (order) and shapes as learned relations. Arithmetic
itself is NOT taught here as facts: it is meant to be *evaluated* by the general
fixed algebra (transport + growth over the learned number web), which is a separate,
general concern — not a hand-authored table.

Each frame is an anchored subsequence with **exactly two slots** (so a parse
commits a fact) separated by anchor words (so no gold ``marks`` are needed — the
segmentation induces itself). The number words are ordinary surface tokens, just
as ``patternbooks`` already emits ``two``/``four`` for leg counts; the numeracy
lives in the *relations between* numbers, which the web learns as fixed-algebra
edges. Nothing here claims the learner is *handed* numbers — only that a leveled
maths reader expresses a functional world it must recover.

``generate(n_episodes=...)`` streams as many episodes as asked; ``world`` returns
the ground truth for the comprehension check (:func:`truth`).
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden world
# The number line as surface words (index == value). Successor / predecessor are
# implicit in the ordering; the frames below express them and the learner must
# recover the ordering as a web of fixed-algebra edges.
NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven",
           "eight", "nine", "ten"]

# Shapes with their (functional) side count. Values repeat across shapes
# (square/rectangle -> four), so no target token dominates its slot — induction
# reads the count position as a slot, not an anchor.
SIDES = {
    "triangle": "three",
    "square": "four",
    "rectangle": "four",
    "pentagon": "five",
    "hexagon": "six",
    "heptagon": "seven",
    "octagon": "eight",
}
SHAPES = list(SIDES)
NUMBER_WORDS = set(NUMBERS)


def _world(seed: int = 0) -> dict:
    """The maths world scored against: the number line and the shape->sides map.
    Deterministic (there is nothing random to seed) — ``seed`` is accepted for a
    uniform generator signature."""
    return {"numbers": list(NUMBERS), "sides": dict(SIDES)}


# ---------------------------------------------------------------- frame specs
# Each spec draws a valid instance and renders ``(tokens, picture, marks)``. The
# PICTURE is the first slot filler, so ``_orient`` makes it the fact's source and
# the other filler the target; ``marks`` is always ``None`` (anchors separate the
# two slots, so the machine induces the breakup itself).

def _f_after(rng, w):                              # n comes after n-1
    i = rng.randint(1, len(NUMBERS) - 1)
    n, m = NUMBERS[i], NUMBERS[i - 1]
    return ([n, "comes", "after", m], n, None)

def _f_before(rng, w):                             # n is before n+1
    # NB the anchor pair {is, before} is deliberately DISJOINT from after's
    # {comes, after}. Sharing an anchor (e.g. both "comes … after/before") lets a
    # page pair that also shares its slot-0 number agree on two columns and merge
    # into one degenerate 3-slot skeleton — which fails the 2-anchor/2-slot gate
    # and induces nothing. Disjoint anchors keep the two orderings separable.
    i = rng.randint(0, len(NUMBERS) - 2)
    n, m = NUMBERS[i], NUMBERS[i + 1]
    return ([n, "is", "before", m], n, None)

def _f_sides(rng, w):                              # a <shape> has <n> sides
    s = rng.choice(SHAPES)
    return (["a", s, "has", w["sides"][s], "sides"], s, None)


# We TEACH the number line (comes-after / is-before) and shapes — nothing more.
# Arithmetic is NOT authored here; it is meant to be evaluated by the general algebra
# over the learned number web. NB: no "one more than" frame — its "one" anchor would
# collide with the number word "one".
FRAMES_BY_LEVEL = {
    1: [_f_after, _f_before],            # counting & number order
    2: [_f_after, _f_before, _f_sides],  # + shapes
}

# Off-frame lines (narrative / questions) that must land on the frontier.
OFF_FRAME = [
    ["let", "us", "count", "together"],
    ["how", "many", "do", "you", "see"],
    ["numbers", "are", "fun"],
    ["that", "is", "all", "for", "today"],
]


def generate(
    *,
    n_episodes: int = 1000,
    level: int = 2,
    pages_per_book: int = 40,
    off_frame_rate: float = 0.03,
    with_marks: bool = True,          # accepted for signature parity; no frame needs marks
    seed: int = 0,
):
    """Stream ``n_episodes`` maths pattern-book episodes at the given ``level``.

    Mirrors :func:`patternbooks.generate`: books of ``pages_per_book`` pages each
    iterate the level's frames with random substitution, a fraction
    ``off_frame_rate`` of pages are off-frame (destined for the frontier).
    Returns ``(episodes, world)`` where each episode is
    ``{book, tokens, picture, marks}``.
    """
    rng = random.Random(seed)
    w = _world(seed)
    specs = FRAMES_BY_LEVEL[level]
    episodes = []
    book_i = 0
    while len(episodes) < n_episodes:
        book = f"maths-{book_i:05d}"
        book_i += 1
        for _ in range(pages_per_book):
            if len(episodes) >= n_episodes:
                break
            if rng.random() < off_frame_rate:
                episodes.append({"book": book, "tokens": list(rng.choice(OFF_FRAME)),
                                 "picture": None, "marks": None})
                continue
            tokens, picture, marks = rng.choice(specs)(rng, w)
            episodes.append({
                "book": book,
                "tokens": tokens,
                "picture": picture,
                "marks": marks if with_marks else None,
            })
    return episodes, w


def truth(world: dict) -> dict:
    """The shape->sides view the comprehension check scores against — the cleanest
    functional relation in the maths world (distinct source per fact, a small set
    of target counts)."""
    return dict(world["sides"])


def quiz(world: dict, level: int = 2) -> list[tuple[str, str]]:
    """A maths WORKSHEET: ``(question, answer)`` pairs in the exact frames taught,
    graded by ``level`` (matches the reading ladder in ``FRAMES_BY_LEVEL``)."""
    items: list[tuple[str, str]] = []
    N = NUMBERS
    for i in range(1, len(N)):
        items.append((f"{N[i]} comes after ?", N[i - 1]))
    for i in range(len(N) - 1):
        items.append((f"{N[i]} is before ?", N[i + 1]))
    if level >= 2:
        for s, n in world["sides"].items():
            items.append((f"a {s} has ? sides", n))
    return items
