"""Evaluation-only access to sealed GraphLog labels and oracle structure.

The runtime bundle intentionally has no route back to this payload.  This
module exposes only scored questions; it never exports the stored maps.
"""

from __future__ import annotations

from types import MappingProxyType
from dataclasses import dataclass
from typing import Mapping, Sequence


class EvaluationKey:
    """Opaque capability holding data forbidden to the certified runtime.

    Construction is confined to the trusted ingest boundary.  The object has
    no dataclass fields, iterator, serializer, or diagnostic representation.
    """

    __slots__ = ("__perm_a", "__perm_b", "__query_targets", "__oracle_rules")

    def __init__(
        self,
        marker: object,
        *,
        perm_a: Mapping[str, str],
        perm_b: Mapping[str, str],
        query_targets: Sequence[str],
        oracle_rules: Mapping[tuple[str, str], str],
    ) -> None:
        if marker is not _INGEST_MARKER:
            raise TypeError("EvaluationKey can only be created by trusted ingest")
        self.__perm_a = MappingProxyType(dict(perm_a))
        self.__perm_b = MappingProxyType(dict(perm_b))
        self.__query_targets = tuple(query_targets)
        self.__oracle_rules = MappingProxyType(dict(oracle_rules))

    def __repr__(self) -> str:
        return "EvaluationKey(<sealed>)"


_INGEST_MARKER = object()


def _seal_evaluation_key(
    *,
    perm_a: Mapping[str, str],
    perm_b: Mapping[str, str],
    query_targets: Sequence[str],
    oracle_rules: Mapping[tuple[str, str], str],
) -> EvaluationKey:
    """Trusted-boundary constructor; not part of the runtime API."""
    return EvaluationKey(
        _INGEST_MARKER,
        perm_a=perm_a,
        perm_b=perm_b,
        query_targets=query_targets,
        oracle_rules=oracle_rules,
    )


def is_true_identity(key: EvaluationKey, a_token: str, b_token: str) -> bool:
    """Score one opaque cross-view identity without disclosing either map."""
    inv_a = {opaque: raw for raw, opaque in key._EvaluationKey__perm_a.items()}
    inv_b = {opaque: raw for raw, opaque in key._EvaluationKey__perm_b.items()}
    return inv_a.get(a_token) is not None and inv_a.get(a_token) == inv_b.get(b_token)


def score_query_predictions(key: EvaluationKey, predictions: Sequence[str]) -> dict[str, int]:
    """Score raw-label predictions inside the evaluation boundary."""
    targets = key._EvaluationKey__query_targets
    if len(predictions) != len(targets):
        raise ValueError("prediction count does not match sealed query count")
    correct = sum(got == want for got, want in zip(predictions, targets))
    return {"correct": correct, "total": len(targets)}


@dataclass(frozen=True, slots=True)
class EpisodeEvaluation:
    episode_index: int
    certified_abstained: bool
    certified_correct: bool
    discrete_correct: bool
    graded_correct: bool
    versus_discrete: str
    versus_graded: str


@dataclass(frozen=True, slots=True)
class IdentityEvaluation:
    target_id: str
    raw_a_label: str | None
    raw_b_label: str | None
    true_identity: bool
    outcome: str
    commitment: str | None


@dataclass(frozen=True, slots=True)
class DevelopmentEvaluation:
    version: str
    world: str
    episode_rows: tuple[EpisodeEvaluation, ...]
    identity_rows: tuple[IdentityEvaluation, ...]
    query_summary: tuple[tuple[str, int | float], ...]
    baseline_gate: tuple[tuple[str, object], ...]


def _flip_label(
    certified: bool, baseline: bool, abstained: bool,
) -> str:
    if abstained:
        return "ABSTAIN_BASELINE_CORRECT" if baseline else "ABSTAIN_BASELINE_WRONG"
    if certified and not baseline:
        return "HEAL"
    if baseline and not certified:
        return "BREAK"
    return "BOTH_CORRECT" if certified else "BOTH_WRONG"


