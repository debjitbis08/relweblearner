"""P6 acceptance: reflection needs no new machinery, only attention allocation.

  (a) classes crystallize over the learner's own acts using UNCHANGED
      type-discovery machinery (scored as purity vs hidden operation kinds);
  (b) the attention budget bounds the regress: consumption never exceeds
      budget and the emitted-but-unconsumed backlog stays finite;
  (c) self-derived quantities: the learner counts its own defect reports with
      the number chain it constructed in P1b.
"""

from __future__ import annotations

from relweblearner import reflection as R
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets.counting import make_collections, random_stream
from relweblearner.number import NumberLearner
from relweblearner.web import Web

TAGS = {"add_edge", "rewire", "grow", "walk", "defect"}


def _workload() -> Web:
    """A web run through structurally-distinct operations; every act emits."""
    w = Web(IntegerGroup(), name="W")
    for i in range(8):
        w.add_node(i)
    for i in range(7):
        w.add_edge(i, i + 1, "succ", 1)          # add_edge  (1,1,1)
    w.rewire(merge=(6, 7))                         # merge     (2,1,1,True)
    w.rewire(merge=(4, 5))
    w.grow(["g0", "g1"], [(3, "g0", "succ", 1), ("g0", "g1", "succ", 1)])  # grow (2,1,0)
    w.walk(0, "succ~", 3)                          # walk off-web (1,2,0)
    w.walk(2, "succ~", 5)
    return w


def _defective_web(n_defects: int) -> Web:
    """A web with exactly ``n_defects`` INDEPENDENT defects (disjoint regions)."""
    w = Web(IntegerGroup(), name="D")
    N = 3 * n_defects + 1
    for i in range(N):
        w.add_node(i)
    for i in range(N - 1):
        w.add_edge(i, i + 1, "succ", 1)
    for k in range(n_defects):
        a = 3 * k
        w.add_edge(a, a + 2, "same", 0)          # holonomy 2, disjoint regions
    return w


# ------------------------------------------------------------- accept (a)
def test_act_classes_crystallize_at_purity_1():
    w = _workload()
    traces = R.act_traces(w.journal, tags=TAGS)
    assert len(traces) >= 10
    classes = R.discover_act_classes(traces)
    assert R.act_class_purity(classes) == 1.0        # each class is one op kind
    # the discovered classes recover the distinct operation kinds
    kinds = {next(iter({R.operation_of(e) for e in eps})) for eps in classes.values()}
    assert {"add_edge", "rewire", "grow", "walk"} <= kinds


def test_act_traces_parse_like_world_episodes():
    w = _workload()
    traces = R.act_traces(w.journal)
    assert R.parses_as_world(traces)                 # homoiconicity, zero branching


# ------------------------------------------------------------- accept (b)
def test_attention_budget_bounds_the_regress():
    w = _workload()
    budget = 5
    res = R.bounded_consume(w.journal, budget=budget)
    assert res["consumed"] <= budget                 # consumption capped
    assert res["consumed"] == budget                 # (enough traces to hit it)
    assert res["backlog"] < 10 ** 6                   # finite: no infinite regress
    # every consumption emitted (emission never stops), yet it terminated
    assert res["emitted_by_consumption"] == res["consumed"]


# ------------------------------------------------------------- accept (c)
def test_learner_counts_its_own_defect_reports_with_its_number_chain():
    L = NumberLearner()
    L.ingest_all(random_stream(make_collections(60, seed=7), 900, seed=1))
    chain = L.project()

    for n in (1, 2, 3):
        wd = _defective_web(n)
        reports = R.emit_defect_reports(wd)
        assert len(reports) == n                      # one report per defect
        assert R.self_count(L, chain, reports) == n   # counted with its own ruler
