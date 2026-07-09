"""es — society (PS): the multi-agent layer.

Runs the society layers on the shared world and reports the headline metrics:
dyad convergence with lateral inhibition, cross-agent adjunction, solipsism-debt
discharge by peer ostension, citation-tracked gossip (rumor vs cited vs Sybil),
population dynamics (dialects + creolization plateau), and the disagreement
protocol (interface defects, queryable, resolved by origin weight).

Writes results/es_society.csv and results/es_society.png.
Run: ``poetry run python experiments/es_society.py``
"""

from __future__ import annotations

import csv
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner import language as L
from relweblearner import society as S
from relweblearner.datasets import language as DL
from relweblearner.datasets import society as D

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def s1_dyad():
    A, B = S.Agent("A", owner="oA", seed=1), S.Agent("B", owner="oB", seed=2)
    rng = random.Random(0)
    curve, window = [], []
    for r in range(1, 401):
        sp, li = (A, B) if r % 2 else (B, A)
        ok = S.naming_round(sp, li, rng.choice(D.CONCEPTS), inhibit=True)
        window.append(ok)
        if r % 80 == 0:
            curve.append(sum(window[-80:]) / 80)
    identical = all(A.top(c) == B.top(c) for c in D.CONCEPTS)
    facts = [("HC", f, c) for f, c in DL.HC.items()]
    adj = S.cross_agent_adjunction(A, B, facts)
    return curve, identical, adj


def s1_solipsism():
    """Two agents share the fruit world; solo grounding stalls at the orbits;
    one peer ostension per orbit discharges the solipsism debt to zero.
    """
    units, _gold = DL.stream_of(300, seed=3)
    words, _b = L.segment(units)
    fw = L.discover_frame_words(words)
    utts = L.chunk(words, fw)
    tok_web = L.token_web(utts, fw)
    con_edges = DL.concept_edges()

    census = [len(L.ground(tok_web, con_edges).orbits)]  # solo: unresolved orbits
    g1 = L.ground(tok_web, con_edges, seeds={"bavu": "mango"})
    census.append(len(g1.orbits))
    g2 = L.ground(tok_web, con_edges, seeds={"bavu": "mango", "runi": "apple"})
    census.append(len(g2.orbits))
    return census


def s3_gossip(n_agents=24, k=3):
    rng = random.Random(7)
    agents = [S.Agent(f"g{i}", owner=f"g{i}", seed=i) for i in range(n_agents)]

    false = ("HC", "lime", "red")
    liar = S.Agent("liar", owner="liar", seed=99)
    for _ in range(50):
        S.teach(liar, agents[0], false)          # loud: one owner, 50 tellings
    for _ in range(4000):
        a, b = rng.sample(agents, 2)
        S.relay(a, b, false)                     # gossip transmits origin set unchanged
    rumor_naive = sum(1 for a in agents if S.committed_naive(a, false, k))
    rumor_committed = sum(1 for a in agents if S.committed(a, false, k))

    true = ("HC", "mango", "yellow")
    for i in range(6):                           # six independent owners, once each
        S.teach(S.Agent(f"own{i}", owner=f"own{i}"), agents[i], true)
    for _ in range(4000):
        a, b = rng.sample(agents, 2)
        S.relay(a, b, true)
    cited_committed = sum(1 for a in agents if S.committed(a, true, k))

    sybils = [S.Agent(f"s{i}", owner="boss", seed=i) for i in range(10)]
    victim = S.Agent("v", owner="v")
    for s in sybils:
        S.teach(s, victim, false)
    sybil_origins = S.origin_count(victim, false)
    return rumor_naive, rumor_committed, cited_committed, sybil_origins, n_agents


def s4_population():
    commA = [S.Agent(f"a{i}", owner=f"a{i}", seed=i) for i in range(5)]
    commB = [S.Agent(f"b{i}", owner=f"b{i}", seed=100 + i) for i in range(5)]
    S.run_population(commA, D.clique_edges(commA), D.CONCEPTS[:6], 3000, inhibit=True, seed=1)
    S.run_population(commB, D.clique_edges(commB), D.CONCEPTS[:6], 3000, inhibit=True, seed=2)
    dialects = (
        S.lexical_convergence(commA, D.CONCEPTS[:6]),
        S.lexical_convergence(commB, D.CONCEPTS[:6]),
        S.cross_agreement(commA, commB, D.CONCEPTS[:6]),
    )

    def creole(inhibit):
        ags = [S.Agent(f"x{i}", owner=f"x{i}", seed=i) for i in range(10)]
        S.run_population(ags, D.clique_edges(ags), D.CONCEPTS[:6], 6000, inhibit=inhibit, seed=5)
        return S.lexical_convergence(ags, D.CONCEPTS[:6])

    return dialects, creole(True), creole(False)


