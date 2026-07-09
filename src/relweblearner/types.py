"""Unlabeled-relation type discovery (P2').

Edges carry no labels. A relation *type* is a structural equivalence class of
edges, found by two opposing operations:

* **refinement** (Weisfeiler–Leman-style role distinction) — type edges by the
  degree signature of their endpoints. This *over-refines*: it splits one true
  relation into many classes. Kept as :func:`naive_degree_typing` for contrast.
* **compression** (the sleep-phase merge) — recover the true types with a
  *mutual-exclusivity* criterion (Markman's bias): two hub nodes belong to the
  same relation type iff their member-sets are **disjoint** (within a type,
  members are mutually exclusive; across types, they overlap). Connected
  components of the disjointness graph are the discovered attribute types; the
  hub-free edges are the chain type.

Known failure mode (`experiment0d_bare.py`): under sparse coverage two hubs from
*different* types can be accidentally disjoint and get conflated. That is a
falsifiable data-volume prediction, logged as the conflation-vs-coverage curve —
not a bug.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

Edge = tuple  # (u, v), unlabeled


def _degrees(edges) -> dict:
    deg: dict = defaultdict(int)
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    return deg


def naive_degree_typing(edges) -> dict:
    """1-round WL / degree-pair typing — the over-refined baseline (for contrast)."""
    deg = _degrees(edges)
    classes: dict = defaultdict(list)
    for e in edges:
        classes[tuple(sorted((deg[e[0]], deg[e[1]])))].append(e)
    return dict(classes)


def discover_types(edges, hub_threshold: int = 3) -> dict:
    """Discover relation types: chain type + one per disjointness component.

    Returns ``{type_name: [edges]}``. ``T0`` is the hub-free (chain) type; ``T1,
    T2, ...`` are the attribute types recovered by disjointness compression.
    """
    deg = _degrees(edges)
    hubs = {n for n, d in deg.items() if d >= hub_threshold}

    chain_edges = [e for e in edges if e[0] not in hubs and e[1] not in hubs]
    attr_edges = [e for e in edges if (e[0] in hubs) != (e[1] in hubs)]

    # member-set of each hub (the non-hub endpoints attached to it)
    members: dict = defaultdict(set)
    for u, v in attr_edges:
        h, m = (u, v) if u in hubs else (v, u)
        members[h].add(m)

    # disjointness graph: hubs joined iff their member-sets don't intersect
    adj: dict = {h: set() for h in members}
    for a, b in combinations(members, 2):
        if not (members[a] & members[b]):
            adj[a].add(b)
            adj[b].add(a)

    # connected components = discovered attribute types
    seen: set = set()
    comps: list = []
    for h in members:
        if h in seen:
            continue
        comp, stack = set(), [h]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend(y for y in adj[x] if y not in comp)
        seen |= comp
        comps.append(comp)

    discovered = {"T0": chain_edges}
    for i, comp in enumerate(comps, 1):
        discovered[f"T{i}"] = [e for e in attr_edges if e[0] in comp or e[1] in comp]
    return discovered


# ------------------------------------------------------------------ scoring
def _majority(es, truth) -> int:
    return Counter(truth[frozenset(e)] for e in es).most_common(1)[0][1]


def purity(discovered: dict, truth: dict) -> dict:
    """Per-type purity: fraction of a discovered type's edges of one true type."""
    out = {}
    for name, es in discovered.items():
        out[name] = _majority(es, truth) / len(es) if es else 1.0
    return out


def overall_purity(discovered: dict, truth: dict) -> float:
    total = sum(len(es) for es in discovered.values())
    correct = sum(_majority(es, truth) for es in discovered.values() if es)
    return correct / total if total else 1.0


def is_conflated(discovered: dict, truth: dict) -> bool:
    """True iff some discovered type mixes more than one ground-truth type."""
    for es in discovered.values():
        if es and len({truth[frozenset(e)] for e in es}) > 1:
            return True
    return False


def n_attribute_types(discovered: dict) -> int:
    """Number of non-empty attribute types discovered (excludes the chain T0)."""
    return sum(1 for name, es in discovered.items() if name != "T0" and es)
