"""G8 interior-decisiveness: tight-bound, certificate, and harness tests.

All validation is on synthetic Dirichlet chains only (the G8 no-smoke-run
rule): the tight bound's outcome on the reused G7 draws is already computed
to the float, so exercising it there would observe a Part II outcome before
preregistration.
"""

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
from relweblearner.certification.types import canonical_digest
from relweblearner.bench import graphlog_g6, graphlog_g7, graphlog_g8
from relweblearner.bench.graphlog_g7_conditional import (
    conditioned_branch,
    discover_conditions,
    hedge_localization,
    localized_error_bounds,
)
from relweblearner.bench.graphlog_g8_conditional import (
    G8ConditionalError,
    HEDGE_CARRYOVER_SOURCE,
    anti_propagation,
    interior_decisiveness,
    secondary_metrics,
    tight_localized_error_bounds,
)
from relweblearner.bench import graphlog_g8_executor
from relweblearner.bench.graphlog_g8_executor import (
    G8_PART1_OVERLAY_STATUSES,
    G8_PART2_OVERLAY_STATUSES,
    _receipt as g8_receipt,
    overlay_status,
)


def _chain(coords, boundary):
    """A unit-weight path Dirichlet system over ``coords`` with pinned ends."""
    n = len(coords)
    rows = tuple(
        tuple(-1 if j == i else (1 if j == i + 1 else 0) for j in range(n))
        for i in range(n - 1)
    )
    block = residual_block_from_rational("path", rows, weight=Fraction(1))
    coboundary = assemble_coboundary(Linearization(coords, (block,)))
    return partition_dirichlet(coboundary, BoundarySpec(boundary))


C4 = ("x0", "x1", "x2", "x3")
C5 = ("x0", "x1", "x2", "x3", "x4")


def _branches(system, cochains, coords, discovery, tol=1e-12):
    return tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=coords,
            field_tolerance=tol,
        )
        for index, cochain in enumerate(cochains)
    )


# --------------------------------------------------------------------------
# Tight bound: soundness, exactness, Cauchy-Schwarz domination
# --------------------------------------------------------------------------

def test_tight_bound_is_sound_bound_at_least_observed():
    system = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C5)
    branches = _branches(system, cochains, C5, discovery)
    for branch, cochain in zip(branches, cochains):
        table = tight_localized_error_bounds(branch, cochain, [2, 3])
        for row in table.values():
            assert row["bound"] >= row["observed_error"]
            assert row["observed_within_bound"] is True


def test_tight_raw_equals_observed_error_to_solver_tolerance():
    system = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C5)
    branches = _branches(system, cochains, C5, discovery)
    for branch, cochain in zip(branches, cochains):
        table = tight_localized_error_bounds(branch, cochain, [2, 3])
        for row in table.values():
            # exact contraction: |g . r| is the true interior error, so the
            # raw value tracks the observed field error to solver tolerance.
            tol = row["solver_error_bound"] + 1e-9
            assert abs(row["tight_raw"] - row["observed_error"]) <= tol


def test_tight_bound_dominates_shipped_cauchy_schwarz_bound_everywhere():
    system = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C5)
    branches = _branches(system, cochains, C5, discovery)
    strict_somewhere = False
    for branch, cochain in zip(branches, cochains):
        tight = tight_localized_error_bounds(branch, cochain, [2, 3])
        shipped = localized_error_bounds(branch, cochain, [2, 3])
        for index in (2, 3):
            assert tight[index]["bound"] <= shipped[index]["bound"] + 1e-15
            assert 0.0 <= tight[index]["alignment"] <= 1.0 + 1e-12
            if tight[index]["bound"] < shipped[index]["bound"] - 1e-9:
                strict_somewhere = True
    # multi-coordinate interior => the Cauchy-Schwarz relaxation is strict
    assert strict_somewhere


# --------------------------------------------------------------------------
# Interior-decisiveness certificate
# --------------------------------------------------------------------------

