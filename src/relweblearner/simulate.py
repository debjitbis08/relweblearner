"""Simulation & lookahead (P6'): imagine before you act.

A seam over parts already built (`docs/design-log.md`): **fork** the projection
(invariant 5), **apply** reversible moves (invariant 2), **score** by holonomy
(invariant 8/9), **discard**. No new primitive.

* **imagine-then-commit** — every consequential move is scored on a fork;
  it commits only if policy clears (default: introduces no new contradiction,
  or strictly reduces defect mass).
* **lookahead** — among several candidate moves, simulate each and commit only
  the least ``(defect, size)`` winner.
* **rehearsal-refusal** — a move whose simulation shows a contradiction is
  refused, with a logged reason (the learner declines by imagining the
  consequence first).
* **counterfactual provenance** — simulated acts ride the shared bus
  ``cf``-flagged; ``Journal.committed`` never yields them, so the cf and real
  sets cannot cross-contaminate.

Known limit (documented, ties to P7): simulation only catches conflicts with
ALREADY-KNOWN structure. It raises the cost of an *inconsistent* lie to infinity
(auto-refused) but does nothing to a fully *consistent* one — coherence is
checkable, correspondence needs the ensemble.
"""

from __future__ import annotations

from dataclasses import dataclass

from .holonomy import defect_mass
from .web import Web


@dataclass
class Score:
    defect: float
    size: int

    def key(self) -> tuple:
        return (self.defect, self.size)


@dataclass
class Outcome:
    committed: bool
    reason: str
    delta_defect: float
    move: tuple


def score(web: Web) -> Score:
    return Score(defect_mass(web), len(web.nodes))


def apply_move(web: Web, move: tuple) -> None:
    """Apply a move spec to a web. Moves: merge / add / grow."""
    kind = move[0]
    if kind == "merge":
        web.rewire(merge=(move[1], move[2]))
    elif kind == "add":
        web.rewire(add=(move[1], move[2], move[3], move[4]))
    elif kind == "grow":
        web.grow(list(move[1]), list(move[2]))
    else:
        raise ValueError(f"unknown move: {kind!r}")


class Simulator:
    """Routes consequential moves through fork-score-discard (the `play` seam)."""

    def __init__(self, web: Web):
        self.web = web

    # ---- the seam: try on a FORK, score, commit nothing ----
    def simulate(self, move: tuple) -> Score:
        fork = self.web.fork()          # cf, shares the bus; discarded on return
        apply_move(fork, move)          # emits cf-flagged traces only
        return score(fork)

    # ---- imagine, then commit only if policy clears ----
    def imagine_then_commit(self, move: tuple) -> Outcome:
        before = score(self.web)
        after = self.simulate(move)
        delta = after.defect - before.defect
        if delta <= 0:                  # policy: no new contradiction (or reduces)
            apply_move(self.web, move)
            self.web.journal.emit({"commit"}, {f"move:{move[0]}"}, [], tag="commit")
            return Outcome(True, "clean", delta, move)
        reason = f"refused: would add {delta} defect mass"
        self.web.journal.emit({"refuse"}, {reason}, [], tag="refuse")
        return Outcome(False, reason, delta, move)

    # ---- lookahead: simulate all, commit only the winner ----
    def lookahead(self, candidates: list) -> tuple:
        scored = [(m, self.simulate(m)) for m in candidates]
        best = min(scored, key=lambda ms: ms[1].key())
        return best[0], {tuple(m): s for m, s in scored}

    def commit_best(self, candidates: list) -> tuple:
        best, scores = self.lookahead(candidates)
        outcome = self.imagine_then_commit(best)
        return best, outcome, scores


# ------------------------------------------------- counterfactual provenance
def cf_trace_ids(web: Web) -> list:
    """Ids of the learner's simulated (cf) act traces on the shared bus."""
    return [eid for eid, ep in web.journal.all_entries() if ep.cf]


def committed_has_no_cf(web: Web) -> bool:
    """The belief stream never contains a counterfactual act (invariant 8)."""
    return all(not ep.cf for _eid, ep in web.journal.committed())
