"""Deterministic G0b notarization of the frozen GraphLog baselines."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ...certification.types import canonical_bytes, canonical_digest
from .spec import VALIDATION_WORLDS


MANIFEST_SCHEMA = "graphlog-certified-baselines/v1"
SEMANTIC_HASH_VERSION = "canonical-json-exact-pointer-exclusions/v1"
SEMANTIC_EXCLUSION_POLICY = "exact JSON pointers removed before canonical JSON hashing"
DEFAULT_MANIFEST = Path("results/graphlog-certified/baselines/manifest.json")


@dataclass(frozen=True, slots=True)
class CollectionSpec:
    pointer: str
    kind: str
    required_fields: tuple[str, ...] = ()
    identity_field: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    artifact_id: str
    path: str
    schema: str
    semantic_exclusions: tuple[str, ...]
    reproduction_command: str
    expected_pointers: tuple[str, ...]
    collections: tuple[CollectionSpec, ...] = ()
    dependencies: tuple[str, ...] = ()


def _world_arg() -> str:
    return ",".join(VALIDATION_WORLDS)


ARTIFACT_SPECS = (
    ArtifactSpec(
        "multiweb_graphlog",
        "results/multiweb-graphlog/results.json",
        "multiweb-graphlog/results-v1",
        ("/summary/elapsed_s",),
        ".venv/bin/python -m relweblearner.bench.multiweb_graphlog "
        f"--worlds {_world_arg()} --n-train 150 --seed 0 "
        "--out results/multiweb-graphlog",
        ("/summary",),
        (CollectionSpec(
            "/worlds", "list",
            ("world", "seed", "accuracy", "alignment", "s0", "rules", "n_labels", "prior"),
            "world",
        ),),
        ("code", "data", "baseline_specs", "graphlog_heldout_reference"),
    ),
    ArtifactSpec(
        "graded_graphlog",
        "results/graded-ensemble/graphlog.json",
        "graded-ensemble/graphlog-v1",
        ("/summary/elapsed_s",),
        ".venv/bin/python -m relweblearner.bench.multiweb_graded "
        "--arm graphlog --out results/graded-ensemble",
        ("/summary",),
        (CollectionSpec(
            "/worlds", "list",
            ("world", "graded", "commits", "discrete", "view_alone", "gold"),
            "world",
        ),),
        ("code", "data", "baseline_specs", "artifact:multiweb_graphlog"),
    ),
    ArtifactSpec(
        "rule20_factorial",
        "results/rule20-diagnosis/factorial.json",
        "rule20-diagnosis/factorial-v1",
        (),
        ".venv/bin/python -m relweblearner.bench.rule20_diag "
        "--exactify --out results/rule20-diagnosis",
        (
            "/factors", "/cells/none/acc", "/cells/R/acc", "/cells/D/acc",
            "/cells/C/acc", "/cells/C+R/acc", "/cells/C+D+R/acc",
            "/cells/C+R+S/acc", "/two_by_two", "/beam_recheck",
        ),
        (CollectionSpec(
            "/cells", "mapping",
            ("acc", "heals", "breaks", "healed_idx", "broken_idx"),
        ),),
        ("code", "data", "baseline_specs", "artifact:multiweb_graphlog",
         "artifact:graded_graphlog"),
    ),
    ArtifactSpec(
        "rule20_episode_sets",
        "results/rule20-diagnosis/episode-sets.json",
        "rule20-diagnosis/episode-sets-v1",
        (),
        ".venv/bin/python -m relweblearner.bench.rule20_diag "
        "--exactify --out results/rule20-diagnosis",
        (
            "/p_commits/n_wrong_commits", "/p_commits/minus_wrong_commits/acc",
            "/p_commits/anchors_only/acc", "/p_ident/acc",
            "/p_agg/max/acc", "/p_agg/count/acc",
        ),
        (),
        ("code", "data", "baseline_specs", "artifact:multiweb_graphlog",
         "artifact:graded_graphlog"),
    ),
    ArtifactSpec(
        "rule27_diagnosis",
        "results/rule27-diagnosis/results.json",
        "rule27-diagnosis/results-v1",
        ("/elapsed_s",),
        ".venv/bin/python -m relweblearner.bench.rule27_diag "
        "--seeds-robust 4 --out results/rule27-diagnosis",
        (
            "/world", "/consistency_gate", "/attribution/n_test",
            "/attribution/cells", "/repair_curve", "/unmerge",
            "/rule_patch/acc_base", "/rule_patch/acc_patched",
            "/rule_patch/acc_gold", "/graded/graded_acc",
            "/graded/graded_commits_n",
        ),
        (CollectionSpec(
            "/attribution/episodes", "list", ("i", "target", "cause"), "i",
        ),),
        ("code", "data", "baseline_specs", "artifact:multiweb_graphlog",
         "artifact:graded_graphlog"),
    ),
    ArtifactSpec(
        "rule27_graded_causal",
        "results/rule27-diagnosis/graded-causal.json",
        "rule27-diagnosis/graded-causal-v1",
        (),
        ".venv/bin/python -m relweblearner.bench.rule27_diag "
        "--graded-causal --out results/rule27-diagnosis",
        ("",),  # Intentionally pin the complete 268-byte headline document.
        (),
        ("code", "data", "baseline_specs", "artifact:multiweb_graphlog",
         "artifact:graded_graphlog", "artifact:rule27_diagnosis"),
    ),
)


CODE_INPUTS = (
    "pyproject.toml",
    "uv.lock",
    "src/relweblearner/bench/graphlog.py",
    "src/relweblearner/bench/multiweb.py",
    "src/relweblearner/bench/multiweb_graphlog.py",
    "src/relweblearner/bench/multiweb_graded.py",
    "src/relweblearner/bench/rule20_diag.py",
    "src/relweblearner/bench/rule27_diag.py",
)

BASELINE_SPEC_INPUTS = (
    "docs/multiweb-graphlog-plan.md",
    "docs/graded-ensemble-plan.md",
    "docs/rule20-diagnosis-plan.md",
    "docs/rule27-diagnosis-plan.md",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def pointer_get(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer {pointer!r}")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = _decode_pointer_part(raw_part)
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(pointer)
    return current


def _remove_pointer(document: Any, pointer: str) -> None:
    if pointer == "" or not pointer.startswith("/"):
        raise ValueError("semantic exclusions must be non-root JSON pointers")
    parts = [_decode_pointer_part(part) for part in pointer[1:].split("/")]
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    final = parts[-1]
    if isinstance(parent, list):
        del parent[int(final)]
    else:
        del parent[final]


def semantic_document(document: Any, exclusions: Iterable[str]) -> Any:
    semantic = copy.deepcopy(document)
    for pointer in exclusions:
        _remove_pointer(semantic, pointer)
    return semantic


def semantic_sha256(document: Any, exclusions: Iterable[str]) -> str:
    return _sha256_bytes(canonical_bytes(semantic_document(document, exclusions)))


def _file_record(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    data = path.read_bytes()
    return {
        "path": relative_path,
        "byte_size": len(data),
        "raw_sha256": _sha256_bytes(data),
    }


def _input_group(root: Path, paths: Iterable[str], *, schema: str) -> dict[str, Any]:
    files = tuple(_file_record(root, path) for path in sorted(paths))
    return {
        "schema": schema,
        "id": f"sha256:{canonical_digest(files)}",
        "files": files,
    }


def _declared_data_paths() -> tuple[str, ...]:
    paths = []
    for world in VALIDATION_WORLDS:
        number = world.split("_", 1)[1]
        base = Path("data/graphlog/graphlog_v1.1/train") / world
        for name in ("train.jsonl", "test.jsonl", f"rules_{number}.json"):
            paths.append(str(base / name))
    return tuple(paths)


def _data_paths(root: Path) -> tuple[str, ...]:
    paths = _declared_data_paths()
    for relative in paths:
        if not (root / relative).is_file():
            raise FileNotFoundError(f"missing GraphLog input {relative}")
    return paths


def _collection_record(document: Any, spec: CollectionSpec) -> dict[str, Any]:
    collection = pointer_get(document, spec.pointer)
    if spec.kind == "list":
        if not isinstance(collection, list):
            raise TypeError(f"{spec.pointer} is not a list")
        values = collection
    elif spec.kind == "mapping":
        if not isinstance(collection, dict):
            raise TypeError(f"{spec.pointer} is not a mapping")
        values = list(collection.values())
    else:
        raise ValueError(f"unsupported collection kind {spec.kind!r}")
    for value in values:
        if not isinstance(value, dict) or not set(spec.required_fields) <= set(value):
            raise ValueError(f"collection {spec.pointer} lacks required fields")
    record: dict[str, Any] = {
        "pointer": spec.pointer,
        "kind": spec.kind,
        "count": len(collection),
        "required_fields": spec.required_fields,
        "canonical_sha256": canonical_digest(collection),
    }
    if spec.identity_field is not None:
        identities = [value[spec.identity_field] for value in values]
        if len(set(identities)) != len(identities):
            raise ValueError(f"collection {spec.pointer} identities are not unique")
        record["identity_field"] = spec.identity_field
        record["identity_sha256"] = canonical_digest(identities)
    return record


def _artifact_record(root: Path, spec: ArtifactSpec) -> dict[str, Any]:
    file_record = _file_record(root, spec.path)
    document = json.loads((root / spec.path).read_text(encoding="utf-8"))
    semantic = semantic_document(document, spec.semantic_exclusions)
    return {
        "artifact_id": spec.artifact_id,
        **file_record,
        "schema": spec.schema,
        "semantic_hash_version": SEMANTIC_HASH_VERSION,
        "semantic_exclusions": spec.semantic_exclusions,
        "semantic_sha256": _sha256_bytes(canonical_bytes(semantic)),
        "reproduction_command": spec.reproduction_command,
        "dependencies": spec.dependencies,
        "expected_fields": {
            pointer: pointer_get(semantic, pointer)
            for pointer in spec.expected_pointers
        },
        "collections": tuple(
            _collection_record(semantic, collection) for collection in spec.collections
        ),
    }


def build_manifest(root: Path | None = None) -> dict[str, Any]:
    root = root or _repo_root()
    input_groups = {
        "code": _input_group(root, CODE_INPUTS, schema="source-files/v1"),
        "baseline_specs": _input_group(
            root, BASELINE_SPEC_INPUTS, schema="baseline-spec-files/v1",
        ),
        "graphlog_heldout_reference": _input_group(
            root,
            ("results/graphlog-heldout/results.json",),
            schema="historical-reference/v1",
        ),
        "data": {
            **_input_group(root, _data_paths(root), schema="graphlog-data-files/v1"),
            "dataset_version": "graphlog/v1.1",
            "declared_source_zip_md5": "5b6762c8e343659eaf96547787c596d4",
            "worlds": VALIDATION_WORLDS,
        },
    }
    raw_artifacts = tuple(_artifact_record(root, spec) for spec in ARTIFACT_SPECS)
    artifacts_by_id = {record["artifact_id"]: record for record in raw_artifacts}
    artifacts = tuple({
        **record,
        "producing_ids": {
            dependency: (
                f"sha256:{artifacts_by_id[dependency.removeprefix('artifact:')]['semantic_sha256']}"
                if dependency.startswith("artifact:")
                else input_groups[dependency]["id"]
            )
            for dependency in spec.dependencies
        },
    } for spec, record in zip(ARTIFACT_SPECS, raw_artifacts))
    body = {
        "schema_version": MANIFEST_SCHEMA,
        "semantic_hash_version": SEMANTIC_HASH_VERSION,
        "semantic_exclusion_policy": SEMANTIC_EXCLUSION_POLICY,
        "input_groups": input_groups,
        "artifacts": artifacts,
    }
    manifest = {**body, "manifest_id": f"sha256:{canonical_digest(body)}"}
    # Return the same JSON-native shape that a checked-in round trip has;
    # tuples are an implementation detail, not a manifest distinction.
    return json.loads(canonical_bytes(manifest))


def _validate_input_group(
    root: Path,
    group: dict[str, Any],
    *,
    expected_schema: str,
    expected_paths: Iterable[str],
    verify_files: bool,
) -> None:
    declared_paths = tuple(sorted(expected_paths))
    recorded_paths = tuple(record["path"] for record in group["files"])
    if group.get("schema") != expected_schema:
        raise ValueError(f"input group schema mismatch: expected {expected_schema}")
    if recorded_paths != declared_paths:
        raise ValueError(f"input group {expected_schema} path set mismatch")
    if not verify_files:
        return
    files = tuple(_file_record(root, record["path"]) for record in group["files"])
    if canonical_bytes(files) != canonical_bytes(group["files"]):
        raise ValueError(f"input group {group['schema']} file digest mismatch")
    if group["id"] != f"sha256:{canonical_digest(files)}":
        raise ValueError(f"input group {group['schema']} id mismatch")


def validate_manifest(
    manifest: dict[str, Any],
    root: Path | None = None,
    *,
    verify_data: bool = False,
) -> None:
    root = root or _repo_root()
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("unsupported baseline manifest schema")
    if manifest.get("semantic_hash_version") != SEMANTIC_HASH_VERSION:
        raise ValueError("baseline semantic hash version mismatch")
    if manifest.get("semantic_exclusion_policy") != SEMANTIC_EXCLUSION_POLICY:
        raise ValueError("baseline semantic exclusion policy mismatch")
    body = {key: value for key, value in manifest.items() if key != "manifest_id"}
    if manifest.get("manifest_id") != f"sha256:{canonical_digest(body)}":
        raise ValueError("baseline manifest id mismatch")

    specs = {spec.artifact_id: spec for spec in ARTIFACT_SPECS}
    records = {record["artifact_id"]: record for record in manifest["artifacts"]}
    if set(records) != set(specs):
        raise ValueError("baseline manifest artifact set mismatch")
    for artifact_id, spec in specs.items():
        expected = _artifact_record(root, spec)
        expected["producing_ids"] = {
            dependency: (
                f"sha256:{records[dependency.removeprefix('artifact:')]['semantic_sha256']}"
                if dependency.startswith("artifact:")
                else manifest["input_groups"][dependency]["id"]
            )
            for dependency in spec.dependencies
        }
        if canonical_bytes(records[artifact_id]) != canonical_bytes(expected):
            raise ValueError(f"baseline artifact {artifact_id} mismatch")

    input_groups = manifest.get("input_groups", {})
    expected_groups = {
        "code": ("source-files/v1", CODE_INPUTS),
        "baseline_specs": ("baseline-spec-files/v1", BASELINE_SPEC_INPUTS),
        "graphlog_heldout_reference": (
            "historical-reference/v1", ("results/graphlog-heldout/results.json",),
        ),
        "data": ("graphlog-data-files/v1", _declared_data_paths()),
    }
    if set(input_groups) != set(expected_groups):
        raise ValueError("baseline manifest input group set mismatch")
    data = input_groups["data"]
    if data.get("dataset_version") != "graphlog/v1.1":
        raise ValueError("GraphLog dataset version mismatch")
    if data.get("declared_source_zip_md5") != "5b6762c8e343659eaf96547787c596d4":
        raise ValueError("GraphLog source archive id mismatch")
    if tuple(data.get("worlds", ())) != VALIDATION_WORLDS:
        raise ValueError("GraphLog validation world cohort mismatch")
    for name, (schema, paths) in expected_groups.items():
        _validate_input_group(
            root,
            input_groups[name],
            expected_schema=schema,
            expected_paths=paths,
            verify_files=name != "data" or verify_data,
        )


def write_manifest(path: Path = DEFAULT_MANIFEST, root: Path | None = None) -> dict[str, Any]:
    root = root or _repo_root()
    manifest = build_manifest(root)
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validate_manifest(manifest, root, verify_data=True)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the frozen manifest")
    parser.add_argument("--verify-data", action="store_true")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args(argv)
    root = _repo_root()
    path = Path(args.manifest)
    if args.write:
        manifest = write_manifest(path, root)
    else:
        manifest = json.loads((root / path).read_text(encoding="utf-8"))
        validate_manifest(manifest, root, verify_data=args.verify_data)
    print(manifest["manifest_id"])


if __name__ == "__main__":
    main()
