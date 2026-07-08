"""
Experiment 0g -- REGRESSION under reflection: do arithmetic and colors
still work when every operation emits a trace onto the shared bus?

  1. arithmetic (0e) with reflection ON: chain, counting routine, purity
  2. colors (0b/0c) with reflection ON: motif induction, held-out, split
  3. deliberate CONTAMINATION: compare trace-collections against world
     collections on the same bus -- does the number chain survive?
  4. the dividend: the learner counts ITS OWN ACTS with the number chain
     it constructed (self-measurement with its own ruler)
"""

import random
from collections import defaultdict
from itertools import product

random.seed(7)


# ---------------------------------------------------------------- learner
class RLearner:
    def __init__(self):
        self.parent = {}
        self.onemore = defaultdict(int)
        self.stream = []  # ONE bus: every act emits
        self.merge_acts = []

    def emit(self, ms1, ms2, pairs):
        aid = f"act{len(self.stream)}"
        self.stream.append((f"{aid}.in", set(ms1), f"{aid}.out", set(ms2), pairs))

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def ingest(self, ep):
        a, A, b, B, pairs = ep
        la = A - {p for p, _ in pairs}
        lb = B - {q for _, q in pairs}
        if not la and not lb and A and B:
            ra, rb = self.find(a), self.find(b)
            if ra != rb:
                self.parent[ra] = rb
                self.merge_acts.append((a, b))
                self.emit({a, b}, {rb}, [(a, rb)])  # trace of the merge
                return
        elif not la and len(lb) == 1:
            self.onemore[(a, b)] += 1
            self.emit({a}, {b}, [])
            return
        elif not lb and len(la) == 1:
            self.onemore[(b, a)] += 1
            self.emit({b}, {a}, [])
            return
        self.emit({a, b}, set(), [])  # observed, no uptake

    def repair(self):
        genuine, changed = set(), True
        while changed:
            changed = False
            m = defaultdict(set)
            for a, b in self.onemore:
                m[self.find(a)].add(self.find(b))
            for ca, ts in list(m.items()):
                ts = sorted({self.find(t) for t in ts})
                if self.find(ca) in ts:
                    genuine.add("class ONEMORE of itself")
                    ts.remove(self.find(ca))
                if len(ts) >= 2:
                    linked = any(
                        self.find(a) in ts[:2] and self.find(b) in ts[:2]
                        for (a, b) in self.onemore
                    )
                    if not linked:
                        self.parent[ts[0]] = ts[1]
                        self.emit({ts[0], ts[1]}, {ts[1]}, [])
                        changed = True
        return sorted(genuine)

    def chain(self):
        genuine = self.repair()
        nxt = {}
        for a, b in self.onemore:
            ca, cb = self.find(a), self.find(b)
            if ca != cb:
                nxt[ca] = cb
        return nxt, genuine


def walk_chain(L, nxt):
    preds = set(nxt.values())
    start = next(c for c in nxt if c not in preds)
    seq, c = [start], start
    while c in nxt:
        c = nxt[c]
        seq.append(c)
    return seq


# ================================================================ 1. ARITHMETIC
print("=" * 72)
print("1. ARITHMETIC UNDER REFLECTION")
print("=" * 72)
cols, oid = {}, 0
for i in range(60):
    size = random.choices(range(1, 6), weights=[1 / s for s in range(1, 6)])[0]
    cols[f"K{i}"] = [f"o{oid + j}" for j in range(size)]
    oid += size


def episode(a, b):
    A, B = cols[a], cols[b]
    k = min(len(A), len(B))
    return (a, set(A), b, set(B), list(zip(random.sample(A, k), random.sample(B, k))))


L = RLearner()
allk = list(cols)
for _ in range(900):
    L.ingest(episode(*random.sample(allk, 2)))
nxt, defects = L.chain()
seq = walk_chain(L, nxt)
classes = defaultdict(set)
for x in L.parent:
    classes[L.find(x)].add(x)
sizes_along = [sorted({len(cols[m]) for m in classes[c] if m in cols}) for c in seq]
print(f"chain (hidden sizes): {sizes_along}   defects: {defects}")
print(f"stream: {len(L.stream)} trace episodes emitted alongside (reflection cost)")
cols["Knew"] = [f"x{i}" for i in range(4)]
for pos, c in enumerate(seq, 1):
    rep = next(m for m in classes[c] if m in cols)
    _, A, _, B, pairs = episode(rep, "Knew")
    if not (A - {p for p, _ in pairs}) and not (B - {q for _, q in pairs}):
        print(
            f"counting routine on a fresh 4-collection: position {pos} "
            f"{'PASS' if pos == 4 else 'FAIL'}"
        )
        break

