"""Talk-back over a model STATE — shared by the interactive :class:`Reader` and
the streaming :class:`~relweblearner.creature.Creature`.

Both learners expose the same small ``state`` view so the creature answers
identically however it was trained:

    state = {
        "frames":      {frame_id: Frame},
        "facts":       {(src, tgt): {source, ...}},   # provenance sources per fact
        "committed":   {(src, tgt), ...},              # facts believed (>= commit_k origins)
        "source_slot": {frame_id: slot_index},         # which slot holds the picture
        "fact_frames": {(src, tgt): {frame_id, ...}},  # frames that expressed the fact
    }

``fact_frames`` types each fact by the frames (relations) that produced it, so a
question in one frame ("the X is ?") is answered only from facts of THAT relation
— not every fact sharing the referent. It is optional; absent, no relation filter
is applied. ``rel_of`` (optional) maps a frame id to its unified RELATION CLASS
(:meth:`~relweblearner.creature.Creature.unify_relations`); with it, synonymous
frames ("the X is Y" and "i see a Y X") share a class and answer each other's
facts. Absent, each frame is its own class and behaviour is unchanged.

Every function here is a pure function of that state — no learner internals, no
storage. The writing path applies the L6 read-back discipline: a fact is only
expressed through a frame that re-parses to the same oriented fact.
"""

from __future__ import annotations

from . import curriculum as C


def _rel(state: dict, fid: str) -> str:
    """A frame's unified relation class (itself, if unification hasn't merged it)."""
    return state.get("rel_of", {}).get(fid, fid)


def _fact_classes(state: dict, fact: tuple) -> set | None:
    """The relation classes a fact belongs to (via the frames that expressed it),
    or ``None`` when the fact carries no relation record (no filtering)."""
    frames = state.get("fact_frames", {}).get(fact)
    return {_rel(state, f) for f in frames} if frames is not None else None


def render_fact(src: str, tgt: str, state: dict, *, verify: bool = True) -> str | None:
    """Express an oriented fact ``(src, tgt)`` through a frame that ACTUALLY
    produced it (its relation), reading the draft back before returning it. Both
    guards matter: relation-filtering stops a colour fact being voiced through the
    ``eats`` frame ("the ant eats black"), and read-back stops a structurally-valid
    but wrong orientation. Falls back to any round-tripping frame if the fact
    carries no relation record."""
    allowed = _fact_classes(state, (src, tgt))   # relation classes, not raw frame ids
    for f in sorted(state["frames"].values(), key=lambda fr: -len(fr.anchors)):
        if f.n_slots != 2:
            continue
        if allowed is not None and _rel(state, f.id) not in allowed:
            continue
        src_slot = state["source_slot"].get(f.id)
        if src_slot is None:
            continue
        draft, slot_i = [], 0
        for e in f.pattern:
            if e[0] == C.LIT:
                draft.append(e[1])
            else:
                draft.append(src if slot_i == src_slot else tgt)
                slot_i += 1
        if verify:
            r = C.parse(draft, state["frames"])
            if r is None or C._orient(r[1], src) != (src, tgt):
                continue
        return " ".join(draft)
    return None


def _status(fact: tuple, state: dict) -> str:
    return "committed" if fact in state["committed"] else "provisional"


def about(state: dict, referent: str) -> dict:
    """Everything believed about a referent, most-committed first."""
    referent = referent.strip().lower()
    beliefs = [
        {
            "target": tgt,
            "status": _status((src, tgt), state),
            "sources": sorted(sources),
            "sentence": render_fact(src, tgt, state),
        }
        for (src, tgt), sources in state["facts"].items()
        if src == referent
    ]
    beliefs.sort(key=lambda b: (b["status"] != "committed", -len(b["sources"])))
    return {"referent": referent, "beliefs": beliefs, "known": bool(beliefs)}


def _is_anchor(tok: str, state: dict) -> bool:
    return any(tok in f.anchors for f in state["frames"].values())


def answer(state: dict, tokens: list[str]) -> dict:
    """Answer a tokenised question with a blank (``?``/``_``); a lone content word
    is treated as an ``about`` query. Refused honestly if no frame matches."""
    if "?" not in tokens and "_" not in tokens:
        content = [t for t in tokens if not _is_anchor(t, state)]
        if len(content) == 1:
            return {"kind": "about", **about(state, content[0])}
        return {"kind": "unparsed", "reason": "give a question with a blank (? or _)"}
    blank = "?" if "?" in tokens else "_"
    for f in sorted(state["frames"].values(), key=lambda fr: (-len(fr.anchors), fr.id)):
        m = C._match(f.pattern, tokens)
        if m is None:
            continue
        blank_slots = [i for i, fill in enumerate(m) if fill == blank]
        other = [(i, fill) for i, fill in enumerate(m) if fill != blank]
        if len(blank_slots) != 1 or len(other) != 1:
            continue
        bi, given = blank_slots[0], other[0][1]
        src_slot = state["source_slot"].get(f.id)
        forward = src_slot is None or bi != src_slot
        qclass = _rel(state, f.id)                 # the question's relation class
        has_types = "fact_frames" in state
        hits = [
            (src, tgt)
            for (src, tgt) in state["facts"]
            if ((forward and src == given) or (not forward and tgt == given))
            and (not has_types or qclass in (_fact_classes(state, (src, tgt)) or {qclass}))
        ]
        answers = sorted(
            (
                {
                    "answer": (tgt if forward else src),
                    "status": _status((src, tgt), state),
                    "sentence": render_fact(src, tgt, state),
                }
                for (src, tgt) in hits
            ),
            key=lambda a: a["status"] != "committed",
        )
        return {"kind": "answer", "frame": f.id, "given": given, "answers": answers, "known": bool(answers)}
    return {"kind": "unparsed", "reason": "that question matches no frame I know yet"}


def say(state: dict, referent: str | None = None, limit: int = 20) -> list[dict]:
    """State committed facts as read-back-verified sentences."""
    pool = sorted(state["committed"])
    if referent is not None:
        referent = referent.strip().lower()
        pool = [f for f in pool if f[0] == referent]
    out = []
    for fact in pool[:limit]:
        sent = render_fact(fact[0], fact[1], state, verify=True)
        if sent is not None:
            out.append({"fact": list(fact), "sentence": sent})
    return out
