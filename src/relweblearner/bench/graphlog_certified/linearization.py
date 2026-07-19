"""GraphLog role-adjacency linearization and observed anchor boundary for G2."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

import numpy as np

from ...certification.provenance import (
    DerivationRef,
    NormalizedProvenance,
    normalize_provenance,
)
from ...certification.t5 import (
    BoundarySpec,
    CellComplex,
    CellIncidence,
    EdgeWeight,
    ExactEntry,
    Linearization,
    ResidualBlock,
    Restriction,
    StalkSpec,
    validate_linearization,
)
from ...certification.types import canonical_digest
from .ingest import OpaqueToken
from .model import (
    CountingScope,
    IdentityExtension,
    ObservationFamily,
    TriangleFact,
    check_support_closed,
)
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


@dataclass(frozen=True, slots=True)
class RoleAdjacencyChannel:
    channel_id: str
    positions: tuple[int, int]
    weight: Fraction
    a_total: Fraction
    b_total: Fraction
    adjacency_a: tuple[tuple[Fraction, ...], ...]
    adjacency_b: tuple[tuple[Fraction, ...], ...]
    retained: bool
    omission_reason: str | None
    head_incidence: str
    tail_incidence: str


@dataclass(frozen=True, slots=True)
class GraphLogLinearization:
    version: str
    world: str
    a_tokens: tuple[OpaqueToken, ...]
    b_tokens: tuple[OpaqueToken, ...]
    channels: tuple[RoleAdjacencyChannel, ...]
    core: Linearization

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.a_tokens), len(self.b_tokens)

    def coordinate_id(self, a_index: int, b_index: int) -> str:
        return self.core.coordinate_ids[a_index * len(self.b_tokens) + b_index]

    def coordinate_index(self, a_token: OpaqueToken, b_token: OpaqueToken) -> int:
        try:
            a_index = self.a_tokens.index(a_token)
            b_index = self.b_tokens.index(b_token)
        except ValueError as exc:
            raise ValueError("coordinate token lies outside the view charts") from exc
        return a_index * len(self.b_tokens) + b_index


def _normalized_adjacency(
    triangles: tuple[TriangleFact, ...],
    tokens: tuple[OpaqueToken, ...],
    positions: tuple[int, int],
) -> tuple[Fraction, tuple[tuple[Fraction, ...], ...]]:
    index = {token: i for i, token in enumerate(tokens)}
    counts: dict[tuple[int, int], int] = defaultdict(int)
    total = 0
    source_position, target_position = positions
    for triangle in triangles:
        source = triangle.positions[source_position]
        target = triangle.positions[target_position]
        if source not in index or target not in index:
            raise ValueError("triangle relation lies outside its declared view chart")
        counts[(index[source], index[target])] += triangle.support
        total += triangle.support
    rational_total = Fraction(total)
    matrix = tuple(
        tuple(
            Fraction(counts.get((i, j), 0), total) if total else Fraction(0)
            for j in range(len(tokens))
        )
        for i in range(len(tokens))
    )
    return rational_total, matrix


def _commutator_block(
    channel_id: str,
    adjacency_a: tuple[tuple[Fraction, ...], ...],
    adjacency_b: tuple[tuple[Fraction, ...], ...],
    weight: Fraction,
) -> ResidualBlock:
    n_a = len(adjacency_a)
    n_b = len(adjacency_b)
    coordinate_count = n_a * n_b
    values: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
    for a in range(n_a):
        for b in range(n_b):
            output = a * n_b + b
            for a_source, coefficient in enumerate(adjacency_a[a]):
                if coefficient:
                    values[(output, a_source * n_b + b)] += coefficient
            for b_source in range(n_b):
                coefficient = adjacency_b[b_source][b]
                if coefficient:
                    values[(output, a * n_b + b_source)] -= coefficient
    entries = tuple(
        ExactEntry(row, column, value)
        for (row, column), value in sorted(values.items())
        if value
    )
    unweighted = np.zeros((coordinate_count, coordinate_count), dtype=float)
    for entry in entries:
        unweighted[entry.row, entry.column] = float(entry.value)
    return ResidualBlock(
        block_id=channel_id,
        row_count=coordinate_count,
        column_count=coordinate_count,
        exact_entries=entries,
        weight=weight,
        weighted_matrix=math.sqrt(float(weight)) * unweighted,
    )


def _restriction_entries(
    adjacency: tuple[tuple[Fraction, ...], ...],
    *,
    side: str,
    n_a: int,
    n_b: int,
) -> tuple[ExactEntry, ...]:
    entries: list[ExactEntry] = []
    if side == "head":
        for a in range(n_a):
            for b in range(n_b):
                output = a * n_b + b
                for a_source, coefficient in enumerate(adjacency[a]):
                    if coefficient:
                        entries.append(
                            ExactEntry(output, a_source * n_b + b, coefficient)
                        )
    elif side == "tail":
        for a in range(n_a):
            for b in range(n_b):
                output = a * n_b + b
                for b_source in range(n_b):
                    coefficient = adjacency[b_source][b]
                    if coefficient:
                        entries.append(
                            ExactEntry(output, a * n_b + b_source, coefficient)
                        )
    else:
        raise ValueError("restriction side must be head or tail")
    return tuple(entries)


def build_role_linearization(
    observations: ObservationFamily,
    scope: CountingScope,
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> GraphLogLinearization:
    """Build the six ordered commutator channels from opaque observations."""
    if not check_support_closed(scope, observations):
        raise ValueError("T5 linearization requires the certified support-closed scope")
    a_tokens = tuple(sorted(set(observations.relation_tokens_a)))
    b_tokens = tuple(sorted(set(observations.relation_tokens_b)))
    if not a_tokens or not b_tokens:
        raise ValueError("both GraphLog view charts must contain relation tokens")
    if any(token.view_id != "A" for token in a_tokens):
        raise ValueError("the A chart contains a non-A token")
    if any(token.view_id != "B" for token in b_tokens):
        raise ValueError("the B chart contains a non-B token")

    coordinate_ids = tuple(
        f"X:{a_index}:{b_index}"
        for a_index in range(len(a_tokens))
        for b_index in range(len(b_tokens))
    )
    channels: list[RoleAdjacencyChannel] = []
    blocks: list[ResidualBlock] = []
    omitted: list[str] = []
    for channel_index, (positions, weight) in enumerate(
        zip(spec.role_channels, spec.role_channel_weights, strict=True)
    ):
        channel_id = f"role:{positions[0]}->{positions[1]}:{channel_index}"
        total_a, adjacency_a = _normalized_adjacency(
            scope.triangles_a, a_tokens, positions
        )
        total_b, adjacency_b = _normalized_adjacency(
            scope.triangles_b, b_tokens, positions
        )
        retained = total_a > 0 and total_b > 0
        reason = None if retained else "empty-view-channel/non-propagating"
        channels.append(RoleAdjacencyChannel(
            channel_id=channel_id,
            positions=positions,
            weight=weight,
            a_total=total_a,
            b_total=total_b,
            adjacency_a=adjacency_a,
            adjacency_b=adjacency_b,
            retained=retained,
            omission_reason=reason,
            head_incidence=f"{channel_id}:head",
            tail_incidence=f"{channel_id}:tail",
        ))
        if retained:
            blocks.append(_commutator_block(
                channel_id, adjacency_a, adjacency_b, weight
            ))
        else:
            omitted.append(channel_id)
    retained_channels = tuple(channel for channel in channels if channel.retained)
    vertex_id = "v_align"
    coordinate_count = len(coordinate_ids)
    cell_complex = CellComplex(
        vertex_ids=(vertex_id,),
        edge_ids=tuple(channel.channel_id for channel in retained_channels),
        incidences=tuple(
            incidence
            for channel in retained_channels
            for incidence in (
                CellIncidence(
                    channel.head_incidence, channel.channel_id, vertex_id, "head"
                ),
                CellIncidence(
                    channel.tail_incidence, channel.channel_id, vertex_id, "tail"
                ),
            )
        ),
    )
    stalks = (
        StalkSpec(vertex_id, "vertex", coordinate_count, spec.field_norm),
        *(
            StalkSpec(
                channel.channel_id, "edge", coordinate_count, spec.field_norm
            )
            for channel in retained_channels
        ),
    )
    restrictions = tuple(
        restriction
        for channel in retained_channels
        for restriction in (
            Restriction(
                restriction_id=f"rho-head:{channel.channel_id}",
                edge_id=channel.channel_id,
                vertex_id=vertex_id,
                incidence_id=channel.head_incidence,
                role="head",
                row_count=coordinate_count,
                column_count=coordinate_count,
                exact_entries=_restriction_entries(
                    channel.adjacency_a,
                    side="head",
                    n_a=len(a_tokens),
                    n_b=len(b_tokens),
                ),
            ),
            Restriction(
                restriction_id=f"rho-tail:{channel.channel_id}",
                edge_id=channel.channel_id,
                vertex_id=vertex_id,
                incidence_id=channel.tail_incidence,
                role="tail",
                row_count=coordinate_count,
                column_count=coordinate_count,
                exact_entries=_restriction_entries(
                    channel.adjacency_b,
                    side="tail",
                    n_a=len(a_tokens),
                    n_b=len(b_tokens),
                ),
            ),
        )
    )
    core = Linearization(
        coordinate_ids,
        tuple(blocks),
        tuple(omitted),
        cell_complex,
        tuple(stalks),
        restrictions,
        tuple(EdgeWeight(channel.channel_id, channel.weight)
              for channel in retained_channels),
    )
    validate_linearization(core)
    return GraphLogLinearization(
        version=spec.linearization_version,
        world=observations.world,
        a_tokens=a_tokens,
        b_tokens=b_tokens,
        channels=tuple(channels),
        core=core,
    )


def build_linearization(
    observations: ObservationFamily,
    scope: CountingScope,
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> GraphLogLinearization:
    """The theorem-facing constructor name from the instantiation plan."""
    return build_role_linearization(observations, scope, spec=spec)


class BoundaryKind(str, Enum):
    ANCHOR = "anchor"
    BIJECTION_EXCLUSION = "bijection_exclusion"


@dataclass(frozen=True, slots=True)
class AnchorBoundaryCoordinate:
    coordinate_id: str
    coordinate_index: int
    value: int
    kind: BoundaryKind
    provenance: NormalizedProvenance


@dataclass(frozen=True, slots=True)
class GraphLogAnchorBoundary:
    version: str
    coordinates: tuple[AnchorBoundaryCoordinate, ...]

    @property
    def core(self) -> BoundarySpec:
        return BoundarySpec(tuple(
            (coordinate.coordinate_id, float(coordinate.value))
            for coordinate in self.coordinates
        ))


def build_anchor_boundary(
    observations: ObservationFamily,
    linearization: GraphLogLinearization,
) -> GraphLogAnchorBoundary:
    """Pin exactly observed anchors and their forced bijection exclusions."""
    anchors_by_pair: dict[
        tuple[OpaqueToken, OpaqueToken], list[NormalizedProvenance]
    ] = defaultdict(list)
    a_to_b: dict[OpaqueToken, OpaqueToken] = {}
    b_to_a: dict[OpaqueToken, OpaqueToken] = {}
    for anchor in observations.anchors:
        if anchor.a_token not in linearization.a_tokens:
            raise ValueError("anchor A token lies outside the linearized chart")
        if anchor.b_token not in linearization.b_tokens:
            raise ValueError("anchor B token lies outside the linearized chart")
        if anchor.a_token in a_to_b and a_to_b[anchor.a_token] != anchor.b_token:
            raise ValueError("anchors contradict row injectivity")
        if anchor.b_token in b_to_a and b_to_a[anchor.b_token] != anchor.a_token:
            raise ValueError("anchors contradict column injectivity")
        a_to_b[anchor.a_token] = anchor.b_token
        b_to_a[anchor.b_token] = anchor.a_token
        anchors_by_pair[(anchor.a_token, anchor.b_token)].append(anchor.provenance)

    records: dict[
        int, tuple[int, BoundaryKind, list[NormalizedProvenance]]
    ] = {}

    def add(
        index: int,
        value: int,
        kind: BoundaryKind,
        provenance: NormalizedProvenance,
    ) -> None:
        if index in records:
            old_value, old_kind, provenances = records[index]
            if old_value != value:
                raise ValueError("anchor boundary assigns conflicting values")
            records[index] = (
                old_value,
                BoundaryKind.ANCHOR
                if old_kind is BoundaryKind.ANCHOR or kind is BoundaryKind.ANCHOR
                else BoundaryKind.BIJECTION_EXCLUSION,
                [*provenances, provenance],
            )
        else:
            records[index] = (value, kind, [provenance])

    for (a_token, b_token), anchor_provenances in sorted(anchors_by_pair.items()):
        anchor_provenance = normalize_provenance(
            (ref for item in anchor_provenances for ref in item.observations),
            (ref for item in anchor_provenances for ref in item.derivations),
        )
        anchor_index = linearization.coordinate_index(a_token, b_token)
        add(anchor_index, 1, BoundaryKind.ANCHOR, anchor_provenance)
        parent_id = canonical_digest((a_token, b_token, anchor_provenance))
        exclusions = {
            linearization.coordinate_index(a_token, other_b)
            for other_b in linearization.b_tokens
            if other_b != b_token
        }
        exclusions.update(
            linearization.coordinate_index(other_a, b_token)
            for other_a in linearization.a_tokens
            if other_a != a_token
        )
        for exclusion_index in sorted(exclusions):
            coordinate_id = linearization.core.coordinate_ids[exclusion_index]
            derivation = DerivationRef(
                linearization.version,
                "bijection_exclusion",
                (parent_id, coordinate_id),
            )
            add(
                exclusion_index,
                0,
                BoundaryKind.BIJECTION_EXCLUSION,
                normalize_provenance(
                    anchor_provenance.observations,
                    (*anchor_provenance.derivations, derivation),
                ),
            )

    coordinates = tuple(
        AnchorBoundaryCoordinate(
            coordinate_id=linearization.core.coordinate_ids[index],
            coordinate_index=index,
            value=value,
            kind=kind,
            provenance=normalize_provenance(
                (ref for item in provenances for ref in item.observations),
                (ref for item in provenances for ref in item.derivations),
            ),
        )
        for index, (value, kind, provenances) in sorted(records.items())
    )
    return GraphLogAnchorBoundary(
        version="graphlog/observed-anchor-boundary/v1",
        coordinates=coordinates,
    )


def encode_extension(
    extension: IdentityExtension,
    linearization: GraphLogLinearization,
) -> np.ndarray:
    """Encode an exact partial bijection as its zero-one stalk matrix."""
    matrix = np.zeros(linearization.shape, dtype=float)
    for a_token, b_token in extension.pairs:
        index = linearization.coordinate_index(a_token, b_token)
        a_index, b_index = divmod(index, len(linearization.b_tokens))
        matrix[a_index, b_index] = 1.0
    if np.any(matrix.sum(axis=0) > 1) or np.any(matrix.sum(axis=1) > 1):
        raise ValueError("extension encoding is not a partial bijection")
    return matrix


def field_matrix(values: np.ndarray, linearization: GraphLogLinearization) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    expected = len(linearization.core.coordinate_ids)
    if values.shape != (expected,):
        raise ValueError("field vector has the wrong GraphLog coordinate dimension")
    return values.reshape(linearization.shape)
