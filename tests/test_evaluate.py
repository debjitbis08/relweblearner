"""The standing examiner — drift detection over metrics rows.

`relweb-eval` is the one-person force multiplier: the machine re-sits the whole
curriculum and compares against last time, so a regression in a continuously-
learning creature is caught by cron, not by a human happening to notice. These
tests pin the drift RULES — what counts as regression and, as importantly, what
does not (a deliberate retraction, growth, a first baseline).
"""

from __future__ import annotations

import copy

from relweblearner.evaluate import REFUSAL_PROBE, drift


def _row(**over) -> dict:
    base = {
        "time": "2026-07-11T00:00:00", "name": "kit",
        "log": {"entries": 100, "position": 100, "excluded": 0},
        "overall": {"score": 1.0, "correct": 20, "total": 20},
        "stages": {"s1": {"score": 1.0, "correct": 10, "total": 10, "mastered": True},
                   "s2": {"score": 1.0, "correct": 10, "total": 10, "mastered": True}},
        "audits": {"refusal_ok": True, "defects": 0, "committed": 50,
                   "nodes": 60, "facts": 55, "frames": 4, "trust_entries": 3,
                   "growth_used": 0, "wonders_open": 2, "wonders_parked": 0},
    }
    for path, v in over.items():
        d, *keys, last = [base] + path.split(".")
        for k in keys:
            d = d[k]
        d[last] = v
    return base


def test_first_examination_is_a_clean_baseline():
    assert drift(None, _row()) == []


def test_identical_rows_are_healthy():
    assert drift(_row(), copy.deepcopy(_row())) == []


def test_stage_score_drop_alerts():
    cur = _row()
    cur["stages"]["s2"] = {"score": 0.9, "correct": 9, "total": 10, "mastered": True}
    alerts = drift(_row(), cur)
    assert len(alerts) == 1 and "s2" in alerts[0] and "9/10" in alerts[0]


def test_new_stage_in_current_row_is_not_drift():
    cur = _row()
    cur["stages"]["s3"] = {"score": 0.5, "correct": 5, "total": 10, "mastered": False}
    assert drift(_row(), cur) == []          # no previous score to fall from


def test_defect_rise_alerts_but_defect_fall_does_not():
    assert any("defects rose" in a for a in drift(_row(), _row(**{"audits.defects": 2})))
    assert drift(_row(**{"audits.defects": 2}), _row()) == []


def test_committed_drop_without_exclusions_alerts():
    alerts = drift(_row(), _row(**{"audits.committed": 45}))
    assert len(alerts) == 1 and "committed facts fell" in alerts[0]


def test_committed_drop_explained_by_retraction_is_not_drift():
    cur = _row(**{"audits.committed": 45, "log.excluded": 3})
    assert drift(_row(), cur) == []          # a deliberate retraction, on the record


def test_refusal_failure_alerts_even_on_first_examination():
    alerts = drift(None, _row(**{"audits.refusal_ok": False}))
    assert len(alerts) == 1 and REFUSAL_PROBE in alerts[0]


def test_growth_is_never_drift():
    cur = _row(**{"audits.committed": 80, "audits.wonders_open": 30})
    cur["log"]["entries"] = 500
    assert drift(_row(), cur) == []
