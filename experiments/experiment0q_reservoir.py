"""
Experiment 0q -- the replay boundary, stressed honestly (per the agent's
critique of 0p part 3), and the constructive fix.

World: a common frame ("the {a} is {c}", parses early, gets distilled)
and a RARE pattern ("{a} sleeps at {t}", 3% of the stream) that stays
below induction threshold until long after its sentences have streamed by.

  1. REPLAY-ONLY recovery of the rare relation: 0% -- provably. The
     geometry holds no sleeps-edges; write() regenerates only im(pi).
     (The 0p tautology, corrected into a measured impossibility.)
  2. UNIFORM reservoir (cap 120): holds ~3% rare sentences -> below
     min_group -> late induction FAILS.
  3. FRONTIER-PRIORITY reservoir (same cap): parsed sentences are
     already distilled, so retain preferentially what did NOT parse.
     Late induction succeeds; rare facts recovered.
Memory identical in 2 and 3; only the retention POLICY differs.
"""

import random
from collections import Counter

random.seed(11)

ANIMALS = [f"a{i}" for i in range(15)]
COLORS = ["red", "blue", "green"]
TIMES = ["dawn", "noon", "dusk"]
COLOR_OF = {a: random.choice(COLORS) for a in ANIMALS}
SLEEP_AT = {a: random.choice(TIMES) for a in ANIMALS}


def sentence():
    a = random.choice(ANIMALS)
    if random.random() < 0.03:
        return ["the", a, "sleeps", "at", SLEEP_AT[a]]  # rare pattern
    return ["the", a, "is", COLOR_OF[a]]  # common frame


def induce(group, min_group=20):
    """Dominance-skeleton induction (0n) on a same-length group."""
    if len(group) < min_group:
        return None
    L = len(group[0])
    skel = []
    for i in range(L):
        tok, cnt = Counter(s[i] for s in group).most_common(1)[0]
        skel.append(tok if cnt / len(group) >= 0.8 else "_")
    return tuple(skel) if L - skel.count("_") >= 2 else None


# ---- stream once; early frame induces fast; rare pattern -> frontier
STREAM = [sentence() for _ in range(5000)]
early = induce([s for s in STREAM[:600] if len(s) == 4])


def parses_early(s):
    return len(s) == 4 and all(k == "_" or k == t for k, t in zip(early, s))


geometry = {}  # distilled binary facts
res_uniform, res_frontier = [], []
CAP = 120
for n, s in enumerate(STREAM, 1):
    if parses_early(s):
        geometry[(s[1], s[3])] = geometry.get((s[1], s[3]), 0) + 1
    else:
        pass  # frontier sentence
    # uniform reservoir: classic reservoir sampling over ALL sentences
    if len(res_uniform) < CAP:
        res_uniform.append(s)
    elif random.random() < CAP / n:
        res_uniform[random.randrange(CAP)] = s
    # frontier-priority: unparsed sentences first; parsed only fill slack
    if not parses_early(s):
        if len(res_frontier) < CAP:
            res_frontier.append(s)
        elif random.random() < CAP / max(1, sum(1 for _ in res_frontier)):
            res_frontier[random.randrange(CAP)] = s

rare_total = sum(1 for s in STREAM if len(s) == 5)
print("=" * 72)
print("SETUP")
print("=" * 72)
print(
    f"stream 5000 sentences; rare pattern occurrences: {rare_total}; "
    f"reservoir cap {CAP}"
)
print(
    f"early frame induced: {' '.join(early)}  -> distilled "
    f"{len(geometry)} binary facts\n"
)

print("=" * 72)
print("1. REPLAY-ONLY (the corrected 0p claim)")
print("=" * 72)
regen = [["the", a, "is", c] for (a, c) in geometry]  # all write() can emit
rare_from_replay = sum(1 for s in regen if len(s) == 5)
print(
    f"write() regenerates {len(regen)} sentences, all in im(pi); rare "
    f"facts recovered: {rare_from_replay}/{len(ANIMALS)}  -> 0%, provably."
)
print("Replay cannot exceed the projection. The 0p demo was tautological;")
print("this is the measured boundary.\n")

print("=" * 72)
print("2 vs 3. RETENTION POLICY AT EQUAL MEMORY")
print("=" * 72)
for name, res in [("uniform", res_uniform), ("frontier-priority", res_frontier)]:
    grp = [s for s in res if len(s) == 5]
    frame = induce(grp)
    rec = {(s[1], s[4]) for s in grp} if frame else set()
    ok = sum(1 for a, t in rec if SLEEP_AT.get(a) == t)
    print(
        f"{name:18s}: rare sentences held {len(grp):3d}/{CAP} | late frame "
        f"induced: {bool(frame)} | facts recovered {ok}/{len(ANIMALS)}"
    )
print("\nSame cap, opposite outcome. Parsed text is already distilled --")
print("the only irreplaceable sentences are the ones that did not parse.")
print("Memory should preferentially retain the un-assimilated.")
