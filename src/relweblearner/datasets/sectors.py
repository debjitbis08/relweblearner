"""Relation loop observations for symmetry-sector inference (P2).

Entities carry a hidden count (their coordinate — in the full pipeline this is
the position in the P1b number chain). The learner never sees the count; it
sees loop observations ``(a, b, relation)`` whose closing path runs through the
count backbone, so each observation pins the relation's transport to
``count(b) - count(a)``:

* ``same``  — equal count → transport 0 (symmetric).
* ``succ``  — count + 1 → transport +1 (antisymmetric).
* ``double`` — count × 2 → transport = count(a), which VARIES per edge: no
  constant transport exists, so ``double`` is non-homogeneous (a motif).

``count`` here is ground truth for scoring/grounding only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class LoopObservation:
    """A relational fact whose closure through the count backbone is a loop."""

    a: str
    b: str
    relation: str


def make_entities(max_count: int = 8, per_count: int = 3) -> tuple[dict, dict]:
    """Entities ``e{c}_{i}`` of count ``c`` for ``c in 0..max_count``.

    Returns ``(by_count, coord)`` where ``coord[entity] = c`` (the chain
    coordinate) and ``by_count[c] = [entities]``.
    """
    by_count: dict[int, list[str]] = {}
    coord: dict[str, int] = {}
    for c in range(0, max_count + 1):
        for i in range(per_count):
            n = f"e{c}_{i}"
            by_count.setdefault(c, []).append(n)
            coord[n] = c
    return by_count, coord


def loop_observations(
    by_count: dict,
    n: int,
    seed: int,
    relations=("same", "succ", "double"),
) -> list[LoopObservation]:
    """``n`` random loop observations spread over the relations."""
    rng = random.Random(seed)
    counts = sorted(by_count)
    obs: list[LoopObservation] = []
    succ_ok = [c for c in counts if (c + 1) in by_count and len(by_count[c + 1]) > 0]
    dbl_ok = [c for c in counts if c >= 1 and (2 * c) in by_count]
    for _ in range(n):
        rel = rng.choice(relations)
        if rel == "same":
            c = rng.choice([c for c in counts if len(by_count[c]) >= 2])
            a, b = rng.sample(by_count[c], 2)
        elif rel == "succ":
            c = rng.choice(succ_ok)
            a, b = rng.choice(by_count[c]), rng.choice(by_count[c + 1])
        else:  # double
            c = rng.choice(dbl_ok)
            a, b = rng.choice(by_count[c]), rng.choice(by_count[2 * c])
        obs.append(LoopObservation(a, b, rel))
    return obs


def inject_mislabel(
    obs: list[LoopObservation], relation: str, seed: int
) -> list[LoopObservation]:
    """Adversarially mislabel one observation as ``relation`` with a wrong
    transport (a same-count pair labeled ``succ``, say). Returns a new list."""
    rng = random.Random(seed)

    def count_of(e: str) -> int:               # entity names are e{c}_{i}
        return int(e[1:].split("_")[0])

    ents = sorted({o.a for o in obs} | {o.b for o in obs})
    groups: dict[int, list[str]] = {}
    for e in ents:
        groups.setdefault(count_of(e), []).append(e)
    equal = [g for g in groups.values() if len(g) >= 2]
    a, b = rng.choice(equal)[:2] if equal else (ents[0], ents[-1])
    bad = LoopObservation(a, b, relation)      # equal-count pair mislabeled: a lie
    out = list(obs)
    out.insert(rng.randrange(len(out) + 1), bad)
    return out
