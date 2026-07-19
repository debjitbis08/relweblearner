"""G1 structured observations, support closure, and exact GraphLog CSP."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from ...certification.extensions import (
    CandidateSummary,
    ExtensionClassification,
    FiniteExtensionProblem,
    SolverLimits,
    TargetClassification,
    VariableDomainSummary,
    classify_extensions as solve_extensions,
    classify_target as project_target,
)
from ...certification.provenance import (
    DerivationRef,
    NormalizedProvenance,
    normalize_provenance,
)
from ...certification.types import canonical_digest
from .ingest import (
    OpaqueEdgeEvent,
    OpaqueToken,
    RuntimeViewBundle,
    TypedAnchor,
)
from .spec import DEFAULT_SPEC, GraphLogCertifiedSpec


TRIANGLE_PROPAGATION_VERSION = "graphlog/triangle-propagation/v1"


class DomainValue(str, Enum):
    UNMAPPED = "UNMAPPED"


@dataclass(frozen=True, slots=True)
class TriangleFact:
    positions: tuple[OpaqueToken, OpaqueToken, OpaqueToken]
    support: int
    provenance: NormalizedProvenance

    def __post_init__(self) -> None:
        if self.support <= 0:
            raise ValueError("triangle support must be positive")
        views = {token.view_id for token in self.positions}
        if len(views) != 1:
            raise ValueError("a triangle fact belongs to exactly one view")

    @property
    def fact_id(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class ExactNegativeIdentity:
    a_token: OpaqueToken
    b_token: OpaqueToken
    admission_id: str
    provenance: NormalizedProvenance

    def __post_init__(self) -> None:
        if self.a_token.view_id != "A" or self.b_token.view_id != "B":
            raise ValueError("negative identity requires one A and one B token")
        if not self.admission_id:
            raise ValueError("exact negative identity requires an admission id")
        if not self.provenance.observations:
            raise ValueError("exact negative identity requires observation provenance")


@dataclass(frozen=True, slots=True)
class ObservationFamily:
    schema_version: str
    dataset_version: str
    world: str
    triangles_a: tuple[TriangleFact, ...]
    triangles_b: tuple[TriangleFact, ...]
    anchors: tuple[TypedAnchor, ...]
    exact_negative_identities: tuple[ExactNegativeIdentity, ...]
    relation_tokens_a: tuple[OpaqueToken, ...]
    relation_tokens_b: tuple[OpaqueToken, ...]


@dataclass(frozen=True, slots=True)
class CandidateIdentity:
    a_token: OpaqueToken
    b_token: OpaqueToken
    support_kind: str
    propagation_rule: str
    provenance: NormalizedProvenance

    def __post_init__(self) -> None:
        if self.a_token.view_id != "A" or self.b_token.view_id != "B":
            raise ValueError("candidate identity requires one A and one B token")
        if self.support_kind not in {"anchor", "triangle_propagation"}:
            raise ValueError(f"unsupported candidate kind {self.support_kind!r}")

    @property
    def candidate_id(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class CountingScope:
    scope_version: str
    extension_semantics_version: str
    world: str
    triangles_a: tuple[TriangleFact, ...]
    triangles_b: tuple[TriangleFact, ...]
    candidate_identities: tuple[CandidateIdentity, ...]
    scoped_a_tokens: tuple[OpaqueToken, ...]
    scoped_b_tokens: tuple[OpaqueToken, ...]
    support_closed: bool

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True, slots=True)
class CrossViewRelationIdentity:
    a_token: OpaqueToken
    b_token: OpaqueToken

    def __post_init__(self) -> None:
        if self.a_token.view_id != "A" or self.b_token.view_id != "B":
            raise ValueError("identity target requires one A and one B token")

    @property
    def target_id(self) -> str:
        return f"CrossViewRelationIdentity({self.a_token.value},{self.b_token.value})"


@dataclass(frozen=True, slots=True)
class IdentityExtension:
    pairs: tuple[tuple[OpaqueToken, OpaqueToken], ...]

    def __post_init__(self) -> None:
        left = [a for a, _b in self.pairs]
        right = [b for _a, b in self.pairs]
        if len(set(left)) != len(left) or len(set(right)) != len(right):
            raise ValueError("identity extension must be a partial bijection")

    def contains(self, target: CrossViewRelationIdentity) -> bool:
        return (target.a_token, target.b_token) in self.pairs

    def as_dict(self) -> dict[OpaqueToken, OpaqueToken]:
        return dict(self.pairs)


def _mine_triangles(episodes: Iterable) -> tuple[TriangleFact, ...]:
    counts: Counter[tuple[OpaqueToken, OpaqueToken, OpaqueToken]] = Counter()
    refs: dict[
        tuple[OpaqueToken, OpaqueToken, OpaqueToken], set
    ] = defaultdict(set)
    for episode in episodes:
        out_index: dict[int, list[OpaqueEdgeEvent]] = defaultdict(list)
        direct: dict[tuple[int, int], list[OpaqueEdgeEvent]] = defaultdict(list)
        for edge in episode.edges:
            out_index[edge.tail].append(edge)
            direct[(edge.tail, edge.head)].append(edge)
        for first in episode.edges:
            for second in out_index[first.head]:
                if second.head == first.tail:
                    continue
                for head in direct.get((first.tail, second.head), ()):
                    triple = (first.relation, second.relation, head.relation)
                    counts[triple] += 1
                    refs[triple].update((
                        first.observation, second.observation, head.observation,
                    ))
    return tuple(
        TriangleFact(triple, counts[triple], normalize_provenance(refs[triple]))
        for triple in sorted(counts)
    )


def build_observations(
    runtime: RuntimeViewBundle,
    anchors: Iterable[TypedAnchor] = (),
    exact_negative_identities: Iterable[ExactNegativeIdentity] = (),
) -> ObservationFamily:
    """Build A_G from opaque runtime inputs; evaluation keys are unaccepted."""
    view_a, view_b = runtime.opaque_views
    tokens_a = tuple(sorted({
        edge.relation for episode in view_a.train_episodes for edge in episode.edges
    }))
    tokens_b = tuple(sorted({
        edge.relation for episode in view_b.train_episodes for edge in episode.edges
    }))
    anchors_tuple = tuple(anchors)
    negatives_tuple = tuple(exact_negative_identities)
    overlap_by_pair: dict[
        tuple[OpaqueToken, OpaqueToken], list
    ] = defaultdict(list)
    for event in runtime.opaque_overlap_events:
        overlap_by_pair[(event.a_token, event.b_token)].append(event)
    for anchor in anchors_tuple:
        if not isinstance(anchor, TypedAnchor):
            raise TypeError("anchors must be TypedAnchor values")
        witnesses = overlap_by_pair.get((anchor.a_token, anchor.b_token), ())
        if not any(
            event.a_observation in anchor.provenance.observations
            and event.b_observation in anchor.provenance.observations
            for event in witnesses
        ):
            raise ValueError("anchor is not backed by an opaque co-witness event")
    if not all(isinstance(fact, ExactNegativeIdentity) for fact in negatives_tuple):
        raise TypeError("exact negatives must be ExactNegativeIdentity values")
    return ObservationFamily(
        schema_version=runtime.schema_version,
        dataset_version=runtime.dataset_version,
        world=runtime.world,
        triangles_a=_mine_triangles(view_a.train_episodes),
        triangles_b=_mine_triangles(view_b.train_episodes),
        anchors=anchors_tuple,
        exact_negative_identities=negatives_tuple,
        relation_tokens_a=tokens_a,
        relation_tokens_b=tokens_b,
    )


def triangle_components(
    triangles: Iterable[TriangleFact],
) -> dict[OpaqueToken, int]:
    """Opaque token components with each observed triangle as a clique."""
    parent: dict[OpaqueToken, OpaqueToken] = {}

    def find(token: OpaqueToken) -> OpaqueToken:
        parent.setdefault(token, token)
        while parent[token] != token:
            parent[token] = parent[parent[token]]
            token = parent[token]
        return token

    for triangle in triangles:
        first, second, third = triangle.positions
        root = find(first)
        parent[find(second)] = root
        parent[find(third)] = root
    roots = sorted({find(token) for token in parent})
    component_id = {root: index for index, root in enumerate(roots)}
    return {token: component_id[find(token)] for token in sorted(parent)}


def _candidate_closure(observations: ObservationFamily) -> tuple[CandidateIdentity, ...]:
    candidates: dict[tuple[OpaqueToken, OpaqueToken], CandidateIdentity] = {}
    for anchor in observations.anchors:
        pair = (anchor.a_token, anchor.b_token)
        candidate = CandidateIdentity(
            *pair,
            support_kind="anchor",
            propagation_rule="observed_co_witness/v1",
            provenance=anchor.provenance,
        )
        # Repeated witnesses normalize into one model-side candidate while
        # retaining every immutable source ref.
        if pair in candidates:
            old = candidates[pair]
            candidate = CandidateIdentity(
                *pair,
                support_kind="anchor",
                propagation_rule="observed_co_witness/v1",
                provenance=normalize_provenance(
                    (*old.provenance.observations, *candidate.provenance.observations),
                    (*old.provenance.derivations, *candidate.provenance.derivations),
                ),
            )
        candidates[pair] = candidate

    changed = True
    while changed:
        changed = False
        supported_pairs = set(candidates)
        for triangle_a in observations.triangles_a:
            for triangle_b in observations.triangles_b:
                for position in range(3):
                    other_positions = tuple(i for i in range(3) if i != position)
                    required = tuple(
                        (triangle_a.positions[i], triangle_b.positions[i])
                        for i in other_positions
                    )
                    if not all(pair in supported_pairs for pair in required):
                        continue
                    pair = (
                        triangle_a.positions[position],
                        triangle_b.positions[position],
                    )
                    if pair in candidates:
                        continue
                    parents = (
                        triangle_a.fact_id,
                        triangle_b.fact_id,
                        *(candidates[required_pair].candidate_id
                          for required_pair in required),
                    )
                    derivation = DerivationRef(
                        TRIANGLE_PROPAGATION_VERSION,
                        f"matched_triangle_position_{position}",
                        parents,
                    )
                    supporting = [candidates[required_pair] for required_pair in required]
                    candidates[pair] = CandidateIdentity(
                        *pair,
                        support_kind="triangle_propagation",
                        propagation_rule=TRIANGLE_PROPAGATION_VERSION,
                        provenance=normalize_provenance(
                            (
                                *triangle_a.provenance.observations,
                                *triangle_b.provenance.observations,
                                *(ref for candidate in supporting
                                  for ref in candidate.provenance.observations),
                            ),
                            (
                                *(ref for candidate in supporting
                                  for ref in candidate.provenance.derivations),
                                derivation,
                            ),
                        ),
                    )
                    changed = True
        # New facts are used only on the next fixed-point pass.  This makes
        # witness selection deterministic and independent of loop traversal.
    return tuple(candidates[pair] for pair in sorted(candidates))


def build_scope(
    observations: ObservationFamily,
    *,
    spec: GraphLogCertifiedSpec = DEFAULT_SPEC,
) -> CountingScope:
    candidates = _candidate_closure(observations)
    scoped_a = tuple(sorted({candidate.a_token for candidate in candidates}))
    scoped_b = tuple(sorted({candidate.b_token for candidate in candidates}))
    scope = CountingScope(
        scope_version=spec.scope_version,
        extension_semantics_version=spec.extension_semantics_version,
        world=observations.world,
        triangles_a=observations.triangles_a,
        triangles_b=observations.triangles_b,
        candidate_identities=candidates,
        scoped_a_tokens=scoped_a,
        scoped_b_tokens=scoped_b,
        support_closed=True,
    )
    if not check_support_closed(scope, observations):
        raise ValueError("constructed GraphLog scope is not support closed")
    return scope


def check_support_closed(scope: CountingScope, observations: ObservationFamily) -> bool:
    if scope.world != observations.world:
        return False
    expected = _candidate_closure(observations)
    return (
        scope.support_closed
        and bool(scope.extension_semantics_version)
        and scope.triangles_a == observations.triangles_a
        and scope.triangles_b == observations.triangles_b
        and scope.candidate_identities == expected
        and scope.scoped_a_tokens
        == tuple(sorted({candidate.a_token for candidate in expected}))
        and scope.scoped_b_tokens
        == tuple(sorted({candidate.b_token for candidate in expected}))
    )


class GraphLogExtensionProblem(FiniteExtensionProblem[IdentityExtension]):
    def __init__(self, observations: ObservationFamily, scope: CountingScope):
        if not check_support_closed(scope, observations):
            raise ValueError("extension classification requires a support-closed scope")
        if (
            scope.extension_semantics_version
            != DEFAULT_SPEC.extension_semantics_version
        ):
            raise ValueError("unsupported extension semantics version")
        self._observations = observations
        self._scope = scope
        self._candidate_by_pair = {
            (candidate.a_token, candidate.b_token): candidate
            for candidate in scope.candidate_identities
        }
        domains: dict[OpaqueToken, set[OpaqueToken]] = defaultdict(set)
        for candidate in scope.candidate_identities:
            domains[candidate.a_token].add(candidate.b_token)

        anchored: dict[OpaqueToken, set[OpaqueToken]] = defaultdict(set)
        for anchor in observations.anchors:
            anchored[anchor.a_token].add(anchor.b_token)
        negatives = {
            (negative.a_token, negative.b_token)
            for negative in observations.exact_negative_identities
        }
        self._anchored_tokens = frozenset(anchored)
        self._positive_domains: dict[OpaqueToken, tuple[OpaqueToken, ...]] = {}
        self._domains: dict[
            OpaqueToken, tuple[OpaqueToken | DomainValue, ...]
        ] = {}
        for token in scope.scoped_a_tokens:
            values = domains[token]
            if token in anchored:
                values = values & anchored[token]
                if len(anchored[token]) > 1:
                    values = set()
            values = {value for value in values if (token, value) not in negatives}
            positive_values = tuple(sorted(values))
            self._positive_domains[token] = positive_values
            if token in anchored:
                self._domains[token] = positive_values
            else:
                self._domains[token] = (*positive_values, DomainValue.UNMAPPED)

        self._token_by_id = {
            self._variable_id(token): token for token in scope.scoped_a_tokens
        }
        ordered_tokens = sorted(
            scope.scoped_a_tokens,
            key=lambda token: (len(self._domains[token]), token.value),
        )
        self._order = tuple(self._variable_id(token) for token in ordered_tokens)
        self._a_triangle_set = {triangle.positions for triangle in scope.triangles_a}
        self._b_triangle_set = {triangle.positions for triangle in scope.triangles_b}
        self._scoped_a_triangles = tuple(
            triangle for triangle in self._a_triangle_set
            if all(token in self._domains for token in triangle)
        )

    @staticmethod
    def _variable_id(token: OpaqueToken) -> str:
        return f"A:{token.value}"

    @property
    def variable_order(self) -> tuple[str, ...]:
        return self._order

    @property
    def domain_summaries(self) -> tuple[VariableDomainSummary, ...]:
        summaries = []
        for variable_id in self._order:
            token = self._token_by_id[variable_id]
            candidates = tuple(
                self._candidate_summary(token, value)
                for value in self._domains[token]
            )
            summaries.append(VariableDomainSummary(variable_id, candidates))
        return tuple(summaries)

    @property
    def constraint_counts(self) -> tuple[tuple[str, int], ...]:
        n_variables = len(self._order)
        scoped_b_triangles = sum(
            all(token in self._scope.scoped_b_tokens for token in triangle)
            for triangle in self._b_triangle_set
        )
        return (
            ("anchor_containment", len(self._observations.anchors)),
            ("exact_negative_identity", len(self._observations.exact_negative_identities)),
            ("injectivity", n_variables * (n_variables - 1) // 2),
            ("a_triangle_preservation", len(self._scoped_a_triangles)),
            ("b_triangle_preservation", scoped_b_triangles),
            ("inclusion_maximality", n_variables - len(self._anchored_tokens)),
        )

    def _candidate_summary(
        self, token: OpaqueToken, value: OpaqueToken | DomainValue,
    ) -> CandidateSummary:
        if value is DomainValue.UNMAPPED:
            return CandidateSummary(
                DomainValue.UNMAPPED.value,
                canonical_digest(("empty_overlap_candidate", token)),
            )
        return CandidateSummary(
            f"B:{value.value}",
            canonical_digest(self._candidate_by_pair[(token, value)].provenance),
        )

    def domain(self, variable_id: str) -> tuple[OpaqueToken | DomainValue, ...]:
        return self._domains[self._token_by_id[variable_id]]

    def _legal_mapping(self, mapping: Mapping[OpaqueToken, OpaqueToken]) -> bool:
        if len(set(mapping.values())) != len(mapping):
            return False
        for triangle in self._scoped_a_triangles:
            if all(token in mapping for token in triangle):
                if tuple(mapping[token] for token in triangle) not in self._b_triangle_set:
                    return False

        inverse = {value: token for token, value in mapping.items()}
        for triangle in self._b_triangle_set:
            if all(token in inverse for token in triangle):
                if tuple(inverse[token] for token in triangle) not in self._a_triangle_set:
                    return False
        return True

    def consistent(
        self, assignment: Mapping[str, OpaqueToken | DomainValue],
    ) -> bool:
        mapping = {
            self._token_by_id[variable_id]: value
            for variable_id, value in assignment.items()
            if value is not DomainValue.UNMAPPED
        }
        if not self._legal_mapping(mapping):
            return False

        # A complete legal partial map counts only when its graph is
        # inclusion-maximal.  If a strict legal supermap exists, adding any
        # one of its new pairs is already legal: the composition constraints
        # are preservation constraints and cannot be repaired by later pairs.
        if len(assignment) == len(self._order):
            used = set(mapping.values())
            for variable_id, value in assignment.items():
                if value is not DomainValue.UNMAPPED:
                    continue
                token = self._token_by_id[variable_id]
                for candidate in self._positive_domains[token]:
                    if candidate in used:
                        continue
                    trial = dict(mapping)
                    trial[token] = candidate
                    if self._legal_mapping(trial):
                        return False
        return True

    def materialize(
        self, assignment: Mapping[str, OpaqueToken | DomainValue],
    ) -> IdentityExtension:
        pairs = tuple(sorted(
            (self._token_by_id[variable_id], value)
            for variable_id, value in assignment.items()
            if value is not DomainValue.UNMAPPED
        ))
        return IdentityExtension(pairs)


def classify_extensions(
    observations: ObservationFamily,
    scope: CountingScope,
    *,
    limits: SolverLimits = SolverLimits(),
) -> ExtensionClassification[IdentityExtension]:
    return solve_extensions(
        GraphLogExtensionProblem(observations, scope), limits=limits,
    )


def classify_target(
    observations: ObservationFamily,
    scope: CountingScope,
    target: CrossViewRelationIdentity,
    *,
    extensions: ExtensionClassification[IdentityExtension] | None = None,
    limits: SolverLimits = SolverLimits(),
) -> TargetClassification:
    whole = extensions or classify_extensions(observations, scope, limits=limits)
    return project_target(
        whole, target_id=target.target_id, project=lambda solution: solution.contains(target),
    )
