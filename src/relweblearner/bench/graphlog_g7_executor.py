"""Reviewed G7 phase adapter: G6 phases plus the conditional overlay.

Structural and T5 delegate verbatim to the pinned G6 executor, so their
artifacts are bitwise identical to a G6 rerun (the ``no_regression``
acceptance rule).  T6 reproduces the pinned base comparison and separation
artifacts exactly, then adds the pivot-conditioned separation layer from
``graphlog_g7_conditional``.  T7 and accuracy delegate to the pinned G6
implementations and append G7-only overlay artifacts (conditional
commitments and their evaluation-key join).  Every receipt is stamped with
the G7 receipt schema; no pinned module is modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from ..certification.t6 import check_separation, compare_field
from ..certification.types import canonical_digest
from . import graphlog_g6_executor as g6x
from .graphlog_certified.enrichment import (
    GraphLogAlgebra,
    certify_graphlog_comparison,
)
from .graphlog_certified.ingest import ingest_world
from .graphlog_certified.linearization import encode_extension
from .graphlog_certified.spec import DEFAULT_SPEC
from .graphlog_g6 import G6Draw, G6Phase
from .graphlog_g7 import G7_RECEIPT_SCHEMA
from .graphlog_g7_conditional import (
    conditional_separation,
    conditioned_branch,
    discover_conditions,
    hedge_localization,
)
from .graphlog import load_world


G7_EXECUTOR_VERSION = "graphlog-certified-g7-executor/v1"
CONDITIONAL_STATE_FILE = "g7-conditional-state.pkl"


def _receipt(
    phase: G6Phase,
    draw: G6Draw,
    output: Path,
    *,
    status: str,
) -> dict[str, Any]:
    receipt = g6x._receipt(phase, draw, output, status=status)
    receipt["schema_version"] = G7_RECEIPT_SCHEMA
    return receipt


def _restamp(receipt: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(receipt)
    value["schema_version"] = G7_RECEIPT_SCHEMA
    return value


def _envelope(artifact_type: str, draw: G6Draw, payload: Any) -> dict[str, Any]:
    value = g6x._envelope(artifact_type, draw, payload)
    value["version_ids"] = {
        **value["version_ids"], "g7_executor": G7_EXECUTOR_VERSION,
    }
    return value


def _disputed_pair_labels(
    linearization: Any,
    disputed_indices: Sequence[int],
) -> tuple[tuple[int, str, str], ...]:
    """Map disputed cochain coordinates to (index, a_token, b_token) labels."""
    width = len(linearization.b_tokens)
    labels = []
    for index in disputed_indices:
        a_index, b_index = divmod(int(index), width)
        labels.append((
            int(index),
            linearization.a_tokens[a_index].value,
            linearization.b_tokens[b_index].value,
        ))
    return tuple(labels)


def _t6(draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path) -> Mapping[str, Any]:
    (
        observations, scope, extensions, compiled, linearization,
        system, t5_run,
    ) = g6x._load_state(
        prior[G6Phase.T5] / "opaque-state.pkl", G6Phase.T5, draw,
    )
    # --- Base layer: byte-identical reproduction of the pinned G6 T6 body.
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
    g6x._write_json(output / "comparison.json", g6x._envelope(
        "g6-t6-comparison/v1",
        draw,
        {"comparisons": tuple(g6x._compact_t6(item) for item in comparisons)},
    ))
    g6x._write_json(output / "separation.json", g6x._envelope(
        "g6-t6-separation/v1", draw, separation,
    ))
    admissible = all(comparison.report.admissible for comparison in comparisons)
    base_separating = bool(separation.separating)

    # --- Conditional layer: invent pivot conditions only when required.
    cochains = tuple(
        encode_extension(extension, linearization).reshape(-1)
        for extension in extensions.solutions
    )
    coordinate_ids = tuple(linearization.core.coordinate_ids)
    conditional_record: dict[str, Any]
    conditional_state: dict[str, Any] | None = None
    if len(cochains) < 2:
        conditional_record = {
            "status": "UNIQUE",
            "conditions_invented": 0,
            "separating": None,
        }
    elif base_separating:
        conditional_record = {
            "status": "BASE_SEPARATING",
            "conditions_invented": 0,
            "separating": None,
        }
    else:
        discovery = discover_conditions(cochains, coordinate_ids)
        if discovery.status == "AMBIGUITY_OVERFLOW":
            conditional_record = {
                "status": "AMBIGUITY_OVERFLOW",
                "solution_count": discovery.solution_count,
                "conditions_invented": 0,
                "separating": False,
            }
        else:
            branches = tuple(
                conditioned_branch(
                    branch_index=index,
                    base_system=system,
                    cochain=cochain,
                    pivot_indices=discovery.pivot_indices,
                    coordinate_ids=coordinate_ids,
                    field_tolerance=float(DEFAULT_SPEC.field_tolerance),
                )
                for index, cochain in enumerate(cochains)
            )
            certificate = conditional_separation(
                discovery=discovery,
                branches=branches,
                cochains=cochains,
                coordinate_ids=coordinate_ids,
            )
            localization = hedge_localization(
                t5_run.field.values, cochains, discovery.disputed_indices,
            )
            conditional_record = {
                "status": (
                    "SEPARATING_CONDITIONAL" if certificate["separating"]
                    else "CONDITIONED_NOT_SEPARATING"
                ),
                "conditions_invented": len(discovery.pivot_indices),
                "condition_id": discovery.condition_id,
                "certificate": certificate,
                "hedge_localization": localization,
                "separating": bool(certificate["separating"]),
            }
            if certificate["separating"]:
                conditional_state = {
                    "condition_id": discovery.condition_id,
                    "certificate_digest": canonical_digest(certificate),
                    "pivot_labels": _disputed_pair_labels(
                        linearization, discovery.pivot_indices,
                    ),
                    "disputed_labels": _disputed_pair_labels(
                        linearization, discovery.disputed_indices,
                    ),
                    "branch_disputed_values": tuple(
                        tuple(
                            int(cochain[index])
                            for index in discovery.disputed_indices
                        )
                        for cochain in cochains
                    ),
                    "branch_pivot_values": tuple(
                        tuple(
                            int(cochain[index])
                            for index in discovery.pivot_indices
                        )
                        for cochain in cochains
                    ),
                }
    g6x._write_json(output / "conditional-separation.json", _envelope(
        "g7-t6-conditional-separation/v1", draw, conditional_record,
    ))

    passed = admissible and (
        base_separating or bool(conditional_record.get("separating"))
    )
    if not passed:
        return _receipt(G6Phase.T6, draw, output, status="REPORTED_FAILURE")
    certificates_by_extension = tuple(
        comparison.report.certificates for comparison in comparisons
    )
    g6x._save_state(
        output / "opaque-state.pkl",
        G6Phase.T6,
        draw,
        (
            observations, scope, extensions, compiled, linearization,
            t5_run, certificates_by_extension, separation,
        ),
    )
    if conditional_state is not None:
        g6x._save_state(
            output / CONDITIONAL_STATE_FILE,
            G6Phase.T6,
            draw,
            conditional_state,
        )
    return _receipt(G6Phase.T6, draw, output, status="PASS")


def _load_conditional_state(
    prior: Mapping[G6Phase, Path], draw: G6Draw,
) -> dict[str, Any] | None:
    path = prior[G6Phase.T6] / CONDITIONAL_STATE_FILE
    if not path.is_file():
        return None
    return g6x._load_state(path, G6Phase.T6, draw)


def _t7(draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path) -> Mapping[str, Any]:
    base = g6x._t7(draw, prior, output)
    conditional = _load_conditional_state(prior, draw)
    if conditional is not None:
        rows = []
        for branch_index, values in enumerate(
            conditional["branch_disputed_values"]
        ):
            for (index, a_value, b_value), value in zip(
                conditional["disputed_labels"], values, strict=True,
            ):
                rows.append({
                    "condition_id": conditional["condition_id"],
                    "branch_index": branch_index,
                    "coordinate_index": index,
                    "a_token": a_value,
                    "b_token": b_value,
                    "commitment": "IDENTICAL" if value else "DISTINCT",
                    "outcome": "COMMIT_CONDITIONAL",
                })
        g6x._write_json(output / "g7-conditional-commitments.json", _envelope(
            "g7-t7-conditional-commitments/v1",
            draw,
            {
                "condition_id": conditional["condition_id"],
                "certificate_digest": conditional["certificate_digest"],
                "pivot_labels": conditional["pivot_labels"],
                "branch_pivot_values": conditional["branch_pivot_values"],
                "commitments": tuple(rows),
                "discharge_rule": (
                    "a future observation fixing every pivot pair resolves "
                    "the condition; the matching branch's commitments become "
                    "unconditional and the others are pruned"
                ),
            },
        ))
    return _receipt(G6Phase.T7_SAFETY, draw, output, status=base["status"])


def _accuracy(
    draw: G6Draw,
    prior: Mapping[G6Phase, Path],
    output: Path,
) -> Mapping[str, Any]:
    base = g6x._accuracy(draw, prior, output)
    conditional = _load_conditional_state(prior, draw)
    if conditional is not None:
        raw_world = load_world(draw.world, n_train=150)
        _runtime, evaluation_key = ingest_world(
            raw_world, seed=draw.seed_uint256, spec=DEFAULT_SPEC,
        )
        del _runtime
        inv_a = {
            opaque: raw
            for raw, opaque in evaluation_key._EvaluationKey__perm_a.items()
        }
        inv_b = {
            opaque: raw
            for raw, opaque in evaluation_key._EvaluationKey__perm_b.items()
        }

        def true_identity(a_value: str, b_value: str) -> bool:
            raw_a = inv_a.get(a_value)
            return raw_a is not None and raw_a == inv_b.get(b_value)

        pivot_truth = tuple(
            1 if true_identity(a_value, b_value) else 0
            for _index, a_value, b_value in conditional["pivot_labels"]
        )
        true_branch = None
        for branch_index, values in enumerate(
            conditional["branch_pivot_values"]
        ):
            if tuple(values) == pivot_truth:
                true_branch = branch_index
                break
        rows = []
        false_positives = 0
        for (index, a_value, b_value), truth in zip(
            conditional["disputed_labels"],
            (
                true_identity(a_value, b_value)
                for _index, a_value, b_value in conditional["disputed_labels"]
            ),
            strict=True,
        ):
            committed = None
            correct = None
            if true_branch is not None:
                position = [
                    item[0] for item in conditional["disputed_labels"]
                ].index(index)
                committed = bool(
                    conditional["branch_disputed_values"][true_branch][position]
                )
                correct = committed == bool(truth)
                if committed and not truth:
                    false_positives += 1
            rows.append({
                "coordinate_index": index,
                "a_token": a_value,
                "b_token": b_value,
                "true_identity": bool(truth),
                "true_branch_commitment": committed,
                "correct": correct,
            })
        g6x._write_json(output / "g7-conditional-evaluation.json", _envelope(
            "g7-accuracy-conditional-join/v1",
            draw,
            {
                "condition_id": conditional["condition_id"],
                "pivot_truth": pivot_truth,
                "true_branch": true_branch,
                "branch_matched_truth": true_branch is not None,
                "disputed_targets": tuple(rows),
                "conditional_false_positive_commits": (
                    false_positives if true_branch is not None
                    else len(conditional["disputed_labels"])
                ),
            },
        ))
    return _receipt(G6Phase.ACCURACY, draw, output, status=base["status"])


def execute_phase(
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """Execute exactly one preregistered G7 phase/world unit."""
    try:
        if phase is G6Phase.ACCURACY:
            return _accuracy(draw, prior_phase_directories, output_directory)
        prior_failure = g6x._prior_failed(prior_phase_directories)
        if prior_failure is not None:
            return _restamp(g6x._failure(
                phase,
                draw,
                output_directory,
                category="PRIOR_PHASE_FAILURE",
                detail=f"{prior_failure[0]}:{prior_failure[1]}",
            ))
        if phase is G6Phase.STRUCTURAL:
            return _restamp(g6x._structural(draw, output_directory))
        if phase is G6Phase.T5:
            return _restamp(g6x._t5(draw, prior_phase_directories, output_directory))
        if phase is G6Phase.T6:
            return _t6(draw, prior_phase_directories, output_directory)
        if phase is G6Phase.T7_SAFETY:
            return _t7(draw, prior_phase_directories, output_directory)
    except Exception as error:
        return _restamp(g6x._failure(
            phase,
            draw,
            output_directory,
            category=f"{type(error).__module__}.{type(error).__qualname__}",
            detail=str(error),
        ))
    raise ValueError(f"unsupported G7 phase {phase!r}")
