"""Reusable certificate primitives for the T5--T7 implementation.

Benchmark adapters live outside this package.  The modules here must remain
independent of GraphLog labels and evaluation data.
"""

from .types import (
    ExtensionCardinality,
    NormId,
    TargetCardinality,
    VersionRef,
    canonical_bytes,
    canonical_digest,
)

__all__ = [
    "ExtensionCardinality",
    "NormId",
    "TargetCardinality",
    "VersionRef",
    "canonical_bytes",
    "canonical_digest",
]
