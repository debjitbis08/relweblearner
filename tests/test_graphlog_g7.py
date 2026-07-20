"""G7 conditional-commitment harness, discovery, and certificate tests."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from relweblearner.certification.t5 import (
    BoundarySpec,
    Linearization,
    assemble_coboundary,
    partition_dirichlet,
    residual_block_from_rational,
)
from relweblearner.bench import graphlog_g6, graphlog_g7
from relweblearner.bench.graphlog_g7_conditional import (
    G7ConditionalError,
    conditional_separation,
    conditioned_branch,
    discover_conditions,
    hedge_localization,
    localized_error_bounds,
)
from relweblearner.bench.graphlog_g7_executor import _receipt as g7_receipt


COORDS = ("x0", "x1", "x2", "x3")


def _chain_system():
    block = residual_block_from_rational(
        "path",
        ((-1, 1, 0, 0), (0, -1, 1, 0), (0, 0, -1, 1)),
        weight=Fraction(1),
    )
    coboundary = assemble_coboundary(Linearization(COORDS, (block,)))
    return partition_dirichlet(
        coboundary, BoundarySpec((("x0", 1.0), ("x3", 0.0)))
    )


def test_discover_conditions_unique_solution_invents_nothing():
    discovery = discover_conditions([np.array([1.0, 0.0, 0.0, 0.0])], COORDS)
    assert discovery.status == "UNIQUE"
    assert discovery.pivot_indices == ()
    assert discovery.condition_id is None


def test_discover_conditions_twofold_uses_single_canonical_pivot():
    y_a = np.array([1.0, 1.0, 1.0, 0.0])
    y_b = np.array([1.0, 0.0, 0.0, 0.0])
    discovery = discover_conditions([y_a, y_b], COORDS)
    assert discovery.status == "CONDITIONED"
    assert discovery.disputed_indices == (1, 2)
    assert discovery.pivot_indices == (1,)
    repeat = discover_conditions([y_a, y_b], COORDS)
    assert repeat.condition_id == discovery.condition_id


def test_discover_conditions_multibit_and_overflow():
    grid = [
        np.array([a, b], dtype=float) for a in (0.0, 1.0) for b in (0.0, 1.0)
    ]
    discovery = discover_conditions(grid, ("c0", "c1"))
    assert discovery.status == "CONDITIONED"
    assert discovery.pivot_indices == (0, 1)
    many = [np.eye(9)[i] for i in range(9)]
    overflow = discover_conditions(many, tuple(f"c{i}" for i in range(9)))
    assert overflow.status == "AMBIGUITY_OVERFLOW"
    assert overflow.pivot_indices == ()


def test_discover_conditions_finds_minimum_not_greedy_pivots():
    # Greedy canonical refinement would take c0 (it splits the set) and
    # still need two more coordinates; the minimum separating subset is
    # {c1, c2} with injective projections (1,1),(0,0),(0,1),(1,0).
    solutions = [
        np.array([0.0, 1.0, 1.0]),
        np.array([1.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 1.0]),
        np.array([1.0, 1.0, 0.0]),
    ]
    discovery = discover_conditions(solutions, ("c0", "c1", "c2"))
    assert discovery.status == "CONDITIONED"
    assert discovery.pivot_indices == (1, 2)


def test_one_hot_solutions_within_cap_need_more_than_log2_bits():
    # Four one-hot solutions admit no 2-coordinate injective projection;
    # the minimum separating subset has 3 coordinates, still within cap.
    solutions = [np.eye(4)[i] for i in range(4)]
    discovery = discover_conditions(solutions, ("c0", "c1", "c2", "c3"))
    assert discovery.status == "CONDITIONED"
    assert discovery.pivot_indices == (0, 1, 2)


def test_conditioned_branch_pins_pivot_and_never_loosens_spectrum():
    system = _chain_system()
    y_a = np.array([1.0, 1.0, 1.0, 0.0])
    discovery = discover_conditions(
        [y_a, np.array([1.0, 0.0, 0.0, 0.0])], COORDS,
    )
    branch = conditioned_branch(
        branch_index=0,
        base_system=system,
        cochain=y_a,
        pivot_indices=discovery.pivot_indices,
        coordinate_ids=COORDS,
        field_tolerance=1e-9,
    )
    assert branch.boundary_consistent
    assert set(branch.system.boundary_ids) == {"x0", "x1", "x3"}
    assert branch.run.field is not None
    assert float(branch.run.field.values[1]) == 1.0
    base_lower = float(1.0)  # interior [[2,-1],[-1,2]] has lambda_min = 1
    conditioned_lower = branch.run.certificate.spectrum.lower_bound
    assert conditioned_lower is not None
    assert conditioned_lower >= base_lower


def test_localized_bounds_are_sound_and_certify_branch_separation():
    system = _chain_system()
    y_a = np.array([1.0, 1.0, 1.0, 0.0])
    y_b = np.array([1.0, 0.0, 0.0, 0.0])
    discovery = discover_conditions([y_a, y_b], COORDS)
    branches = tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=COORDS,
            field_tolerance=1e-9,
        )
        for index, cochain in enumerate((y_a, y_b))
    )
    bounds_b = localized_error_bounds(branches[1], y_b, [2])
    assert bounds_b[2]["observed_within_bound"]
    assert bounds_b[2]["bound"] < 0.5
    certificate = conditional_separation(
        discovery=discovery,
        branches=branches,
        cochains=(y_a, y_b),
        coordinate_ids=COORDS,
    )
    assert certificate["separating"] is True
    (pair,) = certificate["compared_pairs"]
    assert pair["witness_kind"] == "interior"
    assert pair["witness_coordinate_id"] == "x2"
    assert pair["gamma"] == 1.0
    assert pair["remaining_margin"] > 0.0


def test_pinned_fallback_engages_when_interior_bounds_are_too_loose():
    # Branch B claims x2=1 against a conditioned harmonic value of 0; its
    # localized bound at x2 is ~1.0, so the interior margin is negative and
    # the pair must fall back to the always-sound pinned pivot witness.
    system = _chain_system()
    y_a = np.array([1.0, 1.0, 0.0, 0.0])
    y_b = np.array([1.0, 0.0, 1.0, 0.0])
    discovery = discover_conditions([y_a, y_b], COORDS)
    assert discovery.pivot_indices == (1,)
    branches = tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=COORDS,
            field_tolerance=1e-9,
        )
        for index, cochain in enumerate((y_a, y_b))
    )
    certificate = conditional_separation(
        discovery=discovery,
        branches=branches,
        cochains=(y_a, y_b),
        coordinate_ids=COORDS,
    )
    (pair,) = certificate["compared_pairs"]
    assert pair["witness_kind"] == "pinned_fallback"
    assert pair["witness_coordinate_id"] == "x1"
    assert pair["separated"] is True
    assert pair["interior_separated"] is False
    assert pair["best_interior_witness"]["remaining_margin"] <= 0.0
    assert certificate["separating"] is True
    assert certificate["interior_separated_pair_count"] == 0


def test_pinned_only_disagreement_separates_by_construction():
    system = _chain_system()
    y_a = np.array([1.0, 1.0, 0.0, 0.0])
    y_b = np.array([1.0, 0.0, 0.0, 0.0])
    discovery = discover_conditions([y_a, y_b], COORDS)
    assert discovery.disputed_indices == (1,)
    branches = tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=COORDS,
            field_tolerance=1e-9,
        )
        for index, cochain in enumerate((y_a, y_b))
    )
    certificate = conditional_separation(
        discovery=discovery,
        branches=branches,
        cochains=(y_a, y_b),
        coordinate_ids=COORDS,
    )
    (pair,) = certificate["compared_pairs"]
    assert pair["witness_kind"] == "pinned"
    assert pair["separated"] is True
    assert certificate["separating"] is True


def test_hedge_localization_threshold():
    y_a = np.array([1.0, 1.0, 0.0, 0.0])
    y_b = np.array([1.0, 0.0, 0.0, 0.0])
    tight = hedge_localization(
        np.array([1.0, 0.5, 0.01, 0.0]), (y_a, y_b), (1,),
    )
    assert tight["localized"] is True
    sloppy = hedge_localization(
        np.array([0.4, 0.5, 0.6, 0.4]), (y_a, y_b), (1,),
    )
    assert sloppy["localized"] is False


def test_witness_must_be_interior_to_the_conditioned_system():
    system = _chain_system()
    y_a = np.array([1.0, 1.0, 1.0, 0.0])
    branch = conditioned_branch(
        branch_index=0,
        base_system=system,
        cochain=y_a,
        pivot_indices=(1,),
        coordinate_ids=COORDS,
        field_tolerance=1e-9,
    )
    with pytest.raises(G7ConditionalError):
        localized_error_bounds(branch, y_a, [1])


def test_g7_manifest_reuses_g6_draws_with_disclosure():
    study = graphlog_g7.load_study_manifest()
    g6_study = graphlog_g6.load_study_manifest()
    assert study.output_root == Path("results/graphlog-certified/g7")
    assert study.draws == g6_study.draws
    assert study.freeze_commit == g6_study.freeze_commit
    assert study.manifest_id != g6_study.manifest_id
    document = json.loads(
        Path(graphlog_g7.G7_MANIFEST).read_text(encoding="utf-8")
    )
    provenance = document["draw_provenance"]
    assert provenance["reused_from_study"] == g6_study.manifest_id
    assert provenance["g6_outcomes_observed"] is True


def test_g7_amendment_chain_base_is_disabled_and_blocks_execution(tmp_path):
    study = graphlog_g7.load_study_manifest()
    chain = graphlog_g7.load_amendment_chain()
    base = chain[0]
    assert base.execution_enabled is False
    assert base.study_manifest_id == study.manifest_id
    assert len(base.harness_commit) == 40
    with pytest.raises(graphlog_g7.G7PreflightError, match="disabled"):
        graphlog_g7.execute_study(
            study, base, lambda *args: {}, root=tmp_path,
        )
    tip = chain[-1]
    if tip.execution_enabled:
        assert tip.executor_file \
            == "src/relweblearner/bench/graphlog_g7_executor.py"
        assert tip.executor_qualname == "execute_phase"
        assert tip.parent_amendment_id == base.manifest_id


def test_g7_receipt_schema_is_g7_only(tmp_path):
    draw = graphlog_g7.G7Draw(0, "rule_1", "ab" * 32, 7)
    (tmp_path / "artifact.json").write_text("{}\n", encoding="utf-8")
    receipt = g7_receipt(
        graphlog_g7.G7Phase.STRUCTURAL, draw, tmp_path, status="PASS",
    )
    validated = graphlog_g7._validate_receipt(
        receipt, graphlog_g7.G7Phase.STRUCTURAL, draw,
    )
    assert validated["schema_version"] == graphlog_g7.G7_RECEIPT_SCHEMA
    with pytest.raises(ValueError, match="schema"):
        graphlog_g6._validate_receipt(
            receipt, graphlog_g7.G7Phase.STRUCTURAL, draw,
        )
