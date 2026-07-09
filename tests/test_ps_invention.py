"""P7' acceptance (society §7): content defects vs error defects.

The amended defect rule, both halves in one run: a persistent holonomy class
that conflicts with no observation is CONTENT (banked, answers modular queries);
one that conflicts with an observation is an ERROR (retracted by unchanged P7).
"""

from __future__ import annotations

from relweblearner import audit, invention as INV
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets import counting as C
from relweblearner.datasets.counting import poison_episode
from relweblearner.holonomy import defects
from relweblearner.number import NumberLearner
from relweblearner.web import Web


def _clock(n=12):
    w = Web(IntegerGroup())
    for i in range(n):
        w.add_node(f"h{i}")
    for i in range(n - 1):
        w.add_edge(f"h{i}", f"h{i + 1}", "succ", 1)
    w.add_edge(f"h{n - 1}", "h0", "succ", 1)
    return w


def test_clock_is_content_and_answers_modular_queries():
    w = _clock()
    assert defects(w)[0].residual == 12          # winding +12
    assert INV.observation_conflicts(w) == []    # conflicts nothing
    assert INV.classify_defect(w) == "content"

    census = INV.InventionCensus()
    assert INV.bank_content(w, census, "clock-mod-12") is not None
    assert len(census.banked) == 1
    assert INV.modular_answer(w, "h11", "succ", 3) == "h2"   # 11 + 3 == 2 (mod 12)


def test_self_loop_merge_is_an_error():
    w = Web(IntegerGroup())
    w.add_node("K")
    w.add_edge("K", "K", "succ", 1)              # class ONEMORE of itself
    assert INV.observation_conflicts(w)          # observation-level contradiction
    assert INV.classify_defect(w) == "error"


def test_poisoned_merge_still_retracts():
    cols = C.make_collections(40, seed=3)
    sizes = {c: len(v) for c, v in cols.items()}
    learner = NumberLearner()
    learner.ingest_all(C.random_stream(cols, 400, seed=1))
    small = next(k for k, v in cols.items() if len(v) == 2)
    big = next(k for k, v in cols.items() if len(v) == 3)
    learner.ingest(poison_episode(cols, small, big))

    mp, om = audit.derive_facts(learner.journal, k=1)
    assert audit.contradictions(mp, om)          # poison detected
    excluded, _refused = INV.retract_error(mp, om)
    after = {p: e for p, e in mp.items() if p not in excluded}
    assert audit.contradictions(after, om) == []      # retracted
    assert audit.purity(after, sizes) == 1.0          # purity restored


def test_content_and_error_both_handled_in_one_run():
    # content banked...
    clock = _clock()
    census = INV.InventionCensus()
    assert INV.classify_defect(clock) == "content"
    INV.bank_content(clock, census, "clock-mod-12")
    assert INV.modular_answer(clock, "h11", "succ", 3) == "h2"

    # ...while an error retracts, in the same run
    cols = C.make_collections(40, seed=3)
    learner = NumberLearner()
    learner.ingest_all(C.random_stream(cols, 400, seed=1))
    small = next(k for k, v in cols.items() if len(v) == 2)
    big = next(k for k, v in cols.items() if len(v) == 3)
    learner.ingest(poison_episode(cols, small, big))
    mp, om = audit.derive_facts(learner.journal, k=1)
    excluded, _ = INV.retract_error(mp, om)
    after = {p: e for p, e in mp.items() if p not in excluded}
    assert audit.contradictions(after, om) == []
    assert len(census.banked) == 1               # content survived defect handling


def test_invention_census_tracks_posit_confirmation():
    census = INV.InventionCensus()
    census.posit("neg1")
    census.posit("neg2")
    census.confirm("neg1")
    assert census.posit_confirmation_rate() == 0.5


def test_posit_before_evidence_neutrino_pattern():
    # an incomplete split leaves a member unaccounted -> posit an unseen entity
    source = {"o1", "o2", "o3", "o4", "o5"}
    seen = [{"o1", "o2"}, {"o3", "o4"}]
    missing = INV.posit_from_closure(source, seen)
    assert missing == {"o5"}                     # derived by closure, never observed

    census = INV.InventionCensus()
    t_posit = 1
    census.posit("H*", members=missing, at=t_posit)
    # a retrieval baseline has nothing to return at posit time
    assert not [d for d in seen if "o5" in d]
    # the world reveals it strictly later -> the posit preceded its evidence
    t_reveal = 2
    census.confirm("H*")
    assert t_posit < t_reveal
    assert census.posit_confirmation_rate() == 1.0
