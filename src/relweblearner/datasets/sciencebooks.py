"""Grounded elementary-SCIENCE generator — the science rung of the firehose.

Same machine as :mod:`kidbooks`/:mod:`mathbooks` (one template iterated with slot
substitution, emitted as joint ``{book, tokens, picture, marks}`` episodes with the
picture/tap channel, so parsed frames commit CLEAN oriented facts). The worlds are
the staples of a first science reader — modelled on what elementary nature/science
primers actually teach, so the creature *learns science*, not just science-flavoured
words:

    sense    ``the <organ> is for <sense>``       eye -> sight, ear -> hearing …
    class    ``a <animal> is a <class>``            whale -> mammal, frog -> amphibian …
    matter   ``<substance> is a <state>``           ice -> solid, water -> liquid …
    order    ``<planet> is the <ordinal> planet``    mars -> fourth, earth -> third …

Every frame's anchor set is DISJOINT from any other frame it shares a length with
(here and across the other generators that feed the same creature), so no two
constructions collapse into a degenerate skeleton. ``order`` deliberately reuses the
ordinal words, tying science back to the number curriculum.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden worlds
ORGAN_SENSE = {
    "eye": "sight", "ear": "hearing", "nose": "smell", "tongue": "taste", "skin": "feeling",
}
ANIMAL_CLASS = {
    "whale": "mammal", "dog": "mammal", "bat": "mammal",
    "eagle": "bird", "owl": "bird", "hen": "bird",
    "shark": "fish", "trout": "fish", "carp": "fish",
    "snake": "reptile", "lizard": "reptile", "turtle": "reptile",
    "frog": "amphibian", "newt": "amphibian",
    "ant": "insect", "bee": "insect", "moth": "insect",
}
# balanced so no single state dominates the target slot
SUBSTANCE_STATE = {
    "ice": "solid", "rock": "solid", "wood": "solid", "iron": "solid", "glass": "solid",
    "water": "liquid", "milk": "liquid", "oil": "liquid",
    "steam": "gas", "air": "gas", "smoke": "gas",
}
PLANET_ORDER = {
    "mercury": "first", "venus": "second", "earth": "third", "mars": "fourth",
    "jupiter": "fifth", "saturn": "sixth", "uranus": "seventh", "neptune": "eighth",
}

SENSES = set(ORGAN_SENSE.values())
CLASSES = set(ANIMAL_CLASS.values())
STATES = set(SUBSTANCE_STATE.values())
ORDINALS = set(PLANET_ORDER.values())


def _world(seed: int = 0) -> dict:
    return {"sense": dict(ORGAN_SENSE), "class": dict(ANIMAL_CLASS),
            "matter": dict(SUBSTANCE_STATE), "order": dict(PLANET_ORDER)}


# ---------------------------------------------------------------- frame specs
# picture = first slot filler (the entity) -> ``_orient`` makes it the fact source.

def _f_sense(rng, w):                               # the <organ> is for <sense>
    o = rng.choice(list(ORGAN_SENSE))
    return (["the", o, "is", "for", w["sense"][o]], o, None)

def _f_class(rng, w):                               # a <animal> is a <class>
    a = rng.choice(list(ANIMAL_CLASS))
    return (["a", a, "is", "a", w["class"][a]], a, None)

def _f_matter(rng, w):                              # <substance> is a <state>
    s = rng.choice(list(SUBSTANCE_STATE))
    return ([s, "is", "a", w["matter"][s]], s, None)

def _f_order(rng, w):                               # <planet> is the <ordinal> planet
    p = rng.choice(list(PLANET_ORDER))
    return ([p, "is", "the", w["order"][p], "planet"], p, None)


FRAMES_BY_LEVEL = {
    1: [_f_sense, _f_class],                        # living-world basics
    2: [_f_sense, _f_class, _f_matter, _f_order],   # + matter + the solar system
}

OFF_FRAME = [
    ["let", "us", "look", "closely"],
    ["what", "do", "you", "observe"],
    ["science", "is", "everywhere"],
    ["ask", "why", "and", "how"],
]


def generate(*, n_episodes: int = 1000, level: int = 2, pages_per_book: int = 40,
             off_frame_rate: float = 0.03, with_marks: bool = True, seed: int = 0):
    """Stream ``n_episodes`` grounded science episodes at ``level``. Mirrors
    :func:`kidbooks.generate`; returns ``(episodes, world)``."""
    rng = random.Random(seed)
    w = _world(seed)
    specs = FRAMES_BY_LEVEL[level]
    episodes = []
    book_i = 0
    while len(episodes) < n_episodes:
        book = f"science-{book_i:05d}"
        book_i += 1
        for _ in range(pages_per_book):
            if len(episodes) >= n_episodes:
                break
            if rng.random() < off_frame_rate:
                episodes.append({"book": book, "tokens": list(rng.choice(OFF_FRAME)),
                                 "picture": None, "marks": None})
                continue
            tokens, picture, marks = rng.choice(specs)(rng, w)
            episodes.append({"book": book, "tokens": tokens, "picture": picture,
                             "marks": marks if with_marks else None})
    return episodes, w


def truth(world: dict) -> dict:
    """The animal->class view for a quick comprehension check (the level-1 core)."""
    return dict(world["class"])


def quiz(world: dict, level: int = 2) -> list[tuple[str, str]]:
    """A WORKSHEET for this world: ``(question, answer)`` pairs the creature is
    examined on, phrased in the exact frames it was taught (blank marked ``?``).
    Only relations present at ``level`` are asked."""
    items: list[tuple[str, str]] = []
    for o, s in world["sense"].items():
        items.append((f"the {o} is for ?", s))
    for a, c in world["class"].items():
        items.append((f"a {a} is a ?", c))
    if level >= 2:
        for s, st in world["matter"].items():
            items.append((f"{s} is a ?", st))
        for p, o in world["order"].items():
            items.append((f"{p} is the ? planet", o))
    return items
