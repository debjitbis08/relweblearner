"""Adversarial audit (P7): attack the learner, measure detection and recovery.

The event-sourced substrate is what makes recovery possible: the episode log is
immutable, belief is a projection, so a lie is *retracted* by replaying without
it — never deleted. This module adds the recovery *policy*:

* **localize-and-replay** — on a genuine contradiction ("a class ONEMORE of
  itself"), greedily exclude the match-pair whose removal most reduces
  contradictions, until none remain, then reproject (`experiment0h`).
* **k>=2 provisional commitment** (invariant 6, deferred from P1b) — commit a
  merge only with >= k independent supporting episodes, so lone-episode noise
  never enters belief.
* **repeat-lie is one cut** — match evidence is deduped by *pair*, so asserting
  the same false pair a thousand times is a single edge to cut. The attacker
  pays per episode; the learner pays one retraction.
* **consistent-lie cost** — to make a false merge *coherent* (no contradicting
  loop), an attacker must out-fake every independent loop through the region.
  The cost grows with the region's loop connectivity — the core security
  property. (A fully consistent lie is undetectable to a single learner;
  correspondence needs the ensemble, P5.)
* **DoS budgets** — split and growth budgets bound fragmentation and growth; the
  learner degrades to *refusal*, not corruption.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .number import derive


# ---------------------------------------------------------------- derived facts
def derive_facts(journal, exclude=frozenset(), k: int = 1) -> tuple:
    """Match-pairs (deduped, with provenance) and onemores from the log.

    ``k`` is the provisional-commitment threshold: only pairs with ``>= k``
    independent supporting episodes are committed (invariant 6). Deduping by
    pair makes a repeated lie a single edge.
    """
    match_ev: dict = defaultdict(list)
    onemores: list = []
    for eid, ep in journal.committed(extra_exclude=exclude):
        f = derive(ep)
        if f is None:
            continue
        if f[0] == "match":
            match_ev[frozenset((f[1], f[2]))].append(eid)
        else:
            onemores.append(((f[1], f[2]), eid))
    match_pairs = {p: eids for p, eids in match_ev.items() if len(eids) >= k}
    return match_pairs, onemores


def _find_fn(match_pairs):
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in match_pairs:
        a, b = tuple(p)
        parent[find(a)] = find(b)
    return find


def contradictions(match_pairs, onemores) -> list:
    """Onemore relations that became 'a class ONEMORE of itself' under merging."""
    find = _find_fn(match_pairs)
    return [(x, y) for ((x, y), _e) in onemores if find(x) == find(y)]


# ------------------------------------------------------ localize and replay
def localize(match_pairs, onemores, split_budget: int | None = None) -> tuple:
    """Greedy min-cut: exclude match-pairs until no contradiction remains.

    Returns ``(excluded_pairs, refused)``. Ties (redundant bridges, where
    removing any one leaves the contradiction) are broken by **support**: cut
    the pair with the fewest witnessing episodes first. A poison is thinly
    witnessed; a genuine match is thickly witnessed — so the cut lands on the lie
    and collateral stays low. If ``split_budget`` is hit before contradictions
    clear, stop and ``refused=True`` (degrade to refusal — the DoS cap).
    """
    support = {p: len(eids) for p, eids in match_pairs.items()} if isinstance(match_pairs, dict) else {}
    active = set(match_pairs)
    excluded: set = set()
    while True:
        bad = contradictions(active, onemores)
        if not bad:
            return excluded, False
        if split_budget is not None and len(excluded) >= split_budget:
            return excluded, True                      # budget hit -> refuse
        find = _find_fn(active)
        badcls = {find(x) for (x, y) in bad}
        cands = [p for p in active if find(tuple(p)[0]) in badcls]
        worst = min(
            cands,
            key=lambda p: (len(contradictions(active - {p}, onemores)), support.get(p, 1)),
        )
        active.discard(worst)
        excluded.add(worst)


# ------------------------------------------------------------------ metrics
def purity(match_pairs, sizes: dict) -> float:
    """Fraction of multi-member classes pure by hidden size."""
    find = _find_fn(match_pairs)
    cls: dict = defaultdict(set)
    for p in match_pairs:
        for x in tuple(p):
            cls[find(x)].add(x)
    multi = [m for m in cls.values() if len(m) > 1]
    if not multi:
        return 1.0
    pure = sum(1 for m in multi if len({sizes[x] for x in m}) == 1)
    return pure / len(multi)


@dataclass
class AuditResult:
    detected: bool
    n_contradictions: int
    purity_before: float
    purity_after: float
    n_excluded: int
    collateral: int              # clean pairs excluded alongside the poison


def audit(journal, sizes: dict, poison_pairs: set, k: int = 1,
          split_budget: int | None = None) -> AuditResult:
    """Run detection + localize-and-replay; measure damage and collateral."""
    match_pairs, onemores = derive_facts(journal, k=k)
    bad = contradictions(match_pairs, onemores)
    before = purity(match_pairs, sizes)
    excluded, _refused = localize(match_pairs, onemores, split_budget)
    after_pairs = {p: e for p, e in match_pairs.items() if p not in excluded}
    after = purity(after_pairs, sizes)
    collateral = sum(1 for p in excluded if p not in poison_pairs)
    return AuditResult(
        detected=len(bad) > 0,
        n_contradictions=len(bad),
        purity_before=before,
        purity_after=after,
        n_excluded=len(excluded),
        collateral=collateral,
    )


# ------------------------------------------------- consistent-lie cost curve
def consistent_lie_cost(connectivity: int) -> int:
    """Min fake episodes to make a false merge coherent, for a region with
    ``connectivity`` independent loops through the target pair.

    A false merge ``A == B`` turns every independent A–B path into a loop with
    nonzero holonomy — a defect. To make the lie *coherent* (defect-free) an
    attacker must out-fake each such loop, so the cost equals the number of
    independent loops. Measured on the real substrate (holonomy), which — unlike
    the union-find view — sees non-adjacent false merges too.
    """
    from .algebra import IntegerGroup
    from .holonomy import defects
    from .web import Web

    w = Web(IntegerGroup())
    w.add_node("A")
    w.add_node("B")
    for i in range(connectivity):
        m = f"m{i}"
        w.add_node(m)
        w.add_edge("A", m, "succ", 1)                  # A -> m_i -> B  (transport +2)
        w.add_edge(m, "B", "succ", 1)
    w.rewire(merge=("A", "B"))                          # the false merge A == B
    return len(defects(w))                             # loops the lie must out-fake


# ------------------------------------------------------------- growth budget
def growth_capped(engine, web, probes, budget: int) -> dict:
    """Answer off-web probes but cap total grown nodes; refuse beyond budget.

    The unclosable-query DoS: the learner must not grow without bound.
    """
    grown = 0
    refused = 0
    for pos, (start, rel, k) in enumerate(probes):
        if grown >= budget:
            refused += 1
            continue
        ans = engine.answer(web, start, rel, k, position=pos)
        if ans.grew is not None:
            grown += ans.grew.n_nodes
    return {"grown": grown, "refused": refused, "within_budget": grown <= budget}
