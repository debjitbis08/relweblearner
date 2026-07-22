"""Exact-contraction localized bounds and the interior-decisiveness
certificate for G8.

G8 is the two-part successor to the sealed G7 block.  It changes exactly one
inequality in the certified mathematics G7 shipped: the localized
per-coordinate error bound relaxes the interior residual contraction
``e_c = -row_c(H_uu^-1) . r`` with Cauchy--Schwarz
(``|row_c(H_uu^-1)| * |r|``) in G7; G8 keeps the exact contraction
``|row_c(H_uu^-1) . r|``.  The soundness argument is unchanged in kind --
the identity is exact for the true Dirichlet solution and the computed field
differs from it by at most the certified solver bound -- so the same slack
dressing and the same criterion shape are reused verbatim, with one
inequality removed.

Everything else is pinned.  Pivot discovery, conditioned Dirichlet branches,
hedge localization, and every threshold and slack constant are imported from
the frozen ``graphlog_g7_conditional`` module and reused bitwise; this module
adds only the tight bound and the interior-decisiveness certificate that
consumes it.  Like the G7 layer it lives outside ``bench.graphlog_certified``
so the frozen G0--G5 source digest is unchanged, and it never mutates any
object from a pinned module.

Validated on synthetic systems only (the G7 no-smoke-run rule): the tight
bound's outcome on the reused G7 draws is already computed to the float, so
exercising it there would observe a Part II outcome before preregistration.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .graphlog_g7_conditional import (
    BranchField,
    ConditionDiscovery,
    G7ConditionalError,
    LOCAL_BOUND_ABSOLUTE_SLACK,
    LOCAL_BOUND_RELATIVE_SLACK,
)


G8_INTERIOR_METHOD = "g8-interior-decisiveness/v1"


class G8ConditionalError(ValueError):
    """The interior-decisiveness construction violated a stated premise."""


def tight_localized_error_bounds(
    branch: BranchField,
    cochain: np.ndarray,
    witness_indices: Sequence[int],
) -> dict[int, dict[str, float]]:
    """Certified per-coordinate bounds via the exact interior contraction.

    Identical to ``graphlog_g7_conditional.localized_error_bounds`` except the
    Cauchy--Schwarz relaxation ``|row_c(H_uu^-1)| * |r|`` is replaced by the
    exact contraction ``|row_c(H_uu^-1) . r|``.  For the true Dirichlet
    solution the interior error satisfies ``H_uu e = -r`` exactly, hence
    ``e_c = -row_c(H_uu^-1) . r``; the computed field differs from that true
    solution by at most the certified solver bound.  The same preregistered
    slack constants (imported from the G7 module) dress the raw contraction,
    so the tight bound is sound by the same argument as G7 with one
    inequality removed.

    Each row records both the tight raw contraction ``|g . r|`` and the
    Cauchy--Schwarz alignment ``|g . r| / (|g| |r|)`` for disclosure: the
    alignment is the exact factor by which the shipped G7 bound overshot.
    """
    system = branch.system
    field = branch.run.field
    if field is None:
        raise G8ConditionalError("tight bounds require a solved branch field")
    values = np.asarray(cochain, dtype=float).reshape(-1)
    interior = np.asarray(system.interior_indices, dtype=int)
    position = {int(index): i for i, index in enumerate(interior)}
    y_u = values[interior]
    residual = system.laplacian_uu @ y_u + system.forcing
    residual_norm = float(np.linalg.norm(residual))
    solver = branch.run.certificate.solver
    solver_bound = float(solver.error_bound) if solver.error_bound is not None \
        else 0.0
    bounds: dict[int, dict[str, float]] = {}
    for index in witness_indices:
        if int(index) not in position:
            raise G8ConditionalError(
                "witness coordinate is not interior to the conditioned system"
            )
        unit = np.zeros(len(interior))
        unit[position[int(index)]] = 1.0
        green_row = np.linalg.solve(system.laplacian_uu, unit)
        green_row_norm = float(np.linalg.norm(green_row))
        # Exact contraction: |e_c| = |row_c(H_uu^-1) . r| for the true field.
        tight_raw = float(abs(float(green_row @ residual)))
        bound = (
            tight_raw * (1.0 + LOCAL_BOUND_RELATIVE_SLACK)
            + solver_bound
            + LOCAL_BOUND_ABSOLUTE_SLACK
        )
        denominator = green_row_norm * residual_norm
        alignment = tight_raw / denominator if denominator > 0.0 else 0.0
        observed = float(abs(
            float(field.values[int(index)]) - float(values[int(index)])
        ))
        bounds[int(index)] = {
            "green_row_norm": green_row_norm,
            "residual_norm": residual_norm,
            "solver_error_bound": solver_bound,
            "tight_raw": tight_raw,
            "alignment": alignment,
            "bound": bound,
            "observed_error": observed,
            "observed_within_bound": observed <= bound,
        }
    return bounds


def anti_propagation(
    *,
    branches: Sequence[BranchField],
    cochains: Sequence[np.ndarray],
    disputed_indices: Sequence[int],
    coordinate_ids: Sequence[str],
) -> dict[str, Any]:
    """Count disputed coordinates where a conditioned field crosses branches.

    Secondary metric per plan §8.4.  At a disputed coordinate the branch's own
    cochain value is the target its conditioned field is expected to settle
    toward; a field is said to *anti-propagate* when it settles strictly
    closer to another branch's value at that coordinate (the opposing branch's
    value) than to its own -- i.e. the conditioned solve commits to the wrong
    branch's value there.  Pinned pivot coordinates are exact by construction
    and can never cross, so the count is carried by non-pivot disputed
    coordinates.
    """
    vectors = [np.asarray(item, dtype=float).reshape(-1) for item in cochains]
    records: list[dict[str, Any]] = []
    count = 0
    for branch_index, branch in enumerate(branches):
        field = branch.run.field
        if field is None:
            continue
        own = vectors[branch_index]
        for index in disputed_indices:
            own_value = float(own[int(index)])
            opposing = sorted({
                float(vectors[other][int(index)])
                for other in range(len(branches))
                if float(vectors[other][int(index)]) != own_value
            })
            if not opposing:
                continue
            field_value = float(field.values[int(index)])
            nearest = min(opposing, key=lambda value: abs(field_value - value))
            crossed = abs(field_value - nearest) < abs(field_value - own_value)
            if crossed:
                count += 1
            records.append({
                "branch_index": branch_index,
                "coordinate_id": coordinate_ids[int(index)],
                "own_value": own_value,
                "opposing_value": nearest,
                "field_value": field_value,
                "crossed_to_opposing": bool(crossed),
            })
    return {
        "anti_propagation_count": count,
        "records": tuple(records),
    }


def interior_decisiveness(
    *,
    discovery: ConditionDiscovery,
    branches: Sequence[BranchField],
    cochains: Sequence[np.ndarray],
    coordinate_ids: Sequence[str],
) -> dict[str, Any]:
    """Certify pairwise branch separation under the exact-contraction bound.

    Mirrors ``graphlog_g7_conditional.conditional_separation`` but consumes the
    tight bound: a pair separates preferentially at an interior witness -- a
    non-pivot disputed coordinate whose exact gap exceeds the sum of both tight
    localized bounds -- and otherwise falls back to the always-sound pinned
    pivot coordinate.  The ``observed_within_bound`` witness exclusion is
    retained for symmetry with G7, but under the tight bound it cannot falsely
    fire: ``bound = |g . r| * (1 + slack) + solver_bound + slack`` and
    ``observed <= |g . r| + solver_bound`` by the exact contraction, so
    ``observed <= bound`` always and ``bound_soundness_violation_count`` is
    zero by construction on any solved conditioned branch.

    Each pair reports whether interior separation was achieved and the interior
    margin; the certificate also carries the anti-propagation count (§8.4).
    """
    if discovery.status != "CONDITIONED":
        raise G8ConditionalError("interior decisiveness requires a CONDITIONED discovery")
    vectors = [np.asarray(item, dtype=float).reshape(-1) for item in cochains]
    pinned = set(discovery.pivot_indices)
    bound_tables: list[dict[int, dict[str, float]] | None] = []
    for branch, vector in zip(branches, vectors, strict=True):
        if branch.run.field is None or not branch.boundary_consistent:
            bound_tables.append(None)
            continue
        witnesses = [
            index for index in discovery.disputed_indices
            if index not in pinned
        ]
        bound_tables.append(
            tight_localized_error_bounds(branch, vector, witnesses)
        )
    pairs = []
    all_separated = True
    unsound_total = 0
    interior_separated_total = 0
    for left in range(len(branches)):
        for right in range(left + 1, len(branches)):
            differing = [
                index for index in discovery.disputed_indices
                if vectors[left][index] != vectors[right][index]
            ]
            interior_witnesses = [
                index for index in differing if index not in pinned
            ]
            pivot_differs = [index for index in differing if index in pinned]
            left_table = bound_tables[left]
            right_table = bound_tables[right]
            record: dict[str, Any] = {
                "left_branch": left,
                "right_branch": right,
                "witness_kind": None,
                "witness_coordinate_id": None,
                "gamma": None,
                "left_bound": None,
                "right_bound": None,
                "left_tight_raw": None,
                "right_tight_raw": None,
                "remaining_margin": None,
                "unsound_witness_coordinate_ids": (),
                "interior_separated": False,
                "separated": False,
            }
            if left_table is None or right_table is None:
                record["witness_kind"] = "BRANCH_SOLVE_FAILED"
            else:
                best = None
                unsound = []
                for index in interior_witnesses:
                    gamma = float(abs(
                        vectors[left][index] - vectors[right][index]
                    ))
                    left_bound = left_table[index]["bound"]
                    right_bound = right_table[index]["bound"]
                    if not (
                        left_table[index]["observed_within_bound"]
                        and right_table[index]["observed_within_bound"]
                    ):
                        unsound.append(coordinate_ids[index])
                        continue
                    margin = gamma - left_bound - right_bound
                    candidate = (
                        margin, gamma, index, left_bound, right_bound,
                        left_table[index]["tight_raw"],
                        right_table[index]["tight_raw"],
                    )
                    if best is None or candidate > best:
                        best = candidate
                unsound_total += len(unsound)
                record["unsound_witness_coordinate_ids"] = tuple(unsound)
                if best is not None and best[0] > 0.0:
                    (margin, gamma, index, left_bound, right_bound,
                     left_raw, right_raw) = best
                    interior_separated_total += 1
                    record.update({
                        "witness_kind": "interior",
                        "witness_coordinate_id": coordinate_ids[index],
                        "gamma": gamma,
                        "left_bound": left_bound,
                        "right_bound": right_bound,
                        "left_tight_raw": left_raw,
                        "right_tight_raw": right_raw,
                        "remaining_margin": margin,
                        "interior_separated": True,
                        "separated": True,
                    })
                elif pivot_differs:
                    # The pivot set is injective on the solution set, so every
                    # solved branch pair differs at a pinned coordinate where
                    # both fields are exact by construction -- an always-sound
                    # fallback witness.
                    index = pivot_differs[0]
                    gamma = float(abs(
                        vectors[left][index] - vectors[right][index]
                    ))
                    record.update({
                        "witness_kind": (
                            "pinned" if not interior_witnesses
                            else "pinned_fallback"
                        ),
                        "witness_coordinate_id": coordinate_ids[index],
                        "gamma": gamma,
                        "left_bound": 0.0,
                        "right_bound": 0.0,
                        "left_tight_raw": 0.0,
                        "right_tight_raw": 0.0,
                        "remaining_margin": gamma,
                        "separated": gamma > 0.0,
                    })
                    if best is not None:
                        (margin, gamma, index, left_bound, right_bound,
                         left_raw, right_raw) = best
                        record["best_interior_witness"] = {
                            "witness_coordinate_id": coordinate_ids[index],
                            "gamma": gamma,
                            "left_bound": left_bound,
                            "right_bound": right_bound,
                            "left_tight_raw": left_raw,
                            "right_tight_raw": right_raw,
                            "remaining_margin": margin,
                        }
                elif best is not None:
                    (margin, gamma, index, left_bound, right_bound,
                     left_raw, right_raw) = best
                    record.update({
                        "witness_kind": "interior",
                        "witness_coordinate_id": coordinate_ids[index],
                        "gamma": gamma,
                        "left_bound": left_bound,
                        "right_bound": right_bound,
                        "left_tight_raw": left_raw,
                        "right_tight_raw": right_raw,
                        "remaining_margin": margin,
                    })
                else:
                    record["witness_kind"] = "BOUND_SOUNDNESS_VIOLATED"
            all_separated = all_separated and bool(record["separated"])
            pairs.append(record)
    anti = anti_propagation(
        branches=branches,
        cochains=cochains,
        disputed_indices=discovery.disputed_indices,
        coordinate_ids=coordinate_ids,
    )
    return {
        "method": G8_INTERIOR_METHOD,
        "condition_id": discovery.condition_id,
        "pivot_coordinate_ids": tuple(
            coordinate_ids[index] for index in discovery.pivot_indices
        ),
        "disputed_coordinate_ids": tuple(
            coordinate_ids[index] for index in discovery.disputed_indices
        ),
        "branch_count": len(branches),
        "branch_solver_status": tuple(
            "SOLVED" if branch.run.field is not None else "FAILED"
            for branch in branches
        ),
        "branch_boundary_consistent": tuple(
            bool(branch.boundary_consistent) for branch in branches
        ),
        "branch_spectral_lower_bounds": tuple(
            None if branch.run.certificate.spectrum.lower_bound is None
            else float(branch.run.certificate.spectrum.lower_bound)
            for branch in branches
        ),
        "compared_pairs": tuple(pairs),
        "bound_soundness_violation_count": unsound_total,
        "interior_separated_pair_count": interior_separated_total,
        "anti_propagation": anti,
        "separating": all_separated and bool(pairs),
    }


# Source label for the hedge fields below: they are straight carry-overs from
# the reproduced G7 hedge-localization record (the pinned check on the
# *unconditioned* shared field), not a G8 recomputation.
HEDGE_CARRYOVER_SOURCE = "g7-hedge-localization-carryover"


def secondary_metrics(
    certificate: Mapping[str, Any],
    hedge_localization_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the preregistered secondary report as one record (plan §5).

    Everything here is a measured outcome, never a preregistered prediction:
    the interior-decisiveness count, the per-pair interior margins, the
    anti-propagation count (§8.4), and the hedge off-scope errors.  The hedge
    fields matter because a passing mean can hide a large pointwise excursion
    (the sealed rule_2 case: max 1.10 on an agreeing coordinate under a
    passing 0.016 mean), so the **max** off-scope error is first-class here.
    ``hedge_mean_off_scope_error`` / ``hedge_max_off_scope_error`` are straight
    carry-overs from the reproduced G7 ``hedge_localization`` record
    (``HEDGE_CARRYOVER_SOURCE`` names the provenance) so the secondary report
    is a single artifact rather than a cross-reference into the G7 layer.
    """
    interior_margins = []
    for pair in certificate["compared_pairs"]:
        if pair.get("witness_kind") == "interior":
            interior_margins.append(pair["remaining_margin"])
        else:
            best = pair.get("best_interior_witness")
            interior_margins.append(
                None if best is None else best["remaining_margin"]
            )
    record: dict[str, Any] = {
        "interior_separated_pair_count":
            certificate["interior_separated_pair_count"],
        "per_pair_best_interior_margins": tuple(interior_margins),
        "anti_propagation_count":
            certificate["anti_propagation"]["anti_propagation_count"],
        "hedge_mean_off_scope_error": None,
        "hedge_max_off_scope_error": None,
        "hedge_metrics_source": HEDGE_CARRYOVER_SOURCE,
    }
    if hedge_localization_record is not None:
        record["hedge_mean_off_scope_error"] = float(
            hedge_localization_record["mean_absolute_error"]
        )
        record["hedge_max_off_scope_error"] = float(
            hedge_localization_record["max_absolute_error"]
        )
    return record
