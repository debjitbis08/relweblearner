"""Finite T1 extension search and T4/T7 target projection interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar

from .types import (
    ExtensionCardinality,
    TargetCardinality,
    canonical_digest,
)

SolutionT = TypeVar("SolutionT")


@dataclass(frozen=True, slots=True)
class SolverLimits:
    max_search_nodes: int = 1_000_000

    def __post_init__(self) -> None:
        if self.max_search_nodes <= 0:
            raise ValueError("max_search_nodes must be positive")


@dataclass(frozen=True, slots=True)
class CandidateSummary:
    value_id: str
    provenance_digest: str


@dataclass(frozen=True, slots=True)
class VariableDomainSummary:
    variable_id: str
    candidates: tuple[CandidateSummary, ...]


@dataclass(frozen=True, slots=True)
class ExhaustionSummary:
    variable_order: tuple[str, ...]
    candidate_domains: tuple[VariableDomainSummary, ...]
    constraint_counts: tuple[tuple[str, int], ...]
    explored_nodes: int
    exhausted: bool
    solution_count: int
    solution_digest: str | None
    limit_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ExtensionClassification(Generic[SolutionT]):
    verdict: ExtensionCardinality
    solutions: tuple[SolutionT, ...]
    exhaustion: ExhaustionSummary


@dataclass(frozen=True, slots=True)
class TargetWitness:
    value: str
    solution_digest: str


@dataclass(frozen=True, slots=True)
class TargetProjection:
    target_id: str
    output_values: tuple[str, ...]
    witnesses: tuple[TargetWitness, ...]


@dataclass(frozen=True, slots=True)
class TargetClassification:
    verdict: TargetCardinality
    projection: TargetProjection


class FiniteExtensionProblem(Protocol[SolutionT]):
    """Adapter contract for deterministic finite T1 backtracking."""

    @property
    def variable_order(self) -> tuple[str, ...]: ...

    @property
    def domain_summaries(self) -> tuple[VariableDomainSummary, ...]: ...

    @property
    def constraint_counts(self) -> tuple[tuple[str, int], ...]: ...

    def domain(self, variable_id: str) -> tuple[Any, ...]: ...

    def consistent(self, assignment: Mapping[str, Any]) -> bool: ...

    def materialize(self, assignment: Mapping[str, Any]) -> SolutionT: ...


def classify_extensions(
    problem: FiniteExtensionProblem[SolutionT],
    *,
    limits: SolverLimits = SolverLimits(),
) -> ExtensionClassification[SolutionT]:
    """Exhaust a finite CSP, returning UNKNOWN if the declared limit is hit."""
    order = problem.variable_order
    if len(set(order)) != len(order):
        raise ValueError("extension problem variable ids must be unique")
    summaries = problem.domain_summaries
    if tuple(summary.variable_id for summary in summaries) != order:
        raise ValueError("domain summaries must follow the declared variable order")

    assignment: dict[str, Any] = {}
    solutions: list[SolutionT] = []
    explored_nodes = 0
    exhausted = True

    def search(position: int) -> None:
        nonlocal explored_nodes, exhausted
        if explored_nodes >= limits.max_search_nodes:
            exhausted = False
            return
        explored_nodes += 1
        if position == len(order):
            solutions.append(problem.materialize(assignment))
            return
        variable = order[position]
        for candidate in problem.domain(variable):
            assignment[variable] = candidate
            if problem.consistent(assignment):
                search(position + 1)
            assignment.pop(variable, None)
            if not exhausted:
                return

    search(0)
    if exhausted:
        count = len(solutions)
        if count == 0:
            verdict = ExtensionCardinality.EMPTY
        elif count == 1:
            verdict = ExtensionCardinality.SINGLETON
        else:
            verdict = ExtensionCardinality.MANY
        solution_digest = canonical_digest(tuple(solutions))
        limit_reason = None
    else:
        verdict = ExtensionCardinality.UNKNOWN
        solution_digest = None
        limit_reason = "max_search_nodes"

    summary = ExhaustionSummary(
        variable_order=order,
        candidate_domains=summaries,
        constraint_counts=problem.constraint_counts,
        explored_nodes=explored_nodes,
        exhausted=exhausted,
        solution_count=len(solutions),
        solution_digest=solution_digest,
        limit_reason=limit_reason,
    )
    return ExtensionClassification(verdict, tuple(solutions), summary)


def classify_target(
    extensions: ExtensionClassification[SolutionT],
    *,
    target_id: str,
    project: Callable[[SolutionT], bool],
) -> TargetClassification:
    """Apply the declared identity projection after whole-extension search."""
    if extensions.verdict is ExtensionCardinality.UNKNOWN:
        return TargetClassification(
            TargetCardinality.UNKNOWN, TargetProjection(target_id, (), ()),
        )
    if extensions.verdict is ExtensionCardinality.EMPTY:
        return TargetClassification(
            TargetCardinality.EMPTY, TargetProjection(target_id, (), ()),
        )

    first_witness: dict[bool, TargetWitness] = {}
    for solution in extensions.solutions:
        value = bool(project(solution))
        first_witness.setdefault(value, TargetWitness(
            "IDENTICAL" if value else "DISTINCT",
            canonical_digest(solution),
        ))
    values = tuple(
        label for value, label in ((True, "IDENTICAL"), (False, "DISTINCT"))
        if value in first_witness
    )
    witnesses = tuple(first_witness[value] for value in (True, False)
                      if value in first_witness)
    if set(first_witness) == {True}:
        verdict = TargetCardinality.IDENTICAL
    elif set(first_witness) == {False}:
        verdict = TargetCardinality.DISTINCT
    else:
        verdict = TargetCardinality.MANY
    return TargetClassification(
        verdict, TargetProjection(target_id, values, witnesses),
    )
