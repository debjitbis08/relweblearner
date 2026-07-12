"""Multi-web GraphLog: mechanism tests on synthetic webs (no data needed)
plus a dev-world smoke test when the GraphLog corpus is present.

The substantive predictions live in docs/multiweb-graphlog-plan.md and are
scored by the 44-world held-out run — these pin the mechanisms it rests on.
"""

from collections import Counter

import pytest

from relweblearner.bench import multiweb_graphlog as MG
from relweblearner.bench.graphlog import DATA


def test_triangle_votes():
    g = {"edges": [(0, 1, "x"), (1, 2, "y"), (0, 2, "z")]}
    votes = MG.triangle_votes([g])
    assert votes[("x", "y")]["z"] == 1
    assert ("y", "x") not in votes


def _mirror(votes: dict, m: dict) -> dict:
    return {(m[a], m[b]): Counter({m[c]: n for c, n in heads.items()})
            for (a, b), heads in votes.items()}


def test_extension_recovers_true_mapping():
    """From 2 anchors, triangle interference recovers the rest of an
    isomorphic web pair."""
    va = {("a1", "a2"): Counter({"a3": 5}),
          ("a3", "a1"): Counter({"a4": 4}),
          ("a2", "a4"): Counter({"a1": 3})}
    true = {"a1": "b1", "a2": "b2", "a3": "b3", "a4": "b4"}
    vb = _mirror(va, true)
    m = MG.extend_mapping(va, vb, {"a1": "b1", "a2": "b2"})
    assert m == true


def test_destructive_interference_rejects_confabulation():
    """Leftover tokens on each side must NOT be married off when their
    compositional roles disagree."""
    va = {("a1", "a2"): Counter({"a3": 5}),
          ("a1", "a5"): Counter({"a2": 4}),     # a5: A-only token
          ("a5", "a3"): Counter({"a1": 4})}     # a5 composes with a3
    vb = {("b1", "b2"): Counter({"b3": 5}),
          ("b1", "b6"): Counter({"b2": 4}),     # b6: same slot as a5 here...
          ("b6", "b1"): Counter({"b3": 4})}     # ...but composes differently
    m = MG.extend_mapping(va, vb, {"a1": "b1", "a2": "b2", "a3": "b3"})
    assert "a5" not in m


def test_projection_imports_unmapped_vocabulary():
    va = {("a1", "a2"): Counter({"a3": 5})}
    vb = {("b9", "b1"): Counter({"b2": 7})}     # b9 has no correspondence
    rules = MG.project(va, vb, {"a1": "b1", "a2": "b2"})
    assert rules[("a1", "a2")] == "a3"
    assert rules[("b9", "a1")] == "a2"          # imported, partners translated


def test_projection_pools_evidence_across_webs():
    """A rule below the support floor in each web alone clears it pooled."""
    va = {("a1", "a2"): Counter({"a3": 1})}
    vb = {("b1", "b2"): Counter({"b3": 1})}
    m = {"a1": "b1", "a2": "b2", "a3": "b3"}
    assert MG.project(va, vb, m)[("a1", "a2")] == "a3"
    assert not MG._threshold(va)


needs_data = pytest.mark.skipif(not DATA.exists(), reason="GraphLog corpus absent")


@needs_data
def test_dev_world_smoke_and_determinism():
    r1 = MG.run_world("rule_0", 150, seed=0)
    r2 = MG.run_world("rule_0", 150, seed=0)
    assert r1 == r2
    assert set(r1["accuracy"]) == {"view-alone", "ensemble", "gold-pooled"}
    assert r1["accuracy"]["ensemble"] >= r1["accuracy"]["view-alone"]
    assert r1["alignment"]["anchored"] <= MG.ANCHOR_BUDGET
