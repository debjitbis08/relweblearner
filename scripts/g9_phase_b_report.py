#!/usr/bin/env python3
"""G9 Phase B pre-committed report: the mandatory first read of the block.

Implements the preregistered analysis of ``docs/g9-anti-propagation-plan.md``
sections 5-6 with the constants fixed by the sealed Phase A report (section
6).  This script is committed and pushed BEFORE the Phase B seed pulse
exists; after the sealed block promotes, running it is the first read (the
G8 section 7.2 discipline).  Modes:

- ``--mode verification`` (runs before the fresh block exists): the plan
  section 8.3 verification realization.  Reads the ALREADY-SEALED G8 Part II
  block — outcomes precomputed by Phase A and disclosed as such — and
  verifies (a) the instrument claims 1-3 hold on it, and (b) the pinned
  predictor module reproduces Phase A round 2's per-record estimates and
  predictions bit-for-bit (the replication anchor; zero discovery content by
  declaration).  Requires ``--phase-a-output`` (the round-2 JSON) whose
  sha256 must match the value pinned in the G9 manifest when one exists, and
  is printed either way.
- ``--mode measurement`` (the default): reads the sealed G9 block and
  evaluates the preregistered claims:

    1. *Crossing-set reproducibility*: every sealed anti-propagation record
       agrees with the recomputation from ``(H, boundary, cochain)``; records
       inside the guard band are compared as ``AMBIGUOUS_CROSSING``.
    2. *Margin-error identity*: tight bounds recomputed at every interior
       differing witness of every pair; the recorded best-witness tuple
       (including the ``best_interior_witness`` cross-check on
       ``pinned_fallback`` pairs) must equal the recomputed selection and
       satisfy ``|margin - (gamma - tight_raw_L - tight_raw_R)| <=
       rel*(raw_L+raw_R) + solver_L + solver_R + 2*abs`` — the derived
       slack dressing, not a padded budget.  ``BRANCH_SOLVE_FAILED`` pairs
       are reported outcomes; ``BOUND_SOUNDNESS_VIOLATED`` pairs are
       release-blocking G8-instrument defects.
    3. *Crossing guard band*: every record counted as crossed has midpoint
       distance above the disclosed ceiling; band records are reported
       ``AMBIGUOUS_CROSSING`` (a reported outcome, not a defect) and leave
       claim 4's ground truth and the non-vacuity count.
    4. *Predictor accuracy floor*: the frozen Chebyshev predictor (pinned
       module) against the unambiguous non-pivot ground truth, passed iff
       the mean of the TPR/TNR Jeffreys 0.20-quantile lower bounds reaches
       the floor 0.776.  Claim 5 was dropped by the sealed Phase A report;
       depth calibration appears only in the secondary report.

  Non-vacuity: fewer than 5 unambiguous crossing records or fewer than 2
  conditioned worlds means the block is empirically uninformative for the
  mechanism claim and no claim of any strength is made.

The report also surfaces, per world, the sealed certificate's G8
instrument state (``bound_soundness_violation_count``, unsound-witness
lists, ``BOUND_SOUNDNESS_VIOLATED`` pairs): any of these nonzero is a
release-blocking implementation defect per plan section 5, flagged
explicitly.  Everything else is the measured-outcomes secondary report
(per-record table, decode-decisiveness vocabulary at certifying interior
witnesses at the frozen threshold, fresh-draw branch-system spectra,
per-world and per-branch balanced accuracies, all three naive baselines
on their pinned populations, the fresh-draw solve-equivalence Spearman —
reported, not gated — the depth table, and the distance-to-unconditioned
covariate).  Faithfulness gates mirror Phase A: full canonical-digest
comparison of the reconstructed G7 conditional-separation and G8-layer
interior-decisiveness certificates, plus per-record enforcement that the
attribution reproduces the sealed field within the certified solver bound.
Any gate failure aborts before a single claim is evaluated.

Validated on synthetic fixtures only before sealing (``--selftest``); the
authors never run the sealed modes as part of implementation.
"""

from __future__ import annotations

