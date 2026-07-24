"""Manifest-locked, premise-first orchestration for GraphLog G9.

G9 is the single-part successor to the sealed G8 blocks.  It tests the
anti-propagation mechanism predictor frozen by the sealed Phase A analysis:
the predictor, its threshold, and the Phase B report script are all committed
before any fresh draw exists, and the executed block's artifacts are exactly
a G8 part-``"g8"`` unit's -- the G9 layer is realized report-side by the
pre-committed script against the sealed block, so unlike G8 there is no
second execution part (the G9 "verification" runs against the already-sealed
G8 block, not through this harness).  One manifest, one part, one adapter:

* **Measurement** (``part == "g9"``): fresh beacon-seeded draws, outcomes
  unobserved -- the real preregistered test of the mechanism predictor.

Beyond the G8 contract the manifest carries a required
``g9_preregistration`` section pinning the sealed Phase A analysis script,
its two-round output digests, the pre-committed Phase B report script, the
sealed G8 study index (the plan §6 ordering witness), and the frozen
predictor/claim literals; ``repository_preflight`` verifies the on-disk
script and index digests against it.  Like the G6--G8 control planes this
module lives outside ``bench.graphlog_certified`` so the frozen G0--G5
source digest is unchanged, imports no dataset loader during preflight, and
creates no output until an execution-enabling amendment names a pinned
adapter.

The G9 manifest and amendment files do not exist yet -- authoring them is a
separate human-gated governance step -- so every loader fails cleanly with a
``G9PreflightError`` when its document is absent, rather than leaking a raw
``OSError``.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..certification.types import canonical_bytes, canonical_data
from .graphlog_certified.notarization import DEFAULT_MANIFEST, validate_manifest
from .graphlog_certified.spec import DEFAULT_SPEC, VALIDATION_WORLDS
from .graphlog_g6 import (
    G6Amendment,
    G6Draw,
    G6Phase,
    G6PreflightError,
    PhaseExecutor,
    _canonical_document,
    _git,
    _sha256_file,
    _unit_directory,
    _validate_frozen_g5_directory,
)


G9_MANIFEST = Path("results/graphlog-certified/g9-validation-manifest.json")
G9_AMENDMENT = Path("results/graphlog-certified/g9-validation-amendment.json")
G9_MANIFEST_SCHEMA = "graphlog-certified-g9-validation-manifest/v1"
G9_AMENDMENT_SCHEMA = "graphlog-certified-g9-validation-amendment/v1"
G9_HARNESS_VERSION = "graphlog-certified-g9-harness/v1"
G9_RECEIPT_SCHEMA = "graphlog-certified-g9-receipt/v1"
PHASE_ORDER = ("structural", "T5", "T6", "T7_safety", "accuracy")

# Single-part design: one harness, one manifest.  The part-keyed shape is
# kept from G8 so the manifest's declared ``part`` still selects the output
# root, study id, change scope, and adapter by mechanism, but only the
# measurement part exists; the G9 verification is report-side against the
# already-sealed G8 block and never executes here.
G9_PART_MEASUREMENT = "g9"
G9_PARTS = (G9_PART_MEASUREMENT,)
G9_OUTPUT_ROOTS = {
    G9_PART_MEASUREMENT: Path("results/graphlog-certified/g9"),
}
G9_STUDY_IDS = {
    G9_PART_MEASUREMENT: "graphlog-certified-g9-anti-propagation-mechanism/v1",
}
G9_PREREGISTRATION_STATUS = {
    G9_PART_MEASUREMENT: "committed_before_g9_draw_generation_or_scoring",
}
G9_CHANGE_SCOPES = {
    G9_PART_MEASUREMENT: "anti_propagation_mechanism_predictor_fresh_draws",
}
G9_ACCEPTANCE_RULES = {
    "crossing_set_reproducibility",
    "margin_error_identity",
    "crossing_guard_band",
    "predictor_accuracy_floor",
    "non_vacuity",
    "conditional_layer_unchanged",
    "certificate_soundness",
}
# Part identity is threaded to the phase adapter through the pinned executor
# qualname, exactly as in G8; with a single part the pairing check still
# refuses any foreign adapter (in particular the G8 part adapters) before
# any output is created.
G9_EXECUTOR_QUALNAMES = {
    G9_PART_MEASUREMENT: "execute_phase_g9",
}

# Frozen preregistration literals (plan §5 and §8.1 numeric confirmation):
# the manifest must carry these exact declarations, so a drifted predictor
# family, floor, pass rule, or non-vacuity minimum fails closed at load.
G9_PREREGISTRATION_KEYS = {
    "phase_a_script_sha256",
    "phase_b_report_script_sha256",
    "phase_a_output_sha256",
    "sealed_g8_study_index_sha256",
    "predictor",
    "claim_4",
    "claim_5",
    "non_vacuity",
}
G9_PREDICTOR_LITERAL = {
    "family": "chebyshev-semi-iteration",
    "degree": 3,
    "kappa_design": 30,
    "diagnostic_ceiling": 0.99,
}
G9_CLAIM_4_LITERAL = {
    "floor": 0.776,
    "delta_over_baseline": 0.02,
    "pass_rule": "mean-jeffreys-lower-0.20-quantile",
}
G9_CLAIM_5_LITERAL = "dropped-depth-spearman-0.222"
G9_NON_VACUITY_LITERAL = {
    "minimum_unambiguous_crossing_records": 5,
    "minimum_conditioned_worlds": 2,
}
# Repository files whose digests the manifest preregisters; verified at
# ``repository_preflight`` time (not load time) so a manifest can be
# committed before the report script lands, but never executed past it.
G9_PHASE_A_SCRIPT = Path("scripts/g9_phase_a_analysis.py")
G9_PHASE_B_REPORT_SCRIPT = Path("scripts/g9_phase_b_report.py")
G9_SEALED_G8_STUDY_INDEX = Path("results/graphlog-certified/g8/study-index.json")


class G9PreflightError(ValueError):
    """The committed G9 preregistration or repository freeze is not executable."""


# G9 keeps the G6 phase enum, draw, and amendment shapes; only the document
# contracts around them change.  The study dataclass keeps G8's ``part``
# discriminator and adds the three preregistered digests that
# ``repository_preflight`` must verify against the working tree.
G9Phase = G6Phase
G9Draw = G6Draw
G9Amendment = G6Amendment


@dataclass(frozen=True, slots=True)
class G9Study:
    manifest_id: str
    manifest_path: Path
    part: str
    output_root: Path
    freeze_commit: str
    freeze_tree: str
    baseline_manifest_id: str
    spec_digest: str
    phases: tuple[G9Phase, ...]
    draws: tuple[G9Draw, ...]
    g5_runs: tuple[tuple[str, str], ...]
    phase_a_script_sha256: str
    phase_b_report_script_sha256: str
    sealed_g8_study_index_sha256: str


def _read_document(path: Path, label: str) -> dict[str, Any]:
    """Canonicalize a committed document, failing cleanly when absent."""
    if not path.is_file():
        raise G9PreflightError(f"{label} document is absent: {path}")
    try:
        return _canonical_document(path)
    except G6PreflightError as error:
        raise G9PreflightError(str(error)) from error
    except (OSError, ValueError) as error:
        raise G9PreflightError(f"{label} document is unreadable: {path}") from error


def _require_hex_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise G9PreflightError(
            f"G9 preregistration field {label} must be 64-char lowercase hex"
        )
    return value


def load_study_manifest(path: Path = G9_MANIFEST) -> G9Study:
    """Validate the committed G9 study definition without reading data."""
    document = _read_document(path, "G9 validation manifest")
    if document.get("schema_version") != G9_MANIFEST_SCHEMA:
        raise G9PreflightError("unsupported G9 validation manifest schema")
    part = document.get("part")
    if part not in G9_PARTS:
        raise G9PreflightError("G9 manifest declares an unknown part")
    if document.get("study_id") != G9_STUDY_IDS[part]:
        raise G9PreflightError("G9 manifest carries the wrong study id for its part")
    if document.get("preregistration_status") != G9_PREREGISTRATION_STATUS[part]:
        raise G9PreflightError("G9 manifest is not marked preregistered for its part")

    cohort = document.get("cohort", {})
    worlds = cohort.get("worlds")
    if not isinstance(worlds, list) or tuple(worlds) != VALIDATION_WORLDS:
        raise G9PreflightError("G9 cohort differs from the literal frozen tuple")
    if cohort.get("count") != len(worlds) or len(set(worlds)) != len(worlds):
        raise G9PreflightError("G9 cohort count or uniqueness mismatch")
    if document.get("analysis_order") != list(PHASE_ORDER):
        raise G9PreflightError("G9 phase order differs from preregistered order")

    protocol = document.get("data_protocol", {})
    if protocol.get("draws_per_world") != 1:
        raise G9PreflightError("G9 requires exactly one draw per world")
    output_root = Path(str(protocol.get("validation_output_root", "")))
    if output_root.is_absolute() or ".." in output_root.parts or not output_root.parts:
        raise G9PreflightError("G9 output root must be a non-empty repository path")
    if output_root != G9_OUTPUT_ROOTS[part]:
        raise G9PreflightError("G9 output root does not match the declared part")

    provenance = document.get("draw_provenance", {})
    disclosure = provenance.get("float_slack_status")
    if not isinstance(disclosure, str) or not disclosure:
        raise G9PreflightError(
            "G9 manifest must disclose the heuristic float-slack status"
        )
    # The single G9 part mints a fresh master seed committed before any G9
    # computation touches it; nothing is observed.
    if provenance.get("fresh_master_seed") is not True:
        raise G9PreflightError("G9 manifest must mint a fresh master seed")
    if provenance.get("g9_outcomes_observed") is not False:
        raise G9PreflightError("G9 manifest must attest zero observed G9 outcomes")

    seed = document.get("seed", {})
    master_hex = seed.get("master_seed_hex")
    if not isinstance(master_hex, str) or len(master_hex) != 64:
        raise G9PreflightError("G9 master seed must be 32-byte lowercase hex")
    try:
        master = bytes.fromhex(master_hex)
    except ValueError as error:
        raise G9PreflightError("G9 master seed is not hexadecimal") from error
    if master.hex() != master_hex:
        raise G9PreflightError("G9 master seed must use lowercase hex")
    derivation = seed.get("derivation", {})
    expected_derivation = {
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
    }
    if derivation != expected_derivation:
        raise G9PreflightError("G9 seed derivation metadata changed")
    rows = seed.get("expansions")
    if not isinstance(rows, list) or len(rows) != len(worlds):
        raise G9PreflightError("G9 expansion table is incomplete")
    draws = []
    for ordinal, (world, row) in enumerate(zip(worlds, rows, strict=True)):
        if not isinstance(row, dict) or row.get("world") != world:
            raise G9PreflightError("G9 expansion order differs from cohort order")
        digest = hashlib.sha256(master + world.encode("utf-8")).digest()
        digest_hex = digest.hex()
        seed_decimal = str(int.from_bytes(digest, "big"))
        if row.get("sha256_hex") != digest_hex \
                or row.get("draw_seed_uint256") != seed_decimal:
            raise G9PreflightError(f"G9 seed expansion mismatch for {world}")
        draws.append(G9Draw(ordinal, world, digest_hex, int(seed_decimal)))
    if seed.get("unique_expansion_count") != len({d.seed_sha256 for d in draws}):
        raise G9PreflightError("G9 expansion uniqueness declaration mismatch")

    freeze = document.get("freeze", {})
    if freeze.get("spec_digest") != DEFAULT_SPEC.digest:
        raise G9PreflightError("G9 manifest references a different frozen spec")
    for key in ("g0_g5_commit", "g0_g5_tree"):
        value = freeze.get(key)
        if not isinstance(value, str) or len(value) != 40:
            raise G9PreflightError(f"G9 freeze field {key} is malformed")
    baseline_id = freeze.get("baseline_manifest_id")
    if not isinstance(baseline_id, str) or not baseline_id.startswith("sha256:"):
        raise G9PreflightError("G9 baseline manifest id is malformed")
    g5_rows = freeze.get("g5_runs")
    if not isinstance(g5_rows, list) or not g5_rows:
        raise G9PreflightError("G9 freeze has no G5 run records")
    g5_runs = []
    for row in g5_rows:
        if not isinstance(row, dict) or set(row) != {"run_id", "seed", "world"}:
            raise G9PreflightError("G9 freeze has a malformed G5 run record")
        run_id = row["run_id"]
        world = row["world"]
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{64}", run_id) \
                or not isinstance(world, str) or not world \
                or row["seed"] != 0:
            raise G9PreflightError("G9 freeze has an invalid G5 run identity")
        g5_runs.append((run_id, world))
    if len({run_id for run_id, _world in g5_runs}) != len(g5_runs) \
            or len({world for _run_id, world in g5_runs}) != len(g5_runs):
        raise G9PreflightError("G9 freeze repeats a G5 run record")
    if set(document.get("acceptance_rules", {})) != G9_ACCEPTANCE_RULES:
        raise G9PreflightError("G9 acceptance rules are incomplete or changed")

    # The G9 preregistration section pins the sealed Phase A layer, the
    # pre-committed Phase B report script, the sealed G8 study index (the
    # plan §6 ordering witness), and the frozen predictor/claim literals.
    # Digest shapes and literals are checked here; the on-disk file digests
    # are verified at ``repository_preflight`` time, not load time.
    preregistration = document.get("g9_preregistration")
    if not isinstance(preregistration, dict) \
            or set(preregistration) != G9_PREREGISTRATION_KEYS:
        raise G9PreflightError(
            "G9 preregistration section is missing or has the wrong keys"
        )
    phase_a_script_sha256 = _require_hex_digest(
        preregistration["phase_a_script_sha256"], "phase_a_script_sha256",
    )
    phase_b_report_script_sha256 = _require_hex_digest(
        preregistration["phase_b_report_script_sha256"],
        "phase_b_report_script_sha256",
    )
    outputs = preregistration["phase_a_output_sha256"]
    if not isinstance(outputs, dict) or set(outputs) != {"round1", "round2"}:
        raise G9PreflightError(
            "G9 phase_a_output_sha256 must pin exactly round1 and round2"
        )
    for round_name in ("round1", "round2"):
        _require_hex_digest(
            outputs[round_name], f"phase_a_output_sha256.{round_name}",
        )
    sealed_g8_study_index_sha256 = _require_hex_digest(
        preregistration["sealed_g8_study_index_sha256"],
        "sealed_g8_study_index_sha256",
    )
    if preregistration["predictor"] != G9_PREDICTOR_LITERAL:
        raise G9PreflightError(
            "G9 predictor declaration differs from the frozen literal"
        )
    if preregistration["claim_4"] != G9_CLAIM_4_LITERAL:
        raise G9PreflightError(
            "G9 claim_4 declaration differs from the frozen literal"
        )
    if preregistration["claim_5"] != G9_CLAIM_5_LITERAL:
        raise G9PreflightError(
            "G9 claim_5 declaration differs from the frozen literal"
        )
    if preregistration["non_vacuity"] != G9_NON_VACUITY_LITERAL:
        raise G9PreflightError(
            "G9 non_vacuity declaration differs from the frozen literal"
        )

    return G9Study(
        manifest_id=document["manifest_id"],
        manifest_path=path,
        part=part,
        output_root=output_root,
        freeze_commit=freeze["g0_g5_commit"],
        freeze_tree=freeze["g0_g5_tree"],
        baseline_manifest_id=baseline_id,
        spec_digest=freeze["spec_digest"],
        phases=tuple(G9Phase(phase) for phase in PHASE_ORDER),
        draws=tuple(draws),
        g5_runs=tuple(g5_runs),
        phase_a_script_sha256=phase_a_script_sha256,
        phase_b_report_script_sha256=phase_b_report_script_sha256,
        sealed_g8_study_index_sha256=sealed_g8_study_index_sha256,
    )


def load_amendment(path: Path = G9_AMENDMENT) -> G9Amendment:
    document = _read_document(path, "G9 validation amendment")
    if document.get("schema_version") != G9_AMENDMENT_SCHEMA:
        raise G9PreflightError("unsupported G9 amendment schema")
    if document.get("change_scope") not in set(G9_CHANGE_SCOPES.values()):
        raise G9PreflightError("G9 amendment has an unauthorized change scope")
    # G9 attests zero observed outcomes on its fresh draws; the attestation
    # keeps G8's non-empty disclosure-string form (the manifest carries the
    # observation semantics) rather than G7's strict boolean-false.
    disclosure = document.get("g9_outcome_disclosure")
    if not isinstance(disclosure, str) or not disclosure:
        raise G9PreflightError("G9 amendment lacks the outcome-disclosure attestation")
    implementation = document.get("implementation_freeze", {})
    if implementation.get("harness_version") != G9_HARNESS_VERSION:
        raise G9PreflightError("G9 amendment harness version mismatch")
    files = implementation.get("files")
    if not isinstance(files, dict) or not files:
        raise G9PreflightError("G9 amendment has no implementation file freeze")
    if any(
        not isinstance(name, str)
        or Path(name).is_absolute()
        or ".." in Path(name).parts
        or not isinstance(digest, str)
        or len(digest) != 64
        for name, digest in files.items()
    ):
        raise G9PreflightError("G9 implementation file digest is malformed")
    execution = document.get("execution", {})
    enabled = execution.get("enabled")
    executor_file = execution.get("executor_file")
    executor_qualname = execution.get("executor_qualname")
    if not isinstance(enabled, bool):
        raise G9PreflightError("G9 execution-enabled flag is missing")
    commit = implementation.get("commit", "")
    tree = implementation.get("tree", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit) \
            or not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise G9PreflightError("G9 amendment must pin a real freeze commit and tree")
    if enabled:
        if executor_file not in files or not isinstance(executor_qualname, str) \
                or not executor_qualname:
            raise G9PreflightError("enabled G9 amendment lacks a pinned executor")
    elif executor_file is not None or executor_qualname is not None:
        raise G9PreflightError("disabled G9 amendment must not name an executor")
    parent_id = document.get("parent_amendment_id")
    if parent_id is not None and (
        not isinstance(parent_id, str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", parent_id)
    ):
        raise G9PreflightError("G9 parent amendment id is malformed")
    return G9Amendment(
        manifest_id=document["manifest_id"],
        amendment_path=path,
        study_manifest_id=document.get("study_manifest_id", ""),
        parent_amendment_id=parent_id,
        harness_commit=commit,
        harness_tree=tree,
        implementation_files=tuple(sorted(files.items())),
        execution_enabled=enabled,
        executor_file=executor_file,
        executor_qualname=executor_qualname,
    )


def load_amendment_chain(path: Path = G9_AMENDMENT) -> tuple[G9Amendment, ...]:
    """Load contiguous append-only amendments and verify every parent link."""
    pattern = re.compile(
        rf"{re.escape(path.stem)}(?:-(\d+))?{re.escape(path.suffix)}"
    )
    indexed = {}
    for candidate in path.parent.glob(f"{path.stem}*{path.suffix}"):
        match = pattern.fullmatch(candidate.name)
        if match:
            index = 1 if match.group(1) is None else int(match.group(1))
            if index in indexed:
                raise G9PreflightError("duplicate G9 amendment sequence number")
            indexed[index] = candidate
    if not indexed or 1 not in indexed:
        raise G9PreflightError("base G9 amendment is missing")
    expected = set(range(1, max(indexed) + 1))
    if set(indexed) != expected:
        raise G9PreflightError("G9 amendment chain has a numbering gap")
    amendments = tuple(load_amendment(indexed[index]) for index in sorted(indexed))
    if amendments[0].parent_amendment_id is not None:
        raise G9PreflightError("base G9 amendment unexpectedly has a parent")
    for previous, current in zip(amendments, amendments[1:]):
        if current.parent_amendment_id != previous.manifest_id:
            raise G9PreflightError("G9 amendment parent link mismatch")
        if current.study_manifest_id != previous.study_manifest_id:
            raise G9PreflightError("G9 amendment chain changes the study manifest")
    return amendments


def _verify_preregistered_digests(study: G9Study, *, root: Path) -> None:
    """Verify the preregistered script and ordering-witness digests on disk.

    The sealed G8 study index path may be a symlink into the archive; the
    digest is computed reading through it.
    """
    pinned = (
        (G9_PHASE_A_SCRIPT, study.phase_a_script_sha256,
         "G9 Phase A analysis script"),
        (G9_PHASE_B_REPORT_SCRIPT, study.phase_b_report_script_sha256,
         "G9 Phase B report script"),
        (G9_SEALED_G8_STUDY_INDEX, study.sealed_g8_study_index_sha256,
         "sealed G8 study index"),
    )
    for relative, expected, label in pinned:
        path = root / relative
        if not path.is_file():
            raise G9PreflightError(f"{label} is absent: {relative}")
        if _sha256_file(path) != expected:
            raise G9PreflightError(
                f"{label} digest differs from the preregistered value: {relative}"
            )


def repository_preflight(
    study: G9Study,
    amendment: G9Amendment,
    *,
    root: Path,
    require_clean: bool = True,
) -> None:
    """Verify both freezes and refuse any pre-existing G9 execution state."""
    study_path = study.manifest_path if study.manifest_path.is_absolute() \
        else root / study.manifest_path
    amendment_path = amendment.amendment_path \
        if amendment.amendment_path.is_absolute() else root / amendment.amendment_path
    if load_study_manifest(study_path) != study:
        raise G9PreflightError("in-memory G9 study differs from its manifest")
    if load_amendment(amendment_path) != amendment:
        raise G9PreflightError("in-memory G9 amendment differs from its manifest")
    if amendment.study_manifest_id != study.manifest_id:
        raise G9PreflightError("G9 amendment references a different study")
    if len(amendment.harness_commit) != 40 or len(amendment.harness_tree) != 40:
        raise G9PreflightError("G9 harness commit or tree is malformed")
    if _git(root, "rev-parse", f"{study.freeze_commit}^{{tree}}") \
            != study.freeze_tree:
        raise G9PreflightError("G0-G5 freeze tree mismatch")
    if _git(root, "rev-parse", f"{amendment.harness_commit}^{{tree}}") \
            != amendment.harness_tree:
        raise G9PreflightError("G9 harness freeze tree mismatch")
    frozen_ancestor = subprocess.run(
        (
            "git", "merge-base", "--is-ancestor",
            study.freeze_commit, amendment.harness_commit,
        ),
        cwd=root,
    )
    if frozen_ancestor.returncode != 0:
        raise G9PreflightError("G9 harness does not descend from G0-G5 freeze")
    ancestor = subprocess.run(
        ("git", "merge-base", "--is-ancestor", amendment.harness_commit, "HEAD"),
        cwd=root,
    )
    if ancestor.returncode != 0:
        raise G9PreflightError("current HEAD does not descend from G9 harness freeze")
    if require_clean and _git(root, "status", "--porcelain"):
        raise G9PreflightError("G9 execution requires a clean worktree")
    try:
        manifest_relative = str(study_path.resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G9PreflightError("G9 study manifest is outside the repository") from error
    try:
        frozen_manifest = subprocess.run(
            ("git", "show", f"{amendment.harness_commit}:{manifest_relative}"),
            cwd=root, check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise G9PreflightError("G9 study manifest is absent from harness commit") \
            from error
    if hashlib.sha256(frozen_manifest).hexdigest() != _sha256_file(study_path):
        raise G9PreflightError("G9 harness commit predates or changes the study manifest")
    for relative, expected in amendment.implementation_files:
        path = root / relative
        if not path.is_file() or _sha256_file(path) != expected:
            raise G9PreflightError(f"G9 implementation file drift: {relative}")
        try:
            frozen = subprocess.run(
                ("git", "show", f"{amendment.harness_commit}:{relative}"),
                cwd=root, check=True, capture_output=True,
            ).stdout
        except subprocess.CalledProcessError as error:
            raise G9PreflightError(
                f"G9 implementation file absent from commit: {relative}"
            ) from error
        if hashlib.sha256(frozen).hexdigest() != expected:
            raise G9PreflightError(f"G9 implementation commit mismatch: {relative}")

    _verify_preregistered_digests(study, root=root)

    baseline_path = root / DEFAULT_MANIFEST
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    validate_manifest(baseline, root, verify_data=True)
    if baseline.get("manifest_id") != study.baseline_manifest_id:
        raise G9PreflightError("G9 baseline manifest drift")
    for run_id, world in study.g5_runs:
        directory = root / "results/graphlog-certified" / run_id
        _validate_frozen_g5_directory(
            directory,
            expected_world=world,
            baseline_manifest_id=study.baseline_manifest_id,
        )

    output = root / study.output_root
    staging = output.with_name(f".{output.name}.{study.manifest_id[7:19]}.partial")
    if output.exists() or staging.exists():
        raise G9PreflightError("G9 output or partial state already exists; rerun refused")


def _validate_receipt(
    receipt: Mapping[str, Any], phase: G9Phase, draw: G9Draw,
) -> dict[str, Any]:
    value = canonical_data(receipt)
    if not isinstance(value, dict):
        raise ValueError("G9 phase receipt must be a mapping")
    required = {
        "schema_version", "phase", "world", "seed_sha256", "status",
        "artifact_records",
    }
    if set(value) != required:
        raise ValueError("G9 phase receipt fields differ from the frozen contract")
    if value["schema_version"] != G9_RECEIPT_SCHEMA:
        raise ValueError("unsupported G9 phase receipt schema")
    if value["phase"] != phase.value or value["world"] != draw.world \
            or value["seed_sha256"] != draw.seed_sha256:
        raise ValueError("G9 phase receipt identity mismatch")
    if value["status"] not in ("PASS", "REPORTED_FAILURE"):
        raise ValueError("G9 phase receipt has an invalid status")
    records = value["artifact_records"]
    if not isinstance(records, list) or not records:
        raise ValueError("G9 phase receipt must name at least one artifact")
    names = [row.get("name") for row in records if isinstance(row, dict)]
    if len(names) != len(records) or len(set(names)) != len(names):
        raise ValueError("G9 phase receipt artifact names are malformed")
    return value


def _validate_unit_directory(
    unit: Path,
    phase: G9Phase,
    draw: G9Draw,
    expected_receipt_sha256: str,
) -> None:
    entries = tuple(unit.iterdir())
    if any(not path.is_file() for path in entries):
        raise ValueError("G9 phase output may contain only regular files")
    receipt_path = unit / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError("G9 phase receipt is missing")
    if _sha256_file(receipt_path) != expected_receipt_sha256:
        raise ValueError("G9 phase receipt changed after harness creation")
    receipt = _validate_receipt(
        json.loads(receipt_path.read_text(encoding="utf-8")), phase, draw,
    )
    declared = {row["name"]: row for row in receipt["artifact_records"]}
    actual = {
        path.name: {
            "name": path.name,
            "byte_size": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in entries
        if path.name != "receipt.json"
    }
    if actual != declared:
        raise ValueError("G9 phase artifact records do not match output")


def execute_study(
    study: G9Study,
    amendment: G9Amendment,
    executor: PhaseExecutor,
    *,
    root: Path,
    verify_repository: bool = True,
) -> Path:
    """Execute one immutable block; interrupted or existing blocks never rerun."""
    if not amendment.execution_enabled:
        raise G9PreflightError("G9 execution is disabled pending a pinned adapter")
    if amendment.executor_qualname != G9_EXECUTOR_QUALNAMES.get(study.part):
        raise G9PreflightError(
            "G9 executor adapter does not match the study part; each part may "
            "only run under its own status-vocabulary adapter"
        )
    if verify_repository:
        repository_preflight(study, amendment, root=root)
    module = inspect.getmodule(executor)
    source = inspect.getsourcefile(executor)
    if module is None or source is None:
        raise G9PreflightError("G9 executor has no inspectable source module")
    try:
        relative = str(Path(source).resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G9PreflightError("G9 executor source is outside the repository") from error
    qualname = getattr(executor, "__qualname__", type(executor).__qualname__)
    if relative != amendment.executor_file or qualname != amendment.executor_qualname:
        raise G9PreflightError("G9 executor differs from the pinned adapter")
    output = root / study.output_root
    staging = output.with_name(f".{output.name}.{study.manifest_id[7:19]}.partial")
    if output.exists() or staging.exists():
        raise G9PreflightError("G9 output or partial state already exists; rerun refused")
    staging.mkdir(parents=True)
    index = {
        "schema_version": "graphlog-certified-g9-study-index/v1",
        "harness_version": G9_HARNESS_VERSION,
        "part": study.part,
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "phase_order": tuple(phase.value for phase in study.phases),
        "world_order": tuple(draw.world for draw in study.draws),
        "completed_phases": [],
    }
    (staging / "study-index.json").write_bytes(canonical_bytes(index) + b"\n")
    receipt_digests: dict[tuple[G9Phase, int], str] = {}

    for phase_index, phase in enumerate(study.phases):
        if phase is G9Phase.ACCURACY and phase_index != len(study.phases) - 1:
            raise RuntimeError("accuracy must be the final G9 phase")
        for draw in study.draws:
            prior = {
                prior_phase: _unit_directory(staging, prior_phase, draw)
                for prior_phase in study.phases[:phase_index]
            }
            if set(prior) != set(study.phases[:phase_index]):
                raise RuntimeError("G9 phase barrier is incomplete")
            for prior_phase, directory in prior.items():
                _validate_unit_directory(
                    directory, prior_phase, draw,
                    receipt_digests[(prior_phase, draw.ordinal)],
                )
            unit = _unit_directory(staging, phase, draw)
            unit.mkdir(parents=True)
            receipt = _validate_receipt(
                executor(phase, draw, prior, unit), phase, draw,
            )
            receipt_bytes = canonical_bytes(receipt) + b"\n"
            (unit / "receipt.json").write_bytes(receipt_bytes)
            receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
            receipt_digests[(phase, draw.ordinal)] = receipt_digest
            _validate_unit_directory(unit, phase, draw, receipt_digest)
            for prior_phase, directory in prior.items():
                _validate_unit_directory(
                    directory, prior_phase, draw,
                    receipt_digests[(prior_phase, draw.ordinal)],
                )
        index["completed_phases"].append(phase.value)
        (staging / "study-index.json").write_bytes(canonical_bytes(index) + b"\n")

    for phase in study.phases:
        for draw in study.draws:
            _validate_unit_directory(
                _unit_directory(staging, phase, draw), phase, draw,
                receipt_digests[(phase, draw.ordinal)],
            )
    staging.rename(output)
    return output


def preflight(
    *,
    root: Path,
    manifest_path: Path = G9_MANIFEST,
    amendment_path: Path = G9_AMENDMENT,
) -> G9Study:
    study = load_study_manifest(root / manifest_path)
    amendment = load_amendment_chain(root / amendment_path)[-1]
    repository_preflight(study, amendment, root=root)
    return study


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=G9_MANIFEST)
    parser.add_argument("--amendment", type=Path, default=G9_AMENDMENT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    study = preflight(
        root=root, manifest_path=args.manifest, amendment_path=args.amendment,
    )
    amendment = load_amendment_chain(root / args.amendment)[-1]
    print(json.dumps({
        "status": (
            "READY" if amendment.execution_enabled
            else "CONTROL_READY_EXECUTION_DISABLED"
        ),
        "part": study.part,
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "execution_enabled": amendment.execution_enabled,
        "worlds": len(study.draws),
        "phases": [phase.value for phase in study.phases],
    }, indent=2))


if __name__ == "__main__":
    main()