def evaluate_development_run(
    key: EvaluationKey,
    *,
    world: str,
    opaque_a_predictions: Sequence[str | None],
    identity_decisions: Sequence[tuple[str, str, str, str, str | None]],
) -> DevelopmentEvaluation:
    """Join certified outputs to frozen baselines inside the gold boundary.

    ``identity_decisions`` rows are ``(target_id, a_token, b_token, outcome,
    commitment)``.  Raw labels and query targets never leave this module
    except in the explicitly evaluation-only artifact returned here.
    """
    if world not in {"rule_20", "rule_27"}:
        raise ValueError("G5 evaluation is frozen to rule_20 and rule_27")
    targets = key._EvaluationKey__query_targets
    if len(opaque_a_predictions) != len(targets):
        raise ValueError("prediction count does not match sealed query count")
    inv_a = {
        opaque: raw for raw, opaque in key._EvaluationKey__perm_a.items()
    }
    inv_b = {
        opaque: raw for raw, opaque in key._EvaluationKey__perm_b.items()
    }
    certified_raw = tuple(
        None if prediction is None else inv_a.get(prediction)
        for prediction in opaque_a_predictions
    )

    # The legacy constructors stay confined to this evaluation-only module.
    # The certified runner receives correctness bits, never their maps,
    # targets, or oracle rules.
    from ..rule20_diag import (
        _discrete_preds,
        _graded_frozen_preds,
        gate,
        setup,
    )

    context = setup(world, seed=0, n_train=150)
    baseline_gate = gate(context)
    if not baseline_gate["pass"]:
        raise ValueError(f"frozen {world} baseline consistency gate failed")
    if tuple(context["targets"]) != tuple(targets):
        raise ValueError("evaluation key and frozen baseline targets differ")
    discrete = _discrete_preds(context, context["rules_ens"], "ensemble")
    graded = _graded_frozen_preds(context)
    rows = []
    for index, (target, prediction, discrete_prediction, graded_prediction) in enumerate(
        zip(targets, certified_raw, discrete, graded, strict=True)
    ):
        certified_correct = prediction == target
        discrete_correct = discrete_prediction == target
        graded_correct = graded_prediction == target
        abstained = prediction is None
        rows.append(EpisodeEvaluation(
            episode_index=index,
            certified_abstained=abstained,
            certified_correct=certified_correct,
            discrete_correct=discrete_correct,
            graded_correct=graded_correct,
            versus_discrete=_flip_label(
                certified_correct, discrete_correct, abstained,
            ),
            versus_graded=_flip_label(
                certified_correct, graded_correct, abstained,
            ),
        ))

    identity_rows = tuple(IdentityEvaluation(
        target_id=target_id,
        raw_a_label=inv_a.get(a_token),
        raw_b_label=inv_b.get(b_token),
        true_identity=(
            inv_a.get(a_token) is not None
            and inv_a.get(a_token) == inv_b.get(b_token)
        ),
        outcome=outcome,
        commitment=commitment,
    ) for target_id, a_token, b_token, outcome, commitment in identity_decisions)
    total = len(rows)
    summary = (
        ("total", total),
        ("certified_correct", sum(row.certified_correct for row in rows)),
        ("certified_accuracy", sum(row.certified_correct for row in rows) / total),
        ("abstentions", sum(row.certified_abstained for row in rows)),
        ("discrete_correct", sum(row.discrete_correct for row in rows)),
        ("discrete_accuracy", sum(row.discrete_correct for row in rows) / total),
        ("graded_correct", sum(row.graded_correct for row in rows)),
        ("graded_accuracy", sum(row.graded_correct for row in rows) / total),
        ("heals_vs_discrete", sum(
            row.versus_discrete == "HEAL" for row in rows
        )),
        ("breaks_vs_discrete", sum(
            row.versus_discrete == "BREAK" for row in rows
        )),
        ("heals_vs_graded", sum(
            row.versus_graded == "HEAL" for row in rows
        )),
        ("breaks_vs_graded", sum(
            row.versus_graded == "BREAK" for row in rows
        )),
    )
    public_gate = tuple(sorted(
        (name, value) for name, value in baseline_gate.items()
        if name != "_graded_preds"
    ))
    return DevelopmentEvaluation(
        "graphlog-certified-development-evaluation/v1",
        world,
        tuple(rows),
        identity_rows,
        summary,
        public_gate,
    )
