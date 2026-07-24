"""Pinned G9 predictor, guard band, and pass-rule numerics.

G9 tests a mechanism-level predictor of anti-propagation (plan
``docs/g9-anti-propagation-plan.md`` §5; constants fixed by the sealed
Phase A report ``docs/g9-phase-a-report.md`` §6).  This module is the
preregistration instrument: the Phase B report script consumes it, the
enabling amendment pins it, and nothing here may change after the seed
ceremony.

Contents, all frozen:

- The **candidate predictor**: a degree-3 Chebyshev semi-iteration for
  ``H e = -r`` on the design interval ``[b/KAPPA_DESIGN, b]``, where
  ``b`` is the Gershgorin upper bound on the spectrum of
  ``D^-1/2 H D^-1/2`` (a declared closed-form 1-hop aggregate, admitted
  by the amended §8.1 coefficient rule) and ``KAPPA_DESIGN = 30`` is a
  fixed constant.  Four steps, so the estimate is a polynomial of
  degree exactly 3 in ``D^-1 H`` applied to ``D^-1 r`` — inside the
  §8.1 budget class; no solve output enters the formula.  This formula
  is behaviorally identical to Phase A round 2's
  (``scripts/g9_phase_a_analysis.py``), which selected it; the test
  suite asserts the equivalence on synthetic systems.
- The **crossing mirror** of the pinned ``anti_propagation`` rule
  (strict own/nearest-opposing midpoint, set-dedup + sorted + min
  tie-break), applied to predicted fields.
- The **guard band** (plan §5 claim 3): a crossed record is
  ``AMBIGUOUS_CROSSING`` when the field's distance to the
  own/nearest-opposing midpoint is within the disclosed solver
  ceiling; ambiguous records leave claim 4's ground truth and the
  non-vacuity count.
- The **claim-4 pass rule** (Phase A report §6): one-sided Jeffreys
  lower bounds — the 0.20 quantile of ``Beta(s + 1/2, f + 1/2)`` — for
  TPR and TNR; the claim passes iff their mean is at least the floor.
  The mean of two marginal bounds is a preregistered decision
  statistic, not a calibrated confidence bound.  The incomplete-beta
  inverse is implemented here self-contained (no SciPy dependency) and
  pinned with the rest.

Validated on synthetic systems only (the house no-smoke-run rule).
"""

from __future__ import annotations

import math

import numpy as np


G9_PREDICTOR_FAMILY = "chebyshev-semi-iteration"
G9_PREDICTOR_DEGREE = 3
G9_KAPPA_DESIGN = 30.0
G9_DIAGNOSTIC_CEILING = 0.99
G9_CLAIM4_FLOOR = 0.776
G9_JEFFREYS_QUANTILE = 0.20
G9_NONVACUITY_MIN_CROSSINGS = 5
G9_NONVACUITY_MIN_WORLDS = 2
# The frozen G7 hedge-localization threshold, reused by plan §6 as the
# decode threshold for the report-only decisiveness vocabulary.
G9_DECODE_THRESHOLD = 0.1


class G9ConditionalError(ValueError):
    """The G9 numeric construction violated a stated premise."""


def gershgorin_preconditioned_upper(laplacian_uu: np.ndarray) -> float:
    """Gershgorin upper bound on the spectrum of ``D^-1/2 H D^-1/2``.

    1-hop row-sum data only: ``1 + max_i sum_{j != i} |H_ij| /
    sqrt(d_i d_j)``.  Always contains the true spectrum, so the
    Chebyshev residual polynomial designed against it never amplifies
    any mode.
    """
    H = np.asarray(laplacian_uu, dtype=float)
    diagonal = np.diag(H)
    if np.any(diagonal <= 0.0):
        raise G9ConditionalError(
            "Gershgorin aggregate requires a positive diagonal"
        )
    sqrt_d = np.sqrt(diagonal)
    off_diagonal = np.abs(H / np.outer(sqrt_d, sqrt_d))
    np.fill_diagonal(off_diagonal, 0.0)
    return 1.0 + float(off_diagonal.sum(axis=1).max())


def chebyshev_error_estimate(
    laplacian_uu: np.ndarray,
    residual: np.ndarray,
    degree: int = G9_PREDICTOR_DEGREE,
    kappa_design: float = G9_KAPPA_DESIGN,
) -> np.ndarray:
    """The frozen candidate predictor's signed error estimate.

    Chebyshev semi-iteration for ``(D^-1 H) e = -D^-1 r`` on
    ``[b/kappa_design, b]`` with ``b`` from
    :func:`gershgorin_preconditioned_upper`; ``degree + 1`` steps total,
    a polynomial of degree exactly ``degree`` in ``D^-1 H`` applied to
    ``D^-1 r``.
    """
    H = np.asarray(laplacian_uu, dtype=float)
    diagonal = np.diag(H).copy()
    if np.any(diagonal <= 0.0):
        raise G9ConditionalError(
            "Chebyshev estimate requires a positive diagonal"
        )
    upper = gershgorin_preconditioned_upper(H)
    lower = upper / kappa_design
    theta = 0.5 * (upper + lower)
    delta = 0.5 * (upper - lower)
    sigma = theta / delta

    def apply(x: np.ndarray) -> np.ndarray:
        return (H @ x) / diagonal

    f = -np.asarray(residual, dtype=float) / diagonal
    x = f / theta
    step = x.copy()
    rho_prev = 1.0 / sigma
    for _ in range(degree):
        current_residual = f - apply(x)
        rho = 1.0 / (2.0 * sigma - rho_prev)
        step = rho * rho_prev * step + (2.0 * rho / delta) * current_residual
        x = x + step
        rho_prev = rho
    return x


