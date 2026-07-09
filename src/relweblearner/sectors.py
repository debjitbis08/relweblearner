"""Symmetry-sector inference (P2): classify relations by their transport.

Given loop observations and the coordinates the P1b chain constructed, each
observation ``(a, b, r)`` contributes a transport sample ``coord(b) - coord(a)``
for relation ``r``. The learner asks, per relation, whether a *single constant*
transport explains the samples:

* it does, with ``g = 0`` → **symmetric** (``r`` is its own converse: a relation
  seen both ways between a pair forces ``2g = 0`` → ``g = 0``);
* it does, with ``g ≠ 0`` → **antisymmetric** (a directed generator);
* it does **not** (no constant fits) → **non-homogeneous**: the relation is a
  motif, a family of edges, not a single algebra transport. ``double`` lands
  here — its transport is ``count(a)``, which varies per edge.

**Noise tolerance (the description-length / exception rule).** The winning
hypothesis is the transport that minimizes total cost = (a small constant for
"one homogeneous transport") + (a fixed penalty per exception). Equivalently: a
relation is homogeneous iff its best transport explains at least
``1 - exception_fraction`` of the samples. One adversarially mislabeled example
is a single exception — cheaper to pay than to abandon the true transport — so
it cannot flip the classification.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

SYMMETRIC = "symmetric"
ANTISYMMETRIC = "antisymmetric"
NON_HOMOGENEOUS = "non-homogeneous"


@dataclass(frozen=True)
class RelationSector:
    """The inferred sector of one relation."""

    relation: str
    sector: str                 # SYMMETRIC | ANTISYMMETRIC | NON_HOMOGENEOUS
    transport: Optional[int]    # the constant transport, or None if a motif
    support: float              # fraction of samples the best transport explains
    n_samples: int

    @property
    def is_motif(self) -> bool:
        return self.sector == NON_HOMOGENEOUS


def _samples(observations: Iterable, coord: dict) -> dict[str, list[int]]:
    samples: dict[str, list[int]] = defaultdict(list)
    for o in observations:
        if o.a in coord and o.b in coord:
            samples[o.relation].append(coord[o.b] - coord[o.a])
    return samples


def infer_sectors(
    observations: Iterable,
    coord: dict,
    exception_fraction: float = 0.2,
) -> dict[str, RelationSector]:
    """Classify every relation appearing in ``observations``.

    ``coord`` maps entity → integer coordinate (the P1b chain position).
    ``exception_fraction`` is the noise budget: up to this fraction of a
    relation's samples may disagree with its transport before the relation is
    judged non-homogeneous.
    """
    out: dict[str, RelationSector] = {}
    for rel, s in _samples(observations, coord).items():
        n = len(s)
        best_g, best_count = Counter(s).most_common(1)[0]
        support = best_count / n
        if support < 1.0 - exception_fraction:
            out[rel] = RelationSector(rel, NON_HOMOGENEOUS, None, support, n)
        elif best_g == 0:
            out[rel] = RelationSector(rel, SYMMETRIC, 0, support, n)
        else:
            out[rel] = RelationSector(rel, ANTISYMMETRIC, best_g, support, n)
    return out
