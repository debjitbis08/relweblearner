"""Reviewed phase adapter for the preregistered GraphLog G6 study.

All pre-accuracy state contains opaque tokens only.  The evaluation-only join
is dynamically imported in ``_accuracy`` after the harness has completed the
structural, T5, T6, and T7 barriers for every preregistered world.
"""

from __future__ import annotations

import hashlib
import io
import json
import pickle
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ..certification.ledger import CommitmentLedger, replay_ledger
from ..certification.t5 import (
    SolverConfig,
    assemble_coboundary,
    partition_dirichlet,
    run_t5,
)
from ..certification.t6 import check_separation, compare_field
from ..certification.t7 import CommitmentOutcome
from ..certification.types import canonical_bytes, canonical_digest
from .graphlog import load_world
from .graphlog_certified.derivations import compile_derivations
from .graphlog_certified.enrichment import (
    GraphLogAlgebra,
    certify_graphlog_comparison,
)
from .graphlog_certified.hardening import (
    GraphLogIdentityDecision,
    certify_identity_target,
)
from .graphlog_certified.ingest import ingest_world, select_anchors
from .graphlog_certified.linearization import (
    build_anchor_boundary,
    build_linearization,
    encode_extension,
)
from .graphlog_certified.model import (
    CrossViewRelationIdentity,
    IdentityExtension,
    build_observations,
    build_scope,
    classify_extensions,
    classify_target,
    triangle_components,
)
from .graphlog_certified.policy import CommitmentValue, permit
from .graphlog_certified.spec import DEFAULT_SPEC
from .graphlog_g6 import G6Draw, G6Phase


G6_EXECUTOR_VERSION = "graphlog-certified-g6-executor/v1"
STATE_SCHEMA = "graphlog-certified-g6-opaque-phase-state/v1"
RECEIPT_SCHEMA = "graphlog-certified-g6-phase-receipt/v1"


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def _envelope(artifact_type: str, draw: G6Draw, payload: Any) -> dict[str, Any]:
    return {
        "schema_version": DEFAULT_SPEC.artifact_version,
        "artifact_type": artifact_type,
        "version_ids": {
            "executor": G6_EXECUTOR_VERSION,
            "spec": DEFAULT_SPEC.digest,
            "artifact": DEFAULT_SPEC.artifact_version,
        },
        "draw": {
            "ordinal": draw.ordinal,
            "world": draw.world,
            "seed_sha256": draw.seed_sha256,
        },
        "payload": payload,
    }


def _artifact_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "name": path.name,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _receipt(
    phase: G6Phase,
    draw: G6Draw,
    output: Path,
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA,
        "phase": phase.value,
        "world": draw.world,
        "seed_sha256": draw.seed_sha256,
        "status": status,
        "artifact_records": [
            _artifact_record(path)
            for path in sorted(output.iterdir(), key=lambda item: item.name)
        ],
    }


def _save_state(path: Path, phase: G6Phase, draw: G6Draw, payload: Any) -> None:
    wrapper = {
        "schema_version": STATE_SCHEMA,
        "executor_version": G6_EXECUTOR_VERSION,
        "phase": phase.value,
        "world": draw.world,
        "seed_sha256": draw.seed_sha256,
        "payload": payload,
    }
    path.write_bytes(pickle.dumps(wrapper, protocol=5))


def _load_state(path: Path, phase: G6Phase, draw: G6Draw) -> Any:
    value = pickle.loads(path.read_bytes())
    if not isinstance(value, dict) or value.get("schema_version") != STATE_SCHEMA \
            or value.get("executor_version") != G6_EXECUTOR_VERSION \
            or value.get("phase") != phase.value \
            or value.get("world") != draw.world \
            or value.get("seed_sha256") != draw.seed_sha256:
        raise ValueError("G6 opaque phase state identity mismatch")
    return value["payload"]


def _prior_failed(prior: Mapping[G6Phase, Path]) -> tuple[str, str] | None:
    for phase, directory in prior.items():
        receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
        if receipt["status"] != "PASS":
            return phase.value, receipt["status"]
    return None


def _failure(
    phase: G6Phase,
    draw: G6Draw,
    output: Path,
    *,
    category: str,
    detail: str,
) -> Mapping[str, Any]:
    _write_json(output / "failure.json", _envelope(
        "reported-phase-failure/v1",
        draw,
        {"category": category, "detail": detail},
    ))
    return _receipt(phase, draw, output, status="REPORTED_FAILURE")


