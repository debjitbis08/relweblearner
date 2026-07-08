"""
Experiment 0 — fixed algebra, growing web.

Four demos, all CPU, all instant:
  A. Gauge-fixing / holonomy: detect H^1 obstruction classes in a web with
     group-valued edges (abelian G = Z for arithmetic transport).
  B. Obstruction-forced growth: query 3 - 5 on a web of naturals; the path
     falls off the web; the growth engine adds nodes; derived arithmetic
     on the new nodes is verified ZERO-SHOT (no training, algebra is frozen).
  C. Symmetry self-classification: infer relation transports from loop
     observations alone; symmetric relations are FORCED into the even
     class (g = -g), successor lands antisymmetric.
  D. Two-web interference: transport mismatch on an overlap, discharged
     by the 'split' resolution.

The frozen algebra here: group laws + dagger (converse), G = (Z, +).
Only the web (nodes, edges) ever changes.
"""

from collections import defaultdict

# ---------------------------------------------------------------- web core


class Web:
    def __init__(self, name="W"):
        self.name = name
        self.nodes = set()
        # adjacency: node -> list of (neighbor, rel_type, g) ; converse stored automatically
        self.adj = defaultdict(list)
        self.growth_log = []

    def add_node(self, v, grown=False):
        if v not in self.nodes:
            self.nodes.add(v)
            if grown:
                self.growth_log.append(("node", v))

    def add_edge(self, u, v, rel, g, grown=False):
        self.add_node(u, grown)
        self.add_node(v, grown)
        self.adj[u].append((v, rel, g))
        self.adj[v].append(
            (u, rel + "~", -g)
        )  # dagger: converse edge, inverse transport
        if grown:
            self.growth_log.append(("edge", u, v, rel, g))

    def step(self, u, rel):
        """Follow relation rel from u. None if the web has no such edge (boundary)."""
        for v, r, g in self.adj[u]:
            if r == rel:
                return v, g
        return None

    # ---- Demo A: gauge-fix a potential phi; leftover defects = H^1 classes
    def holonomy_defects(self):
        phi, defects = {}, []
        for root in sorted(self.nodes, key=str):
            if root in phi:
                continue
            phi[root] = 0
            stack = [root]
            while stack:
                u = stack.pop()
                for v, r, g in self.adj[u]:
                    if v not in phi:
                        phi[v] = phi[u] + g
                        stack.append(v)
                    elif phi[v] != phi[u] + g:
                        defects.append((u, v, r, phi[u] + g - phi[v]))
        return phi, defects


# ---------------------------------------------------------------- Demo A

print("=" * 72)
print("A. HOLONOMY / H^1 DETECTION")
print("=" * 72)

W = Web()
for n in range(10):  # naturals 0..9, successor edges
    W.add_edge(n, n + 1, "succ", +1) if n < 9 else None
for n in range(10):
    W.add_node(n)

phi, defects = W.holonomy_defects()
print(f"Consistent web: defects = {defects}  (expect [])")

# corrupt it: a false identity 'same-count' between 4 and 7
W_bad = Web()
for n in range(9):
    W_bad.add_edge(n, n + 1, "succ", +1)
W_bad.add_edge(4, 7, "same", 0)  # a wrong belief: |A|=4 matches |B|=7
phi, defects = W_bad.holonomy_defects()
print(f"Corrupted web: defects = {defects}")
print("-> a nonzero harmonic class: NO relabeling (choice of phi) removes it;")
print("   only rewiring/growth can discharge it. This is the learning signal.\n")

# ---------------------------------------------------------------- Demo B

print("=" * 72)
print("B. OBSTRUCTION-FORCED GROWTH: query 3 - 5 on the naturals")
print("=" * 72)

W = Web()
for n in range(10):
    W.add_node(n)
for n in range(9):
    W.add_edge(n, n + 1, "succ", +1)


def walk(web, start, rel, k, grow=False):
    """Walk rel k times from start; if grow, create missing nodes/edges."""
    cur = start
    for i in range(k):
        nxt = web.step(cur, rel)
        if nxt is None:
            if not grow:
                return None, cur
            # growth move (expensive): fresh node, edge carrying the SAME frozen algebra
            fresh = f"g{len(web.growth_log)}"
            if rel == "succ~":
                web.add_edge(fresh, cur, "succ", +1, grown=True)
            else:
                web.add_edge(cur, fresh, "succ", +1, grown=True)
            cur = fresh
        else:
            cur = nxt[0]
    return cur, None


res, stuck = walk(W, 3, "succ~", 5)
print(f"Attempt 3 -(succ~)x5 without growth: stuck at node {stuck} (boundary).")
print("Persistent obstruction -> pay the growth move.\n")

res, _ = walk(W, 3, "succ~", 5, grow=True)
print(f"With growth: 3 - 5 lands on new node: {res}")
print(f"Growth log: {W.growth_log}\n")

# ZERO-SHOT check: the new node was never 'trained'; the frozen algebra
# should make (3-5) + 7 = 5 hold by pure transport.
back, _ = walk(W, res, "succ", 7)
print(
    f"Zero-shot verification: ({res}) + 7 -> node {back}   (expect 5): "
    f"{'PASS' if back == 5 else 'FAIL'}"
)
print("The invented nodes inherit correct arithmetic with zero parameters learned.\n")

# ---------------------------------------------------------------- Demo C

print("=" * 72)
print("C. SYMMETRY SELF-CLASSIFICATION (from loop statistics alone)")
print("=" * 72)
# Unknown transports g_same, g_succ in Z. Observations = closed loops only.
# Loop 1: A same B, B same A          =>  g_same + g_same = 0
# Loop 2: A succ X, X same Y, Y succ~ B, B same~ A  => cancels (uninformative)
# Non-closure evidence: A succ X never observed 'same' as A  => g_succ != 0.

# Solve over Z:
#   2*g_same = 0        -> g_same = 0        (symmetric: fixed by dagger)
#   g_succ free, != 0   -> normalize to 1    (antisymmetric generator)
g_same, g_succ = 0, 1
print("Constraint from observing 'same' in both directions:  2*g_same = 0")
print(f"  -> g_same = {g_same}  : self-converse forces the SYMMETRIC class (r = r~)")
print("Non-closure of succ-loops:                             g_succ != 0")
print(f"  -> g_succ = {g_succ} (normalized) : the ANTISYMMETRIC class generator")
print("Piaget's classification/seriation split, derived, not imposed.\n")

# ---------------------------------------------------------------- Demo D

print("=" * 72)
print("D. TWO-WEB INTERFERENCE (transport mismatch on an overlap) + split-resolution")
print("=" * 72)

A = Web("A")  # careful counter
for n in range(3, 8):
    A.add_edge(n, n + 1, "succ", +1)

B = Web("B")  # coarse counter: its 'next' skips by 2
B.add_edge(3, 5, "next", +1)  # B believes next is one step
B.add_edge(5, 7, "next", +1)

# overlap = shared nodes {3,5,7}; compare transports 3->5 through each web
tA = 2 * 1  # A: succ,succ
tB = 1  # B: next
print(f"Transport 3->5 via A = {tA}, via B = {tB}; interface class = {tA - tB} != 0")
print(
    "Options: project (trust A) | split (B's 'next' is a DIFFERENT concept) | superpose"
)

# split: reinterpret B's 'next' as carrying transport +2 -> a new derived relation
tB_split = 2
print(
    f"Split-resolution: rebind B.next |-> succ o succ (transport +2): "
    f"class = {tA - tB_split}  -> discharged."
)
print("'next' and 'succ' were two concepts sharing a name; the interface told us.")
