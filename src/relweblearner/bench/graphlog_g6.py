"""Manifest-locked, premise-first orchestration for GraphLog G6.

This module is deliberately outside ``bench.graphlog_certified`` so adding the
G6 control plane does not alter the source digest of the frozen G0--G5 theorem
implementation.  Preflight imports no dataset loader and creates no output.
Actual phase computation is supplied as a reviewed ``PhaseExecutor`` adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from ..certification.types import canonical_bytes, canonical_data, canonical_digest
from .graphlog_certified.notarization import DEFAULT_MANIFEST, validate_manifest
from .graphlog_certified.spec import DEFAULT_SPEC, VALIDATION_WORLDS


G6_MANIFEST = Path("results/graphlog-certified/g6-validation-manifest.json")
G6_AMENDMENT = Path("results/graphlog-certified/g6-validation-amendment.json")
G6_MANIFEST_SCHEMA = "graphlog-certified-g6-validation-manifest/v1"
G6_AMENDMENT_SCHEMA = "graphlog-certified-g6-validation-amendment/v1"
G6_HARNESS_VERSION = "graphlog-certified-g6-harness/v1"
PHASE_ORDER = ("structural", "T5", "T6", "T7_safety", "accuracy")


class G6PreflightError(ValueError):
    """The committed preregistration or repository freeze is not executable."""


class G6Phase(str, Enum):
    STRUCTURAL = "structural"
    T5 = "T5"
    T6 = "T6"
    T7_SAFETY = "T7_safety"
    ACCURACY = "accuracy"


@dataclass(frozen=True, slots=True)
class G6Draw:
    ordinal: int
    world: str
    seed_sha256: str
    seed_uint256: int


@dataclass(frozen=True, slots=True)
class G6Study:
    manifest_id: str
    manifest_path: Path
    output_root: Path
    freeze_commit: str
    freeze_tree: str
    baseline_manifest_id: str
    spec_digest: str
    phases: tuple[G6Phase, ...]
    draws: tuple[G6Draw, ...]
    g5_runs: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class G6Amendment:
    manifest_id: str
    amendment_path: Path
    study_manifest_id: str
    parent_amendment_id: str | None
    harness_commit: str
    harness_tree: str
    implementation_files: tuple[tuple[str, str], ...]
    execution_enabled: bool
    executor_file: str | None
    executor_qualname: str | None


class PhaseExecutor(Protocol):
    """Reviewed computation adapter called once for each phase/world pair."""

    def __call__(
        self,
        phase: G6Phase,
        draw: G6Draw,
        prior_phase_directories: Mapping[G6Phase, Path],
        output_directory: Path,
    ) -> Mapping[str, Any]: ...


def _canonical_document(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    canonical_data(document)
    if not isinstance(document, dict):
        raise G6PreflightError(f"{path} must contain a JSON object")
    body = {key: value for key, value in document.items() if key != "manifest_id"}
    expected = f"sha256:{canonical_digest(body)}"
    if document.get("manifest_id") != expected:
        raise G6PreflightError(f"{path} manifest id mismatch")
    return document


def load_study_manifest(path: Path = G6_MANIFEST) -> G6Study:
    """Validate the committed study definition without reading GraphLog data."""
    document = _canonical_document(path)
    if document.get("schema_version") != G6_MANIFEST_SCHEMA:
        raise G6PreflightError("unsupported G6 validation manifest schema")
    if document.get("preregistration_status") \
            != "committed_before_draw_generation_or_scoring":
        raise G6PreflightError("G6 manifest is not marked preregistered")

    cohort = document.get("cohort", {})
    worlds = cohort.get("worlds")
    if not isinstance(worlds, list) or tuple(worlds) != VALIDATION_WORLDS:
        raise G6PreflightError("G6 cohort differs from the literal frozen tuple")
    if cohort.get("count") != len(worlds) or len(set(worlds)) != len(worlds):
        raise G6PreflightError("G6 cohort count or uniqueness mismatch")
    if document.get("analysis_order") != list(PHASE_ORDER):
        raise G6PreflightError("G6 phase order differs from preregistered order")

    protocol = document.get("data_protocol", {})
    if protocol.get("draws_per_world") != 1:
        raise G6PreflightError("G6 requires exactly one draw per world")
    if protocol.get("virgin_draws_generated_at_preregistration") != 0:
        raise G6PreflightError("G6 manifest claims pre-existing validation draws")
    output_root = Path(str(protocol.get("validation_output_root", "")))
    if output_root.is_absolute() or ".." in output_root.parts or not output_root.parts:
        raise G6PreflightError("G6 output root must be a non-empty repository path")

    seed = document.get("seed", {})
    master_hex = seed.get("master_seed_hex")
    if not isinstance(master_hex, str) or len(master_hex) != 64:
        raise G6PreflightError("G6 master seed must be 32-byte lowercase hex")
    try:
        master = bytes.fromhex(master_hex)
    except ValueError as error:
        raise G6PreflightError("G6 master seed is not hexadecimal") from error
    if master.hex() != master_hex:
        raise G6PreflightError("G6 master seed must use lowercase hex")

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
        raise G6PreflightError("G6 seed derivation metadata changed")

    rows = seed.get("expansions")
    if not isinstance(rows, list) or len(rows) != len(worlds):
        raise G6PreflightError("G6 expansion table is incomplete")
    draws = []
    for ordinal, (world, row) in enumerate(zip(worlds, rows, strict=True)):
        if not isinstance(row, dict) or row.get("world") != world:
            raise G6PreflightError("G6 expansion order differs from cohort order")
        digest = hashlib.sha256(master + world.encode("utf-8")).digest()
        digest_hex = digest.hex()
        seed_decimal = str(int.from_bytes(digest, "big"))
        if row.get("sha256_hex") != digest_hex \
                or row.get("draw_seed_uint256") != seed_decimal:
            raise G6PreflightError(f"G6 seed expansion mismatch for {world}")
        draws.append(G6Draw(ordinal, world, digest_hex, int(seed_decimal)))
    if seed.get("unique_expansion_count") != len({d.seed_sha256 for d in draws}):
        raise G6PreflightError("G6 expansion uniqueness declaration mismatch")

    freeze = document.get("freeze", {})
    if freeze.get("spec_digest") != DEFAULT_SPEC.digest:
        raise G6PreflightError("G6 manifest references a different frozen spec")
    for key in ("g0_g5_commit", "g0_g5_tree"):
        value = freeze.get(key)
        if not isinstance(value, str) or len(value) != 40:
            raise G6PreflightError(f"G6 freeze field {key} is malformed")
    baseline_id = freeze.get("baseline_manifest_id")
    if not isinstance(baseline_id, str) or not baseline_id.startswith("sha256:"):
        raise G6PreflightError("G6 baseline manifest id is malformed")
    if document.get("virginity_proof", {}).get("result") != "PASS_ZERO_MATCHES":
        raise G6PreflightError("G6 virginity proof did not pass")
    g5_rows = freeze.get("g5_runs")
    if not isinstance(g5_rows, list) or not g5_rows:
        raise G6PreflightError("G6 freeze has no G5 run records")
    g5_runs = []
    for row in g5_rows:
        if not isinstance(row, dict) or set(row) != {"run_id", "seed", "world"}:
            raise G6PreflightError("G6 freeze has a malformed G5 run record")
        run_id = row["run_id"]
        world = row["world"]
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{64}", run_id) \
                or not isinstance(world, str) or not world \
                or row["seed"] != 0:
            raise G6PreflightError("G6 freeze has an invalid G5 run identity")
        g5_runs.append((run_id, world))
    if len({run_id for run_id, _world in g5_runs}) != len(g5_runs) \
            or len({world for _run_id, world in g5_runs}) != len(g5_runs):
        raise G6PreflightError("G6 freeze repeats a G5 run record")
    required_acceptance = {
        "certificate_soundness", "non_vacuity", "primary_usefulness",
        "secondary_usefulness", "usefulness_claim_requires",
    }
    if set(document.get("acceptance_rules", {})) != required_acceptance:
        raise G6PreflightError("G6 acceptance rules are incomplete or changed")

    return G6Study(
        manifest_id=document["manifest_id"],
        manifest_path=path,
        output_root=output_root,
        freeze_commit=freeze["g0_g5_commit"],
        freeze_tree=freeze["g0_g5_tree"],
        baseline_manifest_id=baseline_id,
        spec_digest=freeze["spec_digest"],
        phases=tuple(G6Phase(phase) for phase in PHASE_ORDER),
        draws=tuple(draws),
        g5_runs=tuple(g5_runs),
    )


def load_amendment(path: Path = G6_AMENDMENT) -> G6Amendment:
    document = _canonical_document(path)
    if document.get("schema_version") != G6_AMENDMENT_SCHEMA:
        raise G6PreflightError("unsupported G6 amendment schema")
    if document.get("change_scope") != "implementation_only_no_draws_or_scores":
        raise G6PreflightError("G6 amendment has an unauthorized change scope")
    if document.get("validation_draws_or_scores_observed") is not False:
        raise G6PreflightError("G6 amendment does not attest zero observed outcomes")
    implementation = document.get("implementation_freeze", {})
    if implementation.get("harness_version") != G6_HARNESS_VERSION:
        raise G6PreflightError("G6 amendment harness version mismatch")
    files = implementation.get("files")
    if not isinstance(files, dict) or not files:
        raise G6PreflightError("G6 amendment has no implementation file freeze")
    if any(
        not isinstance(name, str)
        or Path(name).is_absolute()
        or ".." in Path(name).parts
        or not isinstance(digest, str)
        or len(digest) != 64
        for name, digest in files.items()
    ):
        raise G6PreflightError("G6 implementation file digest is malformed")
    execution = document.get("execution", {})
    enabled = execution.get("enabled")
    executor_file = execution.get("executor_file")
    executor_qualname = execution.get("executor_qualname")
    if not isinstance(enabled, bool):
        raise G6PreflightError("G6 execution-enabled flag is missing")
    if enabled:
        if executor_file not in files or not isinstance(executor_qualname, str) \
                or not executor_qualname:
            raise G6PreflightError("enabled G6 amendment lacks a pinned executor")
    elif executor_file is not None or executor_qualname is not None:
        raise G6PreflightError("disabled G6 amendment must not name an executor")
    parent_id = document.get("parent_amendment_id")
    if parent_id is not None and (
        not isinstance(parent_id, str)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", parent_id)
    ):
        raise G6PreflightError("G6 parent amendment id is malformed")
    return G6Amendment(
        manifest_id=document["manifest_id"],
        amendment_path=path,
        study_manifest_id=document.get("study_manifest_id", ""),
        parent_amendment_id=parent_id,
        harness_commit=implementation.get("commit", ""),
        harness_tree=implementation.get("tree", ""),
        implementation_files=tuple(sorted(files.items())),
        execution_enabled=enabled,
        executor_file=executor_file,
        executor_qualname=executor_qualname,
    )


def load_amendment_chain(path: Path = G6_AMENDMENT) -> tuple[G6Amendment, ...]:
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
                raise G6PreflightError("duplicate G6 amendment sequence number")
            indexed[index] = candidate
    if not indexed or 1 not in indexed:
        raise G6PreflightError("base G6 amendment is missing")
    expected = set(range(1, max(indexed) + 1))
    if set(indexed) != expected:
        raise G6PreflightError("G6 amendment chain has a numbering gap")
    amendments = tuple(load_amendment(indexed[index]) for index in sorted(indexed))
    if amendments[0].parent_amendment_id is not None:
        raise G6PreflightError("base G6 amendment unexpectedly has a parent")
    for previous, current in zip(amendments, amendments[1:]):
        if current.parent_amendment_id != previous.manifest_id:
            raise G6PreflightError("G6 amendment parent link mismatch")
        if current.study_manifest_id != previous.study_manifest_id:
            raise G6PreflightError("G6 amendment chain changes the study manifest")
    return amendments


def _git(root: Path, *args: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ("git", *args), cwd=root, check=check, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as error:
        raise G6PreflightError(
            f"git verification failed: {' '.join(args)}"
        ) from error
    return result.stdout.strip()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_frozen_g5_directory(
    directory: Path,
    *,
    expected_world: str,
    baseline_manifest_id: str,
) -> None:
    """Check immutable G5 content without importing its data-capable runner."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    canonical_data(manifest)
    body = {key: value for key, value in manifest.items() if key != "manifest_id"}
    if manifest.get("manifest_id") != f"sha256:{canonical_digest(body)}":
        raise G6PreflightError("frozen G5 manifest id mismatch")
    if manifest.get("run_id") != directory.name:
        raise G6PreflightError("frozen G5 run directory mismatch")
    if manifest.get("world") != expected_world or manifest.get("seed") != 0:
        raise G6PreflightError("frozen G5 artifact identity mismatch")
    if manifest.get("baseline_manifest_id") != baseline_manifest_id:
        raise G6PreflightError("frozen G5 baseline reference mismatch")
    records = manifest.get("artifacts")
    if not isinstance(records, list) or not records:
        raise G6PreflightError("frozen G5 artifact records are missing")
    names = [row.get("name") for row in records if isinstance(row, dict)]
    if len(names) != len(records) or len(set(names)) != len(names):
        raise G6PreflightError("frozen G5 artifact records are malformed")
    for row in records:
        path = directory / row["name"]
        if not path.is_file() or row.get("byte_size") != path.stat().st_size \
                or row.get("sha256") != _sha256_file(path):
            raise G6PreflightError(f"frozen G5 artifact drift: {path.name}")
    summary = manifest.get("result_summary", {})
    if summary.get("implementation_passed") is not True \
            or summary.get("vacuous") is not True \
            or summary.get("real_nonanchor_commits") != 0:
        raise G6PreflightError("frozen G5 vacuity record mismatch")


