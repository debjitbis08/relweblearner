"""G2 GraphLog commutator and anchor-boundary theorem instance tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from relweblearner.bench.graphlog_certified.ingest import (
    OpaqueToken,
    TypedAnchor,
    ingest_world,
    select_anchors,
)
from relweblearner.bench.graphlog_certified.linearization import (
    BoundaryKind,
    build_anchor_boundary,
    build_role_linearization,
    encode_extension,
    field_matrix,
)
from relweblearner.bench.graphlog_certified.model import (
    IdentityExtension,
    ObservationFamily,
    TriangleFact,
    build_observations,
    build_scope,
    classify_extensions,
    triangle_components,
)
from relweblearner.certification.provenance import ObservationRef, normalize_provenance
from relweblearner.certification.t5 import (
    KernelStatus,
    SolverConfig,
    SolverStatus,
    SpectralStatus,
    assemble_coboundary,
    bound_spectrum,
    certify_kernel,
    partition_dirichlet,
    solve_dirichlet,
    validate_linearization,
)


ROOT = Path(__file__).resolve().parents[1]


def _token(view: str, name: str) -> OpaqueToken:
    return OpaqueToken(view, name)


def _ref(view: str, index: int) -> ObservationRef:
    return ObservationRef(
        "graphlog/test", "g2-fixture", "train", "train:000000", index, view
    )


def _triangle(
    view: str, names: tuple[str, str, str], offset: int, support: int = 3
) -> TriangleFact:
    return TriangleFact(
        tuple(_token(view, name) for name in names),  # type: ignore[arg-type]
        support,
        normalize_provenance(_ref(view, offset + i) for i in range(3)),
    )


def _anchor(a: str, b: str, index: int) -> TypedAnchor:
    return TypedAnchor(
        _token("A", a),
        _token("B", b),
        normalize_provenance((_ref("A", index), _ref("B", index))),
    )


def _family(
    *,
    anchors: tuple[TypedAnchor, ...] | None = None,
    a_support: int = 3,
    b_support: int = 3,
    prefix: str = "",
) -> ObservationFamily:
    a_names = tuple(f"{prefix}{name}" for name in ("a1", "a2", "a3"))
    b_names = tuple(f"{prefix}{name}" for name in ("b1", "b2", "b3"))
    triangles_a = (_triangle("A", a_names, 0, a_support),)
    triangles_b = (_triangle("B", b_names, 10, b_support),)
    if anchors is None:
        anchors = (
            _anchor(a_names[0], b_names[0], 20),
            _anchor(a_names[1], b_names[1], 21),
        )
    return ObservationFamily(
        "graphlog-certified/v1",
        "graphlog/test",
        "g2-fixture",
        triangles_a,
        triangles_b,
        anchors,
        (),
        tuple(sorted({token for triangle in triangles_a for token in triangle.positions})),
        tuple(sorted({token for triangle in triangles_b for token in triangle.positions})),
    )


def test_six_ordered_role_channels_use_declared_rational_normalization():
    family = _family(a_support=3, b_support=11)
    linearization = build_role_linearization(family, build_scope(family))
    assert len(linearization.channels) == 6
    assert len(linearization.core.residual_blocks) == 6
    assert linearization.core.omitted_block_ids == ()
    assert linearization.core.cell_complex is not None
    assert len(linearization.core.cell_complex.incidences) == 12
    assert len(linearization.core.stalks) == 7
    assert len(linearization.core.restrictions) == 12
    assert len(linearization.core.edge_weights) == 6
    validate_linearization(linearization.core)
    for channel in linearization.channels:
        assert channel.retained and channel.omission_reason is None
        assert channel.a_total == 3 and channel.b_total == 11
        assert sum(map(sum, channel.adjacency_a)) == 1
        assert sum(map(sum, channel.adjacency_b)) == 1
        i, j = channel.positions
        assert channel.adjacency_a[i][j] == 1
        assert channel.adjacency_b[i][j] == 1
        assert channel.head_incidence.endswith(":head")
        assert channel.tail_incidence.endswith(":tail")


def test_true_partial_mapping_matrix_is_the_exact_extension_encoding():
    family = _family()
    scope = build_scope(family)
    linearization = build_role_linearization(family, scope)
    extension = classify_extensions(family, scope).solutions[0]
    matrix = encode_extension(extension, linearization)
    np.testing.assert_array_equal(matrix, np.eye(3))
    assert set(np.unique(matrix)) == {0.0, 1.0}
    residual = assemble_coboundary(linearization.core).dense_delta @ matrix.reshape(-1)
    np.testing.assert_array_equal(residual, np.zeros_like(residual))

    partial = IdentityExtension((extension.pairs[0],))
    partial_matrix = encode_extension(partial, linearization)
    assert partial_matrix.sum() == 1
    assert np.max(partial_matrix.sum(axis=0)) <= 1
    assert np.max(partial_matrix.sum(axis=1)) <= 1


def test_anchor_boundary_contains_only_ones_and_derived_row_column_exclusions():
    family = _family()
    linearization = build_role_linearization(family, build_scope(family))
    boundary = build_anchor_boundary(family, linearization)
    assert len(boundary.coordinates) == 8
    ones = [item for item in boundary.coordinates if item.value == 1]
    zeros = [item for item in boundary.coordinates if item.value == 0]
    assert len(ones) == 2 and len(zeros) == 6
    assert all(item.kind is BoundaryKind.ANCHOR for item in ones)
    assert all(item.kind is BoundaryKind.BIJECTION_EXCLUSION for item in zeros)
    assert all(
        any(ref.operation_id == "bijection_exclusion"
            for ref in item.provenance.derivations)
        for item in zeros
    )
    assert all(item.provenance.observations for item in boundary.coordinates)
    assert len(boundary.core.values) == 8


def test_partial_anchor_set_has_no_padding_and_leaves_all_other_coordinates_free():
    family = _family(anchors=(_anchor("a1", "b1", 20),))
    linearization = build_role_linearization(family, build_scope(family))
    boundary = build_anchor_boundary(family, linearization)
    assert len(boundary.coordinates) == 5
    assert sum(item.value for item in boundary.coordinates) == 1
    system = partition_dirichlet(assemble_coboundary(linearization.core), boundary.core)
    assert len(system.interior_indices) == 4


def test_anchored_isomorphic_web_has_unique_spd_completion_equal_to_extension():
    family = _family()
    scope = build_scope(family)
    linearization = build_role_linearization(family, scope)
    boundary = build_anchor_boundary(family, linearization)
    system = partition_dirichlet(assemble_coboundary(linearization.core), boundary.core)
    kernel = certify_kernel(system)
    field, solver = solve_dirichlet(
        system, SolverConfig(field_tolerance=1e-12), kernel=kernel
    )
    assert kernel.status is KernelStatus.UNIQUE
    assert kernel.exact_rank == kernel.interior_dimension == 1
    assert field is not None and solver.status is SolverStatus.CONVERGED
    expected = encode_extension(classify_extensions(family, scope).solutions[0], linearization)
    np.testing.assert_allclose(field_matrix(field.values, linearization), expected)
    assert field.energy == 0.0


def test_unanchored_commutator_has_uncontrolled_kernel_and_solver_refuses():
    family = _family(anchors=())
    linearization = build_role_linearization(family, build_scope(family))
    boundary = build_anchor_boundary(family, linearization)
    assert boundary.coordinates == ()
    system = partition_dirichlet(assemble_coboundary(linearization.core), boundary.core)
    kernel = certify_kernel(system)
    field, solver = solve_dirichlet(system, SolverConfig())
    assert kernel.status is KernelStatus.UNCONTROLLED_KERNEL
    assert kernel.nullity > 0
    assert field is None
    assert solver.status is SolverStatus.UNCONTROLLED_KERNEL


def test_empty_view_channels_are_omitted_and_declared_non_propagating():
    base = _family(anchors=(_anchor("a1", "b1", 20),))
    family = replace(base, triangles_b=())
    scope = build_scope(family)
    linearization = build_role_linearization(family, scope)
    assert linearization.core.residual_blocks == ()
    assert len(linearization.core.omitted_block_ids) == 6
    assert all(not channel.retained for channel in linearization.channels)
    assert all(
        channel.omission_reason == "empty-view-channel/non-propagating"
        for channel in linearization.channels
    )


def test_opaque_relabeling_is_equivariant_for_role_operator_and_energy():
    original = _family()
    renamed = _family(prefix="z")
    original_linearization = build_role_linearization(original, build_scope(original))
    renamed_linearization = build_role_linearization(renamed, build_scope(renamed))
    original_delta = assemble_coboundary(original_linearization.core)
    renamed_delta = assemble_coboundary(renamed_linearization.core)
    np.testing.assert_array_equal(original_delta.dense_delta, renamed_delta.dense_delta)
    probe = np.arange(9, dtype=float) / 8.0
    assert np.linalg.norm(original_delta.dense_delta @ probe) == np.linalg.norm(
        renamed_delta.dense_delta @ probe
    )


@pytest.mark.skipif(
    not (ROOT / "data/graphlog/graphlog_v1.1/train/rule_20/train.jsonl").exists(),
    reason="GraphLog corpus absent",
)
def test_rule20_development_operator_has_certified_unique_tolerance_field():
    base = ROOT / "data/graphlog/graphlog_v1.1/train/rule_20"
    train = [
        json.loads(line)
        for line in (base / "train.jsonl").read_text(encoding="utf-8").splitlines()[:150]
    ]
    test = [
        json.loads(line)
        for line in (base / "test.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    runtime, _evaluation_key = ingest_world(
        {"name": "rule_20", "train": train, "test": test, "rules": {}}, seed=0
    )
    pre_anchor = build_observations(runtime)
    anchors = select_anchors(
        runtime.opaque_overlap_events,
        triangle_components(pre_anchor.triangles_a),
    )
    observations = build_observations(runtime, anchors)
    scope = build_scope(observations)
    linearization = build_role_linearization(observations, scope)
    boundary = build_anchor_boundary(observations, linearization)
    system = partition_dirichlet(
        assemble_coboundary(linearization.core), boundary.core
    )
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, solver = solve_dirichlet(
        system,
        SolverConfig(field_tolerance=1e-6),
        kernel=kernel,
        spectrum=spectrum,
    )
    assert linearization.shape == (16, 16)
    assert len(system.boundary_indices) == 156
    assert len(system.interior_indices) == 100
    assert kernel.status is KernelStatus.UNIQUE and kernel.exact_rank == 100
    assert spectrum.status is SpectralStatus.CERTIFIED
    assert field is not None and solver.status is SolverStatus.CONVERGED
    assert solver.error_bound is not None and solver.error_bound <= 1e-6
