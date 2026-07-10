"""LLM-authored-style pattern-book generator — the scale corpus firehose (spec §4).

The hand-training UI cannot reach StoryWeaver scale; a human is O(time) per
episode. This generator manufactures frame-graded, controlled-vocabulary pattern
books programmatically — copyright-safe, reproducible (seeded), and effectively
unlimited — so experiments run at 10^4–10^6 episodes instead of dozens. It is the
same "frame machine" a leveled reader is (one template iterated with slot
substitution), emitted as joint episodes ``{book, tokens, picture, marks}``.

Each FRAME expresses one relation over a hidden world of typed facts; the same
facts recur across books so provenance accrues and beliefs can commit. Frames are
graded into LEVELS (the reading ladder): later levels add relations and off-frame
noise. Adjacent-filler frames (``i see a <colour> <animal>``) carry gold ``marks``
so the two arguments separate without a human breakup — the machine authors the
segmentation it hasn't yet learned to induce.

``generate(n_episodes=...)`` streams as many episodes as asked; ``world`` returns
the ground truth for the comprehension check.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden world
ANIMALS = ["bear", "cat", "frog", "duck", "horse", "bird", "lion", "cow",
           "spider", "ant", "dog", "pig", "goat", "wolf", "deer", "owl"]
COLOURS = ["red", "blue", "green", "yellow", "brown", "grey", "black", "white"]
FOODS = ["grass", "meat", "corn", "fish", "leaves", "honey", "seeds", "roots"]
LEGS = ["two", "four", "six", "eight"]


def _world(seed: int) -> dict:
    """A deterministic functional world: each animal has one colour, one food and
    a leg-count. This is the truth reading is scored against — never shown as
    labels, only expressed through frames."""
    rng = random.Random(seed)
    return {
        a: {
            "colour": rng.choice(COLOURS),
            "food": rng.choice(FOODS),
            "legs": rng.choice(LEGS),
        }
        for a in ANIMALS
    }


# ---------------------------------------------------------------- frame specs
# Each spec renders a fact into (tokens, picture, marks). ``level`` grades them
# onto the reading ladder. ``marks`` (gold breakup spans) are supplied only where
# fillers abut with no anchor between them.

def _f_is(a, w):
    return (["the", a, "is", w[a]["colour"]], a, None)

def _f_see(a, w):                                  # adjacent fillers -> gold marks
    return (["i", "see", "a", w[a]["colour"], a], a, [[3, 4], [4, 5]])

def _f_legs(a, w):
    return ([a, "has", w[a]["legs"], "legs"], a, None)

def _f_eats(a, w):
    return (["the", a, "eats", w[a]["food"]], a, None)


FRAMES_BY_LEVEL = {
    1: [_f_is, _f_see],
    2: [_f_is, _f_see, _f_legs, _f_eats],
}

# off-frame lines that must land on the frontier (narrative / questions)
OFF_FRAME = [
    ["i", "like", "to", "read"],
    ["who", "can", "i", "read", "to"],
    ["what", "a", "lovely", "day"],
    ["the", "end"],
]


def generate(
    *,
    n_episodes: int = 1000,
    level: int = 2,
    pages_per_book: int = 40,
    off_frame_rate: float = 0.03,
    with_marks: bool = True,
    seed: int = 0,
):
    """Stream ``n_episodes`` pattern-book episodes at the given ladder ``level``.

    Books of ``pages_per_book`` pages each iterate the level's frames with random
    animal substitution; a fraction ``off_frame_rate`` of pages are off-frame
    (destined for the frontier). ``with_marks=False`` withholds the gold breakups
    (to test whether the model induces the segmentation itself). Returns
    ``(episodes, world)`` where each episode is ``{book, tokens, picture, marks}``.
    """
    rng = random.Random(seed)
    w = _world(seed)
    specs = FRAMES_BY_LEVEL[level]
    episodes = []
    book_i = 0
    while len(episodes) < n_episodes:
        book = f"book-{book_i:05d}"
        book_i += 1
        for _ in range(pages_per_book):
            if len(episodes) >= n_episodes:
                break
            if rng.random() < off_frame_rate:
                episodes.append({"book": book, "tokens": list(rng.choice(OFF_FRAME)),
                                 "picture": None, "marks": None})
                continue
            a = rng.choice(ANIMALS)
            tokens, picture, marks = rng.choice(specs)(a, w)
            episodes.append({
                "book": book,
                "tokens": tokens,
                "picture": picture,
                "marks": marks if with_marks else None,
            })
    return episodes, w


def truth(world: dict) -> dict:
    """Flatten the world to the ``{animal: colour}`` view the comprehension check
    scores against (the ``is``/``see`` relation)."""
    return {a: facts["colour"] for a, facts in world.items()}
