"""G1 exact structural layer tests on hand-enumerated triangle webs."""

from __future__ import annotations

from dataclasses import replace

import pytest

from relweblearner.bench.graphlog_certified.ingest import (
    OpaqueToken,
    TypedAnchor,
    ingest_world,
    select_anchors,
)
from relweblearner.bench.graphlog_certified.model import (
    CountingScope,
    CrossViewRelationIdentity,
    ExactNegativeIdentity,
    ObservationFamily,
    TriangleFact,
    build_observations,
    build_scope,
    check_support_closed,
    classify_extensions,
    classify_target,
    triangle_components,
)
from relweblearner.bench.graphlog_certified.policy import (
    CommitmentValue,
    DetectorOutput,
    PolicyCode,
    adapt_detector_output,
    admit_exact_negative_observation,
    permit,
)
from relweblearner.certification.extensions import SolverLimits
from relweblearner.certification.provenance import ObservationRef, normalize_provenance
from relweblearner.certification.types import ExtensionCardinality, TargetCardinality


def _token(view: str, name: str) -> OpaqueToken:
    return OpaqueToken(view, name)


def _ref(view: str, index: int) -> ObservationRef:
    return ObservationRef(
        "graphlog/test", "fixture", "train", "train:000000", index, view,
    )


def _triangle(view: str, names: tuple[str, str, str], offset: int) -> TriangleFact:
    return TriangleFact(
        tuple(_token(view, name) for name in names),  # type: ignore[arg-type]
        3,
        normalize_provenance(_ref(view, offset + i) for i in range(3)),
    )


def _anchor(a: str, b: str, index: int, *, both_origins: bool = True) -> TypedAnchor:
    refs = [_ref("A", index)]
    if both_origins:
        refs.append(_ref("B", index))
    return TypedAnchor(
        _token("A", a), _token("B", b), normalize_provenance(refs),
    )


def _family(
    *,
    b_triangles: tuple[tuple[str, str, str], ...] = (("b1", "b2", "b3"),),
    anchors: tuple[TypedAnchor, ...] | None = None,
    negatives: tuple[ExactNegativeIdentity, ...] = (),
    prefix: str = "",
) -> ObservationFamily:
    if prefix:
        a_names = tuple(f"{prefix}{name}" for name in ("a1", "a2", "a3"))
        transformed_b = tuple(
            tuple(f"{prefix}{name}" for name in triangle) for triangle in b_triangles
        )
        if anchors is None:
            anchors = (
                _anchor(a_names[0], f"{prefix}b1", 20),
                _anchor(a_names[1], f"{prefix}b2", 21),
            )
    else:
        a_names = ("a1", "a2", "a3")
        transformed_b = b_triangles
    if anchors is None:
        anchors = (_anchor("a1", "b1", 20), _anchor("a2", "b2", 21))
    triangles_a = (_triangle("A", a_names, 0),)
    triangles_b = tuple(
        _triangle("B", triangle, 10 + 3 * i)
        for i, triangle in enumerate(transformed_b)
    )
    tokens_a = tuple(sorted({token for fact in triangles_a for token in fact.positions}))
    tokens_b = tuple(sorted({token for fact in triangles_b for token in fact.positions}))
    return ObservationFamily(
        "graphlog-certified/v1",
        "graphlog/test",
        "fixture",
        triangles_a,
        triangles_b,
        anchors,
        negatives,
        tokens_a,
        tokens_b,
    )


def test_support_closure_propagates_only_named_triangle_candidates():
    family = _family()
    scope = build_scope(family)
    pairs = {(c.a_token.value, c.b_token.value): c for c in scope.candidate_identities}

    assert set(pairs) == {("a1", "b1"), ("a2", "b2"), ("a3", "b3")}
    derived = pairs[("a3", "b3")]
    assert derived.support_kind == "triangle_propagation"
    assert len(derived.provenance.origin_ids) == 2
    assert derived.provenance.derivations
    assert check_support_closed(scope, family)
    assert not check_support_closed(replace(scope, support_closed=False), family)
    assert set(triangle_components(family.triangles_a)) == {
        _token("A", "a1"), _token("A", "a2"), _token("A", "a3"),
    }
    assert len(set(triangle_components(family.triangles_a).values())) == 1


def test_isomorphic_web_has_one_exact_extension_and_positive_target():
    family = _family()
    scope = build_scope(family)
    extensions = classify_extensions(family, scope)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    target_result = classify_target(family, scope, target, extensions=extensions)

    assert extensions.verdict is ExtensionCardinality.SINGLETON
    assert extensions.exhaustion.exhausted
    assert extensions.exhaustion.solution_count == 1
    assert extensions.exhaustion.solution_digest
    assert target_result.verdict is TargetCardinality.IDENTICAL


