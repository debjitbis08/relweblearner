"""
Experiment 0c -- actual LEARNING: nothing about the target concept is coded.

The learner receives:
  - primitive observed edges: has-color facts, grows-on facts (a distractor)
  - a few labeled examples of 'same-color-as' (positives, and later negatives)
It must INDUCE the definition of same-color-as as a relation-word over the
primitives, by search over a hypothesis space, under a parsimony prior.

Learning criteria this run demonstrates:
  1. hypothesis space + search   (all relation-words up to length 3: 84 words)
  2. data-dependence             (starved data -> AMBIGUOUS/WRONG; more data -> right)
  3. generalization              (held-out pairs never seen in training)
  4. autonomous structure choice (the mango split is DECIDED by the learner,
                                  scored against the relational record)
"""

from collections import defaultdict
from itertools import product


class Web:
    def __init__(self):
        self.adj = defaultdict(list)

    def add_edge(self, u, v, rel):
        self.adj[u].append((v, rel))
        self.adj[v].append((u, rel + "~"))

    def targets(self, u, rel):
        return [v for (v, r) in self.adj[u] if r == rel]

    def compose(self, u, word):
        frontier = {u}
        for rel in word:
            frontier = {w for v in frontier for w in self.targets(v, rel)}
        return frontier


# ------------------------------------------------- primitive observations
# (the learner sees these edges; it is NOT told what same-color-as means)
HASCOLOR = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
GROWSON = {
    "mango": "tree",
    "banana": "herb",
    "lemon": "tree",
    "apple": "tree",
    "cherry": "tree",
    "lime": "tree",
}
W = Web()
for f, c in HASCOLOR.items():
    W.add_edge(f, c, "has-color")
for f, p in GROWSON.items():
    W.add_edge(f, p, "grows-on")

FRUITS = set(HASCOLOR)
PRIMS = ["has-color", "has-color~", "grows-on", "grows-on~"]


# ------------------------------------------------- the induction engine
def all_words(maxlen):
    for L in range(1, maxlen + 1):
        yield from product(PRIMS, repeat=L)


def consistent(word, positives, negatives):
    for a, b in positives:
        if b not in W.compose(a, word):
            return False
    for a, b in negatives:
        if b in W.compose(a, word):
            return False
    return True


def induce(positives, negatives, maxlen=3):
    """Return ALL minimal-length consistent hypotheses (parsimony prior)."""
    survivors = [w for w in all_words(maxlen) if consistent(w, positives, negatives)]
    if not survivors:
        return []
    m = min(len(w) for w in survivors)
    return [w for w in survivors if len(w) == m]


n_hyp = sum(len(PRIMS) ** L for L in range(1, 4))
print(f"hypothesis space: all relation-words up to length 3 = {n_hyp} candidates\n")

# ------------------------------------------------- Run 1: starved data
print("=" * 72)
print("RUN 1 - one training example, no negatives")
print("=" * 72)
pos1 = [("apple", "cherry")]
h1 = induce(pos1, [])
print(f"training: same-color positives = {pos1}, negatives = []")
print(f"minimal consistent hypotheses: {h1}")
print("-> AMBIGUOUS: the distractor (grows-on o grows-on~) also explains the")
print("   data, because apple and cherry share a plant type too. With this")
print("   evidence the learner CANNOT know the right concept - as it should be.\n")

# ------------------------------------------------- Run 2: richer data
print("=" * 72)
print("RUN 2 - two positives, one negative")
print("=" * 72)
pos2 = [("apple", "cherry"), ("mango", "banana")]
neg2 = [("mango", "apple")]
h2 = induce(pos2, neg2)
print(f"training: positives = {pos2}, negatives = {neg2}")
print(f"minimal consistent hypotheses: {h2}")
print("-> UNIQUE: (mango, banana) kills the grows-on distractor (tree vs herb).")
print("   The definition of same-color-as was INDUCED, not written by anyone.\n")

# ------------------------------------------------- held-out generalization
print("=" * 72)
print("HELD-OUT GENERALIZATION (never in training)")
print("=" * 72)
rule = h2[0]
heldout_pos = [("banana", "lemon"), ("lemon", "mango")]
heldout_neg = [("lime", "apple"), ("lemon", "lime")]
ok = all(b in W.compose(a, rule) for (a, b) in heldout_pos) and all(
    b not in W.compose(a, rule) for (a, b) in heldout_neg
)
print(f"induced rule: same-color-as := {' o '.join(rule)}")
print(f"held-out positives {heldout_pos}: predicted SAME")
print(f"held-out negatives {heldout_neg}: predicted DIFFERENT")
print(f"all correct: {'PASS' if ok else 'FAIL'}\n")

# ------------------------------------------------- autonomous split
print("=" * 72)
print("AUTONOMOUS SPLIT - the learner decides, scored against the record")
print("=" * 72)
W.add_edge("mango", "green", "has-color")  # unripe mango observed
cs = W.targets("mango", "has-color")
print(f"defect: mango has-color {cs} with colors asserted distinct")


# candidate resolutions: move ONE of the conflicting edges to a fresh node.
# score each candidate by how many banked relational facts (training positives
# involving mango, checked via the INDUCED rule) remain reproduced.
def try_split(move_color):
    Wc = Web()
    Wc.adj = defaultdict(list)
    for f, c in HASCOLOR.items():
        tgt = "mango#2" if (f == "mango" and c == move_color) else f
        Wc.add_edge(tgt, c, "has-color")
    for f, p in GROWSON.items():
        Wc.add_edge(f, p, "grows-on")
    if move_color != "green":
        Wc.add_edge("mango", "green", "has-color")
    else:
        Wc.add_edge("mango#2", "green", "has-color")
    banked = [(a, b) for (a, b) in pos2 if "mango" in (a, b)]
    score = sum(1 for (a, b) in banked if b in Wc.compose(a, rule))
    return score, banked


for cand in ["green", "yellow"]:
    score, banked = try_split(cand)
    print(
        f"  split candidate: move '{cand}' edge to mango#2 -> "
        f"preserves {score}/{len(banked)} banked facts {banked}"
    )

best = max(["green", "yellow"], key=lambda c: try_split(c)[0])
print(f"learner's choice: move '{best}' -> mango#2 becomes the unripe concept.")
print("The record (mango ~ banana, both yellow) anchors WHICH mango keeps the")
print("name. No human chose the split; the data did.")
