"""G0/G0b tests for the certified GraphLog boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from relweblearner.bench.graphlog_certified import evaluation as EVAL
from relweblearner.bench.graphlog_certified.ingest import ingest_world, select_anchors
from relweblearner.bench.graphlog_certified.spec import (
    DEFAULT_SPEC,
    VALIDATION_WORLDS,
)
from relweblearner.certification.types import canonical_bytes, canonical_data


def _raw_world(query_target: str = "r0") -> dict:
    labels = [f"r{i}" for i in range(8)]
    train_edges = [(i, i + 1, relation) for i, relation in enumerate(labels)]
    # Add triangles so all visible relations can later participate in an
    # opaque component map; ingest itself does not mine them.
    train_edges += [(0, 2, "r2"), (2, 4, "r4"), (0, 4, "r6")]
    return {
        "name": "rule_synthetic",
        "train": [
            {"edges": train_edges, "target": "r7"},
            {"edges": list(reversed(train_edges)), "target": "r6"},
        ],
        "test": [{
            "edges": [(0, 1, "r0"), (1, 2, "r1"), (0, 2, "r2")],
            "query": (0, 2, query_target),
        }],
        "rules": {("r0", "r1"): "r2"},
    }


def _walk_json(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)
    elif isinstance(value, str):
        yield value


def test_frozen_spec_copies_the_reviewed_validation_cohort():
    assert len(VALIDATION_WORLDS) == 44
    assert "rule_20" in VALIDATION_WORLDS
    assert "rule_27" in VALIDATION_WORLDS
    assert DEFAULT_SPEC.max_path == 5
    assert DEFAULT_SPEC.anchor_budget == 6
    assert DEFAULT_SPEC.extension_semantics_version \
        == "maximal-supported-partial-bijection/v1"
    assert len(DEFAULT_SPEC.digest) == 64
    assert replace(DEFAULT_SPEC).digest == DEFAULT_SPEC.digest
    assert replace(
        DEFAULT_SPEC, extension_semantics_version="total-assignment/v0",
    ).digest != DEFAULT_SPEC.digest


def test_ingest_is_deterministic_and_gold_changes_do_not_reach_runtime():
    runtime_0, key_0 = ingest_world(_raw_world("r0"), seed=0)
    runtime_1, key_1 = ingest_world(_raw_world("target_only_gold"), seed=0)

    # The new answer need not occur anywhere in the observable vocabulary.
    # Byte identity proves query gold cannot even alter opaque token numbering.
    assert canonical_bytes(runtime_0) == canonical_bytes(runtime_1)
    assert EVAL.score_query_predictions(key_0, ["r0"])["correct"] == 1
    assert EVAL.score_query_predictions(key_1, ["r0"])["correct"] == 0


def test_runtime_serialization_has_no_gold_or_permutation_route():
    raw = _raw_world()
    runtime, key = ingest_world(raw, seed=4)
    serialized = canonical_data(runtime)
    flattened = set(_walk_json(serialized))

    forbidden_fields = {
        "perm_a", "perm_b", "true_map", "query_target", "query_targets",
        "oracle_rules", "hide_a", "hide_b", "raw_relation", "target",
    }
    assert flattened.isdisjoint(forbidden_fields)
    assert flattened.isdisjoint({f"r{i}" for i in range(8)})
    assert repr(key) == "EvaluationKey(<sealed>)"
    with pytest.raises(TypeError, match="unsupported canonical"):
        canonical_data(key)


def test_overlap_events_are_co_witnessed_and_normalize_two_origins():
    runtime, key = ingest_world(_raw_world(), seed=2)
    events = runtime.opaque_overlap_events
    assert events
    event = events[0]
    assert event.a_observation.episode_id == event.b_observation.episode_id
    assert event.a_observation.edge_index == event.b_observation.edge_index
    assert event.a_observation in runtime.observation_refs
    assert event.b_observation in runtime.observation_refs
    assert event.provenance.origin_ids == {
        (DEFAULT_SPEC.dataset_version, "A"),
        (DEFAULT_SPEC.dataset_version, "B"),
    }
    assert EVAL.is_true_identity(key, event.a_token.value, event.b_token.value)


def test_anchor_selection_reads_only_opaque_events_and_a_components():
    runtime, _key = ingest_world(_raw_world(), seed=3)
    events = runtime.opaque_overlap_events
    distinct_a = tuple(dict.fromkeys(event.a_token for event in events))
    components = {token: index % 2 for index, token in enumerate(distinct_a)}

    anchors = select_anchors(events, components, budget=6)
    assert len(anchors) == min(6, len(distinct_a))
    assert len({anchor.a_token for anchor in anchors}) == len(anchors)
    assert len({anchor.b_token for anchor in anchors}) == len(anchors)
    assert all(len(anchor.provenance.origin_ids) == 2 for anchor in anchors)


def test_query_views_are_pre_rendered_without_the_answer():
    runtime, _key = ingest_world(_raw_world(), seed=5)
    for view_id in ("A", "B"):
        query = runtime.view(view_id).query_episodes[0]
        assert (query.source_node, query.destination_node) == (0, 2)
        assert all(edge.relation.view_id == view_id for edge in query.edges)
        assert all(edge.observation.split == "test" for edge in query.edges)
