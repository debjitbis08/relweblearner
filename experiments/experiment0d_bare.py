"""
Experiment 0d -- the BARE web: edges carry NO labels. Relation types must be
DISCOVERED as structural equivalence classes, or not at all.

Hidden ground truth (used only for scoring, never shown to the learner):
  - a successor chain n0..n19            (19 edges, type 'succ')
  - 12 fruits x 3 colors, 4 each         (12 edges, type 'has-color')
  - 12 fruits x 2 plant kinds, 9+3       (12 edges, type 'grows-on')
The learner sees one undifferentiated pile of 43 edges.

Pipeline:
  1. degree-role refinement  -> separates chain edges from attribute edges,
     but naive refinement OVER-refines (types fragment).
  2. partition-disjointness  -> hubs whose member-sets are DISJOINT belong to
     the same relation type (mutual exclusivity WITHIN a type; overlap
     ACROSS types). This is Markman's mutual-exclusivity bias, mechanized.
  3. failure mode: with sparse coverage the criterion conflates types --
     a falsifiable data-volume prediction, not a bug.
"""

from collections import defaultdict
from itertools import combinations


def analyze(edges, truth, title):
    print("=" * 72)
    print(title)
    print("=" * 72)
    deg = defaultdict(int)
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1

    # -- stage 0: what naive degree-pair typing does (for contrast)
    naive = defaultdict(list)
    for e in edges:
        naive[tuple(sorted((deg[e[0]], deg[e[1]])))].append(e)
    print(
        f"naive degree-pair typing: {len(naive)} classes "
        f"{sorted(naive.keys())}  <- over-refined (truth has 3)"
    )

    # -- stage 1: role split. hubs = high-degree nodes; an edge with a hub
    #    endpoint is an 'attribute' edge, otherwise 'chain-like'.
    hubs = {x for x, d in deg.items() if d >= 3}
    chain_edges = [e for e in edges if e[0] not in hubs and e[1] not in hubs]
    attr_edges = [e for e in edges if (e[0] in hubs) != (e[1] in hubs)]

    # -- stage 2: type the hubs by partition-disjointness.
    members = defaultdict(set)
    for u, v in attr_edges:
        h, m = (u, v) if u in hubs else (v, u)
        members[h].add(m)
    # same-type graph: hubs joined iff member-sets are disjoint
    same_type = {h: {h} for h in members}
    for a, b in combinations(members, 2):
        if not (members[a] & members[b]):
            same_type[a].add(b)
            same_type[b].add(a)
    # connected components of the disjointness graph = discovered types
    seen, types = set(), []
    for h in members:
        if h in seen:
            continue
        comp, stack = set(), [h]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend(same_type[x] - comp)
        seen |= comp
        types.append(comp)

    discovered = {"T0": chain_edges}
    for i, comp in enumerate(types, 1):
        discovered[f"T{i}"] = [e for e in attr_edges if e[0] in comp or e[1] in comp]

    print(f"discovered types: {len(discovered)}")
    for name, es in discovered.items():
        tl = sorted({truth[frozenset(e)] for e in es})
        purity = max(sum(truth[frozenset(e)] == t for e in es) for t in tl) / len(es)
        print(
            f"  {name}: {len(es):2d} edges | ground-truth content {tl} "
            f"| purity {purity:.2f}"
        )
    print()
    return discovered


# ------------------------------------------------------------ build bare webs
def build(herb_fruits):
    edges, truth = [], {}

    def E(u, v, t):
        edges.append((u, v))
        truth[frozenset((u, v))] = t

    for i in range(19):  # succ chain (no labels emitted!)
        E(f"n{i}", f"n{i + 1}", "succ")
    colors = {
        "c_y": [f"f{i}" for i in range(1, 5)],
        "c_r": [f"f{i}" for i in range(5, 9)],
        "c_g": [f"f{i}" for i in range(9, 13)],
    }
    for c, fs in colors.items():
        for f in fs:
            E(f, c, "has-color")
    for i in range(1, 13):
        E(f"f{i}", "p_herb" if f"f{i}" in herb_fruits else "p_tree", "grows-on")
    return edges, truth


# RUN 1: generic coverage -- one herb fruit of each color
edges, truth = build(herb_fruits={"f1", "f5", "f9"})
analyze(edges, truth, "RUN 1 - bare web, generic coverage (herb spans all colors)")

# RUN 2: sparse coverage -- no green herb exists in the data
edges, truth = build(herb_fruits={"f1", "f2", "f5"})
analyze(edges, truth, "RUN 2 - sparse coverage (no green herb observed)")
print("RUN 2 conflates color-type with plant-type: green and herb happen to be")
print("disjoint, so mutual-exclusivity alone cannot separate the systems yet.")
print("PREDICTION: type individuation requires coverage -- under-sampled")
print("attribute systems are conflated until crossing observations arrive.")
