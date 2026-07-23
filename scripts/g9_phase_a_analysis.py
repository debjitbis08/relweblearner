#!/usr/bin/env python3
"""G9 Phase A: post-hoc anti-propagation analysis of the sealed blocks.

Implements the Phase A deliverables of ``docs/g9-anti-propagation-plan.md``
(sections 4.1-4.4) over both sealed seed families:

  - G7 seed family: block ``results/graphlog-certified/g7``, conditioned
    worlds rule_2/rule_3/rule_7 (draws from the G7 study manifest).
  - G8 seed family: block ``results/graphlog-certified/g8``, conditioned
    worlds rule_2/rule_5/rule_6/rule_8/rule_9/rule_12 (draws from the G8
    Part II study manifest).

For every conditioned world it reconstructs the conditional layer from the
sealed T5 opaque state with the pinned code and refuses to report anything
unless the reconstruction reproduces the sealed certificates bit-for-bit
(full canonical-digest comparison of the G7 conditional-separation
certificate, and of the G8 interior-decisiveness overlay certificate where
the block carries one).  It then reports, in full precision:

  1. Attribution (plan section 4.1): for every evaluated anti-propagation
     record, the exact signed true error ``e_c = -row_c(H_uu^-1) . r``
     decomposed over residual sites (``e_c = -sum_j G_cj r_j``), verified
     to reproduce the sealed field to solver tolerance, with the signed
     toward-own / toward-opposing mass split and the top contributing sites.
  2. Candidate predictor evaluation (plan section 4.2): a budget-compliant
     Jacobi polynomial estimate of ``e_c`` (degree <= 3 in ``D^-1 H_uu``
     times ``D^-1``, the section 8.1 confirmed class), the crossing
     prediction it induces under the exact mirror of the pinned crossing
     rule, confusion matrices on the non-pivot and full populations, per
     seed family and per world (the leave-one-world-out analogue), the
     named naive baselines, and the solve-equivalence diagnostic (Spearman
     rank correlation of the estimate against the true signed error;
     ceiling 0.99 per section 8.1).
  3. Branch-asymmetry adjudication inputs (plan section 4.3): per-branch
     crossing counts against each branch cochain's distance to the
     unconditioned T5 field, and whether branch 0 is the nearest branch.
  4. Decode-decisiveness report (plan section 4.4): every sealed certifying
     interior witness classified DECODE_DECISIVE_BOTH / ONE /
     DISTINGUISHABLE_ONLY at the frozen 0.1 threshold.

This is a human-gated read-only analysis.  Per the house no-smoke-run rule
the authors do NOT run it against the sealed blocks as part of
implementation; ``--selftest`` exercises every numeric core function on
synthetic fixtures only, and running the sealed analysis is a human
decision.  Phase A makes no claims: every number this script emits is
already determined by sealed data (plan section 4).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from relweblearner.bench import graphlog_g6_executor as g6x  # noqa: E402
from relweblearner.bench.graphlog_certified.linearization import (  # noqa: E402
    encode_extension,
)
from relweblearner.bench.graphlog_certified.spec import DEFAULT_SPEC  # noqa: E402
from relweblearner.bench.graphlog_g6 import G6Phase  # noqa: E402
from relweblearner.bench.graphlog_g7 import (  # noqa: E402
    G7_MANIFEST,
    load_study_manifest as load_g7_study,
)
from relweblearner.bench.graphlog_g8 import (  # noqa: E402
    G8_MANIFEST,
    load_study_manifest as load_g8_study,
)
from relweblearner.bench.graphlog_g7_conditional import (  # noqa: E402
    LOCAL_BOUND_ABSOLUTE_SLACK,
    LOCAL_BOUND_RELATIVE_SLACK,
    conditional_separation,
    conditioned_branch,
    discover_conditions,
)
from relweblearner.bench.graphlog_g8_conditional import (  # noqa: E402
    anti_propagation,
    interior_decisiveness,
)
from relweblearner.certification.types import (  # noqa: E402
    canonical_bytes,
    canonical_digest,
)


RECORD_TYPE = "g9-phase-a-analysis/v1"
DECODE_THRESHOLD = 0.1          # frozen G7 hedge threshold (plan section 6)
JACOBI_DEGREE = 3               # section 8.1 confirmed budget: k = 3
DIAGNOSTIC_CEILING = 0.99       # section 8.1 confirmed ceiling
TOP_ATTRIBUTION_SITES = 3

FAMILIES = (
    {
        "family": "g7-seed",
        "block": ROOT / "results/graphlog-certified/g7",
        "worlds": ("rule_2", "rule_3", "rule_7"),
        "overlay_block": ROOT / "results/graphlog-certified/g8-verification",
    },
    {
        "family": "g8-seed",
        "block": ROOT / "results/graphlog-certified/g8",
        "worlds": ("rule_2", "rule_5", "rule_6", "rule_8", "rule_9", "rule_12"),
        "overlay_block": ROOT / "results/graphlog-certified/g8",
    },
)


# ---------------------------------------------------------------------------
# Numeric core (pure functions; exercised by --selftest on synthetic data)
# ---------------------------------------------------------------------------

def signed_error_and_attribution(
    laplacian_uu: np.ndarray,
    forcing: np.ndarray,
    y_u: np.ndarray,
    interior_position: int,
) -> tuple[float, np.ndarray]:
    """Exact signed true error at one interior position, with attribution.

    The branch cochain restricted to the interior, ``y_u``, has residual
    ``r = H_uu y_u + forcing``; the true Dirichlet solution ``y*`` satisfies
    ``H_uu y* = -forcing``, so the signed error of the true field against
    the cochain is ``(y* - y_u)_c = -row_c(H_uu^-1) . r``.  Returns the
    signed error and the per-site contribution vector ``-G_cj r_j`` (which
    sums to it exactly, in exact arithmetic).
    """
    residual = laplacian_uu @ y_u + forcing
    unit = np.zeros(laplacian_uu.shape[0])
    unit[interior_position] = 1.0
    green_row = np.linalg.solve(laplacian_uu, unit)
    contributions = -(green_row * residual)
    return float(contributions.sum()), contributions


def jacobi_estimate(
    laplacian_uu: np.ndarray,
    residual: np.ndarray,
    degree: int = JACOBI_DEGREE,
) -> np.ndarray:
    """Budgeted polynomial estimate of the signed error vector.

    Jacobi iteration for ``H e = -r`` from zero: ``x_{n+1} = x_n -
    D^-1 (H x_n + r)``.  After ``degree + 1`` steps, ``x`` equals
    ``-sum_{i=0..degree} (I - D^-1 H)^i D^-1 r`` — a polynomial of degree
    exactly ``degree`` in ``D^-1 H`` times ``D^-1``, inside the section 8.1
    class ``q(D^-1 H_uu) D^-1`` with ``deg q <= 3``.  No linear solve
    against ``H_uu`` occurs.
    """
    diagonal = np.diag(laplacian_uu).copy()
    if np.any(diagonal == 0.0):
        raise ValueError("Jacobi estimate requires a nonzero diagonal")
    x = np.zeros_like(residual)
    for _ in range(degree + 1):
        x = x - (laplacian_uu @ x + residual) / diagonal
    return x


def nearest_opposing(
    own_value: float, opposing_values: tuple[float, ...], field_value: float,
) -> float | None:
    """Mirror of the pinned rule's opposing-value selection."""
    opposing = sorted({v for v in opposing_values if v != own_value})
    if not opposing:
        return None
    return min(opposing, key=lambda value: abs(field_value - value))


