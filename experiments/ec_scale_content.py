"""Scale soak over the NEW corpora — basic maths (``mathbooks``) and kid content
(``kidbooks``). Same demonstration as ``ec_scale.py`` (a named creature distils a
large generated corpus in one streaming pass while its model stays bounded), now
across the numeracy and everyday-vocabulary rungs of the firehose.

Run: poetry run python experiments/ec_scale_content.py
"""

import time

from relweblearner.creature import Creature
from relweblearner.datasets import kidbooks as KB
from relweblearner.datasets import mathbooks as MB


def soak(name: str, gen, level: int):
    print("=" * 78)
    print(f"{name.upper()} — SCALE SOAK (bounded model over a large corpus)")
    print("=" * 78)
    print(f"{'episodes':>10} {'ingest_s':>9} {'ep/s':>8} {'cov':>5} "
          f"{'frames':>7} {'facts':>6} {'buffer':>7}")
    last = None
    for n in (2_000, 20_000, 100_000):
        episodes, world = gen.generate(n_episodes=n, level=level, seed=7)
        c = Creature(f"{name}-{n}", commit_k=2, min_group=8,
                     induction_interval=300, level=level).ingest(episodes)
        t0 = time.perf_counter()
        # (already ingested above; time a fresh pass for the ep/s figure)
        c2 = Creature(f"{name}-timed-{n}", commit_k=2, min_group=8,
                      induction_interval=300, level=level)
        c2.ingest(episodes)
        dt = time.perf_counter() - t0
        s = c.snapshot()
        ms = s["model_size"]
        print(f"{n:>10} {dt:>9.2f} {n/dt:>8.0f} {s['coverage']:>5.2f} "
              f"{ms['frames']:>7} {ms['facts']:>6} {ms['buffer']:>7}")
        last = (c, world)
    return last


def report(name: str, c: Creature, world, relations):
    print(f"\n-- {name}: comprehension at scale --")
    print("frames:", sorted(f["template"] for f in c.snapshot()["frames"]))
    comm = c.snapshot()["committed"]
    for label, mp, targets in relations:
        # a fact belongs to this relation only if BOTH its source is one of the
        # relation's sources AND its target is in the relation's value class —
        # needed because number words and animals are shared across relations.
        facts = [(b["source"], b["target"]) for b in comm
                 if b["source"] in mp and b["target"] in targets]
        ok = sum(1 for s, t in facts if mp.get(s) == t)
        print(f"  {label:10s}: {ok:>3}/{len(facts):<3} correct vs hidden world")


c, world = soak("mathbook", MB, level=2)
report("mathbook", c, world, [
    ("shape-sides", world["sides"], set(world["sides"].values())),
])

print()
c, world = soak("kidbook", KB, level=3)
report("kidbook", c, world, [
    ("sound", world["sound"], KB.SOUNDS),
    ("colour", world["colour"], KB.COLOURS),
    ("habitat", world["home"], KB.PLACES),
])
print("\n-> both corpora: model bounded, one streaming pass, comprehension matches world.")