import argparse
import hashlib
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
    tight_localized_error_bounds,
)
from relweblearner.bench.graphlog_g9_conditional import (  # noqa: E402
    G9_CLAIM4_FLOOR,
    G9_DECODE_THRESHOLD,
    G9_NONVACUITY_MIN_CROSSINGS,
    G9_NONVACUITY_MIN_WORLDS,
    chebyshev_error_estimate,
    claim_4_verdict,
    crossed_under_pinned_rule,
    crossing_status,
    guard_band_ceiling,
    midpoint_distance,
)
from relweblearner.certification.types import (  # noqa: E402
    canonical_bytes,
    canonical_digest,
)


RECORD_TYPE = "g9-phase-b-preregistered-report/v1"
# Mirrors graphlog_g8_executor._CONDITIONED_STATUSES: a conditioned world
# that fails to separate is a live fresh-draw outcome and must not be
# silently excluded from any claim population.
CONDITIONED_STATUSES = ("SEPARATING_CONDITIONAL", "CONDITIONED_NOT_SEPARATING")


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    def ranks(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="mergesort")
        out = np.empty(len(values), dtype=float)
        i = 0
        while i < len(values):
            j = i
            while j + 1 < len(values) \
                    and values[order[j + 1]] == values[order[i]]:
                j += 1
            out[order[i:j + 1]] = 0.5 * (i + j) + 1.0
            i = j + 1
        return out

    ra, rb = ranks(np.asarray(a, float)), ranks(np.asarray(b, float))
    ra -= ra.mean()
    rb -= rb.mean()
    denominator = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    return 0.0 if denominator == 0.0 else float((ra * rb).sum() / denominator)


def _ceiling() -> float:
    return guard_band_ceiling(
        float(DEFAULT_SPEC.field_tolerance),
        LOCAL_BOUND_RELATIVE_SLACK,
        LOCAL_BOUND_ABSOLUTE_SLACK,
    )


def _reconstruct(draw, block: Path):
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


