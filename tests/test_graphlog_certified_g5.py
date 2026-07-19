"""G5 development vertical-slice artifact and regression acceptance tests."""

from __future__ import annotations

import ast
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import relweblearner.bench.graphlog_certified.runner as runner_module

from relweblearner.bench.graphlog_certified.runner import (
    ARTIFACT_NAMES,
    COMMITMENT_COUNT_ORDER,
    G5_WORLDS,
    G5RunResult,
    QUERY_SUMMARY_ORDER,
    _display_path,
    _records_by_name,
    _source_digest,
    _validated_cached_manifest,
    validate_run_directory,
)
from relweblearner.certification.types import canonical_digest


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/graphlog-certified"


def _manifests() -> dict[str, tuple[Path, dict]]:
    found: dict[str, tuple[Path, dict]] = {}
    current_source = _source_digest(ROOT)
    for path in sorted(RESULTS.glob("*/manifest.json")):
        if path.parent.name == "baselines":
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("descriptor", {}).get("source_digest") != current_source:
            continue
        assert document["run_id"] == canonical_digest(document["descriptor"])
        world = document["world"]
        assert world not in found, f"duplicate current-source G5 run for {world}"
        found[world] = (path.parent, document)
    assert set(found) == set(G5_WORLDS), "both current-source G5 runs are required"
    return found


def _artifact(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text(encoding="utf-8"))


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, str):
        yield value


def test_g5_rule20_then_rule27_artifact_sets_round_trip_from_disk():
    manifests = _manifests()
    assert set(manifests) == set(G5_WORLDS)
    for world in G5_WORLDS:
        directory, manifest = manifests[world]
        assert manifest["world"] == world and manifest["seed"] == 0
        assert {row["name"] for row in manifest["artifacts"]} \
            == set(ARTIFACT_NAMES)
        assert validate_run_directory(directory, root=ROOT) == manifest
        assert manifest["result_summary"]["implementation_passed"]


def test_manifest_artifact_records_reject_duplicates_before_deduplication():
    rows = [{"name": name} for name in ARTIFACT_NAMES]
    rows[-1] = {"name": rows[0]["name"]}
    with pytest.raises(ValueError, match="unique"):
        _records_by_name(rows)


def test_cached_result_order_and_external_output_paths_are_stable(tmp_path):
    manifest = deepcopy(next(iter(_manifests().values()))[1])
    summary = manifest["result_summary"]
    summary["commitment_counts"] = dict(reversed(tuple(
        summary["commitment_counts"].items()
    )))
    summary["query_summary"] = dict(reversed(tuple(
        summary["query_summary"].items()
    )))
    external = tmp_path / manifest["run_id"]
    result = G5RunResult.from_manifest(manifest, external, ROOT)
    assert tuple(key for key, _value in result.commitment_counts) \
        == COMMITMENT_COUNT_ORDER
    assert tuple(key for key, _value in result.query_summary) == QUERY_SUMMARY_ORDER
    assert result.output_directory == str(external)
    assert _display_path(ROOT / "results/example", ROOT) == "results/example"


def test_run_g5_prepares_shared_baseline_and_source_context_once(monkeypatch):
    context = object()
    preparations = []
    worlds = []

    def fake_prepare(root, output_root):
        preparations.append((root, output_root))
        return context

    def fake_run(world, *, seed, spec, context):
        worlds.append((world, seed, spec, context))
        return world

    monkeypatch.setattr(runner_module, "_prepare_g5_context", fake_prepare)
    monkeypatch.setattr(runner_module, "_run_world", fake_run)
    assert runner_module.run_g5(root=ROOT) == G5_WORLDS
    assert len(preparations) == 1
    assert tuple(row[0] for row in worlds) == G5_WORLDS
    assert all(row[1] == 0 and row[3] is context for row in worlds)


def test_interrupted_final_directory_is_discarded_for_regeneration(tmp_path):
    incomplete = tmp_path / "run-id"
    incomplete.mkdir()
    (incomplete / "commitments.jsonl").write_text("partial", encoding="utf-8")
    assert _validated_cached_manifest(
        incomplete, root=ROOT, baseline_manifest_id="baseline",
    ) is None
    assert not incomplete.exists()


