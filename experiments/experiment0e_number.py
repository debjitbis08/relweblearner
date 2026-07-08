"""
Experiment 0e -- constructing NUMBER from counting. No number is ever a node.

Input stream (all the learner ever sees):
  episodes = (members of collection A, members of collection B, pairing edges)
  Object ids and collection ids are opaque gensyms. Sizes are hidden ground
  truth used only for scoring.

The learner derives:
  MATCH(A,B)  := the pairing saturates both sides        (computed, not given)
  ONEMORE(A,B):= saturates A, exactly one unpaired in B  (computed, not given)
then:
  1. quotient: union-find over MATCH -> emergent class nodes  (the numbers)
  2. ONEMORE descends to classes -> the successor chain        (Peano, grown)
  3. counting routine: to number a new collection, pair it along the chain
  4. staged data -> knower-level progression (small classes crystallize first)
  5. a poisoned episode -> a class ONEMORE itself -> detectable defect
"""

import random
from collections import defaultdict

random.seed(7)


# ---------------------------------------------------- hidden world (scoring only)
def make_collections(n, max_size=5):
    cols, oid = {}, 0
    for i in range(n):
        size = random.choices(
            range(1, max_size + 1), weights=[1.0 / s for s in range(1, max_size + 1)]
        )[0]
        cols[f"K{i}"] = [f"o{oid + j}" for j in range(size)]
        oid += size
    return cols


def episode(cols, a, b):
    """Present A and B together with a maximal random pairing."""
    A, B = cols[a], cols[b]
    k = min(len(A), len(B))
    return (a, set(A), b, set(B), list(zip(random.sample(A, k), random.sample(B, k))))


# ---------------------------------------------------- the learner
class NumberLearner:
    def __init__(self):
        self.parent = {}  # union-find over collection ids
        self.onemore_ev = defaultdict(int)  # (repA, repB) evidence
        self.log = []

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def ingest(self, ep):
        a, A, b, B, pairs = ep
        pairedA = {p for p, q in pairs}
        pairedB = {q for p, q in pairs}
        leftA, leftB = A - pairedA, B - pairedB  # learner computes leftovers
        if not leftA and not leftB:  # MATCH: merge (sleep move)
            ra, rb = self.find(a), self.find(b)
            if ra != rb:
                self.parent[ra] = rb
                self.log.append(("merge", a, b))
        elif not leftA and len(leftB) == 1:
            self.onemore_ev[(a, b)] += 1
        elif not leftB and len(leftA) == 1:
            self.onemore_ev[(b, a)] += 1

    def classes(self):
        cls = defaultdict(set)
        for x in self.parent:
            cls[self.find(x)].add(x)
        return cls

    def class_onemore(self):
        m = defaultdict(set)
        for a, b in self.onemore_ev:
            m[self.find(a)].add(self.find(b))
        return m

    def repair(self):
        """Successor INJECTIVITY as an inference rule: if a class has two
        successor-classes, they must be equal -> merge them. Guarded: never
        merge two classes that have ONEMORE evidence between them (that
        merge would make a class ONEMORE of itself = genuine contradiction)."""
        genuine = set()
        changed = True
        while changed:
            changed = False
            m = self.class_onemore()
            for ca, targets in list(m.items()):
                ts = sorted({self.find(t) for t in targets})
                if self.find(ca) in ts:
                    genuine.add(
                        "a class is ONEMORE of itself (one-one principle violated)"
                    )
                    ts.remove(self.find(ca))
                if len(ts) >= 2:
                    t1, t2 = ts[0], ts[1]
                    linked = any(
                        self.find(a) in (t1, t2) and self.find(b) in (t1, t2)
                        for (a, b) in self.onemore_ev
                    )
                    if linked:
                        genuine.add(
                            "conflict unrepairable: candidate equals have "
                            "ONEMORE evidence between them"
                        )
                    else:
                        self.parent[t1] = t2
                        self.log.append(("injectivity-merge", t1, t2))
                        changed = True
        return sorted(genuine)

    def chain(self):
        """Successor on the quotient, after repair; returns chain map + defects."""
        genuine = self.repair()
        nxt = {}
        for ca, targets in self.class_onemore().items():
            ts = {self.find(t) for t in targets} - {self.find(ca)}
            if ts:
                nxt[self.find(ca)] = ts.pop()
        return nxt, genuine


