"""Manifest-locked, premise-first orchestration for GraphLog G8.

G8 is the two-part successor to the sealed G7 block.  It changes exactly one
inequality in the certified mathematics (the localized bound keeps the exact
interior contraction instead of relaxing it with Cauchy--Schwarz) and is
otherwise pinned to the G7/G6 base layers.  Because the tight bound equals
the true error to solver tolerance, its outcome on the reused G7 draws is
already computed to the float; the study therefore splits into two manifests
run through this one harness:

* **Part I -- verification** (``part == "g8-verification"``): the reused G7
  draws, with outcomes disclosed as precomputed.  Replication value only.
* **Part II -- test** (``part == "g8"``): fresh draws, outcomes unobserved --
  the real preregistered test, predicting only at the mechanism level.

The two parts differ only in their ``part`` discriminator, their output
root, their draw provenance, and their amendment change scope; the cohort,
phase order, seed derivation, and G0--G5 freeze are shared.  Like the G6/G7
control planes this module lives outside ``bench.graphlog_certified`` so the
frozen G0--G5 source digest is unchanged, imports no dataset loader during
preflight, and creates no output until an execution-enabling amendment names
a pinned adapter.

The G8 manifest and amendment files do not exist yet -- authoring them is a
separate human-gated governance step -- so every loader fails cleanly with a
``G8PreflightError`` when its document is absent, rather than leaking a raw
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
from .graphlog_g7 import (
    G7_MANIFEST,
    load_study_manifest as _load_g7_study_manifest,
)


G8_MANIFEST = Path("results/graphlog-certified/g8-validation-manifest.json")
G8_AMENDMENT = Path("results/graphlog-certified/g8-validation-amendment.json")
G8_MANIFEST_SCHEMA = "graphlog-certified-g8-validation-manifest/v1"
G8_AMENDMENT_SCHEMA = "graphlog-certified-g8-validation-amendment/v1"
G8_HARNESS_VERSION = "graphlog-certified-g8-harness/v1"
G8_RECEIPT_SCHEMA = "graphlog-certified-g8-receipt/v1"
PHASE_ORDER = ("structural", "T5", "T6", "T7_safety", "accuracy")

# Two-part design: one harness, two manifests distinguished by ``part``.  The
# manifest's declared ``part`` selects the output root, study id, change
# scope, and provenance shape; everything else is shared.
G8_PART_VERIFICATION = "g8-verification"
G8_PART_TEST = "g8"
G8_PARTS = (G8_PART_VERIFICATION, G8_PART_TEST)
G8_OUTPUT_ROOTS = {
    G8_PART_VERIFICATION: Path("results/graphlog-certified/g8-verification"),
    G8_PART_TEST: Path("results/graphlog-certified/g8"),
}
G8_STUDY_IDS = {
    G8_PART_VERIFICATION: "graphlog-certified-g8-verification-precomputed/v1",
    G8_PART_TEST: "graphlog-certified-g8-interior-decisiveness/v1",
}
G8_PREREGISTRATION_STATUS = {
    G8_PART_VERIFICATION: (
        "committed_with_bound_replacement_outcome_precomputed_on_reused_draws"
    ),
    G8_PART_TEST: "committed_before_g8_part2_draw_generation_or_scoring",
}
G8_CHANGE_SCOPES = {
    G8_PART_VERIFICATION: "bound_replacement_outcome_precomputed_on_reused_draws",
    G8_PART_TEST: "exact_contraction_interior_decisiveness_fresh_draws",
}
G8_ACCEPTANCE_RULES = {
    "tight_bound_soundness",
    "tight_bound_tightness",
    "conditional_layer_unchanged",
    "certificate_soundness",
    "no_regression",
}
# Part identity is threaded to the phase adapter through the pinned executor
# qualname: each part may only run under its own adapter, so a sealed Part I
# block carries the precomputed-verification status vocabulary (plan §4) by
# mechanism, not convention.  ``execute_study`` enforces this pairing before
# any output is created.
G8_EXECUTOR_QUALNAMES = {
    G8_PART_VERIFICATION: "execute_phase_verification",
    G8_PART_TEST: "execute_phase_test",
}


class G8PreflightError(ValueError):
    """The committed G8 preregistration or repository freeze is not executable."""


# G8 keeps the G6 phase enum, draw, and amendment shapes; only the document
# contracts around them change.  The study dataclass gains a ``part`` field
# (the two-part discriminator) but is otherwise parallel to G6/G7's.
G8Phase = G6Phase
G8Draw = G6Draw
G8Amendment = G6Amendment


@dataclass(frozen=True, slots=True)
class G8Study:
    manifest_id: str
    manifest_path: Path
    part: str
    output_root: Path
    freeze_commit: str
    freeze_tree: str
    baseline_manifest_id: str
    spec_digest: str
    phases: tuple[G8Phase, ...]
    draws: tuple[G8Draw, ...]
    g5_runs: tuple[tuple[str, str], ...]


def _read_document(path: Path, label: str) -> dict[str, Any]:
    """Canonicalize a committed document, failing cleanly when absent."""
    if not path.is_file():
        raise G8PreflightError(f"{label} document is absent: {path}")
    try:
        return _canonical_document(path)
    except G6PreflightError as error:
        raise G8PreflightError(str(error)) from error
    except (OSError, ValueError) as error:
        raise G8PreflightError(f"{label} document is unreadable: {path}") from error


def load_study_manifest(path: Path = G8_MANIFEST) -> G8Study:
    """Validate a committed G8 study definition without reading data.

    Works for either part; the manifest's ``part`` field selects the study
    id, preregistration status, output root, and draw-provenance shape.
    """
    document = _read_document(path, "G8 validation manifest")
    if document.get("schema_version") != G8_MANIFEST_SCHEMA:
        raise G8PreflightError("unsupported G8 validation manifest schema")
    part = document.get("part")
    if part not in G8_PARTS:
        raise G8PreflightError("G8 manifest declares an unknown part")
    if document.get("study_id") != G8_STUDY_IDS[part]:
        raise G8PreflightError("G8 manifest carries the wrong study id for its part")
    if document.get("preregistration_status") != G8_PREREGISTRATION_STATUS[part]:
        raise G8PreflightError("G8 manifest is not marked preregistered for its part")

    cohort = document.get("cohort", {})
    worlds = cohort.get("worlds")
    if not isinstance(worlds, list) or tuple(worlds) != VALIDATION_WORLDS:
        raise G8PreflightError("G8 cohort differs from the literal frozen tuple")
    if cohort.get("count") != len(worlds) or len(set(worlds)) != len(worlds):
        raise G8PreflightError("G8 cohort count or uniqueness mismatch")
    if document.get("analysis_order") != list(PHASE_ORDER):
        raise G8PreflightError("G8 phase order differs from preregistered order")

    protocol = document.get("data_protocol", {})
    if protocol.get("draws_per_world") != 1:
        raise G8PreflightError("G8 requires exactly one draw per world")
    output_root = Path(str(protocol.get("validation_output_root", "")))
    if output_root.is_absolute() or ".." in output_root.parts or not output_root.parts:
        raise G8PreflightError("G8 output root must be a non-empty repository path")
    if output_root != G8_OUTPUT_ROOTS[part]:
        raise G8PreflightError("G8 output root does not match the declared part")

    provenance = document.get("draw_provenance", {})
    disclosure = provenance.get("float_slack_status")
    if not isinstance(disclosure, str) or not disclosure:
        raise G8PreflightError(
            "G8 manifest must disclose the heuristic float-slack status"
        )
    if part == G8_PART_VERIFICATION:
        # Part I reuses the sealed G7 draws AND declares its own outcome
        # precomputed; it cannot and does not assert unobserved outputs.
        reused_from = provenance.get("reused_from_study")
        if not isinstance(reused_from, str) \
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", reused_from):
            raise G8PreflightError("G8 Part I provenance must name the source study")
        if provenance.get("g7_outcomes_observed") is not True:
            raise G8PreflightError(
                "G8 Part I manifest must disclose that G7 outcomes were observed"
            )
        if provenance.get("part1_outcome_precomputed") is not True:
            raise G8PreflightError(
                "G8 Part I manifest must disclose the precomputed outcome"
            )
    else:
        # Part II mints a fresh master seed committed before any Part II
        # computation touches it; nothing is observed.
        if provenance.get("fresh_master_seed") is not True:
            raise G8PreflightError(
                "G8 Part II manifest must mint a fresh master seed"
            )
        if provenance.get("g8_part2_outcomes_observed") is not False:
            raise G8PreflightError(
                "G8 Part II manifest must attest zero observed Part II outcomes"
            )

    seed = document.get("seed", {})
    master_hex = seed.get("master_seed_hex")
    if not isinstance(master_hex, str) or len(master_hex) != 64:
        raise G8PreflightError("G8 master seed must be 32-byte lowercase hex")
    try:
        master = bytes.fromhex(master_hex)
    except ValueError as error:
        raise G8PreflightError("G8 master seed is not hexadecimal") from error
    if master.hex() != master_hex:
        raise G8PreflightError("G8 master seed must use lowercase hex")
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
        raise G8PreflightError("G8 seed derivation metadata changed")
    rows = seed.get("expansions")
    if not isinstance(rows, list) or len(rows) != len(worlds):
        raise G8PreflightError("G8 expansion table is incomplete")
    draws = []
    for ordinal, (world, row) in enumerate(zip(worlds, rows, strict=True)):
        if not isinstance(row, dict) or row.get("world") != world:
            raise G8PreflightError("G8 expansion order differs from cohort order")
        digest = hashlib.sha256(master + world.encode("utf-8")).digest()
        digest_hex = digest.hex()
        seed_decimal = str(int.from_bytes(digest, "big"))
        if row.get("sha256_hex") != digest_hex \
                or row.get("draw_seed_uint256") != seed_decimal:
            raise G8PreflightError(f"G8 seed expansion mismatch for {world}")
        draws.append(G8Draw(ordinal, world, digest_hex, int(seed_decimal)))
    if seed.get("unique_expansion_count") != len({d.seed_sha256 for d in draws}):
        raise G8PreflightError("G8 expansion uniqueness declaration mismatch")

    freeze = document.get("freeze", {})
    if freeze.get("spec_digest") != DEFAULT_SPEC.digest:
        raise G8PreflightError("G8 manifest references a different frozen spec")
    for key in ("g0_g5_commit", "g0_g5_tree"):
        value = freeze.get(key)
        if not isinstance(value, str) or len(value) != 40:
            raise G8PreflightError(f"G8 freeze field {key} is malformed")
    baseline_id = freeze.get("baseline_manifest_id")
    if not isinstance(baseline_id, str) or not baseline_id.startswith("sha256:"):
        raise G8PreflightError("G8 baseline manifest id is malformed")
    g5_rows = freeze.get("g5_runs")
    if not isinstance(g5_rows, list) or not g5_rows:
        raise G8PreflightError("G8 freeze has no G5 run records")
    g5_runs = []
    for row in g5_rows:
        if not isinstance(row, dict) or set(row) != {"run_id", "seed", "world"}:
            raise G8PreflightError("G8 freeze has a malformed G5 run record")
        run_id = row["run_id"]
        world = row["world"]
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{64}", run_id) \
                or not isinstance(world, str) or not world \
                or row["seed"] != 0:
            raise G8PreflightError("G8 freeze has an invalid G5 run identity")
        g5_runs.append((run_id, world))
    if len({run_id for run_id, _world in g5_runs}) != len(g5_runs) \
            or len({world for _run_id, world in g5_runs}) != len(g5_runs):
        raise G8PreflightError("G8 freeze repeats a G5 run record")
    if set(document.get("acceptance_rules", {})) != G8_ACCEPTANCE_RULES:
        raise G8PreflightError("G8 acceptance rules are incomplete or changed")

    # Part I's reuse claim is executable: the sibling G7 manifest is loaded and
    # its study id and derived draws must match exactly.  Part II mints fresh
    # draws and carries no such cross-check.
    if part == G8_PART_VERIFICATION:
        g7_study = _load_g7_study_manifest(path.parent / Path(G7_MANIFEST).name)
        if provenance.get("reused_from_study") != g7_study.manifest_id:
            raise G8PreflightError(
                "G8 Part I provenance does not name the sealed G7 study"
            )
        if tuple(draws) != g7_study.draws:
            raise G8PreflightError("G8 Part I draws differ from the reused G7 draws")
        if (
            freeze["g0_g5_commit"] != g7_study.freeze_commit
            or freeze["g0_g5_tree"] != g7_study.freeze_tree
            or baseline_id != g7_study.baseline_manifest_id
            or freeze["spec_digest"] != g7_study.spec_digest
        ):
            raise G8PreflightError("G8 Part I freeze identity differs from the G7 study")

    return G8Study(
        manifest_id=document["manifest_id"],
        manifest_path=path,
        part=part,
        output_root=output_root,
        freeze_commit=freeze["g0_g5_commit"],
        freeze_tree=freeze["g0_g5_tree"],
        baseline_manifest_id=baseline_id,
        spec_digest=freeze["spec_digest"],
        phases=tuple(G8Phase(phase) for phase in PHASE_ORDER),
        draws=tuple(draws),
        g5_runs=tuple(g5_runs),
    )


def load_amendment(path: Path = G8_AMENDMENT) -> G8Amendment:
    document = _read_document(path, "G8 validation amendment")
    if document.get("schema_version") != G8_AMENDMENT_SCHEMA:
        raise G8PreflightError("unsupported G8 amendment schema")
    if document.get("change_scope") not in set(G8_CHANGE_SCOPES.values()):
        raise G8PreflightError("G8 amendment has an unauthorized change scope")
    # Part I discloses its outcome precomputed while Part II attests zero
    # observation, so the attestation is a non-empty disclosure string rather
    # than G7's strict boolean-false; the manifest carries the observation
    # semantics per part.
    disclosure = document.get("g8_outcome_disclosure")
    if not isinstance(disclosure, str) or not disclosure:
        raise G8PreflightError("G8 amendment lacks the outcome-disclosure attestation")
    implementation = document.get("implementation_freeze", {})
    if implementation.get("harness_version") != G8_HARNESS_VERSION:
        raise G8PreflightError("G8 amendment harness version mismatch")
    files = implementation.get("files")
    if not isinstance(files, dict) or not files:
        raise G8PreflightError("G8 amendment has no implementation file freeze")
    if any(
        not isinstance(name, str)
        or Path(name).is_absolute()
        or ".." in Path(name).parts
        or not isinstance(digest, str)
        or len(digest) != 64
        for name, digest in files.items()
    ):
        raise G8PreflightError("G8 implementation file digest is malformed")
    execution = document.get("execution", {})
    enabled = execution.get("enabled")
    executor_file = execution.get("executor_file")
    executor_qualname = execution.get("executor_qualname")
    if not isinstance(enabled, bool):
        raise G8PreflightError("G8 execution-enabled flag is missing")
    commit = implementation.get("commit", "")
    tree = implementation.get("tree", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit) \
            or not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise G8PreflightError("G8 amendment must pin a real freeze commit and tree")
    if enabled:
        if executor_file not in files or not isinstance(executor_qualname, str) \
                or not executor_qualname:
            raise G8PreflightError("enabled G8 amendment lacks a pinned executor")
    elif executor_file is not None or executor_qualname is not None:
        raise G8PreflightError("disabled G8 amendment must not name an executor")
    parent_id = document.get("parent_amendment_id")
    if parent_id is not None and (
        not isinstance(parent_id, str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", parent_id)
    ):
        raise G8PreflightError("G8 parent amendment id is malformed")
    return G8Amendment(
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


def load_amendment_chain(path: Path = G8_AMENDMENT) -> tuple[G8Amendment, ...]:
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
                raise G8PreflightError("duplicate G8 amendment sequence number")
            indexed[index] = candidate
    if not indexed or 1 not in indexed:
        raise G8PreflightError("base G8 amendment is missing")
    expected = set(range(1, max(indexed) + 1))
    if set(indexed) != expected:
        raise G8PreflightError("G8 amendment chain has a numbering gap")
    amendments = tuple(load_amendment(indexed[index]) for index in sorted(indexed))
    if amendments[0].parent_amendment_id is not None:
        raise G8PreflightError("base G8 amendment unexpectedly has a parent")
    for previous, current in zip(amendments, amendments[1:]):
        if current.parent_amendment_id != previous.manifest_id:
            raise G8PreflightError("G8 amendment parent link mismatch")
        if current.study_manifest_id != previous.study_manifest_id:
            raise G8PreflightError("G8 amendment chain changes the study manifest")
    return amendments


def repository_preflight(
    study: G8Study,
    amendment: G8Amendment,
    *,
    root: Path,
    require_clean: bool = True,
) -> None:
    """Verify both freezes and refuse any pre-existing G8 execution state."""
    study_path = study.manifest_path if study.manifest_path.is_absolute() \
        else root / study.manifest_path
    amendment_path = amendment.amendment_path \
        if amendment.amendment_path.is_absolute() else root / amendment.amendment_path
    if load_study_manifest(study_path) != study:
        raise G8PreflightError("in-memory G8 study differs from its manifest")
    if load_amendment(amendment_path) != amendment:
        raise G8PreflightError("in-memory G8 amendment differs from its manifest")
    if amendment.study_manifest_id != study.manifest_id:
        raise G8PreflightError("G8 amendment references a different study")
    if len(amendment.harness_commit) != 40 or len(amendment.harness_tree) != 40:
        raise G8PreflightError("G8 harness commit or tree is malformed")
    if _git(root, "rev-parse", f"{study.freeze_commit}^{{tree}}") \
            != study.freeze_tree:
        raise G8PreflightError("G0-G5 freeze tree mismatch")
    if _git(root, "rev-parse", f"{amendment.harness_commit}^{{tree}}") \
            != amendment.harness_tree:
        raise G8PreflightError("G8 harness freeze tree mismatch")
    frozen_ancestor = subprocess.run(
        (
            "git", "merge-base", "--is-ancestor",
            study.freeze_commit, amendment.harness_commit,
        ),
        cwd=root,
    )
    if frozen_ancestor.returncode != 0:
        raise G8PreflightError("G8 harness does not descend from G0-G5 freeze")
    ancestor = subprocess.run(
        ("git", "merge-base", "--is-ancestor", amendment.harness_commit, "HEAD"),
        cwd=root,
    )
    if ancestor.returncode != 0:
        raise G8PreflightError("current HEAD does not descend from G8 harness freeze")
    if require_clean and _git(root, "status", "--porcelain"):
        raise G8PreflightError("G8 execution requires a clean worktree")
    try:
        manifest_relative = str(study_path.resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G8PreflightError("G8 study manifest is outside the repository") from error
    try:
        frozen_manifest = subprocess.run(
            ("git", "show", f"{amendment.harness_commit}:{manifest_relative}"),
            cwd=root, check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise G8PreflightError("G8 study manifest is absent from harness commit") \
            from error
    if hashlib.sha256(frozen_manifest).hexdigest() != _sha256_file(study_path):
        raise G8PreflightError("G8 harness commit predates or changes the study manifest")
    for relative, expected in amendment.implementation_files:
        path = root / relative
        if not path.is_file() or _sha256_file(path) != expected:
            raise G8PreflightError(f"G8 implementation file drift: {relative}")
        try:
            frozen = subprocess.run(
                ("git", "show", f"{amendment.harness_commit}:{relative}"),
                cwd=root, check=True, capture_output=True,
            ).stdout
        except subprocess.CalledProcessError as error:
            raise G8PreflightError(
                f"G8 implementation file absent from commit: {relative}"
            ) from error
        if hashlib.sha256(frozen).hexdigest() != expected:
            raise G8PreflightError(f"G8 implementation commit mismatch: {relative}")

    baseline_path = root / DEFAULT_MANIFEST
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    validate_manifest(baseline, root, verify_data=True)
    if baseline.get("manifest_id") != study.baseline_manifest_id:
        raise G8PreflightError("G8 baseline manifest drift")
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
        raise G8PreflightError("G8 output or partial state already exists; rerun refused")


def _validate_receipt(
    receipt: Mapping[str, Any], phase: G8Phase, draw: G8Draw,
) -> dict[str, Any]:
    value = canonical_data(receipt)
    if not isinstance(value, dict):
        raise ValueError("G8 phase receipt must be a mapping")
    required = {
        "schema_version", "phase", "world", "seed_sha256", "status",
        "artifact_records",
    }
    if set(value) != required:
        raise ValueError("G8 phase receipt fields differ from the frozen contract")
    if value["schema_version"] != G8_RECEIPT_SCHEMA:
        raise ValueError("unsupported G8 phase receipt schema")
    if value["phase"] != phase.value or value["world"] != draw.world \
            or value["seed_sha256"] != draw.seed_sha256:
        raise ValueError("G8 phase receipt identity mismatch")
    if value["status"] not in ("PASS", "REPORTED_FAILURE"):
        raise ValueError("G8 phase receipt has an invalid status")
    records = value["artifact_records"]
    if not isinstance(records, list) or not records:
        raise ValueError("G8 phase receipt must name at least one artifact")
    names = [row.get("name") for row in records if isinstance(row, dict)]
    if len(names) != len(records) or len(set(names)) != len(names):
        raise ValueError("G8 phase receipt artifact names are malformed")
    return value


def _validate_unit_directory(
    unit: Path,
    phase: G8Phase,
    draw: G8Draw,
    expected_receipt_sha256: str,
) -> None:
    entries = tuple(unit.iterdir())
    if any(not path.is_file() for path in entries):
        raise ValueError("G8 phase output may contain only regular files")
    receipt_path = unit / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError("G8 phase receipt is missing")
    if _sha256_file(receipt_path) != expected_receipt_sha256:
        raise ValueError("G8 phase receipt changed after harness creation")
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
        raise ValueError("G8 phase artifact records do not match output")


def execute_study(
    study: G8Study,
    amendment: G8Amendment,
    executor: PhaseExecutor,
    *,
    root: Path,
    verify_repository: bool = True,
) -> Path:
    """Execute one immutable block; interrupted or existing blocks never rerun."""
    if not amendment.execution_enabled:
        raise G8PreflightError("G8 execution is disabled pending a pinned adapter")
    if amendment.executor_qualname != G8_EXECUTOR_QUALNAMES.get(study.part):
        raise G8PreflightError(
            "G8 executor adapter does not match the study part; each part may "
            "only run under its own status-vocabulary adapter"
        )
    if verify_repository:
        repository_preflight(study, amendment, root=root)
    module = inspect.getmodule(executor)
    source = inspect.getsourcefile(executor)
    if module is None or source is None:
        raise G8PreflightError("G8 executor has no inspectable source module")
    try:
        relative = str(Path(source).resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G8PreflightError("G8 executor source is outside the repository") from error
    qualname = getattr(executor, "__qualname__", type(executor).__qualname__)
    if relative != amendment.executor_file or qualname != amendment.executor_qualname:
        raise G8PreflightError("G8 executor differs from the pinned adapter")
    output = root / study.output_root
    staging = output.with_name(f".{output.name}.{study.manifest_id[7:19]}.partial")
    if output.exists() or staging.exists():
        raise G8PreflightError("G8 output or partial state already exists; rerun refused")
    staging.mkdir(parents=True)
    index = {
        "schema_version": "graphlog-certified-g8-study-index/v1",
        "harness_version": G8_HARNESS_VERSION,
        "part": study.part,
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "phase_order": tuple(phase.value for phase in study.phases),
        "world_order": tuple(draw.world for draw in study.draws),
        "completed_phases": [],
    }
    (staging / "study-index.json").write_bytes(canonical_bytes(index) + b"\n")
    receipt_digests: dict[tuple[G8Phase, int], str] = {}

    for phase_index, phase in enumerate(study.phases):
        if phase is G8Phase.ACCURACY and phase_index != len(study.phases) - 1:
            raise RuntimeError("accuracy must be the final G8 phase")
        for draw in study.draws:
            prior = {
                prior_phase: _unit_directory(staging, prior_phase, draw)
                for prior_phase in study.phases[:phase_index]
            }
            if set(prior) != set(study.phases[:phase_index]):
                raise RuntimeError("G8 phase barrier is incomplete")
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
    manifest_path: Path = G8_MANIFEST,
    amendment_path: Path = G8_AMENDMENT,
) -> G8Study:
    study = load_study_manifest(root / manifest_path)
    amendment = load_amendment_chain(root / amendment_path)[-1]
    repository_preflight(study, amendment, root=root)
    return study


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=G8_MANIFEST)
    parser.add_argument("--amendment", type=Path, default=G8_AMENDMENT)
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
