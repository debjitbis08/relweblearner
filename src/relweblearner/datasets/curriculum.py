"""Synthetic pattern-book corpus — the R2 (curriculum reading) data source.

A picture-book PAGE is a native JOINT EPISODE: an illustration (the perceptual
channel, here a single ``picture`` region token) co-presented with a caption
(the language channel, a word sequence), plus the reader's tap on the pictured
referent (spec §0). Early children's books are FRAME MACHINES: one template
iterated with slot substitution (the Brown-Bear convention), so the same fact
recurs across pages and books and accrues origins.

The hidden world is six animals, each with a colour (``has-colour``); it mirrors
``experiment0n_frames.py`` exactly (insertion order and RNG seed) so the module's
acceptance numbers reproduce the spec's reference run. Two caption frames express
the one relation:

    F5 = ``i see a <colour> <animal>``      F4 = ``the <animal> is <colour>``

Only the concept web ever uses the bare ids (``bear``, ``red`` …); the language
side works in a disjoint ``w:``-prefixed surface namespace (built in
``curriculum.py``), so nothing a learner recovers string-matches a concept id
(the disjoint-namespace CI property inherited from SPEC_READWRITE §1).
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- hidden world
# has-colour, a functional relation. Insertion order is load-bearing: ``ANIMALS``
# feeds ``random.choice`` and must match experiment0n's ``list(HC)`` for the
# reference numbers (coverage 0.98, 4 taps, assimilation 0.049) to reproduce.
HIDDEN_COLOUR = {
    "bear": "red",
    "bird": "red",
    "duck": "yellow",
    "frog": "green",
    "cat": "blue",
    "horse": "yellow",
}
ANIMALS = list(HIDDEN_COLOUR)
COLOURS = sorted(set(HIDDEN_COLOUR.values()))


def _page(book: str, tokens: list[str], picture: str) -> dict:
    """One joint episode: a book id, a caption (word sequence), and the pictured
    (tappable) referent."""
    return {"book": book, "tokens": list(tokens), "picture": picture}


def _f5(animal: str) -> list[str]:
    return ["i", "see", "a", HIDDEN_COLOUR[animal], animal]


def _f4(animal: str) -> list[str]:
    return ["the", animal, "is", HIDDEN_COLOUR[animal]]


# The two genuinely off-frame captions injected into the base corpus: one narrative
# line and one question. They are the sentences that MUST land in the frontier.
OFF_FRAME = [
    ("B1", ["the", "bird", "flew", "away"], "bird"),
    ("B2", ["where", "is", "the", "cat"], "cat"),
]


def base_corpus() -> list[dict]:
    """The reference pattern-book corpus: two 60-page books whose captions mix F4
    and F5 with slot substitution, plus the two off-frame pages. Reproduces
    experiment0n_frames.py page-for-page (``random.Random(5)``, same call order),
    so induction, grounding, taps and assimilation match the spec's numbers.
    """
    rng = random.Random(5)

    def make_book(bid: str, n: int) -> list[dict]:
        out = []
        for _ in range(n):
            a = rng.choice(ANIMALS)
            toks = _f5(a) if rng.random() < 0.5 else _f4(a)
            out.append(_page(bid, toks, a))
        return out

    pages = make_book("B1", 60) + make_book("B2", 60)
    pages += [_page(b, t, p) for (b, t, p) in OFF_FRAME]
    rng.shuffle(pages)
    return pages


# The pages the base corpus expects in the frontier (as token tuples).
BASE_FRONTIER = {tuple(t) for (_b, t, _p) in OFF_FRAME}


def pollution_corpus() -> list[dict]:
    """A single length-4 class that mixes a strong-majority frame with a handful
    of structurally different off-frame captions (distinct first *and* verb-slot
    tokens). Grouping by length alone and demanding exact constancy makes every
    position a slot -> an all-slot skeleton that force-parses the off-frame lines
    (the pollution). Dominance>=0.8 + the anchor minimum + rejection is the fix;
    ``test_rc_curriculum`` reproduces the failure without it.
    """
    rng = random.Random(11)
    pages = []
    for _ in range(20):
        a = rng.choice(ANIMALS)
        pages.append(_page("B1", _f4(a), a))
    off = [
        ("B1", ["a", "frog", "can", "jump"], "frog"),
        ("B1", ["my", "duck", "runs", "fast"], "duck"),
        ("B1", ["that", "cat", "looks", "soft"], "cat"),
        ("B1", ["birds", "often", "fly", "high"], "bird"),
    ]
    pages += [_page(b, t, p) for (b, t, p) in off]
    return pages


def frontier_trigger_corpus() -> list[dict]:
    """A clean corpus whose length-4 class is dominated by F4 (``the _ is _``) but
    also carries a repeated *minority* question pattern (``where is the _``) plus
    one lone narrative off-frame line. First-pass induction recovers F4/F5 and
    rejects the questions to the frontier; the questions themselves show
    repetition-with-substitution, so re-inducing on the frontier grows the next
    frame — the obstruction->growth pattern (spec §1, FRONTIER AS TRIGGER). The
    lone narrative line remains in the residual frontier.
    """
    rng = random.Random(7)
    pages = []
    for _ in range(60):  # F4, the majority of the length-4 class
        a = rng.choice(ANIMALS)
        pages.append(_page("B1", _f4(a), a))
    for _ in range(60):  # F5, the length-5 class
        a = rng.choice(ANIMALS)
        pages.append(_page("B2", _f5(a), a))
    for _ in range(12):  # the repeated minority question pattern (length 4)
        a = rng.choice(ANIMALS)
        pages.append(_page("B2", ["where", "is", "the", a], a))
    pages.append(_page("B1", ["the", "bird", "flew", "away"], "bird"))
    return pages


FRONTIER_TRIGGER_RESIDUAL = {("the", "bird", "flew", "away")}


def novel_page() -> dict:
    """A page introducing a novel animal (``zebu``) in a known frame: fast-map
    territory (one page, one tap)."""
    return _page("B2", ["i", "see", "a", "red", "zebu"], "zebu")


# ------------------------------------------------------------------- interfaces


def concept_edges() -> dict[str, set]:
    """The concept web as a typed-edge projection ``{relation: {(x, y), ...}}`` —
    the drop-in ``con_edges`` for grounding."""
    return {"HC": set(HIDDEN_COLOUR.items())}


def truth() -> dict[str, str]:
    """Hidden ground truth (animal -> colour), used only for scoring."""
    return dict(HIDDEN_COLOUR)


def concept_ids() -> set[str]:
    """Every id the concept web uses (nothing on the language side may match one)."""
    return set(HIDDEN_COLOUR) | set(HIDDEN_COLOUR.values()) | {"HC"}