def test_non_target_pair_is_structurally_distinct_in_singleton_extension():
    family = _family()
    scope = build_scope(family)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b2"))
    assert classify_target(family, scope, target).verdict is TargetCardinality.DISTINCT


def test_unanchored_web_has_one_empty_partial_extension_not_ambient_guesses():
    family = _family(anchors=())
    scope = build_scope(family)
    result = classify_extensions(family, scope)
    target = CrossViewRelationIdentity(_token("A", "a1"), _token("B", "b1"))
    assert scope.candidate_identities == ()
    assert result.verdict is ExtensionCardinality.SINGLETON
    assert result.solutions[0].pairs == ()
    assert classify_target(family, scope, target, extensions=result).verdict \
        is TargetCardinality.DISTINCT


def test_symmetric_supported_heads_give_many_extensions_and_many_target_values():
    family = _family(b_triangles=(
        ("b1", "b2", "b3"),
        ("b1", "b2", "b4"),
    ))
    scope = build_scope(family)
    extensions = classify_extensions(family, scope)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    target_result = classify_target(family, scope, target, extensions=extensions)

    assert extensions.verdict is ExtensionCardinality.MANY
    assert extensions.exhaustion.solution_count == 2
    assert target_result.verdict is TargetCardinality.MANY
    assert target_result.projection.output_values == ("IDENTICAL", "DISTINCT")


def test_anchored_composition_conflict_has_no_extension():
    anchors = (
        _anchor("a1", "b1", 20),
        _anchor("a2", "b2", 21),
        _anchor("a3", "b3", 22),
    )
    family = _family(
        b_triangles=(("b1", "b2", "b4"),), anchors=anchors,
    )
    result = classify_extensions(family, build_scope(family))
    assert result.verdict is ExtensionCardinality.EMPTY
    assert result.exhaustion.solution_count == 0


def test_anchor_injectivity_conflict_has_no_extension():
    anchors = (
        _anchor("a1", "b1", 20),
        _anchor("a2", "b1", 21),
    )
    family = _family(anchors=anchors)
    result = classify_extensions(family, build_scope(family))
    assert result.verdict is ExtensionCardinality.EMPTY


def test_exact_negative_fact_changes_constraints_but_detector_score_does_not():
    base = _family(anchors=(
        _anchor("a1", "b1", 20),
        _anchor("a2", "b2", 21),
        _anchor("a3", "b3", 22),
    ))
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    detector = DetectorOutput("heuristic/v1", 0.999, normalize_provenance((_ref("A", 40),)))
    refused = adapt_detector_output(target.a_token, target.b_token, detector)
    assert not refused.admitted and refused.exact_fact is None
    assert classify_extensions(base, build_scope(base)).verdict is ExtensionCardinality.SINGLETON

    admitted = admit_exact_negative_observation(
        target.a_token,
        target.b_token,
        admission_id="exact-negative/fixture",
        provenance=normalize_provenance((_ref("A", 40), _ref("B", 40))),
    )
    assert admitted.exact_fact is not None
    with_negative = replace(base, exact_negative_identities=(admitted.exact_fact,))
    result = classify_extensions(with_negative, build_scope(with_negative))
    assert result.verdict is ExtensionCardinality.EMPTY


def test_spuriously_scoped_orphan_stays_unmapped_in_unique_maximal_extension():
    """A's a4 is hidden in B; b4 only looks compatible in one triangle.

    The second ordered A triangle disproves that candidate.  Total assignment
    made the whole CSP empty; maximal partiality must retain the anchored true
    map and leave the orphan unmapped.
    """
    anchors = (
        _anchor("a1", "b1", 20),
        _anchor("a2", "b2", 21),
        _anchor("a3", "b3", 22),
    )
    triangles_a = (
        _triangle("A", ("a1", "a2", "a4"), 0),
        _triangle("A", ("a4", "a1", "a2"), 3),
    )
    triangles_b = (_triangle("B", ("b1", "b2", "b4"), 10),)
    family = ObservationFamily(
        "graphlog-certified/v1",
        "graphlog/test",
        "fixture",
        triangles_a,
        triangles_b,
        anchors,
        (),
        tuple(sorted({token for fact in triangles_a for token in fact.positions}
                     | {_token("A", "a3")})),
        tuple(sorted({token for fact in triangles_b for token in fact.positions}
                     | {_token("B", "b3")})),
    )
    scope = build_scope(family)
    assert ("a4", "b4") in {
        (candidate.a_token.value, candidate.b_token.value)
        for candidate in scope.candidate_identities
    }

    result = classify_extensions(family, scope)
    assert result.verdict is ExtensionCardinality.SINGLETON
    assert result.solutions[0].pairs == tuple(sorted(
        (anchor.a_token, anchor.b_token) for anchor in anchors
    ))
    orphan_target = CrossViewRelationIdentity(
        _token("A", "a4"), _token("B", "b4"),
    )
    assert classify_target(
        family, scope, orphan_target, extensions=result,
    ).verdict is TargetCardinality.DISTINCT
    a4_domain = next(
        domain for domain in result.exhaustion.candidate_domains
        if domain.variable_id == "A:a4"
    )
    assert [candidate.value_id for candidate in a4_domain.candidates] \
        == ["B:b4", "UNMAPPED"]


