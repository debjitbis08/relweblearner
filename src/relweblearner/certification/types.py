"""Immutable ids, verdicts, and canonical serialization primitives.

Certificate JSON is deliberately stricter than ordinary application JSON:
there are no non-finite floats, mappings have string keys, and sets are not
accepted because their iteration order is not part of a theorem instance.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields, is_dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping


class ExtensionCardinality(str, Enum):
    EMPTY = "EMPTY"
    SINGLETON = "SINGLETON"
    MANY = "MANY"
    UNKNOWN = "UNKNOWN"


class TargetCardinality(str, Enum):
    EMPTY = "empty"
    IDENTICAL = "IDENTICAL"
    DISTINCT = "DISTINCT"
    MANY = "many"
    UNKNOWN = "UNKNOWN"


class NormId(str, Enum):
    SUP = "sup"
    EUCLIDEAN = "euclidean"
    FROBENIUS = "frobenius"


class VersionRef(tuple):
    """Small immutable ``(namespace, identifier)`` version reference."""

    __slots__ = ()

    def __new__(cls, namespace: str, identifier: str):
        if not namespace or not identifier:
            raise ValueError("version namespace and identifier must be non-empty")
        return super().__new__(cls, (namespace, identifier))

    @property
    def namespace(self) -> str:
        return self[0]

    @property
    def identifier(self) -> str:
        return self[1]


def canonical_data(value: Any) -> Any:
    """Convert a typed certificate value to deterministic JSON data."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("certificate values cannot contain NaN or infinity")
        return value
    if isinstance(value, Enum):
        return canonical_data(value.value)
    if isinstance(value, Fraction):
        return {"denominator": value.denominator, "numerator": value.numerator}
    if isinstance(value, VersionRef):
        return {"identifier": value.identifier, "namespace": value.namespace}
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: canonical_data(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("canonical mappings require string keys")
        return {k: canonical_data(value[k]) for k in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [canonical_data(item) for item in value]
    raise TypeError(f"unsupported canonical certificate value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        canonical_data(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