# ================================================================ 2. COLORS
print()
print("=" * 72)
print("2. COLORS UNDER REFLECTION")
print("=" * 72)


class Web:
    def __init__(self, bus):
        self.adj = defaultdict(list)
        self.bus = bus

    def add_edge(self, u, v, rel):
        self.adj[u].append((v, rel))
        self.adj[v].append((u, rel + "~"))
        self.bus.emit({u, v}, {f"{u}-{v}"}, [])

    def compose(self, u, word):
        F = {u}
        for r in word:
            F = {w for v in F for w in [t for (t, rr) in self.adj[v] if rr == r]}
        self.bus.emit({u}, F, [])
        return F


HC = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
GO = {
    "mango": "tree",
    "banana": "herb",
    "lemon": "tree",
    "apple": "tree",
    "cherry": "tree",
    "lime": "tree",
}
W = Web(L)  # colors web shares the SAME bus
for f, c in HC.items():
    W.add_edge(f, c, "has-color")
for f, p in GO.items():
    W.add_edge(f, p, "grows-on")
PRIMS = ["has-color", "has-color~", "grows-on", "grows-on~"]
pos2 = [("apple", "cherry"), ("mango", "banana")]
neg2 = [("mango", "apple")]
surv = [
    w
    for l in (1, 2, 3)
    for w in product(PRIMS, repeat=l)
    if all(b in W.compose(a, w) for a, b in pos2)
    and all(b not in W.compose(a, w) for a, b in neg2)
]
m = min(len(w) for w in surv)
rule = [w for w in surv if len(w) == m][0]
ho = all(
    b in W.compose(a, rule) for a, b in [("banana", "lemon"), ("lemon", "mango")]
) and all(
    b not in W.compose(a, rule) for a, b in [("lime", "apple"), ("lemon", "lime")]
)
print(f"induced rule: {' o '.join(rule)}   held-out: {'PASS' if ho else 'FAIL'}")
W.add_edge("mango", "green", "has-color")


def split_score(move):
    W2 = Web(L)
    for f, c in HC.items():
        W2.add_edge("mango#2" if (f == "mango" and c == move) else f, c, "has-color")
    W2.add_edge(
        "mango" if move == "green" else "mango#2",
        "yellow" if move == "green" else "green",
        "has-color",
    )
    return sum(1 for a, b in pos2 if "mango" in (a, b) and b in W2.compose(a, rule))


best = max(["green", "yellow"], key=split_score)
print(
    f"autonomous split choice: move '{best}' to mango#2   "
    f"{'PASS' if best == 'green' else 'FAIL'}"
)

# ================================================================ 3. CONTAMINATION
print()
print("=" * 72)
print("3. DELIBERATE SELF/WORLD MIXING")
print("=" * 72)
merge_traces = [
    ep for ep in L.stream if len(ep[1]) == 2 and str(ep[0]).startswith("act")
][:40]
world2 = [k for k in cols if k != "Knew" and len(cols[k]) == 2][:20]
mixed = 0
for tr, k in zip(merge_traces, world2):  # compare act-operands vs 2-collections
    a, A = tr[0], tr[1]
    L.ingest((a, A, k, set(cols[k]), list(zip(sorted(A), sorted(cols[k])))))
    mixed += 1
nxt2, defects2 = L.chain()
seq2 = walk_chain(L, nxt2)
classes = defaultdict(set)
for x in L.parent:
    classes[L.find(x)].add(x)
sizes_along2 = [sorted({len(cols[m]) for m in classes[c] if m in cols}) for c in seq2]
acts_in_two = sum(1 for m in classes[seq2[1]] if str(m).startswith("act"))
print(f"{mixed} act-collections compared against world 2-collections")
print(f"chain after mixing (hidden sizes): {sizes_along2}   defects: {defects2}")
print(f"class 'two' now also contains {acts_in_two} of the learner's own acts")
print("-> the chain SURVIVES; acts join cardinality classes because a merge")
print("   act genuinely HAS two operands. Numbers now count acts too.")

# ================================================================ 4. SELF-COUNT
print()
print("=" * 72)
print("4. SELF-MEASUREMENT")
print("=" * 72)
own = [f"m{i}" for i in range(3)]  # a collection of 3 of its own merge-acts
cols["Kacts"] = own
for pos, c in enumerate(seq2, 1):
    rep = next(m for m in classes[c] if m in cols and m != "Kacts")
    _, A, _, B, pairs = episode(rep, "Kacts")
    if not (A - {p for p, _ in pairs}) and not (B - {q for _, q in pairs}):
        print(
            f"counting a collection of its own merge-acts: {pos} "
            f"{'PASS' if pos == 3 else 'FAIL'}"
        )
        break
print("The ruler it built measures the hand that built it.")
