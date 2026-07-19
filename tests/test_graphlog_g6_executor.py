"""No-virgin-draw tests for the reviewed G6 phase adapter."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import relweblearner.bench.graphlog_g6_executor as executor_module

from relweblearner.bench.graphlog_certified.evaluation import _seal_evaluation_key
from relweblearner.bench.graphlog_g6_analysis import (
    _clopper_pearson_lower,
    _coverage_interval,
)
from relweblearner.bench.graphlog_g6 import G6Draw, G6Phase
from relweblearner.bench.graphlog_g6_evaluation import evaluate_g6_draw
from relweblearner.bench.graphlog_g6_executor import execute_phase


ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_SOURCE = ROOT / "src/relweblearner/bench/graphlog_g6_executor.py"


def _draw() -> G6Draw:
    digest = hashlib.sha256(b"synthetic-nonvalidation-draw").hexdigest()
    return G6Draw(0, "synthetic_world", digest, int(digest, 16))


def test_gold_join_is_not_a_module_level_executor_import():
    tree = ast.parse(EXECUTOR_SOURCE.read_text(encoding="utf-8"))
    top_level_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert "graphlog_g6_evaluation" not in top_level_modules
    assert "rule20_diag" not in top_level_modules
    accuracy = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_accuracy"
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "graphlog_g6_evaluation"
        for node in ast.walk(accuracy)
    )


def test_opaque_state_is_bound_to_phase_world_and_seed(tmp_path):
    draw = _draw()
    path = tmp_path / "state.pkl"
    executor_module._save_state(path, G6Phase.STRUCTURAL, draw, ("opaque",))
    assert executor_module._load_state(
        path, G6Phase.STRUCTURAL, draw,
    ) == ("opaque",)
    changed = G6Draw(draw.ordinal, draw.world, "0" * 64, 0)
    try:
        executor_module._load_state(path, G6Phase.STRUCTURAL, changed)
    except ValueError as error:
        assert "identity mismatch" in str(error)
    else:
        raise AssertionError("changed draw unexpectedly opened opaque state")


def test_prior_failure_propagates_without_running_next_phase(tmp_path, monkeypatch):
    draw = _draw()
    prior = tmp_path / "structural"
    prior.mkdir()
    (prior / "receipt.json").write_text(json.dumps({
        "status": "REPORTED_FAILURE",
    }), encoding="utf-8")
    output = tmp_path / "T5"
    output.mkdir()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("T5 implementation must not run")

    monkeypatch.setattr(executor_module, "_t5", forbidden)
    receipt = execute_phase(
        G6Phase.T5, draw, {G6Phase.STRUCTURAL: prior}, output,
    )
    assert receipt["status"] == "REPORTED_FAILURE"
    failure = json.loads((output / "failure.json").read_text(encoding="utf-8"))
    assert failure["payload"]["category"] == "PRIOR_PHASE_FAILURE"


def test_accuracy_join_pairs_seed_and_reports_truth(monkeypatch):
    key = _seal_evaluation_key(
        perm_a={"R0": "a0", "R1": "a1"},
        perm_b={"R0": "b0", "R1": "b1"},
        query_targets=("R0", "R1"),
        oracle_rules={},
    )
    calls = []

    def fake_setup(world, seed, n_train):
        calls.append((world, seed, n_train))
        return {
            "targets": ["R0", "R1"],
            "rules_ens": object(),
        }

    def fake_discrete(_context, _rules, mode):
        assert mode == "ensemble"
        return ["R1", "R1"]

    monkeypatch.setattr(
        "relweblearner.bench.rule20_diag.setup", fake_setup,
    )
    monkeypatch.setattr(
        "relweblearner.bench.rule20_diag._discrete_preds", fake_discrete,
    )
    monkeypatch.setattr(
        "relweblearner.bench.rule20_diag._graded_frozen_preds",
        lambda _context: ["R0", "R0"],
    )
    evaluation = evaluate_g6_draw(
        key,
        world="synthetic_world",
        seed=123,
        seed_sha256="1" * 64,
        opaque_a_predictions=("a0", None),
        identity_decisions=(
            ("target", "a0", "b0", False, "IDENTICAL", "COMMIT", "IDENTICAL"),
        ),
    )
    assert calls == [("synthetic_world", 123, 150)]
    query = dict(evaluation.query_summary)
    identity = dict(evaluation.identity_summary)
    assert query["replacement_accuracy"] == 0.5
    assert query["discrete_accuracy"] == 0.5
    assert query["graded_accuracy"] == 0.5
    assert query["abstentions"] == 1
    assert identity["evaluation_confirmed_real_nonanchor_identity_commits"] == 1
    assert identity["false_positive_identity_commits"] == 0


def test_unexpected_phase_error_is_a_digest_anchored_reported_failure(
    tmp_path, monkeypatch,
):
    draw = _draw()
    output = tmp_path / "structural"
    output.mkdir()
    monkeypatch.setattr(
        executor_module,
        "_structural",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic boom")),
    )
    receipt = execute_phase(G6Phase.STRUCTURAL, draw, {}, output)
    assert receipt["status"] == "REPORTED_FAILURE"
    assert receipt["artifact_records"][0]["name"] == "failure.json"
    data = (output / "failure.json").read_bytes()
    assert receipt["artifact_records"][0]["sha256"] \
        == hashlib.sha256(data).hexdigest()


def test_analysis_intervals_are_fixed_and_deterministic():
    # For all successes, the exact one-sided 95% lower limit has a closed form.
    assert abs(_clopper_pearson_lower(10, 10) - 0.05 ** (1 / 10)) < 1e-12
    first = _coverage_interval(
        ((1, 2), (2, 2), (0, 1)), manifest_id="sha256:synthetic",
    )
    second = _coverage_interval(
        ((1, 2), (2, 2), (0, 1)), manifest_id="sha256:synthetic",
    )
    assert first == second
    assert 0.0 <= first[0] <= first[1] <= 1.0
