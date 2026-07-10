"""Kid-content pattern-book generator — the early-reader rung of the scale firehose.

Same machine as :mod:`patternbooks` and :mod:`mathbooks` (one template iterated
with slot substitution, emitted as joint ``{book, tokens, picture, marks}``
episodes) but broadened to the everyday vocabulary of a picture-book shelf. Four
functional worlds, each an anchored-subsequence frame with **exactly two slots**
separated by anchor words (so no gold ``marks`` are needed):

    sound     ``the <animal> says <sound>``          dog -> woof, cat -> meow …
    colour    ``a <fruit> is <colour>``              apple -> red, lime -> green …
    habitat   ``the <animal> lives in a <place>``     fish -> pond, bee -> hive …
    opposite  ``the opposite of <word> is <word>``    big <-> small, hot <-> cold …

The anchor set of every frame is chosen DISJOINT from any other frame it shares a
length with, so two frames can never agree on two columns and collapse into one
degenerate skeleton (the failure :mod:`mathbooks` documents for ``comes
after``/``comes before``). ``opposite`` is emitted in both directions, so the web
carries it as the symmetric relation it is.

Frames are graded into LEVELS (the reading ladder): level 1 is animal sounds
alone; later levels add colours, habitats and opposites. ``generate(...)`` streams
any volume; ``world`` returns the ground truth for the comprehension check.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden world
# Four functional maps. Sources within a relation are distinct; targets may
# repeat across sources (tree/pond, red/yellow) so no target token dominates its
# slot and induction reads it as an argument, not an anchor.
ANIMAL_SOUND = {
    "dog": "woof", "cat": "meow", "cow": "moo", "duck": "quack", "pig": "oink",
    "sheep": "baa", "frog": "croak", "bird": "tweet", "horse": "neigh", "hen": "cluck",
}
FRUIT_COLOUR = {
    "apple": "red", "banana": "yellow", "grape": "purple", "lime": "green",
    "plum": "purple", "lemon": "yellow", "cherry": "red", "orange": "orange",
    "pear": "green", "berry": "blue",
}
ANIMAL_HOME = {
    "fish": "pond", "bird": "tree", "bear": "cave", "cow": "barn", "bee": "hive",
    "dog": "house", "ant": "hill", "owl": "tree", "frog": "pond", "mouse": "hole",
}
# Opposites — a SYMMETRIC relation; both directions are emitted so the web learns
# it as symmetric rather than functional.
OPPOSITE = {
    "big": "small", "hot": "cold", "up": "down", "day": "night", "fast": "slow",
    "happy": "sad", "wet": "dry", "old": "new", "high": "low", "open": "shut",
}

SOUNDS = set(ANIMAL_SOUND.values())
COLOURS = set(FRUIT_COLOUR.values())
PLACES = set(ANIMAL_HOME.values())


def _world(seed: int = 0) -> dict:
    """The kid world scored against — four functional/symmetric maps. Deterministic;
    ``seed`` is accepted only for a uniform generator signature."""
    both = dict(OPPOSITE)
    both.update({v: k for k, v in OPPOSITE.items()})   # symmetric closure
    return {
        "sound": dict(ANIMAL_SOUND),
        "colour": dict(FRUIT_COLOUR),
        "home": dict(ANIMAL_HOME),
        "opposite": both,
    }


# ---------------------------------------------------------------- frame specs
# The PICTURE is the first slot filler, so ``_orient`` makes it the fact's source.
# ``marks`` is always ``None`` — anchors separate the two slots.

def _f_sound(rng, w):                              # the <animal> says <sound>
    a = rng.choice(list(ANIMAL_SOUND))
    return (["the", a, "says", w["sound"][a]], a, None)

def _f_colour(rng, w):                             # a <fruit> is <colour>
    f = rng.choice(list(FRUIT_COLOUR))
    return (["a", f, "is", w["colour"][f]], f, None)

def _f_home(rng, w):                               # the <animal> lives in a <place>
    a = rng.choice(list(ANIMAL_HOME))
    return (["the", a, "lives", "in", "a", w["home"][a]], a, None)

def _f_opposite(rng, w):                           # the opposite of <word> is <word>
    a = rng.choice(list(w["opposite"]))
    return (["the", "opposite", "of", a, "is", w["opposite"][a]], a, None)


FRAMES_BY_LEVEL = {
    1: [_f_sound],                                  # animal sounds
    2: [_f_sound, _f_colour, _f_home],              # + colours + habitats
    3: [_f_sound, _f_colour, _f_home, _f_opposite], # + opposites
}

# Off-frame lines (narrative / questions) that must land on the frontier.
OFF_FRAME = [
    ["what", "a", "happy", "little", "book"],
    ["can", "you", "read", "with", "me"],
    ["turn", "the", "page"],
    ["good", "night", "everyone"],
]


def generate(
    *,
    n_episodes: int = 1000,
    level: int = 3,
    pages_per_book: int = 40,
    off_frame_rate: float = 0.03,
    with_marks: bool = True,          # accepted for signature parity; no frame needs marks
    seed: int = 0,
):
    """Stream ``n_episodes`` kid pattern-book episodes at the given ``level``.

    Mirrors :func:`patternbooks.generate`. Returns ``(episodes, world)`` where each
    episode is ``{book, tokens, picture, marks}``.
    """
    rng = random.Random(seed)
    w = _world(seed)
    specs = FRAMES_BY_LEVEL[level]
    episodes = []
    book_i = 0
    while len(episodes) < n_episodes:
        book = f"kids-{book_i:05d}"
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
    """The animal->sound view the comprehension check scores against — the level-1
    core relation, fully functional and present at every level."""
    return dict(world["sound"])


def quiz(world: dict, level: int = 3) -> list[tuple[str, str]]:
    """A WORKSHEET over the kid worlds: ``(question, answer)`` in the exact frames
    taught, graded by ``level``."""
    items: list[tuple[str, str]] = []
    for a, s in world["sound"].items():
        items.append((f"the {a} says ?", s))                       # animal sounds (level 1)
    if level >= 2:
        for f, c in world["colour"].items():
            items.append((f"a {f} is ?", c))                       # fruit colours
        for a, p in world["home"].items():
            items.append((f"the {a} lives in a ?", p))             # habitats
    if level >= 3:
        for x, y in world["opposite"].items():
            items.append((f"the opposite of {x} is ?", y))         # opposites
    return items
