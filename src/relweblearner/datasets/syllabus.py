"""The CURRICULUM — graded stages, each with a WORKSHEET the creature must pass.

Progression is mastery-gated: a stage is only cleared when the creature *sits its
worksheet and scores above the pass-mark*. The worksheet for a stage is built from
the stage's grounded (``generated``) sources — those carry the picture/tap channel,
so their hidden world gives gradable ``(question, answer)`` pairs phrased in the
exact frames the stage taught. ``gutenberg`` sources add reading only (no truth to
grade), so a literature stage has an empty worksheet and clears on ingest.

Stages live in ``corpus/sources.json`` (``stages``); this module turns one into a
worksheet and grades the creature against it.
"""

from __future__ import annotations

from . import registry as R


def stage_worksheet(stage: dict, registry: list[dict]) -> list[tuple[str, str]]:
    """The stage's worksheet — the union of its sources' worksheets. Each source
    knows how to grade itself (:func:`registry.source_worksheet`): grounded
    generators quiz their hidden world, WordNet/Wikidata sources blank the object of
    each cached triple, and reading-only sources contribute nothing."""
    items: list[tuple[str, str]] = []
    for sid in stage.get("sources", []):
        e = R.source_by_id(registry, sid)
        if e is not None:
            items.extend(R.source_worksheet(e))
    return items


def run_exam(creature, items: list[tuple[str, str]]) -> dict:
    """Sit the worksheet: the creature fills each blank via :meth:`Creature.answer`;
    return a graded report (score, counts, a few missed items)."""
    correct = 0
    wrong: list[tuple[str, str, str | None]] = []
    for q, a in items:
        r = creature.answer(q)
        got = r["answers"][0]["answer"] if r.get("known") and r.get("answers") else None
        if got == a:
            correct += 1
        elif len(wrong) < 8:
            wrong.append((q, a, got))
    total = len(items)
    return {"correct": correct, "total": total,
            "score": (correct / total) if total else 1.0, "wrong": wrong}


def next_stage(stages: list[dict], passed: set[str]) -> dict | None:
    """The first stage not yet mastered, in curriculum order."""
    return next((s for s in stages if s["id"] not in passed), None)
