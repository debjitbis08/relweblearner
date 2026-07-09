"""Compositional holdout dataset (P3).

Entities ``0..N-1``. Training facts are ``n -(+k)-> n+k`` for ``k in {1, 2}``;
**all** ``k = 5`` facts are held out for test. The held-out relation ``+5`` is
never seen in training, so a scorer can only reach it by *composition*
(``+5 = +1 + 2·(+2)``). The web learner does this exactly by transport; the KGE
baselines must generalize compositionally to score it at all.

Triples are ``(head, relation_index, tail)`` with relation names in ``rels``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Holdout:
    n_entities: int
    train: list          # (h, rel_idx, t)
    test: list           # (h, test_k, t) — relation is the integer k, composed
    rels: list           # relation names, indexed by rel_idx, e.g. ["+1", "+2"]
    train_ks: tuple
    test_k: int


def build_holdout(N: int = 200, train_ks=(1, 2), test_k: int = 5) -> Holdout:
    rels = [f"+{k}" for k in train_ks]
    train = [
        (n, i, n + k)
        for i, k in enumerate(train_ks)
        for n in range(0, N - k)
    ]
    test = [(n, test_k, n + test_k) for n in range(0, N - test_k)]
    return Holdout(N, train, test, rels, tuple(train_ks), test_k)
