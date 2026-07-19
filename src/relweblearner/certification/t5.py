"""Certified finite-dimensional Dirichlet operators for T5.

The exact and numerical representations deliberately live side by side.  The
unweighted rational residuals decide the kernel, while positive row weights
and floating-point arrays define the energy and the local iterative solver.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Iterable, Sequence

import numpy as np
import sympy

from .types import NormId


@dataclass(frozen=True, slots=True)
class ExactEntry:
    row: int
    column: int
    value: Fraction

    def __post_init__(self) -> None:
        if self.row < 0 or self.column < 0:
            raise ValueError("exact entry indices must be non-negative")
        if self.value == 0:
            raise ValueError("zero exact entries must be omitted")


@dataclass(frozen=True, slots=True)
class ResidualBlock:
    """One retained residual block before vertical assembly."""

    block_id: str
    row_count: int
    column_count: int
    exact_entries: tuple[ExactEntry, ...]
    weight: Fraction
    weighted_matrix: np.ndarray

    def __post_init__(self) -> None:
        if not self.block_id:
            raise ValueError("block_id must be non-empty")
        if self.row_count < 0 or self.column_count <= 0:
            raise ValueError("invalid residual block shape")
        if self.weight <= 0:
            raise ValueError("retained residual block weights must be positive")
        matrix = np.asarray(self.weighted_matrix, dtype=float)
        if matrix.shape != (self.row_count, self.column_count):
            raise ValueError("weighted residual matrix has the wrong shape")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("weighted residual matrices must be finite")
        seen: set[tuple[int, int]] = set()
        for entry in self.exact_entries:
            key = (entry.row, entry.column)
            if key in seen:
                raise ValueError("exact residual entries must be coalesced")
            seen.add(key)
            if entry.row >= self.row_count or entry.column >= self.column_count:
                raise ValueError("exact residual entry lies outside the block")


def residual_block_from_rational(
    block_id: str,
    matrix: Sequence[Sequence[Fraction | int]],
    *,
    weight: Fraction = Fraction(1),
) -> ResidualBlock:
    """Build a residual block without losing its exact rational encoding."""
    if weight <= 0:
        raise ValueError("retained residual block weights must be positive")
    rows = tuple(tuple(Fraction(value) for value in row) for row in matrix)
    if not rows:
        raise ValueError("a retained block must contain at least one row")
    column_count = len(rows[0])
    if column_count == 0 or any(len(row) != column_count for row in rows):
        raise ValueError("rational residual matrices must be non-empty rectangles")
    entries = tuple(
        ExactEntry(i, j, value)
        for i, row in enumerate(rows)
        for j, value in enumerate(row)
        if value
    )
    unweighted = np.asarray(
        [[float(value) for value in row] for row in rows], dtype=float
    )
    weighted = math.sqrt(float(weight)) * unweighted
    return ResidualBlock(
        block_id=block_id,
        row_count=len(rows),
        column_count=column_count,
        exact_entries=entries,
        weight=weight,
        weighted_matrix=weighted,
    )


@dataclass(frozen=True, slots=True)
class CellIncidence:
    incidence_id: str
    edge_id: str
    vertex_id: str
    role: str

    def __post_init__(self) -> None:
        if not self.incidence_id or not self.edge_id or not self.vertex_id:
            raise ValueError("cell incidence ids must be non-empty")
        if self.role not in {"head", "tail"}:
            raise ValueError("an incidence role must be head or tail")


@dataclass(frozen=True, slots=True)
class CellComplex:
    vertex_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    incidences: tuple[CellIncidence, ...]

    def __post_init__(self) -> None:
        if not self.vertex_ids or len(set(self.vertex_ids)) != len(self.vertex_ids):
            raise ValueError("cell complexes require unique vertices")
        if len(set(self.edge_ids)) != len(self.edge_ids):
            raise ValueError("cell-complex edges must be unique")
        if len({item.incidence_id for item in self.incidences}) != len(self.incidences):
            raise ValueError("cell incidences must be uniquely named")
        for edge_id in self.edge_ids:
            attached = [item for item in self.incidences if item.edge_id == edge_id]
            if len(attached) != 2 or {item.role for item in attached} != {"head", "tail"}:
                raise ValueError("every edge requires named head and tail incidences")
            if any(item.vertex_id not in self.vertex_ids for item in attached):
                raise ValueError("an incidence names an unknown vertex")
        if any(item.edge_id not in self.edge_ids for item in self.incidences):
            raise ValueError("an incidence names an unknown edge")


@dataclass(frozen=True, slots=True)
class StalkSpec:
    cell_id: str
    cell_kind: str
    dimension: int
    norm: NormId

    def __post_init__(self) -> None:
        if not self.cell_id or self.cell_kind not in {"vertex", "edge"}:
            raise ValueError("stalks require a named vertex or edge cell")
        if self.dimension <= 0:
            raise ValueError("stalk dimensions must be positive")


@dataclass(frozen=True, slots=True)
class Restriction:
    restriction_id: str
    edge_id: str
    vertex_id: str
    incidence_id: str
    role: str
    row_count: int
    column_count: int
    exact_entries: tuple[ExactEntry, ...]

    def __post_init__(self) -> None:
        if not all((self.restriction_id, self.edge_id, self.vertex_id, self.incidence_id)):
            raise ValueError("restriction ids must be non-empty")
        if self.role not in {"head", "tail"}:
            raise ValueError("restriction role must be head or tail")
        if self.row_count <= 0 or self.column_count <= 0:
            raise ValueError("restriction matrices must be non-empty")
        if any(
            entry.row >= self.row_count or entry.column >= self.column_count
            for entry in self.exact_entries
        ):
            raise ValueError("restriction entry lies outside its matrix")


@dataclass(frozen=True, slots=True)
class EdgeWeight:
    edge_id: str
    value: Fraction

    def __post_init__(self) -> None:
        if not self.edge_id or self.value <= 0:
            raise ValueError("retained edges require named positive rational weights")


@dataclass(frozen=True, slots=True)
class Linearization:
    coordinate_ids: tuple[str, ...]
    residual_blocks: tuple[ResidualBlock, ...]
    omitted_block_ids: tuple[str, ...] = ()
    cell_complex: CellComplex | None = None
    stalks: tuple[StalkSpec, ...] = ()
    restrictions: tuple[Restriction, ...] = ()
    edge_weights: tuple[EdgeWeight, ...] = ()

    def __post_init__(self) -> None:
        if not self.coordinate_ids or any(not item for item in self.coordinate_ids):
            raise ValueError("linearizations require named coordinates")
        if len(set(self.coordinate_ids)) != len(self.coordinate_ids):
            raise ValueError("coordinate ids must be unique")
        if len({block.block_id for block in self.residual_blocks}) != len(
            self.residual_blocks
        ):
            raise ValueError("residual block ids must be unique")
        if any(
            block.column_count != len(self.coordinate_ids)
            for block in self.residual_blocks
        ):
            raise ValueError("every residual block must use every coordinate column")
        retained = {block.block_id for block in self.residual_blocks}
        if retained.intersection(self.omitted_block_ids):
            raise ValueError("a block cannot be both retained and omitted")


def validate_linearization(linearization: Linearization) -> None:
    """Check typed cells/restrictions reproduce every exact residual block."""
    complex_ = linearization.cell_complex
    typed_values = (
        linearization.stalks,
        linearization.restrictions,
        linearization.edge_weights,
    )
    if complex_ is None:
        if any(typed_values):
            raise ValueError("typed linearization metadata requires a cell complex")
        return
    stalk_by_cell = {item.cell_id: item for item in linearization.stalks}
    expected_cells = set(complex_.vertex_ids) | set(complex_.edge_ids)
    if set(stalk_by_cell) != expected_cells or len(stalk_by_cell) != len(
        linearization.stalks
    ):
        raise ValueError("every cell requires exactly one stalk")
    for vertex_id in complex_.vertex_ids:
        stalk = stalk_by_cell[vertex_id]
        if stalk.cell_kind != "vertex" or stalk.dimension != len(
            linearization.coordinate_ids
        ):
            raise ValueError("alignment vertex stalk does not match coordinates")
    block_by_edge = {item.block_id: item for item in linearization.residual_blocks}
    weight_by_edge = {item.edge_id: item for item in linearization.edge_weights}
    if set(block_by_edge) != set(complex_.edge_ids):
        raise ValueError("retained edges and residual blocks differ")
    if set(weight_by_edge) != set(complex_.edge_ids):
        raise ValueError("retained edges and positive weights differ")
    incidence_by_id = {item.incidence_id: item for item in complex_.incidences}
    restrictions_by_edge: dict[str, list[Restriction]] = {
        edge_id: [] for edge_id in complex_.edge_ids
    }
    for restriction in linearization.restrictions:
        if restriction.edge_id not in restrictions_by_edge:
            raise ValueError("restriction names an unknown retained edge")
        incidence = incidence_by_id.get(restriction.incidence_id)
        if incidence is None or (
            incidence.edge_id,
            incidence.vertex_id,
            incidence.role,
        ) != (restriction.edge_id, restriction.vertex_id, restriction.role):
            raise ValueError("restriction and incidence metadata disagree")
        restrictions_by_edge[restriction.edge_id].append(restriction)
    for edge_id in complex_.edge_ids:
        stalk = stalk_by_cell[edge_id]
        block = block_by_edge[edge_id]
        if stalk.cell_kind != "edge" or stalk.dimension != block.row_count:
            raise ValueError("edge stalk and residual rows differ")
        if weight_by_edge[edge_id].value != block.weight:
            raise ValueError("edge weight and residual weight differ")
        restrictions = restrictions_by_edge[edge_id]
        if len(restrictions) != 2 or {item.role for item in restrictions} != {
            "head", "tail"
        }:
            raise ValueError("each retained edge requires two restrictions")
        residual: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
        for restriction in restrictions:
            sign = 1 if restriction.role == "head" else -1
            for entry in restriction.exact_entries:
                residual[(entry.row, entry.column)] += sign * entry.value
        residual = {key: value for key, value in residual.items() if value}
        declared = {
            (entry.row, entry.column): entry.value for entry in block.exact_entries
        }
        if residual != declared:
            raise ValueError("restriction difference does not reproduce residual block")


@dataclass(frozen=True, slots=True)
class Coboundary:
    coordinate_ids: tuple[str, ...]
    residual_blocks: tuple[ResidualBlock, ...]
    omitted_block_ids: tuple[str, ...]
    dense_delta: np.ndarray
    laplacian: np.ndarray


def assemble_coboundary(linearization: Linearization) -> Coboundary:
    """Vertically assemble retained blocks and form ``Delta = delta.T delta``."""
    column_count = len(linearization.coordinate_ids)
    if linearization.residual_blocks:
        dense_delta = np.vstack(
            [np.asarray(block.weighted_matrix, dtype=float)
             for block in linearization.residual_blocks]
        )
    else:
        dense_delta = np.zeros((0, column_count), dtype=float)
    laplacian = dense_delta.T @ dense_delta
    return Coboundary(
        coordinate_ids=linearization.coordinate_ids,
        residual_blocks=linearization.residual_blocks,
        omitted_block_ids=linearization.omitted_block_ids,
        dense_delta=dense_delta,
        laplacian=laplacian,
    )


@dataclass(frozen=True, slots=True)
class BoundarySpec:
    """Coordinate values fixed by observation-derived boundary conditions."""

    values: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        ids = tuple(item[0] for item in self.values)
        if len(set(ids)) != len(ids):
            raise ValueError("boundary coordinates must be unique")
        if any(not coordinate_id or not math.isfinite(float(value))
               for coordinate_id, value in self.values):
            raise ValueError("boundary ids and values must be finite and non-empty")


@dataclass(frozen=True, slots=True)
class CoordinatePartition:
    boundary_indices: tuple[int, ...]
    interior_indices: tuple[int, ...]
    boundary_ids: tuple[str, ...]
    interior_ids: tuple[str, ...]
    boundary_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class DirichletSystem:
    coboundary: Coboundary
    partition: CoordinatePartition
    boundary_indices: tuple[int, ...]
    interior_indices: tuple[int, ...]
    boundary_ids: tuple[str, ...]
    interior_ids: tuple[str, ...]
    boundary_values: np.ndarray
    delta_boundary: np.ndarray
    delta_interior: np.ndarray
    laplacian_bb: np.ndarray
    laplacian_bu: np.ndarray
    laplacian_ub: np.ndarray
    laplacian_uu: np.ndarray
    forcing: np.ndarray


def partition_dirichlet(
    delta: Coboundary,
    boundary: BoundarySpec,
) -> DirichletSystem:
    """Partition coordinates into observed boundary and free interior sets."""
    by_id = dict(boundary.values)
    unknown = set(by_id).difference(delta.coordinate_ids)
    if unknown:
        raise ValueError(f"unknown boundary coordinate ids: {sorted(unknown)!r}")
    boundary_indices = tuple(
        i for i, coordinate_id in enumerate(delta.coordinate_ids) if coordinate_id in by_id
    )
    interior_indices = tuple(
        i for i, coordinate_id in enumerate(delta.coordinate_ids) if coordinate_id not in by_id
    )
    boundary_ids = tuple(delta.coordinate_ids[i] for i in boundary_indices)
    interior_ids = tuple(delta.coordinate_ids[i] for i in interior_indices)
    b = np.asarray([float(by_id[item]) for item in boundary_ids], dtype=float)
    d_b = delta.dense_delta[:, boundary_indices]
    d_u = delta.dense_delta[:, interior_indices]
    h = delta.laplacian
    h_bb = h[np.ix_(boundary_indices, boundary_indices)]
    h_bu = h[np.ix_(boundary_indices, interior_indices)]
    h_ub = h[np.ix_(interior_indices, boundary_indices)]
    h_uu = h[np.ix_(interior_indices, interior_indices)]
    forcing = h_ub @ b
    return DirichletSystem(
        coboundary=delta,
        partition=CoordinatePartition(
            boundary_indices=boundary_indices,
            interior_indices=interior_indices,
            boundary_ids=boundary_ids,
            interior_ids=interior_ids,
            boundary_values=tuple(float(value) for value in b),
        ),
        boundary_indices=boundary_indices,
        interior_indices=interior_indices,
        boundary_ids=boundary_ids,
        interior_ids=interior_ids,
        boundary_values=b,
        delta_boundary=d_b,
        delta_interior=d_u,
        laplacian_bb=h_bb,
        laplacian_bu=h_bu,
        laplacian_ub=h_ub,
        laplacian_uu=h_uu,
        forcing=forcing,
    )


class KernelStatus(str, Enum):
    EMPTY_INTERIOR = "EMPTY_INTERIOR"
    UNIQUE = "UNIQUE"
    UNCONTROLLED_KERNEL = "UNCONTROLLED_KERNEL"
    NUMERIC_FAILURE = "NUMERIC_FAILURE"


@dataclass(frozen=True, slots=True)
class KernelComponent:
    coordinate_ids: tuple[str, ...]
    exact_rank: int
    nullity: int


@dataclass(frozen=True, slots=True)
class KernelCertificate:
    status: KernelStatus
    exact_rank: int
    interior_dimension: int
    nullity: int
    symmetry_error: float
    numeric_min_eigenvalue: float | None
    psd_verified: bool
    cholesky_verified: bool
    components: tuple[KernelComponent, ...]
    method: str = "sympy-exact-rank-plus-numeric-spd/v1"


def _exact_interior_matrix(
    system: DirichletSystem,
    selected_interior_positions: tuple[int, ...] | None = None,
) -> sympy.SparseMatrix:
    """Assemble the unweighted rational ``delta_U`` in a sparse exact domain."""
    if selected_interior_positions is None:
        selected_interior_positions = tuple(range(len(system.interior_indices)))
    full_columns = tuple(
        system.interior_indices[position] for position in selected_interior_positions
    )
    column_map = {full: local for local, full in enumerate(full_columns)}
    entries: dict[tuple[int, int], sympy.Rational] = {}
    row_offset = 0
    for block in system.coboundary.residual_blocks:
        for entry in block.exact_entries:
            local_column = column_map.get(entry.column)
            if local_column is not None:
                entries[(row_offset + entry.row, local_column)] = sympy.Rational(
                    entry.value.numerator, entry.value.denominator
                )
        row_offset += block.row_count
    return sympy.SparseMatrix(row_offset, len(full_columns), entries)


def _operator_components(system: DirichletSystem) -> tuple[tuple[int, ...], ...]:
    n = len(system.interior_indices)
    if n == 0:
        return ()
    h = system.laplacian_uu
    scale = max(1.0, float(np.max(np.abs(h)))) if h.size else 1.0
    threshold = 64.0 * np.finfo(float).eps * scale
    neighbors = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(float(h[i, j])) > threshold:
                neighbors[i].add(j)
                neighbors[j].add(i)
    unseen = set(range(n))
    components: list[tuple[int, ...]] = []
    while unseen:
        start = min(unseen)
        stack = [start]
        found: set[int] = set()
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(neighbors[current].difference(found))
        unseen.difference_update(found)
        components.append(tuple(sorted(found)))
    return tuple(components)


def certify_kernel(system: DirichletSystem) -> KernelCertificate:
    """Certify exact uniqueness, then check the floating operator is usable."""
    n = len(system.interior_indices)
    symmetry_error = (
        float(np.max(np.abs(system.laplacian_uu - system.laplacian_uu.T)))
        if n else 0.0
    )
    if n == 0:
        return KernelCertificate(
            status=KernelStatus.EMPTY_INTERIOR,
            exact_rank=0,
            interior_dimension=0,
            nullity=0,
            symmetry_error=symmetry_error,
            numeric_min_eigenvalue=None,
            psd_verified=True,
            cholesky_verified=True,
            components=(),
        )

    exact = _exact_interior_matrix(system)
    # DomainMatrix dispatches to SymPy's exact sparse-field algorithms.  The
    # ordinary Matrix.rank() path is mathematically equivalent but several
    # orders slower on the 1,536 x 100 rule_20 certificate matrix.
    exact_rank = int(exact.to_DM().rank())
    operator_components = _operator_components(system)
    component_records: list[KernelComponent] = []
    for component in operator_components:
        component_rank = (
            exact_rank
            if len(operator_components) == 1
            else int(_exact_interior_matrix(system, component).to_DM().rank())
        )
        component_records.append(KernelComponent(
            coordinate_ids=tuple(system.interior_ids[i] for i in component),
            exact_rank=component_rank,
            nullity=len(component) - component_rank,
        ))
    components = tuple(component_records)
    h = system.laplacian_uu
    eigenvalues = np.linalg.eigvalsh((h + h.T) / 2.0)
    numeric_min = float(eigenvalues[0])
    scale = max(1.0, float(np.max(np.abs(h))))
    numeric_tolerance = 128.0 * np.finfo(float).eps * max(1, n) * scale
    psd_verified = bool(numeric_min >= -numeric_tolerance)
    try:
        np.linalg.cholesky(h)
        cholesky_verified = True
    except np.linalg.LinAlgError:
        cholesky_verified = False

    if exact_rank < n:
        status = KernelStatus.UNCONTROLLED_KERNEL
    elif symmetry_error > numeric_tolerance or not psd_verified or not cholesky_verified:
        status = KernelStatus.NUMERIC_FAILURE
    else:
        status = KernelStatus.UNIQUE
    return KernelCertificate(
        status=status,
        exact_rank=exact_rank,
        interior_dimension=n,
        nullity=n - exact_rank,
        symmetry_error=symmetry_error,
        numeric_min_eigenvalue=numeric_min,
        psd_verified=psd_verified,
        cholesky_verified=cholesky_verified,
        components=components,
    )


class SpectralStatus(str, Enum):
    EMPTY_INTERIOR = "EMPTY_INTERIOR"
    CERTIFIED = "CERTIFIED"
    UNCONTROLLED_KERNEL = "UNCONTROLLED_KERNEL"
    NONPOSITIVE_LOWER_BOUND = "NONPOSITIVE_LOWER_BOUND"


@dataclass(frozen=True, slots=True)
class SpectralCertificate:
    status: SpectralStatus
    lower_bound: float | None
    upper_bound: float | None
    eigenvalue_min_estimate: float | None
    eigenvalue_max_estimate: float | None
    eigen_residual_max: float
    gershgorin_upper: float | None
    rounding_slack: float
    condition_upper_bound: float | None
    method: str = "residual-eigenbound-plus-gershgorin/v1"


def bound_spectrum(
    system: DirichletSystem,
    kernel: KernelCertificate | None = None,
) -> SpectralCertificate:
    """Inflate numerical eigendata and independently bound the top by rows."""
    kernel = kernel or certify_kernel(system)
    n = len(system.interior_indices)
    if n == 0:
        return SpectralCertificate(
            status=SpectralStatus.EMPTY_INTERIOR,
            lower_bound=None,
            upper_bound=None,
            eigenvalue_min_estimate=None,
            eigenvalue_max_estimate=None,
            eigen_residual_max=0.0,
            gershgorin_upper=None,
            rounding_slack=0.0,
            condition_upper_bound=None,
        )
    if kernel.status is not KernelStatus.UNIQUE:
        return SpectralCertificate(
            status=SpectralStatus.UNCONTROLLED_KERNEL,
            lower_bound=None,
            upper_bound=None,
            eigenvalue_min_estimate=None,
            eigenvalue_max_estimate=None,
            eigen_residual_max=0.0,
            gershgorin_upper=None,
            rounding_slack=0.0,
            condition_upper_bound=None,
        )

    h = (system.laplacian_uu + system.laplacian_uu.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(h)
    residual = max(
        float(np.linalg.norm(h @ eigenvectors[:, i] - eigenvalues[i] * eigenvectors[:, i]))
        for i in range(n)
    )
    gershgorin = float(np.max(np.sum(np.abs(h), axis=1)))
    rounding = float(
        64.0 * np.finfo(float).eps * max(1, n) * max(1.0, gershgorin)
    )
    lower = float(float(eigenvalues[0]) - residual - rounding)
    upper = float(gershgorin + rounding)
    if lower <= 0.0 or upper <= 0.0:
        status = SpectralStatus.NONPOSITIVE_LOWER_BOUND
        condition = None
    else:
        status = SpectralStatus.CERTIFIED
        condition = float(upper / lower)
    return SpectralCertificate(
        status=status,
        lower_bound=lower,
        upper_bound=upper,
        eigenvalue_min_estimate=float(eigenvalues[0]),
        eigenvalue_max_estimate=float(eigenvalues[-1]),
        eigen_residual_max=residual,
        gershgorin_upper=gershgorin,
        rounding_slack=rounding,
        condition_upper_bound=condition,
    )


class SolverStatus(str, Enum):
    CONVERGED = "CONVERGED"
    UNCONTROLLED_KERNEL = "UNCONTROLLED_KERNEL"
    UNCERTIFIED_SPECTRUM = "UNCERTIFIED_SPECTRUM"
    MAX_ITERATIONS = "MAX_ITERATIONS"


@dataclass(frozen=True, slots=True)
class SolverConfig:
    field_tolerance: float = 1e-6
    max_iterations: int = 1_000_000
    initialization: str = "zero"
    initial_values: tuple[float, ...] | None = None
    record_trace: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.field_tolerance) or self.field_tolerance <= 0:
            raise ValueError("field_tolerance must be finite and positive")
        if self.max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
        if self.initialization not in {"zero", "uniform", "provided"}:
            raise ValueError("unsupported solver initialization")
        if self.initialization == "provided" and self.initial_values is None:
            raise ValueError("provided initialization requires initial_values")
        if self.initial_values is not None and any(
            not math.isfinite(value) for value in self.initial_values
        ):
            raise ValueError("initial values must be finite")


@dataclass(frozen=True, slots=True)
class ThinkingField:
    coordinate_ids: tuple[str, ...]
    values: np.ndarray
    residual: np.ndarray
    normal_residual: np.ndarray
    energy: float
    interior_trace: tuple[tuple[float, ...], ...]
    value_digest: str


@dataclass(frozen=True, slots=True)
class SolverCertificate:
    status: SolverStatus
    iterations: int
    step_size: float | None
    residual_norm: float | None
    error_bound: float | None
    field_tolerance: float
    contraction_bound: float | None
    geometric_round_bound: int | None
    initialization: str
    method: str = "local-gradient-descent/v1"
    stopping_rule: str = "normal-residual/lambda-min-lower"


def _initial_interior(system: DirichletSystem, config: SolverConfig) -> np.ndarray:
    n = len(system.interior_indices)
    if config.initialization == "zero":
        return np.zeros(n, dtype=float)
    if config.initialization == "uniform":
        return np.full(n, 1.0 / max(1, n), dtype=float)
    assert config.initial_values is not None
    if len(config.initial_values) != n:
        raise ValueError("provided initialization has the wrong dimension")
    return np.asarray(config.initial_values, dtype=float).copy()


def _round_bound(
    initial_error: float, tolerance: float, contraction: float
) -> int | None:
    if initial_error <= tolerance:
        return 0
    if contraction <= 0.0:
        return 1
    if contraction >= 1.0:
        return None
    return int(math.ceil(math.log(tolerance / initial_error) / math.log(contraction)))


def _field(
    system: DirichletSystem,
    interior: np.ndarray,
    trace: list[tuple[float, ...]],
) -> ThinkingField:
    values = np.empty(len(system.coboundary.coordinate_ids), dtype=float)
    values[list(system.boundary_indices)] = system.boundary_values
    values[list(system.interior_indices)] = interior
    residual = system.coboundary.dense_delta @ values
    normal = system.laplacian_uu @ interior + system.forcing
    payload = np.ascontiguousarray(values, dtype="<f8").tobytes()
    digest = hashlib.sha256(payload).hexdigest()
    return ThinkingField(
        coordinate_ids=system.coboundary.coordinate_ids,
        values=values,
        residual=residual,
        normal_residual=normal,
        energy=0.5 * float(residual @ residual),
        interior_trace=tuple(trace),
        value_digest=digest,
    )


def solve_dirichlet(
    system: DirichletSystem,
    config: SolverConfig,
    *,
    kernel: KernelCertificate | None = None,
    spectrum: SpectralCertificate | None = None,
) -> tuple[ThinkingField | None, SolverCertificate]:
    """Run locality-preserving gradient descent, refusing singular systems."""
    kernel = kernel or certify_kernel(system)
    n = len(system.interior_indices)
    if n == 0:
        field = _field(system, np.zeros(0, dtype=float), [])
        return field, SolverCertificate(
            status=SolverStatus.CONVERGED,
            iterations=0,
            step_size=None,
            residual_norm=0.0,
            error_bound=0.0,
            field_tolerance=config.field_tolerance,
            contraction_bound=0.0,
            geometric_round_bound=0,
            initialization=config.initialization,
        )
    if kernel.status is not KernelStatus.UNIQUE:
        return None, SolverCertificate(
            status=SolverStatus.UNCONTROLLED_KERNEL,
            iterations=0,
            step_size=None,
            residual_norm=None,
            error_bound=None,
            field_tolerance=config.field_tolerance,
            contraction_bound=None,
            geometric_round_bound=None,
            initialization=config.initialization,
        )
    spectrum = spectrum or bound_spectrum(system, kernel)
    if (
        spectrum.status is not SpectralStatus.CERTIFIED
        or spectrum.lower_bound is None
        or spectrum.upper_bound is None
    ):
        return None, SolverCertificate(
            status=SolverStatus.UNCERTIFIED_SPECTRUM,
            iterations=0,
            step_size=None,
            residual_norm=None,
            error_bound=None,
            field_tolerance=config.field_tolerance,
            contraction_bound=None,
            geometric_round_bound=None,
            initialization=config.initialization,
        )

    lower = spectrum.lower_bound
    upper = spectrum.upper_bound
    raw_step = 2.0 / (lower + upper)
    strict_cap = np.nextafter(2.0 / upper, 0.0)
    step = float(min(raw_step, float(strict_cap)))
    contraction = float(
        max(abs(1.0 - step * lower), abs(1.0 - step * upper))
    )
    interior = _initial_interior(system, config)
    trace: list[tuple[float, ...]] = []
    if config.record_trace:
        trace.append(tuple(float(value) for value in interior))
    initial_normal = system.laplacian_uu @ interior + system.forcing
    initial_error = float(np.linalg.norm(initial_normal)) / lower
    geometric = _round_bound(initial_error, config.field_tolerance, contraction)

    iterations = 0
    while True:
        normal = system.laplacian_uu @ interior + system.forcing
        residual_norm = float(np.linalg.norm(normal))
        error_bound = residual_norm / lower
        if error_bound <= config.field_tolerance:
            status = SolverStatus.CONVERGED
            break
        if iterations >= config.max_iterations:
            status = SolverStatus.MAX_ITERATIONS
            break
        interior = interior - step * normal
        iterations += 1
        if config.record_trace:
            trace.append(tuple(float(value) for value in interior))

    field = _field(system, interior, trace)
    return field, SolverCertificate(
        status=status,
        iterations=iterations,
        step_size=step,
        residual_norm=residual_norm,
        error_bound=error_bound,
        field_tolerance=config.field_tolerance,
        contraction_bound=contraction,
        geometric_round_bound=geometric,
        initialization=config.initialization,
    )


@dataclass(frozen=True, slots=True)
class T5Certificate:
    partition: CoordinatePartition
    kernel: KernelCertificate
    spectrum: SpectralCertificate
    solver: SolverCertificate
    field_value_digest: str | None
    energy: float | None
    coboundary_residual_norm: float | None
    normal_residual_norm: float | None


@dataclass(frozen=True, slots=True)
class T5Run:
    field: ThinkingField | None
    certificate: T5Certificate


def run_t5(system: DirichletSystem, config: SolverConfig) -> T5Run:
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, solver = solve_dirichlet(
        system, config, kernel=kernel, spectrum=spectrum
    )
    certificate = T5Certificate(
        partition=system.partition,
        kernel=kernel,
        spectrum=spectrum,
        solver=solver,
        field_value_digest=None if field is None else field.value_digest,
        energy=None if field is None else float(field.energy),
        coboundary_residual_norm=(
            None if field is None else float(np.linalg.norm(field.residual))
        ),
        normal_residual_norm=(
            None if field is None else float(np.linalg.norm(field.normal_residual))
        ),
    )
    return T5Run(field=field, certificate=certificate)


def exact_entries_from_rows(
    rows: Iterable[Iterable[Fraction | int]],
) -> tuple[ExactEntry, ...]:
    """Small public helper for sparse adapter construction and tests."""
    return tuple(
        ExactEntry(i, j, value)
        for i, row in enumerate(rows)
        for j, raw in enumerate(row)
        if (value := Fraction(raw))
    )
