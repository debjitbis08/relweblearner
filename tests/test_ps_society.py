"""PS acceptance: the society (multi-agent) layer.

Standalone spec ``docs/spec-society.md``, off the numbered dev-doc roadmap.
Tests the layers S0-S5 against the spec's acceptance criteria: containerization
determinism, dyad convergence via lateral inhibition + cross-agent adjunction +
solipsism-debt discharge, citation-tracked gossip (rumor vs cited vs Sybil),
population dialects/creolization, and the disagreement protocol.
"""

from __future__ import annotations

import random

from relweblearner import language as L
from relweblearner import society as S
from relweblearner.datasets import language as DL
from relweblearner.datasets import society as D


def _play_dyad(inhibit=True, rounds=400):
    A, B = S.Agent("A", owner="oA", seed=1), S.Agent("B", owner="oB", seed=2)
    rng = random.Random(0)
    window = []
    for r in range(1, rounds + 1):
        sp, li = (A, B) if r % 2 else (B, A)
        window.append(S.naming_round(sp, li, rng.choice(D.CONCEPTS), inhibit=inhibit))
    return A, B, window


# ---------------------------------------------------------------- S0 containerize
def test_agents_share_no_memory_and_are_deterministic():
    # same transcript + seeds -> bit-identical agent state (process-independent).
    a1, b1, _ = _play_dyad()
    a2, b2, _ = _play_dyad()
    lex1 = {c: a1.top(c) for c in D.CONCEPTS}
    lex2 = {c: a2.top(c) for c in D.CONCEPTS}
    assert lex1 == lex2
    # agents don't share mutable state: B's lexicon is its own object
    assert a1.assoc is not b1.assoc


def test_provenance_is_per_owner_not_per_agent():
    victim = S.Agent("v", owner="v")
    sybils = [S.Agent(f"s{i}", owner="boss") for i in range(10)]
    for s in sybils:
        S.teach(s, victim, ("HC", "lime", "red"))
    assert S.origin_count(victim, ("HC", "lime", "red")) == 1   # 10 agents, 1 owner


# -------------------------------------------------------------------- S1 dyad
def test_dyad_converges_to_one_shared_lexicon():
    A, B, window = _play_dyad(inhibit=True)
    assert sum(window[-80:]) / 80 == 1.0                       # success -> 1.0
    assert all(A.top(c) == B.top(c) for c in D.CONCEPTS)        # identical lexicons


def test_cross_agent_adjunction_holds_over_expressible_set():
    A, B, _ = _play_dyad(inhibit=True)
    facts = [("HC", f, c) for f, c in DL.HC.items()]
    assert S.cross_agent_adjunction(A, B, facts) == 1.0


def test_solipsism_debt_discharged_by_peer_ostension():
    units, _g = DL.stream_of(300, seed=3)
    words, _b = L.segment(units)
    fw = L.discover_frame_words(words)
    tok_web = L.token_web(L.chunk(words, fw), fw)
    con_edges = DL.concept_edges()

    orbits0 = L.ground(tok_web, con_edges).orbits
    assert len(orbits0) == 2                                    # solo: closed to experience
    g1 = L.ground(tok_web, con_edges, seeds={"bavu": "mango"})
    g2 = L.ground(tok_web, con_edges, seeds={"bavu": "mango", "runi": "apple"})
    assert len(g1.orbits) == 1 and len(g2.orbits) == 0         # #orbits ostensions -> 0


# ------------------------------------------------------------------ S3 gossip
def _gossip_committed(fact, teach_plan, k=3, n_agents=24, rounds=4000):
    rng = random.Random(7)
    agents = [S.Agent(f"g{i}", owner=f"g{i}", seed=i) for i in range(n_agents)]
    teach_plan(agents)
    for _ in range(rounds):
        a, b = rng.sample(agents, 2)
        S.relay(a, b, fact)
    return sum(1 for a in agents if S.committed(a, fact, k)), agents


def test_rumor_is_defeated_by_origin_counting():
    false = ("HC", "lime", "red")

    def plan(agents):
        liar = S.Agent("liar", owner="liar")
        for _ in range(50):
            S.teach(liar, agents[0], false)                    # loud but one origin
    committed, agents = _gossip_committed(false, plan)
    assert committed == 0                                       # 0/24 under origin-counting
    assert S.origin_count(agents[0], false) == 1


def test_independently_cited_fact_commits():
    true = ("HC", "mango", "yellow")

    def plan(agents):
        for i in range(6):                                     # six distinct owners
            S.teach(S.Agent(f"own{i}", owner=f"own{i}"), agents[i], true)
    committed, _agents = _gossip_committed(true, plan)
    assert committed == 24                                      # N/N once origins gossip


# -------------------------------------------------------------- S4 population
def test_dialects_form_without_contact():
    commA = [S.Agent(f"a{i}", owner=f"a{i}", seed=i) for i in range(5)]
    commB = [S.Agent(f"b{i}", owner=f"b{i}", seed=100 + i) for i in range(5)]
    cs = D.CONCEPTS[:6]
    S.run_population(commA, D.clique_edges(commA), cs, 3000, inhibit=True, seed=1)
    S.run_population(commB, D.clique_edges(commB), cs, 3000, inhibit=True, seed=2)
    assert S.lexical_convergence(commA, cs) >= 0.95
    assert S.lexical_convergence(commB, cs) >= 0.95
    assert S.cross_agreement(commA, commB, cs) == 0.0          # separate dialects


def test_creolization_requires_lateral_inhibition():
    cs = D.CONCEPTS[:6]

    def creole(inhibit):
        ags = [S.Agent(f"x{i}", owner=f"x{i}", seed=i) for i in range(10)]
        S.run_population(ags, D.clique_edges(ags), cs, 6000, inhibit=inhibit, seed=5)
        return S.lexical_convergence(ags, cs)

    assert creole(True) >= 0.95                                # inhibition creolizes
    assert creole(False) < 0.5                                 # adopt-only plateaus


# ---------------------------------------------------------- S5 disagreement
def test_disagreement_is_detected_logged_and_resolved():
    victim = S.Agent("B", owner="B")
    lime_red = ("HC", "lime", "red")
    for o in ("o1", "o2", "o3"):
        victim.beliefs[lime_red].add(o)                        # committed (testimony)

    outcome = S.hear_claim(victim, "A", ("HC", "lime", "green"), {"p1", "p2", "p3", "p4"}, k=3)
    assert outcome == "interface_defect"                       # not adopted/retracted
    assert S.disagreements_with(victim, "A")                   # queryable
    winner, how = S.resolve_defect(victim, S.disagreements_with(victim, "A")[0])
    assert winner[2] == "green" and how == "origin_weight"     # better-cited wins


def test_perception_outranks_testimony():
    victim = S.Agent("B", owner="B")
    lime_red = ("HC", "lime", "red")
    victim.perceived[lime_red] = True                          # first-hand (though wrong)
    for o in ("o1", "o2", "o3"):
        victim.beliefs[lime_red].add(o)
    S.hear_claim(victim, "A", ("HC", "lime", "green"), {"p1", "p2", "p3", "p4", "p5"}, k=3)
    winner, how = S.resolve_defect(victim, S.disagreements_with(victim, "A")[0])
    assert winner == lime_red and how == "perception"          # documented limit
