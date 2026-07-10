"""The MOTIF layer — composite relations as words over existing edge types.

The dev-doc glossary (§0) defines a motif as a relation spelled from edges the
web already has — ``same-color(x,y) := has-color(x,c) ∧ has-color(y,c)`` — and
invariant #1 insists learned concepts are motifs, *never* new algebra
operations. This module implements the simplest consequential family: the
INHERITANCE word

    rel(x, z)  ⊇  via(x, y) ∘ rel(y, z)

— "``rel`` factors through ``via``". With ``via`` = *kind of* and ``rel`` =
*has legs*, the never-taught ``hen has ? legs`` is answered by the committed
path ``hen -kind of-> bird -has legs-> two``. With ``via == rel`` the same
schema is transitivity. Nothing here touches the frozen algebra: a motif
answer is a WALK over taught edges, carrying testimony end to end, so unlike
transport derivation (:func:`~relweblearner.transport.derive`) it needs no
loop-constrained transport and works on UNCONSTRAINED classes — exactly the
attribute relations (legs, colour, food) that never accrue converse loops.

**Induction is evidence-scored, not stipulated.** A candidate rule
``(via, rel)`` is read off the committed class maps: every composite path
``x -via-> y -rel-> z`` where ``x`` also carries direct ``rel`` testimony is a
trial — a WITNESS if ``rel(x, z)`` is itself committed, a VIOLATION if ``x``'s
direct testimony names something else. ``x``s with no direct ``rel`` edges are
SILENT: they are the very cases the rule exists to answer, so they may not
count for it (that would be the rule voting for itself). The commitment
discipline is invariant #6 verbatim: committed iff ``witnesses >= commit_k``
and support clears the P2 description-length exception budget
(``witnesses / trials >= 1 - exception_fraction``). This is why colour does
NOT inherit in the pattern-book world (children's colours contradict their
class's) while legs DOES (biology is functional through *kind of*).

The violation test is deliberately CONSERVATIVE for multi-valued relations: a
committed ``via`` pair whose inherited value is merely missing from ``x``'s
direct edge set counts against the rule even though the set may just be
incomplete. Under-committing is the honest side to err on (invariant #6).

**Nothing is reified.** Invariant #8 names motif reification a consequential
move; this layer never makes it — no entailed edge is ever written to the
store or the log, answers are derived at query time from the committed
projection and evaporate with it (a taught fact therefore always overrides an
inherited one: lookup wins before derivation is even tried). Induction itself
is the fork-score restricted to committed geometry — the witness/violation
census IS the coherence score a simulation would compute — and each candidate
verdict rides the shared bus cf-flagged so the imagining is on the record
(invariant #4).

Pure functions of the class maps, like :func:`~relweblearner.transport.infer`:
the rule set is a PROJECTION, rebuilt on staleness, never checkpointed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

__all__ = ["MotifRule", "induce", "derive"]


@dataclass(frozen=True)
class MotifRule:
    """One scored inheritance motif ``rel(x,z) ⊇ via(x,y) ∘ rel(y,z)``."""

    rel: str          # the inherited relation class
    via: str          # the chaining relation class
    witnesses: int    # composite paths confirmed by direct committed testimony
    violations: int   # composite paths contradicted by direct testimony
    support: float    # witnesses / (witnesses + violations)
    committed: bool   # cleared k-witness + exception-budget policy (invariant #6)


def induce(
    cmaps: dict[str, set],
    commit_k: int = 2,
    exception_fraction: float = 0.2,
    journal=None,
) -> list[MotifRule]:
    """Score every candidate inheritance rule against the committed class maps.

    ``cmaps`` maps relation class → eligible ``(source, target)`` pairs (the
    same projection :func:`~relweblearner.transport.infer` consumes). Returns
    every candidate with at least one trial, committed rules first; candidates
    with zero trials (no ``via`` target carries ``rel`` edges, or no ``via``
    source carries direct testimony to score against) are not rules at all and
    are omitted. Each verdict is emitted cf-flagged on ``journal`` — the
    scoring is an imagining, on the record but never in belief.
    """
    classes = sorted(cmaps)
    out_by: dict[str, dict[str, set]] = {}
    for r in classes:
        m: dict[str, set] = defaultdict(set)
        for (s, t) in cmaps[r]:
            m[s].add(t)
        out_by[r] = m

    rules: list[MotifRule] = []
    for via in classes:
        pairs = cmaps[via]
        if not pairs:
            continue
        via_targets = {t for (_s, t) in pairs}
        for rel in classes:
            rel_out = out_by[rel]
            if not via_targets & rel_out.keys():
                continue                      # no composite path exists at all
            w = v = 0
            for (x, y) in pairs:
                if x == y:
                    continue
                inherited = rel_out.get(y)
                if not inherited:
                    continue
                mine = rel_out.get(x)
                if not mine:
                    continue                  # silent: no direct testimony either way
                for z in inherited:
                    if z == x:
                        continue
                    if z in mine:
                        w += 1
                    else:
                        v += 1
            if w + v == 0:
                continue
            support = w / (w + v)
            committed = w >= commit_k and support >= 1.0 - exception_fraction
            rules.append(MotifRule(rel, via, w, v, support, committed))
            if journal is not None:
                journal.emit(
                    {f"rule:{rel}<~{via}"},
                    {f"witnesses:{w}", f"violations:{v}",
                     "commit" if committed else "refuse"},
                    cf=True, tag="motif-score",
                )
    rules.sort(key=lambda r: (not r.committed, -r.support, -r.witnesses, r.rel, r.via))
    return rules


def derive(
    rules: list[MotifRule],
    cmaps: dict[str, set],
    rel: str,
    given: str,
    max_depth: int = 6,
) -> list[dict]:
    """Answers for a forward ``rel`` question about ``given`` entailed by
    committed motif rules — pure, bounded, deterministic (mirrors
    :func:`~relweblearner.transport.derive`).

    BFS UP the ``via`` edges from ``given``, reading direct ``rel`` testimony
    at each ancestor and stopping at the NEAREST depth that answers —
    specificity: a closer relative's testimony shadows a more distant one, the
    inheritance analogue of lookup shadowing derivation.

    Only the forward direction (``given`` is the source) is derived. The
    reverse question ("``? has two legs``") needs no inheritance: any seed a
    downward walk could start from is a committed direct holder, which lookup
    already returns — and enumerating every inheritor below the holders is an
    unbounded scan, refused on P7 boundedness grounds, not a gap.

    Returns ``[{"answer", "via", "through"}]`` where ``through`` is the node
    chain the inheritance walked (the justification, ready to voice or
    display), shortest chains first.
    """
    committed = [r for r in rules if r.rel == rel and r.committed]
    if not committed or rel not in cmaps:
        return []
    rel_out: dict[str, set] = defaultdict(set)
    for (s, t) in cmaps[rel]:
        rel_out[s].add(t)

    hits: dict[str, dict] = {}
    for rule in committed:
        up: dict[str, set] = defaultdict(set)
        for (s, t) in cmaps.get(rule.via, set()):
            if s != t:
                up[s].add(t)
        seen = {given}
        frontier: list[tuple[str, tuple]] = [(given, ())]
        for _ in range(max_depth):
            nxt, found = [], []
            for u, path in frontier:
                for p in sorted(up.get(u, ())):
                    if p in seen:
                        continue
                    seen.add(p)
                    chain = path + (p,)
                    for z in sorted(rel_out.get(p, ())):
                        if z != given:
                            found.append((z, chain))
                    nxt.append((p, chain))
            if found:                         # nearest ancestors answer; stop
                for z, chain in found:
                    prev = hits.get(z)
                    if prev is None or len(chain) < len(prev["through"]):
                        hits[z] = {"answer": z, "via": rule.via, "through": list(chain)}
                break
            frontier = nxt
            if not frontier:
                break
    return sorted(hits.values(), key=lambda h: (len(h["through"]), h["answer"]))