def repository_preflight(
    study: G6Study,
    amendment: G6Amendment,
    *,
    root: Path,
    require_clean: bool = True,
) -> None:
    """Verify both freezes and refuse any pre-existing G6 execution state."""
    study_path = study.manifest_path if study.manifest_path.is_absolute() \
        else root / study.manifest_path
    amendment_path = amendment.amendment_path \
        if amendment.amendment_path.is_absolute() else root / amendment.amendment_path
    if load_study_manifest(study_path) != study:
        raise G6PreflightError("in-memory G6 study differs from its manifest")
    if load_amendment(amendment_path) != amendment:
        raise G6PreflightError("in-memory G6 amendment differs from its manifest")
    if amendment.study_manifest_id != study.manifest_id:
        raise G6PreflightError("G6 amendment references a different study")
    if len(amendment.harness_commit) != 40 or len(amendment.harness_tree) != 40:
        raise G6PreflightError("G6 harness commit or tree is malformed")
    if _git(root, "rev-parse", f"{study.freeze_commit}^{{tree}}") \
            != study.freeze_tree:
        raise G6PreflightError("G0-G5 freeze tree mismatch")
    if _git(root, "rev-parse", f"{amendment.harness_commit}^{{tree}}") \
            != amendment.harness_tree:
        raise G6PreflightError("G6 harness freeze tree mismatch")
    frozen_ancestor = subprocess.run(
        (
            "git", "merge-base", "--is-ancestor",
            study.freeze_commit, amendment.harness_commit,
        ),
        cwd=root,
    )
    if frozen_ancestor.returncode != 0:
        raise G6PreflightError("G6 harness does not descend from G0-G5 freeze")
    ancestor = subprocess.run(
        ("git", "merge-base", "--is-ancestor", amendment.harness_commit, "HEAD"),
        cwd=root,
    )
    if ancestor.returncode != 0:
        raise G6PreflightError("current HEAD does not descend from G6 harness freeze")
    if require_clean and _git(root, "status", "--porcelain"):
        raise G6PreflightError("G6 execution requires a clean worktree")
    try:
        manifest_relative = str(study_path.resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G6PreflightError("G6 study manifest is outside the repository") from error
    try:
        frozen_manifest = subprocess.run(
            ("git", "show", f"{amendment.harness_commit}:{manifest_relative}"),
            cwd=root, check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise G6PreflightError("G6 study manifest is absent from harness commit") \
            from error
    if hashlib.sha256(frozen_manifest).hexdigest() != _sha256_file(study_path):
        raise G6PreflightError("G6 harness commit predates or changes the study manifest")
    for relative, expected in amendment.implementation_files:
        path = root / relative
        if not path.is_file() or _sha256_file(path) != expected:
            raise G6PreflightError(f"G6 implementation file drift: {relative}")
        try:
            frozen = subprocess.run(
                ("git", "show", f"{amendment.harness_commit}:{relative}"),
                cwd=root, check=True, capture_output=True,
            ).stdout
        except subprocess.CalledProcessError as error:
            raise G6PreflightError(
                f"G6 implementation file absent from commit: {relative}"
            ) from error
        if hashlib.sha256(frozen).hexdigest() != expected:
            raise G6PreflightError(f"G6 implementation commit mismatch: {relative}")

    baseline_path = root / DEFAULT_MANIFEST
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    validate_manifest(baseline, root, verify_data=True)
    if baseline.get("manifest_id") != study.baseline_manifest_id:
        raise G6PreflightError("G6 baseline manifest drift")
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
        raise G6PreflightError("G6 output or partial state already exists; rerun refused")


def _unit_directory(root: Path, phase: G6Phase, draw: G6Draw) -> Path:
    return root / f"{draw.ordinal:02d}-{draw.world}" / phase.value


def _validate_receipt(
    receipt: Mapping[str, Any], phase: G6Phase, draw: G6Draw,
) -> dict[str, Any]:
    value = canonical_data(receipt)
    if not isinstance(value, dict):
        raise ValueError("G6 phase receipt must be a mapping")
    required = {
        "schema_version", "phase", "world", "seed_sha256", "status",
        "artifact_records",
    }
    if set(value) != required:
        raise ValueError("G6 phase receipt fields differ from the frozen contract")
    if value["schema_version"] != "graphlog-certified-g6-phase-receipt/v1":
        raise ValueError("unsupported G6 phase receipt schema")
    if value["phase"] != phase.value or value["world"] != draw.world \
            or value["seed_sha256"] != draw.seed_sha256:
        raise ValueError("G6 phase receipt identity mismatch")
    if value["status"] not in ("PASS", "REPORTED_FAILURE"):
        raise ValueError("G6 phase receipt has an invalid status")
    records = value["artifact_records"]
    if not isinstance(records, list) or not records:
        raise ValueError("G6 phase receipt must name at least one artifact")
    names = [row.get("name") for row in records if isinstance(row, dict)]
    if len(names) != len(records) or len(set(names)) != len(names):
        raise ValueError("G6 phase receipt artifact names are malformed")
    return value


def _validate_unit_directory(
    unit: Path,
    phase: G6Phase,
    draw: G6Draw,
    expected_receipt_sha256: str,
) -> None:
    entries = tuple(unit.iterdir())
    if any(not path.is_file() for path in entries):
        raise ValueError("G6 phase output may contain only regular files")
    receipt_path = unit / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError("G6 phase receipt is missing")
    if _sha256_file(receipt_path) != expected_receipt_sha256:
        raise ValueError("G6 phase receipt changed after harness creation")
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
        raise ValueError("G6 phase artifact records do not match output")


def execute_study(
    study: G6Study,
    amendment: G6Amendment,
    executor: PhaseExecutor,
    *,
    root: Path,
    verify_repository: bool = True,
) -> Path:
    """Execute one immutable block; interrupted or existing blocks never rerun."""
    if not amendment.execution_enabled:
        raise G6PreflightError("G6 execution is disabled pending a pinned adapter")
    if verify_repository:
        repository_preflight(study, amendment, root=root)
    module = inspect.getmodule(executor)
    source = inspect.getsourcefile(executor)
    if module is None or source is None:
        raise G6PreflightError("G6 executor has no inspectable source module")
    try:
        relative = str(Path(source).resolve().relative_to(root.resolve()))
    except ValueError as error:
        raise G6PreflightError("G6 executor source is outside the repository") from error
    qualname = getattr(executor, "__qualname__", type(executor).__qualname__)
    if relative != amendment.executor_file or qualname != amendment.executor_qualname:
        raise G6PreflightError("G6 executor differs from the pinned adapter")
    output = root / study.output_root
    staging = output.with_name(f".{output.name}.{study.manifest_id[7:19]}.partial")
    if output.exists() or staging.exists():
        raise G6PreflightError("G6 output or partial state already exists; rerun refused")
    staging.mkdir(parents=True)
    index = {
        "schema_version": "graphlog-certified-g6-study-index/v1",
        "harness_version": G6_HARNESS_VERSION,
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "phase_order": tuple(phase.value for phase in study.phases),
        "world_order": tuple(draw.world for draw in study.draws),
        "completed_phases": [],
    }
    (staging / "study-index.json").write_bytes(canonical_bytes(index) + b"\n")
    receipt_digests: dict[tuple[G6Phase, int], str] = {}

    for phase_index, phase in enumerate(study.phases):
        if phase is G6Phase.ACCURACY and phase_index != len(study.phases) - 1:
            raise RuntimeError("accuracy must be the final G6 phase")
        for draw in study.draws:
            prior = {
                prior_phase: _unit_directory(staging, prior_phase, draw)
                for prior_phase in study.phases[:phase_index]
            }
            if set(prior) != set(study.phases[:phase_index]):
                raise RuntimeError("G6 phase barrier is incomplete")
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
    manifest_path: Path = G6_MANIFEST,
    amendment_path: Path = G6_AMENDMENT,
) -> G6Study:
    study = load_study_manifest(root / manifest_path)
    amendment = load_amendment_chain(root / amendment_path)[-1]
    repository_preflight(study, amendment, root=root)
    return study


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=G6_MANIFEST)
    parser.add_argument("--amendment", type=Path, default=G6_AMENDMENT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    study = preflight(
        root=root, manifest_path=args.manifest, amendment_path=args.amendment,
    )
    amendment = load_amendment_chain(root / args.amendment)[-1]
    print(json.dumps({
        "status": (
            "READY_NO_DRAWS_GENERATED"
            if amendment.execution_enabled
            else "CONTROL_READY_EXECUTION_DISABLED_NO_DRAWS_GENERATED"
        ),
        "study_manifest_id": study.manifest_id,
        "amendment_manifest_id": amendment.manifest_id,
        "execution_enabled": amendment.execution_enabled,
        "worlds": len(study.draws),
        "phases": [phase.value for phase in study.phases],
    }, indent=2))


if __name__ == "__main__":
    main()