def _array_record(array: np.ndarray) -> dict[str, Any]:
    value = np.ascontiguousarray(np.asarray(array))
    if not np.all(np.isfinite(value)):
        raise ValueError("operator artifacts cannot contain NaN or infinity")
    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "order": "C",
        "sha256": hashlib.sha256(value.tobytes(order="C")).hexdigest(),
    }


def _write_deterministic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
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


def _linearization_record(linearization: Any) -> dict[str, Any]:
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


def _compact_t6(comparison: Any) -> dict[str, Any]:
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


def _strict_prediction(values: Sequence[int], algebra: GraphLogAlgebra) -> str | None:
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
    observations: Any,
    linearization: Any,
    field: Any,
    query_derivations: Sequence[Any],
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
        _strict_prediction(algebra.evaluate_exact(dag)[dag.root_id], algebra)
        for dag in query_derivations
    )


def _commitment_lines(
    decisions: Sequence[tuple[CrossViewRelationIdentity, GraphLogIdentityDecision]],
) -> tuple[tuple[bytes, ...], CommitmentLedger]:
    ledger = CommitmentLedger()
    lines = []
    for target, decision in decisions:
        certificate = decision.certificate
        ledger = ledger.append_certificate(certificate)
        event = ledger.events[-1]
        lines.append(canonical_bytes({
            "schema_version": "graphlog-certified-commitment-record/v1",
            "target_tokens": {
                "a": target.a_token.value,
                "b": target.b_token.value,
            },
            "certificate_id": certificate.certificate_id,
            "certificate": certificate,
            "event": event,
        }))
    replayed = replay_ledger(ledger.events)
    if canonical_bytes(replayed.live_commitments) != canonical_bytes(
        ledger.state.live_commitments
    ):
        raise ValueError("ledger replay changed live commitments")
    return tuple(lines), ledger


def _structural(draw: G6Draw, output: Path) -> Mapping[str, Any]:
    raw_world = load_world(draw.world, n_train=150)
    runtime, evaluation_key = ingest_world(
        raw_world, seed=draw.seed_uint256, spec=DEFAULT_SPEC,
    )
    # The sealed capability is deliberately destroyed at the ingest boundary;
    # accuracy independently reconstructs it after the global T7 barrier.
    del evaluation_key
    pre_anchor = build_observations(runtime)
    anchors = select_anchors(
        runtime.opaque_overlap_events,
        triangle_components(pre_anchor.triangles_a),
        budget=DEFAULT_SPEC.anchor_budget,
    )
    observations = build_observations(runtime, anchors)
    scope = build_scope(observations, spec=DEFAULT_SPEC)
    extensions = classify_extensions(observations, scope)
    compiled = compile_derivations(
        runtime, scope.candidate_identities, spec=DEFAULT_SPEC,
    )
    _write_json(output / "structural.json", _envelope(
        "g6-structural-classification/v1",
        draw,
        {
            "runtime_id": canonical_digest(runtime),
            "observations": observations,
            "scope": scope,
            "extensions": extensions,
            "derivation_family_id": compiled.digest,
            "query_path_counts": compiled.query_path_counts,
        },
    ))
    _save_state(
        output / "opaque-state.pkl",
        G6Phase.STRUCTURAL,
        draw,
        (observations, scope, extensions, compiled),
    )
    if not extensions.solutions:
        return _receipt(G6Phase.STRUCTURAL, draw, output, status="REPORTED_FAILURE")
    return _receipt(G6Phase.STRUCTURAL, draw, output, status="PASS")