def test_interior_decisiveness_certifies_on_synthetic_chain():
    system = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C5)
    assert discovery.pivot_indices == (1,)
    branches = _branches(system, cochains, C5, discovery)
    certificate = interior_decisiveness(
        discovery=discovery,
        branches=branches,
        cochains=cochains,
        coordinate_ids=C5,
    )
    assert certificate["separating"] is True
    assert certificate["interior_separated_pair_count"] == 1
    (pair,) = certificate["compared_pairs"]
    assert pair["witness_kind"] == "interior"
    assert pair["interior_separated"] is True
    assert pair["gamma"] == 1.0
    assert pair["remaining_margin"] > 0.0
    assert pair["left_tight_raw"] is not None


def test_interior_decisiveness_requires_conditioned_discovery():
    unique = discover_conditions([np.array([1.0, 0.0, 0.0, 0.0])], C4)
    with pytest.raises(G8ConditionalError):
        interior_decisiveness(
            discovery=unique, branches=(), cochains=(), coordinate_ids=C4,
        )


def test_exclusion_never_falsely_fires_under_tight_bound():
    # Across a certifying chain and a hedging chain, the tight bound is >=
    # observed by construction, so no witness is ever excluded as unsound.
    system5 = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains5 = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    system4 = _chain(C4, (("x0", 1.0), ("x3", 0.0)))
    cochains4 = (np.array([1., 1., 0., 0.]), np.array([1., 0., 1., 0.]))
    for system, cochains, coords in (
        (system5, cochains5, C5), (system4, cochains4, C4),
    ):
        discovery = discover_conditions(cochains, coords)
        branches = _branches(system, cochains, coords, discovery)
        certificate = interior_decisiveness(
            discovery=discovery,
            branches=branches,
            cochains=cochains,
            coordinate_ids=coords,
        )
        assert certificate["bound_soundness_violation_count"] == 0
        for pair in certificate["compared_pairs"]:
            assert pair["unsound_witness_coordinate_ids"] == ()


def test_pinned_fallback_retained_when_interior_margin_negative():
    # Branch B hedges/anti-propagates at x2 so the tight interior margin is
    # negative; the pair must fall back to the always-sound pinned pivot.
    system = _chain(C4, (("x0", 1.0), ("x3", 0.0)))
    cochains = (np.array([1., 1., 0., 0.]), np.array([1., 0., 1., 0.]))
    discovery = discover_conditions(cochains, C4)
    assert discovery.pivot_indices == (1,)
    branches = _branches(system, cochains, C4, discovery)
    certificate = interior_decisiveness(
        discovery=discovery,
        branches=branches,
        cochains=cochains,
        coordinate_ids=C4,
    )
    (pair,) = certificate["compared_pairs"]
    assert pair["witness_kind"] == "pinned_fallback"
    assert pair["separated"] is True
    assert pair["interior_separated"] is False
    assert certificate["separating"] is True
    assert certificate["interior_separated_pair_count"] == 0


# --------------------------------------------------------------------------
# Anti-propagation counter (§8.4)
# --------------------------------------------------------------------------

def test_anti_propagation_counts_cross_to_opposing_value():
    system = _chain(C4, (("x0", 1.0), ("x3", 0.0)))
    cochains = (np.array([1., 1., 0., 0.]), np.array([1., 0., 1., 0.]))
    discovery = discover_conditions(cochains, C4)
    branches = _branches(system, cochains, C4, discovery)
    report = anti_propagation(
        branches=branches,
        cochains=cochains,
        disputed_indices=discovery.disputed_indices,
        coordinate_ids=C4,
    )
    # Branch 1 pins x1=0 and its x2 field settles at 0, i.e. it commits to
    # branch 0's value (0) against its own cochain value 1 -> one crossing.
    assert report["anti_propagation_count"] == 1
    crossed = [r for r in report["records"] if r["crossed_to_opposing"]]
    assert len(crossed) == 1
    assert crossed[0]["branch_index"] == 1
    assert crossed[0]["coordinate_id"] == "x2"
    # The certificate surfaces the same count.
    certificate = interior_decisiveness(
        discovery=discovery, branches=branches,
        cochains=cochains, coordinate_ids=C4,
    )
    assert certificate["anti_propagation"]["anti_propagation_count"] == 1


