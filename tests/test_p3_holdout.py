"""P3 acceptance (e3): compositional holdout vs baselines.

Accepts iff the web learner scores the held-out ``+5`` triples at Hits@1 = 1.0
by construction, and we record the baseline gap. The web is exact with zero
learned parameters; the trained KGE baselines fall well short on exact
composition — the headline sample-efficiency figure.
"""

from __future__ import annotations

from relweblearner.datasets.holdout import build_holdout
from relweblearner.holdout import complex_metrics, transe_metrics, web_metrics


def test_web_learner_is_exact_by_construction():
    data = build_holdout(N=200)
    m = web_metrics(data)
    assert m.hits1 == 1.0        # every held-out +5 triple scored exactly
    assert m.mrr == 1.0
    # the web has zero parameters for the +5 relation — it composes +1 and +2.


def test_baselines_fall_short_of_the_web_gap():
    # smaller N + shorter training to keep the test fast; the gap is robust.
    data = build_holdout(N=120)
    web = web_metrics(data)
    cx = complex_metrics(data, epochs=120, seed=0)

    assert web.hits1 == 1.0
    assert cx.hits1 < web.hits1                       # a real compositional gap
    assert web.hits1 - cx.hits1 >= 0.3                # and a large one
    assert 0.0 <= cx.hits1 <= 1.0 and 0.0 <= cx.mrr <= 1.0


def test_transe_runs_and_underperforms_the_web():
    data = build_holdout(N=120)
    tr = transe_metrics(data, epochs=200, seed=0)
    assert 0.0 <= tr.hits1 <= 1.0
    assert tr.hits1 < 1.0                             # cannot match exact composition
