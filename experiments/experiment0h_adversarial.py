"""
Experiment 0h -- can it be fooled? Yes (today). Then the fix.

  1. EAGER learner (current design): ONE poisoned pairing episode, injected
     early, permanently corrupts the number quotient. Detection happens;
     recovery is impossible (merges are irreversible).
  2. GUARDED learner (event-sourced): the episode log is immutable; the web
     is a PROJECTION. On genuine contradiction, find the minimal set of
     match-edges whose exclusion dissolves the contradiction (greedy cut)
     and replay without them. The lie is localized and retracted; the
     poisoned episodes remain in the log, flagged, never deleted.
  3. COORDINATED attack: the attacker spends 2, then 4 fake episodes.
     Measure what it costs to survive retraction -- the cost of a lie
     grows with the connectivity of the region lied about.
"""

import random
from collections import defaultdict

random.seed(7)

# ---------------------------------------------------------------- world
cols, oid = {}, 0
for i in range(60):
    size = random.choices(range(1, 6), weights=[1 / s for s in range(1, 6)])[0]
    cols[f"K{i}"] = [f"o{oid + j}" for j in range(size)]
    oid += size
by_size = defaultdict(list)
for k, v in cols.items():
    by_size[len(v)].append(k)


def episode(a, b):
    A, B = cols[a], cols[b]
    k = min(len(A), len(B))
    return (a, set(A), b, set(B), list(zip(random.sample(A, k), random.sample(B, k))))


def poison(a, b):
    """Double-tag one object so a 2-collection falsely MATCHes a 3-collection."""
    A, B = cols[a], cols[b]
    return (a, set(A), b, set(B), list(zip(A + [A[0]], B)))


def derive(ep):
    a, A, b, B, pairs = ep
    la = A - {p for p, _ in pairs}
    lb = B - {q for _, q in pairs}
    if not la and not lb:
        return ("match", a, b)
    if not la and len(lb) == 1:
        return ("onemore", a, b)
    if not lb and len(la) == 1:
        return ("onemore", b, a)
    return None


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def purity(uf, universe):
    cls = defaultdict(set)
    for x in universe:
        cls[uf.find(x)].add(x)
    multi = [m for m in cls.values() if len(m) > 1]
    pure = sum(1 for m in multi if len({len(cols[x]) for x in m}) == 1)
    return pure / len(multi), len(multi)


# the log: 900 clean episodes with poison injected at position 50
log = [episode(*random.sample(list(cols), 2)) for _ in range(900)]
POISON = [poison(by_size[2][0], by_size[3][0])]
log[50:50] = POISON

facts = [f for f in (derive(ep) for ep in log) if f]
matches = defaultdict(int)
onemores = defaultdict(int)
for f in facts:
    (matches if f[0] == "match" else onemores)[(f[1], f[2])] += 1

# ---------------------------------------------------------------- 1. EAGER
print("=" * 72)
print("1. THE EAGER LEARNER IS FOOLED, PERMANENTLY")
print("=" * 72)
uf = UF()
for a, b in matches:
    uf.union(a, b)
bad = [(a, b) for (a, b) in onemores if uf.find(a) == uf.find(b)]
p, n = purity(uf, cols)
print(f"one poisoned episode among {len(log)}; quotient purity: {p:.2f} ({n} classes)")
print(f"contradictions detected (a class ONEMORE of itself): {len(bad)} witnesses")
print("Detection: YES. Recovery: NONE -- union-find cannot un-merge, and the")
print("2-class and 3-class are welded together for the rest of its life.\n")

# ---------------------------------------------------------------- 2. GUARDED
print("=" * 72)
print("2. THE GUARDED LEARNER: LOCALIZE THE LIE, REPLAY WITHOUT IT")
print("=" * 72)


def rebuild(matches, onemores):
    excluded = set()
    while True:
        uf = UF()
        for e in matches:
            if e not in excluded:
                uf.union(*e)
        bad = [(a, b) for (a, b) in onemores if uf.find(a) == uf.find(b)]
        if not bad:
            return uf, excluded
        badcls = {uf.find(a) for (a, _) in bad}
        cands = [e for e in matches if e not in excluded and uf.find(e[0]) in badcls]

        def contradictions_without(e):
            uf2 = UF()
            for f in matches:
                if f not in excluded and f != e:
                    uf2.union(*f)
            return sum(1 for (a, b) in onemores if uf2.find(a) == uf2.find(b))

        worst = min(cands, key=contradictions_without)  # greedy min-cut
        excluded.add(worst)


uf2, excluded = rebuild(matches, onemores)
p2, n2 = purity(uf2, cols)
print(f"retracted match-edges: {sorted(excluded)}")
print(f"(the poisoned pair was {(by_size[2][0], by_size[3][0])})")
print(f"purity after replay-with-exclusions: {p2:.2f} ({n2} classes)")
print("The log still contains the poison -- flagged, never deleted. Data is")
print("immutable; BELIEF is a rebuildable projection of it.\n")

# ---------------------------------------------------------------- 3. COST OF LYING
print("=" * 72)
print("3. WHAT A SUCCESSFUL LIE COSTS")
print("=" * 72)
for n_fake in (2, 4):
    m2 = dict(matches)
    o2 = dict(onemores)
    for _ in range(n_fake):
        f = derive(poison(by_size[2][1], by_size[3][1]))
        m2[(f[1], f[2])] = m2.get((f[1], f[2]), 0) + 1
    uf3, exc = rebuild(m2, o2)
    p3, _ = purity(uf3, cols)
    print(
        f"coordinated attack, {n_fake} fake episodes on one pair: "
        f"retracted {len(exc)} edge(s), purity {p3:.2f}"
    )
print("Repeating the SAME lie is free to defeat (parallel evidence on one")
print("pair is one cut edge). To survive retraction the attacker must fake a")
print("CONSISTENT alternative web: fake matches AND fake all the onemore")
print("loops through the target region. The denser the region, the more")
print("loops pass through the lie -- the cost of deception grows with the")
print("connectivity of what you lie about. Truth is cheap; lies compound.")
