"""Reflection (P6): the learner's own acts, fed back through the ordinary path.

Invariant 4 already put every operation's trace on the bus as a bare episode.
Reflection therefore needs **no new machinery** — only attention allocation:

* **(a) act-classes crystallize.** The act traces are ordinary episodes; the
  same structural type-discovery that types relations (P2' role refinement)
  types *acts*, recovering the hidden operation kinds (edge-add, merge, grow,
  walk, defect-report). Scored as purity against those kinds. The world-episode
  parser (`number.derive`) consumes act traces unchanged — homoiconicity.
* **(b) the regress is potential, not actual.** Consuming a trace is itself an
  act that emits a trace, so emission never stops — but *consumption* is drawn
  from a bounded attention budget, so the unconsumed backlog stays finite and
  consumption never exceeds budget.
* **(c) self-measurement.** The learner counts its own defect-report acts with
  the number chain it built in P1b — the system measuring itself with its own
  ruler.
"""

from __future__ import annotations

from collections import defaultdict

from .episode import Episode
from .journal import Journal


# ------------------------------------------------------------ act structure
def operation_of(ep: Episode) -> str:
    """The hidden operation kind of an act trace (from its act id; scoring only).

    Act ids look like ``@act:<web>.<tag><seq>.in`` — strip to ``<tag>``.
    """
    core = str(ep.id1).split(":", 1)[-1]        # "<web>.<tag><seq>.in"
    parts = core.split(".")
    if len(parts) < 2:
        return "?"
    return parts[1].rstrip("0123456789")


def act_signature(ep: Episode) -> tuple:
    """A structural role signature of an act episode (the refinement key).

    Uses only structure — collection sizes, pairing arity, reflexivity — never
    the operation label. Acts of the same kind share a signature.
    """
    reflexive = any(a == b for a, b in ep.pairing)
    return (len(ep.members1), len(ep.members2), len(ep.pairing), reflexive)


# ---------------------------------------------------- act-class discovery
def act_traces(journal: Journal, tags=None) -> list:
    """The learner's own (non-cf) act traces, optionally filtered to ``tags``."""
    out = []
    for _eid, ep in journal.act_stream():
        if tags is None or operation_of(ep) in tags:
            out.append(ep)
    return out


def discover_act_classes(traces: list) -> dict:
    """Type-discovery over acts: group by structural role signature (refinement)."""
    classes: dict = defaultdict(list)
    for ep in traces:
        classes[act_signature(ep)].append(ep)
    return dict(classes)


def act_class_purity(classes: dict) -> float:
    """Fraction of acts whose class is dominated by their true operation kind."""
    total = sum(len(v) for v in classes.values())
    if total == 0:
        return 1.0
    correct = 0
    for members in classes.values():
        counts: dict = defaultdict(int)
        for ep in members:
            counts[operation_of(ep)] += 1
        correct += max(counts.values())
    return correct / total


# ------------------------------------------------- homoiconic ingest check
def parses_as_world(traces: list) -> bool:
    """Every act trace is consumed by the world-episode parser unchanged.

    Runs `number.derive` (the MATCH/ONEMORE parser) on each act episode with
    zero branching on origin — the homoiconicity claim of invariant 4.
    """
    from .number import derive

    for ep in traces:
        derive(ep)               # must not raise; act episodes parse like world ones
        ep.leftovers()
    return True


# ------------------------------------------------ attention budget / regress
def bounded_consume(journal: Journal, budget: int, tag: str = "consume") -> dict:
    """Consume act traces under an attention budget; consuming emits (regress).

    Returns ``{consumed, emitted_by_consumption, backlog}``. Consumption never
    exceeds ``budget`` and the backlog stays finite even though emission never
    stops (invariant 4 / experiment0f part 4).
    """
    consumed = 0
    emitted = 0
    already = {eid for eid, _ in journal.act_stream()}
    frontier = list(already)
    while frontier and consumed < budget:
        frontier.pop(0)
        # consuming is itself an act -> it emits a new trace
        journal.emit({f"seen{consumed}"}, {f"digest{consumed}"}, [], tag=tag)
        emitted += 1
        consumed += 1
        # newly emitted traces join the backlog but are not consumed past budget
        frontier = [eid for eid, _ in journal.act_stream() if eid not in already]
    backlog = len([eid for eid, _ in journal.act_stream() if eid not in already])
    return {"consumed": consumed, "emitted_by_consumption": emitted, "backlog": backlog}


# ------------------------------------------------------- defect-report acts
def emit_defect_reports(web, journal: Journal | None = None) -> list:
    """Emit one act trace per current defect (the learner reporting on itself).

    Returns the emitted episode ids — a collection the learner can then *count*.
    """
    from .holonomy import defects

    j = journal if journal is not None else web.journal
    ids = []
    for d in defects(web):
        eid = j.emit({d.edge.u}, {f"defect:{d.edge.u}->{d.edge.v}"}, [], tag="defect")
        ids.append(eid)
    return ids


def self_count(number_learner, chain, collection) -> int:
    """Count a collection of the learner's own acts with the P1b number chain."""
    return number_learner.count(chain, set(collection))
