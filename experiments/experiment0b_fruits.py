"""
Experiment 0b -- fruits & colors: a NON-numeric domain on the same architecture.

What this tests that arithmetic could not:
  E. Partial, many-to-one relations (has-color): no true inverse exists;
     the composite has-color o has-color~ is an IDEMPOTENT (a domain
     marker), not the identity -- the inverse-semigroup rung of the ladder.
  F. Derived relation as MOTIF: same-color-as is never primitive; it is
     the commuting triangle  fruit --has-color--> color <--has-color-- fruit,
     and unseen same-color facts are predicted ZERO-SHOT by composition.
  G. Contradiction-driven CONCEPT SPLITTING: 'mango is green' + 'mango is
     yellow' forces (through composition) yellow = green, which collides
     with color-distinctness -> a defect no relabeling removes -> the
     growth move splits 'mango' into two concepts (unripe/ripe), and both
     halves are locally consistent afterward. Disambiguation, mechanized.

Frozen algebra: composition + dagger + partiality (steps may be undefined).
Only the web mutates. No numbers anywhere.
"""

from collections import defaultdict


class Web:
    def __init__(self):
        self.nodes = set()
        self.adj = defaultdict(list)  # u -> [(v, rel)]
        self.distinct = set()  # non-closure assertions: pairs known unequal
        self.growth_log = []

    def add_edge(self, u, v, rel, grown=False):
        self.nodes.update([u, v])
        self.adj[u].append((v, rel))
        self.adj[v].append((u, rel + "~"))  # dagger
        if grown:
            self.growth_log.append((u, v, rel))

    def targets(self, u, rel):
        """Multi-valued, PARTIAL step: may return zero, one, or many."""
        return [v for (v, r) in self.adj[u] if r == rel]

    def compose(self, u, rels):
        """All endpoints of paths from u along the relation word."""
        frontier = {u}
        for rel in rels:
            frontier = {w for v in frontier for w in self.targets(v, rel)}
        return frontier


# ---------------------------------------------------------------- build web

FRUITS = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
COLORS = ["yellow", "red", "green"]

W = Web()
for f, c in FRUITS.items():
    W.add_edge(f, c, "has-color")
# colors are distinct primitives (non-closure evidence, cf. D13-style counting)
for i in range(len(COLORS)):
    for j in range(i + 1, len(COLORS)):
        W.distinct.add(frozenset((COLORS[i], COLORS[j])))

# the ONLY observed same-color fact:
observed_same = [("mango", "banana")]

print("=" * 72)
print("E. PARTIALITY IS NATIVE (no inverse, only a pseudo-inverse)")
print("=" * 72)
print(
    f"has-color from 'yellow' (a color): {W.compose('yellow', ['has-color'])}"
    f"   <- undefined/empty: colors have no color; the walk just stops."
)
idem1 = W.compose("mango", ["has-color", "has-color~"])
idem2 = W.compose("mango", ["has-color", "has-color~", "has-color", "has-color~"])
print(f"(has-color o has-color~) from mango:        {sorted(idem1)}")
print(f"applied twice:                              {sorted(idem2)}")
print(
    f"idempotent (e o e = e): {'PASS' if idem1 == idem2 else 'FAIL'}"
    f"   <- a domain marker, not the identity: it returns ALL yellow"
)
print("     fruits, not just mango. This relation has no group inverse;")
print("     the algebra needed here is inverse-semigroup shaped.\n")

print("=" * 72)
print("F. DERIVED RELATION AS MOTIF: same-color-as := has-color o has-color~")
print("=" * 72)
predicted = set()
for f in FRUITS:
    for g in W.compose(f, ["has-color", "has-color~"]):
        if g != f and g in FRUITS:
            predicted.add(frozenset((f, g)))

for a, b in observed_same:
    ok = frozenset((a, b)) in predicted
    print(
        f"observed fact ({a} ~ {b}) reproduced by the motif: "
        f"{'PASS' if ok else 'FAIL'}  -> banked as a 2-cell (commuting triangle)"
    )

unseen = predicted - {frozenset(p) for p in observed_same}
truth = {
    frozenset((f, g))
    for f in FRUITS
    for g in FRUITS
    if f != g and FRUITS[f] == FRUITS[g]
}
print(
    f"zero-shot predictions (never observed): {sorted(tuple(sorted(p)) for p in unseen)}"
)
print(f"all correct vs ground truth: {'PASS' if predicted == truth else 'FAIL'}")
print("Compositional generalization in a domain with no numbers at all.\n")

print("=" * 72)
print("G. CONTRADICTION -> DEFECT -> SPLIT (concept formation)")
print("=" * 72)
# new observation: an unripe mango
W.add_edge("mango", "green", "has-color")


def color_defects(web):
    """Loops color <-has-color- fruit -has-color-> color' force color = color';
    if the pair is asserted-distinct, that's a defect no relabeling removes."""
    out = []
    for f in list(web.nodes):
        cs = web.targets(f, "has-color")
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if frozenset((cs[i], cs[j])) in web.distinct:
                    out.append((f, cs[i], cs[j]))
    return out


d = color_defects(W)
print(f"after observing 'mango has-color green': defects = {d}")
print("relabel: renaming nodes changes nothing (structure is the same) -> can't fix")
print(
    "rewire:  deleting either edge = discarding an observation -> data is not a belief"
)
print("=> persistent class: pay the growth move. Resolution = SPLIT the node.\n")

# split: grow a new node, move ONE observation to it
W.adj["mango"] = [
    (v, r) for (v, r) in W.adj["mango"] if not (r == "has-color" and v == "green")
]
W.adj["green"] = [
    (v, r) for (v, r) in W.adj["green"] if not (r == "has-color~" and v == "mango")
]
W.add_edge("mango#2", "green", "has-color", grown=True)

d = color_defects(W)
print(f"after split (grew node 'mango#2'): defects = {d}   (expect [])")
same_as_lime = [
    f for f in W.compose("lime", ["has-color", "has-color~"]) if f != "lime"
]
same_as_banana = [
    f for f in W.compose("banana", ["has-color", "has-color~"]) if f != "banana"
]
print(f"what is same-color-as lime?   {same_as_lime}   <- the unripe concept")
print(
    f"what is same-color-as banana? {sorted(same_as_banana)}   <- the ripe one kept its place"
)
print(f"growth log: {W.growth_log}")
print("\nOne name, two concepts; the web now knows it. What a mind calls")
print("'realizing mango has a ripeness dimension' is here one grow move")
print("triggered by one undischargeable defect class.")
