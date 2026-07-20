"""Pivot-conditioned separation for G7 (conditional commitments).

This module implements the certified mathematics that G7 adds on top of the
frozen G0--G5 theorem code: pivot discovery over an enumerated exact solution
set, per-branch Dirichlet fields conditioned on the pivot hypothesis, sound
per-coordinate (localized) error bounds via discrete Green's-function rows,
the branch-conditional separation certificate, and the hedge-localization
check on the unconditioned shared field.

It deliberately lives outside ``bench.graphlog_certified`` so the frozen
G0--G5 source digest is unchanged, and it never mutates any object from the
pinned modules; conditioning is expressed purely through new
``BoundarySpec`` instances fed back into the pinned T5 solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Sequence

import numpy as np

from ..certification.t5 import (
    BoundarySpec,
    DirichletSystem,
    SolverConfig,
    T5Run,
    partition_dirichlet,
    run_t5,
)
from ..certification.types import canonical_digest


G7_CONDITIONAL_METHOD = "g7-pivot-conditioned-separation/v1"
# Parsimony cap: at most this many invented condition bits per world.  A
# solution set needing more is reported as AMBIGUITY_OVERFLOW, never grown.
MAX_CONDITION_BITS = 3
# Preregistered hedge-localization threshold: mean absolute error of the
# unconditioned shared field on coordinates where all solutions agree.
HEDGE_LOCALIZATION_MEAN_THRESHOLD = 0.1
# Multiplicative and additive slack on the localized Green's-row bound to
# absorb floating-point solve error on top of the certified solver bound.
LOCAL_BOUND_RELATIVE_SLACK = 1e-9
LOCAL_BOUND_ABSOLUTE_SLACK = 1e-9


class G7ConditionalError(ValueError):
    """The conditional-separation construction violated a stated premise."""


@dataclass(frozen=True, slots=True)
class ConditionDiscovery:
    """Deterministic pivot discovery over an exact solution set.

    ``status`` is one of ``UNIQUE`` (no invention required),
    ``CONDITIONED`` (pivot bits invented), or ``AMBIGUITY_OVERFLOW``
    (solution count exceeds the preregistered cap).
    """

    status: str
    solution_count: int
    disputed_indices: tuple[int, ...]
    pivot_indices: tuple[int, ...]
    condition_id: str | None


def discover_conditions(
    cochains: Sequence[np.ndarray],
    coordinate_ids: Sequence[str],
) -> ConditionDiscovery:
    """Choose the minimum-cardinality pivot set that separates all solutions.

    Candidate subsets of the disputed coordinates are searched in order of
    size and then lexicographically in canonical ``coordinate_ids`` order;
    the first subset on which the solution projections are injective wins.
    The result is deterministic, needs no scoring, and never exceeds
    ``MAX_CONDITION_BITS`` coordinates — solution sets with no separating
    subset that small report ``AMBIGUITY_OVERFLOW``.
    """
    vectors = [np.asarray(item, dtype=float).reshape(-1) for item in cochains]
    if not vectors:
        raise G7ConditionalError("condition discovery requires at least one solution")
    length = len(coordinate_ids)
    if any(vector.shape != (length,) for vector in vectors):
        raise G7ConditionalError("solution cochain length differs from coordinates")
    if len(vectors) == 1:
        return ConditionDiscovery("UNIQUE", 1, (), (), None)
    stacked = np.stack(vectors)
    disputed = tuple(
        int(index) for index in np.flatnonzero(
            np.any(stacked != stacked[0], axis=0)
        )
    )
    if not disputed:
        raise G7ConditionalError("distinct solutions with identical cochains")
    pivots: tuple[int, ...] | None = None
    if len(vectors) <= 2 ** MAX_CONDITION_BITS:
        for size in range(1, MAX_CONDITION_BITS + 1):
            for subset in combinations(disputed, size):
                projections = {
                    tuple(stacked[member, list(subset)])
                    for member in range(len(vectors))
                }
                if len(projections) == len(vectors):
                    pivots = subset
                    break
            if pivots is not None:
                break
    if pivots is None:
        return ConditionDiscovery(
            "AMBIGUITY_OVERFLOW", len(vectors), disputed, (), None,
        )
    condition_id = "condition:" + canonical_digest({
        "method": G7_CONDITIONAL_METHOD,
        "pivot_coordinate_ids": tuple(
            coordinate_ids[index] for index in pivots
        ),
    })
    return ConditionDiscovery(
        "CONDITIONED", len(vectors), disputed, tuple(pivots), condition_id,
    )


@dataclass(frozen=True, slots=True)
class BranchField:
    """One conditioned Dirichlet solve for one member of the solution set."""

    branch_index: int
    pivot_values: tuple[float, ...]
    system: DirichletSystem
    run: T5Run
    boundary_consistent: bool


def conditioned_branch(
    *,
    branch_index: int,
    base_system: DirichletSystem,
    cochain: np.ndarray,
    pivot_indices: Sequence[int],
    coordinate_ids: Sequence[str],
    field_tolerance: float,
) -> BranchField:
    """Re-solve the pinned Dirichlet problem with pivot coordinates pinned.

    Only the pivot coordinates join the boundary; the remaining disputed
    coordinates stay interior so the solve itself must propagate the branch
    hypothesis to them.  Enlarging the Dirichlet boundary can only raise
    the interior spectral lower bound, so conditioning never loosens the
    T5 constants.
    """
    values = np.asarray(cochain, dtype=float).reshape(-1)
    base_pairs = tuple(zip(
        base_system.boundary_ids,
        (float(item) for item in base_system.boundary_values),
    ))
    base_ids = set(base_system.boundary_ids)
    boundary_consistent = all(
        float(values[index]) == float(value)
        for index, value in zip(
            base_system.boundary_indices, base_system.boundary_values,
        )
    )
    pivot_pairs = tuple(
        (coordinate_ids[index], float(values[index]))
        for index in pivot_indices
        if coordinate_ids[index] not in base_ids
    )
    system = partition_dirichlet(
        base_system.coboundary,
        BoundarySpec(values=(*base_pairs, *pivot_pairs)),
    )
    run = run_t5(system, SolverConfig(field_tolerance=float(field_tolerance)))
    return BranchField(
        branch_index=branch_index,
        pivot_values=tuple(float(values[index]) for index in pivot_indices),
        system=system,
        run=run,
        boundary_consistent=boundary_consistent,
    )


def localized_error_bounds(
    branch: BranchField,
    cochain: np.ndarray,
    witness_indices: Sequence[int],
) -> dict[int, dict[str, float]]:
    """Certified per-coordinate bounds |field_c - exact_c| at interior coords.

    For interior error ``e = u - y_u`` the Dirichlet system gives
    ``H_uu e = -r`` with ``r = H_uu y_u + H_ub b`` the exact interior
    residual, so ``|e_c| <= ||row_c(H_uu^-1)||_2 * ||r||_2``.  The row norm
    is obtained by one linear solve per witness and the certified solver
    error bound is added on top, with preregistered floating-point slack.
    """
    system = branch.system
    field = branch.run.field
    if field is None:
        raise G7ConditionalError("localized bounds require a solved branch field")
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
            raise G7ConditionalError(
                "witness coordinate is not interior to the conditioned system"
            )
        unit = np.zeros(len(interior))
        unit[position[int(index)]] = 1.0
        green_row = np.linalg.solve(system.laplacian_uu, unit)
        raw = float(np.linalg.norm(green_row)) * residual_norm
        bound = (
            raw * (1.0 + LOCAL_BOUND_RELATIVE_SLACK)
            + solver_bound
            + LOCAL_BOUND_ABSOLUTE_SLACK
        )
        observed = float(abs(
            float(field.values[int(index)]) - float(values[int(index)])
        ))
        bounds[int(index)] = {
            "green_row_norm": float(np.linalg.norm(green_row)),
            "residual_norm": residual_norm,
            "solver_error_bound": solver_bound,
            "bound": bound,
            "observed_error": observed,
            "observed_within_bound": observed <= bound,
        }
    return bounds


def hedge_localization(
    shared_field_values: np.ndarray,
    cochains: Sequence[np.ndarray],
    disputed_indices: Sequence[int],
) -> dict[str, Any]:
    """Check the unconditioned field errs only where the exact solutions fork."""
    stacked = np.stack([
        np.asarray(item, dtype=float).reshape(-1) for item in cochains
    ])
    field = np.asarray(shared_field_values, dtype=float).reshape(-1)
    agreeing = np.setdiff1d(
        np.arange(stacked.shape[1]), np.asarray(disputed_indices, dtype=int),
    )
    errors = np.abs(field[agreeing] - stacked[0, agreeing])
    mean_error = float(errors.mean()) if len(errors) else 0.0
    return {
        "agreeing_coordinate_count": int(len(agreeing)),
        "mean_absolute_error": mean_error,
        "max_absolute_error": float(errors.max()) if len(errors) else 0.0,
        "threshold": HEDGE_LOCALIZATION_MEAN_THRESHOLD,
        "localized": mean_error <= HEDGE_LOCALIZATION_MEAN_THRESHOLD,
    }


def conditional_separation(
    *,
    discovery: ConditionDiscovery,
    branches: Sequence[BranchField],
    cochains: Sequence[np.ndarray],
    coordinate_ids: Sequence[str],
) -> dict[str, Any]:
    """Certify pairwise branch separation at localized witnesses.

    A pair separates preferentially at an interior witness — a disputed
    coordinate interior to both conditioned systems whose exact gap exceeds
    the sum of both localized bounds (the propagation-decisiveness claim,
    reported as ``interior_separated``) — and otherwise falls back to a
    pinned pivot coordinate where both branch fields are exact by
    construction.  The fallback always exists for solved branch pairs
    because the pivot set is injective on the solution set.  Witnesses
    whose observed error violates their own bound are excluded and
    disclosed per pair and in a certificate-level count.
    """
    if discovery.status != "CONDITIONED":
        raise G7ConditionalError("separation requires a CONDITIONED discovery")
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
            localized_error_bounds(branch, vector, witnesses)
        )
    pairs = []
    all_separated = True
    unsound_total = 0
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
                    candidate = (margin, gamma, index, left_bound, right_bound)
                    if best is None or candidate > best:
                        best = candidate
                unsound_total += len(unsound)
                record["unsound_witness_coordinate_ids"] = tuple(unsound)
                if best is not None and best[0] > 0.0:
                    margin, gamma, index, left_bound, right_bound = best
                    record.update({
                        "witness_kind": "interior",
                        "witness_coordinate_id": coordinate_ids[index],
                        "gamma": gamma,
                        "left_bound": left_bound,
                        "right_bound": right_bound,
                        "remaining_margin": margin,
                        "interior_separated": True,
                        "separated": True,
                    })
                elif pivot_differs:
                    # The pivot set is injective on the solution set, so
                    # every solved branch pair differs at a pinned
                    # coordinate where both fields are exact by
                    # construction — an always-sound fallback witness.
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
                        "remaining_margin": gamma,
                        "separated": gamma > 0.0,
                    })
                    if best is not None:
                        margin, gamma, index, left_bound, right_bound = best
                        record["best_interior_witness"] = {
                            "witness_coordinate_id": coordinate_ids[index],
                            "gamma": gamma,
                            "left_bound": left_bound,
                            "right_bound": right_bound,
                            "remaining_margin": margin,
                        }
                elif best is not None:
                    margin, gamma, index, left_bound, right_bound = best
                    record.update({
                        "witness_kind": "interior",
                        "witness_coordinate_id": coordinate_ids[index],
                        "gamma": gamma,
                        "left_bound": left_bound,
                        "right_bound": right_bound,
                        "remaining_margin": margin,
                    })
                else:
                    record["witness_kind"] = "BOUND_SOUNDNESS_VIOLATED"
            all_separated = all_separated and bool(record["separated"])
            pairs.append(record)
    return {
        "method": G7_CONDITIONAL_METHOD,
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
        "interior_separated_pair_count": sum(
            1 for pair in pairs if pair["interior_separated"]
        ),
        "separating": all_separated and bool(pairs),
    }
