"""
Experiment 0p -- graph-native compression: keep what was LEARNED plus
per-source deltas; retract by DECREMENT; recover retroactivity by
GENERATIVE REPLAY. No episode is stored anywhere.

  1. stream 30,000 episodes -> memory O(distinct facts), not O(episodes)
  2. a 2-source collusion commits a lie (k=2) -- then retracting one
     source is a DECREMENT-JOIN over aggregates: the lie un-commits,
     honest facts survive, zero episodes consulted
  3. a frame induced LATE never saw the dropped text: regenerate
     sentences from geometry via write() and reparse -- retroactivity
     recovered from the codec, not the corpus
"""

import random, sys

random.seed(3)

HC = {f"a{i}": random.choice(["red", "blue", "green", "gold"]) for i in range(20)}
SOURCES = ["s1", "s2", "s3", "s4", "s5", "s6"]


class DeltaStore:  # per-(edge, source) counts + inverse index
    def __init__(self, k=2):
        self.ev = {}  # (s,t) -> {source: count}
        self.by_source = {}  # source -> set of edges
        self.k = k

    def observe(self, fact, source):
        d = self.ev.setdefault(fact, {})
        d[source] = d.get(source, 0) + 1
        self.by_source.setdefault(source, set()).add(fact)

    def committed(self):
        return {f for f, d in self.ev.items() if len(d) >= self.k}

    def retract_source(self, source):  # CRDT decrement-join: remove one summand
        for f in self.by_source.pop(source, set()):
            self.ev[f].pop(source, None)
            if not self.ev[f]:
                del self.ev[f]


S = DeltaStore(k=2)
n_ep = 30000
for _ in range(n_ep):  # massively repetitive honest stream
    a = random.choice(list(HC))
    S.observe((a, HC[a]), random.choice(SOURCES))

print("=" * 72)
print("1. MEMORY = LEARNED STRUCTURE, NOT EPISODES")
print("=" * 72)
cells = sum(len(d) for d in S.ev.values())
print(f"episodes streamed: {n_ep}   facts held: {len(S.ev)}   evidence cells: {cells}")
print(
    f"an append-only log would hold {n_ep} entries; the store holds {cells} counters.\n"
)

print("=" * 72)
print("2. RETRACTION BY DECREMENT (no log anywhere)")
print("=" * 72)
S.observe(("a0", "black"), "liar1")
S.observe(("a0", "black"), "liar2")
lie = ("a0", "black")
print(f"collusion: 2 sources teach {lie} -> committed: {lie in S.committed()}")
before = len(S.committed())
S.retract_source("liar1")
print(
    f"retract source 'liar1' (decrement-join): lie committed now: "
    f"{lie in S.committed()}"
)
print(
    f"honest facts before/after: {before - 1}/{len(S.committed())} "
    f"(all survive: {len(S.committed()) == before - 1})"
)
print("Replay-with-exclusions semantics, recovered from aggregates alone.\n")

print("=" * 72)
print("3. GENERATIVE REPLAY: the geometry is the codec")
print("=" * 72)


def write_F5(fact):
    return ["i", "see", "a", fact[1], fact[0]]  # old frame


def parse_F4(toks):  # frame induced LATE
    return (
        (toks[1], toks[3])
        if len(toks) == 4 and toks[0] == "the" and toks[2] == "is"
        else None
    )


def write_F4(fact):
    return ["the", fact[0], "is", fact[1]]


regenerated = [write_F4(f) for f in S.committed()]  # write() from geometry
reparsed = {parse_F4(t) for t in regenerated}
print(f"late frame 'the _ is _' never saw the 30,000 dropped sentences;")
print(
    f"regenerated {len(regenerated)} sentences from geometry, reparsed "
    f"{len(reparsed & S.committed())}/{len(S.committed())} facts under it."
)
print("Retroactivity from write(), not from a corpus: read(write(x)) = x")
print("is not just a correctness law -- it is the decompressor.")
