"""Full-integration smoke test (next-step 2): layers wired together stay bounded.

A small, fast version of the Part D′ integration soak: complete agents (number
substrate + society lexicon + reflection bus) interacting concurrently. Asserts
the correctness/resource curves stay bounded when the layers run together — the
cross-layer check the home-substrate soaks could not make. (The super-linear
recovery-cost finding is reported by ``experiments/verify_soak_integrated.py``,
not gated here.)
"""

from __future__ import annotations

import random

from relweblearner import audit, reflection, society as S
from relweblearner.datasets import counting as C
from relweblearner.datasets.counting import pairing_episode, poison_episode
from relweblearner.journal import Journal
from relweblearner.number import NumberLearner


class _Agent:
    def __init__(self, i):
        self.learner = NumberLearner()
        self.soc = S.Agent(f"g{i}", owner=f"g{i}", seed=i)
        self.trace = Journal(f"t{i}")
        self.excluded: set = set()


def test_integrated_layers_stay_bounded():
    cols = C.make_collections(50, seed=7)
    smalls = [k for k, v in cols.items() if len(v) == 2]
    bigs = [k for k, v in cols.items() if len(v) == 3]
    keys = list(cols)
    concepts = [f"c{i}" for i in range(4)]
    agents = [_Agent(i) for i in range(3)]
    rng = random.Random(0)

    for _ in range(6000):
        a, b = rng.sample(agents, 2)
        S.naming_round(a.soc, b.soc, rng.choice(concepts))         # society
        if rng.random() < 0.01 and smalls and bigs:                # 1% poison
            b.learner.ingest(poison_episode(cols, rng.choice(smalls), rng.choice(bigs)))
        else:                                                      # substrate
            b.learner.ingest(pairing_episode(cols, *rng.sample(keys, 2), rng=rng))

    for ag in agents:
        chain = ag.learner.project()                               # real projection
        mp, om = audit.derive_facts(ag.learner.journal, k=2)
        excluded, _ = audit.localize(mp, om)                       # recovery
        after = {p: e for p, e in mp.items() if p not in excluded}
        reflection.emit_defect_reports(chain.web, ag.trace)        # reflection
        bk = reflection.bounded_consume(ag.trace, budget=50)

        assert len(chain.order) <= 6                               # concept memory bounded
        assert audit.contradictions(after, om) == []              # defect mass recovers to 0
        assert bk["consumed"] <= 50                                # backlog capped by budget

    # society still converges with the substrate running underneath it
    assert S.lexical_convergence([a.soc for a in agents], concepts) >= 0.9
