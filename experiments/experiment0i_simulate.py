"""
Experiment 0i -- SIMULATE, then act. Emergent from parts already built:
  fork the projection (event sourcing) + apply reversible moves + score
  by holonomy = try-before-commit. No new primitive; a new SEAM.

  1. imagine-then-commit: score a candidate merge on a FORK; commit to the
     real log only if it introduces no contradiction.
  2. counterfactual provenance: simulated acts emit traces flagged 'cf';
     they never contaminate the real projection (the boundary is a flag,
     not a separate mechanism).
  3. lookahead: among several candidate growth moves for an open query,
     pick the one whose SIMULATED result has least defect + least size.
  4. mental rehearsal of a lie: run a poisoned episode in simulation,
     observe the contradiction it WOULD cause, refuse to commit it --
     the learner declines an action by imagining its consequence.
"""

import random
from collections import defaultdict

random.seed(11)


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


class Projection:
    """A rebuildable belief state: union-find over committed match-edges."""

    def __init__(self):
        self.matches = []  # committed match edges (the log projection)
        self.onemores = set()

    def _uf(self, extra=()):
        p = {}

        def find(x):
            p.setdefault(x, x)
            while p[x] != x:
                p[x] = p[p[x]]
                x = p[x]
            return x

        for a, b in list(self.matches) + list(extra):
            p[find(a)] = find(b)
        return find

    def contradictions(self, extra_match=()):
        find = self._uf(extra_match)
        return sum(1 for (a, b) in self.onemores if find(a) == find(b))

    def n_classes(self, extra_match=()):
        find = self._uf(extra_match)
        return len(
            {find(a) for (a, b) in self.matches + list(extra_match) for a in (a, b)}
        )

    def fork(self):
        f = Projection()
        f.matches = list(self.matches)
        f.onemores = set(self.onemores)
        return f

    def commit_match(self, e):
        self.matches.append(e)

    def add_onemore(self, e):
        self.onemores.add(e)


class SimLearner:
    def __init__(self):
        self.proj = Projection()
        self.stream = []  # real + counterfactual, cf-flagged

    def emit(self, kind, payload, cf=False):
        self.stream.append({"kind": kind, "cf": cf, "payload": payload})

    def observe(self, ep):
        f = derive(ep)
        if not f:
            return
        if f[0] == "onemore":
            self.proj.add_onemore((f[1], f[2]))

    # -- the seam: try a candidate on a FORK, return its score, commit nothing
    def simulate_match(self, e):
        fk = self.proj.fork()
        before = fk.contradictions()
        after = fk.contradictions(extra_match=(e,))
        self.emit("sim-match", {"edge": e, "d_contra": after - before}, cf=True)
        return after - before

    def act_match(self, e):
        """Imagine first; commit only if the simulation is clean."""
        delta = self.simulate_match(e)
        if delta == 0:
            self.proj.commit_match(e)
            self.emit("commit-match", {"edge": e})
            return True
        self.emit("refuse-match", {"edge": e, "would_cause": delta})
        return False


# ---------------------------------------------------------------- setup
cols, oid = {}, 0
for i in range(40):
    size = random.choices(range(1, 5), weights=[1 / s for s in range(1, 5)])[0]
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
    A, B = cols[a], cols[b]
    return (a, set(A), b, set(B), list(zip(A + [A[0]], B)))


L = SimLearner()
for _ in range(400):  # learn onemore structure
    L.observe(episode(*random.sample(list(cols), 2)))

# ---------------------------------------------------------------- 1 + 2
print("=" * 72)
print("1+2. IMAGINE, THEN COMMIT (and cf never leaks)")
print("=" * 72)
good = (by_size[2][0], by_size[2][1])  # two genuine 2-collections
ok = L.act_match(good)
print(f"honest merge {good}: simulated delta 0 -> committed = {ok}")
real_before = list(L.proj.matches)
_ = L.simulate_match((by_size[2][0], by_size[3][0]))  # a pure thought experiment
print(
    f"ran a standalone simulation; real projection changed: "
    f"{L.proj.matches != real_before}  (expect False)"
)
cf = sum(1 for e in L.stream if e["cf"])
real = sum(1 for e in L.stream if not e["cf"])
print(f"stream: {real} real acts, {cf} counterfactual acts -- same bus, flagged.")
print("Imagined episodes are episodes; the boundary is a flag, not a wall.\n")

# ---------------------------------------------------------------- 3
print("=" * 72)
print("3. LOOKAHEAD: pick the move with the best simulated result")
print("=" * 72)
# open query: attach a fresh class; candidates differ in how they wire in.
# give the learner prior knowledge that makes one candidate collide.
L.proj.add_onemore((by_size[2][2], by_size[3][0]))  # fresh class distinct from the 3s
candidates = {
    "merge-into-2": (by_size[2][0], by_size[2][2]),
    "merge-into-3": (by_size[3][0], by_size[2][2]),  # collides via the onemore above
}
scored = {}
for name, e in candidates.items():
    fk = L.proj.fork()
    d = fk.contradictions(extra_match=(e,)) - fk.contradictions()
    scored[name] = d
    L.emit("sim-candidate", {"name": name, "d_contra": d}, cf=True)
best = min(scored, key=scored.get)
print(f"candidate simulated defects: {scored}")
print(f"chosen without committing the others: '{best}' (least simulated defect)")
print("Play is now EVALUATED proposal: it looks before it leaps.\n")

# ---------------------------------------------------------------- 4
print("=" * 72)
print("4. MENTAL REHEARSAL OF A LIE -> REFUSAL")
print("=" * 72)
# a poisoned episode arrives; the learner rehearses committing its match.
# NOTE: simulation only catches lies that collide with EXISTING knowledge.
# So first ensure the two target classes are known-distinct via onemore.
c2, c3 = by_size[2][0], by_size[3][0]
L.proj.add_onemore((c2, c3))  # observed: c2 is one-less-than c3
print(f"prior knowledge: {c2} ONEMORE-related to {c3} (they are distinct)")
bad_ep = poison(c2, c3)
f = derive(bad_ep)
print(f"incoming episode derives: {f}")
if f and f[0] == "match":
    committed = L.act_match((f[1], f[2]))
    print(f"committed after rehearsal: {committed}  (expect False)")
    refusals = [e for e in L.stream if e["kind"] == "refuse-match"]
    if refusals:
        print(
            f"refusal record: would_cause "
            f"{refusals[-1]['payload']['would_cause']} contradiction(s)"
        )
print("It declined the action by imagining the consequence first -- the")
print("difference between a system that DOES and one that CONSIDERS.")
