"""Typed exhaustive GraphLog path/CYK derivation compiler for G3."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from ...certification.provenance import DerivationRef, normalize_provenance
from ...certification.t6 import DerivationDAG, DerivationNode, NodeKind
from ...certification.types import canonical_digest
from .ingest import OpaqueEdgeEvent, OpaqueQueryEpisode, OpaqueToken, RuntimeViewBundle
from .model import CandidateIdentity
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


RELATION_SET_TYPE = "graphlog/relation-set"
PROOF_VECTOR_TYPE = "graphlog/proof-vector"
IDENTITY_MATRIX_TYPE = "graphlog/identity-matrix"


def token_payload(token: OpaqueToken) -> str:
    return f"{token.view_id}:{token.value}"


@dataclass(frozen=True, slots=True)
class CompiledDerivationFamily:
    version: str
    query_derivations: tuple[DerivationDAG, ...]
    identity_derivations: tuple[DerivationDAG, ...]
    query_path_counts: tuple[tuple[str, int], ...]

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class _Builder:
    def __init__(self, derivation_id: str, spec: GraphLogCertifiedSpec):
        self.derivation_id = derivation_id
        self.spec = spec
        self.nodes: list[DerivationNode] = []
        self._by_id: dict[str, DerivationNode] = {}
        self._leaf_by_key: dict[tuple[str, str], str] = {}

    def _id(self, label: str) -> str:
        return f"n{len(self.nodes):05d}:{label}"

    def leaf(
        self,
        *,
        reader_id: str,
        output_type_id: str,
        payload_id: str,
        event: OpaqueEdgeEvent | None,
        share_key: tuple[str, str] | None = None,
    ) -> str:
        if share_key is not None and share_key in self._leaf_by_key:
            return self._leaf_by_key[share_key]
        node_id = self._id(reader_id)
        provenance = normalize_provenance(
            () if event is None else (event.observation,)
        )
        node = DerivationNode(
            node_id=node_id,
            kind=NodeKind.LEAF,
            output_type_id=output_type_id,
            child_ids=(),
            operation_id=None,
            reader_id=reader_id,
            payload_id=payload_id,
            provenance=provenance,
        )
        self.nodes.append(node)
        self._by_id[node_id] = node
        if share_key is not None:
            self._leaf_by_key[share_key] = node_id
        return node_id

    def operation(
        self,
        operation_id: str,
        output_type_id: str,
        children: Iterable[str],
    ) -> str:
        child_ids = tuple(children)
        observations = tuple(
            ref for child in child_ids for ref in self._by_id[child].provenance.observations
        )
        node_id = self._id(operation_id)
        derivation = DerivationRef(
            self.spec.derivation_version,
            operation_id,
            child_ids,
        )
        node = DerivationNode(
            node_id=node_id,
            kind=NodeKind.OPERATION,
            output_type_id=output_type_id,
            child_ids=child_ids,
            operation_id=operation_id,
            reader_id=None,
            payload_id=None,
            # Parent node ids retain the derivation DAG; copying every
            # transitive DerivationRef into every descendant would turn the
            # finite CYK DAG into a quadratic provenance document.
            provenance=normalize_provenance(observations, (derivation,)),
        )
        self.nodes.append(node)
        self._by_id[node_id] = node
        return node_id

    def finish(self, root_id: str) -> DerivationDAG:
        return DerivationDAG(self.derivation_id, tuple(self.nodes), root_id)


def _combined_query_edges(
    query_a: OpaqueQueryEpisode,
    query_b: OpaqueQueryEpisode,
) -> tuple[OpaqueEdgeEvent, ...]:
    if (
        query_a.episode_id != query_b.episode_id
        or query_a.source_node != query_b.source_node
        or query_a.destination_node != query_b.destination_node
    ):
        raise ValueError("paired opaque query episodes disagree on public topology")
    # Prefer A when an edge is visible in both charts; otherwise retain B's
    # opaque token.  This reconstructs the certified ensemble view using only
    # public observation ids, never hidden-set or permutation metadata.
    a_by_edge = {edge.observation.edge_index: edge for edge in query_a.edges}
    b_by_edge = {edge.observation.edge_index: edge for edge in query_b.edges}
    combined: list[OpaqueEdgeEvent] = []
    for edge_index in sorted(set(a_by_edge) | set(b_by_edge)):
        edge_a = a_by_edge.get(edge_index)
        edge_b = b_by_edge.get(edge_index)
        if edge_a is not None and edge_b is not None:
            if (edge_a.tail, edge_a.head) != (edge_b.tail, edge_b.head):
                raise ValueError("co-indexed query observations disagree on topology")
            combined.append(edge_a)
        else:
            chosen = edge_a if edge_a is not None else edge_b
            assert chosen is not None
            combined.append(chosen)
    return tuple(combined)


def _enumerate_paths(
    edges: tuple[OpaqueEdgeEvent, ...],
    source: int,
    destination: int,
    max_path: int,
) -> tuple[tuple[OpaqueEdgeEvent, ...], ...]:
    outgoing: dict[int, list[OpaqueEdgeEvent]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.tail].append(edge)
    for values in outgoing.values():
        values.sort(key=lambda edge: (
            edge.head, edge.observation.edge_index,
            edge.relation.view_id, edge.relation.value,
        ))
    paths: list[tuple[OpaqueEdgeEvent, ...]] = []

    def visit(node: int, path: tuple[OpaqueEdgeEvent, ...]) -> None:
        if node == destination and path:
            paths.append(path)
            return
        if len(path) >= max_path:
            return
        for edge in outgoing.get(node, ()):
            visit(edge.head, (*path, edge))

    visit(source, ())
    return tuple(paths)


def _compile_query(
    query_a: OpaqueQueryEpisode,
    query_b: OpaqueQueryEpisode,
    spec: GraphLogCertifiedSpec,
) -> tuple[DerivationDAG, int]:
    derivation_id = f"query:{query_a.episode_id}"
    builder = _Builder(derivation_id, spec)
    edges = _combined_query_edges(query_a, query_b)
    paths = _enumerate_paths(
        edges, query_a.source_node, query_a.destination_node, spec.max_path
    )
    empty = builder.leaf(
        reader_id="empty_proof",
        output_type_id=PROOF_VECTOR_TYPE,
        payload_id="structural-zero",
        event=None,
    )
    aggregate = empty
    for path in paths:
        leaves: list[str] = []
        for edge in path:
            raw = builder.leaf(
                reader_id="relation_token",
                output_type_id=RELATION_SET_TYPE,
                payload_id=token_payload(edge.relation),
                event=edge,
                share_key=(edge.observation.episode_id, str(edge.observation.edge_index)),
            )
            if edge.relation.view_id == "B":
                raw = builder.operation(
                    "translate_B_to_A", RELATION_SET_TYPE, (raw,)
                )
            leaves.append(raw)

        span: dict[tuple[int, int], str] = {
            (index, index + 1): leaf for index, leaf in enumerate(leaves)
        }
        for width in range(2, len(leaves) + 1):
            for start in range(0, len(leaves) - width + 1):
                end = start + width
                alternatives = [
                    builder.operation(
                        "compose",
                        RELATION_SET_TYPE,
                        (span[(start, split)], span[(split, end)]),
                    )
                    for split in range(start + 1, end)
                ]
                combined = alternatives[0]
                for alternative in alternatives[1:]:
                    combined = builder.operation(
                        "span_aggregate",
                        RELATION_SET_TYPE,
                        (combined, alternative),
                    )
                span[(start, end)] = combined
        path_result = span[(0, len(leaves))]
        aggregate = builder.operation(
            "path_aggregate", PROOF_VECTOR_TYPE, (aggregate, path_result)
        )
    root = builder.operation("decode_output", PROOF_VECTOR_TYPE, (aggregate,))
    return builder.finish(root), len(paths)


def compile_query_derivations(
    runtime: RuntimeViewBundle,
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> tuple[tuple[DerivationDAG, ...], tuple[tuple[str, int], ...]]:
    view_a, view_b = runtime.opaque_views
    if len(view_a.query_episodes) != len(view_b.query_episodes):
        raise ValueError("opaque query views differ in episode count")
    compiled = tuple(
        _compile_query(query_a, query_b, spec)
        for query_a, query_b in zip(
            view_a.query_episodes, view_b.query_episodes, strict=True
        )
    )
    return (
        tuple(item[0] for item in compiled),
        tuple((item[0].derivation_id, item[1]) for item in compiled),
    )


def compile_identity_derivations(
    candidates: Iterable[CandidateIdentity],
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> tuple[DerivationDAG, ...]:
    dags = []
    for candidate in sorted(candidates, key=lambda item: (
        item.a_token.value, item.b_token.value
    )):
        derivation_id = (
            f"identity:{candidate.a_token.value}:{candidate.b_token.value}"
        )
        builder = _Builder(derivation_id, spec)
        root = builder.operation("decode_identity", IDENTITY_MATRIX_TYPE, ())
        # The zero-arity decoder depends on the candidate's supported target.
        node = builder.nodes[-1]
        builder.nodes[-1] = DerivationNode(
            node_id=node.node_id,
            kind=node.kind,
            output_type_id=node.output_type_id,
            child_ids=node.child_ids,
            operation_id=node.operation_id,
            reader_id=node.reader_id,
            payload_id=(
                f"{token_payload(candidate.a_token)}|{token_payload(candidate.b_token)}"
            ),
            provenance=normalize_provenance(
                candidate.provenance.observations,
                (*candidate.provenance.derivations, *node.provenance.derivations),
            ),
        )
        builder._by_id[root] = builder.nodes[-1]
        dags.append(builder.finish(root))
    return tuple(dags)


def compile_derivations(
    runtime: RuntimeViewBundle,
    candidates: Iterable[CandidateIdentity],
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> CompiledDerivationFamily:
    query_dags, path_counts = compile_query_derivations(runtime, spec=spec)
    identity_dags = compile_identity_derivations(candidates, spec=spec)
    return CompiledDerivationFamily(
        version=spec.derivation_version,
        query_derivations=query_dags,
        identity_derivations=identity_dags,
        query_path_counts=path_counts,
    )
