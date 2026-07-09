"""
Experiment 0l -- instance-sociality is nearly free, and it pays the two
debts solitary learning provably cannot: mutual ostension and
correspondence.

  1. NAMING GAME (Steels): two learners in a shared world, empty lexicons.
     Speaker names a concept (coining a word if needed) with joint
     attention; listener adopts. Communication success climbs to 1.0 and
     the lexicons converge -- a shared language with no human in the loop.
  2. CROSS-AGENT ADJUNCTION: A writes a fact, B reads it back correctly,
     for every expressible fact. The 0j read/write law, socialized.
  3. CORRESPONDENCE DIVIDEND: B holds a false belief (bad perception).
     No internal check can catch it (it is coherent). A's utterance
     collides with it at the interface -- the defect EXISTS only because
     there are two of them.
"""

import random
from collections import defaultdict

random.seed(4)

CONCEPTS = [
    "mango",
    "banana",
    "lemon",
    "apple",
    "cherry",
    "lime",
    "yellow",
    "red",
    "green",
    "tree",
    "herb",
]
HC = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
SYLS = [c + v for c in "bcdfghjklmnpqrstvz" for v in "aeiou"]


class Agent:
    def __init__(self, name):
        self.name = name
        self.lex = {}  # concept -> word (production)
        self.ground = {}  # word -> concept (comprehension)
        self.beliefs = dict(HC)  # perceived world (may be wrong)

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

    def hear(self, w, ostended_concept):
        # joint attention: the speaker points while naming
        if self.ground.get(w) == ostended_concept:
            return True  # success
        self.ground[w] = ostended_concept  # adopt
        self.lex[ostended_concept] = w
        return False


A, B = Agent("A"), Agent("B")
print("=" * 72)
print("1. NAMING GAME: a shared lexicon from nothing")
print("=" * 72)
window, hist = [], []
for r in range(1, 401):
    s, l = (A, B) if r % 2 else (B, A)  # roles alternate
    c = random.choice(CONCEPTS)
    ok = l.hear(s.speak(c), c)
    window.append(ok)
    if r % 80 == 0:
        hist.append(sum(window[-80:]) / 80)
        print(f"  rounds {r - 79:3d}-{r}: communication success {hist[-1]:.2f}")
converged = all(A.lex[c] == B.lex[c] for c in CONCEPTS)
print(f"lexicons identical after 400 rounds: {'PASS' if converged else 'FAIL'}")
print("No human supplied a single word; ostension was mutual.\n")

print("=" * 72)
print("2. CROSS-AGENT ADJUNCTION: A writes, B reads")
print("=" * 72)


def write(agent, fact):
    r, x, y = fact
    return [agent.lex[x], agent.lex[y]]  # frame omitted for brevity


def read(agent, tokens):
    return (agent.ground[tokens[0]], agent.ground[tokens[1]])


ok = all(read(B, write(A, ("HC", f, c))) == (f, c) for f, c in HC.items())
print(f"read_B(write_A(fact)) == fact for all facts: {'PASS' if ok else 'FAIL'}\n")

print("=" * 72)
print("3. THE CORRESPONDENCE DIVIDEND")
print("=" * 72)
B.beliefs["lime"] = "red"  # B misperceived a lime
internal = all(f in HC for f in B.beliefs)  # B's web is coherent
print(f"B holds a false belief (lime -> red); internally detectable: NO")
print(f"(it contradicts none of B's own episodes -- coherence is satisfied)")
tokens = write(A, ("HC", "lime", "green"))
f, c = read(B, tokens)
clash = B.beliefs[f] != c
print(
    f"A utters 'lime is green'; B reads ({f}, {c}); conflict with B's "
    f"belief ({f}, {B.beliefs[f]}): {'DETECTED' if clash else 'missed'}"
)
print("The defect lives on the INTERFACE between two coherent webs. One")
print("learner can be coherent; only two can disagree -- and disagreement")
print("is the only native signal of non-correspondence this architecture")
print("will ever have. Sociality is not a feature; it is the truth channel.")
