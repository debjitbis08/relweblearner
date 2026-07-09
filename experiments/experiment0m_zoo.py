"""
Experiment 0m -- a ZOO of adopted creatures: population dynamics.

  1. DIALECTS: two communities of creatures play naming games only among
     neighbors -> each converges internally on its own coined lexicon;
     cross-community agreement stays near zero.
  2. CREOLIZATION: open a bridge between communities -> global agreement
     climbs; the dialects negotiate a common tongue.
  3. RUMOR vs CITATION: a false fact is taught to ONE creature by ONE
     owner, repeated 50 times, and retold enthusiastically. A true fact
     is taught once each by SIX different owners.
       - naive counting (commit at 3 hearings) commits the lie and
         spreads it;
       - origin-tracked provenance (commit at 3 DISTINCT ORIGINS, and
         retellings carry their original citations) never commits the
         lie anywhere, while the true fact diffuses population-wide.
     Gossip with citations: the P7 repeat-lie defense, socialized.
"""

import random
from collections import defaultdict

random.seed(9)

CONCEPTS = ["mango", "banana", "lemon", "apple", "lime", "tree", "herb", "sun"]
SYLS = [c + v for c in "bcdfghjklmnpqrstvz" for v in "aeiou"]


class Creature:
    def __init__(self, cid):
        self.id = cid
        self.lex, self.ground = {}, {}
        self.heard = defaultdict(int)  # fact -> naive count
        self.origins = defaultdict(set)  # fact -> origin owner ids
        self.committed_naive = set()
        self.committed_cited = set()

    def coin(self):
        while True:
            w = "".join(random.sample(SYLS, 2))
            if w not in self.ground:
                return w

    def speak(self, c):
        if c not in self.lex:
            w = self.coin()
            self.lex[c] = w
            self.ground[w] = c
        return self.lex[c]

    def hear_name(self, w, c):
        if self.ground.get(w) == c:
            return True
        self.ground[w] = c
        self.lex[c] = w
        return False

    def hear_fact(self, fact, origin_set):
        self.heard[fact] += 1
        self.origins[fact] |= origin_set
        if self.heard[fact] >= 3:
            self.committed_naive.add(fact)
        if len(self.origins[fact]) >= 3:
            self.committed_cited.add(fact)


N = 24
zoo = [Creature(i) for i in range(N)]
commA, commB = zoo[:12], zoo[12:]


def games(pop_pairs, rounds):
    for _ in range(rounds):
        s, l = random.sample(pop_pairs, 1)[0] if False else random.choice(pop_pairs)
        c = random.choice(CONCEPTS)
        l.hear_name(s.speak(c), c)


def agreement(g1, g2):
    pairs = [(a, b) for a in g1 for b in g2 if a is not b]
    hits = sum(
        1
        for a, b in pairs
        for c in CONCEPTS
        if a.lex.get(c) and a.lex.get(c) == b.lex.get(c)
    )
    return hits / (len(pairs) * len(CONCEPTS))


print("=" * 72)
print("1. DIALECTS (communities talk only internally)")
print("=" * 72)
pairsA = [(a, b) for a in commA for b in commA if a is not b]
pairsB = [(a, b) for a in commB for b in commB if a is not b]
games(pairsA, 1500)
games(pairsB, 1500)
print(
    f"within-A agreement {agreement(commA, commA):.2f} | "
    f"within-B {agreement(commB, commB):.2f} | "
    f"cross A-B {agreement(commA, commB):.2f}"
)
print("Two fully functional languages, mutually unintelligible. Dialects")
print("are the default geometry of a social graph.\n")

print("=" * 72)
print("2. CREOLIZATION (open the bridge)")
print("=" * 72)
bridge = [(a, b) for a in zoo for b in zoo if a is not b]
for k in range(3):
    games(bridge, 1200)
    print(
        f"  after {1200 * (k + 1)} mixed rounds: global agreement "
        f"{agreement(zoo, zoo):.2f}"
    )
print("Contact negotiates a common tongue; no committee designed it.\n")

print("=" * 72)
print("3. RUMOR vs CITATION")
print("=" * 72)
TRUE_FACT, FALSE_FACT = ("lime", "green"), ("lime", "red")
# six owners independently teach the true fact to their six creatures
for i in range(6):
    zoo[i].hear_fact(TRUE_FACT, {f"owner{i}"})
# one owner drills the false fact into one creature, 50 times
for _ in range(50):
    zoo[20].hear_fact(FALSE_FACT, {"owner20"})
# gossip: creatures retell facts they hold, CARRYING their citation sets
for _ in range(4000):
    s, l = random.sample(zoo, 2)
    tellable = list(s.origins.keys())
    if tellable:
        f = random.choice(tellable)
        l.hear_fact(f, s.origins[f])
naive_false = sum(1 for c in zoo if FALSE_FACT in c.committed_naive)
cited_false = sum(1 for c in zoo if FALSE_FACT in c.committed_cited)
cited_true = sum(1 for c in zoo if TRUE_FACT in c.committed_cited)
print(f"false fact committed under NAIVE counting:   {naive_false}/{N} creatures")
print(f"false fact committed under CITED provenance: {cited_false}/{N}")
print(f"true fact committed under CITED provenance:  {cited_true}/{N}")
print("Fifty repetitions and enthusiastic gossip never exceed ONE origin;")
print("six independent teachers cross the threshold everywhere they reach.")
print("A rumor is loud but cites itself. Citations are the immune system.")
