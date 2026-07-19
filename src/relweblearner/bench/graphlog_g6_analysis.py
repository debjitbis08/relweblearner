"""Read-only validation and preregistered acceptance analysis for G6 output."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ..certification.t7 import PremiseId
from ..certification.types import canonical_bytes, canonical_data, canonical_digest
from .graphlog_g6 import (
    G6_AMENDMENT,
    G6_MANIFEST,
    G6Phase,
    _sha256_file,
    _unit_directory,
    _validate_unit_directory,
    load_amendment_chain,
    load_study_manifest,
)
from .graphlog_g6_executor import _array_record, _load_state


G6_ANALYSIS_VERSION = "graphlog-certified-g6-analysis/v1"
BOOTSTRAP_REPLICATES = 10_000
INTERVAL_ALPHA = 0.05


def _canonical_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    value = json.loads(data)
    canonical_data(value)
    if data != canonical_bytes(value) + b"\n":
        raise ValueError(f"non-canonical G6 JSON artifact: {path}")
    if not isinstance(value, dict):
        raise ValueError(f"G6 JSON artifact is not an object: {path}")
    return value


def _validate_operator(unit: Path) -> None:
    t5 = _canonical_json(unit / "t5.json")
    declared = t5["payload"]["arrays"]
    with np.load(unit / "operator.npz", allow_pickle=False) as arrays:
        if set(arrays.files) != set(declared):
            raise ValueError("G6 operator array membership mismatch")
        for name in arrays.files:
            if _array_record(arrays[name]) != declared[name]:
                raise ValueError(f"G6 operator array mismatch: {name}")


def _validate_commitments(unit: Path) -> tuple[int, bool]:
    path = unit / "commitments.jsonl"
    if not path.is_file():
        return 0, True
    premise_ids = {premise.value for premise in PremiseId}
    commits = 0
    all_commit_premises = True
    for line in path.read_bytes().splitlines():
        row = json.loads(line)
        canonical_data(row)
        if line != canonical_bytes(row):
            raise ValueError("non-canonical G6 commitment row")
        certificate = row["certificate"]
        if row["certificate_id"] != canonical_digest(certificate):
            raise ValueError("G6 commitment certificate id mismatch")
        event = row["event"]
        if event["event_id"] != canonical_digest(event["body"]):
            raise ValueError("G6 commitment event id mismatch")
        if certificate["outcome"] == "COMMIT":
            commits += 1
            premises = certificate["premises"]
            all_commit_premises = all_commit_premises and (
                len(premises) == len(premise_ids)
                and {item["premise_id"] for item in premises} == premise_ids
                and all(item["satisfied"] for item in premises)
            )
    return commits, all_commit_premises


def _binomial_upper_tail(n: int, x: int, probability: float) -> float:
    return sum(
        math.comb(n, k)
        * probability ** k
        * (1.0 - probability) ** (n - k)
        for k in range(x, n + 1)
    )


def _clopper_pearson_lower(
    successes: int,
    trials: int,
    *,
    alpha: float = INTERVAL_ALPHA,
) -> float:
    """Exact one-sided lower confidence limit for a binomial proportion."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("invalid binomial counts")
    if successes == 0:
        return 0.0
    low, high = 0.0, successes / trials
    for _iteration in range(100):
        midpoint = (low + high) / 2.0
        if _binomial_upper_tail(trials, successes, midpoint) < alpha:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot take a percentile of no values")
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight
    )


def _coverage_interval(
    rows: Sequence[tuple[int, int]],
    *,
    manifest_id: str,
) -> tuple[float, float]:
    seed = int.from_bytes(hashlib.sha256(
        manifest_id.encode("utf-8") + b"coverage-bootstrap/v1"
    ).digest(), "big")
    rng = random.Random(seed)
    values = []
    for _replicate in range(BOOTSTRAP_REPLICATES):
        sample = tuple(rows[rng.randrange(len(rows))] for _item in rows)
        numerator = sum(row[0] for row in sample)
        denominator = sum(row[1] for row in sample)
        values.append(numerator / denominator if denominator else 0.0)
    values.sort()
    return (
        _percentile(values, INTERVAL_ALPHA / 2.0),
        _percentile(values, 1.0 - INTERVAL_ALPHA / 2.0),
    )


