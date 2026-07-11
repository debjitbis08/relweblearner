"""Curiosity (PQ) — the wonder ledger + oracle ticks (docs/spec-curiosity.md).

The creature already knows what it doesn't know: a parsed question it couldn't
answer (minted onto the episode log by ``Creature.answer``), a provisional edge
one independent witness short of belief, a committed conflict ``revise()``
declines to settle. This module PROJECTS those into one ranked ledger of open
WONDERS and batch-answers them with a budgeted TICK that routes each wonder to
declared ORACLES and ingests whatever comes back as ORDINARY TESTIMONY.

Curiosity is a policy layer, never a new epistemology. Everything it fetches
enters through ``ingest`` under the standing rules — ``commit_k`` independent
witnesses, per-domain trust, replay-retraction — so one oracle is one witness
(a lone answer stays PROVISIONAL and chains into a fresh ``confirm`` wonder),
and a lying oracle is caught and discounted by the standard machinery. The
theoretical placement: ASK extends the move hierarchy below refusal —
``relabel < rewire < grow < ask < refuse`` — the repair for defects whose
cause is missing evidence, not bad geometry.

Budgets everywhere (P7: exhaustion degrades to refusal, never fabrication):
``wonder_cap`` bounds minting, ``budget`` bounds a tick, ``corroborate``
bounds oracles per question, ``max_attempts`` parks the fruitless — recorded
on the final ``sought`` act, so parking survives replay and knob changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# ------------------------------------------------------------------- oracles


@dataclass(frozen=True)
class Oracle:
    """A declared knowledge source the tick may consult, targeted per subject.

    ``id`` is the source name stamped on every episode it teaches — the handle
    the trust ledger judges, so one oracle is ONE witness however often it
    repeats itself. ``anchors`` are the relation-naming words it can answer
    about (routing is lexical: a wonder routes here iff the anchor sets
    intersect). ``frames`` are the paraphrase templates its triples are
    rendered through — prefer constructions the curriculum already taught, so
    testimony lands in the induced class. ``lookup(subject)`` returns
    ``(subject, object)`` triples; it may hit the network and may raise (the
    tick treats a raised lookup as fruitless, never a retry loop)."""

    id: str
    anchors: frozenset
    frames: list
    lookup: Callable[[str], list]
    domain: str = "curiosity"


def oracles_from_json(path: str | Path) -> list[Oracle]:
    """Build the declared oracle registry (``corpus/oracles.json``). Kinds:
    ``triples`` (inline table, offline), ``wordnet-lookup`` (hypernyms of one
    word, offline corpus), ``wikidata-lookup`` (one entity's one property via
    SPARQL). Lookups are lazy — construction never touches the network."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for e in data["oracles"] if isinstance(data, dict) else data:
        kind = e["kind"]
        if kind == "triples":
            table = tuple((s, o) for s, o in e.get("triples", ()))
            lookup = lambda subject, _t=table: [(s, o) for s, o in _t if s == subject]
        elif kind == "wordnet-lookup":
            from .datasets import factsource as FS
            lookup = lambda subject: FS.wordnet_lookup(subject)
        elif kind == "wikidata-lookup":
            from .datasets import factsource as FS
            lookup = lambda subject, _p=e["property"]: FS.wikidata_lookup(subject, _p)
        else:
            raise LookupError(f"unknown oracle kind {kind!r}")
        out.append(Oracle(id=e["id"], anchors=frozenset(e.get("anchors", ())),
                          frames=[list(f) for f in e["frames"]],
                          lookup=lookup, domain=e.get("domain", "curiosity")))
    return out


# ------------------------------------------------------------------ the ledger


def _edge_anchors(creature, info: dict) -> tuple:
    """The anchor words of every frame witnessing an edge — the relation's
    stable name (frame IDS are induction-order-dependent; anchors are not).
    Tolerant of fids a replay renumbered away."""
    anchors: set = set()
    for fid in info.get("frames", ()):
        f = creature.frames.get(fid)
        if f is not None:
            anchors |= set(f.anchors)
    return tuple(sorted(anchors))


