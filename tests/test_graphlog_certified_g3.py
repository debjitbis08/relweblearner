"""G3 GraphLog derivation coverage and local comparison tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from relweblearner.bench.graphlog_certified.derivations import (
    PROOF_VECTOR_TYPE,
    compile_derivations,
    compile_query_derivations,
)
from relweblearner.bench.graphlog_certified.enrichment import (
    GraphLogAlgebra,
    build_graphlog_comparison_package,
    certify_graphlog_comparison,
)
from relweblearner.bench.graphlog_certified.ingest import (
    OpaqueEdgeEvent,
    OpaqueQueryEpisode,
    OpaqueToken,
    OpaqueView,
    RuntimeViewBundle,
    TypedAnchor,
    ingest_world,
)
from relweblearner.bench.graphlog_certified.linearization import (
    build_anchor_boundary,
    build_linearization,
    encode_extension,
)
from relweblearner.bench.graphlog_certified.model import (
    ObservationFamily,
    TriangleFact,
    build_scope,
    classify_extensions,
)
from relweblearner.certification.provenance import ObservationRef, normalize_provenance
from relweblearner.certification.t5 import (
    SolverConfig,
    assemble_coboundary,
    bound_spectrum,
    certify_kernel,
    partition_dirichlet,
    solve_dirichlet,
)
from relweblearner.certification.t6 import (
    compare_field,
    propagate_budget,
)
from relweblearner.certification.types import canonical_data


ROOT = Path(__file__).resolve().parents[1]


def _token(view: str, name: str) -> OpaqueToken:
    return OpaqueToken(view, name)


def _ref(view: str, index: int, *, split: str = "train") -> ObservationRef:
    return ObservationRef(
        "graphlog/test", "g3-fixture", split, f"{split}:000000", index, view
    )


def _family(prefix: str = "") -> ObservationFamily:
    a1, a2, a3 = (f"{prefix}{name}" for name in ("a1", "a2", "a3"))
    b1, b2, b3 = (f"{prefix}{name}" for name in ("b1", "b2", "b3"))
    triangle_a = TriangleFact(
        (_token("A", a1), _token("A", a2), _token("A", a3)),
        3,
        normalize_provenance(_ref("A", i) for i in range(3)),
    )
    triangle_b = TriangleFact(
        (_token("B", b1), _token("B", b2), _token("B", b3)),
        5,
        normalize_provenance(_ref("B", 10 + i) for i in range(3)),
    )
    anchors = (
        TypedAnchor(
            _token("A", a1), _token("B", b1),
            normalize_provenance((_ref("A", 20), _ref("B", 20))),
        ),
        TypedAnchor(
            _token("A", a2), _token("B", b2),
            normalize_provenance((_ref("A", 21), _ref("B", 21))),
        ),
    )
    return ObservationFamily(
        "graphlog-certified/v1", "graphlog/test", "g3-fixture",
        (triangle_a,), (triangle_b,), anchors, (),
        triangle_a.positions, triangle_b.positions,
    )


def _edge(
    view: str, index: int, tail: int, head: int, relation: str
) -> OpaqueEdgeEvent:
    return OpaqueEdgeEvent(
        tail, head, _token(view, relation), _ref(view, index, split="test")
    )


def _runtime(*, with_paths: bool = True, prefix: str = "") -> RuntimeViewBundle:
    if with_paths:
        edges_a = (
            _edge("A", 0, 0, 1, f"{prefix}a1"),
            _edge("A", 2, 2, 3, f"{prefix}a3"),
            _edge("A", 3, 0, 3, f"{prefix}a3"),
        )
        edges_b = (_edge("B", 1, 1, 2, f"{prefix}b2"),)
    else:
        edges_a = (_edge("A", 0, 0, 1, f"{prefix}a1"),)
        edges_b = ()
    query_a = OpaqueQueryEpisode("test:000000", 0, 3, edges_a)
    query_b = OpaqueQueryEpisode("test:000000", 0, 3, edges_b)
    view_a = OpaqueView("A", (), (query_a,))
    view_b = OpaqueView("B", (), (query_b,))
    refs = tuple(sorted(edge.observation for edge in (*edges_a, *edges_b)))
    return RuntimeViewBundle(
        "graphlog-certified/v1", "graphlog/test", "g3-fixture", 0,
        (view_a, view_b), (), refs,
    )


def _operator_fixture(prefix: str = ""):
    family = _family(prefix)
    scope = build_scope(family)
    extension = classify_extensions(family, scope).solutions[0]
    linearization = build_linearization(family, scope)
    boundary = build_anchor_boundary(family, linearization)
    system = partition_dirichlet(
        assemble_coboundary(linearization.core), boundary.core
    )
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field, _solver = solve_dirichlet(
        system, SolverConfig(field_tolerance=1e-12),
        kernel=kernel, spectrum=spectrum,
    )
    assert field is not None
    comparison = compare_field(
        extension_id="fixture-extension",
        system=system,
        spectrum=spectrum,
        exact_cochain=encode_extension(extension, linearization).reshape(-1),
        field=field,
    )
    return family, scope, extension, linearization, field, comparison


def test_compiler_exhausts_paths_and_names_every_semantics_affecting_operation():
    runtime = _runtime()
    dags, path_counts = compile_query_derivations(runtime)
    assert path_counts == (("query:test:000000", 2),)
    dag = dags[0]
    operations = {node.operation_id for node in dag.nodes if node.operation_id}
    assert operations == {
        "translate_B_to_A", "compose", "span_aggregate",
        "path_aggregate", "decode_output",
    }
    assert all("fallback" not in (node.operation_id or "") for node in dag.nodes)
    assert dag.nodes[-1].operation_id == "decode_output"
    canonical_data(dag)


def test_no_path_compiles_to_typed_empty_proof_without_majority_fallback():
    dags, path_counts = compile_query_derivations(_runtime(with_paths=False))
    assert path_counts == (("query:test:000000", 0),)
    dag = dags[0]
    assert [node.reader_id for node in dag.nodes if node.reader_id] == ["empty_proof"]
    assert [node.operation_id for node in dag.nodes if node.operation_id] == [
        "decode_output"
    ]
    assert dag.nodes[0].output_type_id == PROOF_VECTOR_TYPE


def test_exact_bridge_package_covers_all_six_operations_with_zero_observed_error():
    family, scope, extension, linearization, field, comparison = _operator_fixture()
    compiled = compile_derivations(_runtime(), scope.candidate_identities)
    derivations = (*compiled.query_derivations, *compiled.identity_derivations)
    algebra = GraphLogAlgebra(
        observations=family,
        extension=extension,
        linearization=linearization,
        field=field,
    )
    runtime_package = build_graphlog_comparison_package(
        algebra=algebra,
        derivations=derivations,
        field_comparison=comparison,
    )
    package = runtime_package.package
    assert package.admissible
    assert {item.operation_id for item in package.coverage} == {
        "translate_B_to_A", "compose", "span_aggregate", "path_aggregate",
        "decode_output", "decode_identity",
    }
    assert all(item.covered for item in package.coverage)
    assert all(item.defect_verified for item in package.local_contracts)
    assert all(item.lipschitz_verified for item in package.local_contracts)

    for dag in derivations:
        exact = algebra.evaluate_exact(dag)
        enriched = algebra.evaluate_enriched(dag)
        certificate = propagate_budget(
            dag=dag,
            extension_id="fixture-extension",
            package=package,
            field_comparison=comparison,
            exact_values=exact,
            enriched_values=enriched,
            encoders=algebra.encoders,
            norms=algebra.norms,
        )
        assert certificate.admissible
        assert certificate.root_budget == 0.0
        assert certificate.root_observed_error == 0.0
        canonical_data(certificate)


def test_translation_and_rule_tensor_agree_with_exact_partial_bijection_bridge():
    family, _scope, extension, linearization, field, _comparison = _operator_fixture()
    algebra = GraphLogAlgebra(
        observations=family, extension=extension,
        linearization=linearization, field=field,
    )
    b2 = algebra.payload_index["B:b2"]
    a2 = algebra.payload_index["A:a2"]
    exact = algebra.exact_operations["translate_B_to_A"]((frozenset((b2,)),))
    enriched = algebra.enriched_operations["translate_B_to_A"]((
        algebra.encode_relation_set(frozenset((b2,))),
    ))
    assert exact == frozenset((a2,))
    np.testing.assert_array_equal(enriched, algebra.encode_relation_set(exact))
    assert (algebra.payload_index["A:a1"], a2, algebra.payload_index["A:a3"]) \
        in algebra.exact_rules


def test_graphlog_report_takes_uniform_root_supremum_and_builds_behavior_record():
    family, scope, extension, linearization, field, comparison = _operator_fixture()
    compiled = compile_derivations(_runtime(), scope.candidate_identities)
    derivations = (*compiled.query_derivations, *compiled.identity_derivations)
    algebra = GraphLogAlgebra(
        observations=family, extension=extension,
        linearization=linearization, field=field,
    )
    certified = certify_graphlog_comparison(
        extension_id="fixture-extension",
        algebra=algebra,
        derivations=derivations,
        field_comparison=comparison,
    )
    assert certified.report.admissible
    assert certified.report.uniform_root_budget == 0.0
    assert certified.report.maximum_observed_root_error == 0.0
    assert len(certified.report.certificates) == len(derivations)
    assert len(certified.behavior.outputs) == len(derivations)
    assert len(certified.behavior.budgets) == len(derivations)
    canonical_data(certified)


def test_compiled_family_and_certificate_have_no_evaluation_gold_fields():
    family, scope, extension, linearization, field, comparison = _operator_fixture()
    compiled = compile_derivations(_runtime(), scope.candidate_identities)
    algebra = GraphLogAlgebra(
        observations=family, extension=extension,
        linearization=linearization, field=field,
    )
    package = build_graphlog_comparison_package(
        algebra=algebra,
        derivations=(*compiled.query_derivations, *compiled.identity_derivations),
        field_comparison=comparison,
    ).package
    serialized = repr(canonical_data((compiled, package)))
    assert "query_target" not in serialized
    assert "true_map" not in serialized
    assert "oracle_rules" not in serialized


def test_local_contracts_are_equivariant_under_opaque_token_renaming():
    tables = []
    for prefix in ("", "z"):
        family, scope, extension, linearization, field, comparison = \
            _operator_fixture(prefix)
        compiled = compile_derivations(
            _runtime(prefix=prefix), scope.candidate_identities
        )
        algebra = GraphLogAlgebra(
            observations=family, extension=extension,
            linearization=linearization, field=field,
        )
        package = build_graphlog_comparison_package(
            algebra=algebra,
            derivations=(*compiled.query_derivations, *compiled.identity_derivations),
            field_comparison=comparison,
        ).package
        tables.append(tuple(
            (
                contract.operation_id,
                contract.measured_max_defect,
                contract.lipschitz_constants,
                contract.legal_tuple_count,
            )
            for contract in package.local_contracts
        ))
    assert tables[0] == tables[1]


@pytest.mark.skipif(
    not (ROOT / "data/graphlog/graphlog_v1.1/train/rule_20/train.jsonl").exists(),
    reason="GraphLog corpus absent",
)
def test_rule20_full_query_family_is_exhaustively_compiled_without_pruning():
    base = ROOT / "data/graphlog/graphlog_v1.1/train/rule_20"
    raw = {
        "name": "rule_20",
        "train": [
            json.loads(line) for line in
            (base / "train.jsonl").read_text(encoding="utf-8").splitlines()[:150]
        ],
        "test": [
            json.loads(line) for line in
            (base / "test.jsonl").read_text(encoding="utf-8").splitlines()
        ],
        "rules": {},
    }
    runtime, _evaluation_key = ingest_world(raw, seed=0)
    dags, path_counts = compile_query_derivations(runtime)
    assert len(dags) == 1000
    assert sum(count for _derivation_id, count in path_counts) == 24_162
    assert sum(len(dag.nodes) for dag in dags) == 554_847
    operations = {
        node.operation_id for dag in dags for node in dag.nodes if node.operation_id
    }
    assert operations == {
        "translate_B_to_A", "compose", "span_aggregate",
        "path_aggregate", "decode_output",
    }