def s5_disagreement():
    victim = S.Agent("B", owner="B")
    lime_red = ("HC", "lime", "red")
    for o in ("o1", "o2", "o3"):
        victim.beliefs[lime_red].add(o)          # committed by testimony (no perception)
    outcome = S.hear_claim(victim, "A", ("HC", "lime", "green"), {"p1", "p2", "p3", "p4"}, k=3)
    queryable = S.disagreements_with(victim, "A")
    winner, how = S.resolve_defect(victim, queryable[0])
    return outcome, bool(queryable), winner, how


def run():
    curve, identical, adj = s1_dyad()
    census = s1_solipsism()
    rumor_naive, rumor, cited, sybil, n = s3_gossip()
    dialects, creole_on, creole_off = s4_population()
    outcome, queryable, winner, how = s5_disagreement()

    print("=" * 66)
    print("S1. DYAD: naming game with lateral inhibition")
    print("=" * 66)
    print("communication success per 80 rounds:", " ".join(f"{c:.2f}" for c in curve))
    print(f"lexicons identical: {identical}; cross-agent adjunction: {adj:.2f}")
    print(f"solipsism debt (unresolved orbits) after 0/1/2 peer ostensions: {census}")

    print("\n" + "=" * 66)
    print("S3. CITATION-TRACKED GOSSIP (the immune system)")
    print("=" * 66)
    print(f"rumor (1 owner, 50 tellings, 4000 gossip rounds): "
          f"NAIVE hearing-count {rumor_naive}/{n} vs ORIGIN-count {rumor}/{n}")
    print(f"cited (6 independent owners, once each): committed {cited}/{n}")
    print(f"Sybil (10 agents, 1 owner): origin count {sybil}")

    print("\n" + "=" * 66)
    print("S4. POPULATION: dialects & creolization")
    print("=" * 66)
    print(f"dialects: within {dialects[0]:.2f}/{dialects[1]:.2f}, cross {dialects[2]:.2f}")
    print(f"creolization WITH inhibition {creole_on:.2f}  vs  WITHOUT {creole_off:.2f} (plateau)")

    print("\n" + "=" * 66)
    print("S5. DISAGREEMENT PROTOCOL")
    print("=" * 66)
    print(f"conflicting claim -> {outcome}; queryable: {queryable}; "
          f"resolved to {winner[2]} by {how}")

    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "es_society.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["dyad_success_final", f"{curve[-1]:.3f}"])
        w.writerow(["dyad_lexicons_identical", int(identical)])
        w.writerow(["cross_agent_adjunction", f"{adj:.3f}"])
        w.writerow(["solipsism_debt_final", census[-1]])
        w.writerow(["rumor_committed_naive", f"{rumor_naive}/{n}"])
        w.writerow(["rumor_committed_origin", f"{rumor}/{n}"])
        w.writerow(["cited_committed", f"{cited}/{n}"])
        w.writerow(["sybil_origin_count", sybil])
        w.writerow(["dialect_within", f"{dialects[0]:.3f}"])
        w.writerow(["dialect_cross", f"{dialects[2]:.3f}"])
        w.writerow(["creolization_with_inhibition", f"{creole_on:.3f}"])
        w.writerow(["creolization_without_inhibition", f"{creole_off:.3f}"])
        w.writerow(["disagreement_resolution", how])
    _plot(curve, census, (rumor_naive, rumor, cited, n), (creole_on, creole_off),
          os.path.join(RESULTS, "es_society.png"))
    print(f"\nwrote {csv_path}")


def _plot(curve, census, gossip, creole, path):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    ax = axes[0]
    ax.plot(range(80, 401, 80), curve, "-o", color="#2c3e50")
    ax.axhline(1.0, ls="--", color="#7f8c8d", lw=1)
    ax.set_title("S1 dyad: communication success\n(lateral inhibition -> 1.0)")
    ax.set_xlabel("round")
    ax.set_ylabel("success (last 80)")
    ax.set_ylim(0, 1.05)

    ax = axes[1]
    rumor_naive, rumor, cited, n = gossip
    ax.bar(["rumor\n(naive)", "rumor\n(origin)", "cited\n(6 owners)"],
           [rumor_naive, rumor, cited], color=["#e67e22", "#c0392b", "#2c3e50"])
    ax.axhline(n, ls="--", color="#7f8c8d", lw=1)
    ax.set_title("S3 gossip: naive counting trusts the rumor,\norigin-counting doesn't")
    ax.set_ylabel(f"agents committed (of {n})")
    ax.set_ylim(0, n + 1)

    ax = axes[2]
    on, off = creole
    ax.bar(["with\ninhibition", "without\n(plateau)"], [on, off],
           color=["#2c3e50", "#c0392b"])
    ax.axhline(0.95, ls="--", color="#7f8c8d", lw=1)
    ax.set_title("S4 creolization: lexical convergence\n(inhibition is required)")
    ax.set_ylabel("convergence")
    ax.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
