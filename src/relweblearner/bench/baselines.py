"""Baselines for the falsification benchmark — what RelWeb must beat (or not).

All three systems consume the same page stream as the creature but with GOLD
parses (the oriented triple each page expresses): they are spared frame
induction, relation unification and orientation discovery entirely. That
handicap runs AGAINST RelWeb, so any RelWeb win here is conservative.

They share the creature's commitment discipline (k distinct sources) and its
raw-testimony functionality judgment, so differences isolate the REASONING
layer, not the bookkeeping:

* :class:`Lookup` — the provenance-aware graph: committed edges, exact
  recall, nothing else. The floor.
* :class:`InducedRules` — Lookup plus AMIE-style statistical rule induction:
  converse pairs and 2-hop compositions mined from the committed graph at the
  same exception budget RelWeb uses, then applied as a bounded forward
  closure. The fair competitor: everything it induces, it induces from data.
* :class:`OracleRules` — the same closure engine handed the ground-truth
  rules. The ceiling: what perfect structure knowledge yields.

Detection parity: every system exposes ``flags()`` — committed double-targets
in a functional relation (the D1 signal) and, where the system derives at
all, derived-vs-committed disagreements (the D2 signal). Exact unlearning is
exclusion + recompute for all three (they are pure functions of the stream).
"""

from __future__ import annotations

from collections import defaultdict

CONF = 0.8          # rule-induction confidence floor (mirrors 1 - exception_fraction)
MIN_SUPPORT = 2     # witnessed instantiations before a rule exists
FUNCTIONAL = 0.8    # fraction of single-valued subjects for a functional verdict
CLOSURE_ROUNDS = 3  # bounded forward chaining (converse-of-composed etc.)


class GoldKB:
    """Provenance-counted gold triples with k-witness commitment."""

    def __init__(self, pages: list[tuple[str, tuple]], k: int = 2,
                 excluded_books: frozenset = frozenset()):
        self.k = k
        self.witnesses: dict[tuple, set] = defaultdict(set)
        for book, g in pages:
            if g is not None and book not in excluded_books:
                self.witnesses[g].add(book)
        self.committed = {f for f, bs in self.witnesses.items() if len(bs) >= k}
        self.raw = set(self.witnesses)

    def rels(self) -> set:
        return {r for r, _s, _t in self.committed}

    def pairs(self, rel: str, facts: set | None = None) -> set:
        src = self.committed if facts is None else facts
        return {(s, t) for r, s, t in src if r == rel}

    def functional(self, rel: str) -> bool:
        """Judged on RAW testimony, like the creature: a many-valued relation
        must not look single-valued just because commitment is thin."""
        by_s: dict[str, set] = defaultdict(set)
        for r, s, t in self.raw:
            if r == rel:
                by_s[s].add(t)
        if not by_s:
            return False
        multi = sum(1 for ts in by_s.values() if len(ts) > 1)
        return 1 - multi / len(by_s) >= FUNCTIONAL


class Lookup:
    """Committed recall, most-witnessed target first. Refuses everything else."""

    name = "lookup"

    def __init__(self, kb: GoldKB):
        self.kb = kb
        self.derived: set = set()          # lookup derives nothing

    def answer(self, rel: str, s: str) -> str | None:
        targets = [(t, len(self.kb.witnesses[(rel, s, t)]))
                   for r, s2, t in self.kb.committed if r == rel and s2 == s]
        if not targets:
            return None
        targets.sort(key=lambda x: (-x[1], x[0]))
        return targets[0][0]

    def answer_set(self, rel: str, s: str) -> set:
        """Every answer the system holds for ``(rel, s)`` — committed plus
        whatever it derives — for the many-valued retrieval metric (F6)."""
        return ({t for r, s2, t in self.kb.committed if r == rel and s2 == s}
                | {t for r, s2, t in self.derived if r == rel and s2 == s})

    def flags(self) -> list[dict]:
        """Committed double-targets in functional relations (D1), plus
        derived-vs-committed disagreements where the system derives (D2)."""
        out = []
        by: dict[tuple, set] = defaultdict(set)
        for r, s, t in self.kb.committed:
            by[(r, s)].add(t)
        for (r, s), ts in sorted(by.items()):
            if len(ts) > 1 and self.kb.functional(r):
                out.append({"kind": "double-target", "rel": r, "subject": s,
                            "targets": sorted(ts)})
        for r, s, t in sorted(self.derived):
            if not self.kb.functional(r):
                continue
            committed = by.get((r, s), set())
            if committed and t not in committed:
                out.append({"kind": "derived-conflict", "rel": r, "subject": s,
                            "derived": t, "committed": sorted(committed)})
        return out