def _class_anchors(creature, cl: str) -> tuple:
    """Union of anchor words across a relation class's frames."""
    anchors: set = set()
    for fid, f in creature.frames.items():
        if creature._rel_find(fid) == cl:
            anchors |= set(f.anchors)
    return tuple(sorted(anchors))


def _arbitrate_rows(creature) -> list[dict]:
    """Standing committed conflicts (``_belief_conflicts``, the ones a
    decree-less ``revise()`` keeps as corroborated dissent), each with whether
    the camps' trust-weighted support is already DECISIVE — testimony never
    erases testimony, so 'no longer tied' is what an oracle can achieve."""
    rel_of = creature._rel_of()
    rows = []
    for cl, s, tm in creature._belief_conflicts(rel_of):
        anchors = _class_anchors(creature, cl)
        supports = sorted((creature._edge_support(info, rel_of) for info in tm.values()),
                          reverse=True)
        rows.append({"wid": f"a:{s}:{'-'.join(anchors)}", "qkind": "arbitrate",
                     "subject": creature._desense(s), "object": None,
                     "targets": sorted(creature._desense(t) for t in tm),
                     "anchors": anchors, "phrase": None,
                     "decisive": len(supports) > 1 and supports[0] > supports[1]})
    return rows


def _confirm_rows(creature) -> list[dict]:
    """Every provisional edge — real testimony below the commitment weight,
    where ONE more independent witness is the whole ask. Grown structure
    (act-only sources) is excluded: posits are confirmed by growth's own
    persistence rules, not by testimony shopping."""
    rel_of = creature._rel_of()
    rows = []
    for s, t, info in creature.edges.iter_edges():
        srcs = info.get("sources") or {}
        if not srcs or all(str(x).startswith("act:") for x in srcs):
            continue
        if creature._committed_info(info, rel_of):
            continue
        rows.append({"wid": f"c:{s}:{t}", "qkind": "confirm",
                     "subject": creature._desense(s), "object": creature._desense(t),
                     "fact": (s, t),        # the raw (possibly sense-bound) edge key
                     "anchors": _edge_anchors(creature, info), "phrase": None})
    return rows


def _unknown_rows(creature) -> list[dict]:
    """The persisted wonders, in birth order (dict insertion = log order)."""
    return [{"wid": e["wid"], "qkind": "unknown", "subject": e["subject"],
             "object": None, "anchors": tuple(e.get("anchors", ())),
             "phrase": e.get("phrase")}
            for e in creature.wonder_events.values()]


def ledger(creature) -> dict:
    """The whole curiosity ledger, a pure projection: ``open`` (ranked
    arbitrate > confirm > unknown, oldest first within a kind), ``parked``
    (given up on the record), ``resolved`` (wid -> how; never reopens)."""
    rows = _arbitrate_rows(creature) + _confirm_rows(creature) + _unknown_rows(creature)
    open_rows, parked_rows = [], []
    for r in rows:
        if r["wid"] in creature.resolved_wonders:
            continue
        r["sought"] = creature.sought_counts.get(r["wid"], 0)
        (parked_rows if r["wid"] in creature.parked_wonders else open_rows).append(r)
    return {"open": open_rows, "parked": parked_rows,
            "resolved": dict(creature.resolved_wonders)}


def wonders(creature) -> list[dict]:
    """The open ledger — what the creature currently wonders about, ranked."""
    return ledger(creature)["open"]


# --------------------------------------------------------------------- the tick