def _t5(draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path) -> Mapping[str, Any]:
    observations, scope, extensions, compiled = _load_state(
        prior[G6Phase.STRUCTURAL] / "opaque-state.pkl",
        G6Phase.STRUCTURAL,
        draw,
    )
    linearization = build_linearization(observations, scope, spec=DEFAULT_SPEC)
    boundary = build_anchor_boundary(observations, linearization)
    coboundary = assemble_coboundary(linearization.core)
    system = partition_dirichlet(coboundary, boundary.core)
    t5_run = run_t5(
        system,
        SolverConfig(field_tolerance=float(DEFAULT_SPEC.field_tolerance)),
    )
    arrays = {
        "coboundary": coboundary.dense_delta,
        "laplacian": coboundary.laplacian,
        "laplacian_uu": system.laplacian_uu,
        "laplacian_ub": system.laplacian_ub,
        "boundary_values": system.boundary_values,
    }
    if t5_run.field is not None:
        arrays.update({
            "field_values": t5_run.field.values,
            "field_residual": t5_run.field.residual,
            "normal_residual": t5_run.field.normal_residual,
        })
    _write_deterministic_npz(output / "operator.npz", arrays)
    _write_json(output / "t5.json", _envelope(
        "g6-t5-operator-certificate/v1",
        draw,
        {
            "linearization": _linearization_record(linearization),
            "boundary": boundary,
            "certificate": t5_run.certificate,
            "arrays": {name: _array_record(value) for name, value in arrays.items()},
        },
    ))
    if t5_run.field is None:
        return _receipt(G6Phase.T5, draw, output, status="REPORTED_FAILURE")
    _save_state(
        output / "opaque-state.pkl",
        G6Phase.T5,
        draw,
        (
            observations, scope, extensions, compiled, linearization,
            system, t5_run,
        ),
    )
    return _receipt(G6Phase.T5, draw, output, status="PASS")


def _t6(draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path) -> Mapping[str, Any]:
    (
        observations, scope, extensions, compiled, linearization,
        system, t5_run,
    ) = _load_state(
        prior[G6Phase.T5] / "opaque-state.pkl", G6Phase.T5, draw,
    )
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
            spec=DEFAULT_SPEC,
        )
        comparisons.append(certify_graphlog_comparison(
            extension_id=extension_id,
            algebra=algebra,
            derivations=all_derivations,
            field_comparison=field_comparison,
            spec=DEFAULT_SPEC,
        ))
    separation = check_separation(tuple(
        comparison.behavior for comparison in comparisons
    ))
    _write_json(output / "comparison.json", _envelope(
        "g6-t6-comparison/v1",
        draw,
        {"comparisons": tuple(_compact_t6(item) for item in comparisons)},
    ))
    _write_json(output / "separation.json", _envelope(
        "g6-t6-separation/v1", draw, separation,
    ))
    if not all(comparison.report.admissible for comparison in comparisons) \
            or not separation.separating:
        return _receipt(G6Phase.T6, draw, output, status="REPORTED_FAILURE")
    certificates_by_extension = tuple(
        comparison.report.certificates for comparison in comparisons
    )
    _save_state(
        output / "opaque-state.pkl",
        G6Phase.T6,
        draw,
        (
            observations, scope, extensions, compiled, linearization,
            t5_run, certificates_by_extension, separation,
        ),
    )
    return _receipt(G6Phase.T6, draw, output, status="PASS")


def _t7(draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path) -> Mapping[str, Any]:
    (
        observations, scope, extensions, compiled, linearization,
        t5_run, certificate_rows, separation,
    ) = _load_state(
        prior[G6Phase.T6] / "opaque-state.pkl", G6Phase.T6, draw,
    )
    dag_by_id = {
        dag.derivation_id: dag for dag in compiled.identity_derivations
    }
    certificates_by_extension = tuple({
        certificate.derivation_id: certificate
        for certificate in certificates
    } for certificates in certificate_rows)
    target_rows = []
    decisions = []
    evaluation_rows = []
    shared_operator_report = None
    anchor_pairs = {
        (anchor.a_token, anchor.b_token) for anchor in observations.anchors
    }
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
                spec=DEFAULT_SPEC,
                shared_operator_report=shared_operator_report,
            )
            if decision.perturbation is not None and shared_operator_report is None:
                shared_operator_report = decision.perturbation
            is_anchor = (a_token, b_token) in anchor_pairs
            target_rows.append({
                "target_id": target.target_id,
                "a_token": a_token.value,
                "b_token": b_token.value,
                "is_anchor": is_anchor,
                "classification": classification,
                "policy": policy,
                "decision_id": decision.certificate.certificate_id,
            })
            decisions.append((target, decision))
            evaluation_rows.append((
                target.target_id,
                a_token.value,
                b_token.value,
                is_anchor,
                classification.verdict.value,
                decision.certificate.outcome.value,
                decision.certificate.commitment,
            ))

    commitment_lines, ledger = _commitment_lines(decisions)
    (output / "commitments.jsonl").write_bytes(
        b"\n".join(commitment_lines) + b"\n"
    )
    predictions = _replacement_predictions(
        observations=observations,
        linearization=linearization,
        field=t5_run.field,
        query_derivations=compiled.query_derivations,
        decisions=decisions,
    )
    counts = {
        outcome.value: sum(
            decision.certificate.outcome is outcome
            for _target, decision in decisions
        )
        for outcome in CommitmentOutcome
    }
    _write_json(output / "targets.json", _envelope(
        "g6-t7-target-projection-policy/v1",
        draw,
        {
            "targets": target_rows,
            "commitment_counts": counts,
            "ledger_live_commitments": len(ledger.state.live_commitments),
        },
    ))
    _save_state(
        output / "opaque-predictions.pkl",
        G6Phase.T7_SAFETY,
        draw,
        (predictions, tuple(evaluation_rows)),
    )
    return _receipt(G6Phase.T7_SAFETY, draw, output, status="PASS")