def test_resource_limit_is_fail_closed_unknown_not_a_fourth_exact_state():
    family = _family()
    result = classify_extensions(
        family, build_scope(family), limits=SolverLimits(max_search_nodes=1),
    )
    assert result.verdict is ExtensionCardinality.UNKNOWN
    assert not result.exhaustion.exhausted
    assert result.exhaustion.solution_digest is None
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    projected = classify_target(family, build_scope(family), target, extensions=result)
    assert projected.verdict is TargetCardinality.UNKNOWN


def test_relabeling_preserves_cardinality_and_target_classification():
    original = _family(b_triangles=(
        ("b1", "b2", "b3"), ("b1", "b2", "b4"),
    ))
    renamed = _family(
        b_triangles=(("b1", "b2", "b3"), ("b1", "b2", "b4")),
        prefix="opaque_",
    )
    result_0 = classify_extensions(original, build_scope(original))
    result_1 = classify_extensions(renamed, build_scope(renamed))
    target_0 = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    target_1 = CrossViewRelationIdentity(
        _token("A", "opaque_a3"), _token("B", "opaque_b3"),
    )
    assert result_0.verdict is result_1.verdict is ExtensionCardinality.MANY
    assert result_0.exhaustion.solution_count == result_1.exhaustion.solution_count
    assert classify_target(original, build_scope(original), target_0).verdict \
        is classify_target(renamed, build_scope(renamed), target_1).verdict


def test_p1_requires_two_normalized_view_origins_for_positive_identity():
    family = _family()
    scope = build_scope(family)
    target = CrossViewRelationIdentity(_token("A", "a3"), _token("B", "b3"))
    classification = classify_target(family, scope, target)
    verdict = permit(
        family, scope, target, classification, CommitmentValue.IDENTICAL,
    )
    assert verdict.permitted and verdict.code is PolicyCode.PERMIT
    assert len(verdict.origin_ids) == 2

    one_origin = _family(
        b_triangles=(),
        anchors=(_anchor("a1", "b1", 20, both_origins=False),),
    )
    one_scope = build_scope(one_origin)
    one_target = CrossViewRelationIdentity(_token("A", "a1"), _token("B", "b1"))
    one_class = classify_target(one_origin, one_scope, one_target)
    refused = permit(
        one_origin, one_scope, one_target, one_class, CommitmentValue.IDENTICAL,
    )
    assert not refused.permitted
    assert refused.code is PolicyCode.P1_INSUFFICIENT_ORIGINS


def test_invalid_scope_and_wrong_view_targets_are_rejected():
    family = _family()
    scope = build_scope(family)
    broken = replace(scope, candidate_identities=())
    with pytest.raises(ValueError, match="support-closed"):
        classify_extensions(family, broken)
    stale_semantics = replace(scope, extension_semantics_version="total-map/v0")
    with pytest.raises(ValueError, match="extension semantics"):
        classify_extensions(family, stale_semantics)
    with pytest.raises(ValueError, match="one A and one B"):
        CrossViewRelationIdentity(_token("B", "b1"), _token("A", "a1"))


def test_runtime_adapter_accepts_only_co_witnessed_anchors_and_not_eval_key():
    labels = [f"raw{i}" for i in range(8)]
    raw = {
        "name": "adapter_fixture",
        "train": [{
            "edges": (
                [(i, i + 1, label) for i, label in enumerate(labels)]
                + [(0, 2, "raw2"), (2, 4, "raw4"), (0, 4, "raw6")]
            ),
            "target": "raw7",
        }],
        "test": [{"edges": [], "query": (0, 1, "sealed_answer")}],
        "rules": {},
    }
    runtime, evaluation_key = ingest_world(raw, seed=0)
    preliminary = build_observations(runtime)
    components = triangle_components(preliminary.triangles_a)
    anchors = select_anchors(runtime.opaque_overlap_events, components)
    family = build_observations(runtime, anchors)
    assert family.anchors == anchors
    assert check_support_closed(build_scope(family), family)

    with pytest.raises(TypeError, match="TypedAnchor"):
        build_observations(runtime, (evaluation_key,))  # type: ignore[arg-type]
    fake = _anchor("not_observed", "also_not_observed", 99)
    with pytest.raises(ValueError, match="co-witness"):
        build_observations(runtime, (fake,))
