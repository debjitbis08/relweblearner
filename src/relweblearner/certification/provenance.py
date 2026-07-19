"""Normalized immutable provenance records and source counting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProvenanceKind(str, Enum):
    OBSERVATION = "observation"
    DERIVATION = "derivation"
    ANCHOR = "anchor"
    BIJECTION_EXCLUSION = "bijection_exclusion"
    PRIOR = "prior"
    REGULARIZER = "regularizer"
    IMAGINED = "imagined"
    EVALUATION_GOLD = "evaluation_gold"


@dataclass(frozen=True, order=True, slots=True)
class ObservationRef:
    dataset_version: str
    world: str
    split: str
    episode_id: str
    edge_index: int
    view_id: str

    def __post_init__(self) -> None:
        if not self.dataset_version or not self.world or not self.episode_id:
            raise ValueError("observation ids must be non-empty")
        if self.split not in {"train", "test"}:
            raise ValueError(f"unsupported split {self.split!r}")
        if self.edge_index < 0:
            raise ValueError("edge_index must be non-negative")
        if self.view_id not in {"A", "B"}:
            raise ValueError(f"unsupported view {self.view_id!r}")

    @property
    def origin_id(self) -> tuple[str, str]:
        """P1 counts view origins, not the number of derived paths."""
        return self.dataset_version, self.view_id


@dataclass(frozen=True, order=True, slots=True)
class DerivationRef:
    rule_version: str
    operation_id: str
    ordered_parent_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.rule_version or not self.operation_id:
            raise ValueError("derivation ids must be non-empty")


@dataclass(frozen=True, slots=True)
class NormalizedProvenance:
    observations: tuple[ObservationRef, ...] = ()
    derivations: tuple[DerivationRef, ...] = ()

    @property
    def origin_ids(self) -> frozenset[tuple[str, str]]:
        return frozenset(ref.origin_id for ref in self.observations)


def normalize_provenance(
    observations: Iterable[ObservationRef] = (),
    derivations: Iterable[DerivationRef] = (),
) -> NormalizedProvenance:
    """Deduplicate and sort refs so path multiplicity cannot inflate P1."""
    return NormalizedProvenance(
        observations=tuple(sorted(set(observations))),
        derivations=tuple(sorted(set(derivations))),
    )