def test_anti_propagation_zero_when_fields_settle_in_own_valley():
    system = _chain(C4, (("x0", 1.0), ("x3", 0.0)))
    cochains = (np.array([1., 1., 1., 0.]), np.array([1., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C4)
    branches = _branches(system, cochains, C4, discovery)
    report = anti_propagation(
        branches=branches,
        cochains=cochains,
        disputed_indices=discovery.disputed_indices,
        coordinate_ids=C4,
    )
    assert report["anti_propagation_count"] == 0


# --------------------------------------------------------------------------
# Part I vs Part II overlay status vocabulary (plan §4)
# --------------------------------------------------------------------------

def _interior_separating_certificate():
    system = _chain(C5, (("x0", 1.0), ("x4", 0.0)))
    cochains = (np.array([1., 1., 1., 1., 0.]), np.array([1., 0., 0., 0., 0.]))
    discovery = discover_conditions(cochains, C5)
    branches = _branches(system, cochains, C5, discovery)
    return interior_decisiveness(
        discovery=discovery, branches=branches,
        cochains=cochains, coordinate_ids=C5,
    )


def _pivot_only_certificate():
    system = _chain(C4, (("x0", 1.0), ("x3", 0.0)))
    cochains = (np.array([1., 1., 0., 0.]), np.array([1., 0., 1., 0.]))
    discovery = discover_conditions(cochains, C4)
    branches = _branches(system, cochains, C4, discovery)
    return interior_decisiveness(
        discovery=discovery, branches=branches,
        cochains=cochains, coordinate_ids=C4,
    )


def test_part1_vocabulary_is_disjoint_and_never_claims_a_finding():
    assert set(G8_PART1_OVERLAY_STATUSES).isdisjoint(G8_PART2_OVERLAY_STATUSES)
    for status in G8_PART1_OVERLAY_STATUSES:
        assert "SEPARATING" not in status
        assert "INTERIOR" not in status
        assert status.startswith("VERIFIED_PRECOMPUTED")


def test_part1_overlay_status_is_verified_precomputed_for_any_outcome():
    # Whatever the certificate says -- interior-certifying or pivot-only --
    # a Part I overlay stamps the precomputed-verification vocabulary.
    for certificate in (
        _interior_separating_certificate(), _pivot_only_certificate(),
    ):
        status = overlay_status(
            graphlog_g8.G8_PART_VERIFICATION,
            conditioned=True,
            certificate=certificate,
        )
        assert status == "VERIFIED_PRECOMPUTED"
        assert status in G8_PART1_OVERLAY_STATUSES
    passthrough = overlay_status(
        graphlog_g8.G8_PART_VERIFICATION, conditioned=False,
    )
    assert passthrough == "VERIFIED_PRECOMPUTED_PASSTHROUGH"


def test_part2_overlay_status_uses_measurement_vocabulary():
    assert overlay_status(
        graphlog_g8.G8_PART_TEST,
        conditioned=True,
        certificate=_interior_separating_certificate(),
    ) == "INTERIOR_SEPARATING"
    assert overlay_status(
        graphlog_g8.G8_PART_TEST,
        conditioned=True,
        certificate=_pivot_only_certificate(),
    ) == "SEPARATING_PIVOT_ONLY"
    assert overlay_status(
        graphlog_g8.G8_PART_TEST, conditioned=False,
    ) == "NO_CONDITIONAL_LAYER"
    with pytest.raises(ValueError, match="unknown G8 part"):
        overlay_status("g9", conditioned=False)


def test_part_adapters_exist_and_match_the_harness_pinning_map():
    for part, qualname in graphlog_g8.G8_EXECUTOR_QUALNAMES.items():
        adapter = getattr(graphlog_g8_executor, qualname)
        assert callable(adapter)
        assert adapter.__qualname__ == qualname
    assert set(graphlog_g8.G8_EXECUTOR_QUALNAMES) == set(graphlog_g8.G8_PARTS)
    # No part-less adapter exists to bypass the vocabulary threading.
    assert not hasattr(graphlog_g8_executor, "execute_phase")


# --------------------------------------------------------------------------
# Single-artifact secondary metrics (plan §5)
# --------------------------------------------------------------------------

def test_secondary_metrics_surface_hedge_max_and_anti_propagation():
    certificate = _pivot_only_certificate()
    cochains = (np.array([1., 1., 0., 0.]), np.array([1., 0., 1., 0.]))
    # Unconditioned shared field with a large pointwise excursion on an
    # agreeing coordinate hidden under a small mean (the sealed rule_2
    # pattern: max 1.10 under a passing 0.016 mean).
    shared_field = np.array([1.0, 0.5, 0.5, 1.1])
    hedge = hedge_localization(shared_field, cochains, (1, 2))
    assert hedge["max_absolute_error"] == pytest.approx(1.1)
    report = secondary_metrics(certificate, hedge)
    assert report["hedge_max_off_scope_error"] == pytest.approx(1.1)
    assert report["hedge_mean_off_scope_error"] == \
        pytest.approx(hedge["mean_absolute_error"])
    assert report["hedge_metrics_source"] == HEDGE_CARRYOVER_SOURCE
    assert report["anti_propagation_count"] == 1
    assert report["interior_separated_pair_count"] == 0
    (margin,) = report["per_pair_best_interior_margins"]
    assert margin is not None and margin <= 0.0


def test_secondary_metrics_without_hedge_record_are_explicitly_null():
    certificate = _interior_separating_certificate()
    report = secondary_metrics(certificate)
    assert report["hedge_max_off_scope_error"] is None
    assert report["hedge_mean_off_scope_error"] is None
    assert report["hedge_metrics_source"] == HEDGE_CARRYOVER_SOURCE
    assert report["interior_separated_pair_count"] == 1
    (margin,) = report["per_pair_best_interior_margins"]
    assert margin > 0.0


# --------------------------------------------------------------------------
# Harness: disabled gate, receipt separation, manifest loaders
# --------------------------------------------------------------------------

def _dummy_amendment(**overrides):
    base = dict(
        manifest_id="sha256:" + "0" * 64,
        amendment_path=Path("results/graphlog-certified/g8-validation-amendment.json"),
        study_manifest_id="sha256:" + "1" * 64,
        parent_amendment_id=None,
        harness_commit="a" * 40,
        harness_tree="b" * 40,
        implementation_files=(),
        execution_enabled=False,
        executor_file=None,
        executor_qualname=None,
    )
    base.update(overrides)
    return graphlog_g8.G8Amendment(**base)


def _dummy_study(**overrides):
    base = dict(
        manifest_id="sha256:" + "1" * 64,
        manifest_path=Path("results/graphlog-certified/g8-validation-manifest.json"),
        part=graphlog_g8.G8_PART_TEST,
        output_root=Path("results/graphlog-certified/g8"),
        freeze_commit="a" * 40,
        freeze_tree="b" * 40,
        baseline_manifest_id="sha256:" + "2" * 64,
        spec_digest="deadbeef",
        phases=(),
        draws=(),
        g5_runs=(),
    )
    base.update(overrides)
    return graphlog_g8.G8Study(**base)


def test_g8_execution_gate_is_disabled(tmp_path):
    study = _dummy_study()
    amendment = _dummy_amendment(execution_enabled=False)
    with pytest.raises(graphlog_g8.G8PreflightError, match="disabled"):
        graphlog_g8.execute_study(study, amendment, lambda *args: {}, root=tmp_path)


def test_execute_study_refuses_cross_part_executor(tmp_path):
    # A Part II study pinned to the Part I adapter (or vice versa) must be
    # refused before any output is created: the status vocabulary is bound
    # to the adapter, so this check is what makes the vocabulary structural.
    study = _dummy_study(part=graphlog_g8.G8_PART_TEST)
    wrong = _dummy_amendment(
        execution_enabled=True,
        executor_file="src/relweblearner/bench/graphlog_g8_executor.py",
        executor_qualname="execute_phase_verification",
    )
    with pytest.raises(graphlog_g8.G8PreflightError, match="part"):
        graphlog_g8.execute_study(
            study, wrong, graphlog_g8_executor.execute_phase_verification,
            root=tmp_path, verify_repository=False,
        )
    # With the matching adapter the part gate passes; the run is then
    # stopped by a later check (the executor source is outside tmp root),
    # proving the refusal above was the part pairing, not something else.
    right = _dummy_amendment(
        execution_enabled=True,
        executor_file="src/relweblearner/bench/graphlog_g8_executor.py",
        executor_qualname="execute_phase_test",
    )
    with pytest.raises(graphlog_g8.G8PreflightError, match="outside"):
        graphlog_g8.execute_study(
            study, right, graphlog_g8_executor.execute_phase_test,
            root=tmp_path, verify_repository=False,
        )
    assert not any(tmp_path.iterdir())


def test_g8_receipt_schema_is_g8_only(tmp_path):
    draw = graphlog_g8.G8Draw(0, "rule_1", "ab" * 32, 7)
    (tmp_path / "artifact.json").write_text("{}\n", encoding="utf-8")
    receipt = g8_receipt(
        graphlog_g8.G8Phase.STRUCTURAL, draw, tmp_path, status="PASS",
    )
    validated = graphlog_g8._validate_receipt(
        receipt, graphlog_g8.G8Phase.STRUCTURAL, draw,
    )
    assert validated["schema_version"] == graphlog_g8.G8_RECEIPT_SCHEMA
    # The G7 receipt validator must reject a G8-stamped receipt.
    with pytest.raises(ValueError, match="schema"):
        graphlog_g7._validate_receipt(
            receipt, graphlog_g8.G8Phase.STRUCTURAL, draw,
        )
    with pytest.raises(ValueError, match="schema"):
        graphlog_g6._validate_receipt(
            receipt, graphlog_g8.G8Phase.STRUCTURAL, draw,
        )


def test_g8_manifest_loader_fails_cleanly_when_absent(tmp_path):
    with pytest.raises(graphlog_g8.G8PreflightError, match="absent"):
        graphlog_g8.load_study_manifest(tmp_path / "nonexistent-manifest.json")
    with pytest.raises(graphlog_g8.G8PreflightError, match="absent"):
        graphlog_g8.load_amendment(tmp_path / "nonexistent-amendment.json")


def test_g8_manifest_loader_rejects_mismatched_schema(tmp_path):
    body = {
        "schema_version": "graphlog-certified-not-g8/v1",
        "part": graphlog_g8.G8_PART_TEST,
    }
    document = {"manifest_id": f"sha256:{canonical_digest(body)}", **body}
    path = tmp_path / "g8-validation-manifest.json"
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    with pytest.raises(graphlog_g8.G8PreflightError, match="schema"):
        graphlog_g8.load_study_manifest(path)


def test_g8_manifest_paths_and_two_part_roots_are_declared():
    assert graphlog_g8.G8_MANIFEST == Path(
        "results/graphlog-certified/g8-validation-manifest.json"
    )
    assert graphlog_g8.G8_AMENDMENT == Path(
        "results/graphlog-certified/g8-validation-amendment.json"
    )
    assert graphlog_g8.G8_OUTPUT_ROOTS[graphlog_g8.G8_PART_VERIFICATION] == Path(
        "results/graphlog-certified/g8-verification"
    )
    assert graphlog_g8.G8_OUTPUT_ROOTS[graphlog_g8.G8_PART_TEST] == Path(
        "results/graphlog-certified/g8"
    )
    assert graphlog_g8.G8_RECEIPT_SCHEMA == "graphlog-certified-g8-receipt/v1"
    assert graphlog_g8.G8_HARNESS_VERSION == "graphlog-certified-g8-harness/v1"
