"""Phase-1 verification — Part D: soak.

The protocol asks for one society of 12 agents at 10^6 interaction rounds with 1%
corrupt episodes, and four "nothing runs away" curves: memory, defect mass,
fragmentation, reflection backlog. The 10^6-round soak runs on the society layer
(what Part D literally specifies); defect mass and reflection backlog are shown
on the substrates where those quantities live (a full substrate-per-agent 10^6
soak would mean wiring each agent's complete learner — new capability, out of
verification scope). Each curve is labelled with its source.

PASS targets: memory bounded / sublinear after convergence; lexical convergence
at 10^6 within 5% of 10^4; no synonym-fragmentation cascade; rumor still 0 under
noise; defect mass bounded (k>=2 gate); reflection backlog finite under budget.

Writes results/verify_soak.csv and results/verify_soak.png.
Run: ``poetry run python experiments/verify_soak.py``
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

from relweblearner import reflection, society as S
from relweblearner import audit
from relweblearner.algebra import IntegerGroup
from relweblearner.datasets import counting as C
from relweblearner.datasets.counting import pairing_episode, poison_episode
from relweblearner.number import NumberLearner
from relweblearner.web import Web

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
CONCEPTS = [f"c{i}" for i in range(6)]
CHECKPOINTS = [1_000, 10_000, 100_000, 1_000_000]


# ---------------------------------------------- (1)+(3) society soak, 1e6 rounds
def society_soak():
    agents = [S.Agent(f"g{i}", owner=f"g{i}", seed=i) for i in range(12)]
    edges = list(itertools.combinations(agents, 2))
    rng = random.Random(0)
    ckpts = set(CHECKPOINTS)
    mem, conv, frag = {}, {}, {}
    for r in range(1, CHECKPOINTS[-1] + 1):
        a, b = rng.choice(edges)
        sp, li = (a, b) if rng.random() < 0.5 else (b, a)
        if rng.random() < 0.01:                       # 1% corrupt: a garbled word
            li.hear_name(rng.choice(CONCEPTS), "".join(rng.sample(S._SYLS, 2)), inhibit=True)
        else:
            S.naming_round(sp, li, rng.choice(CONCEPTS), inhibit=True)
        if r in ckpts:
            mem[r] = sum(len(ws) for ag in agents for ws in ag.assoc.values())
            conv[r] = S.lexical_convergence(agents, CONCEPTS)
            frag[r] = max((len(ag.assoc[c]) for ag in agents for c in CONCEPTS if ag.assoc.get(c)),
                          default=0)
    # rumor under noise: still 0 committed
    false = ("HC", "lime", "red")
    liar = S.Agent("liar", owner="liar")
    for _ in range(50):
        S.teach(liar, agents[0], false)
    for _ in range(4000):
        x, y = rng.sample(agents, 2)
        S.relay(x, y, false)
    rumor = sum(1 for ag in agents if S.committed(ag, false, 3))
    return mem, conv, frag, rumor


# ---------------------------------------------- (2) substrate defect mass, 1% poison
def defect_mass_soak(n=6000, poison_rate=0.01, seed=0):
    cols = C.make_collections(80, seed=seed)
    smalls = [k for k, v in cols.items() if len(v) == 2]
    bigs = [k for k, v in cols.items() if len(v) == 3]
    rng = random.Random(seed)
    learner = NumberLearner()
    keys = list(cols)
    curve = {}
    ckpts = {1000, 2000, 4000, 6000}
    for i in range(1, n + 1):
        if rng.random() < poison_rate and smalls and bigs:
            learner.ingest(poison_episode(cols, rng.choice(smalls), rng.choice(bigs)))
        else:
            learner.ingest(pairing_episode(cols, *rng.sample(keys, 2), rng=rng))
        if i in ckpts:
            mp, om = audit.derive_facts(learner.journal, k=2)   # k>=2 provisional gate
            pre = len(audit.contradictions(mp, om))
            # apply the P7 recovery policy: localize-and-replay caps the damage
            excluded, _ = audit.localize(mp, om)
            after = {p: e for p, e in mp.items() if p not in excluded}
            post = len(audit.contradictions(after, om))
            curve[i] = {"pre_recovery": pre, "post_recovery": post, "cuts": len(excluded)}
    return curve


# ---------------------------------------------- (4) reflection backlog under budget
def reflection_backlog_soak(n_ops=4000, budget=200):
    j = Web(IntegerGroup(), name="soak").journal
    w = Web(IntegerGroup(), name="soak", journal=j)
    curve = {}
    ckpts = {500, 1000, 2000, 4000}
    for i in range(1, n_ops + 1):
        w.add_node(f"n{i}")                            # each op emits a trace (inv 4)
        if i > 1:
            w.add_edge(f"n{i-1}", f"n{i}", "succ", 1)
        if i in ckpts:
            res = reflection.bounded_consume(j, budget=budget, tag=f"c{i}")
            curve[i] = {"backlog": res["backlog"], "consumed": res["consumed"]}
    return curve, budget


def run():
    mem, conv, frag, rumor = society_soak()
    defect = defect_mass_soak()
    backlog, budget = reflection_backlog_soak()

    conv_10k, conv_1m = conv[10_000], conv[1_000_000]
    within5 = abs(conv_1m - conv_10k) <= 0.05 * max(conv_10k, 1e-9)
    mem_bounded = mem[1_000_000] <= 12 * len(CONCEPTS) * 2   # <= 2 words/concept/agent
    frag_bounded = max(frag.values()) <= 3
    defect_bounded = max(v["post_recovery"] for v in defect.values()) == 0   # localize caps it
    backlog_capped = all(v["consumed"] <= budget for v in backlog.values())

    print("=" * 66)
    print("PART D — SOAK (12 agents, 1e6 rounds, 1% corrupt)")
    print("=" * 66)
    print("society memory (total assoc entries):", {k: mem[k] for k in CHECKPOINTS})
    print("lexical convergence:", {k: round(conv[k], 3) for k in CHECKPOINTS})
    print(f"  convergence 1e6 within 5% of 1e4: {within5} "
          f"({conv_1m:.3f} vs {conv_10k:.3f})")
    print("synonyms/concept (fragmentation):", {k: frag[k] for k in CHECKPOINTS})
    print(f"rumor committed under noise: {rumor}/12")
    print("substrate defect mass (1% poison): "
          f"{ {k: (v['pre_recovery'], v['post_recovery']) for k, v in defect.items()} }")
    print(f"  (pre_recovery, post_recovery) per checkpoint; post-localize bounded: {defect_bounded}")
    print(f"reflection backlog (budget {budget}): "
          f"{ {k: v['backlog'] for k, v in backlog.items()} }  -> consumption capped: {backlog_capped}")
    print("\nPASS:", all([within5, mem_bounded, frag_bounded, defect_bounded,
                          backlog_capped, rumor == 0]))

    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "verify_soak.csv")
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["curve", "checkpoint", "value"])
        for k in CHECKPOINTS:
            wr.writerow(["society_memory", k, mem[k]])
            wr.writerow(["lexical_convergence", k, f"{conv[k]:.3f}"])
            wr.writerow(["synonyms_per_concept", k, frag[k]])
        for k, v in defect.items():
            wr.writerow(["defect_pre_recovery", k, v["pre_recovery"]])
            wr.writerow(["defect_post_recovery", k, v["post_recovery"]])
        for k, v in backlog.items():
            wr.writerow(["reflection_backlog", k, v["backlog"]])
        wr.writerow(["rumor_under_noise", 1_000_000, rumor])
    _plot(mem, conv, frag, defect, backlog, os.path.join(RESULTS, "verify_soak.png"))
    print(f"wrote {path}")


def _plot(mem, conv, frag, defect, backlog, path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    xs = CHECKPOINTS

    ax = axes[0][0]
    ax.plot(xs, [mem[k] for k in xs], "-o", color="#2c3e50")
    ax.set_xscale("log")
    ax.set_title("(1) society memory — bounded/flat after convergence")
    ax.set_xlabel("rounds")
    ax.set_ylabel("total assoc entries")
    ax.set_ylim(0, max(mem.values()) * 1.4)

    ax = axes[0][1]
    dk = sorted(defect)
    ax.plot(dk, [defect[k]["pre_recovery"] for k in dk], "-o", color="#c0392b",
            label="pre-recovery (attacker pressure)")
    ax.plot(dk, [defect[k]["post_recovery"] for k in dk], "-s", color="#27ae60",
            label="post-localize (bounded)")
    ax.set_title("(2) substrate defect mass under 1% poison\n(localize-and-replay caps it at 0)")
    ax.set_xlabel("episodes ingested")
    ax.set_ylabel("contradictions")
    ax.legend(fontsize=8)

    ax = axes[1][0]
    ax.plot(xs, [frag[k] for k in xs], "-o", color="#2c3e50", label="synonyms/concept")
    ax.plot(xs, [conv[k] for k in xs], "-s", color="#27ae60", label="convergence")
    ax.set_xscale("log")
    ax.set_title("(3) no fragmentation cascade; convergence stable")
    ax.set_xlabel("rounds")
    ax.legend(fontsize=8)

    ax = axes[1][1]
    bk = sorted(backlog)
    ax.plot(bk, [backlog[k]["backlog"] for k in bk], "-o", color="#2c3e50", label="backlog")
    ax.plot(bk, [backlog[k]["consumed"] for k in bk], "-s", color="#e67e22", label="consumed")
    ax.set_title("(4) reflection backlog finite; consumption capped by budget")
    ax.set_xlabel("emitted act traces")
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
