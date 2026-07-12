"""The carrier ladder: oracle feasibility of finite dagger monoids on GraphLog.

Referee-recommended sweep (docs/falsification-plan.md §7¼), nested on one
3-point latent set:

    Z  ⊂-ish  S3  ⊂  I3  ⊂  B3      (with CYK/free rewriting above)

* ``S3``  — the 6 total permutations: adds NONCOMMUTATIVITY, keeps totality
  and invertibility;
* ``I3``  — the 34 partial bijections (symmetric inverse monoid): adds
  PARTIALITY and idempotents, keeps injectivity;
* ``B3``  — all 512 binary relations on 3 points, Boolean matrix
  composition: adds many-to-one and one-to-many transport — the closest
  finite carrier to what knowledge-graph relations actually are.

Every element is a 9-bit int (bit ``3*i + j`` = relation holds of (i, j)).
Composition is Boolean matrix multiplication (precomputed table); dagger is
transpose; the identity is the diagonal; the empty relation is a LEGITIMATE
zero, distinct from "composition undefined" (which does not arise here —
B3 composition is total). Gauge transformations are conjugation by the
units (S3) only; arbitrary relations are not valid relabelings.

The dagger contract holds by construction and is pinned by tests:
``(AB)† = B†A†`` and ``(A†)† = A``.

ORACLE FEASIBILITY, not discovery: for each GraphLog world the TRUE rules
``(a, b) -> h`` become constraints ``X_h = X_a ∘ X_b`` solved over the
carrier by min-conflicts local search with restarts (deterministic seeding).
Local search yields a LOWER BOUND on satisfiable rules — "exact" means a
full solution was found, "max satisfied" below total does not prove
infeasibility. The found assignment is decoded on the world's real test
queries by the same forward path-voting used for Z. A carrier whose oracle
cannot outperform the Z reference is dead before any learning begins.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from functools import lru_cache

N = 3
ALL = range(512)
IDENTITY = sum(1 << (i * N + i) for i in range(N))
ZERO = 0

_ROW = [[(e >> (i * N)) & 0b111 for i in range(N)] for e in ALL]


@lru_cache(maxsize=1)
def _compose_table() -> list:
    """512x512 Boolean matrix products, one flat list (a*512 + b)."""
    # row i of A∘B = OR of B's rows k where A_ik holds
    rows_of = _ROW
    table = [0] * (512 * 512)
    for a in ALL:
        ra = rows_of[a]
        for b in ALL:
            rb = rows_of[b]
            c = 0
            for i in range(N):
                row = 0
                bits = ra[i]
                if bits & 1:
                    row |= rb[0]
                if bits & 2:
                    row |= rb[1]
                if bits & 4:
                    row |= rb[2]
                c |= row << (i * N)
            table[a * 512 + b] = c
    return table


def compose(a: int, b: int) -> int:
    return _compose_table()[a * 512 + b]


def dagger(a: int) -> int:
    t = 0
    for i in range(N):
        for j in range(N):
            if a & (1 << (i * N + j)):
                t |= 1 << (j * N + i)
    return t


def _rows_ok(e: int, at_most_one: bool, exactly_one: bool) -> bool:
    for i in range(N):
        bits = bin(_ROW[e][i]).count("1")
        if exactly_one and bits != 1:
            return False
        if at_most_one and bits > 1:
            return False
    return True


def s3() -> list[int]:
    """Total bijections: exactly one bit per row AND per column."""
    return [e for e in ALL
            if _rows_ok(e, False, True) and _rows_ok(dagger(e), False, True)]


def i3() -> list[int]:
    """Partial bijections: at most one bit per row AND per column."""
    return [e for e in ALL
            if _rows_ok(e, True, False) and _rows_ok(dagger(e), True, False)]


def b3() -> list[int]:
    return list(ALL)


CARRIERS = {"S3": s3, "I3": i3, "B3": b3}


# ------------------------------------------------------------- feasibility

def solve_rules(rules: dict[tuple, str], carrier: list[int], seed: int,
                restarts: int = 40, iters: int = 2000) -> tuple[dict, int]:
    """Min-conflicts local search for ``X_h = X_a ∘ X_b`` over the carrier,
    with a LEXICOGRAPHIC objective: satisfied rules first, then DISTINCT
    elements. Satisfaction alone is a trap on carriers with an absorbing
    zero — mapping nearly every relation to the empty relation satisfies
    everything (0 ∘ x = 0) and discriminates nothing, so among equally
    satisfying values the search prefers ones no other relation holds, and
    after reaching exactness it keeps hill-climbing on distinctness while
    preserving it. Returns ``(assignment, satisfied)`` — a lower bound on
    the maximum satisfiable rule count. Deterministic per (rules, seed)."""
    rng = random.Random(seed)
    rels = sorted({x for k, v in rules.items() for x in (*k, v)})
    rlist = [(a, b, h) for (a, b), h in sorted(rules.items())]
    touching: dict[str, list] = defaultdict(list)
    for idx, (a, b, h) in enumerate(rlist):
        for x in {a, b, h}:
            touching[x].append(idx)

    def violations(assign, idxs=None):
        idxs = range(len(rlist)) if idxs is None else idxs
        return [i for i in idxs
                if compose(assign[rlist[i][0]], assign[rlist[i][1]])
                != assign[rlist[i][2]]]

    def move(assign, var):
        """Best value for ``var``: fewest local violations, then fewest
        collisions with other relations' current values."""
        cands = carrier if len(carrier) <= 64 else \
            rng.sample(carrier, 64) + [assign[var]]
        held = Counter(v for r, v in assign.items() if r != var)
        scored = []
        for val in cands:
            old = assign[var]
            assign[var] = val
            scored.append((len(violations(assign, touching[var])),
                           held[val], rng.random(), val))
            assign[var] = old
        scored.sort()
        assign[var] = scored[0][3]

    def quality(assign):
        return (len(rlist) - len(violations(assign)),
                len(set(assign.values())))

    best_assign, best_q = None, (-1, -1)
    for _ in range(restarts):
        assign = {r: rng.choice(carrier) for r in rels}
        for _ in range(iters):
            viol = violations(assign)
            if not viol:
                break
            a, b, h = rlist[rng.choice(viol)]
            move(assign, rng.choice([a, b, h]))
        # exact: spread collided values apart wherever the rules allow it
        if not violations(assign):
            for _ in range(4 * len(rels)):
                held = Counter(assign.values())
                crowded = [r for r in rels if held[assign[r]] > 1]
                if not crowded:
                    break
                move(assign, rng.choice(crowded))
                if violations(assign):            # never trade exactness away
                    break
        q = quality(assign)
        if q > best_q:
            best_assign, best_q = dict(assign), q
    return best_assign, best_q[0]