def crossed_under_rule(
    field_value: float, own_value: float, opposing_values: tuple[float, ...],
) -> bool | None:
    """Exact mirror of the pinned ``anti_propagation`` crossing rule."""
    nearest = nearest_opposing(own_value, opposing_values, field_value)
    if nearest is None:
        return None
    return abs(field_value - nearest) < abs(field_value - own_value)


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation with average ranks for ties."""

    def average_ranks(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="mergesort")
        ranks = np.empty(len(values), dtype=float)
        i = 0
        while i < len(values):
            j = i
            while j + 1 < len(values) \
                    and values[order[j + 1]] == values[order[i]]:
                j += 1
            ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
            i = j + 1
        return ranks

    ra, rb = average_ranks(np.asarray(a, float)), average_ranks(
        np.asarray(b, float))
    ra -= ra.mean()
    rb -= rb.mean()
    denominator = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    if denominator == 0.0:
        return 0.0
    return float((ra * rb).sum() / denominator)


def balanced_accuracy(
    predictions: list[bool], truths: list[bool],
) -> float | None:
    """Mean of true-positive and true-negative rates; None if one-class."""
    pairs = list(zip(predictions, truths, strict=True))
    positives = [p for p, t in pairs if t]
    negatives = [p for p, t in pairs if not t]
    if not positives or not negatives:
        return None
    tpr = sum(1 for p in positives if p) / len(positives)
    tnr = sum(1 for p in negatives if not p) / len(negatives)
    return 0.5 * (tpr + tnr)


def decode_class(
    left_error: float, right_error: float, threshold: float = DECODE_THRESHOLD,
) -> str:
    left_ok = left_error <= threshold
    right_ok = right_error <= threshold
    if left_ok and right_ok:
        return "DECODE_DECISIVE_BOTH"
    if left_ok or right_ok:
        return "DECODE_DECISIVE_ONE"
    return "DISTINGUISHABLE_ONLY"


def attribution_within_tolerance(
    delta: float, solver_error_bound: float,
) -> bool:
    """Plan section 4.1 enforcement: the attribution must reproduce the
    sealed field to the certified solver bound (dressed with the frozen
    slack constants).  The caller aborts on failure."""
    ceiling = (
        solver_error_bound * (1.0 + LOCAL_BOUND_RELATIVE_SLACK)
        + LOCAL_BOUND_ABSOLUTE_SLACK
    )
    return delta <= ceiling


def system_spectra(laplacian_uu: np.ndarray) -> dict[str, float]:
    """Raw and Jacobi-preconditioned spectra (section 8.1 measurement
    obligation): lambda_min/lambda_max/kappa of ``H_uu``, the same for
    ``D^-1/2 H_uu D^-1/2``, and the spectral radius of ``I - D^-1 H_uu``
    (whether the degree-3 Jacobi iterate smooths or diverges)."""
    H = np.asarray(laplacian_uu, dtype=float)
    raw = np.linalg.eigvalsh(H)
    d_isqrt = np.diag(1.0 / np.sqrt(np.diag(H)))
    preconditioned = np.linalg.eigvalsh(d_isqrt @ H @ d_isqrt)
    return {
        "lambda_min": float(raw[0]),
        "lambda_max": float(raw[-1]),
        "condition_number": float(raw[-1] / raw[0]),
        "preconditioned_lambda_min": float(preconditioned[0]),
        "preconditioned_lambda_max": float(preconditioned[-1]),
        "preconditioned_condition_number":
            float(preconditioned[-1] / preconditioned[0]),
        "jacobi_iteration_spectral_radius":
            float(np.max(np.abs(1.0 - preconditioned))),
    }


def confusion(
    predictions: list[bool], truths: list[bool],
) -> dict[str, int]:
    pairs = list(zip(predictions, truths, strict=True))
    return {
        "true_positive": sum(1 for p, t in pairs if p and t),
        "false_positive": sum(1 for p, t in pairs if p and not t),
        "true_negative": sum(1 for p, t in pairs if not p and not t),
        "false_negative": sum(1 for p, t in pairs if not p and t),
    }


# ---------------------------------------------------------------------------
# Sealed-block analysis (read-only; digest-gated)
# ---------------------------------------------------------------------------

def reconstruct(draw, block: Path):
    """Reconstruct the conditional layer from sealed T5 state (pinned code)."""
    unit = block / f"{draw.ordinal:02d}-{draw.world}"
    (
        _observations, _scope, extensions, _compiled, linearization,
        system, t5_run,
    ) = g6x._load_state(unit / "T5" / "opaque-state.pkl", G6Phase.T5, draw)
    cochains = tuple(
        encode_extension(extension, linearization).reshape(-1)
        for extension in extensions.solutions
    )
    coordinate_ids = tuple(linearization.core.coordinate_ids)
    discovery = discover_conditions(cochains, coordinate_ids)
    branches = tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=coordinate_ids,
            field_tolerance=float(DEFAULT_SPEC.field_tolerance),
        )
        for index, cochain in enumerate(cochains)
    )
    unconditioned = np.asarray(t5_run.field.values, dtype=float).reshape(-1)
    return unit, discovery, branches, cochains, coordinate_ids, unconditioned


def verify_faithfulness(
    unit: Path, overlay_unit: Path, discovery, branches, cochains,
    coordinate_ids,
) -> dict:
    """Digest-gate: reconstruction must equal the sealed certificates.

    Always compares the reconstructed G7 conditional-separation certificate
    against the sealed one; where the overlay block carries a
    g8-t6-interior-decisiveness artifact, also compares the reconstructed
    interior-decisiveness certificate against it.  Any divergence aborts
    before a single analysis number is reported.
    """
    sealed_g7 = json.loads(
        (unit / "T6" / "conditional-separation.json").read_text(
            encoding="utf-8")
    )["payload"]["certificate"]
    live_g7 = conditional_separation(
        discovery=discovery, branches=branches, cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    if canonical_digest(live_g7) != canonical_digest(sealed_g7):
        raise AssertionError(
            f"{unit}: reconstruction does not reproduce the sealed G7 "
            "conditional-separation certificate; refusing to analyze"
        )
    overlay_path = overlay_unit / "T6" / "g8-t6-interior-decisiveness.json"
    sealed_overlay = json.loads(overlay_path.read_text(encoding="utf-8"))[
        "payload"]["certificate"]
    live_overlay = interior_decisiveness(
        discovery=discovery, branches=branches, cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    if canonical_digest(live_overlay) != canonical_digest(sealed_overlay):
        raise AssertionError(
            f"{overlay_path}: reconstruction does not reproduce the sealed "
            "interior-decisiveness certificate; refusing to analyze"
        )
    return live_overlay


def analyze_world(family: dict, draw) -> dict:
    unit, discovery, branches, cochains, coordinate_ids, unconditioned = \
        reconstruct(draw, family["block"])
    overlay_unit = family["overlay_block"] / f"{draw.ordinal:02d}-{draw.world}"
    certificate = verify_faithfulness(
        unit, overlay_unit, discovery, branches, cochains, coordinate_ids,
    )

    vectors = [np.asarray(c, dtype=float).reshape(-1) for c in cochains]
    pinned = set(discovery.pivot_indices)
    anti = anti_propagation(
        branches=branches, cochains=cochains,
        disputed_indices=discovery.disputed_indices,
        coordinate_ids=coordinate_ids,
    )

    records = []
    for sealed in anti["records"]:
        branch_index = sealed["branch_index"]
        coordinate_id = sealed["coordinate_id"]
        index = coordinate_ids.index(coordinate_id)
        branch = branches[branch_index]
        system = branch.system
        own = float(sealed["own_value"])
        field_value = float(sealed["field_value"])
        is_pivot = index in pinned
        record = {
            "family": family["family"],
            "world": draw.world,
            "branch_index": branch_index,
            "coordinate_id": coordinate_id,
            "own_value": own,
            "opposing_value": sealed["opposing_value"],
            "field_value": field_value,
            "crossed_to_opposing": bool(sealed["crossed_to_opposing"]),
            "is_pivot": is_pivot,
            "signed_true_error": None,
            "attribution_faithfulness_delta": None,
            "toward_opposing_mass": None,
            "toward_own_mass": None,
            "top_sites": None,
            "jacobi_signed_estimate": None,
            "predicted_field": None,
            "predicted_crossed": None,
        }
        record["crossing_depth"] = abs(field_value - own)
        if not is_pivot:
            interior = np.asarray(system.interior_indices, dtype=int)
            position = {int(v): i for i, v in enumerate(interior)}
            y_u = vectors[branch_index][interior]
            signed_error, contributions = signed_error_and_attribution(
                np.asarray(system.laplacian_uu, dtype=float),
                np.asarray(system.forcing, dtype=float),
                y_u, position[index],
            )
            # Faithfulness: the sealed field must equal own + signed error
            # to within the certified solver bound (plan section 4.1) —
            # enforced, not merely recorded.
            delta = abs(field_value - (own + signed_error))
            solver = branch.run.certificate.solver
            solver_bound = float(solver.error_bound) \
                if solver.error_bound is not None else 0.0
            if not attribution_within_tolerance(delta, solver_bound):
                raise AssertionError(
                    f"{draw.world} branch {branch_index} {coordinate_id}: "
                    f"attribution delta {delta} exceeds the certified "
                    f"solver bound {solver_bound}; refusing to report"
                )
            direction = np.sign(float(sealed["opposing_value"]) - own)
            toward_opposing = float(
                np.maximum(contributions * direction, 0.0).sum())
            toward_own = float(
                np.maximum(-contributions * direction, 0.0).sum())
            order = np.argsort(-np.abs(contributions))[:TOP_ATTRIBUTION_SITES]
            top_sites = [
                {
                    "site_coordinate_id": coordinate_ids[int(interior[i])],
                    "contribution": float(contributions[i]),
                }
                for i in order
            ]
            residual = (
                np.asarray(system.laplacian_uu, dtype=float) @ y_u
                + np.asarray(system.forcing, dtype=float)
            )
            estimate = jacobi_estimate(
                np.asarray(system.laplacian_uu, dtype=float), residual,
            )[position[index]]
            predicted_field = own + float(estimate)
            all_values = tuple(float(v[index]) for v in vectors)
            opposing_values = tuple(
                value for value in all_values if value != own
            )
            record.update({
                "signed_true_error": signed_error,
                "attribution_faithfulness_delta": delta,
                "toward_opposing_mass": toward_opposing,
                "toward_own_mass": toward_own,
                "top_sites": top_sites,
                "jacobi_signed_estimate": float(estimate),
                "predicted_field": predicted_field,
                "predicted_crossed": crossed_under_rule(
                    predicted_field, own, opposing_values,
                ),
            })
        records.append(record)

    # Branch asymmetry inputs (plan section 4.3).
    disputed = np.asarray(discovery.disputed_indices, dtype=int)
    per_branch = []
    distances = []
    for branch_index, vector in enumerate(vectors):
        crossing_count = sum(
            1 for r in records
            if r["branch_index"] == branch_index and r["crossed_to_opposing"]
        )
        l2_disputed = float(
            np.linalg.norm(vector[disputed] - unconditioned[disputed]))
        linf_disputed = float(
            np.max(np.abs(vector[disputed] - unconditioned[disputed])))
        distances.append(l2_disputed)
        per_branch.append({
            "branch_index": branch_index,
            "crossing_count": crossing_count,
            "l2_distance_to_unconditioned_on_disputed": l2_disputed,
            "linf_distance_to_unconditioned_on_disputed": linf_disputed,
        })
    branch_asymmetry = {
        "per_branch": per_branch,
        "branch_0_is_nearest_to_unconditioned":
            bool(int(np.argmin(distances)) == 0),
    }

    # Decode-decisiveness at the sealed certifying interior witnesses
    # (plan section 4.4; frozen threshold 0.1).
    decode_report = []
    for pair in certificate["compared_pairs"]:
        if pair.get("witness_kind") != "interior":
            continue
        index = coordinate_ids.index(pair["witness_coordinate_id"])
        left, right = pair["left_branch"], pair["right_branch"]
        left_error = abs(
            float(branches[left].run.field.values[index])
            - float(vectors[left][index]))
        right_error = abs(
            float(branches[right].run.field.values[index])
            - float(vectors[right][index]))
        decode_report.append({
            "pair": [left, right],
            "witness_coordinate_id": pair["witness_coordinate_id"],
            "left_decode_error": left_error,
            "right_decode_error": right_error,
            "classification": decode_class(left_error, right_error),
        })

    # Section 8.1 measurement obligation: raw and preconditioned spectra
    # per conditioned branch system.
    spectra = [
        {
            "branch_index": branch_index,
            **system_spectra(
                np.asarray(branch.system.laplacian_uu, dtype=float)),
        }
        for branch_index, branch in enumerate(branches)
        if branch.run.field is not None
    ]

    return {
        "world": draw.world,
        "faithfulness": "full-certificate digests matched (G7 layer and "
                        "interior-decisiveness overlay); attribution "
                        "reproduced the sealed field within the certified "
                        "solver bound at every non-pivot record",
        "records": records,
        "branch_system_spectra": spectra,
        "branch_asymmetry": branch_asymmetry,
        "decode_decisiveness": decode_report,
    }


def predictor_metrics(records: list[dict]) -> dict:
    """Confusion matrices, baselines, and the solve-equivalence diagnostic."""
    non_pivot = [r for r in records if not r["is_pivot"]]
    truths_np = [r["crossed_to_opposing"] for r in non_pivot]
    preds_np = [bool(r["predicted_crossed"]) for r in non_pivot]
    truths_all = [r["crossed_to_opposing"] for r in records]

    baselines = {
        "majority_not_crossed": balanced_accuracy(
            [False] * len(non_pivot), truths_np),
        "crossed_iff_branch_nonzero": balanced_accuracy(
            [r["branch_index"] != 0 for r in non_pivot], truths_np),
        "crossed_iff_non_pivot_full_population": balanced_accuracy(
            [not r["is_pivot"] for r in records], truths_all),
    }

    estimates = np.asarray(
        [r["jacobi_signed_estimate"] for r in non_pivot], dtype=float)
    errors = np.asarray(
        [r["signed_true_error"] for r in non_pivot], dtype=float)
    diagnostic = spearman(estimates, errors)

    per_world = {}
    for world in sorted({r["world"] for r in non_pivot}):
        rows = [r for r in non_pivot if r["world"] == world]
        per_world[world] = balanced_accuracy(
            [bool(r["predicted_crossed"]) for r in rows],
            [r["crossed_to_opposing"] for r in rows],
        )

    # Plan section 4.2: per-branch predictor performance.
    per_branch = {}
    for branch_index in sorted({r["branch_index"] for r in non_pivot}):
        rows = [r for r in non_pivot if r["branch_index"] == branch_index]
        per_branch[str(branch_index)] = balanced_accuracy(
            [bool(r["predicted_crossed"]) for r in rows],
            [r["crossed_to_opposing"] for r in rows],
        )

    # Plan section 4.2: performance as a function of crossing depth (a
    # continuous covariate, not modes) — the full per-crossing table, plus
    # the predicted-vs-observed depth rank correlation on crossings (the
    # section 5.5 licensing number).
    crossings = sorted(
        (r for r in non_pivot if r["crossed_to_opposing"]),
        key=lambda r: r["crossing_depth"],
    )
    depth_table = [
        {
            "world": r["world"],
            "branch_index": r["branch_index"],
            "coordinate_id": r["coordinate_id"],
            "observed_depth": r["crossing_depth"],
            "predicted_depth": abs(r["predicted_field"] - r["own_value"]),
            "predicted_crossed": bool(r["predicted_crossed"]),
        }
        for r in crossings
    ]
    depth_correlation = spearman(
        np.asarray([row["predicted_depth"] for row in depth_table]),
        np.asarray([row["observed_depth"] for row in depth_table]),
    ) if len(depth_table) >= 3 else None

    return {
        "population_non_pivot": {
            "count": len(non_pivot),
            "positives": sum(truths_np),
            "confusion": confusion(preds_np, truths_np),
            "balanced_accuracy": balanced_accuracy(preds_np, truths_np),
        },
        "population_full": {
            "count": len(records),
            "positives": sum(truths_all),
            "note": "pivot records carry no budgeted estimate; the "
                    "predictor is evaluated on the non-pivot population "
                    "(plan claim 4); full population reported for "
                    "disclosure only",
        },
        "per_world_balanced_accuracy": per_world,
        "per_branch_balanced_accuracy": per_branch,
        "performance_by_crossing_depth": depth_table,
        "predicted_vs_observed_depth_spearman_on_crossings":
            depth_correlation,
        "naive_baselines": baselines,
        "solve_equivalence_diagnostic": {
            "spearman_estimate_vs_true_signed_error": diagnostic,
            "ceiling": DIAGNOSTIC_CEILING,
            "rejected_as_solve_in_disguise":
                bool(diagnostic > DIAGNOSTIC_CEILING),
        },
    }


def run_sealed_analysis() -> dict:
    g7_study = load_g7_study(ROOT / G7_MANIFEST)
    g8_study = load_g8_study(ROOT / G8_MANIFEST)
    draws = {
        "g7-seed": {d.world: d for d in g7_study.draws},
        "g8-seed": {d.world: d for d in g8_study.draws},
    }
    worlds_out = []
    all_records = []
    for family in FAMILIES:
        for world in family["worlds"]:
            result = analyze_world(family, draws[family["family"]][world])
            worlds_out.append({"family": family["family"], **result})
            all_records.extend(result["records"])

    families_metrics = {
        name: predictor_metrics(
            [r for r in all_records if r["family"] == name])
        for name in ("g7-seed", "g8-seed")
    }
    return {
        "record_type": RECORD_TYPE,
        "plan": "docs/g9-anti-propagation-plan.md sections 4.1-4.4",
        "discipline": "Phase A makes no claims; every number here is "
                      "determined by sealed data; hypothesis selection on "
                      "this output must be disclosed in the Phase A report",
        "decode_threshold": DECODE_THRESHOLD,
        "jacobi_degree": JACOBI_DEGREE,
        "source_manifests": {
            "g7": g7_study.manifest_id,
            "g8_part2": g8_study.manifest_id,
        },
        "worlds": worlds_out,
        "predictor_metrics_pooled": predictor_metrics(all_records),
        "predictor_metrics_per_family": families_metrics,
    }


# ---------------------------------------------------------------------------
# Synthetic self-test (never touches sealed data)
# ---------------------------------------------------------------------------

def selftest() -> int:
    rng_free_failures = []

    def check(name: str, condition: bool) -> None:
        print(f"  {'PASS' if condition else 'FAIL'}: {name}")
        if not condition:
            rng_free_failures.append(name)

    # Fixed small SPD system: 1-D path Laplacian + identity (n = 6).
    n = 6
    laplacian = 2.0 * np.eye(n) + np.eye(n)
    laplacian[np.arange(n - 1), np.arange(1, n)] = -1.0
    laplacian[np.arange(1, n), np.arange(n - 1)] = -1.0
    forcing = np.array([0.3, -0.1, 0.7, 0.0, -0.4, 0.2])
    y_u = np.array([1.0, 0.0, 1.0, 1.0, 0.0, 0.0])

    # (a) attribution sums exactly to the signed error, every position.
    truth = np.linalg.solve(laplacian, -forcing)
    ok = True
    for position in range(n):
        signed_error, contributions = signed_error_and_attribution(
            laplacian, forcing, y_u, position)
        ok &= abs(contributions.sum() - signed_error) < 1e-12
        ok &= abs((y_u[position] + signed_error) - truth[position]) < 1e-10
    check("attribution sums to the signed error and reproduces the true "
          "field", ok)

    # (b) the Jacobi estimate equals the explicit degree-3 polynomial.
    residual = laplacian @ y_u + forcing
    diagonal_inverse = np.diag(1.0 / np.diag(laplacian))
    m = np.eye(n) - diagonal_inverse @ laplacian
    explicit = -(
        np.eye(n) + m + m @ m + m @ m @ m
    ) @ diagonal_inverse @ residual
    check("Jacobi iterate equals the explicit degree-3 polynomial in "
          "D^-1 H times D^-1",
          bool(np.allclose(jacobi_estimate(laplacian, residual, 3),
                           explicit, atol=1e-12)))

    # (c) the crossing mirror agrees with the pinned rule's arithmetic.
    cases = [
        (0.9, 0.0, (1.0,), True),      # deep crossing
        (0.49, 0.0, (1.0,), False),    # sub-midpoint hedge
        (0.51, 0.0, (1.0,), True),     # shallow crossing
        (-0.6, 0.0, (1.0,), False),    # away-side excursion: NOT a crossing
        (0.2, 1.0, (0.0,), True),      # crossing from own=1 toward 0
        (0.5, 0.0, (1.0,), False),     # exact midpoint: strict rule says no
        (0.7, 0.0, (), None),          # no opposing values
    ]
    check("crossing mirror matches the pinned strict-midpoint rule on all "
          "fixed cases",
          all(crossed_under_rule(f, o, opp) is expected
              for f, o, opp, expected in cases))

    # (d) Spearman: exact on monotone, sign-flipped, and tied data.
    a = np.array([1.0, 2.0, 3.0, 4.0])
    check("spearman monotone == 1", abs(spearman(a, a ** 3) - 1.0) < 1e-12)
    check("spearman reversed == -1", abs(spearman(a, -a) + 1.0) < 1e-12)
    check("spearman ties handled",
          abs(spearman(np.array([1.0, 1.0, 2.0]),
                       np.array([3.0, 3.0, 5.0])) - 1.0) < 1e-12)

    # (e) balanced accuracy and confusion bookkeeping.
    preds = [True, False, True, False]
    truths = [True, True, False, False]
    check("balanced accuracy 0.5 on the mixed toy case",
          balanced_accuracy(preds, truths) == 0.5)
    check("balanced accuracy is None on one-class truth",
          balanced_accuracy([True], [True]) is None)
    c = confusion(preds, truths)
    check("confusion counts sum to n", sum(c.values()) == 4
          and c["true_positive"] == 1 and c["false_positive"] == 1)

    # (f) decode classification at the frozen threshold.
    check("decode classes",
          decode_class(0.05, 0.02) == "DECODE_DECISIVE_BOTH"
          and decode_class(0.0634, 0.8995) == "DECODE_DECISIVE_ONE"
          and decode_class(0.4, 0.3) == "DISTINGUISHABLE_ONLY")

    # (g) end-to-end synthetic sanity: a cochain far from harmonic at one
    # site produces a signed error the attribution and estimate both see.
    signed_error, _ = signed_error_and_attribution(laplacian, forcing, y_u, 2)
    estimate = jacobi_estimate(laplacian, residual)[2]
    check("estimate and true signed error share a sign on the synthetic "
          "system",
          bool(np.sign(estimate) == np.sign(signed_error)))

    # (h) attribution-tolerance enforcement: passes at the bound, fails
    # beyond it (dressed with the frozen slack constants).
    bound = 1e-6
    ceiling = bound * (1.0 + LOCAL_BOUND_RELATIVE_SLACK) \
        + LOCAL_BOUND_ABSOLUTE_SLACK
    check("attribution tolerance enforcement accepts <= ceiling and "
          "rejects beyond",
          attribution_within_tolerance(ceiling, bound)
          and not attribution_within_tolerance(ceiling * 1.01, bound))

    # (i) spectra: SPD input gives positive lambda_min, kappa >= 1, and a
    # smoothing Jacobi radius (< 1) on this diagonally dominant system.
    spectra = system_spectra(laplacian)
    check("spectra sane on the synthetic SPD system",
          spectra["lambda_min"] > 0.0
          and spectra["condition_number"] >= 1.0
          and spectra["preconditioned_condition_number"] >= 1.0
          and 0.0 < spectra["jacobi_iteration_spectral_radius"] < 1.0)

    print(f"\nselftest: {'ALL PASS' if not rng_free_failures else 'FAILURES'}")
    return 1 if rng_free_failures else 0


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selftest", action="store_true",
        help="run the synthetic numeric-core self-test only (never touches "
             "sealed data)")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    report = run_sealed_analysis()
    sys.stdout.buffer.write(canonical_bytes(report) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
