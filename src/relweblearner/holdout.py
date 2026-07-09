"""Compositional-holdout evaluation (P3): web learner vs KGE baselines.

The web learner builds a web from the ``{+1, +2}`` training facts and scores the
held-out ``+5`` triples by **transport composition** — the tail is the node
whose transport from the head is ``+5``. Because the frozen algebra composes
``+1`` and ``+2`` exactly, this is right for every triple: **Hits@1 = 1.0 by
construction**, with zero parameters learned for the ``+5`` relation.

The baselines (``baselines/kge.py``) must instead compose their learned relation
embeddings; the gap is the headline sample-efficiency figure.
"""

from __future__ import annotations

from dataclasses import dataclass

from .algebra import IntegerGroup
from .datasets.holdout import Holdout
from .holonomy import potential
from .web import Web


@dataclass
class Metrics:
    name: str
    hits1: float
    hits10: float
    mrr: float


def _metrics(name: str, ranks: list) -> Metrics:
    n = len(ranks)
    hits1 = sum(1 for r in ranks if r == 1) / n
    hits10 = sum(1 for r in ranks if r <= 10) / n
    mrr = sum(1.0 / r for r in ranks) / n
    return Metrics(name, hits1, hits10, mrr)


# ---------------------------------------------------------------- web learner
def build_web(data: Holdout) -> Web:
    """A web from the training facts: each ``+k`` fact is a ``+k`` transport edge."""
    w = Web(IntegerGroup(), name="holdout")
    for h, ri, t in data.train:
        k = data.train_ks[ri]
        w.add_edge(h, t, f"+{k}", k)
    return w


def web_metrics(data: Holdout) -> Metrics:
    """Score the held-out ``+k`` triples by transport composition."""
    w = build_web(data)
    phi = potential(w)                              # exact coordinate per node
    base = phi.get(0, 0)
    coord = {n: phi[n] - base for n in w.nodes}
    coords = list(coord.values())
    ranks = []
    for h, k, t in data.test:
        target = coord[h] + k
        # rank entities by |coordinate - target|; the true tail sits exactly at
        # the target (distance 0) -> rank 1. Exact for every triple.
        better = sum(1 for c in coords if abs(c - target) < abs(coord[t] - target))
        ranks.append(better + 1)
    return _metrics("web", ranks)


# ---------------------------------------------------------------- baselines
def transe_metrics(data: Holdout, dim: int = 32, epochs: int = 300, seed: int = 0) -> Metrics:
    from .baselines.kge import TransE

    model = TransE(data.n_entities, len(data.rels), dim=dim, seed=seed)
    model.fit(data.train, epochs=epochs, seed=seed)
    # +5 = +1 then +2 then +2  (relation indices 0, 1, 1 for train_ks (1, 2))
    steps = _compose_steps(data)
    rvec = model.compose(steps)
    ranks = [model.rank_tail(h, rvec, t) for h, _k, t in data.test]
    return _metrics("TransE", ranks)


def complex_metrics(data: Holdout, dim: int = 32, epochs: int = 300, seed: int = 0) -> Metrics:
    from .baselines.kge import ComplEx

    model = ComplEx(data.n_entities, len(data.rels), dim=dim, seed=seed)
    model.fit(data.train, epochs=epochs, seed=seed)
    steps = _compose_steps(data)
    rvec = model.compose(steps)
    ranks = [model.rank_tail(h, rvec, t) for h, _k, t in data.test]
    return _metrics("ComplEx", ranks)


def _compose_steps(data: Holdout) -> list:
    """Relation-index sequence whose transports sum to ``test_k``.

    Greedy over the (sorted, descending) training steps — e.g. test_k=5 with
    steps {+1:0, +2:1} -> [1, 1, 0] (2+2+1).
    """
    ks = sorted(range(len(data.train_ks)), key=lambda i: -data.train_ks[i])
    remaining = data.test_k
    steps = []
    while remaining > 0:
        for i in ks:
            if data.train_ks[i] <= remaining:
                steps.append(i)
                remaining -= data.train_ks[i]
                break
        else:
            break
    return steps