def _digest_gates(unit, discovery, branches, cochains, coordinate_ids):
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
            f"{unit}: sealed G7-layer certificate not reproduced; aborting"
        )
    overlay_path = unit / "T6" / "g8-t6-interior-decisiveness.json"
    sealed_overlay = json.loads(overlay_path.read_text(encoding="utf-8"))[
        "payload"]["certificate"]
    live_overlay = interior_decisiveness(
        discovery=discovery, branches=branches, cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    if canonical_digest(live_overlay) != canonical_digest(sealed_overlay):
        raise AssertionError(
            f"{overlay_path}: sealed interior-decisiveness certificate not "
            "reproduced; aborting"
        )
    return live_overlay


def _conditioned_worlds(study, block: Path) -> list:
    draws = []
    for draw in study.draws:
        unit = block / f"{draw.ordinal:02d}-{draw.world}"
        record = json.loads(
            (unit / "T6" / "conditional-separation.json").read_text(
                encoding="utf-8")
        )["payload"]
        if record.get("status") in CONDITIONED_STATUSES:
            draws.append(draw)
    return draws


def analyze_world(draw, block: Path) -> dict:
    unit, discovery, branches, cochains, coordinate_ids, unconditioned = \
        _reconstruct(draw, block)
    certificate = _digest_gates(
        unit, discovery, branches, cochains, coordinate_ids)
    vectors = [np.asarray(c, dtype=float).reshape(-1) for c in cochains]
    pinned = set(discovery.pivot_indices)
    ceiling = _ceiling()
    anti = anti_propagation(
        branches=branches, cochains=cochains,
        disputed_indices=discovery.disputed_indices,
        coordinate_ids=coordinate_ids,
    )

    records = []
    claim1_disagreements = []
    for sealed in anti["records"]:
        branch_index = sealed["branch_index"]
        coordinate_id = sealed["coordinate_id"]
        index = coordinate_ids.index(coordinate_id)
        branch = branches[branch_index]
        system = branch.system
        own = float(sealed["own_value"])
        field_value = float(sealed["field_value"])
        is_pivot = index in pinned
        all_values = tuple(float(v[index]) for v in vectors)
        opposing_values = tuple(v for v in all_values if v != own)
        status = crossing_status(field_value, own, opposing_values, ceiling)
        # Claim 1: the sealed strict bit must agree with the recomputation
        # wherever the record is unambiguous; band records are compared at
        # the AMBIGUOUS_CROSSING level.
        if status == "CROSSED" and not sealed["crossed_to_opposing"] \
                or status == "NOT_CROSSED" and sealed["crossed_to_opposing"]:
            claim1_disagreements.append(
                {"world": draw.world, "branch_index": branch_index,
                 "coordinate_id": coordinate_id})
        record = {
            "world": draw.world,
            "branch_index": branch_index,
            "coordinate_id": coordinate_id,
            "own_value": own,
            "opposing_value": sealed["opposing_value"],
            "field_value": field_value,
            "crossed_to_opposing": bool(sealed["crossed_to_opposing"]),
            "crossing_status": status,
            "crossing_depth": abs(field_value - own),
            "midpoint_distance": midpoint_distance(
                field_value, own, opposing_values),
            "is_pivot": is_pivot,
            "signed_true_error": None,
            "chebyshev_signed_estimate": None,
            "chebyshev_predicted_field": None,
            "chebyshev_predicted_crossed": None,
        }
        if not is_pivot:
            interior = np.asarray(system.interior_indices, dtype=int)
            position = {int(v): i for i, v in enumerate(interior)}
            H = np.asarray(system.laplacian_uu, dtype=float)
            y_u = vectors[branch_index][interior]
            residual = H @ y_u + np.asarray(system.forcing, dtype=float)
            unit_vec = np.zeros(len(interior))
            unit_vec[position[index]] = 1.0
            green_row = np.linalg.solve(H, unit_vec)
            signed_error = float(-(green_row @ residual))
            solver = branch.run.certificate.solver
            solver_bound = float(solver.error_bound) \
                if solver.error_bound is not None else 0.0
            delta = abs(field_value - (own + signed_error))
            if delta > solver_bound * (1.0 + LOCAL_BOUND_RELATIVE_SLACK) \
                    + LOCAL_BOUND_ABSOLUTE_SLACK:
                raise AssertionError(
                    f"{draw.world} branch {branch_index} {coordinate_id}: "
                    f"ground-truth delta {delta} exceeds the certified "
                    f"solver bound {solver_bound}; aborting"
                )
            estimate = float(
                chebyshev_error_estimate(H, residual)[position[index]])
            predicted_field = own + estimate
            record.update({
                "signed_true_error": signed_error,
                "chebyshev_signed_estimate": estimate,
                "chebyshev_predicted_field": predicted_field,
                "chebyshev_predicted_crossed": crossed_under_pinned_rule(
                    predicted_field, own, opposing_values),
            })
        records.append(record)

    # Claim 2: recompute tight bounds at every interior differing witness
    # of every pair; the recorded best tuple must match the recomputed
    # selection, and the recorded margin must equal
    # ``gamma - tight_raw_L - tight_raw_R`` up to the slack dressing.
    # The dressing budget is derived, not padded: the recorded bound is
    # ``raw * (1 + rel) + solver + abs`` per side, so the margin differs
    # from the raw-contraction margin by exactly
    # ``rel * (raw_L + raw_R) + solver_L + solver_R + 2 * abs``.
    claim2_failures = []
    claim2_reported = []
    claim2_defects = []
    max_identity_deviation = 0.0
    bound_tables = {}

    def bound_table(side: int):
        if side not in bound_tables:
            witnesses = [
                i for i in discovery.disputed_indices if i not in pinned
            ]
            bound_tables[side] = tight_localized_error_bounds(
                branches[side], cochains[side], witnesses)
        return bound_tables[side]

    def recompute_best(left: int, right: int):
        best = None
        for i in discovery.disputed_indices:
            if i in pinned or vectors[left][i] == vectors[right][i]:
                continue
            row_l, row_r = bound_table(left)[i], bound_table(right)[i]
            if not (row_l["observed_within_bound"]
                    and row_r["observed_within_bound"]):
                continue
            gamma = float(abs(vectors[left][i] - vectors[right][i]))
            candidate = (
                gamma - row_l["bound"] - row_r["bound"], gamma, i,
                row_l["bound"], row_r["bound"],
                row_l["tight_raw"], row_r["tight_raw"],
            )
            if best is None or candidate > best:
                best = candidate
        return best

    def identity_check(recorded: dict, best) -> dict | None:
        raw_l = recorded["left_tight_raw"]
        raw_r = recorded["right_tight_raw"]
        index = coordinate_ids.index(recorded["witness_coordinate_id"])
        solver_sum = (
            bound_table_pair[0][index]["solver_error_bound"]
            + bound_table_pair[1][index]["solver_error_bound"]
        )
        budget = (
            LOCAL_BOUND_RELATIVE_SLACK * (raw_l + raw_r)
            + solver_sum + 2.0 * LOCAL_BOUND_ABSOLUTE_SLACK + 1e-12
        )
        deviation = abs(
            recorded["remaining_margin"]
            - (recorded["gamma"] - raw_l - raw_r)
        )
        nonlocal max_identity_deviation
        max_identity_deviation = max(max_identity_deviation, deviation)
        recomputed_ok = (
            best is not None
            and coordinate_ids[best[2]]
            == recorded["witness_coordinate_id"]
            and abs(best[0] - recorded["remaining_margin"]) <= budget
        )
        if deviation > budget or not recomputed_ok:
            return {
                "identity_deviation": deviation,
                "budget": budget,
                "recomputed_selection_matches": bool(recomputed_ok),
            }
        return None

    for pair in certificate["compared_pairs"]:
        left, right = pair["left_branch"], pair["right_branch"]
        kind = pair.get("witness_kind")
        if kind == "BRANCH_SOLVE_FAILED":
            # An anticipated certificate state, reported, never a crash
            # (a first-read script must degrade to reported outcomes).
            claim2_reported.append({
                "world": draw.world, "pair": [left, right],
                "status": "BRANCH_SOLVE_FAILED",
            })
            continue
        if kind == "BOUND_SOUNDNESS_VIOLATED":
            claim2_defects.append({
                "world": draw.world, "pair": [left, right],
                "status": "BOUND_SOUNDNESS_VIOLATED",
            })
            continue
        if kind not in ("interior", "pinned", "pinned_fallback"):
            continue
        bound_table_pair = (bound_table(left), bound_table(right))
        best = recompute_best(left, right)
        if kind == "interior":
            failure = identity_check(pair, best)
            if failure is not None:
                claim2_failures.append({
                    "world": draw.world, "pair": [left, right],
                    "witness": pair["witness_coordinate_id"], **failure,
                })
        elif kind == "pinned_fallback" and "best_interior_witness" in pair:
            failure = identity_check(pair["best_interior_witness"], best)
            if failure is not None:
                claim2_failures.append({
                    "world": draw.world, "pair": [left, right],
                    "witness": pair["best_interior_witness"][
                        "witness_coordinate_id"],
                    "cross_check": "pinned_fallback best_interior_witness",
                    **failure,
                })

    # Decode-decisiveness vocabulary at certifying interior witnesses
    # (report fields, never acceptance criteria).
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
        left_ok = left_error <= G9_DECODE_THRESHOLD
        right_ok = right_error <= G9_DECODE_THRESHOLD
        decode_report.append({
            "pair": [left, right],
            "witness_coordinate_id": pair["witness_coordinate_id"],
            "left_decode_error": left_error,
            "right_decode_error": right_error,
            "classification": (
                "DECODE_DECISIVE_BOTH" if left_ok and right_ok
                else "DECODE_DECISIVE_ONE" if left_ok or right_ok
                else "DISTINGUISHABLE_ONLY"
            ),
        })

    disputed = np.asarray(discovery.disputed_indices, dtype=int)
    per_branch = [
        {
            "branch_index": i,
            "crossing_count": sum(
                1 for r in records
                if r["branch_index"] == i
                and r["crossing_status"] == "CROSSED"
            ),
            "l2_distance_to_unconditioned_on_disputed": float(
                np.linalg.norm(v[disputed] - unconditioned[disputed])),
        }
        for i, v in enumerate(vectors)
    ]

    # Plan §5: a breach of a G8 instrument claim surfacing in a G9 run is
    # an implementation defect and blocks release — surfaced here, never
    # silently inherited from the digest gate.
    unsound_witnesses = [
        {"pair": [p["left_branch"], p["right_branch"]],
         "coordinate_ids": list(p["unsound_witness_coordinate_ids"])}
        for p in certificate["compared_pairs"]
        if p.get("unsound_witness_coordinate_ids")
    ]
    g8_instrument_defects = {
        "bound_soundness_violation_count":
            certificate["bound_soundness_violation_count"],
        "unsound_witnesses": unsound_witnesses,
        "bound_soundness_violated_pairs": claim2_defects,
        "defect": bool(
            certificate["bound_soundness_violation_count"]
            or unsound_witnesses or claim2_defects
        ),
    }

    # Fresh-draw spectra (secondary; branch systems share H_uu within a
    # world, but report per solved branch for the record).
    spectra = []
    for i, branch in enumerate(branches):
        if branch.run.field is None:
            continue
        H = np.asarray(branch.system.laplacian_uu, dtype=float)
        raw = np.linalg.eigvalsh(H)
        d_isqrt = np.diag(1.0 / np.sqrt(np.diag(H)))
        pre = np.linalg.eigvalsh(d_isqrt @ H @ d_isqrt)
        spectra.append({
            "branch_index": i,
            "lambda_min": float(raw[0]),
            "lambda_max": float(raw[-1]),
            "condition_number": float(raw[-1] / raw[0]),
            "preconditioned_condition_number": float(pre[-1] / pre[0]),
            "jacobi_iteration_spectral_radius":
                float(np.max(np.abs(1.0 - pre))),
        })

    return {
        "world": draw.world,
        "records": records,
        "claim1_disagreements": claim1_disagreements,
        "claim2_failures": claim2_failures,
        "claim2_reported": claim2_reported,
        "claim2_max_identity_deviation": max_identity_deviation,
        "g8_instrument_defects": g8_instrument_defects,
        "branch_system_spectra": spectra,
        "decode_decisiveness": decode_report,
        "branch_distances": per_branch,
    }


def evaluate_block(study, block: Path) -> dict:
    conditioned = _conditioned_worlds(study, block)
    worlds = [analyze_world(draw, block) for draw in conditioned]
    records = [r for w in worlds for r in w["records"]]
    unambiguous = [
        r for r in records
        if not r["is_pivot"] and r["crossing_status"] != "AMBIGUOUS_CROSSING"
    ]
    truths = [r["crossing_status"] == "CROSSED" for r in unambiguous]
    predictions = [
        bool(r["chebyshev_predicted_crossed"]) for r in unambiguous
    ]
    pairs = list(zip(predictions, truths, strict=True))
    tp = sum(1 for p, t in pairs if p and t)
    fn = sum(1 for p, t in pairs if not p and t)
    tn = sum(1 for p, t in pairs if not p and not t)
    fp = sum(1 for p, t in pairs if p and not t)

    ambiguous = [
        r for r in records if r["crossing_status"] == "AMBIGUOUS_CROSSING"
    ]
    crossings = sum(truths)
    non_vacuous = (
        crossings >= G9_NONVACUITY_MIN_CROSSINGS
        and len(conditioned) >= G9_NONVACUITY_MIN_WORLDS
    )

    claim1_disagreements = [
        d for w in worlds for d in w["claim1_disagreements"]
    ]
    claim2_failures = [f for w in worlds for f in w["claim2_failures"]]
    banded_crossed_ok = all(
        r["midpoint_distance"] is None
        or r["midpoint_distance"] > _ceiling()
        for r in records if r["crossing_status"] == "CROSSED"
    )

    estimates = np.asarray([
        r["chebyshev_signed_estimate"] for r in records if not r["is_pivot"]
    ], dtype=float)
    errors = np.asarray([
        r["signed_true_error"] for r in records if not r["is_pivot"]
    ], dtype=float)
    crossed_rows = sorted(
        (r for r in unambiguous if r["crossing_status"] == "CROSSED"),
        key=lambda r: r["crossing_depth"],
    )

    claims = {
        "1_crossing_set_reproducibility": {
            "passed": not claim1_disagreements,
            "disagreements": claim1_disagreements,
        },
        "2_margin_error_identity": {
            "passed": not claim2_failures,
            "failures": claim2_failures,
            "reported_outcomes": [
                r for w in worlds for r in w["claim2_reported"]
            ],
            "max_identity_deviation": max(
                (w["claim2_max_identity_deviation"] for w in worlds),
                default=0.0,
            ),
        },
        "3_crossing_guard_band": {
            "passed": bool(banded_crossed_ok),
            "guard_ceiling": _ceiling(),
            "ambiguous_crossing_records": [
                {"world": r["world"], "branch_index": r["branch_index"],
                 "coordinate_id": r["coordinate_id"]}
                for r in ambiguous
            ],
        },
        "4_predictor_accuracy_floor": (
            {
                **claim_4_verdict(tp, fn, tn, fp),
                "note": "evaluated on unambiguous non-pivot records only; "
                        "claim 5 was dropped by the sealed Phase A report",
            }
            if (tp + fn) >= 1 and (tn + fp) >= 1 else {
                "passed": None,
                "note": "claim 4 unevaluable: a truth class is empty on "
                        "the unambiguous non-pivot population",
            }
        ),
    }
    if not non_vacuous:
        claims["4_predictor_accuracy_floor"]["passed"] = None

    secondary = {
        "discipline": "measured outcomes only; none of these numbers was "
                      "predicted and none licenses a claim beyond its own "
                      "value",
        "conditioned_worlds": [w["world"] for w in worlds],
        "unambiguous_crossing_count": crossings,
        "ambiguous_crossing_count": len(ambiguous),
        "confusion": {"tp": tp, "fn": fn, "tn": tn, "fp": fp},
        "balanced_accuracy_point": (
            0.5 * (tp / (tp + fn) + tn / (tn + fp))
            if (tp + fn) and (tn + fp) else None
        ),
        "naive_baselines": {
            "majority_not_crossed": 0.5 if (tp + fn) and (tn + fp) else None,
            "crossed_iff_branch_nonzero": (
                0.5 * (
                    sum(1 for r in unambiguous
                        if r["branch_index"] != 0
                        and r["crossing_status"] == "CROSSED")
                    / max(crossings, 1)
                    + sum(1 for r in unambiguous
                          if r["branch_index"] == 0
                          and r["crossing_status"] != "CROSSED")
                    / max(len(unambiguous) - crossings, 1)
                ) if crossings and len(unambiguous) - crossings else None
            ),
            "crossed_iff_non_pivot_full_population": (
                0.5 * (
                    1.0
                    + sum(1 for r in records if r["is_pivot"])
                    / max(sum(
                        1 for r in records
                        if r["crossing_status"] != "CROSSED"
                    ), 1)
                ) if crossings and any(
                    r["crossing_status"] != "CROSSED" for r in records
                ) else None
            ),
            "note": "the full-population baseline counts "
                    "AMBIGUOUS_CROSSING records among its negatives; the "
                    "other baselines and claim 4 exclude them (report-only "
                    "convention, stated for cross-baseline comparability)",
        },
        "per_world_balanced_accuracy": {
            w["world"]: (
                0.5 * (wtp / (wtp + wfn) + wtn / (wtn + wfp))
                if (wtp + wfn) and (wtn + wfp) else None
            )
            for w in worlds
            for rows in [[
                r for r in w["records"]
                if not r["is_pivot"]
                and r["crossing_status"] != "AMBIGUOUS_CROSSING"
            ]]
            for wtp in [sum(
                1 for r in rows
                if r["crossing_status"] == "CROSSED"
                and bool(r["chebyshev_predicted_crossed"]))]
            for wfn in [sum(
                1 for r in rows
                if r["crossing_status"] == "CROSSED"
                and not bool(r["chebyshev_predicted_crossed"]))]
            for wtn in [sum(
                1 for r in rows
                if r["crossing_status"] != "CROSSED"
                and not bool(r["chebyshev_predicted_crossed"]))]
            for wfp in [sum(
                1 for r in rows
                if r["crossing_status"] != "CROSSED"
                and bool(r["chebyshev_predicted_crossed"]))]
        },
        "per_branch_balanced_accuracy": {
            str(branch): (
                0.5 * (btp / (btp + bfn) + btn / (btn + bfp))
                if (btp + bfn) and (btn + bfp) else None
            )
            for branch in sorted({r["branch_index"] for r in unambiguous})
            for rows in [[
                r for r in unambiguous if r["branch_index"] == branch
            ]]
            for btp in [sum(
                1 for r in rows
                if r["crossing_status"] == "CROSSED"
                and bool(r["chebyshev_predicted_crossed"]))]
            for bfn in [sum(
                1 for r in rows
                if r["crossing_status"] == "CROSSED"
                and not bool(r["chebyshev_predicted_crossed"]))]
            for btn in [sum(
                1 for r in rows
                if r["crossing_status"] != "CROSSED"
                and not bool(r["chebyshev_predicted_crossed"]))]
            for bfp in [sum(
                1 for r in rows
                if r["crossing_status"] != "CROSSED"
                and bool(r["chebyshev_predicted_crossed"]))]
        },
        "solve_equivalence_spearman_fresh": (
            _spearman(estimates, errors) if len(estimates) >= 3 else None
        ),
        "depth_spearman_on_crossings": (
            _spearman(
                np.asarray([abs(r["chebyshev_predicted_field"]
                                - r["own_value"]) for r in crossed_rows]),
                np.asarray([r["crossing_depth"] for r in crossed_rows]),
            ) if len(crossed_rows) >= 3 else None
        ),
        "per_world": [
            {
                "world": w["world"],
                "records": w["records"],
                "decode_decisiveness": w["decode_decisiveness"],
                "branch_distances": w["branch_distances"],
            }
            for w in worlds
        ],
    }

    instrument_defects = {
        "per_world": {
            w["world"]: w["g8_instrument_defects"] for w in worlds
        },
        "release_blocking_defect": any(
            w["g8_instrument_defects"]["defect"] for w in worlds
        ),
        "note": "plan §5: a G8 instrument-claim breach in a G9 run is an "
                "implementation defect and blocks release of the block",
    }

    return {
        "claims": claims,
        "g8_instrument_defects": instrument_defects,
        "non_vacuity": {
            "unambiguous_crossing_records": crossings,
            "conditioned_world_count": len(conditioned),
            "minimum_unambiguous_crossing_records":
                G9_NONVACUITY_MIN_CROSSINGS,
            "minimum_conditioned_worlds": G9_NONVACUITY_MIN_WORLDS,
            "empirically_informative": bool(non_vacuous),
            "on_vacuous": "report the block as empirically uninformative "
                          "for the mechanism claim; no claim of any "
                          "strength is made",
        },
        "secondary_report": secondary,
    }


def run_measurement(block: Path, manifest: Path) -> dict:
    from relweblearner.bench.graphlog_g9 import load_study_manifest
    study = load_study_manifest(manifest)
    result = evaluate_block(study, block)
    return {
        "record_type": RECORD_TYPE,
        "mode": "measurement",
        "block": str(block),
        "study_manifest_id": study.manifest_id,
        "claim_4_floor": G9_CLAIM4_FLOOR,
        **result,
    }


def run_verification(block: Path, phase_a_output: Path) -> dict:
    """Plan section 8.3 realization: outcomes precomputed, disclosed."""
    payload = json.loads(phase_a_output.read_text(encoding="utf-8"))
    output_sha256 = hashlib.sha256(
        phase_a_output.read_bytes()).hexdigest()
    study = load_g8_study(ROOT / G8_MANIFEST)
    result = evaluate_block(study, block)
    expected = {
        (r["world"], r["branch_index"], r["coordinate_id"]): r
        for w in payload["worlds"] if w["family"] == "g8-seed"
        for r in w["records"] if not r["is_pivot"]
    }
    mismatches = []
    compared = 0
    for w in result["secondary_report"]["per_world"]:
        for r in w["records"]:
            if r["is_pivot"]:
                continue
            key = (r["world"], r["branch_index"], r["coordinate_id"])
            reference = expected.pop(key, None)
            if reference is None:
                mismatches.append({"missing_in_phase_a": list(key)})
                continue
            compared += 1
            if (r["chebyshev_signed_estimate"]
                    != reference["chebyshev_signed_estimate"]
                    or bool(r["chebyshev_predicted_crossed"])
                    != bool(reference["chebyshev_predicted_crossed"])):
                mismatches.append({"prediction_mismatch": list(key)})
    for key in expected:
        mismatches.append({"missing_in_verification": list(key)})
    return {
        "record_type": RECORD_TYPE,
        "mode": "verification",
        "disclosure": "outcomes precomputed by the sealed Phase A analysis "
                      "and disclosed as such; this pass is a replication "
                      "anchor with zero discovery content by declaration "
                      "(plan sections 3 and 8.3)",
        "block": str(block),
        "phase_a_output_sha256": output_sha256,
        "instrument_claims_on_sealed_block": {
            key: value for key, value in result["claims"].items()
            if key.startswith(("1_", "2_", "3_"))
        },
        "predictor_replication": {
            "records_compared": compared,
            "bit_identical": not mismatches,
            "mismatches": mismatches,
        },
    }


def selftest() -> int:
    failures = []

    def check(name: str, condition: bool) -> None:
        print(f"  {'PASS' if condition else 'FAIL'}: {name}")
        if not condition:
            failures.append(name)

    ceiling = _ceiling()
    check("guard ceiling is the dressed 2x field tolerance",
          abs(ceiling - (2.0 * float(DEFAULT_SPEC.field_tolerance)
                         * (1.0 + LOCAL_BOUND_RELATIVE_SLACK)
                         + LOCAL_BOUND_ABSOLUTE_SLACK)) < 1e-18)

    check("three-valued claim-1 comparison treats band records as "
          "ambiguous",
          crossing_status(0.5 + ceiling / 2, 0.0, (1.0,), ceiling)
          == "AMBIGUOUS_CROSSING"
          and crossing_status(0.5 + 2 * ceiling, 0.0, (1.0,), ceiling)
          == "CROSSED")

    verdict = claim_4_verdict(6, 0, 8, 0)
    check("claim-4 wiring reproduces the g7-scale reference (0.891)",
          abs(verdict["decision_statistic"] - 0.891) < 2e-3
          and verdict["passed"])

    check("non-vacuity thresholds are the preregistered constants",
          G9_NONVACUITY_MIN_CROSSINGS == 5
          and G9_NONVACUITY_MIN_WORLDS == 2
          and abs(G9_CLAIM4_FLOOR - 0.776) < 1e-12)

    spearman_check = _spearman(
        np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.0, 8.0, 27.0, 64.0]))
    check("spearman monotone == 1", abs(spearman_check - 1.0) < 1e-12)

    print(f"\nselftest: {'ALL PASS' if not failures else 'FAILURES'}")
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("measurement", "verification"),
        default="measurement")
    parser.add_argument(
        "--block", type=Path, default=None,
        help="block root (defaults: results/graphlog-certified/g9 for "
             "measurement, results/graphlog-certified/g8 for verification)")
    parser.add_argument(
        "--manifest", type=Path,
        default=ROOT / "results/graphlog-certified/g9-validation-manifest.json")
    parser.add_argument(
        "--phase-a-output", type=Path, default=None,
        help="verification mode: path to the Phase A round-2 JSON")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.mode == "verification":
        if args.phase_a_output is None:
            parser.error("verification mode requires --phase-a-output")
        block = args.block or ROOT / "results/graphlog-certified/g8"
        report = run_verification(block, args.phase_a_output)
    else:
        block = args.block or ROOT / "results/graphlog-certified/g9"
        report = run_measurement(block, args.manifest)
    sys.stdout.buffer.write(canonical_bytes(report) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
