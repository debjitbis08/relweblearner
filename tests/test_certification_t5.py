"""Reusable T5 operator certificates on hand-computable finite systems."""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from relweblearner.certification.t5 import (
    BoundarySpec,
    KernelStatus,
    Linearization,
    SolverConfig,
    SolverStatus,
    SpectralStatus,
    assemble_coboundary,
    bound_spectrum,
    certify_kernel,
    partition_dirichlet,
    residual_block_from_rational,
    run_t5,
    solve_dirichlet,
)
from relweblearner.certification.types import canonical_data


def _chain_system(*, weight: Fraction = Fraction(1)):
    block = residual_block_from_rational(
        "path",
        ((-1, 1, 0, 0), (0, -1, 1, 0), (0, 0, -1, 1)),
        weight=weight,
    )
    coboundary = assemble_coboundary(
        Linearization(("x0", "x1", "x2", "x3"), (block,))
    )
    return partition_dirichlet(
        coboundary, BoundarySpec((("x0", 1.0), ("x3", 0.0)))
    )


def test_scalar_delta_laplacian_energy_and_solution_are_exactly_as_declared():
    block = residual_block_from_rational("edge", ((-1, 1),), weight=Fraction(4))
    coboundary = assemble_coboundary(Linearization(("left", "right"), (block,)))
    np.testing.assert_array_equal(coboundary.dense_delta, [[-2.0, 2.0]])
    np.testing.assert_array_equal(coboundary.laplacian, [[4.0, -4.0], [-4.0, 4.0]])

    system = partition_dirichlet(coboundary, BoundarySpec((("left", 3.0),)))
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, solver = solve_dirichlet(
        system, SolverConfig(field_tolerance=1e-12), kernel=kernel, spectrum=spectrum
    )
    assert kernel.status is KernelStatus.UNIQUE
    assert kernel.exact_rank == 1
    assert spectrum.status is SpectralStatus.CERTIFIED
    assert solver.status is SolverStatus.CONVERGED
    assert field is not None
    np.testing.assert_allclose(field.values, [3.0, 3.0], atol=1e-12)
    np.testing.assert_allclose(field.normal_residual, [0.0], atol=1e-12)
    assert field.energy == pytest.approx(0.0, abs=1e-24)
    canonical_data(kernel)
    canonical_data(spectrum)
    canonical_data(solver)


def test_orientation_and_orthogonal_coordinate_changes_preserve_energy():
    matrix = np.asarray([[1.0, 2.0], [-3.0, 1.0]])
    original = residual_block_from_rational("d", ((1, 2), (-3, 1)))
    reversed_block = residual_block_from_rational("-d", ((-1, -2), (3, -1)))
    delta = assemble_coboundary(Linearization(("x", "y"), (original,)))
    reversed_delta = assemble_coboundary(
        Linearization(("x", "y"), (reversed_block,))
    )
    np.testing.assert_allclose(delta.laplacian, reversed_delta.laplacian)

    # Signed coordinate swap is exactly orthogonal and remains rational.
    q = np.asarray([[0.0, -1.0], [1.0, 0.0]])
    transformed_matrix = matrix @ q
    transformed = residual_block_from_rational(
        "dq", tuple(tuple(int(value) for value in row) for row in transformed_matrix)
    )
    transformed_delta = assemble_coboundary(
        Linearization(("u", "v"), (transformed,))
    )
    np.testing.assert_allclose(transformed_delta.laplacian, q.T @ delta.laplacian @ q)
    x = np.asarray([0.25, -0.75])
    xp = q.T @ x
    assert np.linalg.norm(delta.dense_delta @ x) ** 2 == pytest.approx(
        np.linalg.norm(transformed_delta.dense_delta @ xp) ** 2
    )


def test_positive_weights_preserve_exact_rank_and_empty_blocks_are_recorded():
    block = residual_block_from_rational("kept", ((1, -1),), weight=Fraction(9, 4))
    coboundary = assemble_coboundary(
        Linearization(("x", "y"), (block,), ("empty-channel",))
    )
    assert coboundary.omitted_block_ids == ("empty-channel",)
    assert certify_kernel(
        partition_dirichlet(coboundary, BoundarySpec((("x", 1.0),)))
    ).exact_rank == 1
    with pytest.raises(ValueError, match="positive"):
        residual_block_from_rational("zero", ((1,),), weight=Fraction(0))


