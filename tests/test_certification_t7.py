"""Core T7 hardening, perturbation, six-premise, and ledger tests."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from relweblearner.certification.ledger import (
    CommitmentLedger,
    LedgerEventKind,
    feedback_provenance,
    replay_ledger,
)
from relweblearner.certification.provenance import (
    NormalizedProvenance,
    ObservationRef,
    ProvenanceKind,
    normalize_provenance,
)
from relweblearner.certification.t5 import (
    BoundarySpec,
    Linearization,
    SolverConfig,
    assemble_coboundary,
    bound_spectrum,
    certify_kernel,
    partition_dirichlet,
    residual_block_from_rational,
    solve_dirichlet,
)
from relweblearner.certification.t6 import (
    DerivationDAG,
    DerivationNode,
    EnrichedOperation,
    ExactOperation,
    ExactType,
    FieldComparison,
    LeafReaderContract,
    LocalComparisonContract,
    MetricCarrier,
    NodeKind,
    Tube,
    build_comparison_package,
    propagate_budget,
)
from relweblearner.certification.t7 import (
    CommitmentOutcome,
    HardenerSpec,
    PerturbationTerm,
    PremiseId,
    bound_boundary_perturbation,
    bound_operator_perturbation,
    certify_commitment,
    mutual_argmax_contains,
    mutual_argmax_margin,
    propagate_perturbation,
)
from relweblearner.certification.types import (
    NormId,
    TargetCardinality,
    canonical_bytes,
    canonical_data,
    canonical_digest,
)


def _ref(index: int, view: str = "A") -> ObservationRef:
    return ObservationRef(
        "fixture/v1", "t7", "train", "train:000000", index, view
    )


HARDENER = HardenerSpec("mutual/v1", 0.5, NormId.SUP, "mutual-argmax")


def _margin(matrix: np.ndarray | None = None):
    return mutual_argmax_margin(
        target_id="pair:0:0",
        references=(("reference", np.eye(2) if matrix is None else matrix),),
        row_index=0,
        column_index=0,
        spec=HARDENER,
    )


def _t6_fixture(*, field_error: float = 0.0, tube_radius: float = 1.0):
    provenance = normalize_provenance((_ref(0),))
    dag = DerivationDAG(
        "identity-reader",
        (
            DerivationNode(
                "leaf", NodeKind.LEAF, "scalar", (), None, "reader", "x",
                provenance,
            ),
            DerivationNode(
                "root", NodeKind.OPERATION, "scalar", ("leaf",), "identity",
                None, None, provenance,
            ),
        ),
        "root",
    )
    contract = LocalComparisonContract(
        "identity", "finite/v1", 0.0, 0.0, "analytic/v1", (1.0,),
        Tube("encoded-ball", (tube_radius,)), 1, True, True,
    )
    package = build_comparison_package(
        version="fixture/v1",
        required_operation_ids=("identity",),
        exact_types=(ExactType("scalar", "indicator/v1", ("0", "1")),),
        carriers=(MetricCarrier("scalar", "R", 1, NormId.EUCLIDEAN),),
        exact_operations=(ExactOperation(
            "identity", "exact/v1", ("scalar",), "scalar", ("tuple",), "union",
        ),),
        enriched_operations=(EnrichedOperation(
            "identity", "enriched/v1", ("R",), "R", "equivariant",
        ),),
        local_contracts=(contract,),
        leaf_contracts=(LeafReaderContract(
            "reader", "scalar", "R", 1.0, 0.0, "preserve-source",
        ),),
    )
    comparison = FieldComparison(
        "extension", 0.0, 0.0, 0.0, 0.0, 0.0,
        field_error, None, True,
    )
    certificate = propagate_budget(
        dag=dag,
        extension_id="extension",
        package=package,
        field_comparison=comparison,
    )
    return dag, certificate


def _perturbation(*, field_radius: float = 0.0, tube_radius: float = 1.0):
    dag, t6 = _t6_fixture(field_error=0.0, tube_radius=tube_radius)
    perturbation = propagate_perturbation(
        dag=dag,
        t6_certificate=t6,
        terms=(PerturbationTerm(
            "solver", "solver", field_radius, True, "field", "CERTIFIED",
        ),),
        leaf_field_constants={"reader": 1.0},
    )
    return dag, t6, perturbation


def _stable(**overrides):
    _dag, t6, perturbation = _perturbation()
    values = dict(
        version="t7/v1",
        target_id="pair:0:0",
        target_verdict=TargetCardinality.IDENTICAL,
        policy_permitted=True,
        policy_evidence="policy",
        t5_certified=True,
        t5_evidence="t5",
        t6_certified=True,
        separation_certified=True,
        t6_evidence=t6,
        approximation_budget=0.0,
        margin=_margin(),
        perturbation=perturbation,
        provenance=normalize_provenance((_ref(0), _ref(1, "B"))),
        model_versions=(("model", "v1"),),
    )
    values.update(overrides)
    return certify_commitment(**values)


def test_mutual_argmax_margin_covers_threshold_row_column_and_ties():
    exact = _margin()
    assert exact.uniform_margin == 0.5
    assert exact.all_references_inside
    assert mutual_argmax_contains(np.eye(2), 0, 0, HARDENER)

    threshold = _margin(np.asarray([[0.5001, 0.0], [0.0, 1.0]]))
    assert threshold.uniform_margin == pytest.approx(0.0001)
    row_near = _margin(np.asarray([[1.0, 0.98], [0.0, 1.0]]))
    assert row_near.uniform_margin == pytest.approx(0.01)
    column_near = _margin(np.asarray([[1.0, 0.0], [0.99, 1.0]]))
    assert column_near.uniform_margin == pytest.approx(0.005)

    row_tie = np.asarray([[1.0, 1.0], [0.0, 0.0]])
    assert _margin(row_tie).uniform_margin == 0.0
    assert not mutual_argmax_contains(row_tie, 0, 0, HARDENER)
    # Reversing competitor order cannot turn the exact tie into a commit.
    assert not mutual_argmax_contains(row_tie[:, ::-1], 0, 1, HARDENER)


def test_boundary_and_operator_perturbations_refuse_changed_structure():
    boundary = bound_boundary_perturbation(
        boundary_change=np.asarray([3.0, 4.0]),
        kappa_boundary_upper=2.0,
        expected_dimension=2,
    )
    assert boundary.valid
    assert boundary.field_radius == pytest.approx(5.0 * np.sqrt(5.0))
    changed = bound_boundary_perturbation(
        boundary_change=np.asarray([0.0]), kappa_boundary_upper=1.0,
        expected_dimension=1, scope_preserved=False,
    )
    assert not changed.valid and changed.field_radius is None

    block = residual_block_from_rational("edge", ((-1, 1),))
    system = partition_dirichlet(
        assemble_coboundary(Linearization(("b", "u"), (block,))),
        BoundarySpec((("b", 1.0),)),
    )
    spectrum = bound_spectrum(system, certify_kernel(system))
    zero = bound_operator_perturbation(
        system=system, spectrum=spectrum,
        h_matrix=np.zeros((1, 1)), g_vector=np.zeros(1),
        base_interior=np.ones(1),
    )
    assert zero.valid and zero.field_radius == 0.0
    neumann_failure = bound_operator_perturbation(
        system=system, spectrum=spectrum,
        h_matrix=np.asarray([[-2.0]]), g_vector=np.zeros(1),
        base_interior=np.ones(1),
    )
    assert not neumann_failure.valid
    dimension_failure = bound_operator_perturbation(
        system=system, spectrum=spectrum,
        h_matrix=np.zeros((2, 2)), g_vector=np.zeros(2),
        base_interior=np.ones(2),
    )
    assert not dimension_failure.valid


def test_joint_tube_fails_when_separate_E_and_R_radii_each_fit():
    dag, t6 = _t6_fixture(field_error=0.4, tube_radius=0.6)
    assert t6.admissible
    perturbation = propagate_perturbation(
        dag=dag,
        t6_certificate=t6,
        terms=(PerturbationTerm(
            "solver", "solver", 0.3, True, "field", "CERTIFIED",
        ),),
        leaf_field_constants={"reader": 1.0},
    )
    assert not perturbation.valid
    assert not perturbation.joint_tubes_satisfied
    assert any("joint T6 tube" in reason for reason in perturbation.rejection_reasons)
    leaf = perturbation.node_perturbations[0]
    assert leaf.approximation_budget == 0.4
    assert leaf.perturbation_radius == 0.3
    assert leaf.joint_radius == 0.7


@pytest.mark.parametrize(
    "override",
    (
        {"target_verdict": TargetCardinality.MANY},
        {"policy_permitted": False},
        {"t5_certified": False},
        {"margin": _margin(np.asarray([[1.0, 1.0], [0.0, 0.0]]))},
        {"perturbation": None},
        {"approximation_budget": 0.5},
    ),
)
def test_removing_each_t7_premise_forces_abstention(override):
    certificate = _stable(**override)
    assert certificate.outcome is CommitmentOutcome.ABSTAIN
    assert not certificate.premises or any(
        not premise.satisfied for premise in certificate.premises
    )


def test_structural_branches_precede_metric_hardening():
    assert _stable().outcome is CommitmentOutcome.COMMIT
    assert len(_stable().premises) == len(PremiseId) == 6
    empty = _stable(target_verdict=TargetCardinality.EMPTY)
    assert empty.outcome is CommitmentOutcome.REJECT
    assert len(empty.premises) == 6
    distinct = _stable(target_verdict=TargetCardinality.DISTINCT)
    assert distinct.outcome is CommitmentOutcome.EXCLUSION
    assert distinct.commitment == "DISTINCT"
    assert len(distinct.premises) == 6
    assert _stable(target_verdict=TargetCardinality.MANY).outcome \
        is CommitmentOutcome.ABSTAIN
    assert _stable(target_verdict=TargetCardinality.UNKNOWN).outcome \
        is CommitmentOutcome.ABSTAIN


def test_duplicate_perturbation_term_and_evaluation_gold_provenance_refuse():
    dag, t6 = _t6_fixture()
    duplicate = PerturbationTerm(
        "same", "solver", 0.0, True, "field", "CERTIFIED"
    )
    perturbation = propagate_perturbation(
        dag=dag, t6_certificate=t6, terms=(duplicate, duplicate)
    )
    assert not perturbation.valid and not perturbation.terms_counted_once

    invalid = NormalizedProvenance(
        observations=(ProvenanceKind.EVALUATION_GOLD,),  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError, match="ObservationRef"):
        _stable(provenance=invalid)


def test_commitment_and_ledger_refuse_missing_observation_provenance():
    empty = NormalizedProvenance()
    refused = _stable(provenance=empty)
    assert refused.outcome is CommitmentOutcome.ABSTAIN
    assert refused.code == "ABSTAIN_POLICY_PERMIT"
    assert not next(
        premise for premise in refused.premises
        if premise.premise_id is PremiseId.POLICY_PERMIT
    ).satisfied

    forged = replace(_stable(), provenance=empty)
    with pytest.raises(ValueError, match="observation provenance"):
        CommitmentLedger().append_certificate(forged)


def test_ledger_retraction_replay_and_feedback_preserve_exact_sources():
    first = _stable()
    ledger = CommitmentLedger().append_certificate(first)
    first_event = ledger.events[-1]
    second = replace(first, target_id="pair:1:1")
    ledger = ledger.append_certificate(
        second, depends_on_event_ids=(first_event.event_id,)
    )
    assert len(ledger.state.live_events) == 2

    feedback = feedback_provenance(first, parent_event_id=first_event.event_id)
    assert feedback.origin_ids == first.provenance.origin_ids
    assert len(feedback.observations) == len(first.provenance.observations)

    removed_id = canonical_digest(_ref(0))
    retracted = ledger.retract_observations((removed_id,))
    assert retracted.state.live_events == ()
    retract_events = tuple(
        event for event in retracted.events
        if event.body.kind is LedgerEventKind.RETRACT
    )
    assert len(retract_events) == 2
    replayed = replay_ledger(retracted.events)
    assert canonical_bytes(replayed.live_commitments) == canonical_bytes(
        retracted.state.live_commitments
    )
    canonical_data(retracted)
