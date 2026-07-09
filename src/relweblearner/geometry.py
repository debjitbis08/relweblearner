"""Ensemble geometry (P8, stretch): is concept geometry stable across runs?

Hypothesis: the geometric structure of the learned concept space may be stable
only across an *ensemble*, not in any single run. We spectral-embed each web
(graph-Laplacian eigenmaps) and ask whether the **magnitude axis** — the number
line implicit in the successor chain — is recovered, and whether it stabilizes
across the ensemble even though any single run's orientation is arbitrary.

Why it's arbitrary per run: a Laplacian eigenvector is defined only up to sign,
and each learner sees a different collection universe and observation order — so
the Fiedler coordinate of "the class of size 3" points in a run-dependent
direction. Aligning the ensemble (fix each run's sign against a reference) is
what makes the shared geometry appear.
"""

from __future__ import annotations

import numpy as np


def relational_graph(match_pairs, onemores, w_match: float = 1.0, w_onemore: float = 1.0):
    """Undirected weighted adjacency over collections.

    MATCH edges bind same-class collections into clusters; ONEMORE edges chain
    the clusters into the magnitude order. Returns ``(nodes, A)``.
    """
    nodes = sorted(
        {x for p in match_pairs for x in tuple(p)}
        | {x for (a, b), _e in onemores for x in (a, b)}
    )
    idx = {n: i for i, n in enumerate(nodes)}
    A = np.zeros((len(nodes), len(nodes)))
    for p in match_pairs:
        a, b = tuple(p)
        A[idx[a], idx[b]] += w_match
        A[idx[b], idx[a]] += w_match
    for (a, b), _e in onemores:
        if a in idx and b in idx:
            A[idx[a], idx[b]] += w_onemore
            A[idx[b], idx[a]] += w_onemore
    return nodes, A


def laplacian_eigenmaps(A: np.ndarray, dim: int = 2):
    """Graph-Laplacian eigenmaps: the ``dim`` smallest nonzero eigenvectors.

    Returns ``(embedding[n, dim], eigenvalues)``. Column 0 is the Fiedler
    vector — the magnitude axis for a chain-like graph.
    """
    d = A.sum(axis=1)
    L = np.diag(d) - A
    vals, vecs = np.linalg.eigh(L)              # symmetric -> real, ascending
    return vecs[:, 1 : 1 + dim], vals


def embed_run(match_pairs, onemores, sizes: dict) -> dict:
    """One run: relational graph -> eigenmaps -> per-size magnitude-axis profile."""
    nodes, A = relational_graph(match_pairs, onemores)
    emb, _vals = laplacian_eigenmaps(A, dim=2)
    return size_profile(nodes, emb[:, 0], sizes)


def size_profile(nodes, fiedler: np.ndarray, sizes: dict) -> dict:
    """Mean Fiedler coordinate per hidden size (the magnitude-axis profile)."""
    by_size: dict = {}
    for n, c in zip(nodes, fiedler):
        by_size.setdefault(sizes[n], []).append(c)
    return {s: float(np.mean(cs)) for s, cs in by_size.items()}


def _profile_vector(profile: dict) -> np.ndarray:
    return np.array([profile[s] for s in sorted(profile)])


def axis_recovery(profile: dict) -> float:
    """|correlation| of the per-size profile with the true size order (0..1)."""
    sizes = np.array(sorted(profile), dtype=float)
    coords = _profile_vector(profile)
    if coords.std() == 0:
        return 0.0
    return abs(float(np.corrcoef(sizes, coords)[0, 1]))


def align_sign(profile: dict, reference: dict) -> dict:
    """Flip a run's profile so it points the same way as ``reference``."""
    a = _profile_vector(profile)
    r = _profile_vector({s: reference[s] for s in sorted(profile)})
    return {s: -v for s, v in profile.items()} if float(np.dot(a, r)) < 0 else dict(profile)


def ensemble_stability(profiles: list) -> dict:
    """Compare raw vs sign-aligned ensemble geometry.

    Aligns every run's profile to the first (a reference orientation, no truth
    used), then reports the mean per-size profile and the mean per-size spread
    (std) for raw and aligned. Aligned spread << raw spread iff the geometry is
    stable only across the aligned ensemble.
    """
    sizes = sorted(profiles[0])
    raw = np.array([[p[s] for s in sizes] for p in profiles])
    ref = profiles[0]
    aligned = np.array([[align_sign(p, ref)[s] for s in sizes] for p in profiles])
    return {
        "sizes": sizes,
        "raw_mean": raw.mean(axis=0).tolist(),
        "raw_spread": float(raw.std(axis=0).mean()),
        "aligned_mean": aligned.mean(axis=0).tolist(),
        "aligned_spread": float(aligned.std(axis=0).mean()),
    }