def decode(rec: dict, assign: dict[str, int], majority: str,
           prior: Counter, max_len: int = 5) -> str:
    """Forward path-voting with carrier composition — the same decoder shape
    as the Z reference: candidates are the relations whose element equals the
    path composite (the empty relation is a real element and votes like any
    other), prior breaks ties."""
    u0, v0, _ = rec["query"]
    out_idx: dict[int, list] = defaultdict(list)
    for u, v, rel in rec["edges"]:
        e = assign.get(rel)
        if e is not None:
            out_idx[u].append((v, e))
    votes: Counter = Counter()
    stack = [(u0, IDENTITY, 0)]
    while stack:
        node, acc, depth = stack.pop()
        if node == v0 and depth:
            for r, e in assign.items():
                if e == acc:
                    votes[r] += 1
            continue
        if depth >= max_len:
            continue
        for y, e in out_idx[node]:
            stack.append((y, compose(acc, e), depth + 1))
    if not votes:
        return majority
    return max(votes, key=lambda r: (votes[r], prior[r], r))


def audit(assign: dict[str, int], satisfied: int, total: int) -> dict:
    """The referee's feasibility diagnostics for one found assignment."""
    vals = Counter(assign.values())
    return {"exact": satisfied == total,
            "satisfied": [satisfied, total],
            "distinct_elements": len(vals),
            "collisions": sum(n * (n - 1) // 2 for n in vals.values() if n > 1),
            "forced_identity": sum(1 for v in assign.values() if v == IDENTITY),
            "forced_zero": sum(1 for v in assign.values() if v == ZERO)}
