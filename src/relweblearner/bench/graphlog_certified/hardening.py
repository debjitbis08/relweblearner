"""GraphLog mutual-argmax T7 adapter and ordered premise assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ...certification.extensions import (
    ExtensionClassification,
    TargetClassification,
)
from ...certification.provenance import normalize_provenance
from ...certification.t5 import (
    KernelStatus,
    SolverStatus,
    SpectralStatus,
    T5Run,
)
from ...certification.t6 import (
    DerivationDAG,
    SeparationCertificate,
    T6Certificate,
)
from ...certification.t7 import (
    BoundaryPerturbationCertificate,
    CommitmentOutcome,
    DecisionMargin,
    HardenerSpec,
    OperatorPerturbationCertificate,
    PerturbationCertificate,
    PerturbationTerm,
    StableCommitmentCertificate,
    bound_boundary_perturbation,
    bound_operator_perturbation,
    certify_commitment,
    mutual_argmax_contains,
    mutual_argmax_margin,
    propagate_perturbation,
    solver_perturbation_term,
)
from ...certification.types import TargetCardinality
from .linearization import (
    GraphLogLinearization,
    encode_extension,
    field_matrix,
)
from .model import (
    CountingScope,
    CrossViewRelationIdentity,
    IdentityExtension,
    ObservationFamily,
)
from .policy import PolicyVerdict
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


@dataclass(frozen=True, slots=True)
class InitialPerturbationReport:
    boundary: BoundaryPerturbationCertificate
    operator: OperatorPerturbationCertificate
    propagated: PerturbationCertificate


@dataclass(frozen=True, slots=True)
class GraphLogIdentityDecision:
    target_id: str
    margin: DecisionMargin | None
    observed_in_hardener_region: bool
    perturbation: InitialPerturbationReport | None
    certificate: StableCommitmentCertificate


def graphlog_hardener_spec(
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> HardenerSpec:
    return HardenerSpec(
        version=spec.hardener_version,
        threshold=float(spec.identity_threshold),
        norm=spec.decision_norm,
        region="threshold-plus-strict-row-and-column-maximum/v1",
    )


def identity_margin(
    *,
    target: CrossViewRelationIdentity,
    extensions: Sequence[IdentityExtension],
    linearization: GraphLogLinearization,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> DecisionMargin:
    a_index = linearization.a_tokens.index(target.a_token)
    b_index = linearization.b_tokens.index(target.b_token)
    references = tuple(
        (
            f"extension:{index}",
            encode_extension(extension, linearization),
        )
        for index, extension in enumerate(extensions)
    )
    return mutual_argmax_margin(
        target_id=target.target_id,
        references=references,
        row_index=a_index,
        column_index=b_index,
        spec=graphlog_hardener_spec(spec),
    )


def _longdouble_laplacian(linearization: GraphLogLinearization) -> np.ndarray:
    dimension = len(linearization.core.coordinate_ids)
    laplacian = np.zeros((dimension, dimension), dtype=np.longdouble)
    for block in linearization.core.residual_blocks:
        exact = np.zeros((block.row_count, block.column_count), dtype=np.longdouble)
        for entry in block.exact_entries:
            exact[entry.row, entry.column] = (
                np.longdouble(entry.value.numerator)
                / np.longdouble(entry.value.denominator)
            )
        laplacian += np.longdouble(block.weight.numerator) \
            / np.longdouble(block.weight.denominator) * (exact.T @ exact)
    return laplacian


def initial_identity_perturbation(
    *,
    dag: DerivationDAG,
    t6_certificate: T6Certificate,
    t5_run: T5Run,
    linearization: GraphLogLinearization,
    shared_operator_report: InitialPerturbationReport | None = None,
) -> InitialPerturbationReport:
    if t5_run.field is None:
        raise ValueError("initial perturbation requires an accepted T5 field")
    if shared_operator_report is not None:
        propagated = propagate_perturbation(
            dag=dag,
            t6_certificate=t6_certificate,
            terms=shared_operator_report.propagated.terms,
            operation_field_constants={"decode_identity": 1.0},
            operation_zetas={"decode_identity": 0.0},
        )
        return InitialPerturbationReport(
            shared_operator_report.boundary,
            shared_operator_report.operator,
            propagated,
        )
    t5 = t5_run.certificate
    system_partition = t5.partition
    # The T5 certificate intentionally serializes arrays by digest.  The
    # field's system is recovered from the caller's linearization and the
    # partition committed by that certificate.
    from ...certification.t5 import assemble_coboundary, partition_dirichlet, BoundarySpec

    coboundary = assemble_coboundary(linearization.core)
    boundary = BoundarySpec(tuple(zip(
        system_partition.boundary_ids,
        system_partition.boundary_values,
        strict=True,
    )))
    system = partition_dirichlet(coboundary, boundary)
    exactish = _longdouble_laplacian(linearization)
    interior = list(system.interior_indices)
    boundary_indices = list(system.boundary_indices)
    reference_uu = np.asarray(exactish[np.ix_(interior, interior)], dtype=float)
    reference_ub = np.asarray(
        exactish[np.ix_(interior, boundary_indices)], dtype=float
    )
    h_matrix = reference_uu - system.laplacian_uu
    g_vector = -(
        reference_ub - system.laplacian_ub
    ) @ system.boundary_values
    interior_values = t5_run.field.values[interior]
    operator = bound_operator_perturbation(
        system=system,
        spectrum=t5.spectrum,
        h_matrix=h_matrix,
        g_vector=g_vector,
        base_interior=interior_values,
    )
    kappa_boundary = (
        float(np.linalg.norm(system.laplacian_ub, ord=2) / t5.spectrum.lower_bound)
        if system.interior_indices and system.boundary_indices
        and t5.spectrum.lower_bound is not None
        else 0.0
    )
    boundary_report = bound_boundary_perturbation(
        boundary_change=np.zeros(len(boundary_indices), dtype=float),
        kappa_boundary_upper=kappa_boundary,
        expected_dimension=len(boundary_indices),
    )
    terms = (
        PerturbationTerm(
            "rational-vs-float-operator", "operator",
            operator.field_radius, operator.valid, "field", operator.reason,
        ),
        solver_perturbation_term(t5.solver),
        PerturbationTerm(
            "floating-evaluator-decoder", "evaluator", 0.0, True,
            "operation:decode_identity", "EXACT_REFERENCE_IMPLEMENTATION",
        ),
        PerturbationTerm(
            "zero-initial-boundary", "boundary",
            boundary_report.field_radius, boundary_report.valid, "field",
            boundary_report.reason,
        ),
    )
    propagated = propagate_perturbation(
        dag=dag,
        t6_certificate=t6_certificate,
        terms=terms,
        operation_field_constants={"decode_identity": 1.0},
        operation_zetas={"decode_identity": 0.0},
    )
    return InitialPerturbationReport(boundary_report, operator, propagated)


def _target_provenance(
    observations: ObservationFamily,
    scope: CountingScope,
    target: CrossViewRelationIdentity,
):
    candidates = tuple(
        candidate for candidate in scope.candidate_identities
        if candidate.a_token == target.a_token and candidate.b_token == target.b_token
    )
    negatives = tuple(
        negative for negative in observations.exact_negative_identities
        if negative.a_token == target.a_token and negative.b_token == target.b_token
    )
    if candidates or negatives:
        return normalize_provenance(
            (
                ref
                for item in (*candidates, *negatives)
                for ref in item.provenance.observations
            ),
            (
                ref
                for item in (*candidates, *negatives)
                for ref in item.provenance.derivations
            ),
        )
    related = tuple(
        triangle for triangle in (*observations.triangles_a, *observations.triangles_b)
        if target.a_token in triangle.positions or target.b_token in triangle.positions
    )
    return normalize_provenance(
        ref for triangle in related for ref in triangle.provenance.observations
    )


def certify_identity_target(
    *,
    observations: ObservationFamily,
    scope: CountingScope,
    target: CrossViewRelationIdentity,
    extension_classification: ExtensionClassification[IdentityExtension],
    target_classification: TargetClassification,
    policy: PolicyVerdict,
    linearization: GraphLogLinearization,
    t5_run: T5Run,
    target_dag: DerivationDAG | None,
    target_t6_certificates: Sequence[T6Certificate],
    separation: SeparationCertificate,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
    shared_operator_report: InitialPerturbationReport | None = None,
) -> GraphLogIdentityDecision:
    verdict = target_classification.verdict
    t5 = t5_run.certificate
    t5_valid = (
        t5_run.field is not None
        and t5.kernel.status in {KernelStatus.UNIQUE, KernelStatus.EMPTY_INTERIOR}
        and t5.spectrum.status in {
            SpectralStatus.CERTIFIED, SpectralStatus.EMPTY_INTERIOR,
        }
        and t5.solver.status is SolverStatus.CONVERGED
    )
    t6_valid = (
        bool(target_t6_certificates)
        and all(certificate.admissible for certificate in target_t6_certificates)
    )
    budgets = tuple(
        certificate.root_budget for certificate in target_t6_certificates
        if certificate.root_budget is not None
    )
    approximation_budget = (
        max(budgets)
        if len(budgets) == len(target_t6_certificates) and budgets else None
    )
    margin = None
    perturbation_report = None
    observed_in_region = False
    metric_prerequisites = (
        verdict is TargetCardinality.IDENTICAL
        and policy.permitted
        and t5_valid
        and t6_valid
        and separation.separating
        and approximation_budget is not None
        and bool(extension_classification.solutions)
    )
    if metric_prerequisites:
        margin = identity_margin(
            target=target,
            extensions=extension_classification.solutions,
            linearization=linearization,
            spec=spec,
        )
        a_index = linearization.a_tokens.index(target.a_token)
        b_index = linearization.b_tokens.index(target.b_token)
        if t5_run.field is not None:
            observed_in_region = mutual_argmax_contains(
                field_matrix(t5_run.field.values, linearization),
                a_index, b_index, graphlog_hardener_spec(spec),
            )
        if target_dag is not None and len(target_t6_certificates) == 1:
            perturbation_report = initial_identity_perturbation(
                dag=target_dag,
                t6_certificate=target_t6_certificates[0],
                t5_run=t5_run,
                linearization=linearization,
                shared_operator_report=shared_operator_report,
            )
    certificate = certify_commitment(
        version="graphlog-t7-identity/v1",
        target_id=target.target_id,
        target_verdict=verdict,
        policy_permitted=policy.permitted,
        policy_evidence=policy,
        t5_certified=t5_valid,
        t5_evidence=t5,
        t6_certified=t6_valid,
        separation_certified=separation.separating,
        t6_evidence=(tuple(target_t6_certificates), separation),
        approximation_budget=approximation_budget,
        margin=margin,
        perturbation=(
            perturbation_report.propagated
            if perturbation_report is not None else None
        ),
        provenance=_target_provenance(observations, scope, target),
        model_versions=(
            ("schema", spec.schema_version),
            ("scope", spec.scope_version),
            ("extension", spec.extension_semantics_version),
            ("linearization", spec.linearization_version),
            ("comparison", spec.comparison_version),
            ("policy", spec.policy_version),
            ("hardener", spec.hardener_version),
        ),
    )
    if certificate.outcome is CommitmentOutcome.COMMIT and not observed_in_region:
        raise ValueError(
            "T7 inequality certified a commit outside the observed hardener region"
        )
    return GraphLogIdentityDecision(
        target.target_id, margin, observed_in_region,
        perturbation_report, certificate,
    )
