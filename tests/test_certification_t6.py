"""Core T6 comparison, DAG budget, and separation certificate tests."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from relweblearner.certification.provenance import (
    ObservationRef,
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
    BehaviorInstance,
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
    SeparationStatus,
    Tube,
    build_comparison_package,
    check_separation,
    compare_field,
    compute_local_defect,
    compute_local_defects,
    eval_enriched,
    eval_exact,
    propagate_budget,
    verify_leaf_bounds,
    verify_lipschitz,
)
from relweblearner.certification.types import NormId, canonical_data


def _ref(index: int) -> ObservationRef:
    return ObservationRef(
        "fixture/v1", "t6", "train", "train:000000", index, "A"
    )


def _package(*, tube_radius: float = 10.0, include_enriched: bool = True):
    exact = ExactOperation(
        "add", "add-exact/v1", ("scalar", "scalar"), "scalar", ("all",), "union"
    )
    enriched = EnrichedOperation(
        "add", "add-enriched/v1", ("R", "R"), "R", "permutation-equivariant"
    )
    contract = LocalComparisonContract(
        operation_id="add",
        defect_method="finite-exhaustion/v1",
        declared_epsilon=0.1,
        measured_max_defect=0.0,
        lipschitz_method="analytic-addition/v1",
        lipschitz_constants=(1.0, 1.0),
        tube=Tube("encoded-exact-child-balls/v1", (tube_radius, tube_radius)),
        legal_tuple_count=4,
        defect_verified=True,
        lipschitz_verified=True,
    )
    return build_comparison_package(
        version="fixture/v1",
        required_operation_ids=("add",),
        exact_types=(ExactType("scalar", "indicator/v1", ("0", "1", "2")),),
        carriers=(MetricCarrier("scalar", "R", 1, NormId.EUCLIDEAN),),
        exact_operations=(exact,),
        enriched_operations=(enriched,) if include_enriched else (),
        local_contracts=(contract,),
        leaf_contracts=(
            LeafReaderContract("read", "scalar", "R", 1.0, 0.0, "source-union"),
        ),
    )


def _dag(*, preserve_sources: bool = True) -> DerivationDAG:
    p0 = normalize_provenance((_ref(0),))
    p1 = normalize_provenance((_ref(1),))
    combined = normalize_provenance((_ref(0), _ref(1)))
    broken = normalize_provenance((_ref(0),))
    return DerivationDAG(
        "shared-add/v1",
        (
            DerivationNode("a", NodeKind.LEAF, "scalar", (), None, "read", "a", p0),
            DerivationNode("b", NodeKind.LEAF, "scalar", (), None, "read", "b", p1),
            DerivationNode(
                "sum", NodeKind.OPERATION, "scalar", ("a", "b"), "add", None,
                None, combined,
            ),
            DerivationNode(
                "root", NodeKind.OPERATION, "scalar", ("sum", "sum"), "add",
                None, None, combined if preserve_sources else broken,
            ),
        ),
        "root",
    )


def _field_comparison(error: float = 0.2) -> FieldComparison:
    return FieldComparison("extension", 0.0, 0.0, 0.0, 0.0, 0.0, error, None, True)


def test_missing_operation_is_rejection_not_a_large_local_defect():
    package = _package(include_enriched=False)
    assert not package.admissible
    assert package.coverage[0].exact_present
    assert not package.coverage[0].enriched_present
    assert package.rejection_reasons == ("missing comparison coverage: add",)


def test_finite_local_square_and_independent_lipschitz_checks():
    legal = ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0))
    encoder = lambda value: np.asarray([value], dtype=float)
    exact_add = lambda values: values[0] + values[1]
    enriched_add = lambda values: values[0] + values[1]
    defect = compute_local_defect(
        legal_tuples=legal,
        exact_apply=exact_add,
        enriched_apply=enriched_add,
        input_encoders=(encoder, encoder),
        output_encoder=encoder,
        output_norm=NormId.EUCLIDEAN,
    )
    assert defect == 0.0
    assert compute_local_defects(
        legal_tuples=legal,
        exact_apply=exact_add,
        enriched_apply=enriched_add,
        input_encoders=(encoder, encoder),
        output_encoder=encoder,
        output_norm=NormId.EUCLIDEAN,
    ) == defect
    samples = ((
        (np.asarray([0.2]), np.asarray([-0.4])),
        (np.asarray([0.7]), np.asarray([0.9])),
    ),)
    assert verify_lipschitz(
        samples=samples,
        enriched_apply=enriched_add,
        constants=(1.0, 1.0),
        input_norms=(NormId.EUCLIDEAN, NormId.EUCLIDEAN),
        output_norm=NormId.EUCLIDEAN,
    )
    assert not verify_lipschitz(
        samples=samples,
        enriched_apply=enriched_add,
        constants=(0.1, 0.1),
        input_norms=(NormId.EUCLIDEAN, NormId.EUCLIDEAN),
        output_norm=NormId.EUCLIDEAN,
    )
    leaf = verify_leaf_bounds(
        contract=LeafReaderContract(
            "reader", "scalar", "R", 1.0, 0.1, "source-union"
        ),
        field_error_bound=0.2,
        samples=((np.asarray([0.25]), np.asarray([0.0])),),
        norm=NormId.EUCLIDEAN,
    )
    assert leaf.declared_bound == 0.30000000000000004
    assert leaf.measured_max_error == 0.25 and leaf.verified
    canonical_data(leaf)


def test_shared_dag_evaluation_and_recursive_budget_match_manual_calculation():
    dag = _dag()
    exact = eval_exact(
        dag, leaf_values={"a": 1.0, "b": 2.0},
        operations={"add": lambda values: values[0] + values[1]},
    )
    enriched = eval_enriched(
        dag,
        leaf_values={"a": np.asarray([1.0]), "b": np.asarray([2.0])},
        operations={"add": lambda values: values[0] + values[1]},
    )
    assert exact["sum"] == 3.0 and exact["root"] == 6.0
    np.testing.assert_array_equal(enriched["root"], [6.0])
    certificate = propagate_budget(
        dag=dag,
        extension_id="extension",
        package=_package(),
        field_comparison=_field_comparison(),
        exact_values=exact,
        enriched_values=enriched,
        encoders={"scalar": lambda value: np.asarray([value])},
        norms={"scalar": NormId.EUCLIDEAN},
    )
    by_node = {item.node_id: item for item in certificate.node_budgets}
    assert by_node["a"].budget == 0.2
    assert by_node["sum"].budget == 0.5
    assert by_node["root"].budget == 1.1
    assert certificate.root_observed_error == 0.0
    assert certificate.admissible
    canonical_data(certificate)


def test_tube_and_source_preservation_fail_closed_with_serializable_reasons():
    tube_failure = propagate_budget(
        dag=_dag(), extension_id="extension", package=_package(tube_radius=0.1),
        field_comparison=_field_comparison(),
    )
    assert not tube_failure.admissible and not tube_failure.tubes_satisfied
    assert any("tube exceeded" in reason for reason in tube_failure.rejection_reasons)
    canonical_data(tube_failure)

    source_failure = propagate_budget(
        dag=_dag(preserve_sources=False), extension_id="extension",
        package=_package(), field_comparison=_field_comparison(),
    )
    assert not source_failure.admissible
    assert not source_failure.source_preservation_verified


def test_harmonic_field_comparison_exact_bridge_and_boundary_mismatch():
    block = residual_block_from_rational("edge", ((-1, 1),), weight=Fraction(1))
    coboundary = assemble_coboundary(Linearization(("x", "y"), (block,)))
    system = partition_dirichlet(coboundary, BoundarySpec((("x", 1.0),)))
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, _solver = solve_dirichlet(
        system, SolverConfig(field_tolerance=1e-12), kernel=kernel, spectrum=spectrum
    )
    assert field is not None
    exact = compare_field(
        extension_id="same", system=system, spectrum=spectrum,
        exact_cochain=np.asarray([1.0, 1.0]), field=field,
    )
    assert exact.boundary_mismatch == exact.naturality_defect == 0.0
    assert exact.field_error_bound == exact.actual_field_error == 0.0
    assert exact.verified

    mismatch = compare_field(
        extension_id="different", system=system, spectrum=spectrum,
        exact_cochain=np.asarray([0.0, 0.0]),
    )
    assert mismatch.boundary_mismatch == 1.0
    assert mismatch.naturality_defect == 0.0
    assert mismatch.field_error_bound >= 1.0

    naturality = compare_field(
        extension_id="non-natural", system=system, spectrum=spectrum,
        exact_cochain=np.asarray([1.0, 0.0]),
    )
    assert naturality.boundary_mismatch == 0.0
    assert naturality.naturality_defect == 1.0
    assert naturality.beta == naturality.kappa_delta_upper


def _behavior(
    extension: str, behavior: str, output: tuple[float, ...], budget: float
) -> BehaviorInstance:
    return BehaviorInstance(
        extension,
        (("d", behavior),),
        (("d", output),),
        (("d", budget),),
    )


def test_separation_distinguishes_success_literal_collision_and_consumed_margin():
    separated = check_separation((
        _behavior("a", "left", (1.0, 0.0), 0.1),
        _behavior("b", "right", (0.0, 1.0), 0.1),
    ))
    assert separated.status is SeparationStatus.SEPARATING
    assert separated.compared_pairs[0].remaining_margin == 0.8

    collision = check_separation((
        _behavior("a", "left", (0.0, 0.0), 0.0),
        _behavior("b", "right", (0.0, 0.0), 0.0),
    ))
    assert collision.status is SeparationStatus.LITERAL_COLLISION
    assert collision.compared_pairs[0].literal_collision

    consumed = check_separation((
        _behavior("a", "left", (1.0, 0.0), 0.6),
        _behavior("b", "right", (0.0, 1.0), 0.6),
    ))
    assert consumed.status is SeparationStatus.BUDGET_CONSUMED
    assert not consumed.compared_pairs[0].literal_collision

    insufficient = check_separation((_behavior("a", "only", (1.0,), 0.1),))
    assert insufficient.status is SeparationStatus.INSUFFICIENT_BEHAVIORS
    assert insufficient.separating  # vacuous over pairs, not a capacity datum

    missing_budget = check_separation((
        _behavior("a", "left", (1.0, 0.0), 0.1),
        BehaviorInstance("b", (("d", "right"),), (("d", (0.0, 1.0)),), ()),
    ))
    assert missing_budget.status is SeparationStatus.UNCERTIFIED_BUDGET