def score(learner, cols):
    out = []
    for rep, members in sorted(learner.classes().items(), key=lambda kv: -len(kv[1])):
        sizes = {len(cols[m]) for m in members}
        out.append((len(members), sorted(sizes)))
    return out


# ==================================================== RUN 1: knower-level staging
print("=" * 72)
print("RUN 1 - staged data: early experience is mostly SMALL collections")
print("=" * 72)
cols = make_collections(60)
by_size = defaultdict(list)
for k, v in cols.items():
    by_size[len(v)].append(k)

L = NumberLearner()
# stage A: only collections of size <= 2 are ever presented together
small = by_size[1] + by_size[2]
for _ in range(150):
    L.ingest(episode(cols, *random.sample(small, 2)))
crystal = [(n, s) for n, s in score(L, cols) if n > 1]
print(f"after stage A: crystallized classes (members, hidden sizes): {crystal}")
print("-> a 'two-knower': classes for 1 and 2 exist; every larger collection")
print("   is still its own singleton -- an undifferentiated 'many'.\n")

# stage B: full experience
allk = list(cols)
for _ in range(800):
    L.ingest(episode(cols, *random.sample(allk, 2)))
nxt, defects = L.chain()  # runs injectivity repair first
crystal = [(n, s) for n, s in score(L, cols) if n > 1]
print(f"after stage B (post-repair): crystallized classes: {crystal}")
# walk the chain from the class with no predecessor
preds = set(nxt.values())
start = next(c for c in nxt if c not in preds)
seq, c = [start], start
while c in nxt:
    c = nxt[c]
    seq.append(c)
sizes_along_chain = [sorted({len(cols[m]) for m in L.classes()[c]}) for c in seq]
print(f"emergent successor chain, hidden sizes along it: {sizes_along_chain}")
print(f"well-definedness defects: {defects}")
print("Peano structure grown from pairing episodes; no number node was ever input.\n")

# ==================================================== RUN 2: the counting routine
print("=" * 72)
print("RUN 2 - counting a NEW collection = pairing along the chain")
print("=" * 72)
new = [f"x{i}" for i in range(4)]  # a fresh collection, size 4
cols["Knew"] = new
for pos, c in enumerate(seq, start=1):
    rep = next(iter(L.classes()[c]))
    _, A, _, B, pairs = episode(cols, rep, "Knew")
    la, lb = A - {p for p, _ in pairs}, B - {q for _, q in pairs}
    print(
        f"  pair against a class-{pos} representative: "
        f"{'MATCH -> its number is position ' + str(pos) if not la and not lb else 'no match, continue'}"
    )
    if not la and not lb:
        break
print("The count list = the chain of class representatives; tagging = pairing;")
print("cardinality = the position where pairing saturates. Counting, derived.\n")

# ==================================================== RUN 3: poisoned episode
print("=" * 72)
print("RUN 3 - a corrupt observation creates a DETECTABLE defect")
print("=" * 72)
a2, a3 = by_size[2][0], by_size[3][0]
fake = (
    a2,
    set(cols[a2]),
    a3,
    set(cols[a3]),
    list(zip(cols[a2] + [cols[a2][0]], cols[a3])),
)  # object tagged twice!
L.ingest(fake)  # false MATCH: merges 2 with 3
nxt, defects = L.chain()
print(f"defects after poison: {defects}")
print("A class that is ONEMORE of itself is a loop that cannot close --")
print("double-tagging an object breaks the one-one principle and the web says so.")
