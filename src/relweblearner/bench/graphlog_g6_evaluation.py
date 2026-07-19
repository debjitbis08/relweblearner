"""Evaluation-only join for preregistered GraphLog G6 draws.

This module is imported dynamically by the G6 phase adapter only while the
global harness is executing its final ``accuracy`` phase.  It is the sole G6
consumer of the sealed evaluation capability and legacy baseline internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .graphlog_certified.evaluation import EvaluationKey


G6_EVALUATION_VERSION = "graphlog-certified-g6-evaluation/v1"


@dataclass(frozen=True, slots=True)
class G6EpisodeEvaluation:
    episode_index: int
    replacement_abstained: bool
    replacement_correct: bool
    discrete_correct: bool
    graded_correct: bool
    versus_discrete: str
    versus_graded: str


@dataclass(frozen=True, slots=True)
class G6IdentityEvaluation:
    target_id: str
    raw_a_label: str | None
    raw_b_label: str | None
    true_identity: bool
    is_anchor: bool
    structural_classification: str
    outcome: str
    commitment: str | None


@dataclass(frozen=True, slots=True)
class G6DrawEvaluation:
    version: str
    world: str
    seed_sha256: str
    episode_rows: tuple[G6EpisodeEvaluation, ...]
    identity_rows: tuple[G6IdentityEvaluation, ...]
    query_summary: tuple[tuple[str, int | float], ...]
    identity_summary: tuple[tuple[str, int | float], ...]


def _flip_label(replacement: bool, baseline: bool, abstained: bool) -> str:
    if abstained:
        return "ABSTAIN_BASELINE_CORRECT" if baseline else "ABSTAIN_BASELINE_WRONG"
    if replacement and not baseline:
        return "HEAL"
    if baseline and not replacement:
        return "BREAK"
    return "BOTH_CORRECT" if replacement else "BOTH_WRONG"


def evaluate_g6_draw(
    key: EvaluationKey,
    *,
    world: str,
    seed: int,
    seed_sha256: str,
    opaque_a_predictions: Sequence[str | None] | None,
    identity_decisions: Sequence[
        tuple[str, str, str, bool, str, str, str | None]
    ],
) -> G6DrawEvaluation:
    """Join frozen G6 outputs with labels and paired baselines.

    Identity rows are ``(target_id, a_token, b_token, is_anchor,
    structural_classification, outcome, commitment)``.  When an earlier
    premise failed, ``opaque_a_predictions`` is ``None`` and the replacement
    is scored as abstaining on every query without changing either baseline.
    """
    targets = key._EvaluationKey__query_targets
    inv_a = {
        opaque: raw for raw, opaque in key._EvaluationKey__perm_a.items()
    }
    inv_b = {
        opaque: raw for raw, opaque in key._EvaluationKey__perm_b.items()
    }
    if opaque_a_predictions is None:
        opaque_a_predictions = (None,) * len(targets)
    if len(opaque_a_predictions) != len(targets):
        raise ValueError("prediction count does not match sealed query count")
    replacement = tuple(
        None if prediction is None else inv_a.get(prediction)
        for prediction in opaque_a_predictions
    )

    # Legacy construction stays inside this evaluation-only boundary.  The
    # G5 fixed-value gate is intentionally not used: G6 pairs every arm on a
    # new per-world seed rather than reproducing the two seed-zero G5 rows.
    from .rule20_diag import _discrete_preds, _graded_frozen_preds, setup

    context = setup(world, seed=seed, n_train=150)
    if tuple(context["targets"]) != tuple(targets):
        raise ValueError("evaluation key and paired baseline targets differ")
    discrete = tuple(
        _discrete_preds(context, context["rules_ens"], "ensemble")
    )
    graded = tuple(_graded_frozen_preds(context))
    rows = []
    for index, (target, prediction, discrete_prediction, graded_prediction) in enumerate(
        zip(targets, replacement, discrete, graded, strict=True)
    ):
        replacement_correct = prediction == target
        discrete_correct = discrete_prediction == target
        graded_correct = graded_prediction == target
        abstained = prediction is None
        rows.append(G6EpisodeEvaluation(
            episode_index=index,
            replacement_abstained=abstained,
            replacement_correct=replacement_correct,
            discrete_correct=discrete_correct,
            graded_correct=graded_correct,
            versus_discrete=_flip_label(
                replacement_correct, discrete_correct, abstained,
            ),
            versus_graded=_flip_label(
                replacement_correct, graded_correct, abstained,
            ),
        ))

    identity_rows = tuple(G6IdentityEvaluation(
        target_id=target_id,
        raw_a_label=inv_a.get(a_token),
        raw_b_label=inv_b.get(b_token),
        true_identity=(
            inv_a.get(a_token) is not None
            and inv_a.get(a_token) == inv_b.get(b_token)
        ),
        is_anchor=is_anchor,
        structural_classification=classification,
        outcome=outcome,
        commitment=commitment,
    ) for (
        target_id, a_token, b_token, is_anchor, classification, outcome,
        commitment,
    ) in identity_decisions)

    total = len(rows)
    replacement_correct = sum(row.replacement_correct for row in rows)
    discrete_correct = sum(row.discrete_correct for row in rows)
    graded_correct = sum(row.graded_correct for row in rows)
    query_summary = (
        ("total", total),
        ("replacement_correct", replacement_correct),
        ("replacement_accuracy", replacement_correct / total),
        ("abstentions", sum(row.replacement_abstained for row in rows)),
        ("discrete_correct", discrete_correct),
        ("discrete_accuracy", discrete_correct / total),
        ("graded_correct", graded_correct),
        ("graded_accuracy", graded_correct / total),
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
    nonanchor_identical = tuple(
        row for row in identity_rows
        if not row.is_anchor and row.structural_classification == "IDENTICAL"
    )
    nonanchor_commits = tuple(
        row for row in nonanchor_identical if row.outcome == "COMMIT"
    )
    true_nonanchor_commits = tuple(
        row for row in nonanchor_commits if row.true_identity
    )
    false_positive_commits = sum(
        row.outcome == "COMMIT" and not row.true_identity
        for row in identity_rows
    )
    identity_summary = (
        ("targets", len(identity_rows)),
        ("nonanchor_structural_identical", len(nonanchor_identical)),
        ("nonanchor_identity_commits", len(nonanchor_commits)),
        ("evaluation_confirmed_real_nonanchor_identity_commits",
         len(true_nonanchor_commits)),
        ("false_positive_identity_commits", false_positive_commits),
        ("coverage", (
            len(nonanchor_commits) / len(nonanchor_identical)
            if nonanchor_identical else 0.0
        )),
    )
    return G6DrawEvaluation(
        G6_EVALUATION_VERSION,
        world,
        seed_sha256,
        tuple(rows),
        identity_rows,
        query_summary,
        identity_summary,
    )
