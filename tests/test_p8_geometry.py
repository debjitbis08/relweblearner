"""P8 acceptance (stretch): ensemble geometry.

The hypothesis: the concept geometry (a magnitude axis) is recovered in each
run but its orientation is arbitrary per run, so it is stable only across the
sign-aligned ensemble — not in any single run's raw coordinates.
"""

from __future__ import annotations

import numpy as np

from relweblearner import audit, geometry
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner


def _profiles(n_runs: int = 20):
    profs = []
    for seed in range(n_runs):
        cols = make_collections(60, seed=seed)
        sizes = {c: len(v) for c, v in cols.items()}
        L = NumberLearner()
        L.ingest_all(random_stream(cols, 900, seed=seed + 100))
        mp, om = audit.derive_facts(L.journal, k=2)
        profs.append(geometry.embed_run(mp, om, sizes))
    return profs


def _orientation(profile):
    sizes = sorted(profile)
    coords = [profile[s] for s in sizes]
    return np.sign(np.corrcoef(sizes, coords)[0, 1])


def test_magnitude_axis_recovered_in_each_run():
    profs = _profiles()
    recoveries = [geometry.axis_recovery(p) for p in profs]
    assert np.mean(recoveries) >= 0.8            # the axis exists every run
    assert min(recoveries) >= 0.6


def test_per_run_orientation_is_arbitrary():
    profs = _profiles()
    signs = {_orientation(p) for p in profs}
    assert len(signs) > 1                        # both orientations occur -> varies per run


def test_geometry_stabilizes_only_across_the_aligned_ensemble():
    profs = _profiles()
    st = geometry.ensemble_stability(profs)

    # aligned ensemble is tighter than raw
    assert st["aligned_spread"] < st["raw_spread"]

    # aligned mean recovers the magnitude axis; raw mean washes out
    aligned = {s: v for s, v in zip(st["sizes"], st["aligned_mean"])}
    raw = {s: v for s, v in zip(st["sizes"], st["raw_mean"])}
    assert geometry.axis_recovery(aligned) >= 0.9
    assert geometry.axis_recovery(aligned) > geometry.axis_recovery(raw)
