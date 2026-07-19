"""GraphLog exact/enriched algebra and finite local comparison package."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from ...certification.t5 import ThinkingField
from ...certification.t6 import (
    BehaviorInstance,
    ComparisonPackage,
    EnrichedOperation,
    ExactOperation,
    ExactType,
    FieldComparison,
    LeafReaderContract,
    LocalComparisonContract,
    MetricCarrier,
    Tube,
    T6Certificate,
    build_comparison_package,
    compute_local_defect,
    eval_enriched,
    eval_exact,
    propagate_budget,
)
from ...certification.types import NormId, canonical_digest
from .derivations import (
    IDENTITY_MATRIX_TYPE,
    PROOF_VECTOR_TYPE,
    RELATION_SET_TYPE,
    DerivationDAG,
    token_payload,
)
from .ingest import OpaqueToken
from .linearization import GraphLogLinearization, encode_extension, field_matrix
from .model import IdentityExtension, ObservationFamily
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


@dataclass(frozen=True, slots=True)
class GraphLogVocabulary:
    tokens: tuple[OpaqueToken, ...]
    a_dimension: int

    @property
    def dimension(self) -> int:
        return len(self.tokens)

    @property
    def payloads(self) -> tuple[str, ...]:
        return tuple(token_payload(token) for token in self.tokens)


def _exact_key(value: Any) -> Any:
    if isinstance(value, frozenset):
        return ("set", *sorted(value))
    if isinstance(value, tuple):
        return value
    return value


class GraphLogAlgebra:
    """Per-extension implementations; metadata lives in ComparisonPackage."""

    def __init__(
        self,
        *,
        observations: ObservationFamily,
        extension: IdentityExtension,
        linearization: GraphLogLinearization,
        field: ThinkingField,
        spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
    ) -> None:
        self.observations = observations
        self.extension = extension
        self.linearization = linearization
        self.field = field
        self.spec = spec
        self.vocabulary = GraphLogVocabulary(
            (*linearization.a_tokens, *linearization.b_tokens),
            len(linearization.a_tokens),
        )
        self.index = {token: i for i, token in enumerate(self.vocabulary.tokens)}
        self.payload_index = {
            token_payload(token): i for token, i in self.index.items()
        }
        self.dimension = self.vocabulary.dimension
        self.identity_dimension = len(linearization.core.coordinate_ids)
        self.exact_identity = tuple(
            int(value) for value in encode_extension(extension, linearization).reshape(-1)
        )
        self.q_exact, self.exact_token_map = self._exact_translation()
        self.q_enriched = self._enriched_translation()
        self.exact_rules = self._exact_rules()
        self.enriched_rule_tensor = self._enriched_rule_tensor()
        self._translate_cache: dict[bytes, np.ndarray] = {}
        self._compose_cache: dict[tuple[bytes, bytes], np.ndarray] = {}
        self._span_cache: dict[tuple[bytes, bytes], np.ndarray] = {}
        self.exact_operations = {
            "translate_B_to_A": self._exact_translate,
            "compose": self._exact_compose,
            "span_aggregate": self._exact_span,
            "path_aggregate": self._exact_path,
            "decode_output": self._exact_decode,
            "decode_identity": lambda _values: self.exact_identity,
        }
        self.enriched_operations = {
            "translate_B_to_A": self._enriched_translate,
            "compose": self._enriched_compose,
            "span_aggregate": self._enriched_span,
            "path_aggregate": self._enriched_path,
            "decode_output": self._enriched_decode,
            "decode_identity": lambda _values: np.asarray(field.values, dtype=float),
        }
        self.encoders = {
            RELATION_SET_TYPE: self.encode_relation_set,
            PROOF_VECTOR_TYPE: self.encode_proof_vector,
            IDENTITY_MATRIX_TYPE: self.encode_identity,
        }
        self.norms = {
            RELATION_SET_TYPE: spec.decision_norm,
            PROOF_VECTOR_TYPE: spec.decision_norm,
            IDENTITY_MATRIX_TYPE: spec.field_norm,
        }

    def _exact_translation(self) -> tuple[np.ndarray, dict[int, int]]:
        q = np.zeros((self.dimension, self.dimension), dtype=float)
        mapping: dict[int, int] = {}
        inverse = {b: a for a, b in self.extension.pairs}
        for index, token in enumerate(self.vocabulary.tokens):
            if token.view_id == "A":
                target = index
            elif token in inverse:
                target = self.index[inverse[token]]
            else:
                target = index
            mapping[index] = target
            q[target, index] = 1.0
        return q, mapping

    def _enriched_translation(self) -> np.ndarray:
        q = np.zeros((self.dimension, self.dimension), dtype=float)
        n_a = len(self.linearization.a_tokens)
        scores = field_matrix(self.field.values, self.linearization)
        q[:n_a, :n_a] = np.eye(n_a)
        for b_index in range(len(self.linearization.b_tokens)):
            column = n_a + b_index
            q[:n_a, column] = scores[:, b_index]
            q[column, column] = 1.0 - float(np.sum(scores[:, b_index]))
        return q

    def _exact_rules(self) -> frozenset[tuple[int, int, int]]:
        rules: set[tuple[int, int, int]] = set()
        for triangle in self.observations.triangles_a:
            rules.add(tuple(self.index[token] for token in triangle.positions))
        for triangle in self.observations.triangles_b:
            rules.add(tuple(
                self.exact_token_map[self.index[token]] for token in triangle.positions
            ))
        return frozenset(rules)

    def _enriched_rule_tensor(self) -> np.ndarray:
        tensor_a = np.zeros((self.dimension,) * 3, dtype=float)
        tensor_b = np.zeros_like(tensor_a)
        for triangle in self.observations.triangles_a:
            p, q, h = (self.index[token] for token in triangle.positions)
            tensor_a[h, p, q] = 1.0
        for triangle in self.observations.triangles_b:
            p, q, h = (self.index[token] for token in triangle.positions)
            tensor_b[h, p, q] = 1.0
        translated_b = np.einsum(
            "ia,jb,kc,abc->ijk",
            self.q_enriched,
            self.q_enriched,
            self.q_enriched,
            tensor_b,
            optimize=True,
        )
        return np.maximum(tensor_a, translated_b)

    def encode_relation_set(self, value: frozenset[int]) -> np.ndarray:
        encoded = np.zeros(self.dimension, dtype=float)
        if value:
            encoded[list(value)] = 1.0
        return encoded

    def encode_proof_vector(self, value: tuple[int, ...]) -> np.ndarray:
        encoded = np.asarray(value, dtype=float)
        if encoded.shape != (self.dimension,):
            raise ValueError("proof vector has the wrong vocabulary dimension")
        return encoded

    def encode_identity(self, value: tuple[int, ...]) -> np.ndarray:
        encoded = np.asarray(value, dtype=float)
        if encoded.shape != (self.identity_dimension,):
            raise ValueError("identity encoding has the wrong stalk dimension")
        return encoded

    def _exact_translate(self, values: tuple[Any, ...]) -> frozenset[int]:
        (relations,) = values
        return frozenset(self.exact_token_map[index] for index in relations)

    def _exact_compose(self, values: tuple[Any, ...]) -> frozenset[int]:
        left, right = values
        return frozenset(
            h for p, q, h in self.exact_rules if p in left and q in right
        )

    @staticmethod
    def _exact_span(values: tuple[Any, ...]) -> frozenset[int]:
        left, right = values
        return frozenset((*left, *right))

    def _exact_path(self, values: tuple[Any, ...]) -> tuple[int, ...]:
        proof, relations = values
        result = list(proof)
        for index in relations:
            result[index] += 1
        return tuple(result)

    @staticmethod
    def _exact_decode(values: tuple[Any, ...]) -> tuple[int, ...]:
        (proof,) = values
        return tuple(proof)

    def _enriched_translate(self, values: tuple[np.ndarray, ...]) -> np.ndarray:
        (relations,) = values
        key = relations.tobytes()
        if key not in self._translate_cache:
            self._translate_cache[key] = self.q_enriched @ relations
        return self._translate_cache[key].copy()

    def _enriched_compose(self, values: tuple[np.ndarray, ...]) -> np.ndarray:
        left, right = values
        key = (left.tobytes(), right.tobytes())
        if key not in self._compose_cache:
            self._compose_cache[key] = np.einsum(
                "hpq,p,q->h", self.enriched_rule_tensor, left, right, optimize=True
            )
        return self._compose_cache[key].copy()

    def _enriched_span(self, values: tuple[np.ndarray, ...]) -> np.ndarray:
        key = (values[0].tobytes(), values[1].tobytes())
        if key not in self._span_cache:
            self._span_cache[key] = np.maximum(values[0], values[1])
        return self._span_cache[key].copy()

    @staticmethod
    def _enriched_path(values: tuple[np.ndarray, ...]) -> np.ndarray:
        return values[0] + values[1]

    @staticmethod
    def _enriched_decode(values: tuple[np.ndarray, ...]) -> np.ndarray:
        return values[0].copy()

    def exact_leaf_values(self, dag: DerivationDAG) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for node in dag.nodes:
            if node.reader_id == "relation_token":
                if node.payload_id not in self.payload_index:
                    raise KeyError(f"unknown opaque relation payload {node.payload_id}")
                values[node.node_id] = frozenset((self.payload_index[node.payload_id],))
            elif node.reader_id == "empty_proof":
                values[node.node_id] = (0,) * self.dimension
        return values

    def enriched_leaf_values(self, dag: DerivationDAG) -> dict[str, np.ndarray]:
        exact = self.exact_leaf_values(dag)
        return {
            node.node_id: self.encoders[node.output_type_id](exact[node.node_id])
            for node in dag.nodes if node.reader_id is not None
        }

    def evaluate_exact(self, dag: DerivationDAG) -> dict[str, Any]:
        return eval_exact(
            dag, leaf_values=self.exact_leaf_values(dag),
            operations=self.exact_operations,
        )

    def evaluate_enriched(self, dag: DerivationDAG) -> dict[str, np.ndarray]:
        return eval_enriched(
            dag, leaf_values=self.enriched_leaf_values(dag),
            operations=self.enriched_operations,
        )


@dataclass(frozen=True, slots=True)
class GraphLogComparisonRuntime:
    package: ComparisonPackage
    derivation_ids: tuple[str, ...]
    exact_root_ids: tuple[tuple[str, str], ...]
    enriched_root_digests: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class GraphLogT6Report:
    package: ComparisonPackage
    certificates: tuple[T6Certificate, ...]
    uniform_root_budget: float | None
    maximum_observed_root_error: float | None
    admissible: bool


@dataclass(frozen=True, slots=True)
class GraphLogCertifiedComparison:
    report: GraphLogT6Report
    behavior: BehaviorInstance


def _operation_types() -> dict[str, tuple[tuple[str, ...], str]]:
    return {
        "translate_B_to_A": ((RELATION_SET_TYPE,), RELATION_SET_TYPE),
        "compose": ((RELATION_SET_TYPE, RELATION_SET_TYPE), RELATION_SET_TYPE),
        "span_aggregate": (
            (RELATION_SET_TYPE, RELATION_SET_TYPE), RELATION_SET_TYPE,
        ),
        "path_aggregate": ((PROOF_VECTOR_TYPE, RELATION_SET_TYPE), PROOF_VECTOR_TYPE),
        "decode_output": ((PROOF_VECTOR_TYPE,), PROOF_VECTOR_TYPE),
        "decode_identity": ((), IDENTITY_MATRIX_TYPE),
    }


def _fallback_legal_tuples(
    operation_id: str, algebra: GraphLogAlgebra
) -> tuple[tuple[Any, ...], ...]:
    empty = frozenset()
    singletons = tuple(frozenset((index,)) for index in range(algebra.dimension))
    zero = (0,) * algebra.dimension
    if operation_id == "translate_B_to_A":
        b_start = algebra.vocabulary.a_dimension
        return tuple((frozenset((index,)),) for index in range(b_start, algebra.dimension))
    if operation_id == "compose":
        return tuple((left, right) for left in singletons for right in singletons)
    if operation_id == "span_aggregate":
        return ((empty, empty), *((empty, value) for value in singletons))
    if operation_id == "path_aggregate":
        return ((zero, empty), *((zero, value) for value in singletons))
    if operation_id == "decode_output":
        return ((zero,),)
    if operation_id == "decode_identity":
        return ((),)
    raise KeyError(operation_id)


def _analytic_lipschitz(
    operation_id: str,
    algebra: GraphLogAlgebra,
    tube_radius: float,
) -> tuple[float, ...]:
    if operation_id == "translate_B_to_A":
        return (float(np.max(np.sum(np.abs(algebra.q_enriched), axis=1))),)
    if operation_id == "compose":
        tensor_mass = float(np.max(np.sum(
            np.abs(algebra.enriched_rule_tensor), axis=(1, 2)
        )))
        bound = tensor_mass * (1.0 + tube_radius)
        return (bound, bound)
    if operation_id in {"span_aggregate", "path_aggregate"}:
        return (1.0, 1.0)
    if operation_id == "decode_output":
        return (1.0,)
    if operation_id == "decode_identity":
        return ()
    raise KeyError(operation_id)


def _node_contract_factory(algebra: GraphLogAlgebra):
    tensor_mass = float(np.max(np.sum(
        np.abs(algebra.enriched_rule_tensor), axis=(1, 2)
    )))

    def instantiate(node, child_budgets, base):
        if any(not math.isfinite(value) for value in child_budgets):
            return base
        radii = tuple(
            float(np.nextafter(max(0.0, value), math.inf))
            for value in child_budgets
        )
        if node.operation_id == "compose":
            left_radius, right_radius = radii
            constants = (
                tensor_mass * (1.0 + right_radius),
                tensor_mass * (1.0 + left_radius),
            )
        else:
            constants = base.lipschitz_constants
        return replace(
            base,
            lipschitz_method=(
                "rule-tensor-node-tube-analytic-sup/v1"
                if node.operation_id == "compose"
                else base.lipschitz_method
            ),
            lipschitz_constants=tuple(float(value) for value in constants),
            tube=Tube("node-encoded-child-budget-ball/v1", radii),
        )

    return instantiate


def build_graphlog_comparison_package(
    *,
    algebra: GraphLogAlgebra,
    derivations: Sequence[DerivationDAG],
    field_comparison: FieldComparison,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
    tube_radius: float = 4.0,
) -> GraphLogComparisonRuntime:
    """Build finite D-specific legal tuples and all six operation contracts."""
    if not math.isfinite(tube_radius) or tube_radius <= 0:
        raise ValueError("comparison tube radius must be finite and positive")
    operation_types = _operation_types()
    legal: dict[str, dict[str, tuple[Any, ...]]] = {}
    for operation_id in spec.derivation_operations:
        legal[operation_id] = {}
        for values in _fallback_legal_tuples(operation_id, algebra):
            key = canonical_digest(tuple(_exact_key(item) for item in values))
            legal[operation_id].setdefault(key, values)
    legal_values_by_type: dict[str, dict[str, Any]] = {
        RELATION_SET_TYPE: {}, PROOF_VECTOR_TYPE: {}, IDENTITY_MATRIX_TYPE: {},
    }
    root_ids: list[tuple[str, str]] = []
    enriched_root_digests: list[tuple[str, str]] = []
    for dag in derivations:
        exact_values = algebra.evaluate_exact(dag)
        enriched_values = algebra.evaluate_enriched(dag)
        for node in dag.nodes:
            value = exact_values[node.node_id]
            key = canonical_digest(_exact_key(value))
            legal_values_by_type[node.output_type_id].setdefault(key, value)
            if node.operation_id in legal:
                child_values = tuple(
                    exact_values[child] for child in node.child_ids
                )
                tuple_id = canonical_digest(tuple(
                    _exact_key(item) for item in child_values
                ))
                legal[node.operation_id].setdefault(tuple_id, child_values)
        root_ids.append((
            dag.derivation_id,
            canonical_digest(_exact_key(exact_values[dag.root_id])),
        ))
        enriched_root_digests.append((
            dag.derivation_id,
            canonical_digest(tuple(
                float(value) for value in enriched_values[dag.root_id]
            )),
        ))

    # Structural/fallback values make operation coverage independent of which
    # operation happens to occur in a particular query DAG.
    for operation_id, tuples_by_id in legal.items():
        input_types, output_type = operation_types[operation_id]
        for values in tuples_by_id.values():
            for type_id, value in zip(input_types, values, strict=True):
                legal_values_by_type[type_id].setdefault(
                    canonical_digest(_exact_key(value)), value
                )
            output = algebra.exact_operations[operation_id](values)
            legal_values_by_type[output_type].setdefault(
                canonical_digest(_exact_key(output)), output
            )

    dimensions = {
        RELATION_SET_TYPE: algebra.dimension,
        PROOF_VECTOR_TYPE: algebra.dimension,
        IDENTITY_MATRIX_TYPE: algebra.identity_dimension,
    }
    exact_types = tuple(
        ExactType(type_id, "graphlog-zero-one-or-count/v1", tuple(sorted(values)))
        for type_id, values in legal_values_by_type.items()
    )
    carriers = tuple(
        MetricCarrier(
            type_id,
            f"real-vector:{type_id}",
            dimensions[type_id],
            algebra.norms[type_id],
        )
        for type_id in dimensions
    )
    exact_operations = []
    enriched_operations = []
    contracts = []
    carrier_id = {item.type_id: item.carrier_id for item in carriers}
    for operation_id in spec.derivation_operations:
        input_types, output_type = operation_types[operation_id]
        tuples = tuple(legal[operation_id].values())
        exact_operations.append(ExactOperation(
            operation_id=operation_id,
            version=f"graphlog-exact/{operation_id}/v1",
            input_type_ids=input_types,
            output_type_id=output_type,
            legal_tuple_ids=tuple(
                canonical_digest(tuple(_exact_key(item) for item in values))
                for values in tuples
            ),
            provenance_rule="normalized-union-of-child-sources/v1",
        ))
        enriched_operations.append(EnrichedOperation(
            operation_id=operation_id,
            version=f"graphlog-enriched/{operation_id}/v1",
            input_carrier_ids=tuple(carrier_id[item] for item in input_types),
            output_carrier_id=carrier_id[output_type],
            equivariance_check="opaque-A/B-permutation-equivariant/v1",
        ))
        measured = compute_local_defect(
            legal_tuples=tuples,
            exact_apply=algebra.exact_operations[operation_id],
            enriched_apply=algebra.enriched_operations[operation_id],
            input_encoders=tuple(algebra.encoders[item] for item in input_types),
            output_encoder=algebra.encoders[output_type],
            output_norm=algebra.norms[output_type],
        )
        if operation_id == "decode_identity":
            declared_base = max(measured, field_comparison.field_error_bound)
        else:
            declared_base = measured
        declared = (
            float(np.nextafter(declared_base, math.inf))
            if declared_base else 0.0
        )
        lipschitz = _analytic_lipschitz(operation_id, algebra, tube_radius)
        contracts.append(LocalComparisonContract(
            operation_id=operation_id,
            defect_method="finite-D-legal-tuple-exhaustion/v1",
            declared_epsilon=declared,
            measured_max_defect=measured,
            lipschitz_method=(
                "rule-tensor-analytic-sup/v1" if operation_id == "compose"
                else "analytic-coordinate-bound/v1"
            ),
            lipschitz_constants=lipschitz,
            tube=Tube(
                "encoded-legal-input-ball/v1", (tube_radius,) * len(input_types)
            ),
            legal_tuple_count=len(tuples),
            defect_verified=measured <= declared,
            lipschitz_verified=True,
        ))

    leaf_contracts = (
        LeafReaderContract(
            "relation_token", RELATION_SET_TYPE,
            carrier_id[RELATION_SET_TYPE], 0.0, 0.0,
            "preserve-observation-ref/v1",
        ),
        LeafReaderContract(
            "empty_proof", PROOF_VECTOR_TYPE,
            carrier_id[PROOF_VECTOR_TYPE], 0.0, 0.0,
            "structural-empty-no-source/v1",
        ),
    )
    package = build_comparison_package(
        version=spec.comparison_version,
        required_operation_ids=spec.derivation_operations,
        exact_types=exact_types,
        carriers=carriers,
        exact_operations=exact_operations,
        enriched_operations=enriched_operations,
        local_contracts=contracts,
        leaf_contracts=leaf_contracts,
    )
    return GraphLogComparisonRuntime(
        package=package,
        derivation_ids=tuple(dag.derivation_id for dag in derivations),
        exact_root_ids=tuple(root_ids),
        enriched_root_digests=tuple(enriched_root_digests),
    )


def certify_graphlog_comparison(
    *,
    extension_id: str,
    algebra: GraphLogAlgebra,
    derivations: Sequence[DerivationDAG],
    field_comparison: FieldComparison,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
    tube_radius: float = 4.0,
) -> GraphLogCertifiedComparison:
    """Evaluate D once per node and report uniform extension-relative budgets."""
    runtime = build_graphlog_comparison_package(
        algebra=algebra,
        derivations=derivations,
        field_comparison=field_comparison,
        spec=spec,
        tube_radius=tube_radius,
    )
    certificates: list[T6Certificate] = []
    exact_behavior_ids: list[tuple[str, str]] = []
    outputs: list[tuple[str, tuple[float, ...]]] = []
    budgets: list[tuple[str, float]] = []
    for dag in derivations:
        exact_values = algebra.evaluate_exact(dag)
        enriched_values = algebra.evaluate_enriched(dag)
        certificate = propagate_budget(
            dag=dag,
            extension_id=extension_id,
            package=runtime.package,
            field_comparison=field_comparison,
            exact_values=exact_values,
            enriched_values=enriched_values,
            encoders=algebra.encoders,
            norms=algebra.norms,
            node_contract_factory=_node_contract_factory(algebra),
        )
        certificates.append(certificate)
        exact_root = exact_values[dag.root_id]
        exact_behavior_ids.append((
            dag.derivation_id, canonical_digest(_exact_key(exact_root))
        ))
        outputs.append((
            dag.derivation_id,
            tuple(float(value) for value in algebra.encoders[
                next(node.output_type_id for node in dag.nodes
                     if node.node_id == dag.root_id)
            ](exact_root)),
        ))
        if certificate.root_budget is not None:
            budgets.append((dag.derivation_id, certificate.root_budget))
    all_budgeted = len(budgets) == len(derivations)
    root_budgets = [item[1] for item in budgets]
    observed = [
        certificate.root_observed_error for certificate in certificates
        if certificate.root_observed_error is not None
    ]
    report = GraphLogT6Report(
        package=runtime.package,
        certificates=tuple(certificates),
        uniform_root_budget=max(root_budgets) if all_budgeted and root_budgets else (
            0.0 if all_budgeted else None
        ),
        maximum_observed_root_error=max(observed) if observed else None,
        admissible=runtime.package.admissible and all(
            certificate.admissible for certificate in certificates
        ),
    )
    behavior = BehaviorInstance(
        extension_id=extension_id,
        exact_behavior_ids=tuple(exact_behavior_ids),
        outputs=tuple(outputs),
        budgets=tuple(budgets),
    )
    return GraphLogCertifiedComparison(report=report, behavior=behavior)
