"""P1b acceptance (e1b): constructing number from bare pairing episodes.

Accepts iff:
  (a) grep-proof — no input token is a numeral;
  (b) final classes are pure by hidden size and the successor graph is a single
      chain isomorphic to an initial segment of the naturals;
  (c) a fresh collection is numbered correctly by the chain-pairing routine;
  (d) a small-collections-first schedule yields staged crystallization;
  (e) a double-tagged episode produces exactly the 'class ONEMORE of itself'
      defect, quarantined (never repaired by merging) — and is retractable by
      replay-with-exclusion.
"""

from __future__ import annotations

import re

import pytest

from relweblearner.datasets.counting import (
    by_size,
    make_collections,
    poison_episode,
    random_stream,
    staged_stream,
)
from relweblearner.number import NumberLearner

NUMERAL = re.compile(r"^-?\d+$")


def _learner_with_full_data(seed=7, n=900):
    cols = make_collections(60, max_size=5, seed=seed)
    L = NumberLearner()
    L.ingest_all(random_stream(cols, n, seed=1))
    return cols, L


def _sizes_along(cols, chain):
    return [sorted({len(cols[m]) for m in chain.class_members[c]}) for c in chain.order]


# ------------------------------------------------------------- accept (a)
def test_no_input_token_is_a_numeral():
    cols, L = _learner_with_full_data()
    for _eid, ep in L.journal.committed():
        for token in ep.all_ids():
            assert not NUMERAL.match(str(token)), f"numeral token in stream: {token!r}"


# ------------------------------------------------------------- accept (b)
def test_classes_pure_by_size_and_single_naturals_chain():
    cols, L = _learner_with_full_data()
    chain = L.project()

    # every class is pure by hidden size
    for rep, members in chain.class_members.items():
        assert len({len(cols[m]) for m in members}) == 1, "impure class"

    # the chain is a single path isomorphic to 1,2,3,...
    sizes = [s[0] for s in _sizes_along(cols, chain)]
    assert sizes == list(range(1, max(by_size(cols)) + 1))
    # single chain: every class has at most one successor
    for c, ts in L._successor_map(chain.web).items():
        assert len({chain.web.resolve(t) for t in ts}) <= 1
    assert chain.contradictions == []


# ------------------------------------------------------------- accept (c)
def test_fresh_collection_is_counted_correctly():
    cols, L = _learner_with_full_data()
    chain = L.project()
    for size in range(1, max(by_size(cols)) + 1):
        fresh = {f"z{i}" for i in range(size)}
        assert L.count(chain, fresh) == size, f"miscounted a size-{size} collection"


# ------------------------------------------------------------- accept (d)
def test_staged_schedule_yields_staged_crystallization():
    cols = make_collections(60, max_size=5, seed=7)
    stage_a, stage_b = staged_stream(cols, small_max=2, n_small=150, n_full=800, seed=1)

    L = NumberLearner()
    L.ingest_all(stage_a)
    early = L.project()
    early_multi_sizes = {
        len(cols[m])
        for members in early.class_members.values()
        if len(members) > 1
        for m in members
    }
    # only small numbers have crystallized (a "two-knower")
    assert early_multi_sizes <= {1, 2}
    assert early_multi_sizes, "nothing crystallized in stage A"

    L.ingest_all(stage_b)
    full = L.project()
    full_sizes = {s[0] for s in _sizes_along(cols, full)}
    assert full_sizes == set(range(1, max(by_size(cols)) + 1))   # all sizes now


# ------------------------------------------------------------- accept (e)
def test_poison_makes_class_onemore_of_itself_and_is_quarantined():
    cols, L = _learner_with_full_data()
    a2, a3 = by_size(cols)[2][0], by_size(cols)[3][0]

    clean = L.project()
    assert clean.contradictions == []

    pid = L.ingest(poison_episode(cols, a2, a3))     # false MATCH: 2 == 3
    poisoned = L.project()

    # exactly the 'class ONEMORE of itself' defect (a +1 holonomy self-loop)
    assert len(poisoned.contradictions) == 1
    assert poisoned.contradictions[0][0] == "class ONEMORE of itself"
    # the lie welded the 2-class and 3-class into one impure class ...
    assert any(
        {len(cols[m]) for m in members} == {2, 3}
        for members in poisoned.class_members.values()
    )
    # ... and injectivity did NOT "repair" it by merging the defect away
    assert poisoned.contradictions, "the contradiction must stay visible, not be hidden"

    # quarantine: exclude the poison episode and replay -> purity restored
    restored = L.project(exclude=frozenset({pid}))
    assert restored.contradictions == []
    for members in restored.class_members.values():
        assert len({len(cols[m]) for m in members}) == 1
