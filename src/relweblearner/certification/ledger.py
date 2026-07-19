"""Append-only commitment events, exact retraction, and deterministic replay."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .provenance import DerivationRef, NormalizedProvenance, normalize_provenance
from .t7 import CommitmentOutcome, StableCommitmentCertificate
from .types import canonical_digest


class LedgerEventKind(str, Enum):
    COMMIT = "COMMIT"
    EXCLUSION = "EXCLUSION"
    ABSTAIN = "ABSTAIN"
    REJECT = "REJECT"
    RETRACT = "RETRACT"


@dataclass(frozen=True, slots=True)
class LedgerEventBody:
    ledger_version: str
    sequence: int
    kind: LedgerEventKind
    target_id: str
    commitment: str | None
    certificate_id: str
    source_observation_ids: tuple[str, ...]
    depends_on_event_ids: tuple[str, ...]
    retracts_event_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    body: LedgerEventBody
    event_id: str

    def __post_init__(self) -> None:
        if self.event_id != canonical_digest(self.body):
            raise ValueError("ledger event id does not match its canonical body")


@dataclass(frozen=True, slots=True)
class ReplayState:
    live_events: tuple[LedgerEvent, ...]
    live_commitments: tuple[tuple[str, str, str], ...]


def _event(body: LedgerEventBody) -> LedgerEvent:
    return LedgerEvent(body, canonical_digest(body))


def _source_ids(provenance: NormalizedProvenance) -> tuple[str, ...]:
    return tuple(sorted(canonical_digest(ref) for ref in provenance.observations))


def replay_ledger(
    events: Iterable[LedgerEvent],
    *,
    active_observation_ids: Iterable[str] | None = None,
) -> ReplayState:
    """Replay event bytes in sequence, recursively invalidating dependencies."""
    ordered = tuple(events)
    active_sources = (
        None if active_observation_ids is None else frozenset(active_observation_ids)
    )
    seen: dict[str, LedgerEvent] = {}
    live: dict[str, LedgerEvent] = {}

    def remove_with_dependents(event_id: str) -> None:
        pending = [event_id]
        while pending:
            removed = pending.pop()
            live.pop(removed, None)
            pending.extend(
                candidate_id for candidate_id, candidate in tuple(live.items())
                if removed in candidate.body.depends_on_event_ids
            )

    for expected_sequence, event in enumerate(ordered):
        body = event.body
        if body.sequence != expected_sequence:
            raise ValueError("ledger sequence is not contiguous")
        if event.event_id in seen:
            raise ValueError("ledger event ids must be unique")
        if any(dependency not in seen for dependency in body.depends_on_event_ids):
            raise ValueError("ledger event names a future or unknown dependency")
        if body.retracts_event_id is not None and body.retracts_event_id not in seen:
            raise ValueError("retraction names an unknown event")
        seen[event.event_id] = event
        if body.kind in {LedgerEventKind.COMMIT, LedgerEventKind.EXCLUSION}:
            if not body.source_observation_ids:
                raise ValueError("live commitments require observation provenance")
            sources_live = (
                active_sources is None
                or set(body.source_observation_ids).issubset(active_sources)
            )
            dependencies_live = all(
                dependency in live for dependency in body.depends_on_event_ids
            )
            if sources_live and dependencies_live:
                live[event.event_id] = event
        elif body.kind is LedgerEventKind.RETRACT:
            assert body.retracts_event_id is not None
            remove_with_dependents(body.retracts_event_id)
    live_events = tuple(sorted(live.values(), key=lambda event: event.body.sequence))
    commitments = tuple(
        (event.body.target_id, event.body.commitment or "", event.event_id)
        for event in live_events
    )
    return ReplayState(live_events, commitments)


@dataclass(frozen=True, slots=True)
class CommitmentLedger:
    version: str = "certified-commitment-ledger/v1"
    events: tuple[LedgerEvent, ...] = ()

    @property
    def digest(self) -> str:
        return canonical_digest(self)

    @property
    def state(self) -> ReplayState:
        return replay_ledger(self.events)

    def append_certificate(
        self,
        certificate: StableCommitmentCertificate,
        *,
        depends_on_event_ids: Iterable[str] = (),
    ) -> "CommitmentLedger":
        kind = {
            CommitmentOutcome.COMMIT: LedgerEventKind.COMMIT,
            CommitmentOutcome.EXCLUSION: LedgerEventKind.EXCLUSION,
            CommitmentOutcome.ABSTAIN: LedgerEventKind.ABSTAIN,
            CommitmentOutcome.REJECT: LedgerEventKind.REJECT,
        }[certificate.outcome]
        dependencies = tuple(sorted(set(depends_on_event_ids)))
        sources = _source_ids(certificate.provenance)
        if kind in {LedgerEventKind.COMMIT, LedgerEventKind.EXCLUSION} and not sources:
            raise ValueError("live commitments require observation provenance")
        body = LedgerEventBody(
            ledger_version=self.version,
            sequence=len(self.events),
            kind=kind,
            target_id=certificate.target_id,
            commitment=certificate.commitment,
            certificate_id=certificate.certificate_id,
            source_observation_ids=sources,
            depends_on_event_ids=dependencies,
            retracts_event_id=None,
            reason=certificate.code,
        )
        result = CommitmentLedger(self.version, (*self.events, _event(body)))
        replay_ledger(result.events)
        return result

    def retract_observations(
        self,
        removed_observation_ids: Iterable[str],
        *,
        reason: str = "OBSERVATION_RETRACTED",
    ) -> "CommitmentLedger":
        removed = frozenset(removed_observation_ids)
        live = self.state.live_events
        invalid: set[str] = {
            event.event_id for event in live
            if removed.intersection(event.body.source_observation_ids)
        }
        changed = True
        while changed:
            changed = False
            for event in live:
                if event.event_id not in invalid and invalid.intersection(
                    event.body.depends_on_event_ids
                ):
                    invalid.add(event.event_id)
                    changed = True
        ledger = self
        by_id = {event.event_id: event for event in live}
        for event_id in sorted(invalid, key=lambda item: by_id[item].body.sequence):
            target = by_id[event_id]
            body = LedgerEventBody(
                ledger_version=self.version,
                sequence=len(ledger.events),
                kind=LedgerEventKind.RETRACT,
                target_id=target.body.target_id,
                commitment=None,
                certificate_id="retraction/no-certificate",
                source_observation_ids=(),
                depends_on_event_ids=(),
                retracts_event_id=event_id,
                reason=reason,
            )
            ledger = CommitmentLedger(
                ledger.version, (*ledger.events, _event(body))
            )
        replay_ledger(ledger.events)
        return ledger


def feedback_provenance(
    certificate: StableCommitmentCertificate,
    *,
    parent_event_id: str,
    rule_version: str = "certified-feedback/v1",
) -> NormalizedProvenance:
    """Derived feedback retains sources and cannot manufacture a P1 origin."""
    derivation = DerivationRef(
        rule_version,
        "certified_feedback",
        (certificate.certificate_id, parent_event_id),
    )
    return normalize_provenance(
        certificate.provenance.observations,
        (*certificate.provenance.derivations, derivation),
    )