def _accuracy(
    draw: G6Draw,
    prior: Mapping[G6Phase, Path],
    output: Path,
) -> Mapping[str, Any]:
    prior_failure = _prior_failed(prior)
    predictions = None
    evaluation_rows: Sequence[
        tuple[str, str, str, bool, str, str, str | None]
    ] = ()
    if prior_failure is None:
        predictions, evaluation_rows = _load_state(
            prior[G6Phase.T7_SAFETY] / "opaque-predictions.pkl",
            G6Phase.T7_SAFETY,
            draw,
        )
    else:
        structural_state = prior[G6Phase.STRUCTURAL] / "opaque-state.pkl"
        if structural_state.is_file():
            observations, scope, extensions, _compiled = _load_state(
                structural_state, G6Phase.STRUCTURAL, draw,
            )
            anchor_pairs = {
                (anchor.a_token, anchor.b_token)
                for anchor in observations.anchors
            }
            evaluation_rows = tuple(
                (
                    target.target_id,
                    a_token.value,
                    b_token.value,
                    (a_token, b_token) in anchor_pairs,
                    classify_target(
                        observations, scope, target, extensions=extensions,
                    ).verdict.value,
                    CommitmentOutcome.ABSTAIN.value,
                    None,
                )
                for a_token in observations.relation_tokens_a
                for b_token in observations.relation_tokens_b
                for target in (CrossViewRelationIdentity(a_token, b_token),)
            )
    raw_world = load_world(draw.world, n_train=150)
    _runtime, evaluation_key = ingest_world(
        raw_world, seed=draw.seed_uint256, spec=DEFAULT_SPEC,
    )
    del _runtime
    from .graphlog_g6_evaluation import evaluate_g6_draw

    evaluation = evaluate_g6_draw(
        evaluation_key,
        world=draw.world,
        seed=draw.seed_uint256,
        seed_sha256=draw.seed_sha256,
        opaque_a_predictions=predictions,
        identity_decisions=evaluation_rows,
    )
    _write_json(output / "evaluation.json", _envelope(
        "g6-evaluation-only-join/v1", draw, evaluation,
    ))
    if prior_failure is not None:
        _write_json(output / "premise-failure.json", _envelope(
            "g6-accuracy-premise-failure/v1",
            draw,
            {"failed_phase": prior_failure[0], "status": prior_failure[1]},
        ))
        return _receipt(G6Phase.ACCURACY, draw, output, status="REPORTED_FAILURE")
    return _receipt(G6Phase.ACCURACY, draw, output, status="PASS")


def execute_phase(
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """Execute exactly one preregistered phase/world unit."""
    try:
        if phase is G6Phase.ACCURACY:
            return _accuracy(draw, prior_phase_directories, output_directory)
        prior_failure = _prior_failed(prior_phase_directories)
        if prior_failure is not None:
            return _failure(
                phase,
                draw,
                output_directory,
                category="PRIOR_PHASE_FAILURE",
                detail=f"{prior_failure[0]}:{prior_failure[1]}",
            )
        if phase is G6Phase.STRUCTURAL:
            return _structural(draw, output_directory)
        if phase is G6Phase.T5:
            return _t5(draw, prior_phase_directories, output_directory)
        if phase is G6Phase.T6:
            return _t6(draw, prior_phase_directories, output_directory)
        if phase is G6Phase.T7_SAFETY:
            return _t7(draw, prior_phase_directories, output_directory)
    except Exception as error:
        return _failure(
            phase,
            draw,
            output_directory,
            category=f"{type(error).__module__}.{type(error).__qualname__}",
            detail=str(error),
        )
    raise ValueError(f"unsupported G6 phase {phase!r}")
