"""Trusted raw-label boundary for the certified two-view GraphLog slice.

Raw relation labels, visibility sets, and permutations are local variables in
``ingest_world``.  The returned runtime object contains only opaque per-view
events and typed observation refs.  Gold remains behind an ``EvaluationKey``.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ...certification.provenance import (
    NormalizedProvenance,
    ObservationRef,
    normalize_provenance,
)
from .evaluation import EvaluationKey, _seal_evaluation_key
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


@dataclass(frozen=True, order=True, slots=True)
class OpaqueToken:
    view_id: str
    value: str

    def __post_init__(self) -> None:
        if self.view_id not in {"A", "B"}:
            raise ValueError(f"unsupported view {self.view_id!r}")
        if not self.value:
            raise ValueError("opaque token value must be non-empty")


@dataclass(frozen=True, slots=True)
class OpaqueEdgeEvent:
    tail: int
    head: int
    relation: OpaqueToken
    observation: ObservationRef

    def __post_init__(self) -> None:
        if self.relation.view_id != self.observation.view_id:
            raise ValueError("edge token and observation must name the same view")


@dataclass(frozen=True, slots=True)
class OpaqueEpisode:
    episode_id: str
    edges: tuple[OpaqueEdgeEvent, ...]


@dataclass(frozen=True, slots=True)
class OpaqueQueryEpisode:
    episode_id: str
    source_node: int
    destination_node: int
    edges: tuple[OpaqueEdgeEvent, ...]


@dataclass(frozen=True, slots=True)
class OpaqueView:
    view_id: str
    train_episodes: tuple[OpaqueEpisode, ...]
    query_episodes: tuple[OpaqueQueryEpisode, ...]

    def __post_init__(self) -> None:
        if self.view_id not in {"A", "B"}:
            raise ValueError(f"unsupported view {self.view_id!r}")


@dataclass(frozen=True, slots=True)
class OpaqueOverlapEvent:
    episode_id: str
    edge_index: int
    a_token: OpaqueToken
    b_token: OpaqueToken
    a_observation: ObservationRef
    b_observation: ObservationRef

    def __post_init__(self) -> None:
        if self.a_token.view_id != "A" or self.b_token.view_id != "B":
            raise ValueError("overlap events require one A token and one B token")
        if self.a_observation.episode_id != self.b_observation.episode_id:
            raise ValueError("overlap observations must co-witness one episode")
        if self.a_observation.edge_index != self.b_observation.edge_index:
            raise ValueError("overlap observations must co-witness one edge")

    @property
    def provenance(self) -> NormalizedProvenance:
        return normalize_provenance((self.a_observation, self.b_observation))


@dataclass(frozen=True, slots=True)
class RuntimeViewBundle:
    schema_version: str
    dataset_version: str
    world: str
    seed: int
    opaque_views: tuple[OpaqueView, OpaqueView]
    opaque_overlap_events: tuple[OpaqueOverlapEvent, ...]
    observation_refs: tuple[ObservationRef, ...]

    def __post_init__(self) -> None:
        if tuple(view.view_id for view in self.opaque_views) != ("A", "B"):
            raise ValueError("runtime bundle must contain ordered A and B views")
        nested_refs = {
            edge.observation
            for view in self.opaque_views
            for episode in (*view.train_episodes, *view.query_episodes)
            for edge in episode.edges
        }
        if self.observation_refs != tuple(sorted(nested_refs)):
            raise ValueError("observation_refs must be the normalized runtime edge refs")

    def view(self, view_id: str) -> OpaqueView:
        if view_id not in {"A", "B"}:
            raise KeyError(view_id)
        return self.opaque_views[0 if view_id == "A" else 1]


@dataclass(frozen=True, slots=True)
class TypedAnchor:
    a_token: OpaqueToken
    b_token: OpaqueToken
    provenance: NormalizedProvenance


def _relation_labels(raw_world: Mapping) -> list[str]:
    # Relation vocabulary comes from observable edge inputs only.  In
    # particular, changing a held-out query answer (even to a target-only
    # label) cannot alter a permutation, hidden set, or runtime byte.
    labels = {
        relation
        for split in ("train", "test")
        for episode in raw_world.get(split, ())
        for _tail, _head, relation in episode["edges"]
    }
    if not labels:
        raise ValueError("GraphLog world has no relation labels")
    return sorted(labels)


def ingest_world(
    raw_world: Mapping,
    *,
    seed: int,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> tuple[RuntimeViewBundle, EvaluationKey]:
    """Split a raw GraphLog world into runtime and sealed evaluation values."""
    world = str(raw_world.get("name", ""))
    if not world:
        raise ValueError("raw world requires a name")
    labels = _relation_labels(raw_world)
    rng = random.Random(seed)
    n_hide = max(2, round(float(spec.hide_fraction) * len(labels)))
    if 2 * n_hide > len(labels):
        raise ValueError("world has too few labels for two disjoint hidden sets")
    hidden = rng.sample(labels, 2 * n_hide)
    hide_a, hide_b = set(hidden[:n_hide]), set(hidden[n_hide:])

    def permutation(prefix: str) -> dict[str, str]:
        order = list(labels)
        rng.shuffle(order)
        return {label: f"{prefix}{i}" for i, label in enumerate(order)}

    perm_a, perm_b = permutation("a"), permutation("b")

    overlap: list[OpaqueOverlapEvent] = []

    def render_train(view_id: str, hidden_set: set[str], perm: Mapping[str, str]):
        rendered = []
        for episode_index, episode in enumerate(raw_world.get("train", ())):
            episode_id = f"train:{episode_index:06d}"
            edges = []
            for edge_index, (tail, head, raw_relation) in enumerate(episode["edges"]):
                if raw_relation in hidden_set:
                    continue
                ref = ObservationRef(
                    spec.dataset_version, world, "train", episode_id, edge_index, view_id,
                )
                edges.append(OpaqueEdgeEvent(
                    int(tail), int(head), OpaqueToken(view_id, perm[raw_relation]), ref,
                ))
            rendered.append(OpaqueEpisode(episode_id, tuple(edges)))
        return tuple(rendered)

    train_a = render_train("A", hide_a, perm_a)
    train_b = render_train("B", hide_b, perm_b)

    # Overlap is emitted at the same boundary, while the raw relation is in
    # scope, so later anchor selection never needs a permutation or gold label.
    for episode_index, episode in enumerate(raw_world.get("train", ())):
        episode_id = f"train:{episode_index:06d}"
        for edge_index, (_tail, _head, raw_relation) in enumerate(episode["edges"]):
            if raw_relation in hide_a or raw_relation in hide_b:
                continue
            a_ref = ObservationRef(
                spec.dataset_version, world, "train", episode_id, edge_index, "A",
            )
            b_ref = ObservationRef(
                spec.dataset_version, world, "train", episode_id, edge_index, "B",
            )
            overlap.append(OpaqueOverlapEvent(
                episode_id,
                edge_index,
                OpaqueToken("A", perm_a[raw_relation]),
                OpaqueToken("B", perm_b[raw_relation]),
                a_ref,
                b_ref,
            ))

    def render_queries(view_id: str, hidden_set: set[str], perm: Mapping[str, str]):
        rendered = []
        for episode_index, episode in enumerate(raw_world.get("test", ())):
            episode_id = f"test:{episode_index:06d}"
            query = episode.get("query")
            if not query or len(query) < 2:
                raise ValueError(f"test episode {episode_id} has no query endpoints")
            edges = []
            for edge_index, (tail, head, raw_relation) in enumerate(episode["edges"]):
                if raw_relation in hidden_set:
                    continue
                ref = ObservationRef(
                    spec.dataset_version, world, "test", episode_id, edge_index, view_id,
                )
                edges.append(OpaqueEdgeEvent(
                    int(tail), int(head), OpaqueToken(view_id, perm[raw_relation]), ref,
                ))
            rendered.append(OpaqueQueryEpisode(
                episode_id, int(query[0]), int(query[1]), tuple(edges),
            ))
        return tuple(rendered)

    view_a = OpaqueView("A", train_a, render_queries("A", hide_a, perm_a))
    view_b = OpaqueView("B", train_b, render_queries("B", hide_b, perm_b))
    observation_refs = tuple(sorted({
        edge.observation
        for view in (view_a, view_b)
        for episode in (*view.train_episodes, *view.query_episodes)
        for edge in episode.edges
    }))
    runtime = RuntimeViewBundle(
        schema_version=spec.schema_version,
        dataset_version=spec.dataset_version,
        world=world,
        seed=seed,
        opaque_views=(view_a, view_b),
        opaque_overlap_events=tuple(overlap),
        observation_refs=observation_refs,
    )

    raw_rules = raw_world.get("rules", {})
    oracle_rules = {
        tuple(body.split(",")) if isinstance(body, str) else tuple(body): head
        for body, head in raw_rules.items()
    }
    evaluation_key = _seal_evaluation_key(
        perm_a=perm_a,
        perm_b=perm_b,
        query_targets=tuple(episode["query"][2] for episode in raw_world.get("test", ())),
        oracle_rules=oracle_rules,
    )
    return runtime, evaluation_key


def select_anchors(
    overlap_events: Iterable[OpaqueOverlapEvent],
    component_of_a: Mapping[OpaqueToken, int],
    *,
    budget: int = DEFAULT_SPEC.anchor_budget,
) -> tuple[TypedAnchor, ...]:
    """Choose co-witnessed anchors using only opaque overlap and A topology."""
    if budget < 0:
        raise ValueError("anchor budget must be non-negative")
    events = tuple(overlap_events)
    if any(token.view_id != "A" for token in component_of_a):
        raise ValueError("component map may contain only A-view tokens")
    component_size = Counter(component_of_a.values())
    anchored_a: set[OpaqueToken] = set()
    anchored_b: set[OpaqueToken] = set()
    selected: list[TypedAnchor] = []
    for _ in range(budget):
        anchored_count = Counter(
            component_of_a[token] for token in anchored_a if token in component_of_a
        )
        ranked = sorted(
            component_size,
            key=lambda component: (
                anchored_count[component], -component_size[component], component,
            ),
        )
        chosen = None
        for component in ranked:
            chosen = next((
                event for event in events
                if event.a_token not in anchored_a
                and event.b_token not in anchored_b
                and component_of_a.get(event.a_token) == component
            ), None)
            if chosen is not None:
                break
        if chosen is None:
            chosen = next((
                event for event in events
                if event.a_token not in anchored_a and event.b_token not in anchored_b
            ), None)
        if chosen is None:
            break
        anchored_a.add(chosen.a_token)
        anchored_b.add(chosen.b_token)
        selected.append(TypedAnchor(
            chosen.a_token, chosen.b_token, chosen.provenance,
        ))
    return tuple(selected)