def test_development_loader_uses_the_shared_graphlog_data_boundary(monkeypatch):
    sentinel = {"name": "rule_20", "train": (), "test": (), "rules": {}}
    calls = []

    def fake_load_world(world, n_train):
        calls.append((world, n_train))
        return sentinel

    monkeypatch.setattr(runner_module, "load_world", fake_load_world)
    assert runner_module._load_development_world("rule_20") is sentinel
    assert calls == [("rule_20", 150)]


def test_g5_evaluation_has_paired_episode_joins_and_baseline_headlines():
    expected = {
        "rule_20": {"discrete_accuracy": 0.659, "graded_accuracy": 0.317},
        "rule_27": {"discrete_accuracy": 0.163, "graded_accuracy": 0.163},
    }
    for world, (directory, _manifest) in _manifests().items():
        evaluation = _artifact(directory, "evaluation.json")["payload"]
        summary = dict(evaluation["query_summary"])
        assert len(evaluation["episode_rows"]) == summary["total"]
        assert _manifest["result_summary"]["query_summary"]["total"] \
            == summary["total"]
        assert summary["discrete_accuracy"] == expected[world]["discrete_accuracy"]
        assert summary["graded_accuracy"] == expected[world]["graded_accuracy"]
        assert all(
            row["versus_discrete"] and row["versus_graded"]
            for row in evaluation["episode_rows"]
        )


def test_g5_reports_vacuity_without_promoting_false_identity_events():
    manifests = _manifests()
    assert all(
        manifest["result_summary"]["vacuous"]
        and manifest["result_summary"]["real_nonanchor_commits"] == 0
        for _directory, manifest in manifests.values()
    )
    rule27 = _artifact(manifests["rule_27"][0], "evaluation.json")["payload"]
    split_hub = [
        row for row in rule27["identity_rows"]
        if row["raw_a_label"] == row["raw_b_label"] == "R_9_-"
    ]
    assert split_hub
    assert all(row["outcome"] != "COMMIT" for row in split_hub)


def _from_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return tuple(
        (node.level, node.module, {alias.name for alias in node.names})
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )


def test_certified_runtime_has_only_narrow_structural_gold_boundary_imports():
    package = ROOT / "src/relweblearner/bench/graphlog_certified"
    runner_imports = _from_imports(package / "runner.py")
    assert (1, "evaluation", {
        "DevelopmentEvaluation", "evaluate_development_run",
    }) in runner_imports
    assert (2, "graphlog", {"load_world"}) in runner_imports

    ingest_imports = _from_imports(package / "ingest.py")
    assert (1, "evaluation", {"EvaluationKey", "_seal_evaluation_key"}) \
        in ingest_imports

    runtime_modules = (
        "derivations.py", "enrichment.py", "hardening.py",
        "linearization.py", "model.py", "policy.py", "spec.py",
    )
    forbidden_modules = {
        "evaluation", "multiweb_graphlog", "multiweb_graded",
        "rule20_diag", "rule27_diag",
    }
    for name in runtime_modules:
        for _level, module, _names in _from_imports(package / name):
            assert module not in forbidden_modules
            assert module is None or module.rsplit(".", 1)[-1] \
                not in forbidden_modules


def test_non_evaluation_artifacts_have_no_gold_label_route():
    forbidden_fields = {
        "perm_a", "perm_b", "true_map", "query_target", "query_targets",
        "oracle_rules", "hide_a", "hide_b", "raw_relation", "target",
    }
    raw_label = re.compile(r"^R_\d+_[+-]$")
    for directory, _manifest in _manifests().values():
        for name in (
            "scope.json", "t1.json", "targets.json", "t5.json",
            "comparison.json", "separation.json",
        ):
            for item in _walk(_artifact(directory, name)):
                assert item not in forbidden_fields
                assert not raw_label.match(item)
