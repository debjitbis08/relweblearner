"""Stable hardening, perturbation, and joint-tube certificates for T7."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

import numpy as np

from .provenance import (
    DerivationRef,
    NormalizedProvenance,
    ObservationRef,
)
from .t5 import DirichletSystem, SolverCertificate, SolverStatus, SpectralCertificate
from .t6 import DerivationDAG, NodeKind, T6Certificate
from .types import NormId, TargetCardinality, canonical_digest


@dataclass(frozen=True, slots=True)
class HardenerSpec:
    version: str
    threshold: float
    norm: NormId
    region: str

    def __post_init__(self) -> None:
        if not self.version or not self.region:
            raise ValueError("hardener metadata must be named")
        if not math.isfinite(self.threshold):
            raise ValueError("hardener threshold must be finite")


@dataclass(frozen=True, slots=True)
class ReferenceMargin:
    reference_id: str
    threshold_margin: float
    half_row_gap: float | None
    half_column_gap: float | None
    margin: float
    inside_region: bool


@dataclass(frozen=True, slots=True)
class DecisionMargin:
    target_id: str
    hardener_version: str
    reference_margins: tuple[ReferenceMargin, ...]
    uniform_margin: float
    all_references_inside: bool
    method: str = "mutual-argmax-exact-region-distance/v1"


def _competitor(values: np.ndarray, excluded_index: int) -> float | None:
    competitors = np.delete(np.asarray(values, dtype=float), excluded_index)
    return float(np.max(competitors)) if competitors.size else None


def mutual_argmax_margin(
    *,
    target_id: str,
    references: Sequence[tuple[str, np.ndarray]],
    row_index: int,
    column_index: int,
    spec: HardenerSpec,
) -> DecisionMargin:
    """Compute the exact distance to threshold, row-tie, or column-tie."""
    if not references:
        raise ValueError("decision margin requires at least one exact reference")
    records: list[ReferenceMargin] = []
    shape: tuple[int, int] | None = None
    for reference_id, raw in references:
        matrix = np.asarray(raw, dtype=float)
        if matrix.ndim != 2 or not np.all(np.isfinite(matrix)):
            raise ValueError("mutual-argmax references must be finite matrices")
        if shape is None:
            shape = matrix.shape
        elif matrix.shape != shape:
            raise ValueError("exact references must share one matrix shape")
        if row_index not in range(matrix.shape[0]) or column_index not in range(
            matrix.shape[1]
        ):
            raise ValueError("target coordinate lies outside the score matrix")
        score = float(matrix[row_index, column_index])
        threshold_margin = score - spec.threshold
        row_other = _competitor(matrix[row_index, :], column_index)
        column_other = _competitor(matrix[:, column_index], row_index)
        row_gap = None if row_other is None else (score - row_other) / 2.0
        column_gap = None if column_other is None else (score - column_other) / 2.0
        finite_margins = [threshold_margin]
        if row_gap is not None:
            finite_margins.append(row_gap)
        if column_gap is not None:
            finite_margins.append(column_gap)
        margin = max(0.0, min(finite_margins))
        inside = threshold_margin > 0.0 and all(
            value is None or value > 0.0 for value in (row_gap, column_gap)
        )
        records.append(ReferenceMargin(
            reference_id=reference_id,
            threshold_margin=float(threshold_margin),
            half_row_gap=None if row_gap is None else float(row_gap),
            half_column_gap=None if column_gap is None else float(column_gap),
            margin=float(margin),
            inside_region=inside,
        ))
    return DecisionMargin(
        target_id=target_id,
        hardener_version=spec.version,
        reference_margins=tuple(records),
        uniform_margin=min(item.margin for item in records),
        all_references_inside=all(item.inside_region for item in records),
    )


def mutual_argmax_contains(
    matrix: np.ndarray,
    row_index: int,
    column_index: int,
    spec: HardenerSpec,
) -> bool:
    """Membership check with explicit strict ties; array order never decides."""
    scores = np.asarray(matrix, dtype=float)
    if scores.ndim != 2 or not np.all(np.isfinite(scores)):
        return False
    score = float(scores[row_index, column_index])
    row_other = _competitor(scores[row_index, :], column_index)
    column_other = _competitor(scores[:, column_index], row_index)
    return (
        score >= spec.threshold
        and (row_other is None or score > row_other)
        and (column_other is None or score > column_other)
    )


@dataclass(frozen=True, slots=True)
class BoundaryPerturbationCertificate:
    valid: bool
    boundary_change_norm: float
    kappa_boundary_upper: float
    field_radius: float | None
    dimension_preserved: bool
    partition_preserved: bool
    scope_preserved: bool
    reason: str


def bound_boundary_perturbation(
    *,
    boundary_change: np.ndarray,
    kappa_boundary_upper: float,
    expected_dimension: int,
    dimension_preserved: bool = True,
    partition_preserved: bool = True,
    scope_preserved: bool = True,
) -> BoundaryPerturbationCertificate:
    change = np.asarray(boundary_change, dtype=float)
    norm = float(np.linalg.norm(change))
    metadata_valid = (
        change.shape == (expected_dimension,)
        and dimension_preserved and partition_preserved and scope_preserved
        and math.isfinite(kappa_boundary_upper) and kappa_boundary_upper >= 0
    )
    radius = (
        float(math.sqrt(1.0 + kappa_boundary_upper ** 2) * norm)
        if metadata_valid else None
    )
    return BoundaryPerturbationCertificate(
        valid=metadata_valid,
        boundary_change_norm=norm,
        kappa_boundary_upper=kappa_boundary_upper,
        field_radius=radius,
        dimension_preserved=dimension_preserved,
        partition_preserved=partition_preserved,
        scope_preserved=scope_preserved,
        reason="CERTIFIED" if metadata_valid else "DIMENSION_SCOPE_OR_PARTITION_CHANGED",
    )


@dataclass(frozen=True, slots=True)
class OperatorPerturbationCertificate:
    valid: bool
    symmetry_error: float
    perturbed_min_eigenvalue: float | None
    perturbed_spd: bool
    h_norm: float
    g_norm: float
    relative_inverse_h: float | None
    inverse_norm_upper: float | None
    field_radius: float | None
    dimension_preserved: bool
    partition_preserved: bool
    scope_preserved: bool
    reason: str
    method: str = "neumann-dirichlet-operator-bound/v1"


def bound_operator_perturbation(
    *,
    system: DirichletSystem,
    spectrum: SpectralCertificate,
    h_matrix: np.ndarray,
    g_vector: np.ndarray,
    base_interior: np.ndarray,
    dimension_preserved: bool = True,
    partition_preserved: bool = True,
    scope_preserved: bool = True,
) -> OperatorPerturbationCertificate:
    h = np.asarray(h_matrix, dtype=float)
    g = np.asarray(g_vector, dtype=float)
    x = np.asarray(base_interior, dtype=float)
    n = len(system.interior_indices)
    shapes_valid = h.shape == (n, n) and g.shape == (n,) and x.shape == (n,)
    metadata_valid = (
        shapes_valid and dimension_preserved and partition_preserved and scope_preserved
    )
    symmetry = float(np.max(np.abs(h - h.T))) if shapes_valid and n else 0.0
    if not metadata_valid or spectrum.lower_bound is None or spectrum.lower_bound <= 0:
        return OperatorPerturbationCertificate(
            False, symmetry, None, False,
            float(np.linalg.norm(h)) if h.size else 0.0,
            float(np.linalg.norm(g)) if g.size else 0.0,
            None, None, None,
            dimension_preserved, partition_preserved, scope_preserved,
            "DIMENSION_SCOPE_PARTITION_OR_SPECTRUM_CHANGED",
        )
    if n == 0:
        valid = not h.size and not g.size
        return OperatorPerturbationCertificate(
            valid, symmetry, None, valid, 0.0, 0.0, 0.0,
            0.0, 0.0 if valid else None,
            dimension_preserved, partition_preserved, scope_preserved,
            "CERTIFIED" if valid else "NONEMPTY_PERTURBATION_ON_EMPTY_INTERIOR",
        )
    a = (system.laplacian_uu + system.laplacian_uu.T) / 2.0
    perturbed = a + h
    perturbed_symmetry = float(np.max(np.abs(perturbed - perturbed.T)))
    symmetry = max(symmetry, perturbed_symmetry)
    eigenvalues, eigenvectors = np.linalg.eigh(a)
    if float(eigenvalues[0]) <= 0:
        return OperatorPerturbationCertificate(
            False, symmetry, None, False, float(np.linalg.norm(h, ord=2)),
            float(np.linalg.norm(g)), None, None, None,
            dimension_preserved, partition_preserved, scope_preserved,
            "BASE_OPERATOR_NOT_SPD",
        )
    inverse_h = eigenvectors @ (
        (eigenvectors.T @ h) / eigenvalues[:, np.newaxis]
    )
    relative = float(np.linalg.norm(inverse_h, ord=2))
    h_norm = float(np.linalg.norm(h, ord=2))
    g_norm = float(np.linalg.norm(g))
    perturbed_min = float(np.linalg.eigvalsh((perturbed + perturbed.T) / 2.0)[0])
    scale = max(1.0, float(np.max(np.abs(perturbed))))
    symmetry_tolerance = 128 * np.finfo(float).eps * max(1, n) * scale
    spd = symmetry <= symmetry_tolerance and perturbed_min > 0.0
    inverse_upper = float(1.0 / spectrum.lower_bound)
    neumann = relative < 1.0
    radius = (
        inverse_upper / (1.0 - relative)
        * (g_norm + h_norm * float(np.linalg.norm(x)))
        if spd and neumann else None
    )
    valid = spd and neumann and radius is not None and math.isfinite(radius)
    reason = (
        "CERTIFIED" if valid
        else "PERTURBED_OPERATOR_NOT_SPD" if not spd
        else "NEUMANN_CONDITION_FAILED"
    )
    return OperatorPerturbationCertificate(
        valid=valid,
        symmetry_error=symmetry,
        perturbed_min_eigenvalue=perturbed_min,
        perturbed_spd=spd,
        h_norm=h_norm,
        g_norm=g_norm,
        relative_inverse_h=relative,
        inverse_norm_upper=inverse_upper,
        field_radius=float(radius) if radius is not None else None,
        dimension_preserved=dimension_preserved,
        partition_preserved=partition_preserved,
        scope_preserved=scope_preserved,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class PerturbationTerm:
    term_id: str
    category: str
    radius: float | None
    valid: bool
    counted_at: str
    reason: str

    def __post_init__(self) -> None:
        if not self.term_id or not self.category or not self.counted_at:
            raise ValueError("perturbation terms must be named")
        if self.radius is not None and (
            not math.isfinite(self.radius) or self.radius < 0
        ):
            raise ValueError("perturbation radii must be finite and non-negative")


def solver_perturbation_term(solver: SolverCertificate) -> PerturbationTerm:
    valid = (
        solver.status is SolverStatus.CONVERGED
        and solver.error_bound is not None
        and math.isfinite(solver.error_bound)
    )
    return PerturbationTerm(
        term_id="finite-solver-residual",
        category="solver",
        radius=float(solver.error_bound) if valid else None,
        valid=valid,
        counted_at="field",
        reason="CERTIFIED" if valid else "SOLVER_ERROR_UNCERTIFIED",
    )


@dataclass(frozen=True, slots=True)
class NodePerturbation:
    node_id: str
    perturbation_radius: float
    approximation_budget: float | None
    joint_radius: float | None
    joint_tube_satisfied: bool


@dataclass(frozen=True, slots=True)
class PerturbationCertificate:
    derivation_id: str
    terms: tuple[PerturbationTerm, ...]
    field_radius: float | None
    node_perturbations: tuple[NodePerturbation, ...]
    output_radius: float | None
    joint_tubes_satisfied: bool
    terms_counted_once: bool
    valid: bool
    rejection_reasons: tuple[str, ...]
    method: str = "nodewise-joint-E-plus-R/v1"


def propagate_perturbation(
    *,
    dag: DerivationDAG,
    t6_certificate: T6Certificate,
    terms: Sequence[PerturbationTerm],
    leaf_field_constants: Mapping[str, float] | None = None,
    operation_field_constants: Mapping[str, float] | None = None,
    leaf_zetas: Mapping[str, float] | None = None,
    operation_zetas: Mapping[str, float] | None = None,
) -> PerturbationCertificate:
    if t6_certificate.derivation_id != dag.derivation_id:
        raise ValueError("T6 and perturbation DAG ids differ")
    leaf_field_constants = leaf_field_constants or {}
    operation_field_constants = operation_field_constants or {}
    leaf_zetas = leaf_zetas or {}
    operation_zetas = operation_zetas or {}
    term_ids = tuple(term.term_id for term in terms)
    counted_once = len(set(term_ids)) == len(term_ids)
    reasons: list[str] = []
    if not counted_once:
        reasons.append("perturbation term counted more than once")
    reasons.extend(
        f"invalid perturbation term: {term.term_id}"
        for term in terms if not term.valid
    )
    field_terms = tuple(
        term for term in terms if term.counted_at == "field"
    )
    field_valid = all(term.valid and term.radius is not None for term in field_terms)
    field_radius = (
        float(sum(term.radius or 0.0 for term in field_terms))
        if field_valid else None
    )
    budgets = {item.node_id: item.budget for item in t6_certificate.node_budgets}
    contracts = {item.node_id: item.contract for item in t6_certificate.node_contracts}
    perturbations: dict[str, float] = {}
    records: list[NodePerturbation] = []
    joint_ok = True
    for node in dag.nodes:
        if node.kind is NodeKind.LEAF:
            field_constant = leaf_field_constants.get(node.reader_id or "", 0.0)
            zeta = leaf_zetas.get(node.reader_id or "", 0.0)
            radius = field_constant * (field_radius or 0.0) + zeta
            node_joint_ok = True
        else:
            contract = contracts.get(node.node_id)
            if contract is None:
                reasons.append(f"missing T6 node contract: {node.node_id}")
                radius = 0.0
                node_joint_ok = False
            else:
                child_radii = tuple(perturbations[child] for child in node.child_ids)
                field_constant = operation_field_constants.get(
                    node.operation_id or "", 0.0
                )
                zeta = operation_zetas.get(node.operation_id or "", 0.0)
                radius = field_constant * (field_radius or 0.0) + zeta + sum(
                    constant * child_radius
                    for constant, child_radius in zip(
                        contract.lipschitz_constants, child_radii, strict=True
                    )
                )
                node_joint_ok = all(
                    budgets[child] is not None
                    and budgets[child] + child_radius <= tube_radius
                    for child, child_radius, tube_radius in zip(
                        node.child_ids, child_radii,
                        contract.tube.input_radii, strict=True,
                    )
                )
                if not node_joint_ok:
                    reasons.append(f"joint T6 tube exceeded: {node.node_id}")
        approximation = budgets.get(node.node_id)
        joint = None if approximation is None else approximation + radius
        perturbations[node.node_id] = float(radius)
        joint_ok = joint_ok and node_joint_ok
        records.append(NodePerturbation(
            node_id=node.node_id,
            perturbation_radius=float(radius),
            approximation_budget=approximation,
            joint_radius=joint,
            joint_tube_satisfied=node_joint_ok,
        ))
    output_radius = perturbations.get(dag.root_id)
    valid = (
        counted_once and field_valid and all(term.valid for term in terms)
        and joint_ok and output_radius is not None and not reasons
    )
    return PerturbationCertificate(
        derivation_id=dag.derivation_id,
        terms=tuple(terms),
        field_radius=field_radius,
        node_perturbations=tuple(records),
        output_radius=output_radius if valid else None,
        joint_tubes_satisfied=joint_ok,
        terms_counted_once=counted_once,
        valid=valid,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


class PremiseId(str, Enum):
    TARGET_SINGLETON = "TARGET_SINGLETON"
    POLICY_PERMIT = "POLICY_PERMIT"
    T5_T6_CERTIFIED = "T5_T6_CERTIFIED"
    POSITIVE_MARGIN = "POSITIVE_MARGIN"
    PERTURBATION_JOINT_TUBES = "PERTURBATION_JOINT_TUBES"
    STRICT_INEQUALITY = "STRICT_INEQUALITY"


@dataclass(frozen=True, slots=True)
class PremiseRecord:
    premise_id: PremiseId
    satisfied: bool
    evidence_id: str
    reason: str


class CommitmentOutcome(str, Enum):
    COMMIT = "COMMIT"
    EXCLUSION = "EXCLUSION"
    ABSTAIN = "ABSTAIN"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class StableCommitmentCertificate:
    version: str
    target_id: str
    target_verdict: TargetCardinality
    commitment: str | None
    outcome: CommitmentOutcome
    code: str
    premises: tuple[PremiseRecord, ...]
    approximation_budget: float | None
    perturbation_radius: float | None
    decision_margin: float | None
    strict_inequality: bool
    model_versions: tuple[tuple[str, str], ...]
    provenance: NormalizedProvenance

    @property
    def certificate_id(self) -> str:
        return canonical_digest(self)


def validate_runtime_provenance(provenance: NormalizedProvenance) -> None:
    if not all(isinstance(ref, ObservationRef) for ref in provenance.observations):
        raise TypeError("runtime provenance may contain only ObservationRef values")
    if not all(isinstance(ref, DerivationRef) for ref in provenance.derivations):
        raise TypeError("runtime provenance may contain only DerivationRef values")


def _premise(
    premise_id: PremiseId, satisfied: bool, evidence: object, reason: str
) -> PremiseRecord:
    return PremiseRecord(
        premise_id, satisfied, canonical_digest(evidence), reason
    )


def certify_commitment(
    *,
    version: str,
    target_id: str,
    target_verdict: TargetCardinality,
    policy_permitted: bool,
    policy_evidence: object,
    t5_certified: bool,
    t5_evidence: object,
    t6_certified: bool,
    separation_certified: bool,
    t6_evidence: object,
    approximation_budget: float | None,
    margin: DecisionMargin | None,
    perturbation: PerturbationCertificate | None,
    provenance: NormalizedProvenance,
    model_versions: Sequence[tuple[str, str]],
) -> StableCommitmentCertificate:
    """Apply structural branches first, then record all six positive premises."""
    validate_runtime_provenance(provenance)
    def short_circuit_premises(
        *, target_satisfied: bool, policy_satisfied: bool, reason: str
    ) -> tuple[PremiseRecord, ...]:
        return (
            _premise(PremiseId.TARGET_SINGLETON, target_satisfied,
                     target_verdict, reason),
            _premise(PremiseId.POLICY_PERMIT, policy_satisfied,
                     policy_evidence, "PERMIT" if policy_satisfied else "NOT_REACHED"),
            _premise(PremiseId.T5_T6_CERTIFIED, False, "not-reached", "NOT_REACHED"),
            _premise(PremiseId.POSITIVE_MARGIN, False, "not-reached", "NOT_REACHED"),
            _premise(PremiseId.PERTURBATION_JOINT_TUBES, False,
                     "not-reached", "NOT_REACHED"),
            _premise(PremiseId.STRICT_INEQUALITY, False,
                     "not-reached", "NOT_REACHED"),
        )
    if target_verdict is TargetCardinality.EMPTY:
        return StableCommitmentCertificate(
            version, target_id, target_verdict, None, CommitmentOutcome.REJECT,
            "STRUCTURAL_EMPTY",
            short_circuit_premises(
                target_satisfied=False, policy_satisfied=False,
                reason="STRUCTURAL_EMPTY",
            ),
            None, None, None, False,
            tuple(model_versions), provenance,
        )
    if target_verdict in {TargetCardinality.MANY, TargetCardinality.UNKNOWN}:
        return StableCommitmentCertificate(
            version, target_id, target_verdict, None, CommitmentOutcome.ABSTAIN,
            "STRUCTURAL_AMBIGUOUS" if target_verdict is TargetCardinality.MANY
            else "STRUCTURAL_UNKNOWN",
            short_circuit_premises(
                target_satisfied=False, policy_satisfied=False,
                reason=("STRUCTURAL_AMBIGUOUS"
                        if target_verdict is TargetCardinality.MANY
                        else "STRUCTURAL_UNKNOWN"),
            ),
            None, None, None, False, tuple(model_versions), provenance,
        )
    if target_verdict is TargetCardinality.DISTINCT:
        exclusion_permitted = policy_permitted and bool(provenance.observations)
        return StableCommitmentCertificate(
            version, target_id, target_verdict, "DISTINCT",
            CommitmentOutcome.EXCLUSION
            if exclusion_permitted else CommitmentOutcome.ABSTAIN,
            "CERTIFIED_DISTINCT_EXCLUSION"
            if exclusion_permitted else "POLICY_OR_PROVENANCE_REFUSAL",
            short_circuit_premises(
                target_satisfied=True, policy_satisfied=exclusion_permitted,
                reason="DISTINCT_EXCLUSION",
            ),
            None, None, None, False, tuple(model_versions), provenance,
        )

    target_ok = target_verdict is TargetCardinality.IDENTICAL
    policy_ok = policy_permitted and bool(provenance.observations)
    t5_t6_ok = (
        t5_certified and t6_certified and separation_certified
        and approximation_budget is not None
        and math.isfinite(approximation_budget)
        and approximation_budget >= 0
    )
    margin_ok = (
        margin is not None and margin.all_references_inside
        and margin.uniform_margin > 0
    )
    perturbation_ok = (
        perturbation is not None and perturbation.valid
        and perturbation.joint_tubes_satisfied
        and perturbation.output_radius is not None
    )
    inequality = (
        t5_t6_ok and margin_ok and perturbation_ok
        and approximation_budget is not None
        and perturbation is not None and perturbation.output_radius is not None
        and margin is not None
        and approximation_budget + perturbation.output_radius
        < margin.uniform_margin
    )
    premises = (
        _premise(PremiseId.TARGET_SINGLETON, target_ok, target_verdict,
                 "IDENTICAL" if target_ok else "NOT_IDENTICAL"),
        _premise(PremiseId.POLICY_PERMIT, policy_ok, policy_evidence,
                 "PERMIT" if policy_ok else "REFUSED_OR_MISSING_PROVENANCE"),
        _premise(
            PremiseId.T5_T6_CERTIFIED, t5_t6_ok,
            (t5_evidence, t6_evidence),
            "CERTIFIED" if t5_t6_ok else "T5_T6_OR_SEPARATION_FAILED",
        ),
        _premise(PremiseId.POSITIVE_MARGIN, margin_ok, margin,
                 "POSITIVE" if margin_ok else "NONPOSITIVE_OR_OUTSIDE"),
        _premise(
            PremiseId.PERTURBATION_JOINT_TUBES, perturbation_ok, perturbation,
            "CERTIFIED" if perturbation_ok else "PERTURBATION_OR_JOINT_TUBE_FAILED",
        ),
        _premise(PremiseId.STRICT_INEQUALITY, inequality,
                 (approximation_budget, perturbation, margin),
                 "STRICT" if inequality else "E_PLUS_R_NOT_BELOW_MARGIN"),
    )
    all_satisfied = all(record.satisfied for record in premises)
    if all_satisfied:
        code = "CERTIFIED_IDENTICAL"
    else:
        first_failure = next(record.premise_id.value for record in premises
                             if not record.satisfied)
        code = f"ABSTAIN_{first_failure}"
    return StableCommitmentCertificate(
        version=version,
        target_id=target_id,
        target_verdict=target_verdict,
        commitment="IDENTICAL" if all_satisfied else None,
        outcome=CommitmentOutcome.COMMIT if all_satisfied else CommitmentOutcome.ABSTAIN,
        code=code,
        premises=premises,
        approximation_budget=approximation_budget,
        perturbation_radius=(
            perturbation.output_radius if perturbation is not None else None
        ),
        decision_margin=margin.uniform_margin if margin is not None else None,
        strict_inequality=inequality,
        model_versions=tuple(model_versions),
        provenance=provenance,
    )