def test_singular_and_disconnected_interiors_refuse_a_model_determined_field():
    singular = residual_block_from_rational("only-boundary", ((1, 0),))
    system = partition_dirichlet(
        assemble_coboundary(Linearization(("b", "free"), (singular,))),
        BoundarySpec((("b", 2.0),)),
    )
    kernel = certify_kernel(system)
    field, solver = solve_dirichlet(system, SolverConfig())
    assert kernel.status is KernelStatus.UNCONTROLLED_KERNEL
    assert kernel.nullity == 1
    assert field is None
    assert solver.status is SolverStatus.UNCONTROLLED_KERNEL

    disconnected = residual_block_from_rational("edge", ((-1, 1, 0),))
    disconnected_system = partition_dirichlet(
        assemble_coboundary(
            Linearization(("boundary", "controlled", "island"), (disconnected,))
        ),
        BoundarySpec((("boundary", 1.0),)),
    )
    disconnected_kernel = certify_kernel(disconnected_system)
    assert disconnected_kernel.status is KernelStatus.UNCONTROLLED_KERNEL
    assert disconnected_kernel.nullity == 1
    assert sorted(component.nullity for component in disconnected_kernel.components) == [0, 1]


def test_empty_interior_is_an_explicit_zero_round_success():
    block = residual_block_from_rational("edge", ((-1, 1),))
    system = partition_dirichlet(
        assemble_coboundary(Linearization(("x", "y"), (block,))),
        BoundarySpec((("x", 2.0), ("y", -1.0))),
    )
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, solver = solve_dirichlet(system, SolverConfig())
    assert kernel.status is KernelStatus.EMPTY_INTERIOR
    assert spectrum.status is SpectralStatus.EMPTY_INTERIOR
    assert solver.status is SolverStatus.CONVERGED and solver.iterations == 0
    assert field is not None
    np.testing.assert_array_equal(field.values, [2.0, -1.0])
    assert field.energy == pytest.approx(4.5)


def test_ill_conditioned_full_rank_system_gets_conservative_spectral_bounds():
    block = residual_block_from_rational(
        "diagonal", ((1, 0), (0, Fraction(1, 10_000)))
    )
    system = partition_dirichlet(
        assemble_coboundary(Linearization(("x", "y"), (block,))), BoundarySpec()
    )
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    actual = np.linalg.eigvalsh(system.laplacian_uu)
    assert kernel.status is KernelStatus.UNIQUE
    assert spectrum.status is SpectralStatus.CERTIFIED
    assert spectrum.lower_bound is not None and spectrum.lower_bound <= actual[0]
    assert spectrum.upper_bound is not None and spectrum.upper_bound >= actual[-1]
    assert spectrum.condition_upper_bound is not None
    assert spectrum.condition_upper_bound > 99_000_000


@pytest.mark.parametrize(
    ("initialization", "initial_values"),
    (("zero", None), ("uniform", None), ("provided", (0.2, -1.0))),
)
def test_local_gradient_solver_matches_direct_oracle_from_multiple_starts(
    initialization: str, initial_values: tuple[float, ...] | None,
):
    system = _chain_system()
    field, solver = solve_dirichlet(
        system,
        SolverConfig(
            field_tolerance=1e-10,
            initialization=initialization,
            initial_values=initial_values,
        ),
    )
    oracle = np.linalg.solve(system.laplacian_uu, -system.forcing)
    assert field is not None and solver.status is SolverStatus.CONVERGED
    np.testing.assert_allclose(
        field.values[list(system.interior_indices)], oracle, atol=1e-10
    )
    assert solver.error_bound is not None and solver.error_bound <= 1e-10
    assert solver.geometric_round_bound is not None
    assert solver.iterations <= solver.geometric_round_bound


def test_one_gradient_round_propagates_only_to_operator_neighbors():
    system = _chain_system()
    field, solver = solve_dirichlet(
        system,
        SolverConfig(max_iterations=1, field_tolerance=1e-15, record_trace=True),
    )
    assert field is not None and solver.status is SolverStatus.MAX_ITERATIONS
    assert len(field.interior_trace) == 2
    initial, after_one = field.interior_trace
    np.testing.assert_array_equal(initial, [0.0, 0.0])
    assert after_one[0] > 0.0
    assert after_one[1] == 0.0


def test_boundary_changes_affect_only_the_forcing_and_expected_solution():
    system = _chain_system()
    mirrored = partition_dirichlet(
        system.coboundary, BoundarySpec((("x0", 0.0), ("x3", 1.0)))
    )
    np.testing.assert_allclose(system.laplacian_uu, mirrored.laplacian_uu)
    left, _ = solve_dirichlet(system, SolverConfig(field_tolerance=1e-10))
    right, _ = solve_dirichlet(mirrored, SolverConfig(field_tolerance=1e-10))
    assert left is not None and right is not None
    np.testing.assert_allclose(left.values + right.values, np.ones(4), atol=1e-10)


def test_t5_certificate_serializes_partition_and_field_commitments_not_arrays():
    run = run_t5(_chain_system(), SolverConfig(field_tolerance=1e-10))
    assert run.field is not None
    encoded = canonical_data(run.certificate)
    assert encoded["partition"]["boundary_ids"] == ["x0", "x3"]
    assert encoded["partition"]["interior_ids"] == ["x1", "x2"]
    assert encoded["field_value_digest"] == run.field.value_digest
    assert encoded["normal_residual_norm"] <= 1e-10