def nearest_opposing_value(
    own_value: float,
    opposing_values: tuple[float, ...],
    field_value: float,
) -> float | None:
    """Mirror of the pinned rule's opposing-value selection."""
    opposing = sorted({v for v in opposing_values if v != own_value})
    if not opposing:
        return None
    return min(opposing, key=lambda value: abs(field_value - value))


def crossed_under_pinned_rule(
    field_value: float,
    own_value: float,
    opposing_values: tuple[float, ...],
) -> bool | None:
    """Exact mirror of ``anti_propagation``'s strict-midpoint crossing."""
    nearest = nearest_opposing_value(own_value, opposing_values, field_value)
    if nearest is None:
        return None
    return abs(field_value - nearest) < abs(field_value - own_value)


def midpoint_distance(
    field_value: float,
    own_value: float,
    opposing_values: tuple[float, ...],
) -> float | None:
    """Distance to the own/nearest-opposing midpoint (invariant form)."""
    nearest = nearest_opposing_value(own_value, opposing_values, field_value)
    if nearest is None:
        return None
    return abs(field_value - (own_value + nearest) / 2.0)


def guard_band_ceiling(
    field_tolerance: float,
    relative_slack: float,
    absolute_slack: float,
) -> float:
    """Plan §5 claim 3's disclosed solver ceiling for the crossing band.

    ``2 x field_tolerance`` (the guaranteed solver ceiling; one field is
    involved so 1x would suffice — the 2x is stated conservatism)
    dressed with the frozen slack constants.
    """
    return 2.0 * field_tolerance * (1.0 + relative_slack) + absolute_slack


def crossing_status(
    field_value: float,
    own_value: float,
    opposing_values: tuple[float, ...],
    ceiling: float,
) -> str | None:
    """Three-valued crossing outcome: CROSSED / NOT_CROSSED / AMBIGUOUS.

    ``AMBIGUOUS_CROSSING`` is a reported outcome, not a defect (plan §5
    claim 3); ambiguous records are excluded from claim 4's ground
    truth and from the non-vacuity count.
    """
    crossed = crossed_under_pinned_rule(field_value, own_value, opposing_values)
    if crossed is None:
        return None
    distance = midpoint_distance(field_value, own_value, opposing_values)
    if distance is not None and distance <= ceiling:
        return "AMBIGUOUS_CROSSING"
    return "CROSSED" if crossed else "NOT_CROSSED"


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """``I_x(a, b)`` via the Lentz continued fraction (self-contained)."""
    if not 0.0 <= x <= 1.0:
        raise G9ConditionalError("incomplete beta requires x in [0, 1]")
    if x == 0.0 or x == 1.0:
        return float(x)
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_front)

    def continued_fraction(x: float, a: float, b: float) -> float:
        tiny = 1e-300
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d
        h = d
        for m in range(1, 400):
            m2 = 2 * m
            numerator = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + numerator * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + numerator / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            h *= d * c
            numerator = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + numerator * d
            if abs(d) < tiny:
                d = tiny
            c = 1.0 + numerator / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                return h
        raise G9ConditionalError("incomplete beta did not converge")

    if x < (a + 1.0) / (a + b + 2.0):
        return front * continued_fraction(x, a, b) / a
    return 1.0 - math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + b * math.log1p(-x) + a * math.log(x)
    ) * continued_fraction(1.0 - x, b, a) / b


def beta_quantile(p: float, a: float, b: float) -> float:
    """Inverse of ``I_x(a, b)`` by deterministic bisection."""
    if not 0.0 < p < 1.0:
        raise G9ConditionalError("beta quantile requires p in (0, 1)")
    low, high = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (low + high)
        if _regularized_incomplete_beta(mid, a, b) < p:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def jeffreys_lower_bound(
    successes: int, failures: int, quantile: float = G9_JEFFREYS_QUANTILE,
) -> float:
    """One-sided Jeffreys lower bound: the ``quantile`` of
    ``Beta(s + 1/2, f + 1/2)`` (Phase A report §6, exact form)."""
    if successes < 0 or failures < 0:
        raise G9ConditionalError("counts must be non-negative")
    if successes + failures == 0:
        raise G9ConditionalError("Jeffreys bound requires at least one trial")
    return beta_quantile(quantile, successes + 0.5, failures + 0.5)


def claim_4_verdict(
    true_positives: int,
    false_negatives: int,
    true_negatives: int,
    false_positives: int,
    floor: float = G9_CLAIM4_FLOOR,
) -> dict[str, float | bool | int]:
    """The frozen claim-4 pass rule over realized unambiguous non-pivot
    counts.  Passes iff the mean of the TPR and TNR Jeffreys lower
    bounds is at least the floor."""
    tpr_lb = jeffreys_lower_bound(true_positives, false_negatives)
    tnr_lb = jeffreys_lower_bound(true_negatives, false_positives)
    statistic = 0.5 * (tpr_lb + tnr_lb)
    return {
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "tpr_jeffreys_lower_bound": tpr_lb,
        "tnr_jeffreys_lower_bound": tnr_lb,
        "decision_statistic": statistic,
        "floor": floor,
        "passed": bool(statistic >= floor),
    }
