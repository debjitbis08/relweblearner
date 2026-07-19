"""Deterministic G5 GraphLog development vertical slice and artifact validator.

The runner only orchestrates typed G1--G4 objects.  It contains no theorem
logic and sends its sealed evaluation capability directly to ``evaluation``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ...certification.ledger import CommitmentLedger, replay_ledger
from ...certification.t5 import (
    SolverConfig,
    assemble_coboundary,
    partition_dirichlet,
    run_t5,
)
from ...certification.t6 import check_separation, compare_field
from ...certification.t7 import CommitmentOutcome, PremiseId
from ...certification.types import canonical_bytes, canonical_data, canonical_digest
from .derivations import compile_derivations
from ..graphlog import load_world
from .enrichment import GraphLogAlgebra, certify_graphlog_comparison
from .evaluation import DevelopmentEvaluation, evaluate_development_run
from .hardening import GraphLogIdentityDecision, certify_identity_target
from .ingest import ingest_world, select_anchors
from .linearization import (
    build_anchor_boundary,
    build_linearization,
    encode_extension,
)
from .model import (
    CrossViewRelationIdentity,
    IdentityExtension,
    build_observations,
    build_scope,
    classify_extensions,
    classify_target,
    triangle_components,
)
from .notarization import DEFAULT_MANIFEST, validate_manifest
from .policy import CommitmentValue, permit
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


G5_WORLDS = ("rule_20", "rule_27")
RUNNER_VERSION = "graphlog-certified-g5-runner/v1"
RUN_MANIFEST_SCHEMA = "graphlog-certified-run-manifest/v1"
ARTIFACT_NAMES = (
    "scope.json",
    "t1.json",
    "targets.json",
    "operator.npz",
    "t5.json",
    "comparison.json",
    "separation.json",
    "commitments.jsonl",
    "evaluation.json",
)
JSON_ARTIFACTS = tuple(
    name for name in ARTIFACT_NAMES if name.endswith(".json")
)
COMMITMENT_COUNT_ORDER = tuple(outcome.value for outcome in CommitmentOutcome)
QUERY_SUMMARY_ORDER = (
    "total", "certified_correct", "certified_accuracy", "abstentions",
    "discrete_correct", "discrete_accuracy", "graded_correct",
    "graded_accuracy", "heals_vs_discrete", "breaks_vs_discrete",
    "heals_vs_graded", "breaks_vs_graded",
)


@dataclass(frozen=True, slots=True)
class G5RunResult:
    run_id: str
    output_directory: str
    world: str
    implementation_passed: bool
    vacuous: bool
    synthetic_nonvacuity_witness: str
    real_nonanchor_commits: int
    commitment_counts: tuple[tuple[str, int], ...]
    query_summary: tuple[tuple[str, int | float], ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_canonical_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def _envelope(
    artifact_type: str,
    payload: Any,
    *,
    spec: GraphLogCertifiedSpec,
) -> dict[str, Any]:
    return {
        "schema_version": spec.artifact_version,
        "artifact_type": artifact_type,
        "version_ids": {
            "runner": RUNNER_VERSION,
            "spec": spec.digest,
            "artifact": spec.artifact_version,
        },
        "payload": payload,
    }


def _source_digest(root: Path) -> str:
    paths = tuple(sorted(
        path for base in (
            root / "src/relweblearner/certification",
            root / "src/relweblearner/bench/graphlog_certified",
        )
        for path in base.glob("*.py")
    ))
    records = tuple(
        (str(path.relative_to(root)), _sha256(path.read_bytes())) for path in paths
    )
    return canonical_digest(records)


def _load_development_world(world: str) -> dict[str, Any]:
    if world not in G5_WORLDS:
        raise ValueError(f"G5 world must be one of {G5_WORLDS}")
    return load_world(world, n_train=150)


def _array_record(array: np.ndarray) -> dict[str, Any]:
    value = np.ascontiguousarray(np.asarray(array))
    if not np.all(np.isfinite(value)):
        raise ValueError("operator artifacts cannot contain NaN or infinity")
    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "order": "C",
        "sha256": _sha256(value.tobytes(order="C")),
    }


def _linearization_record(linearization) -> dict[str, Any]:
    """Serialize exact operator metadata while arrays live in operator.npz."""
    core = linearization.core
    return {
        "version": linearization.version,
        "world": linearization.world,
        "a_tokens": linearization.a_tokens,
        "b_tokens": linearization.b_tokens,
        "channels": linearization.channels,
        "core": {
            "coordinate_ids": core.coordinate_ids,
            "residual_blocks": tuple({
                "block_id": block.block_id,
                "row_count": block.row_count,
                "column_count": block.column_count,
                "exact_entries": block.exact_entries,
                "weight": block.weight,
                "weighted_matrix": _array_record(block.weighted_matrix),
            } for block in core.residual_blocks),
            "omitted_block_ids": core.omitted_block_ids,
            "cell_complex": core.cell_complex,
            "stalks": core.stalks,
            "restrictions": core.restrictions,
            "edge_weights": core.edge_weights,
        },
    }


def _write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write NPY members with fixed ZIP metadata for byte reproducibility."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(
                buffer, np.asarray(arrays[name]), allow_pickle=False,
            )
            info = zipfile.ZipInfo(f"{name}.npy", (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, buffer.getvalue())


def _strict_prediction(
    values: Sequence[int], algebra: GraphLogAlgebra,
) -> str | None:
    scores = np.asarray(values, dtype=float)
    if scores.shape != (algebra.dimension,) or not np.all(np.isfinite(scores)):
        return None
    maximum = float(np.max(scores))
    winners = np.flatnonzero(scores == maximum)
    if maximum <= 0.0 or len(winners) != 1:
        return None
    winner = int(winners[0])
    if winner >= algebra.vocabulary.a_dimension:
        return None
    return algebra.vocabulary.tokens[winner].value


def _replacement_predictions(
    *,
    observations,
    linearization,
    field,
    query_derivations,
    decisions: Sequence[tuple[CrossViewRelationIdentity, GraphLogIdentityDecision]],
) -> tuple[str | None, ...]:
    accepted = {
        (anchor.a_token, anchor.b_token) for anchor in observations.anchors
    }
    accepted.update(
        (target.a_token, target.b_token)
        for target, decision in decisions
        if decision.certificate.outcome is CommitmentOutcome.COMMIT
        and decision.certificate.commitment == "IDENTICAL"
    )
    extension = IdentityExtension(tuple(sorted(accepted)))
    algebra = GraphLogAlgebra(
        observations=observations,
        extension=extension,
        linearization=linearization,
        field=field,
    )
    return tuple(
        _strict_prediction(
            algebra.evaluate_exact(dag)[dag.root_id], algebra,
        )
        for dag in query_derivations
    )


def _compact_t6(comparison) -> dict[str, Any]:
    report = comparison.report
    return {
        "extension_id": comparison.behavior.extension_id,
        "package": report.package,
        "package_id": report.package.digest,
        "uniform_root_budget": report.uniform_root_budget,
        "maximum_observed_root_error": report.maximum_observed_root_error,
        "admissible": report.admissible,
        "certificates": tuple({
            "certificate_id": canonical_digest(certificate),
            "derivation_id": certificate.derivation_id,
            "field_comparison": certificate.field_comparison,
            "node_budget_columns": (
                "node_id", "budget", "observed_error", "tube_satisfied",
                "source_ids_digest",
            ),
            "node_budgets": tuple((
                node.node_id,
                node.budget,
                node.observed_error,
                node.tube_satisfied,
                canonical_digest(node.source_ids),
            ) for node in certificate.node_budgets),
            "node_budget_digest": canonical_digest(certificate.node_budgets),
            "node_contract_digest": canonical_digest(certificate.node_contracts),
            "node_count": len(certificate.node_budgets),
            "root_budget": certificate.root_budget,
            "root_observed_error": certificate.root_observed_error,
            "operation_coverage_complete": certificate.operation_coverage_complete,
            "tubes_satisfied": certificate.tubes_satisfied,
            "source_preservation_verified": certificate.source_preservation_verified,
            "admissible": certificate.admissible,
            "rejection_reasons": certificate.rejection_reasons,
        } for certificate in report.certificates),
        "behavior": comparison.behavior,
    }


def _commitment_lines(
    decisions: Sequence[tuple[CrossViewRelationIdentity, GraphLogIdentityDecision]],
) -> tuple[bytes, CommitmentLedger]:
    ledger = CommitmentLedger()
    lines = []
    for target, decision in decisions:
        certificate = decision.certificate
        ledger = ledger.append_certificate(certificate)
        event = ledger.events[-1]
        row = {
            "schema_version": "graphlog-certified-commitment-record/v1",
            "target_tokens": {
                "a": target.a_token.value,
                "b": target.b_token.value,
            },
            "certificate_id": certificate.certificate_id,
            "certificate": certificate,
            "event": event,
        }
        lines.append(canonical_bytes(row))
    replayed = replay_ledger(ledger.events)
    if canonical_bytes(replayed.live_commitments) != canonical_bytes(
        ledger.state.live_commitments
    ):
        raise ValueError("ledger replay changed live commitments")
    return tuple(lines), ledger


def _artifact_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return _artifact_record_from_bytes(path.name, data)


def _artifact_record_from_bytes(name: str, data: bytes) -> dict[str, Any]:
    return {
        "name": name,
        "byte_size": len(data),
        "sha256": _sha256(data),
    }


def _records_by_name(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != len(ARTIFACT_NAMES):
        raise ValueError("run artifact record count mismatch")
    if not all(isinstance(row, dict) and isinstance(row.get("name"), str)
               for row in rows):
        raise ValueError("run artifact records are malformed")
    names = tuple(row["name"] for row in rows)
    if len(set(names)) != len(names):
        raise ValueError("run artifact names must be unique")
    if set(names) != set(ARTIFACT_NAMES):
        raise ValueError("run artifact set mismatch")
    return {row["name"]: row for row in rows}


def _display_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)


def _result_from_manifest(
    manifest: dict[str, Any], output: Path, root: Path,
) -> G5RunResult:
    summary = manifest["result_summary"]
    counts = summary["commitment_counts"]
    query = summary["query_summary"]
    return G5RunResult(
        manifest["run_id"], _display_path(output, root), manifest["world"],
        summary["implementation_passed"], summary["vacuous"],
        summary["synthetic_nonvacuity_witness"],
        summary["real_nonanchor_commits"],
        tuple((key, counts[key]) for key in COMMITMENT_COUNT_ORDER),
        tuple((key, query[key]) for key in QUERY_SUMMARY_ORDER),
    )


def _discard_incomplete_output(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _validated_cached_manifest(
    output: Path,
    *,
    root: Path,
    baseline_manifest_id: str,
) -> dict[str, Any] | None:
    if not output.exists():
        return None
    try:
        return validate_run_directory(
            output,
            root=root,
            verify_baselines=False,
            expected_baseline_manifest_id=baseline_manifest_id,
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        _discard_incomplete_output(output)
        return None


def _finite_json(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    return value is None or isinstance(value, (str, bool, int))


def validate_run_directory(
    directory: Path,
    *,
    root: Path | None = None,
    verify_baselines: bool = True,
    expected_baseline_manifest_id: str | None = None,
    require_directory_name: bool = True,
) -> dict[str, Any]:
    """Round-trip and content-check a G5 run directory from disk."""
    root = root or _repo_root()
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != RUN_MANIFEST_SCHEMA:
        raise ValueError("unsupported run manifest schema")
    body = {key: value for key, value in manifest.items() if key != "manifest_id"}
    if manifest.get("manifest_id") != f"sha256:{canonical_digest(body)}":
        raise ValueError("run manifest id mismatch")
    if require_directory_name and directory.name != manifest.get("run_id"):
        raise ValueError("content-addressed run directory name mismatch")
    records = _records_by_name(manifest.get("artifacts"))
    blobs: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    for name in ARTIFACT_NAMES:
        data = (directory / name).read_bytes()
        blobs[name] = data
        if _artifact_record_from_bytes(name, data) != records[name]:
            raise ValueError(f"run artifact {name} mismatch")
        if name in JSON_ARTIFACTS:
            documents[name] = json.loads(data)
    for name, document in documents.items():
        if not _finite_json(document):
            raise ValueError(f"run artifact {name} contains non-finite data")
        if not document.get("schema_version") or not document.get("version_ids"):
            raise ValueError(f"run artifact {name} lacks version metadata")

    t5_document = documents["t5.json"]
    declared_arrays = t5_document["payload"]["arrays"]
    with np.load(io.BytesIO(blobs["operator.npz"]), allow_pickle=False) as arrays:
        if set(arrays.files) != set(declared_arrays):
            raise ValueError("operator array membership mismatch")
        for name in arrays.files:
            if _array_record(arrays[name]) != declared_arrays[name]:
                raise ValueError(f"operator array {name} mismatch")

    premise_ids = {premise.value for premise in PremiseId}
    lines = blobs["commitments.jsonl"].splitlines()
    if not lines:
        raise ValueError("commitment ledger is empty")
    for line in lines:
        row = json.loads(line)
        if not _finite_json(row) or not row.get("schema_version"):
            raise ValueError("invalid commitment record")
        certificate = row["certificate"]
        if row["certificate_id"] != canonical_digest(certificate):
            raise ValueError("commitment certificate id mismatch")
        if {item["premise_id"] for item in certificate["premises"]} != premise_ids:
            raise ValueError("commitment record lacks a complete six-premise table")
        event = row["event"]
        if event["event_id"] != canonical_digest(event["body"]):
            raise ValueError("commitment event id mismatch")
    evaluation = documents["evaluation.json"]
    if len(evaluation["payload"]["episode_rows"]) != 1000:
        raise ValueError("development evaluation lacks per-episode rows")
    if expected_baseline_manifest_id is not None and (
        manifest.get("baseline_manifest_id") != expected_baseline_manifest_id
    ):
        raise ValueError("run references a different baseline manifest")
    if verify_baselines:
        baseline_path = root / DEFAULT_MANIFEST
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        validate_manifest(baseline, root, verify_data=True)
        if manifest["baseline_manifest_id"] != baseline["manifest_id"]:
            raise ValueError("run references a different baseline manifest")
    return manifest


def run_world(
    world: str,
    *,
    seed: int = 0,
    root: Path | None = None,
    output_root: Path = Path("results/graphlog-certified"),
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> G5RunResult:
    """Execute one ordered G5 world and emit its validated artifact directory."""
    if seed != 0:
        raise ValueError("G5 development runs are frozen to seed=0")
    root = root or _repo_root()
    baseline = json.loads((root / DEFAULT_MANIFEST).read_text(encoding="utf-8"))
    validate_manifest(baseline, root, verify_data=True)
    source_digest = _source_digest(root)
    descriptor = {
        "runner_version": RUNNER_VERSION,
        "world": world,
        "seed": seed,
        "spec_digest": spec.digest,
        "source_digest": source_digest,
        "baseline_manifest_id": baseline["manifest_id"],
    }
    run_id = canonical_digest(descriptor)
    output_base = output_root if output_root.is_absolute() else root / output_root
    output_base.mkdir(parents=True, exist_ok=True)
    output = output_base / run_id
    cached = _validated_cached_manifest(
        output, root=root, baseline_manifest_id=baseline["manifest_id"],
    )
    if cached is not None:
        return _result_from_manifest(cached, output, root)
    artifact_dir = Path(tempfile.mkdtemp(
        prefix=f".{run_id}.partial-", dir=output_base,
    ))

    raw_world = _load_development_world(world)
    runtime, evaluation_key = ingest_world(raw_world, seed=seed, spec=spec)
    pre_anchor = build_observations(runtime)
    anchors = select_anchors(
        runtime.opaque_overlap_events,
        triangle_components(pre_anchor.triangles_a),
        budget=spec.anchor_budget,
    )
    observations = build_observations(runtime, anchors)
    scope = build_scope(observations, spec=spec)
    extensions = classify_extensions(observations, scope)
    if not extensions.solutions:
        raise ValueError(f"{world} has no controlled exact extension for G5")

    linearization = build_linearization(observations, scope, spec=spec)
    boundary = build_anchor_boundary(observations, linearization)
    coboundary = assemble_coboundary(linearization.core)
    system = partition_dirichlet(coboundary, boundary.core)
    t5_run = run_t5(
        system,
        SolverConfig(field_tolerance=float(spec.field_tolerance)),
    )
    if t5_run.field is None:
        raise ValueError(f"{world} T5 field is not certified")

    compiled = compile_derivations(runtime, scope.candidate_identities, spec=spec)
    all_derivations = (
        *compiled.query_derivations,
        *compiled.identity_derivations,
    )
    comparisons = []
    for extension_index, extension in enumerate(extensions.solutions):
        extension_id = f"extension:{extension_index}"
        field_comparison = compare_field(
            extension_id=extension_id,
            system=system,
            spectrum=t5_run.certificate.spectrum,
            exact_cochain=encode_extension(extension, linearization).reshape(-1),
            field=t5_run.field,
        )
        algebra = GraphLogAlgebra(
            observations=observations,
            extension=extension,
            linearization=linearization,
            field=t5_run.field,
            spec=spec,
        )
        comparisons.append(certify_graphlog_comparison(
            extension_id=extension_id,
            algebra=algebra,
            derivations=all_derivations,
            field_comparison=field_comparison,
            spec=spec,
        ))
    if not all(comparison.report.admissible for comparison in comparisons):
        raise ValueError(f"{world} has an inadmissible T6 comparison")
    separation = check_separation(tuple(
        comparison.behavior for comparison in comparisons
    ))

    dag_by_id = {
        dag.derivation_id: dag for dag in compiled.identity_derivations
    }
    certificates_by_extension = tuple({
        certificate.derivation_id: certificate
        for certificate in comparison.report.certificates
    } for comparison in comparisons)
    target_rows = []
    decisions = []
    shared_operator_report = None
    for a_token in linearization.a_tokens:
        for b_token in linearization.b_tokens:
            target = CrossViewRelationIdentity(a_token, b_token)
            classification = classify_target(
                observations, scope, target, extensions=extensions,
            )
            commitment = (
                CommitmentValue.IDENTICAL
                if classification.verdict.value == "IDENTICAL"
                else CommitmentValue.DISTINCT
            )
            policy = permit(
                observations, scope, target, classification, commitment,
            )
            derivation_id = f"identity:{a_token.value}:{b_token.value}"
            dag = dag_by_id.get(derivation_id)
            target_certificates = tuple(
                table[derivation_id] for table in certificates_by_extension
                if derivation_id in table
            )
            decision = certify_identity_target(
                observations=observations,
                scope=scope,
                target=target,
                extension_classification=extensions,
                target_classification=classification,
                policy=policy,
                linearization=linearization,
                t5_run=t5_run,
                target_dag=dag,
                target_t6_certificates=target_certificates,
                separation=separation,
                spec=spec,
                shared_operator_report=shared_operator_report,
            )
            if decision.perturbation is not None and shared_operator_report is None:
                shared_operator_report = decision.perturbation
            target_rows.append({
                "target_id": target.target_id,
                "a_token": a_token.value,
                "b_token": b_token.value,
                "classification": classification,
                "policy": policy,
                "decision_id": decision.certificate.certificate_id,
            })
            decisions.append((target, decision))

    commitment_lines, ledger = _commitment_lines(decisions)
    (artifact_dir / "commitments.jsonl").write_bytes(
        b"\n".join(commitment_lines) + b"\n"
    )
    predictions = _replacement_predictions(
        observations=observations,
        linearization=linearization,
        field=t5_run.field,
        query_derivations=compiled.query_derivations,
        decisions=decisions,
    )
    evaluation: DevelopmentEvaluation = evaluate_development_run(
        evaluation_key,
        world=world,
        opaque_a_predictions=predictions,
        identity_decisions=tuple(
            (
                target.target_id,
                target.a_token.value,
                target.b_token.value,
                decision.certificate.outcome.value,
                decision.certificate.commitment,
            )
            for target, decision in decisions
        ),
    )

    arrays = {
        "coboundary": coboundary.dense_delta,
        "laplacian": coboundary.laplacian,
        "laplacian_uu": system.laplacian_uu,
        "laplacian_ub": system.laplacian_ub,
        "boundary_values": system.boundary_values,
        "field_values": t5_run.field.values,
        "field_residual": t5_run.field.residual,
        "normal_residual": t5_run.field.normal_residual,
    }
    _write_deterministic_npz(artifact_dir / "operator.npz", arrays)
    _write_canonical_json(artifact_dir / "scope.json", _envelope(
        "scope/v1",
        {
            "runtime_id": canonical_digest(runtime),
            "observations": observations,
            "scope": scope,
            "derivation_family_id": compiled.digest,
            "query_path_counts": compiled.query_path_counts,
        },
        spec=spec,
    ))
    _write_canonical_json(artifact_dir / "t1.json", _envelope(
        "t1-extension-classification/v1", extensions, spec=spec,
    ))
    _write_canonical_json(artifact_dir / "targets.json", _envelope(
        "target-projection-policy/v1", {"targets": target_rows}, spec=spec,
    ))
    _write_canonical_json(artifact_dir / "t5.json", _envelope(
        "t5-operator-certificate/v1",
        {
            "linearization": _linearization_record(linearization),
            "boundary": boundary,
            "certificate": t5_run.certificate,
            "arrays": {name: _array_record(value) for name, value in arrays.items()},
        },
        spec=spec,
    ))
    _write_canonical_json(artifact_dir / "comparison.json", _envelope(
        "t6-comparison/v1",
        {"comparisons": tuple(_compact_t6(item) for item in comparisons)},
        spec=spec,
    ))
    _write_canonical_json(artifact_dir / "separation.json", _envelope(
        "t6-separation/v1", separation, spec=spec,
    ))
    _write_canonical_json(artifact_dir / "evaluation.json", _envelope(
        "evaluation-only-development-join/v1", evaluation, spec=spec,
    ))

    counts = {
        outcome.value: sum(
            decision.certificate.outcome is outcome
            for _target, decision in decisions
        )
        for outcome in CommitmentOutcome
    }
    anchor_pairs = {
        (anchor.a_token, anchor.b_token) for anchor in observations.anchors
    }
    real_nonanchor_commits = sum(
        decision.certificate.outcome is CommitmentOutcome.COMMIT
        and (target.a_token, target.b_token) not in anchor_pairs
        for target, decision in decisions
    )
    query_summary = dict(evaluation.query_summary)
    result_summary = {
        "implementation_passed": True,
        "vacuous": real_nonanchor_commits == 0,
        "synthetic_nonvacuity_witness": "tests/test_graphlog_certified_g4.py",
        "real_nonanchor_commits": real_nonanchor_commits,
        "commitment_counts": counts,
        "query_summary": query_summary,
        "ledger_live_commitments": len(ledger.state.live_commitments),
    }
    artifact_records = tuple(
        _artifact_record(artifact_dir / name) for name in ARTIFACT_NAMES
    )
    manifest_body = {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "run_id": run_id,
        "descriptor": descriptor,
        "world": world,
        "seed": seed,
        "baseline_manifest_id": baseline["manifest_id"],
        "artifacts": artifact_records,
        "result_summary": result_summary,
    }
    manifest = {
        **manifest_body,
        "manifest_id": f"sha256:{canonical_digest(manifest_body)}",
    }
    _write_canonical_json(artifact_dir / "manifest.json", manifest)
    validate_run_directory(
        artifact_dir,
        root=root,
        verify_baselines=False,
        expected_baseline_manifest_id=baseline["manifest_id"],
        require_directory_name=False,
    )
    try:
        artifact_dir.rename(output)
    except FileExistsError:
        # A concurrent identical run won promotion.  Accept only its fully
        # validated content-addressed directory and discard our staging tree.
        winner = validate_run_directory(
            output,
            root=root,
            verify_baselines=False,
            expected_baseline_manifest_id=baseline["manifest_id"],
        )
        _discard_incomplete_output(artifact_dir)
        return _result_from_manifest(winner, output, root)
    return _result_from_manifest(manifest, output, root)


def run_g5(
    *,
    root: Path | None = None,
    output_root: Path = Path("results/graphlog-certified"),
) -> tuple[G5RunResult, G5RunResult]:
    """Run the frozen development order: rule_20 first, then rule_27."""
    root = root or _repo_root()
    return tuple(
        run_world(world, root=root, output_root=output_root)
        for world in G5_WORLDS
    )  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", choices=(*G5_WORLDS, "all"), default="all")
    parser.add_argument("--output-root", default="results/graphlog-certified")
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args(argv)
    root = _repo_root()
    if args.validate is not None:
        manifest = validate_run_directory(root / args.validate, root=root)
        print(manifest["manifest_id"])
        return
    worlds = G5_WORLDS if args.world == "all" else (args.world,)
    results = tuple(run_world(
        world,
        root=root,
        output_root=Path(args.output_root),
    ) for world in worlds)
    print(json.dumps(canonical_data(results), indent=2))


if __name__ == "__main__":
    main()
