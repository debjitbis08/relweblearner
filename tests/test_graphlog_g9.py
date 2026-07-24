"""G9 anti-propagation-mechanism harness tests.

All documents are synthetic (the G9 no-smoke-run rule): the real G9
manifest, amendment chain, and fresh master seed do not exist yet, and
nothing under ``results/`` or ``/data`` is read or written -- every loader
and preflight path is exercised against temporary documents only.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from relweblearner.bench import graphlog_g8, graphlog_g8_executor
from relweblearner.bench import graphlog_g9, graphlog_g9_executor
from relweblearner.bench.graphlog_certified.spec import DEFAULT_SPEC, VALIDATION_WORLDS
from relweblearner.certification.types import canonical_bytes, canonical_digest


def _write_manifest(path: Path, document: dict) -> None:
    body = {key: value for key, value in document.items() if key != "manifest_id"}
    document["manifest_id"] = f"sha256:{canonical_digest(body)}"
    path.write_bytes(canonical_bytes(document) + b"\n")


def _manifest_document() -> dict:
    master_hex = "5e" * 32
    master = bytes.fromhex(master_hex)
    worlds = list(VALIDATION_WORLDS)
    expansions = []
    for world in worlds:
        digest = hashlib.sha256(master + world.encode("utf-8")).digest()
        expansions.append({
            "world": world,
            "sha256_hex": digest.hex(),
            "draw_seed_uint256": str(int.from_bytes(digest, "big")),
        })
    return {
        "schema_version": graphlog_g9.G9_MANIFEST_SCHEMA,
        "part": graphlog_g9.G9_PART_MEASUREMENT,
        "study_id": graphlog_g9.G9_STUDY_IDS[graphlog_g9.G9_PART_MEASUREMENT],
        "preregistration_status": graphlog_g9.G9_PREREGISTRATION_STATUS[
            graphlog_g9.G9_PART_MEASUREMENT
        ],
        "cohort": {"worlds": worlds, "count": len(worlds)},
        "analysis_order": list(graphlog_g9.PHASE_ORDER),
        "data_protocol": {
            "draws_per_world": 1,
            "validation_output_root": "results/graphlog-certified/g9",
        },
        "draw_provenance": {
            "float_slack_status": (
                "disclosed: 2e-6 crossing guard band with stated conservatism"
            ),
            "fresh_master_seed": True,
            "g9_outcomes_observed": False,
        },
        "seed": {
            "master_seed_hex": master_hex,
            "derivation": {
                "concatenation": (
                    "hex_decode(master_seed_hex) || utf8(world_name), "
                    "with no delimiter or terminator"
                ),
                "digest": "SHA-256",
                "draw_seed_conversion": (
                    "interpret the complete 32-byte digest as one unsigned "
                    "big-endian integer"
                ),
                "formula": "SHA-256(master_seed || world_name)",
                "world_name_encoding": "UTF-8",
            },
            "expansions": expansions,
            "unique_expansion_count": len(
                {row["sha256_hex"] for row in expansions}
            ),
        },
        "freeze": {
            "spec_digest": DEFAULT_SPEC.digest,
            "g0_g5_commit": "a" * 40,
            "g0_g5_tree": "b" * 40,
            "baseline_manifest_id": "sha256:" + "2" * 64,
            "g5_runs": [
                {
                    "run_id": hashlib.sha256(world.encode("utf-8")).hexdigest(),
                    "seed": 0,
                    "world": world,
                }
                for world in worlds
            ],
        },
        "acceptance_rules": {
            rule: "preregistered"
            for rule in sorted(graphlog_g9.G9_ACCEPTANCE_RULES)
        },
        "g9_preregistration": {
            "phase_a_script_sha256": "3" * 64,
            "phase_b_report_script_sha256": "4" * 64,
            "phase_a_output_sha256": {"round1": "5" * 64, "round2": "6" * 64},
            "sealed_g8_study_index_sha256": "7" * 64,
            "predictor": dict(graphlog_g9.G9_PREDICTOR_LITERAL),
            "claim_4": dict(graphlog_g9.G9_CLAIM_4_LITERAL),
            "claim_5": graphlog_g9.G9_CLAIM_5_LITERAL,
            "non_vacuity": dict(graphlog_g9.G9_NON_VACUITY_LITERAL),
        },
    }


def _amendment_document() -> dict:
    return {
        "schema_version": graphlog_g9.G9_AMENDMENT_SCHEMA,
        "change_scope": graphlog_g9.G9_CHANGE_SCOPES[
            graphlog_g9.G9_PART_MEASUREMENT
        ],
        "g9_outcome_disclosure": (
            "no G9 outcome observed; the fresh master seed is unminted"
        ),
        "study_manifest_id": "sha256:" + "1" * 64,
        "parent_amendment_id": None,
        "implementation_freeze": {
            "harness_version": graphlog_g9.G9_HARNESS_VERSION,
            "commit": "a" * 40,
            "tree": "b" * 40,
            "files": {
                "src/relweblearner/bench/graphlog_g9.py": "0" * 64,
                "src/relweblearner/bench/graphlog_g9_executor.py": "1" * 64,
            },
        },
        "execution": {
            "enabled": False,
            "executor_file": None,
            "executor_qualname": None,
        },
    }


# --------------------------------------------------------------------------
# Manifest loading: happy path and each validation failure
# --------------------------------------------------------------------------

def test_g9_manifest_paths_and_single_part_constants_are_declared():
    assert graphlog_g9.G9_MANIFEST == Path(
        "results/graphlog-certified/g9-validation-manifest.json"
    )
    assert graphlog_g9.G9_AMENDMENT == Path(
        "results/graphlog-certified/g9-validation-amendment.json"
    )
    assert graphlog_g9.G9_PARTS == ("g9",)
    assert graphlog_g9.G9_OUTPUT_ROOTS[graphlog_g9.G9_PART_MEASUREMENT] == Path(
        "results/graphlog-certified/g9"
    )
    assert graphlog_g9.G9_RECEIPT_SCHEMA == "graphlog-certified-g9-receipt/v1"
    assert graphlog_g9.G9_HARNESS_VERSION == "graphlog-certified-g9-harness/v1"
    assert graphlog_g9.G9_ACCEPTANCE_RULES == {
        "crossing_set_reproducibility",
        "margin_error_identity",
        "crossing_guard_band",
        "predictor_accuracy_floor",
        "non_vacuity",
        "conditional_layer_unchanged",
        "certificate_soundness",
    }


def test_g9_manifest_loader_fails_cleanly_when_absent(tmp_path):
    with pytest.raises(graphlog_g9.G9PreflightError, match="absent"):
        graphlog_g9.load_study_manifest(tmp_path / "nonexistent-manifest.json")
    with pytest.raises(graphlog_g9.G9PreflightError, match="absent"):
        graphlog_g9.load_amendment(tmp_path / "nonexistent-amendment.json")


def test_g9_manifest_happy_path_loads_and_derives_every_draw(tmp_path):
    document = _manifest_document()
    path = tmp_path / "g9-validation-manifest.json"
    _write_manifest(path, document)
    study = graphlog_g9.load_study_manifest(path)
    assert study.part == graphlog_g9.G9_PART_MEASUREMENT
    assert study.output_root == Path("results/graphlog-certified/g9")
    assert tuple(draw.world for draw in study.draws) == VALIDATION_WORLDS
    assert tuple(phase.value for phase in study.phases) == graphlog_g9.PHASE_ORDER
    assert len(study.draws) == len({d.seed_sha256 for d in study.draws}) == 44
    assert study.phase_a_script_sha256 == "3" * 64
    assert study.phase_b_report_script_sha256 == "4" * 64
    assert study.sealed_g8_study_index_sha256 == "7" * 64
    assert study.manifest_id == document["manifest_id"]


@pytest.mark.parametrize("mutation, message", [
    ("wrong_schema", "schema"),
    ("unknown_part", "unknown part"),
    ("wrong_study_id", "study id"),
    ("not_preregistered", "preregistered"),
    ("missing_world", "cohort"),
    ("accuracy_early", "phase order"),
    ("wrong_output_root", "declared part"),
    ("seed_not_fresh", "fresh master seed"),
    ("outcomes_observed", "zero observed"),
    ("changed_seed", "expansion mismatch"),
    ("acceptance_rule_dropped", "acceptance rules"),
    ("acceptance_rule_added", "acceptance rules"),
])
def test_g9_manifest_tampering_fails_closed(tmp_path, mutation, message):
    document = _manifest_document()
    if mutation == "wrong_schema":
        document["schema_version"] = "graphlog-certified-not-g9/v1"
    elif mutation == "unknown_part":
        document["part"] = "g8"
    elif mutation == "wrong_study_id":
        document["study_id"] = "graphlog-certified-g8-interior-decisiveness/v1"
    elif mutation == "not_preregistered":
        document["preregistration_status"] = "committed_after_scoring"
    elif mutation == "missing_world":
        document["cohort"]["worlds"].pop()
        document["cohort"]["count"] -= 1
        document["seed"]["expansions"].pop()
        document["seed"]["unique_expansion_count"] -= 1
    elif mutation == "accuracy_early":
        document["analysis_order"] = [
            "structural", "accuracy", "T5", "T6", "T7_safety",
        ]
    elif mutation == "wrong_output_root":
        document["data_protocol"]["validation_output_root"] = (
            "results/graphlog-certified/g8"
        )
    elif mutation == "seed_not_fresh":
        document["draw_provenance"]["fresh_master_seed"] = False
    elif mutation == "outcomes_observed":
        document["draw_provenance"]["g9_outcomes_observed"] = True
    elif mutation == "changed_seed":
        document["seed"]["expansions"][0]["draw_seed_uint256"] = "1"
    elif mutation == "acceptance_rule_dropped":
        del document["acceptance_rules"]["non_vacuity"]
    else:
        document["acceptance_rules"]["no_regression"] = "smuggled"
    path = tmp_path / "g9-validation-manifest.json"
    _write_manifest(path, document)
    with pytest.raises(graphlog_g9.G9PreflightError, match=message):
        graphlog_g9.load_study_manifest(path)


@pytest.mark.parametrize("mutation, message", [
    ("section_missing", "missing or has the wrong keys"),
    ("key_missing", "missing or has the wrong keys"),
    ("key_added", "missing or has the wrong keys"),
    ("phase_a_script_not_hex", "phase_a_script_sha256"),
    ("phase_b_script_not_hex", "phase_b_report_script_sha256"),
    ("output_rounds_incomplete", "round1 and round2"),
    ("output_round1_not_hex", "round1"),
    ("sealed_index_not_hex", "sealed_g8_study_index_sha256"),
    ("predictor_degree_drift", "predictor"),
    ("predictor_family_drift", "predictor"),
    ("claim_4_floor_drift", "claim_4"),
    ("claim_4_pass_rule_drift", "claim_4"),
    ("claim_5_drift", "claim_5"),
    ("non_vacuity_drift", "non_vacuity"),
])
def test_g9_preregistration_section_drift_fails_closed(tmp_path, mutation, message):
    document = _manifest_document()
    section = document["g9_preregistration"]
    if mutation == "section_missing":
        del document["g9_preregistration"]
    elif mutation == "key_missing":
        del section["claim_5"]
    elif mutation == "key_added":
        section["claim_6"] = "invented"
    elif mutation == "phase_a_script_not_hex":
        section["phase_a_script_sha256"] = "G" * 64
    elif mutation == "phase_b_script_not_hex":
        section["phase_b_report_script_sha256"] = "4" * 63
    elif mutation == "output_rounds_incomplete":
        del section["phase_a_output_sha256"]["round2"]
    elif mutation == "output_round1_not_hex":
        section["phase_a_output_sha256"]["round1"] = "not-a-digest"
    elif mutation == "sealed_index_not_hex":
        section["sealed_g8_study_index_sha256"] = "7" * 65
    elif mutation == "predictor_degree_drift":
        section["predictor"]["degree"] = 4
    elif mutation == "predictor_family_drift":
        section["predictor"]["family"] = "neumann-series"
    elif mutation == "claim_4_floor_drift":
        section["claim_4"]["floor"] = 0.7
    elif mutation == "claim_4_pass_rule_drift":
        section["claim_4"]["pass_rule"] = "point-estimate"
    elif mutation == "claim_5_drift":
        section["claim_5"] = "depth-spearman-0.5"
    else:
        section["non_vacuity"]["minimum_unambiguous_crossing_records"] = 1
    path = tmp_path / "g9-validation-manifest.json"
    _write_manifest(path, document)
    with pytest.raises(graphlog_g9.G9PreflightError, match=message):
        graphlog_g9.load_study_manifest(path)


def test_g9_preregistration_literals_match_the_confirmed_plan_numbers():
    assert graphlog_g9.G9_PREDICTOR_LITERAL == {
        "family": "chebyshev-semi-iteration",
        "degree": 3,
        "kappa_design": 30,
        "diagnostic_ceiling": 0.99,
    }
    assert graphlog_g9.G9_CLAIM_4_LITERAL == {
        "floor": 0.776,
        "delta_over_baseline": 0.02,
        "pass_rule": "mean-jeffreys-lower-0.20-quantile",
    }
    assert graphlog_g9.G9_CLAIM_5_LITERAL == "dropped-depth-spearman-0.222"
    assert graphlog_g9.G9_NON_VACUITY_LITERAL == {
        "minimum_unambiguous_crossing_records": 5,
        "minimum_conditioned_worlds": 2,
    }


# --------------------------------------------------------------------------
# Amendment loading and the append-only chain
# --------------------------------------------------------------------------

def test_g9_amendment_base_is_disabled_and_blocks_execution(tmp_path):
    path = tmp_path / "g9-validation-amendment.json"
    _write_manifest(path, _amendment_document())
    amendment = graphlog_g9.load_amendment(path)
    assert amendment.execution_enabled is False
    assert amendment.executor_file is None
    assert amendment.executor_qualname is None
    with pytest.raises(graphlog_g9.G9PreflightError, match="disabled"):
        graphlog_g9.execute_study(
            _dummy_study(), amendment, lambda *args: {}, root=tmp_path,
        )


@pytest.mark.parametrize("mutation, message", [
    ("wrong_schema", "schema"),
    ("wrong_scope", "change scope"),
    ("empty_disclosure", "outcome-disclosure"),
    ("harness_drift", "harness version"),
    ("disabled_names_executor", "must not name"),
    ("enabled_without_executor", "pinned executor"),
    ("fake_commit", "real freeze commit"),
])
def test_g9_amendment_tampering_fails_closed(tmp_path, mutation, message):
    document = _amendment_document()
    if mutation == "wrong_schema":
        document["schema_version"] = "graphlog-certified-not-g9/v1"
    elif mutation == "wrong_scope":
        document["change_scope"] = (
            "exact_contraction_interior_decisiveness_fresh_draws"
        )
    elif mutation == "empty_disclosure":
        document["g9_outcome_disclosure"] = ""
    elif mutation == "harness_drift":
        document["implementation_freeze"]["harness_version"] = "changed/v0"
    elif mutation == "disabled_names_executor":
        document["execution"]["executor_qualname"] = "execute_phase_g9"
    elif mutation == "enabled_without_executor":
        document["execution"] = {
            "enabled": True,
            "executor_file": "src/relweblearner/bench/absent.py",
            "executor_qualname": "execute_phase_g9",
        }
    else:
        document["implementation_freeze"]["commit"] = "not-a-sha"
    path = tmp_path / "g9-validation-amendment.json"
    _write_manifest(path, document)
    with pytest.raises(graphlog_g9.G9PreflightError, match=message):
        graphlog_g9.load_amendment(path)


def test_g9_append_only_amendment_chain_links_and_pins_the_adapter(tmp_path):
    first = _amendment_document()
    first_path = tmp_path / "g9-validation-amendment.json"
    _write_manifest(first_path, first)

    second = deepcopy(first)
    second["parent_amendment_id"] = first["manifest_id"]
    second["execution"] = {
        "enabled": True,
        "executor_file": "src/relweblearner/bench/graphlog_g9_executor.py",
        "executor_qualname": "execute_phase_g9",
    }
    second_path = tmp_path / "g9-validation-amendment-2.json"
    _write_manifest(second_path, second)

    chain = graphlog_g9.load_amendment_chain(first_path)
    assert len(chain) == 2
    assert chain[0].execution_enabled is False
    assert chain[1].parent_amendment_id == chain[0].manifest_id
    assert chain[1].study_manifest_id == chain[0].study_manifest_id
    assert chain[1].execution_enabled is True
    assert chain[1].executor_file \
        == "src/relweblearner/bench/graphlog_g9_executor.py"
    assert chain[1].executor_qualname == "execute_phase_g9"

    broken = json.loads(second_path.read_text(encoding="utf-8"))
    broken["parent_amendment_id"] = "sha256:" + "0" * 64
    _write_manifest(second_path, broken)
    with pytest.raises(graphlog_g9.G9PreflightError, match="parent link"):
        graphlog_g9.load_amendment_chain(first_path)


def test_g9_amendment_chain_gap_and_missing_base_fail_closed(tmp_path):
    document = _amendment_document()
    orphan_path = tmp_path / "g9-validation-amendment-2.json"
    _write_manifest(orphan_path, document)
    with pytest.raises(graphlog_g9.G9PreflightError, match="base G9 amendment"):
        graphlog_g9.load_amendment_chain(
            tmp_path / "g9-validation-amendment.json"
        )


# --------------------------------------------------------------------------
# Harness: disabled gate, adapter pairing, receipt separation
# --------------------------------------------------------------------------

def _dummy_amendment(**overrides):
    base = dict(
        manifest_id="sha256:" + "0" * 64,
        amendment_path=Path("results/graphlog-certified/g9-validation-amendment.json"),
        study_manifest_id="sha256:" + "1" * 64,
        parent_amendment_id=None,
        harness_commit="a" * 40,
        harness_tree="b" * 40,
        implementation_files=(),
        execution_enabled=False,
        executor_file=None,
        executor_qualname=None,
    )
    base.update(overrides)
    return graphlog_g9.G9Amendment(**base)


def _dummy_study(**overrides):
    base = dict(
        manifest_id="sha256:" + "1" * 64,
        manifest_path=Path("results/graphlog-certified/g9-validation-manifest.json"),
        part=graphlog_g9.G9_PART_MEASUREMENT,
        output_root=Path("results/graphlog-certified/g9"),
        freeze_commit="a" * 40,
        freeze_tree="b" * 40,
        baseline_manifest_id="sha256:" + "2" * 64,
        spec_digest="deadbeef",
        phases=(),
        draws=(),
        g5_runs=(),
        phase_a_script_sha256="3" * 64,
        phase_b_report_script_sha256="4" * 64,
        sealed_g8_study_index_sha256="7" * 64,
    )
    base.update(overrides)
    return graphlog_g9.G9Study(**base)


def test_g9_execution_gate_is_disabled(tmp_path):
    study = _dummy_study()
    amendment = _dummy_amendment(execution_enabled=False)
    with pytest.raises(graphlog_g9.G9PreflightError, match="disabled"):
        graphlog_g9.execute_study(study, amendment, lambda *args: {}, root=tmp_path)


def test_execute_study_refuses_foreign_part_executor(tmp_path):
    # A G9 study pinned to a G8 part adapter must be refused before any
    # output is created: the status vocabulary is bound to the adapter, so
    # this check is what makes the vocabulary structural.
    study = _dummy_study()
    wrong = _dummy_amendment(
        execution_enabled=True,
        executor_file="src/relweblearner/bench/graphlog_g8_executor.py",
        executor_qualname="execute_phase_test",
    )
    with pytest.raises(graphlog_g9.G9PreflightError, match="part"):
        graphlog_g9.execute_study(
            study, wrong, graphlog_g8_executor.execute_phase_test,
            root=tmp_path, verify_repository=False,
        )
    # With the matching adapter the part gate passes; the run is then
    # stopped by a later check (the executor source is outside tmp root),
    # proving the refusal above was the part pairing, not something else.
    right = _dummy_amendment(
        execution_enabled=True,
        executor_file="src/relweblearner/bench/graphlog_g9_executor.py",
        executor_qualname="execute_phase_g9",
    )
    with pytest.raises(graphlog_g9.G9PreflightError, match="outside"):
        graphlog_g9.execute_study(
            study, right, graphlog_g9_executor.execute_phase_g9,
            root=tmp_path, verify_repository=False,
        )
    assert not any(tmp_path.iterdir())


def test_g9_adapter_exists_and_matches_the_harness_pinning_map():
    assert set(graphlog_g9.G9_EXECUTOR_QUALNAMES) == set(graphlog_g9.G9_PARTS)
    for part, qualname in graphlog_g9.G9_EXECUTOR_QUALNAMES.items():
        adapter = getattr(graphlog_g9_executor, qualname)
        assert callable(adapter)
        assert adapter.__qualname__ == qualname
    # No part-less adapter exists to bypass the vocabulary threading.
    assert not hasattr(graphlog_g9_executor, "execute_phase")


def test_execute_phase_g9_restamps_the_delegate_receipt(tmp_path, monkeypatch):
    draw = graphlog_g9.G9Draw(0, "rule_1", "ab" * 32, 7)
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    data = artifact.read_bytes()
    delegate_receipt = {
        "schema_version": graphlog_g8.G8_RECEIPT_SCHEMA,
        "phase": graphlog_g9.G9Phase.STRUCTURAL.value,
        "world": draw.world,
        "seed_sha256": draw.seed_sha256,
        "status": "PASS",
        "artifact_records": [{
            "name": artifact.name,
            "byte_size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }],
    }
    calls = []

    def fake_execute_phase_test(phase, draw_, prior, output):
        calls.append((phase, draw_, prior, output))
        return delegate_receipt

    monkeypatch.setattr(
        graphlog_g8_executor, "execute_phase_test", fake_execute_phase_test,
    )
    receipt = graphlog_g9_executor.execute_phase_g9(
        graphlog_g9.G9Phase.STRUCTURAL, draw, {}, tmp_path,
    )
    # Delegation is verbatim and the only change is the schema stamp; the
    # delegate's own receipt object is left unmutated.
    assert calls == [(graphlog_g9.G9Phase.STRUCTURAL, draw, {}, tmp_path)]
    assert receipt["schema_version"] == graphlog_g9.G9_RECEIPT_SCHEMA
    assert delegate_receipt["schema_version"] == graphlog_g8.G8_RECEIPT_SCHEMA
    assert {k: v for k, v in receipt.items() if k != "schema_version"} \
        == {k: v for k, v in delegate_receipt.items() if k != "schema_version"}
    validated = graphlog_g9._validate_receipt(
        receipt, graphlog_g9.G9Phase.STRUCTURAL, draw,
    )
    assert validated["schema_version"] == graphlog_g9.G9_RECEIPT_SCHEMA
    # The G8 receipt validator must reject a G9-stamped receipt and the G9
    # validator must reject the unstamped delegate receipt.
    with pytest.raises(ValueError, match="schema"):
        graphlog_g8._validate_receipt(
            receipt, graphlog_g9.G9Phase.STRUCTURAL, draw,
        )
    with pytest.raises(ValueError, match="schema"):
        graphlog_g9._validate_receipt(
            delegate_receipt, graphlog_g9.G9Phase.STRUCTURAL, draw,
        )


# --------------------------------------------------------------------------
# Preflight: preregistered script and ordering-witness digests
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _preregistered_layout(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    phase_a = scripts / "g9_phase_a_analysis.py"
    phase_a.write_text("print('phase a')\n", encoding="utf-8")
    phase_b = scripts / "g9_phase_b_report.py"
    phase_b.write_text("print('phase b')\n", encoding="utf-8")
    # The sealed G8 study index is reached through a symlink into the
    # archive, exactly as the archived repository lays it out.
    archive = tmp_path / "archive"
    archive.mkdir()
    real_index = archive / "study-index.json"
    real_index.write_text("{\"sealed\": true}\n", encoding="utf-8")
    g8_root = tmp_path / "results/graphlog-certified/g8"
    g8_root.mkdir(parents=True)
    (g8_root / "study-index.json").symlink_to(real_index)
    return phase_a, phase_b, real_index


def test_preflight_digest_checks_pass_and_read_through_the_symlink(tmp_path):
    phase_a, phase_b, real_index = _preregistered_layout(tmp_path)
    study = _dummy_study(
        phase_a_script_sha256=_sha256(phase_a),
        phase_b_report_script_sha256=_sha256(phase_b),
        sealed_g8_study_index_sha256=_sha256(real_index),
    )
    graphlog_g9._verify_preregistered_digests(study, root=tmp_path)


@pytest.mark.parametrize("target, message", [
    ("phase_a", "Phase A"),
    ("phase_b", "Phase B"),
    ("index", "study index"),
])
def test_preflight_digest_drift_fails_closed(tmp_path, target, message):
    phase_a, phase_b, real_index = _preregistered_layout(tmp_path)
    study = _dummy_study(
        phase_a_script_sha256=_sha256(phase_a),
        phase_b_report_script_sha256=_sha256(phase_b),
        sealed_g8_study_index_sha256=_sha256(real_index),
    )
    tampered = {
        "phase_a": phase_a, "phase_b": phase_b, "index": real_index,
    }[target]
    tampered.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(graphlog_g9.G9PreflightError, match=message):
        graphlog_g9._verify_preregistered_digests(study, root=tmp_path)


def test_preflight_digest_check_requires_every_pinned_file(tmp_path):
    phase_a, phase_b, real_index = _preregistered_layout(tmp_path)
    study = _dummy_study(
        phase_a_script_sha256=_sha256(phase_a),
        phase_b_report_script_sha256=_sha256(phase_b),
        sealed_g8_study_index_sha256=_sha256(real_index),
    )
    phase_b.unlink()
    with pytest.raises(graphlog_g9.G9PreflightError, match="absent"):
        graphlog_g9._verify_preregistered_digests(study, root=tmp_path)
