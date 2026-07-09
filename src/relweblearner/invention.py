"""Invention — the P7 amendment: content defects vs error defects (society §7).

The P7 rule "persistent defect -> localize and retract" is incomplete. A
persistent holonomy class that contradicts ZERO observations is not an error but
CONTENT. The canonical case: glue a counting chain to a wrap-around observation
and the 12-cycle carries holonomy +12 — a defect that conflicts with nothing and
correctly predicts never-observed facts (11 + 3 = 2). Retracting it would destroy
modular arithmetic.

Amended rule (both halves live here; the error half still delegates to
:mod:`.audit`, unchanged):

  * persistent class WITH an observation conflict  -> **error**: localize, retract;
  * persistent class with NO observation conflict  -> **content**: BANK it (reify
    as structure) and log it in the invention census.

An *observation conflict* is read off the substrate exactly: a ``succ`` self-loop
(a "class ONEMORE of itself") or a merge of two nodes observed ``distinct``. The
clock's +12 winding is neither — 0..11 stay distinct and nothing was asserted to
close — so it banks. A poisoned merge weld *is* a self-loop, so it retracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import audit
from .holonomy import defects
from .web import Node, Web


# ------------------------------------------------------------- observation conflicts
def observation_conflicts(web: Web) -> list:
    """Observation-level contradictions in ``web`` (empty => any defect is content).

    * a ``succ`` self-loop with nonzero value — a class that became ONEMORE of
      itself (the number-learner's contradiction), and
    * a ``distinct(a, b)`` observation whose nodes now resolve equal (a merge that
      violated an asserted distinctness).
    """
    conflicts: list = []
    for e in web.edges():
        if web.resolve(e.u) == web.resolve(e.v) and not web.algebra.is_identity(e.value):
            conflicts.append(("self-loop", web.resolve(e.u)))
    for obs in web.observations:
        if obs.kind == "distinct":
            a, b = obs.data
            if web.resolve(a) == web.resolve(b):
                conflicts.append(("distinct-merged", (a, b)))
    return conflicts


def classify_defect(web: Web) -> str:
    """``"none"`` | ``"error"`` | ``"content"`` for ``web``'s persistent defects.

    A defect with any observation conflict is an error (retract); a defect that
    violates no observation is content (bank).
    """
    if not defects(web):
        return "none"
    return "error" if observation_conflicts(web) else "content"


# --------------------------------------------------------------- invention census
@dataclass
class InventionCensus:
    """Standing census of the learner's inventions (society §7 metric)."""

    banked: list = field(default_factory=list)   # content classes reified as structure
    posited: list = field(default_factory=list)  # entities grown before any witness
    confirmed: set = field(default_factory=set)  # posits later witnessed
    refuted: set = field(default_factory=set)     # posits later contradicted

    def bank(self, label: str, web: Web) -> dict:
        """Reify a content defect: record its holonomy class (the structure the
        wrap-around defines). The banked edges are kept, not retracted.
        """
        entry = {"label": label, "holonomy": [d.residual for d in defects(web)]}
        self.banked.append(entry)
        return entry

    def posit(self, node: Node) -> None:
        """Log an entity grown from a closure requirement before any evidence."""
        self.posited.append(node)

    def confirm(self, node: Node) -> None:
        if node in self.posited:
            self.confirmed.add(node)

    def refute(self, node: Node) -> None:
        if node in self.posited:
            self.refuted.add(node)

    def posit_confirmation_rate(self) -> float:
        return len(self.confirmed) / len(self.posited) if self.posited else 0.0


# ---------------------------------------------------------------- content: banking
def bank_content(web: Web, census: InventionCensus, label: str) -> Optional[dict]:
    """If ``web``'s defect is content, bank it and return the census entry."""
    if classify_defect(web) != "content":
        return None
    return census.bank(label, web)


def modular_answer(web: Web, start: Node, rel: str, k: int) -> Optional[Node]:
    """Answer a query on a banked (cyclic) web by ordinary transport — the
    wrap-around edge makes ``11 + 3`` walk ``11 -> 0 -> 1 -> 2`` and land on 2.
    """
    node = start
    for _ in range(k):
        nxt = web.step(node, rel)
        if nxt is None:
            return None
        node = nxt[0]
    return node


# ------------------------------------------------------------------ error: retract
def retract_error(match_pairs, onemores, split_budget: int | None = None) -> tuple:
    """Delegate to P7 localize-and-replay (unchanged) for an error defect."""
    return audit.localize(match_pairs, onemores, split_budget)
