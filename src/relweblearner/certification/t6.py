"""Typed local-to-global enrichment comparison certificates for T6."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .provenance import NormalizedProvenance
from .t5 import DirichletSystem, SpectralCertificate, SpectralStatus, ThinkingField
from .types import NormId, canonical_digest


Array = np.ndarray
ExactApply = Callable[[tuple[Any, ...]], Any]
EnrichedApply = Callable[[tuple[Array, ...]], Array]
Encoder = Callable[[Any], Array]
NodeContractFactory = Callable[
    ["DerivationNode", tuple[float, ...], "LocalComparisonContract"],
    "LocalComparisonContract",
]


@dataclass(frozen=True, slots=True)
class ExactType:
    type_id: str
    encoding_version: str
    legal_value_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.type_id or not self.encoding_version:
            raise ValueError("exact types require ids and encoding versions")
        if len(set(self.legal_value_ids)) != len(self.legal_value_ids):
            raise ValueError("legal exact value ids must be unique")


@dataclass(frozen=True, slots=True)
class MetricCarrier:
    type_id: str
    carrier_id: str
    dimension: int
    norm: NormId

    def __post_init__(self) -> None:
        if not self.type_id or not self.carrier_id or self.dimension <= 0:
            raise ValueError("metric carriers require ids and positive dimension")


@dataclass(frozen=True, slots=True)
class ExactOperation:
    operation_id: str
    version: str
    input_type_ids: tuple[str, ...]
    output_type_id: str
    legal_tuple_ids: tuple[str, ...]
    provenance_rule: str

    def __post_init__(self) -> None:
        if not all((self.operation_id, self.version, self.output_type_id,
                    self.provenance_rule)):
            raise ValueError("exact operation metadata must be named")


@dataclass(frozen=True, slots=True)
class EnrichedOperation:
    operation_id: str
    version: str
    input_carrier_ids: tuple[str, ...]
    output_carrier_id: str
    equivariance_check: str

    def __post_init__(self) -> None:
        if not all((self.operation_id, self.version, self.output_carrier_id,
                    self.equivariance_check)):
            raise ValueError("enriched operation metadata must be named")


@dataclass(frozen=True, slots=True)
class Tube:
    center_rule: str
    input_radii: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.center_rule or any(
            not math.isfinite(radius) or radius < 0 for radius in self.input_radii
        ):
            raise ValueError("tube radii must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class LocalComparisonContract:
    operation_id: str
    defect_method: str
    declared_epsilon: float
    measured_max_defect: float
    lipschitz_method: str
    lipschitz_constants: tuple[float, ...]
    tube: Tube
    legal_tuple_count: int
    defect_verified: bool
    lipschitz_verified: bool

    def __post_init__(self) -> None:
        scalars = (
            self.declared_epsilon,
            self.measured_max_defect,
            *self.lipschitz_constants,
        )
        if not self.operation_id or any(
            not math.isfinite(value) or value < 0 for value in scalars
        ):
            raise ValueError("local comparison constants must be finite and non-negative")
        if len(self.lipschitz_constants) != len(self.tube.input_radii):
            raise ValueError("every operation input requires a tube and Lipschitz constant")


@dataclass(frozen=True, slots=True)
class LeafReaderContract:
    reader_id: str
    exact_type_id: str
    enriched_carrier_id: str
    alpha: float
    epsilon: float
    source_rule: str

    def __post_init__(self) -> None:
        if not all((self.reader_id, self.exact_type_id,
                    self.enriched_carrier_id, self.source_rule)):
            raise ValueError("leaf reader contracts must be named")
        if any(
            not math.isfinite(value) or value < 0
            for value in (self.alpha, self.epsilon)
        ):
            raise ValueError("leaf bounds must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class OperationCoverage:
    operation_id: str
    exact_present: bool
    enriched_present: bool
    contract_present: bool
    covered: bool


@dataclass(frozen=True, slots=True)
class ComparisonPackage:
    version: str
    exact_types: tuple[ExactType, ...]
    carriers: tuple[MetricCarrier, ...]
    exact_operations: tuple[ExactOperation, ...]
    enriched_operations: tuple[EnrichedOperation, ...]
    local_contracts: tuple[LocalComparisonContract, ...]
    leaf_contracts: tuple[LeafReaderContract, ...]
    coverage: tuple[OperationCoverage, ...]
    admissible: bool
    rejection_reasons: tuple[str, ...]

    @property
    def digest(self) -> str:
        return canonical_digest(self)


def build_comparison_package(
    *,
    version: str,
    required_operation_ids: Sequence[str],
    exact_types: Sequence[ExactType],
    carriers: Sequence[MetricCarrier],
    exact_operations: Sequence[ExactOperation],
    enriched_operations: Sequence[EnrichedOperation],
    local_contracts: Sequence[LocalComparisonContract],
    leaf_contracts: Sequence[LeafReaderContract],
) -> ComparisonPackage:
    """Build a fail-closed operation coverage table."""
    required = tuple(required_operation_ids)
    if len(set(required)) != len(required):
        raise ValueError("required operation ids must be unique")
    exact_ids = {item.operation_id for item in exact_operations}
    enriched_ids = {item.operation_id for item in enriched_operations}
    contract_ids = {item.operation_id for item in local_contracts}
    coverage = tuple(
        OperationCoverage(
            operation_id=operation_id,
            exact_present=operation_id in exact_ids,
            enriched_present=operation_id in enriched_ids,
            contract_present=operation_id in contract_ids,
            covered=(
                operation_id in exact_ids
                and operation_id in enriched_ids
                and operation_id in contract_ids
            ),
        )
        for operation_id in required
    )
    reasons = [
        f"missing comparison coverage: {item.operation_id}"
        for item in coverage if not item.covered
    ]
    contract_by_id = {item.operation_id: item for item in local_contracts}
    reasons.extend(
        f"unverified local contract: {operation_id}"
        for operation_id in required
        if operation_id in contract_by_id
        and not (
            contract_by_id[operation_id].defect_verified
            and contract_by_id[operation_id].lipschitz_verified
        )
    )
    return ComparisonPackage(
        version=version,
        exact_types=tuple(exact_types),
        carriers=tuple(carriers),
        exact_operations=tuple(exact_operations),
        enriched_operations=tuple(enriched_operations),
        local_contracts=tuple(local_contracts),
        leaf_contracts=tuple(leaf_contracts),
        coverage=coverage,
        admissible=not reasons,
        rejection_reasons=tuple(reasons),
    )


def distance(left: Array, right: Array, norm: NormId) -> float:
    difference = np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
    if norm is NormId.SUP:
        return float(np.max(np.abs(difference))) if difference.size else 0.0
    if norm in {NormId.EUCLIDEAN, NormId.FROBENIUS}:
        return float(np.linalg.norm(difference))
    raise ValueError(f"unsupported comparison norm {norm}")


def compute_local_defect(
    *,
    legal_tuples: Sequence[tuple[Any, ...]],
    exact_apply: ExactApply,
    enriched_apply: EnrichedApply,
    input_encoders: Sequence[Encoder],
    output_encoder: Encoder,
    output_norm: NormId,
) -> float:
    """Exhaustively measure a finite operation square on legal exact tuples."""
    maximum = 0.0
    for values in legal_tuples:
        if len(values) != len(input_encoders):
            raise ValueError("legal tuple has the wrong operation arity")
        enriched_inputs = tuple(
            encoder(value) for encoder, value in zip(input_encoders, values, strict=True)
        )
        observed = enriched_apply(enriched_inputs)
        expected = output_encoder(exact_apply(tuple(values)))
        maximum = max(maximum, distance(observed, expected, output_norm))
    return float(maximum)


def compute_local_defects(**kwargs: Any) -> float:
    """The theorem-facing plural spelling for exhaustive operation squares."""
    return compute_local_defect(**kwargs)


@dataclass(frozen=True, slots=True)
class LeafBoundCheck:
    reader_id: str
    declared_bound: float
    measured_max_error: float
    sample_count: int
    verified: bool


def verify_leaf_bounds(
    *,
    contract: LeafReaderContract,
    field_error_bound: float,
    samples: Sequence[tuple[Array, Array]],
    norm: NormId,
    slack: float = 1e-12,
) -> LeafBoundCheck:
    """Check reader samples against ``alpha e_field + epsilon``."""
    declared = contract.alpha * field_error_bound + contract.epsilon
    measured = max(
        (distance(observed, encoded_exact, norm)
         for observed, encoded_exact in samples),
        default=0.0,
    )
    return LeafBoundCheck(
        reader_id=contract.reader_id,
        declared_bound=float(declared),
        measured_max_error=float(measured),
        sample_count=len(samples),
        verified=measured <= declared + slack,
    )


def verify_lipschitz(
    *,
    samples: Sequence[tuple[tuple[Array, ...], tuple[Array, ...]]],
    enriched_apply: EnrichedApply,
    constants: Sequence[float],
    input_norms: Sequence[NormId],
    output_norm: NormId,
    slack: float = 1e-12,
) -> bool:
    """Check adversarial/property samples against independently supplied bounds."""
    if len(constants) != len(input_norms):
        raise ValueError("Lipschitz constants and input norms differ in arity")
    for left, right in samples:
        if len(left) != len(constants) or len(right) != len(constants):
            raise ValueError("Lipschitz sample has the wrong arity")
        observed = distance(enriched_apply(left), enriched_apply(right), output_norm)
        bound = sum(
            constant * distance(x, y, norm)
            for constant, x, y, norm in zip(
                constants, left, right, input_norms, strict=True
            )
        )
        if observed > bound + slack:
            return False
    return True


class NodeKind(str, Enum):
    LEAF = "leaf"
    OPERATION = "operation"


@dataclass(frozen=True, slots=True)
class DerivationNode:
    node_id: str
    kind: NodeKind
    output_type_id: str
    child_ids: tuple[str, ...]
    operation_id: str | None
    reader_id: str | None
    payload_id: str | None
    provenance: NormalizedProvenance

    def __post_init__(self) -> None:
        if not self.node_id or not self.output_type_id:
            raise ValueError("derivation nodes require ids and output types")
        if self.kind is NodeKind.LEAF:
            if self.child_ids or not self.reader_id or self.operation_id is not None:
                raise ValueError("leaf nodes require one reader and no children")
        elif self.operation_id is None or self.reader_id is not None:
            raise ValueError("operation nodes require an operation id")


@dataclass(frozen=True, slots=True)
class DerivationDAG:
    derivation_id: str
    nodes: tuple[DerivationNode, ...]
    root_id: str

    def __post_init__(self) -> None:
        if not self.derivation_id or not self.nodes:
            raise ValueError("derivations require an id and at least one node")
        seen: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen:
                raise ValueError("derivation node ids must be unique")
            if any(child not in seen for child in node.child_ids):
                raise ValueError("derivation nodes must be in topological order")
            seen.add(node.node_id)
        if self.root_id not in seen:
            raise ValueError("derivation root is absent")

    @property
    def digest(self) -> str:
        return canonical_digest(self)


def eval_exact(
    dag: DerivationDAG,
    *,
    leaf_values: Mapping[str, Any],
    operations: Mapping[str, ExactApply],
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in dag.nodes:
        if node.kind is NodeKind.LEAF:
            if node.node_id not in leaf_values:
                raise KeyError(f"missing exact leaf value {node.node_id}")
            values[node.node_id] = leaf_values[node.node_id]
        else:
            if node.operation_id not in operations:
                raise KeyError(f"missing exact operation {node.operation_id}")
            values[node.node_id] = operations[node.operation_id](
                tuple(values[child] for child in node.child_ids)
            )
    return values


def eval_enriched(
    dag: DerivationDAG,
    *,
    leaf_values: Mapping[str, Array],
    operations: Mapping[str, EnrichedApply],
) -> dict[str, Array]:
    values: dict[str, Array] = {}
    for node in dag.nodes:
        if node.kind is NodeKind.LEAF:
            if node.node_id not in leaf_values:
                raise KeyError(f"missing enriched leaf value {node.node_id}")
            values[node.node_id] = np.asarray(leaf_values[node.node_id], dtype=float)
        else:
            if node.operation_id not in operations:
                raise KeyError(f"missing enriched operation {node.operation_id}")
            values[node.node_id] = np.asarray(
                operations[node.operation_id](
                    tuple(values[child] for child in node.child_ids)
                ),
                dtype=float,
            )
    return values


@dataclass(frozen=True, slots=True)
class FieldComparison:
    extension_id: str
    kappa_boundary_upper: float
    kappa_delta_upper: float
    boundary_mismatch: float
    naturality_defect: float
    beta: float
    field_error_bound: float
    actual_field_error: float | None
    verified: bool
    method: str = "t5-harmonic-comparison/v1"


def compare_field(
    *,
    extension_id: str,
    system: DirichletSystem,
    spectrum: SpectralCertificate,
    exact_cochain: Array,
    field: ThinkingField | None = None,
    verification_slack: float = 1e-9,
) -> FieldComparison:
    """Compute conservative T5-to-exact harmonic comparison constants."""
    y = np.asarray(exact_cochain, dtype=float)
    if y.shape != (len(system.coboundary.coordinate_ids),):
        raise ValueError("exact cochain has the wrong dimension")
    boundary_mismatch = float(
        np.linalg.norm(system.boundary_values - y[list(system.boundary_indices)])
    )
    naturality = float(np.linalg.norm(system.coboundary.dense_delta @ y))
    if not system.interior_indices:
        kappa_boundary = 0.0
        kappa_delta = 0.0
        beta = 0.0
    else:
        if (
            spectrum.status is not SpectralStatus.CERTIFIED
            or spectrum.lower_bound is None
            or spectrum.lower_bound <= 0
        ):
            raise ValueError("field comparison requires a positive T5 spectral bound")
        lower = spectrum.lower_bound
        kappa_boundary = float(
            np.linalg.norm(system.laplacian_ub, ord=2) / lower
        ) if system.boundary_indices else 0.0
        kappa_delta = float(1.0 / math.sqrt(lower))
        beta = kappa_boundary * boundary_mismatch + kappa_delta * naturality
    field_bound = float(math.hypot(boundary_mismatch, beta))
    actual = None if field is None else float(np.linalg.norm(field.values - y))
    verified = actual is None or actual <= field_bound + verification_slack
    return FieldComparison(
        extension_id=extension_id,
        kappa_boundary_upper=kappa_boundary,
        kappa_delta_upper=kappa_delta,
        boundary_mismatch=boundary_mismatch,
        naturality_defect=naturality,
        beta=beta,
        field_error_bound=field_bound,
        actual_field_error=actual,
        verified=verified,
    )


@dataclass(frozen=True, slots=True)
class NodeBudget:
    node_id: str
    budget: float | None
    observed_error: float | None
    tube_satisfied: bool
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NodeContractUse:
    node_id: str
    contract: LocalComparisonContract


@dataclass(frozen=True, slots=True)
class T6Certificate:
    derivation_id: str
    extension_id: str
    comparison_package_id: str
    field_comparison: FieldComparison
    node_contracts: tuple[NodeContractUse, ...]
    node_budgets: tuple[NodeBudget, ...]
    root_budget: float | None
    root_observed_error: float | None
    operation_coverage_complete: bool
    tubes_satisfied: bool
    source_preservation_verified: bool
    admissible: bool
    rejection_reasons: tuple[str, ...]


def propagate_budget(
    *,
    dag: DerivationDAG,
    extension_id: str,
    package: ComparisonPackage,
    field_comparison: FieldComparison,
    exact_values: Mapping[str, Any] | None = None,
    enriched_values: Mapping[str, Array] | None = None,
    encoders: Mapping[str, Encoder] | None = None,
    norms: Mapping[str, NormId] | None = None,
    node_contract_factory: NodeContractFactory | None = None,
) -> T6Certificate:
    """Propagate leaf and operation defects once per topological DAG node."""
    leaf_contracts = {item.reader_id: item for item in package.leaf_contracts}
    contracts = {item.operation_id: item for item in package.local_contracts}
    budgets: dict[str, float] = {}
    records: list[NodeBudget] = []
    contract_uses: list[NodeContractUse] = []
    reasons = list(package.rejection_reasons)
    tubes_satisfied = True
    source_preserved = True
    node_by_id = {node.node_id: node for node in dag.nodes}
    for node in dag.nodes:
        if node.kind is NodeKind.LEAF:
            contract = leaf_contracts.get(node.reader_id or "")
            if contract is None:
                reasons.append(f"missing leaf contract: {node.reader_id}")
                budget = math.inf
                tube_ok = False
            else:
                budget = (
                    contract.alpha * field_comparison.field_error_bound
                    + contract.epsilon
                )
                tube_ok = True
        else:
            contract = contracts.get(node.operation_id or "")
            if contract is None:
                reasons.append(f"missing local contract: {node.operation_id}")
                budget = math.inf
                tube_ok = False
            else:
                child_budgets = tuple(budgets[child] for child in node.child_ids)
                if node_contract_factory is not None:
                    contract = node_contract_factory(node, child_budgets, contract)
                contract_uses.append(NodeContractUse(node.node_id, contract))
                tube_ok = len(child_budgets) == len(contract.tube.input_radii) and all(
                    child_budget <= radius
                    for child_budget, radius in zip(
                        child_budgets, contract.tube.input_radii, strict=True
                    )
                )
                if not tube_ok:
                    reasons.append(f"tube exceeded at node: {node.node_id}")
                budget = contract.declared_epsilon + sum(
                    constant * child_budget
                    for constant, child_budget in zip(
                        contract.lipschitz_constants, child_budgets, strict=True
                    )
                ) if len(child_budgets) == len(contract.lipschitz_constants) else math.inf
            child_sources = {
                ref
                for child_id in node.child_ids
                for ref in node_by_id[child_id].provenance.observations
            }
            if not child_sources.issubset(set(node.provenance.observations)):
                source_preserved = False
        budgets[node.node_id] = float(budget)
        tubes_satisfied = tubes_satisfied and tube_ok
        observed = None
        if (
            exact_values is not None
            and enriched_values is not None
            and encoders is not None
            and norms is not None
            and node.node_id in exact_values
            and node.node_id in enriched_values
        ):
            observed = distance(
                enriched_values[node.node_id],
                encoders[node.output_type_id](exact_values[node.node_id]),
                norms[node.output_type_id],
            )
            if math.isfinite(budget) and observed > budget + 1e-9:
                reasons.append(f"observed error exceeds budget: {node.node_id}")
        records.append(NodeBudget(
            node_id=node.node_id,
            budget=float(budget) if math.isfinite(budget) else None,
            observed_error=observed,
            tube_satisfied=tube_ok,
            source_ids=tuple(
                sorted(canonical_digest(ref) for ref in node.provenance.observations)
            ),
        ))
    if not source_preserved:
        reasons.append("derivation provenance does not preserve child sources")
    root_record = next(item for item in records if item.node_id == dag.root_id)
    admissible = (
        package.admissible
        and field_comparison.verified
        and tubes_satisfied
        and source_preserved
        and not reasons
        and root_record.budget is not None
    )
    return T6Certificate(
        derivation_id=dag.derivation_id,
        extension_id=extension_id,
        comparison_package_id=package.digest,
        field_comparison=field_comparison,
        node_contracts=tuple(contract_uses),
        node_budgets=tuple(records),
        root_budget=root_record.budget,
        root_observed_error=root_record.observed_error,
        operation_coverage_complete=package.admissible,
        tubes_satisfied=tubes_satisfied,
        source_preservation_verified=source_preserved,
        admissible=admissible,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


@dataclass(frozen=True, slots=True)
class BehaviorInstance:
    extension_id: str
    exact_behavior_ids: tuple[tuple[str, str], ...]
    outputs: tuple[tuple[str, tuple[float, ...]], ...]
    budgets: tuple[tuple[str, float], ...]


class SeparationStatus(str, Enum):
    SEPARATING = "SEPARATING"
    LITERAL_COLLISION = "LITERAL_COLLISION"
    BUDGET_CONSUMED = "BUDGET_CONSUMED"
    UNCERTIFIED_BUDGET = "UNCERTIFIED_BUDGET"
    INSUFFICIENT_BEHAVIORS = "INSUFFICIENT_BEHAVIORS"


@dataclass(frozen=True, slots=True)
class SeparationPair:
    left_extension_id: str
    right_extension_id: str
    witness_derivation_id: str | None
    gamma: float
    left_budget: float
    right_budget: float
    remaining_margin: float
    literal_collision: bool
    budget_certified: bool
    separated: bool


@dataclass(frozen=True, slots=True)
class SeparationCertificate:
    status: SeparationStatus
    behavior_class_count: int
    compared_pairs: tuple[SeparationPair, ...]
    separating: bool
    method: str = "finite-D-retained-separation/v1"


def check_separation(
    instances: Sequence[BehaviorInstance],
    *,
    norm: NormId = NormId.SUP,
) -> SeparationCertificate:
    """Check every distinct exact behavior class for one retained witness."""
    behavior_key = lambda item: item.exact_behavior_ids
    class_representatives: dict[
        tuple[tuple[str, str], ...], BehaviorInstance
    ] = {}
    for instance in instances:
        class_representatives.setdefault(behavior_key(instance), instance)
    representatives = tuple(class_representatives.values())
    if len(representatives) < 2:
        return SeparationCertificate(
            status=SeparationStatus.INSUFFICIENT_BEHAVIORS,
            behavior_class_count=len(representatives),
            compared_pairs=(),
            # D-separation is universal over pairs of distinct behavior
            # classes, hence vacuously true for zero or one class.  The status
            # remains explicit so this is never reported as evidence about
            # multi-behavior capacity.
            separating=True,
        )
    pairs: list[SeparationPair] = []
    for left_index, left in enumerate(representatives):
        left_outputs = dict(left.outputs)
        left_budgets = dict(left.budgets)
        for right in representatives[left_index + 1:]:
            right_outputs = dict(right.outputs)
            right_budgets = dict(right.budgets)
            derivations = sorted(set(left_outputs) & set(right_outputs))
            budget_certified = all(
                derivation_id in left_budgets and derivation_id in right_budgets
                for derivation_id in derivations
            )
            candidates = []
            for derivation_id in derivations:
                if (
                    derivation_id not in left_budgets
                    or derivation_id not in right_budgets
                ):
                    continue
                gamma = distance(
                    np.asarray(left_outputs[derivation_id]),
                    np.asarray(right_outputs[derivation_id]),
                    norm,
                )
                left_budget = float(left_budgets[derivation_id])
                right_budget = float(right_budgets[derivation_id])
                candidates.append((
                    gamma - left_budget - right_budget,
                    gamma,
                    derivation_id,
                    left_budget,
                    right_budget,
                ))
            if not candidates:
                best = (0.0, 0.0, None, 0.0, 0.0)
            else:
                best = max(candidates, key=lambda item: (item[0], item[1], item[2]))
            margin, gamma, witness, left_budget, right_budget = best
            literal = bool(candidates) and all(item[1] == 0.0 for item in candidates)
            pairs.append(SeparationPair(
                left_extension_id=left.extension_id,
                right_extension_id=right.extension_id,
                witness_derivation_id=witness,
                gamma=float(gamma),
                left_budget=float(left_budget),
                right_budget=float(right_budget),
                remaining_margin=float(margin),
                literal_collision=literal,
                budget_certified=budget_certified,
                separated=budget_certified and margin > 0.0,
            ))
    if all(item.separated for item in pairs):
        status = SeparationStatus.SEPARATING
    elif any(not item.budget_certified for item in pairs):
        status = SeparationStatus.UNCERTIFIED_BUDGET
    elif any(item.literal_collision for item in pairs):
        status = SeparationStatus.LITERAL_COLLISION
    else:
        status = SeparationStatus.BUDGET_CONSUMED
    return SeparationCertificate(
        status=status,
        behavior_class_count=len(representatives),
        compared_pairs=tuple(pairs),
        separating=status is SeparationStatus.SEPARATING,
    )
