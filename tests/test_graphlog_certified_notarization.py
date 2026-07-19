"""G0b baseline notarization, semantic hashing, and tamper checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from relweblearner.bench.graphlog_certified.notarization import (
    ARTIFACT_SPECS,
    DEFAULT_MANIFEST,
    MANIFEST_SCHEMA,
    build_manifest,
    pointer_get,
    semantic_sha256,
    validate_manifest,
)
from relweblearner.certification.types import canonical_digest


ROOT = Path(__file__).resolve().parents[1]


def _checked_manifest() -> dict:
    return json.loads((ROOT / DEFAULT_MANIFEST).read_text(encoding="utf-8"))


def _resign(manifest: dict) -> None:
    body = {key: value for key, value in manifest.items() if key != "manifest_id"}
    manifest["manifest_id"] = f"sha256:{canonical_digest(body)}"


def test_semantic_hash_excludes_only_declared_json_pointers():
    first = {"summary": {"elapsed_s": 1.0, "accuracy": 0.5}, "rows": [1, 2]}
    slower = {"summary": {"elapsed_s": 99.0, "accuracy": 0.5}, "rows": [1, 2]}
    changed = {"summary": {"elapsed_s": 1.0, "accuracy": 0.6}, "rows": [1, 2]}

    exclusions = ("/summary/elapsed_s",)
    assert semantic_sha256(first, exclusions) == semantic_sha256(slower, exclusions)
    assert semantic_sha256(first, exclusions) != semantic_sha256(changed, exclusions)
    assert pointer_get(first, "/summary/accuracy") == 0.5
    with pytest.raises((KeyError, ValueError)):
        semantic_sha256(first, ("/summary/not_present",))


def test_checked_manifest_round_trips_and_pins_required_headlines():
    manifest = _checked_manifest()
    validate_manifest(manifest, ROOT)
    assert manifest["schema_version"] == MANIFEST_SCHEMA
    assert len(manifest["artifacts"]) == len(ARTIFACT_SPECS) == 6
    assert manifest["manifest_id"].startswith("sha256:")

    artifacts = {row["artifact_id"]: row for row in manifest["artifacts"]}
    assert artifacts["multiweb_graphlog"]["expected_fields"]["/summary"][
        "mean_ensemble"
    ] == 0.5143636363636364
    assert artifacts["graded_graphlog"]["expected_fields"]["/summary"][
        "mean_graded"
    ] == 0.5358636363636363
    assert artifacts["rule20_factorial"]["expected_fields"][
        "/cells/C+R/acc"
    ] == 0.669
    assert artifacts["rule27_diagnosis"]["expected_fields"][
        "/repair_curve"
    ][1] == {"repaired": "R_9_-", "evicted": [], "acc": 0.496}
    assert artifacts["rule27_graded_causal"]["expected_fields"][""][
        "episodes_total"
    ] == 1000

    world_collection = artifacts["multiweb_graphlog"]["collections"][0]
    episode_collection = artifacts["rule27_diagnosis"]["collections"][0]
    assert world_collection["count"] == 44
    assert episode_collection["count"] == 1000
    assert world_collection["canonical_sha256"]
    assert episode_collection["identity_sha256"]


def test_manifest_detects_tampering_even_with_recomputed_outer_id():
    manifest = _checked_manifest()
    tampered = copy.deepcopy(manifest)
    tampered["artifacts"][0]["semantic_sha256"] = "0" * 64
    _resign(tampered)
    with pytest.raises(ValueError, match="artifact multiweb_graphlog mismatch"):
        validate_manifest(tampered, ROOT)


def test_standalone_validator_reconstructs_data_membership():
    tampered = copy.deepcopy(_checked_manifest())
    data = tampered["input_groups"]["data"]
    data["files"] = [
        record for record in data["files"] if "/rule_50/" not in record["path"]
    ]
    data["id"] = f"sha256:{canonical_digest(data['files'])}"
    for artifact in tampered["artifacts"]:
        if "data" in artifact["producing_ids"]:
            artifact["producing_ids"]["data"] = data["id"]
    _resign(tampered)

    with pytest.raises(ValueError, match="path set mismatch"):
        validate_manifest(tampered, ROOT, verify_data=True)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("semantic_hash_version", "attacker/v1", "semantic hash version"),
        ("semantic_exclusion_policy", "drop anything", "exclusion policy"),
    ),
)
def test_standalone_validator_pins_top_level_semantic_policy(field, value, message):
    tampered = copy.deepcopy(_checked_manifest())
    tampered[field] = value
    _resign(tampered)
    with pytest.raises(ValueError, match=message):
        validate_manifest(tampered, ROOT)


def test_standalone_validator_pins_data_metadata_and_worlds():
    for field, value, message in (
        ("dataset_version", "graphlog/other", "dataset version"),
        ("declared_source_zip_md5", "0" * 32, "source archive"),
        ("worlds", list(_checked_manifest()["input_groups"]["data"]["worlds"][:-1]),
         "world cohort"),
    ):
        tampered = copy.deepcopy(_checked_manifest())
        tampered["input_groups"]["data"][field] = value
        _resign(tampered)
        with pytest.raises(ValueError, match=message):
            validate_manifest(tampered, ROOT)


@pytest.mark.skipif(
    not (ROOT / "data/graphlog/graphlog_v1.1").exists(),
    reason="GraphLog corpus absent",
)
def test_generator_is_deterministic_and_data_fingerprint_is_complete():
    checked = _checked_manifest()
    rebuilt = build_manifest(ROOT)
    assert rebuilt == checked
    data = checked["input_groups"]["data"]
    assert data["dataset_version"] == "graphlog/v1.1"
    assert len(data["worlds"]) == 44
    assert len(data["files"]) == 44 * 3
    validate_manifest(checked, ROOT, verify_data=True)
