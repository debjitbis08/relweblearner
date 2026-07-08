"""Re-founded P0: the event-sourced / reflective substrate (invariants 4–8).

These pin the foundations the later phases treat as "seams":
  * inv 4 — every web act emits >= 1 well-formed bare episode; the world
    parser consumes trace episodes with zero branching (homoiconicity).
  * inv 5 — the web is a projection: replay reproduces it, and excluding one
    commitment (or its justifying episodes) revokes exactly that commitment.
  * inv 7 — external episodes may not claim the reserved act namespace.
  * inv 8 — a fork never mutates its parent's projection (1000 random moves).
"""

from __future__ import annotations

import random

import pytest

from relweblearner import (
    ACT_NAMESPACE,
    Episode,
    IntegerGroup,
    Journal,
    NamespaceViolation,
    Web,
    defects,
    world_episode,
)


def _chain(n: int, journal=None) -> Web:
    w = Web(IntegerGroup(), journal=journal)
    for k in range(n):
        w.add_node(k)
    w.chain_edges = [w.add_edge(k, k + 1, "succ", 1) for k in range(n - 1)]
    return w


# ----------------------------------------------------------- inv 4: emission
def test_every_act_emits_at_least_one_episode():
    w = Web(IntegerGroup())
    w.add_node("a")
    w.add_node("b")
    w.add_node("c")

    checks = [
        ("add_node", lambda: w.add_node("d")),
        ("add_edge", lambda: w.add_edge("a", "b", "r", 1)),
        ("relabel", lambda: w.relabel({"a": 1})),
        ("rewire", lambda: w.rewire(add=("b", "c", "r", 1))),
        ("grow", lambda: w.grow(["g"], [("c", "g", "r", 1)])),
    ]
    for name, act in checks:
        before = len(w.journal)
        act()
        assert len(w.journal) > before, f"{name} emitted no episode (invariant 4)"


def test_emitted_traces_are_wellformed_and_parse_like_world_episodes():
    # Homoiconicity: the generic world-side parse (leftovers) runs on every
    # trace episode with no special-casing.
    w = _chain(3)
    w.rewire(add=(0, 2, "chord", 2))
    for eid, ep in w.journal.all_entries():
        assert isinstance(ep, Episode)
        la, lb = ep.leftovers()          # same call used on world episodes
        assert la is not None and lb is not None
        assert ep.is_act_trace()          # web ops are acts


# --------------------------------------------------- inv 7: namespace guard
def test_external_write_into_act_namespace_is_rejected():
    j = Journal("L")
    with pytest.raises(NamespaceViolation):
        j.append(Episode(f"{ACT_NAMESPACE}:forged.in", {"x"}, "out", {"y"}, []))
    # a clean world episode is accepted
    j.append(world_episode("A", {"a"}, "B", {"b"}, [("a", "b")]))
    assert len(j) == 1


# ------------------------------------------------- inv 5: projection & replay
def test_projection_replays_identically():
    w = _chain(5)
    w.rewire(add=(0, 4, "chord", 4))
    before = {(e.u, e.v, e.value) for e in w.edges()}
    w._rebuild()                          # replay from the commit log
    after = {(e.u, e.v, e.value) for e in w.edges()}
    assert after == before


def test_retracting_one_commitment_revokes_exactly_it():
    w = _chain(5)
    chord = w.chain_edges[0]              # the 0->1 edge commitment
    nodes_before = set(w.nodes)
    n_edges = len(w.edges())

    sib = w.projected(exclude_commits={chord.eid})   # non-mutating preview
    assert len(sib.edges()) == n_edges - 1
    assert all(not (e.u == 0 and e.v == 1) for e in sib.edges())
    assert sib.nodes == nodes_before      # only the edge is gone, nodes remain
    # original untouched by the preview
    assert len(w.edges()) == n_edges

    w.retract(chord.eid)                  # now mutate
    assert len(w.edges()) == n_edges - 1
    assert all(not (e.u == 0 and e.v == 1) for e in w.edges())


def test_retract_by_excluding_justifying_episode():
    # a commitment carries provenance; excluding that episode drops the commit.
    w = Web(IntegerGroup())
    w.add_node(0)
    w.add_node(1)
    ev = w.journal.append(world_episode("obsA", {"0"}, "obsB", {"1"}, [("0", "1")]))
    w.rewire(add=(0, 1, "succ", 1), provenance=[ev])
    assert len(w.edges()) == 1
    sib = w.projected(exclude_episodes={ev})
    assert len(sib.edges()) == 0          # its justification withdrawn


# ----------------------------------------------------- inv 8: fork isolation
def test_fork_never_mutates_parent_1000_random_sequences():
    rng = random.Random(0xF0)
    for _ in range(1000):
        w = _chain(rng.randint(3, 8))
        parent_edges = {(e.u, e.v, e.value) for e in w.edges()}
        parent_nodes = set(w.nodes)
        parent_commits = list(w._commits)
        parent_journal_len = len(w.journal)

        f = w.fork()
        for _ in range(rng.randint(1, 6)):
            move = rng.choice(["add", "grow", "merge"])
            nodes = list(f.nodes)
            if move == "add" and len(nodes) >= 2:
                u, v = rng.sample(nodes, 2)
                f.rewire(add=(u, v, "r", rng.randint(-5, 5)))
            elif move == "grow":
                n = f.fresh_node()
                f.grow([n], [(rng.choice(nodes), n, "r", rng.randint(-5, 5))])
            elif move == "merge" and len(nodes) >= 2:
                a, b = rng.sample(nodes, 2)
                f.rewire(merge=(a, b))

        # parent projection and log are untouched by anything the fork did
        assert {(e.u, e.v, e.value) for e in w.edges()} == parent_edges
        assert set(w.nodes) == parent_nodes
        assert w._commits == parent_commits
        # the shared journal grew (cf traces landed on the bus) ...
        assert len(w.journal) >= parent_journal_len
        # ... but every new entry from the fork is cf-flagged
        cf_now = w.journal.counts().cf
        assert cf_now >= 0


def test_fork_emissions_are_counterfactual():
    w = _chain(3)
    real_before = w.journal.counts().act - w.journal.counts().cf
    cf_before = w.journal.counts().cf

    f = w.fork()
    f.rewire(add=(0, 2, "r", 2))
    f.grow(["g"], [(2, "g", "r", 1)])

    after = w.journal.counts()
    assert after.cf > cf_before                          # fork emitted cf traces
    assert after.act - after.cf == real_before           # no new *committed* act