class InducedRules(Lookup):
    """Lookup + statistical rule induction over the committed graph.

    Converses: ``r2(t,s) <- r1(s,t)`` when the overlap of committed pairs
    supports it. Compositions: ``r3(s,t) <- r1(s,m) ^ r2(m,t)`` scored by
    PCA-style confidence (body instantiations whose subject has ANY committed
    r3 target are the denominator — silent heads never vote, mirroring the
    motif layer's discipline). Rules apply as a bounded forward closure;
    committed facts always outrank derived ones."""

    name = "induced-rules"

    def __init__(self, kb: GoldKB):
        super().__init__(kb)
        self.converses: dict[str, set] = defaultdict(set)
        self.compositions: list[tuple] = []           # (head, body1, body2)
        self._induce()
        self._close()

    def _induce(self) -> None:
        rels = sorted(self.kb.rels())
        pairs = {r: self.kb.pairs(r) for r in rels}
        for r1 in rels:
            for r2 in rels:
                inv = {(t, s) for s, t in pairs[r2]}
                overlap = pairs[r1] & inv
                if len(overlap) >= MIN_SUPPORT and \
                        len(overlap) / min(len(pairs[r1]), len(pairs[r2])) >= CONF:
                    self.converses[r1].add(r2)
        for r1 in rels:
            for r2 in rels:
                body = {(s, t) for s, m in pairs[r1] for m2, t in pairs[r2]
                        if m == m2 and s != t}
                if not body:
                    continue
                for r3 in rels:
                    subjects = {s for s, _t in pairs[r3]}
                    applicable = {(s, t) for s, t in body if s in subjects}
                    support = applicable & pairs[r3]
                    if len(support) >= MIN_SUPPORT and applicable and \
                            len(support) / len(applicable) >= CONF:
                        self.compositions.append((r3, r1, r2))

    def _close(self) -> None:
        known: set = set(self.kb.committed)
        for _ in range(CLOSURE_ROUNDS):
            new: set = set()
            for r1, cs in self.converses.items():
                for r2 in cs:
                    new |= {(r2, t, s) for r, s, t in known if r == r1}
            for head, b1, b2 in self.compositions:
                p1 = {(s, t) for r, s, t in known if r == b1}
                p2 = {(s, t) for r, s, t in known if r == b2}
                new |= {(head, s, t) for s, m in p1 for m2, t in p2
                        if m == m2 and s != t}
            if new <= known:
                break
            known |= new
        self.derived = known - set(self.kb.committed)

    def answer(self, rel: str, s: str) -> str | None:
        direct = super().answer(rel, s)
        if direct is not None:
            return direct
        hits = sorted(t for r, s2, t in self.derived if r == rel and s2 == s)
        return hits[0] if hits else None


class OracleRules(InducedRules):
    """The same closure engine handed ground-truth structure — the ceiling."""

    name = "oracle-rules"

    def __init__(self, kb: GoldKB, converses: dict[str, set],
                 compositions: list[tuple]):
        Lookup.__init__(self, kb)
        self.converses = defaultdict(set, {r: set(cs) for r, cs in converses.items()})
        self.compositions = list(compositions)
        self._close()


def bench_oracle(kb: GoldKB) -> OracleRules:
    """The oracle wired for THIS benchmark's world (docs/falsification-plan.md):
    the true converse pairs, the true composition, and nothing about color or
    likes (deriving an attribute would be the hallucination RelWeb refuses)."""
    return OracleRules(
        kb,
        converses={"step+": {"step-"}, "step-": {"step+"},
                   "skip+": {"skip-"}, "skip-": {"skip+"},
                   "likes": {"likes"}},
        compositions=[("skip+", "step+", "step+"), ("skip-", "step-", "step-")],
    )
