"""Acceptance for the mastery-gated CURRICULUM — worksheets, grading, gating.

Network-free: uses the grounded generators (whose hidden truth makes the worksheets
gradable). A stage is only cleared when the creature actually SOLVES its worksheet.
"""

from __future__ import annotations

from relweblearner.creature import Creature
from relweblearner.datasets import registry as R
from relweblearner.datasets import syllabus as SYL


def _teach(sources_gen, n=12000, level=2, seed=1):
    c = Creature("student", commit_k=2, min_group=8, induction_interval=300, buffer_cap=30000)
    eps, _ = sources_gen.generate(n_episodes=n, level=level, seed=seed)
    c.ingest(eps)
    return c


def test_worksheet_is_built_from_grounded_truth():
    from relweblearner.datasets import mathbooks as MB
    stage = {"id": "s", "name": "maths", "sources": ["g-math"]}
    registry = [{"id": "g-math", "kind": "generated", "generator": "mathbooks",
                 "params": {"n_episodes": 100, "level": 3, "seed": 7}}]
    items = SYL.stage_worksheet(stage, registry)
    # every worksheet item is a (question-with-blank, answer) drawn from the world
    assert items and all("?" in q and isinstance(a, str) for q, a in items)
    # a gutenberg source contributes NO worksheet items (no gradable truth)
    stage2 = {"id": "s2", "sources": ["book"]}
    reg2 = [{"id": "book", "kind": "gutenberg", "ref": 1}]
    assert SYL.stage_worksheet(stage2, reg2) == []


def test_creature_that_learned_the_stage_passes_its_worksheet():
    from relweblearner.datasets import sciencebooks as SB
    c = _teach(SB, level=2)
    world = SB._world(1)
    report = SYL.run_exam(c, SB.quiz(world, level=2))
    assert report["total"] > 0
    assert report["score"] >= 0.9          # it genuinely solves the science worksheet
    assert report["correct"] == report["total"] - len(report["wrong"]) or report["wrong"]


def test_an_untaught_creature_fails_the_worksheet():
    from relweblearner.datasets import sciencebooks as SB
    c = Creature("blank")                    # never read anything
    report = SYL.run_exam(c, SB.quiz(SB._world(1), level=2))
    assert report["score"] == 0.0            # mastery gating would hold it here


def test_next_stage_follows_curriculum_order_and_skips_passed():
    stages = R.load_stages()
    assert stages, "curriculum has stages"
    assert SYL.next_stage(stages, set())["id"] == stages[0]["id"]
    passed = {stages[0]["id"], stages[1]["id"]}
    assert SYL.next_stage(stages, passed)["id"] == stages[2]["id"]
    all_ids = {s["id"] for s in stages}
    assert SYL.next_stage(stages, all_ids) is None    # complete


def test_math_and_science_lead_the_curriculum():
    # the user's requirement: math & science are the backbone, literature secondary
    stages = R.load_stages()
    registry = R.load_registry()
    def domains(stage):
        return {R.source_by_id(registry, s)["domain"] for s in stage["sources"]}
    assert domains(stages[0]) == {"math"}
    # science within the first five (counting play + how-many added two more
    # math stages up front — the backbone got MORE math, not less)
    assert "science" in {d for s in stages[:5] for d in domains(s)}
    # literature is not the first thing taught
    assert "literature" not in domains(stages[0])
