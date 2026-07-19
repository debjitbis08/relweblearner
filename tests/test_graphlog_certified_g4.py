"""G4 GraphLog identity hardening from ordered G1--G3 premises."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from relweblearner.bench.graphlog_certified.derivations import (
    compile_identity_derivations,
)
from relweblearner.bench.graphlog_certified.enrichment import (
    GraphLogAlgebra,
    certify_graphlog_comparison,
)
from relweblearner.bench.graphlog_certified.hardening import (
    certify_identity_target,
)
from relweblearner.bench.graphlog_certified.ingest import (
    OpaqueToken,
    TypedAnchor,
    ingest_world,
    select_anchors,
)
from relweblearner.bench.graphlog_certified.linearization import (
    build_anchor_boundary,
    build_linearization,
    encode_extension,
)
from relweblearner.bench.graphlog_certified.model import (
    CrossViewRelationIdentity,
    ExactNegativeIdentity,
    ObservationFamily,
    TriangleFact,
    build_observations,
    build_scope,
    classify_extensions,
    classify_target,
    triangle_components,
)
from relweblearner.bench.graphlog_certified.policy import (
    CommitmentValue,
    PolicyCode,
    permit,
)
from relweblearner.certification.provenance import ObservationRef, normalize_provenance
from relweblearner.certification.t5 import (
    SolverConfig,
    assemble_coboundary,
    bound_spectrum,
    certify_kernel,
    partition_dirichlet,
    run_t5,
)
from relweblearner.certification.t6 import (
    SeparationStatus,
    check_separation,
    compare_field,
)
from relweblearner.certification.t7 import CommitmentOutcome
from relweblearner.certification.types import canonical_data


ROOT = Path(__file__).resolve().parents[1]


def _token(view: str, name: str) -> OpaqueToken:
    return OpaqueToken(view, name)


def _ref(view: str, index: int) -> ObservationRef:
    return ObservationRef(
        "graphlog/test", "g4-fixture", "train", "train:000000", index, view
    )


def _family(*, first_anchor_two_origins: bool = True) -> ObservationFamily:
    triangle_a = TriangleFact(
        (_token("A", "a1"), _token("A", "a2"), _token("A", "a3")),
        3, normalize_provenance(_ref("A", i) for i in range(3)),
    )
    triangle_b = TriangleFact(
        (_token("B", "b1"), _token("B", "b2"), _token("B", "b3")),
        5, normalize_provenance(_ref("B", 10 + i) for i in range(3)),
    )
    first_refs = (_ref("A", 20), _ref("B", 20)) \
        if first_anchor_two_origins else (_ref("A", 20),)
    anchors = (
        TypedAnchor(
            _token("A", "a1"), _token("B", "b1"),
            normalize_provenance(first_refs),
        ),
        TypedAnchor(
            _token("A", "a2"), _token("B", "b2"),
            normalize_provenance((_ref("A", 21), _ref("B", 21))),
        ),
    )
    return ObservationFamily(
        "graphlog-certified/v1", "graphlog/test", "g4-fixture",
        (triangle_a,), (triangle_b,), anchors, (),
        triangle_a.positions, triangle_b.positions,
    )


def _operator(family: ObservationFamily):
    scope = build_scope(family)
    extensions = classify_extensions(family, scope)
    linearization = build_linearization(family, scope)
    boundary = build_anchor_boundary(family, linearization)
    system = partition_dirichlet(
        assemble_coboundary(linearization.core), boundary.core
    )
    t5_run = run_t5(system, SolverConfig(field_tolerance=1e-12))
    assert t5_run.field is not None
    return scope, extensions, linearization, system, t5_run


def _target_comparison(
    family, scope, extensions, linearization, system, t5_run, target,
):
    dag = next(
        dag for dag in compile_identity_derivations(scope.candidate_identities)
        if dag.derivation_id == f"identity:{target.a_token.value}:{target.b_token.value}"
    )
    kernel = certify_kernel(system)
    spectrum = bound_spectrum(system, kernel)
    field_comparison = compare_field(
        extension_id="extension:0",
        system=system,
        spectrum=spectrum,
        exact_cochain=encode_extension(
            extensions.solutions[0], linearization
        ).reshape(-1),
        field=t5_run.field,
    )
    algebra = GraphLogAlgebra(
        observations=family,
        extension=extensions.solutions[0],
        linearization=linearization,
        field=t5_run.field,
    )
    comparison = certify_graphlog_comparison(
        extension_id="extension:0",
        algebra=algebra,
        derivations=(dag,),
        field_comparison=field_comparison,
    )
    separation = check_separation((comparison.behavior,))
    return dag, comparison.report.certificates[0], separation


def test_exact_bridge_positive_identity_commits_with_all_six_premises():
    family = _family()
    scope, extensions, linearization, system, t5_run = _operator(family)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    target_result = classify_target(family, scope, target, extensions=extensions)
    policy = permit(
        family, scope, target, target_result, CommitmentValue.IDENTICAL
    )
    dag, t6, separation = _target_comparison(
        family, scope, extensions, linearization, system, t5_run, target
    )
    assert separation.status is SeparationStatus.INSUFFICIENT_BEHAVIORS
    assert separation.separating  # vacuous for the singleton behavior class
    decision = certify_identity_target(
        observations=family,
        scope=scope,
        target=target,
        extension_classification=extensions,
        target_classification=target_result,
        policy=policy,
        linearization=linearization,
        t5_run=t5_run,
        target_dag=dag,
        target_t6_certificates=(t6,),
        separation=separation,
    )
    assert decision.certificate.outcome is CommitmentOutcome.COMMIT
    assert all(item.satisfied for item in decision.certificate.premises)
    assert decision.margin is not None and decision.margin.uniform_margin == 0.5
    assert decision.observed_in_hardener_region
    assert decision.perturbation is not None
    assert decision.perturbation.propagated.output_radius == 0.0
    assert {term.term_id for term in decision.perturbation.propagated.terms} == {
        "rational-vs-float-operator", "finite-solver-residual",
        "floating-evaluator-decoder", "zero-initial-boundary",
    }
    canonical_data(decision)


def test_negative_singleton_is_an_exclusion_and_never_a_merge_commit():
    family = _family()
    scope, extensions, linearization, _system, t5_run = _operator(family)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b2"))
    target_result = classify_target(family, scope, target, extensions=extensions)
    policy = permit(family, scope, target, target_result, CommitmentValue.DISTINCT)
    separation = check_separation(())
    decision = certify_identity_target(
        observations=family, scope=scope, target=target,
        extension_classification=extensions,
        target_classification=target_result, policy=policy,
        linearization=linearization, t5_run=t5_run,
        target_dag=None, target_t6_certificates=(), separation=separation,
    )
    assert decision.certificate.outcome is CommitmentOutcome.EXCLUSION
    assert decision.certificate.commitment == "DISTINCT"
    assert not decision.observed_in_hardener_region


def test_p1_refusal_short_circuits_before_margin_or_perturbation():
    family = _family(first_anchor_two_origins=False)
    scope, extensions, linearization, _system, t5_run = _operator(family)
    target = CrossViewRelationIdentity(_token("A", "a1"), _token("B", "b1"))
    target_result = classify_target(family, scope, target, extensions=extensions)
    policy = permit(
        family, scope, target, target_result, CommitmentValue.IDENTICAL
    )
    assert policy.code is PolicyCode.P1_INSUFFICIENT_ORIGINS
    decision = certify_identity_target(
        observations=family, scope=scope, target=target,
        extension_classification=extensions,
        target_classification=target_result, policy=policy,
        linearization=linearization, t5_run=t5_run,
        target_dag=None, target_t6_certificates=(),
        separation=check_separation(()),
    )
    assert decision.certificate.outcome is CommitmentOutcome.ABSTAIN
    assert decision.certificate.code == "ABSTAIN_POLICY_PERMIT"
    assert decision.margin is None
    assert decision.perturbation is None


def test_admitted_p2_conflict_is_structurally_rejected_before_hardening():
    base = _family()
    conflict = ExactNegativeIdentity(
        _token("A", "a1"), _token("B", "b1"), "p2:fixture",
        normalize_provenance((_ref("A", 30), _ref("B", 30))),
    )
    family = replace(base, exact_negative_identities=(conflict,))
    scope, extensions, linearization, _system, t5_run = _operator(family)
    target = CrossViewRelationIdentity(_token("A", "a1"), _token("B", "b1"))
    target_result = classify_target(family, scope, target, extensions=extensions)
    policy = permit(
        family, scope, target, target_result, CommitmentValue.IDENTICAL
    )
    decision = certify_identity_target(
        observations=family, scope=scope, target=target,
        extension_classification=extensions,
        target_classification=target_result, policy=policy,
        linearization=linearization, t5_run=t5_run,
        target_dag=None, target_t6_certificates=(),
        separation=check_separation(()),
    )
    assert decision.certificate.outcome is CommitmentOutcome.REJECT
    assert decision.certificate.code == "STRUCTURAL_EMPTY"
    assert decision.margin is None and decision.perturbation is None


@pytest.mark.skipif(
    not (ROOT / "data/graphlog/graphlog_v1.1/train/rule_20/train.jsonl").exists(),
    reason="GraphLog corpus absent",
)
def test_rule20_real_nonanchor_target_abstains_when_budget_exceeds_margin():
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
    pre_anchor = build_observations(runtime)
    anchors = select_anchors(
        runtime.opaque_overlap_events,
        triangle_components(pre_anchor.triangles_a),
    )
    family = build_observations(runtime, anchors)
    scope, extensions, linearization, system, t5_run = _operator(family)
    anchored_pairs = {(item.a_token, item.b_token) for item in family.anchors}
    a_token, b_token = next(
        pair for pair in extensions.solutions[0].pairs if pair not in anchored_pairs
    )
    target = CrossViewRelationIdentity(a_token, b_token)
    target_result = classify_target(family, scope, target, extensions=extensions)
    policy = permit(
        family, scope, target, target_result, CommitmentValue.IDENTICAL
    )
    dag, t6, separation = _target_comparison(
        family, scope, extensions, linearization, system, t5_run, target
    )
    decision = certify_identity_target(
        observations=family, scope=scope, target=target,
        extension_classification=extensions,
        target_classification=target_result, policy=policy,
        linearization=linearization, t5_run=t5_run,
        target_dag=dag, target_t6_certificates=(t6,), separation=separation,
    )
    assert decision.certificate.outcome is CommitmentOutcome.ABSTAIN
    assert decision.certificate.approximation_budget is not None
    assert decision.certificate.decision_margin == 0.5
    assert decision.certificate.approximation_budget > 0.5