def _render(triples, oracle: Oracle) -> list[dict]:
    """Oracle triples -> ordinary world episodes, one per triple per frame,
    doubled (the corpus habit: repetition within one source is capped support,
    never extra witnesses). The subject is the picture — it grounds and
    orients the fact, so reversed-argument paraphrases stay honest."""
    eps = []
    for s, o in triples:
        for fr in oracle.frames:
            tokens = [s if t == "{s}" else o if t == "{o}" else t for t in fr]
            eps.append({"book": oracle.id, "tokens": tokens, "picture": s})
    return eps * 2


def _resolution(creature, w: dict) -> str | None:
    """Did wonder ``w`` settle? ``unknown`` -> 'answered' once the phrase
    answers at all (even provisionally: no longer ignorant — and the thin edge
    re-surfaces as a ``confirm`` wonder, the chaining that keeps single-oracle
    answers honest). ``confirm`` -> 'committed' when the edge commits.
    ``arbitrate`` -> 'settled' when the conflict is gone (a decree got there),
    or 'informed' when the camps are no longer tied — testimony never erases
    testimony, so a decisive margin ON THE RECORD is curiosity's whole job."""
    if w["qkind"] == "unknown":
        if w.get("phrase") and creature.answer(w["phrase"]).get("known"):
            return "answered"
        return None
    if w["qkind"] == "confirm":
        fact = tuple(w.get("fact") or (w["subject"], w["object"]))
        if creature._status(fact) == "committed":
            return "committed"
        return None
    if w["qkind"] == "arbitrate":
        row = next((r for r in _arbitrate_rows(creature) if r["wid"] == w["wid"]), None)
        if row is None:
            return "settled"
        return "informed" if row["decisive"] else None
    return None


def _log_act(creature, event: dict) -> None:
    """A ledger act is a log entry like any committed move (invariant #5):
    replay re-applies it as recorded."""
    creature.log_position = creature.log.append({"kind": "act", **event}) + 1
    creature._apply_act(event)


def tick(creature, oracles, budget: int = 8, corroborate: int = 2,
         max_attempts: int = 3) -> dict:
    """One curiosity batch (the cron sibling of the training tick; run under
    the same ``creature_lock``). Takes the top ``budget`` open wonders that
    have at least one routable oracle — an unroutable wonder is SKIPPED
    untouched, so it can never creep toward parked while no oracle exists for
    it — consults up to ``corroborate`` oracles each (two when possible: one
    oracle can never commit alone, by design), ingests the answers as ordinary
    testimony, and logs ``resolved`` or ``sought`` per wonder. A wonder with
    ``max_attempts`` fruitless attempts is parked on its final sought act:
    refusal, not fabrication. Consulting no one writes nothing."""
    attempted, resolved, parked = [], [], []
    for w in wonders(creature):
        if len(attempted) >= budget:
            break
        routable = [o for o in oracles if set(o.anchors) & set(w["anchors"])]
        if not routable:
            continue
        attempted.append(w["wid"])
        consulted = []
        for o in routable[:corroborate]:
            try:
                triples = list(o.lookup(w["subject"]) or ())
            except Exception:               # network trouble: fruitless, never a retry loop
                triples = []
            consulted.append(o.id)
            eps = _render(triples, o)
            if eps:
                creature.ingest(eps)        # ordinary testimony: k-gated, trusted, revisable
        how = _resolution(creature, w)
        if how is not None:
            _log_act(creature, {"move": "resolved", "wid": w["wid"], "how": how})
            resolved.append(w["wid"])
            creature._trace("resolve-wonder", {w["wid"]}, {how})
        else:
            parks = creature.sought_counts.get(w["wid"], 0) + 1 >= max_attempts
            event = {"move": "sought", "wid": w["wid"], "oracles": consulted}
            if parks:
                event["parked"] = True
                parked.append(w["wid"])
            _log_act(creature, event)
            creature._trace("seek", {w["wid"]}, set(consulted) or {"no-answer"})
    creature.commit()
    return {"attempted": attempted, "resolved": resolved, "parked": parked,
            "open": len(wonders(creature))}
