"""Knowledge-graph embedding baselines: TransE and ComplEx (numpy, CPU).

Both train on the ``{+1, +2}`` triples and must score the held-out ``+5``
relation by **composition** of learned relation embeddings — TransE additively
(``r+1 + 2·r+2``), ComplEx multiplicatively (``r+1 ⊙ r+2 ⊙ r+2``). This is the
compositional-generalization test the web learner passes by construction.

Notes for reproducibility:
* Optimizer is Adam (implemented inline); training is mini-batched.
* ComplEx uses standard uniform tail-corruption negatives and fits the training
  relations exactly. TransE additionally mixes in *nearby* (hard) negatives —
  without them TransE collapses to the ``r ≈ 0`` degenerate on a dense integer
  chain and learns nothing (a known weakness); with them it learns local order.
* numpy, not torch: the models are tiny (dim 32, N≈200) and this keeps the
  baseline deterministic and dependency-light.
"""

from __future__ import annotations

import numpy as np


def _ranks(scores: np.ndarray, correct: int, higher_is_better: bool) -> int:
    target = scores[correct]
    better = np.sum(scores > target) if higher_is_better else np.sum(scores < target)
    return int(better) + 1


class _Adam:
    def __init__(self, shape, lr):
        self.lr = lr
        self.m = np.zeros(shape)
        self.v = np.zeros(shape)
        self.t = 0

    def step(self, P, g):
        self.t += 1
        self.m = 0.9 * self.m + 0.1 * g
        self.v = 0.999 * self.v + 0.001 * (g * g)
        mh = self.m / (1 - 0.9 ** self.t)
        vh = self.v / (1 - 0.999 ** self.t)
        P -= self.lr * mh / (np.sqrt(vh) + 1e-8)


class TransE:
    """TransE: score(h, r, t) = -||E_h + R_r - E_t||. Margin ranking loss."""

    def __init__(self, n_entities: int, n_relations: int, dim: int = 32, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.E = rng.normal(0, 0.1, (n_entities, dim))
        self.R = rng.normal(0, 0.1, (n_relations, dim))

    def fit(self, triples, epochs: int = 800, bs: int = 64, lr: float = 0.01,
            margin: float = 3.0, seed: int = 0):
        rng = np.random.default_rng(seed)
        tr = np.asarray(triples)
        H, Ri, T = tr[:, 0], tr[:, 1], tr[:, 2]
        n = self.E.shape[0]
        oE, oR = _Adam(self.E.shape, lr), _Adam(self.R.shape, lr)
        idx = np.arange(len(tr))
        for _ in range(epochs):
            rng.shuffle(idx)
            for s in range(0, len(idx), bs):
                b = idx[s:s + bs]
                h, ri, t = H[b], Ri[b], T[b]
                # hard negatives: nearby corruption, plus 30% uniform
                tn = np.clip(t + rng.choice([-2, -1, 1, 2], size=len(b)), 0, n - 1)
                u = rng.random(len(b)) < 0.3
                tn[u] = rng.integers(0, n, size=int(u.sum()))
                r = self.R[ri]
                pos, neg = self.E[h] + r - self.E[t], self.E[h] + r - self.E[tn]
                dp = np.linalg.norm(pos, axis=1) + 1e-9
                dn = np.linalg.norm(neg, axis=1) + 1e-9
                a = (margin + dp - dn) > 0
                gp = (pos / dp[:, None]) * a[:, None]
                gn = (neg / dn[:, None]) * a[:, None]
                gE, gR = np.zeros_like(self.E), np.zeros_like(self.R)
                np.add.at(gE, h, gp - gn)
                np.add.at(gE, t, -gp)
                np.add.at(gE, tn, gn)
                np.add.at(gR, ri, gp - gn)
                oE.step(self.E, gE)
                oR.step(self.R, gR)

    def compose(self, rel_indices) -> np.ndarray:
        return self.R[list(rel_indices)].sum(axis=0)

    def rank_tail(self, h: int, rvec: np.ndarray, correct: int) -> int:
        d = np.linalg.norm(self.E[h] + rvec - self.E, axis=1)
        return _ranks(d, correct, higher_is_better=False)


class ComplEx:
    """ComplEx: score(h, r, t) = Re(<e_h, w_r, conj(e_t)>). Logistic loss."""

    def __init__(self, n_entities: int, n_relations: int, dim: int = 32, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.Er = rng.normal(0, 0.1, (n_entities, dim))
        self.Ei = rng.normal(0, 0.1, (n_entities, dim))
        self.Rr = rng.normal(0, 0.1, (n_relations, dim))
        self.Ri = rng.normal(0, 0.1, (n_relations, dim))

    def _score(self, hr, hi, rr, ri, tr, ti):
        return np.sum(hr * rr * tr + hr * ri * ti + hi * rr * ti - hi * ri * tr, axis=-1)

    def fit(self, triples, epochs: int = 300, bs: int = 128, lr: float = 0.01,
            reg: float = 1e-3, seed: int = 0):
        rng = np.random.default_rng(seed)
        tr = np.asarray(triples)
        H, Ridx, T = tr[:, 0], tr[:, 1], tr[:, 2]
        n = self.Er.shape[0]
        opt = [_Adam(p.shape, lr) for p in (self.Er, self.Ei, self.Rr, self.Ri)]
        idx = np.arange(len(tr))
        for _ in range(epochs):
            rng.shuffle(idx)
            for s in range(0, len(idx), bs):
                b = idx[s:s + bs]
                h, ridx = H[b], Ridx[b]
                Tn = rng.integers(0, n, size=len(b))
                for tt, y in ((T[b], 1.0), (Tn, -1.0)):
                    hr, hi = self.Er[h], self.Ei[h]
                    rr, ri = self.Rr[ridx], self.Ri[ridx]
                    tr_, ti = self.Er[tt], self.Ei[tt]
                    sc = np.clip(self._score(hr, hi, rr, ri, tr_, ti), -30, 30)
                    g = (-y / (1.0 + np.exp(y * sc)))[:, None]
                    gEr, gEi = np.zeros_like(self.Er), np.zeros_like(self.Ei)
                    gRr, gRi = np.zeros_like(self.Rr), np.zeros_like(self.Ri)
                    np.add.at(gEr, h, g * (rr * tr_ + ri * ti) + reg * hr)
                    np.add.at(gEi, h, g * (rr * ti - ri * tr_) + reg * hi)
                    np.add.at(gEr, tt, g * (hr * rr - hi * ri) + reg * tr_)
                    np.add.at(gEi, tt, g * (hr * ri + hi * rr) + reg * ti)
                    np.add.at(gRr, ridx, g * (hr * tr_ + hi * ti) + reg * rr)
                    np.add.at(gRi, ridx, g * (hr * ti - hi * tr_) + reg * ri)
                    for o, P, gp in zip(opt, (self.Er, self.Ei, self.Rr, self.Ri),
                                        (gEr, gEi, gRr, gRi)):
                        o.step(P, gp)

    def compose(self, rel_indices) -> tuple:
        rr = np.ones_like(self.Rr[0])
        ri = np.zeros_like(self.Ri[0])
        for idx in rel_indices:
            ar, ai = self.Rr[idx], self.Ri[idx]
            rr, ri = rr * ar - ri * ai, rr * ai + ri * ar
        return rr, ri

    def rank_tail(self, h: int, rvec: tuple, correct: int) -> int:
        rr, ri = rvec
        scores = self._score(self.Er[h], self.Ei[h], rr, ri, self.Er, self.Ei)
        return _ranks(scores, correct, higher_is_better=True)
