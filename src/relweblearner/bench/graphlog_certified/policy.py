"""GraphLog P1 verdicts and the fail-closed P2 evidence adapter."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ...certification.extensions import TargetClassification
from ...certification.provenance import NormalizedProvenance
from ...certification.types import TargetCardinality
from .ingest import OpaqueToken
from .model import (
    CandidateIdentity,
    CountingScope,
    CrossViewRelationIdentity,
    ExactNegativeIdentity,
    ObservationFamily,
)


class CommitmentValue(str, Enum):
    IDENTICAL = "IDENTICAL"
    DISTINCT = "DISTINCT"


class PolicyCode(str, Enum):
    PERMIT = "PERMIT"
    TARGET_NOT_SINGLETON = "TARGET_NOT_SINGLETON"
    P1_INSUFFICIENT_ORIGINS = "P1_INSUFFICIENT_ORIGINS"
    P1_UNSUPPORTED_IDENTITY = "P1_UNSUPPORTED_IDENTITY"
    P2_EXACT_CONFLICT = "P2_EXACT_CONFLICT"


@dataclass(frozen=True, slots=True)
class PolicyVerdict:
    permitted: bool
    code: PolicyCode
    commitment: CommitmentValue
    origin_ids: tuple[tuple[str, str], ...]
    exact_conflict_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DetectorOutput:
    detector_version: str
    score: float
    provenance: NormalizedProvenance

    def __post_init__(self) -> None:
        if not self.detector_version:
            raise ValueError("detector output requires a version")
        if not math.isfinite(self.score):
            raise ValueError("detector score must be finite")


@dataclass(frozen=True, slots=True)
class P2AdmissionVerdict:
    admitted: bool
    code: str
    exact_fact: ExactNegativeIdentity | None


def admit_exact_negative_observation(
    a_token: OpaqueToken,
    b_token: OpaqueToken,
    *,
    admission_id: str,
    provenance: NormalizedProvenance,
) -> P2AdmissionVerdict:
    """Admit an already-exact negative fact; this does no score conversion."""
    if not provenance.observations:
        raise ValueError("an exact negative observation requires source provenance")
    fact = ExactNegativeIdentity(a_token, b_token, admission_id, provenance)
    return P2AdmissionVerdict(True, "EXACT_OBSERVATION", fact)


def adapt_detector_output(
    _a_token: OpaqueToken,
    _b_token: OpaqueToken,
    detector_output: DetectorOutput,
) -> P2AdmissionVerdict:
    """GraphLog has no P2 detector-to-exact discharge; always refuse it."""
    return P2AdmissionVerdict(
        False,
        f"UNADMITTED_DETECTOR:{detector_output.detector_version}",
        None,
    )


def _candidate(
    scope: CountingScope, target: CrossViewRelationIdentity,
) -> CandidateIdentity | None:
    return next((
        candidate for candidate in scope.candidate_identities
        if candidate.a_token == target.a_token and candidate.b_token == target.b_token
    ), None)


def permit(
    observations: ObservationFamily,
    scope: CountingScope,
    target: CrossViewRelationIdentity,
    target_classification: TargetClassification,
    commitment: CommitmentValue,
) -> PolicyVerdict:
    """Apply P2 and P1 after structural target classification."""
    expected = (
        TargetCardinality.IDENTICAL
        if commitment is CommitmentValue.IDENTICAL
        else TargetCardinality.DISTINCT
    )
    if target_classification.verdict is not expected:
        return PolicyVerdict(
            False, PolicyCode.TARGET_NOT_SINGLETON, commitment, (), (),
        )

    conflicts = tuple(sorted(
        negative.admission_id
        for negative in observations.exact_negative_identities
        if negative.a_token == target.a_token and negative.b_token == target.b_token
    ))
    if commitment is CommitmentValue.IDENTICAL and conflicts:
        return PolicyVerdict(
            False, PolicyCode.P2_EXACT_CONFLICT, commitment, (), conflicts,
        )

    if commitment is CommitmentValue.IDENTICAL:
        candidate = _candidate(scope, target)
        if candidate is None:
            return PolicyVerdict(
                False, PolicyCode.P1_UNSUPPORTED_IDENTITY, commitment, (), (),
            )
        origins = tuple(sorted(candidate.provenance.origin_ids))
        if len(origins) < 2:
            return PolicyVerdict(
                False,
                PolicyCode.P1_INSUFFICIENT_ORIGINS,
                commitment,
                origins,
                (),
            )
        return PolicyVerdict(
            True, PolicyCode.PERMIT, commitment, origins, (),
        )

    # A negative singleton never feeds the merge map.  G1 allows it to be
    # persisted as a structural exclusion without inventing P1 support.
    return PolicyVerdict(True, PolicyCode.PERMIT, commitment, (), conflicts)
