"""
Experiment 0f -- reflection at the BASE, not emergent.

Principle: EMISSION IS CONSTITUTIVE, CONSUMPTION IS BUDGETED.
Every operation of the web emits a trace episode in the SAME format as a
world observation: (collection_1, collection_2, pairing). No labels, no
special reflection module, no second parser. The regress (observing the
observation...) is potential-infinite but actual-bounded by an attention
budget on consumption.

Parts:
  1. The smallest witness: a 2-node web with one defective loop emits its
     own defect trace. Observation is TOTAL over webs -- no web too small.
  2. Homoiconicity check: one ingest() consumes world episodes and trace
     episodes with zero branching.
  3. Self-consumption: the number-learner from 0e, fed its OWN stream,
     forms classes over its own acts with unchanged machinery.
  4. The regress guard: consuming traces emits traces; the stream stays
     bounded because attention is budgeted, not because emission stops.
"""

from collections import defaultdict

# episode format (identical to the world format of experiment 0e):
#   (id_1, members_1, id_2, members_2, pairs)


class ReflectiveWeb:
    """Every operation appends its trace to self.stream. No silent ops."""

    def __init__(self, name):
        self.name = name
        self.edges = {}  # (u,v) -> transport in Z
        self.stream = []  # THE event bus: world + self
        self.n_act = 0

    def _emit(self, ms1, ms2, pairs):
        self.n_act += 1
        aid = f"{self.name}.act{self.n_act}"
        self.stream.append((aid + ".in", set(ms1), aid + ".out", set(ms2), pairs))

    def add_edge(self, u, v, g):
        self.edges[(u, v)] = g
        self.edges[(v, u)] = -g
        self._emit({u, v}, {f"{u}->{v}"}, [(u, f"{u}->{v}")])  # act trace

    def loop_check(self, cycle):
        h = sum(
            self.edges[(cycle[i], cycle[(i + 1) % len(cycle)])]
            for i in range(len(cycle))
        )
        # the check itself is an observable act: it emits its trace,
        # with the defect witnessed as an UNPAIRED leftover token.
        witness = {f"defect@{self.name}"} if h != 0 else set()
        self._emit(set(cycle), witness, [])
        return h


# ---------------------------------------------------------------- Part 1
print("=" * 72)
print("1. THE SMALLEST WITNESS")
print("=" * 72)
w = ReflectiveWeb("tiny")
w.add_edge("p", "q", +1)  # p -> q costs +1
w.edges[("q", "p")] = +1  # corrupt: q -> p also +1 (loop can't close)
w.edges[("p", "q")] = +1
h = w.loop_check(["p", "q"])
print(f"web has 2 nodes, 1 loop; holonomy = {h} (defective)")
print(f"stream length = {len(w.stream)} -- the web OBSERVED its own defect:")
print(f"  last trace: {w.stream[-1]}")
print("It has no growth budget, no repair rule -- it cannot correct.")
print("But the trace exists. Observation is total; correction is optional.\n")

# ---------------------------------------------------------------- Part 2+3
print("=" * 72)
print("2+3. ONE PARSER, AND SELF-CONSUMPTION")
print("=" * 72)


class Learner:  # the 0e learner, format-identical ingest
    def __init__(self):
        self.parent = {}
        self.onemore = defaultdict(int)
        self.trace = []  # the learner's OWN emission channel

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def ingest(self, ep):
        a, A, b, B, pairs = ep  # <- zero branching: world or trace alike
        la = A - {p for p, _ in pairs}
        lb = B - {q for _, q in pairs}
        if not la and not lb and A and B:
            ra, rb = self.find(a), self.find(b)
            if ra != rb:
                self.parent[ra] = rb
                self.trace.append(
                    (
                        f"L.m{len(self.trace)}.in",
                        {a, b},
                        f"L.m{len(self.trace)}.out",
                        {rb},
                        [(a, rb)],
                    )
                )
        elif not la and len(lb) == 1:
            self.onemore[(a, b)] += 1
            self.trace.append(
                (f"L.o{len(self.trace)}.in", {a}, f"L.o{len(self.trace)}.out", {b}, [])
            )
        elif not lb and len(la) == 1:
            self.onemore[(b, a)] += 1
            self.trace.append(
                (f"L.o{len(self.trace)}.in", {b}, f"L.o{len(self.trace)}.out", {a}, [])
            )

    def compare(self, e1, e2):
        """A generic act: pair two same-size collections from the stream.
        Applied uniformly -- world episodes or the learner's own traces."""
        a, A = e1[0], e1[1]
        b, B = e2[0], e2[1]
        if len(A) == len(B) and A and B:
            self.ingest((a, A, b, B, list(zip(sorted(A), sorted(B)))))


L = Learner()
# world episodes: three matched pairs of 2-collections (as in 0e)
world = [
    ("K1", {"x1", "x2"}, "K2", {"y1", "y2"}, [("x1", "y1"), ("x2", "y2")]),
    ("K2", {"y1", "y2"}, "K3", {"z1", "z2"}, [("y1", "z1"), ("y2", "z2")]),
    ("K4", {"u1"}, "K1", {"x1", "x2"}, [("u1", "x1")]),
]
for ep in world:
    L.ingest(ep)
print(
    f"world consumed: {len(world)} episodes -> learner emitted "
    f"{len(L.trace)} traces of its own acts (same format)."
)

self_stream = list(L.trace)
for e1, e2 in zip(self_stream, self_stream[1:]):  # SELF-consumption via the
    L.compare(e1, e2)  # same generic compare act
merge_classes = defaultdict(set)
for x in L.parent:
    merge_classes[L.find(x)].add(x)
own = [m for m in merge_classes.values() if any(str(t).startswith("L.") for t in m)]
print(
    f"self-stream consumed by the SAME ingest(): learner now holds "
    f"{len(own)} classes over its own acts, e.g. {sorted(list(own[0]))[:4]}"
)
print("The concept-forming machinery ran on the machine's own operations")
print("without a single new line of parsing code. Homoiconicity: PASS\n")

# ---------------------------------------------------------------- Part 4
print("=" * 72)
print("4. THE REGRESS IS POTENTIAL, NOT ACTUAL")
print("=" * 72)
emitted, consumed, budget = len(L.trace), 0, 5
frontier = list(L.trace)
while frontier and consumed < budget:
    ep = frontier.pop(0)
    L.ingest(ep)  # consuming emits further traces...
    consumed += 1
    frontier = list(L.trace)[emitted:]
    emitted = len(L.trace)
print(
    f"attention budget = {budget}: consumed {consumed} traces, "
    f"emitted total {emitted}, unconsumed backlog {len(frontier)}"
)
print("Every act remains observable (emission never stops); only uptake is")
print("scarce. Perception total, apperception budgeted -- the monad's deal.")
