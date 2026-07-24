"""Synthetic-only tests for the pinned G9 numeric module.

Never touches sealed blocks, results/, or /data (house no-smoke-run
rule).  The equivalence tests import the Phase A analysis script to
prove the pinned predictor is behaviorally identical to the formula
Phase A round 2 selected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from relweblearner.bench.graphlog_g9_conditional import (
    G9ConditionalError,
    beta_quantile,
    chebyshev_error_estimate,
    claim_4_verdict,
    crossed_under_pinned_rule,
    crossing_status,
    gershgorin_preconditioned_upper,
    guard_band_ceiling,
    jeffreys_lower_bound,
    midpoint_distance,
)


ROOT = Path(__file__).resolve().parent.parent


def _load_phase_a_module():
    spec = importlib.util.spec_from_file_location(
        "g9_phase_a_analysis", ROOT / "scripts/g9_phase_a_analysis.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _path_system(n: int = 6) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    laplacian = 2.0 * np.eye(n) + np.eye(n)
    laplacian[np.arange(n - 1), np.arange(1, n)] = -1.0
    laplacian[np.arange(1, n), np.arange(n - 1)] = -1.0
    forcing = np.array([0.3, -0.1, 0.7, 0.0, -0.4, 0.2])
    y_u = np.array([1.0, 0.0, 1.0, 1.0, 0.0, 0.0])
    return laplacian, forcing, y_u


def _clique_system() -> tuple[np.ndarray, np.ndarray]:
    clique = np.ones((6, 6)) + 0.5 * np.eye(6)
    residual = clique @ np.array([1.0, 0.0, 0.0, 1.0, 0.0, 1.0]) \
        + np.array([0.2, -0.3, 0.1, 0.4, -0.2, 0.05])
    return clique, residual


class TestPredictorEquivalenceWithPhaseA:
    def test_chebyshev_matches_phase_a_bitwise(self):
        phase_a = _load_phase_a_module()
        for H, r in (
            (_path_system()[0],
             _path_system()[0] @ _path_system()[2] + _path_system()[1]),
            _clique_system(),
        ):
            ours = chebyshev_error_estimate(H, r)
            theirs = phase_a.chebyshev_estimate(H, r)
            assert np.array_equal(ours, theirs)

    def test_crossing_mirror_matches_phase_a(self):
        phase_a = _load_phase_a_module()
        cases = [
            (0.9, 0.0, (1.0,)), (0.49, 0.0, (1.0,)), (0.51, 0.0, (1.0,)),
            (-0.6, 0.0, (1.0,)), (0.2, 1.0, (0.0,)), (0.5, 0.0, (1.0,)),
            (0.7, 0.0, ()), (0.4, 0.0, (1.0, 2.0)),
        ]
        for field, own, opposing in cases:
            assert crossed_under_pinned_rule(field, own, opposing) \
                == phase_a.crossed_under_rule(field, own, opposing)

    def test_gershgorin_matches_phase_a_interval(self):
        phase_a = _load_phase_a_module()
        H, _ = _clique_system()
        diagonal = np.diag(H)
        sqrt_d = np.sqrt(diagonal)
        off = np.abs(H / np.outer(sqrt_d, sqrt_d))
        np.fill_diagonal(off, 0.0)
        expected = 1.0 + float(off.sum(axis=1).max())
        assert gershgorin_preconditioned_upper(H) == expected
        assert phase_a.chebyshev_estimate(H, np.ones(6)) is not None


class TestPredictorProperties:
    def test_degree_bookkeeping_krylov_membership(self):
        H, forcing, y_u = _path_system()
        residual = H @ y_u + forcing
        estimate = chebyshev_error_estimate(H, residual)
        diagonal = np.diag(H)
        f = -residual / diagonal
        basis = [f]
        for _ in range(3):
            basis.append((H @ basis[-1]) / diagonal)
        matrix = np.stack(basis, axis=1)
        coefficients = np.linalg.lstsq(matrix, estimate, rcond=None)[0]
        assert np.linalg.norm(matrix @ coefficients - estimate) < 1e-10

    def test_contraction_on_diverging_jacobi_system(self):
        clique, residual = _clique_system()
        true_error = np.linalg.solve(clique, -residual)
        estimate = chebyshev_error_estimate(clique, residual)
        assert np.linalg.norm(estimate - true_error) \
            <= np.linalg.norm(true_error) + 1e-12

    def test_rejects_nonpositive_diagonal(self):
        bad = np.array([[0.0, 1.0], [1.0, 2.0]])
        with pytest.raises(G9ConditionalError):
            chebyshev_error_estimate(bad, np.ones(2))


class TestGuardBand:
    def test_ceiling_formula(self):
        assert guard_band_ceiling(1e-6, 0.0, 0.0) == 2e-6
        assert guard_band_ceiling(1e-6, 1e-9, 1e-9) \
            == 2e-6 * (1 + 1e-9) + 1e-9

    def test_three_valued_status(self):
        ceiling = 1e-3
        assert crossing_status(0.9, 0.0, (1.0,), ceiling) == "CROSSED"
        assert crossing_status(0.1, 0.0, (1.0,), ceiling) == "NOT_CROSSED"
        assert crossing_status(0.5005, 0.0, (1.0,), ceiling) \
            == "AMBIGUOUS_CROSSING"
        assert crossing_status(0.4995, 0.0, (1.0,), ceiling) \
            == "AMBIGUOUS_CROSSING"
        assert crossing_status(0.7, 0.0, (), ceiling) is None

    def test_midpoint_distance_invariant_form(self):
        assert midpoint_distance(0.8, 0.0, (1.0,)) == pytest.approx(0.3)
        assert midpoint_distance(0.8, 1.0, (0.0,)) == pytest.approx(0.3)
        assert midpoint_distance(1.4, 1.0, (2.0, 0.0)) == pytest.approx(0.1)


class TestJeffreysPassRule:
    def test_beta_quantile_uniform_identity(self):
        for p in (0.2, 0.5, 0.9):
            assert beta_quantile(p, 1.0, 1.0) == pytest.approx(p, abs=1e-9)

    def test_beta_quantile_symmetry(self):
        assert beta_quantile(0.5, 3.5, 3.5) == pytest.approx(0.5, abs=1e-9)
        low = beta_quantile(0.2, 2.5, 4.5)
        high = beta_quantile(0.8, 4.5, 2.5)
        assert low == pytest.approx(1.0 - high, abs=1e-9)

    def test_referee_reference_values(self):
        # The four sanity checks computed independently during the §4.5
        # review of the Phase A report (decision statistic to 3 decimals).
        cases = [
            ((6, 0, 8, 0), 0.891, True),     # g7-scale transfer
            ((16, 4, 30, 1), 0.821, True),   # g8-scale transfer
            ((5, 0, 30, 0), 0.914, True),    # perfect at non-vacuity minimum
            ((18, 2, 21, 10), 0.715, False), # branch!=0 baseline replayed
        ]
        for (tp, fn, tn, fp), expected, passes in cases:
            verdict = claim_4_verdict(tp, fn, tn, fp)
            assert verdict["decision_statistic"] \
                == pytest.approx(expected, abs=2e-3)
            assert verdict["passed"] is passes

    def test_lower_bound_is_below_point_estimate(self):
        assert jeffreys_lower_bound(22, 4) < 22 / 26
        assert jeffreys_lower_bound(38, 1) < 38 / 39

    def test_rejects_empty_counts(self):
        with pytest.raises(G9ConditionalError):
            jeffreys_lower_bound(0, 0)
