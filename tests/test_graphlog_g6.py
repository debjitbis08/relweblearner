"""No-draw tests for the manifest-locked G6 control harness."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import relweblearner.bench.graphlog_g6 as g6_module

from relweblearner.bench.graphlog_g6 import (
    G6Amendment,
    G6Phase,
    G6PreflightError,
    PHASE_ORDER,
    execute_study,
    load_study_manifest,
)
from relweblearner.bench.graphlog_certified.spec import VALIDATION_WORLDS
from relweblearner.certification.types import canonical_bytes, canonical_digest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results/graphlog-certified/g6-validation-manifest.json"


def _write_manifest(path: Path, document: dict) -> None:
    body = {key: value for key, value in document.items() if key != "manifest_id"}
    document["manifest_id"] = f"sha256:{canonical_digest(body)}"
    path.write_bytes(canonical_bytes(document) + b"\n")


def _amendment(study_id: str) -> G6Amendment:
    return G6Amendment(
        manifest_id="sha256:test-amendment",
        amendment_path=Path("unused.json"),
        study_manifest_id=study_id,
        harness_commit="0" * 40,
        harness_tree="0" * 40,
        implementation_files=(("unused.py", "0" * 64),),
        execution_enabled=False,
        executor_file=None,
        executor_qualname=None,
    )


def test_manifest_load_is_literal_complete_and_does_not_create_output():
    output = ROOT / "results/graphlog-certified/g6"
    assert not output.exists()
    study = load_study_manifest(MANIFEST)
    assert tuple(draw.world for draw in study.draws) == VALIDATION_WORLDS
    assert tuple(phase.value for phase in study.phases) == PHASE_ORDER
    assert len(study.draws) == len({draw.seed_sha256 for draw in study.draws}) == 44
    assert not output.exists()


@pytest.mark.parametrize("mutation, message", [
    ("missing_world", "cohort"),
    ("changed_seed", "expansion"),
    ("accuracy_early", "phase order"),
])
def test_manifest_tampering_fails_closed(tmp_path, mutation, message):
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if mutation == "missing_world":
        document["cohort"]["worlds"].pop()
        document["cohort"]["count"] -= 1
        document["seed"]["expansions"].pop()
        document["seed"]["unique_expansion_count"] -= 1
    elif mutation == "changed_seed":
        document["seed"]["expansions"][0]["draw_seed_uint256"] = "1"
    else:
        document["analysis_order"] = [
            "structural", "accuracy", "T5", "T6", "T7_safety",
        ]
    path = tmp_path / "manifest.json"
    _write_manifest(path, document)
    with pytest.raises(G6PreflightError, match=message):
        load_study_manifest(path)


def test_executor_observes_complete_phase_barriers_and_accuracy_last(tmp_path):
    source = load_study_manifest(MANIFEST)
    study = deepcopy(source)
    object.__setattr__(study, "output_root", Path("g6-test-output"))
    calls = []

    def executor(phase, draw, prior, output):
        calls.append((phase, draw.ordinal, tuple(prior)))
        artifact = output / "phase.json"
        artifact.write_bytes(canonical_bytes({
            "phase": phase.value,
            "world": draw.world,
            "seed_sha256": draw.seed_sha256,
        }))
        data = artifact.read_bytes()
        return {
            "schema_version": "graphlog-certified-g6-phase-receipt/v1",
            "phase": phase.value,
            "world": draw.world,
            "seed_sha256": draw.seed_sha256,
            "status": "PASS",
            "artifact_records": [{
                "name": artifact.name,
                "byte_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }],
        }

    output = execute_study(
        study, _amendment(study.manifest_id), executor,
        root=tmp_path, verify_repository=False,
    )
    assert output.is_dir()
    assert len(calls) == 44 * 5
    for phase_index, phase in enumerate(study.phases):
        block = calls[phase_index * 44:(phase_index + 1) * 44]
        assert all(call[0] is phase for call in block)
        assert tuple(call[1] for call in block) == tuple(range(44))
        assert all(call[2] == study.phases[:phase_index] for call in block)
    assert calls[-44][0] is G6Phase.ACCURACY


def test_existing_or_interrupted_study_is_never_rerun(tmp_path):
    source = load_study_manifest(MANIFEST)
    study = deepcopy(source)
    object.__setattr__(study, "output_root", Path("g6-test-output"))
    partial = tmp_path / f".g6-test-output.{study.manifest_id[7:19]}.partial"
    partial.mkdir()

    def forbidden_executor(*_args):
        raise AssertionError("executor must not run")

    with pytest.raises(G6PreflightError, match="rerun refused"):
        execute_study(
            study, _amendment(study.manifest_id), forbidden_executor,
            root=tmp_path, verify_repository=False,
        )


def test_production_execution_is_disabled_without_pinned_adapter(
    tmp_path, monkeypatch,
):
    source = load_study_manifest(MANIFEST)
    study = deepcopy(source)
    object.__setattr__(study, "output_root", Path("g6-test-output"))
    amendment = _amendment(study.manifest_id)
    monkeypatch.setattr(g6_module, "repository_preflight", lambda *_args, **_kw: None)

    with pytest.raises(G6PreflightError, match="disabled pending"):
        execute_study(
            study, amendment, lambda *_args: {}, root=tmp_path,
            verify_repository=True,
        )
    assert not (tmp_path / study.output_root).exists()


def test_executor_cannot_mutate_a_prior_phase(tmp_path):
    source = load_study_manifest(MANIFEST)
    study = deepcopy(source)
    object.__setattr__(study, "output_root", Path("g6-test-output"))

    def executor(phase, draw, prior, output):
        if phase is G6Phase.T5 and draw.ordinal == 0:
            (prior[G6Phase.STRUCTURAL] / "phase.json").write_text(
                "tampered", encoding="utf-8",
            )
        artifact = output / "phase.json"
        artifact.write_bytes(canonical_bytes({"phase": phase.value}))
        data = artifact.read_bytes()
        return {
            "schema_version": "graphlog-certified-g6-phase-receipt/v1",
            "phase": phase.value,
            "world": draw.world,
            "seed_sha256": draw.seed_sha256,
            "status": "PASS",
            "artifact_records": [{
                "name": artifact.name,
                "byte_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }],
        }

    with pytest.raises(ValueError, match="do not match"):
        execute_study(
            study, _amendment(study.manifest_id), executor,
            root=tmp_path, verify_repository=False,
        )


def test_harness_has_no_graphlog_loader_or_world_specific_branches():
    source = (
        ROOT / "src/relweblearner/bench/graphlog_g6.py"
    ).read_text(encoding="utf-8")
    # These are structural capability exclusions, not legacy symbol-name
    # proxies: the harness has no import from any data or evaluation module.
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not {
        "graphlog", "multiweb_graphlog", "multiweb_graded", "rule20_diag",
        "relweblearner.bench.graphlog",
    } & imported_modules
    world_literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.fullmatch(r"rule_\d+", node.value)
    }
    assert world_literals == set()