def analyze_study(*, root: Path) -> dict[str, Any]:
    """Validate a completed G6 block and compute frozen acceptance rules."""
    study = load_study_manifest(root / G6_MANIFEST)
    amendment = load_amendment_chain(root / G6_AMENDMENT)[-1]
    output = root / study.output_root
    if not output.is_dir():
        raise ValueError("completed G6 output is absent")
    index = _canonical_json(output / "study-index.json")
    if index.get("study_manifest_id") != study.manifest_id \
            or index.get("amendment_manifest_id") != amendment.manifest_id \
            or index.get("completed_phases") != [
                phase.value for phase in study.phases
            ] \
            or index.get("world_order") != [draw.world for draw in study.draws]:
        raise ValueError("G6 study index differs from the effective freeze")

    phase_status_counts = {
        phase.value: {"PASS": 0, "REPORTED_FAILURE": 0}
        for phase in study.phases
    }
    world_rows = []
    total_t7_commits = 0
    all_commit_premises = True
    for draw in study.draws:
        statuses = {}
        for phase in study.phases:
            unit = _unit_directory(output, phase, draw)
            receipt_path = unit / "receipt.json"
            _validate_unit_directory(
                unit, phase, draw, _sha256_file(receipt_path),
            )
            receipt = _canonical_json(receipt_path)
            status = receipt["status"]
            statuses[phase.value] = status
            phase_status_counts[phase.value][status] += 1
            for record in receipt["artifact_records"]:
                artifact = unit / record["name"]
                if artifact.suffix == ".json":
                    _canonical_json(artifact)
            if phase is G6Phase.STRUCTURAL:
                if (unit / "opaque-state.pkl").is_file():
                    _load_state(unit / "opaque-state.pkl", phase, draw)
            elif phase is G6Phase.T5:
                if (unit / "t5.json").is_file() \
                        and (unit / "operator.npz").is_file():
                    _validate_operator(unit)
                if status == "PASS":
                    _load_state(unit / "opaque-state.pkl", phase, draw)
            elif phase is G6Phase.T6 and status == "PASS":
                _load_state(unit / "opaque-state.pkl", phase, draw)
            elif phase is G6Phase.T7_SAFETY and status == "PASS":
                _load_state(unit / "opaque-predictions.pkl", phase, draw)

        t7_unit = _unit_directory(output, G6Phase.T7_SAFETY, draw)
        commit_count, premises_ok = _validate_commitments(t7_unit)
        total_t7_commits += commit_count
        all_commit_premises = all_commit_premises and premises_ok
        accuracy_unit = _unit_directory(output, G6Phase.ACCURACY, draw)
        evaluation_path = accuracy_unit / "evaluation.json"
        if not evaluation_path.is_file():
            world_rows.append({
                "world": draw.world,
                "phase_statuses": statuses,
                "query_summary": None,
                "identity_summary": None,
            })
            continue
        evaluation = _canonical_json(evaluation_path)["payload"]
        query = dict(evaluation["query_summary"])
        identity = dict(evaluation["identity_summary"])
        identity_rows = tuple(evaluation["identity_rows"])
        world_rows.append({
            "world": draw.world,
            "phase_statuses": statuses,
            "query_summary": query,
            "identity_summary": identity,
            "identity_commit_total": sum(
                row["outcome"] == "COMMIT" for row in identity_rows
            ),
            "identity_commit_true": sum(
                row["outcome"] == "COMMIT" and row["true_identity"]
                for row in identity_rows
            ),
        })

    complete_accuracy = all(row["query_summary"] is not None for row in world_rows)
    scored_rows = [row for row in world_rows if row["query_summary"] is not None]
    primary_differences = [
        row["query_summary"]["replacement_accuracy"]
        - row["query_summary"]["discrete_accuracy"]
        for row in scored_rows
    ]
    secondary_differences = [
        row["query_summary"]["replacement_accuracy"]
        - row["query_summary"]["graded_accuracy"]
        for row in scored_rows
    ]
    macro_primary = (
        sum(primary_differences) / len(primary_differences)
        if complete_accuracy else None
    )
    macro_secondary = (
        sum(secondary_differences) / len(secondary_differences)
        if complete_accuracy else None
    )
    false_positive_commits = sum(
        row["identity_summary"]["false_positive_identity_commits"]
        for row in scored_rows
    )
    confirmed_nonanchor_commits = sum(
        row["identity_summary"][
            "evaluation_confirmed_real_nonanchor_identity_commits"
        ]
        for row in scored_rows
    )
    all_identity_commits = sum(
        row["identity_commit_total"] for row in scored_rows
    )
    true_identity_commits = sum(
        row["identity_commit_true"] for row in scored_rows
    )
    coverage_rows = tuple((
        row["identity_summary"]["nonanchor_identity_commits"],
        row["identity_summary"]["nonanchor_structural_identical"],
    ) for row in scored_rows)
    coverage_numerator = sum(row[0] for row in coverage_rows)
    coverage_denominator = sum(row[1] for row in coverage_rows)
    coverage = (
        coverage_numerator / coverage_denominator
        if coverage_denominator else 0.0
    )
    coverage_interval = (
        _coverage_interval(coverage_rows, manifest_id=study.manifest_id)
        if complete_accuracy else None
    )

    evaluation_join_complete = total_t7_commits == all_identity_commits
    soundness = (
        all_commit_premises
        and false_positive_commits == 0
        and evaluation_join_complete
    )
    non_vacuity = confirmed_nonanchor_commits > 0
    primary = macro_primary is not None and macro_primary >= 0.0
    secondary = macro_secondary is not None and macro_secondary >= 0.0
    usefulness = soundness and non_vacuity and primary
    return {
        "schema_version": G6_ANALYSIS_VERSION,
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "world_count": len(study.draws),
        "phase_status_counts": phase_status_counts,
        "certificate_soundness_details": {
            "all_commit_certificates_have_complete_satisfied_six_premises": (
                all_commit_premises
            ),
            "false_positive_identity_commits": false_positive_commits,
            "t7_commit_count": total_t7_commits,
            "evaluation_joined_commit_count": all_identity_commits,
            "evaluation_join_complete": evaluation_join_complete,
        },
        "non_vacuity_details": {
            "evaluation_confirmed_real_nonanchor_identity_commits": (
                confirmed_nonanchor_commits
            ),
        },
        "accuracy_details": {
            "complete_world_count": len(scored_rows),
            "macro_mean_replacement_minus_discrete": macro_primary,
            "macro_mean_replacement_minus_graded": macro_secondary,
        },
        "identity_commit_precision": {
            "true": true_identity_commits,
            "total": all_identity_commits,
            "precision": (
                true_identity_commits / all_identity_commits
                if all_identity_commits else None
            ),
            "one_sided_95_percent_exact_lower": (
                _clopper_pearson_lower(true_identity_commits, all_identity_commits)
                if all_identity_commits else None
            ),
        },
        "coverage": {
            "numerator": coverage_numerator,
            "denominator": coverage_denominator,
            "pooled_fraction": coverage,
            "paired_world_bootstrap_95_percent_interval": coverage_interval,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        },
        "acceptance": {
            "certificate_soundness": soundness,
            "non_vacuity": non_vacuity,
            "primary_usefulness": primary,
            "secondary_usefulness": secondary,
            "usefulness_claim": usefulness,
        },
        "world_rows": world_rows,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(analyze_study(root=args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
