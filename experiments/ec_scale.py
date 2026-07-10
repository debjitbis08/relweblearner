"""Scale soak — the streaming Creature over large generated corpora.

Demonstrates the scalable substrate: a named creature distils a corpus that is
orders of magnitude larger than any hand-training session, in one streaming pass,
while its MODEL stays bounded (memory grows with what is learned, not what is
read) and persists to a compact file. Contrast the old Reader, which keeps every
episode in a log and re-derives from scratch.

Run: poetry run python experiments/ec_scale.py
"""

import tempfile
import time
from pathlib import Path

from relweblearner.creature import Creature
from relweblearner.datasets import patternbooks as PB

print("=" * 78)
print("STREAMING CREATURE — SCALE SOAK (bounded model over a large corpus)")
print("=" * 78)
print(f"{'episodes':>10} {'ingest_s':>9} {'ep/s':>8} {'cov':>5} {'frames':>7} "
      f"{'facts':>6} {'buffer':>7} {'model_kb':>9} {'assim':>7}")

world_truth = None
for n in (1_000, 5_000, 20_000, 100_000):
    episodes, world = PB.generate(n_episodes=n, level=2, seed=7)
    world_truth = world
    c = Creature(f"scholar-{n}", commit_k=2, min_group=8, induction_interval=300, level=2)

    t0 = time.perf_counter()
    c.ingest(episodes)
    dt = time.perf_counter() - t0

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
        c.save(fh.name)
        kb = Path(fh.name).stat().st_size / 1024
    Path(fh.name).unlink()

    s = c.snapshot()
    ms = s["model_size"]
    print(f"{n:>10} {dt:>9.2f} {n/dt:>8.0f} {s['coverage']:>5.2f} {ms['frames']:>7} "
          f"{ms['facts']:>6} {ms['buffer']:>7} {kb:>8.1f}K {s['assimilation_rate']:>7.4f}")

# correctness at scale: committed colour beliefs match the hidden world
print("\n" + "=" * 78)
print("COMPREHENSION AT SCALE (the last creature)")
print("=" * 78)
committed = [b for b in s["committed"] if b["target"] in PB.COLOURS]
correct = sum(1 for b in committed if world_truth[b["source"]]["colour"] == b["target"])
print(f"committed colour facts: {len(committed)}  correct vs hidden world: {correct}/{len(committed)}")
print("frames it induced:", [f["template"] for f in s["frames"]])
a = committed[0]["source"] if committed else "bear"
print(f"ask 'the {a} is ?' ->", c.answer(f"the {a} is ?").get("answers", [{}])[:1])
print("say (3):", [x["sentence"] for x in c.say(limit=3)])
print("\nidentity:", s["identity"])
print("-> model bounded, one streaming pass, no episode log retained.")
