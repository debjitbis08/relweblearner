"""FastAPI app wrapping a single persistent :class:`~relweblearner.creature.Creature`
— the SAME trained creature ``relweb-train`` produces.

Thin by design: every endpoint is a direct call into the Creature. ``feed``
tokenises the phrase and streams it in through :meth:`Creature.observe`, so typing
in the UI is live incremental teaching on top of the corpus the creature already
read — not a separate session log. A process-wide lock serialises writes (the
distilled geometry is the source of truth; one creature, one file). The creature
is loaded from ``data/creatures/<name>.json`` (``RELWEB_CREATURE`` selects the
name); if none is trained yet a fresh, hand-training-friendly creature is made."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import curriculum as C
from ..creature import Creature, _slug
from ..episodelog import JsonlEpisodeLog, creature_lock
from ..reader import tokenize

NAME = os.environ.get("RELWEB_CREATURE", "scholar")
DATA = Path(os.environ.get("RELWEB_DATA", f"data/creatures/{_slug(NAME)}.json"))
DATA.parent.mkdir(parents=True, exist_ok=True)

_STATIC = Path(__file__).parent / "static"
_lock = threading.Lock()
# the durable episode log next to the checkpoint (shared with relweb-train);
# one handle for the process — every reload reuses it.
_LOG = JsonlEpisodeLog(DATA.with_suffix(".episodes.jsonl"))


def _load_creature() -> Creature:
    if DATA.exists():
        return Creature.load(DATA, log=_LOG)      # replays any tail past the checkpoint
    # no trained creature yet: a fresh one tuned for hand-training (a human feeds a
    # handful of examples per frame, so induce from small groups, often). A log
    # with no checkpoint (e.g. a crash before the first save) is replayed whole.
    c = Creature(NAME, min_group=3, induction_interval=50, log=_LOG)
    if len(_LOG):
        c.catch_up()
    return c


_creature = _load_creature()
_mtime = DATA.stat().st_mtime if DATA.exists() else 0.0


def _fresh_creature() -> Creature:
    """Return the creature, reloading from disk if the file changed underneath us
    (the cron/curriculum trainer is the other writer). Keeps the viewer and the
    scheduled training from clobbering each other's saves — training stays the
    source of truth, and teaching through the UI is applied on top of the latest."""
    global _creature, _mtime
    if DATA.exists():
        m = DATA.stat().st_mtime
        if m > _mtime:
            _LOG.refresh()                        # the trainer appended: resync the counter
            _creature = Creature.load(DATA, log=_LOG)
            _mtime = m
    return _creature

app = FastAPI(title="relweblearner — reading app", version="0.2.0")


class FeedIn(BaseModel):
    text: str
    picture: str | None = None
    book: str = "reading"
    marks: list | None = None   # human breakup: [[start, end], ...] slot-filler spans


class AskIn(BaseModel):
    text: str


class SayIn(BaseModel):
    referent: str | None = None


class RetractIn(BaseModel):
    source: str            # the entity a fact is ABOUT ("owl")
    target: str            # the value being retracted ("four")
    reason: str = "marked wrong in the reading app"


class CorrectIn(BaseModel):
    source: str            # the entity ("owl")
    wrong: str             # the mistaken value ("four")
    right: str             # the corrected value ("two")


@app.get("/api/status")
def status() -> dict:
    return _fresh_creature().snapshot()


@app.get("/api/mindmap")
def mindmap() -> dict:
    """The mind's learned geometry — concepts at the coordinates the fixed machinery
    computes for them (relational MDS of the concept web). The data behind the
    latent-space visual."""
    return _fresh_creature().mind_map()


@app.get("/api/web")
def web(focus: str | None = None, limit: int = 40) -> dict:
    """A bounded ego-graph around ``focus`` (or a committed seed) — the web
    explorer's data: neighbours, relation markers, committed/grown status."""
    return _fresh_creature().web_view(focus, limit=limit)


@app.get("/api/chains")
def chains() -> dict:
    """The learned GAUGE GROUPS, made legible: for each constraint group of the
    concept web, its relation classes (sector, transport, templates), its nodes
    ordered by holonomy coordinate (a chain group IS a number line), and its
    nonzero-holonomy defects. This is the geometry the creature actually
    reasons with — transport runs along these rails."""
    from ..holonomy import defects as _defects
    from ..holonomy import potential

    c = _fresh_creature()
    webs = c.concept_webs()
    rows = {r["class"]: r for r in c._sector_rows()}
    groups = []
    for gid, w in sorted(webs.items()):
        phi = potential(w)
        comps, seen = [], set()
        for root in sorted(w.nodes, key=repr):
            if root in seen:
                continue
            comp, stack = [], [root]
            seen.add(root)
            while stack:
                u = stack.pop()
                comp.append(u)
                for v, _g, _e in w.neighbors(u):
                    if v not in seen:
                        seen.add(v)
                        stack.append(v)
            comps.append(sorted(comp, key=lambda n: (phi.get(n, 0), str(n))))
        comps.sort(key=len, reverse=True)
        groups.append({
            "group": gid,
            "classes": [rows[r] for r in sorted(c._rel_groups)
                        if c._rel_groups[r] == gid and r in rows],
            "components": [[{"id": n, "coord": phi.get(n, 0)} for n in comp]
                           for comp in comps[:6]],
            "n_components": len(comps),
            "defects": [{"u": d.edge.u, "v": d.edge.v, "class": d.edge.rel,
                         "residual": d.residual} for d in _defects(w)][:12],
        })
    return {"groups": groups}


@app.get("/api/tokenize")
def tok(text: str) -> dict:
    """Tokenise a phrase so the UI can render one chip per word for tapping the
    pictured referent (single source of truth for word boundaries)."""
    return {"tokens": tokenize(text)}


@app.post("/api/feed")
def feed(body: FeedIn) -> dict:
    """Read one phrase into the creature: tokenise, validate the tap/breakup, stream
    it through ``observe``, and persist the distilled geometry."""
    with _lock:
        try:
            tokens = tokenize(body.text)
            if not tokens:
                raise ValueError("empty phrase")
            pic = (body.picture or "").strip().lower() or None
            if pic is not None and pic not in tokens:
                raise ValueError(f"referent {pic!r} is not a word in the phrase {tokens}")
            marks = None
            if body.marks:
                marks = [[int(a), int(b)] for a, b in body.marks]
                for a, b in marks:
                    if not (0 <= a < b <= len(tokens)):
                        raise ValueError(f"slot span [{a}, {b}] out of range for {tokens}")
                C.pattern_from_marks(tokens, marks)   # validates non-overlap
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        global _mtime
        # cross-process exclusion against the cron trainer (same lock the
        # trainer holds for its whole run): refuse politely, never interleave.
        with creature_lock(DATA.parent, blocking=False) as held:
            if not held:
                raise HTTPException(status_code=409,
                                    detail="a training run is writing this creature; try again shortly")
            c = _fresh_creature()                 # apply teaching on top of the latest trained state
            observation = c.observe(tokens, picture=pic, source=body.book, marks=marks)
            c.commit()
            c.save(DATA)
            _mtime = DATA.stat().st_mtime         # our own write; don't treat it as an external change
        return {"observation": observation, "status": c.snapshot()}


def _write_locked(mutate):
    """Run ``mutate(creature)`` under both the process lock and the cross-process
    trainer lock, then persist — the write path shared by feed/retract/correct so
    a correction can never interleave with a scheduled training run."""
    with _lock:
        global _mtime
        with creature_lock(DATA.parent, blocking=False) as held:
            if not held:
                raise HTTPException(status_code=409,
                                    detail="a training run is writing this creature; try again shortly")
            c = _fresh_creature()
            result = mutate(c)
            c.commit()
            c.save(DATA)
            _mtime = DATA.stat().st_mtime
        return result, c


@app.post("/api/retract")
def retract(body: RetractIn) -> dict:
    """Un-teach one wrong fact (invariant #6, claim granularity): flag the
    episodes that taught ``source -> target`` excluded and rebuild by
    replay-with-exclusions — a durable fix, no from-scratch retrain."""
    report, c = _write_locked(lambda c: c.retract_claim(body.source, body.target, body.reason))
    return {"retraction": report, "status": c.snapshot()}


@app.post("/api/correct")
def correct(body: CorrectIn) -> dict:
    """Fix a mistake in one move: teach ``source -> right`` through the wrong
    fact's own frame as an authoritative correction; the creature revises the
    conflict itself, dropping ``source -> wrong`` and dinging the trust of the
    sources that taught it."""
    report, c = _write_locked(lambda c: c.correct(body.source, body.wrong, body.right))
    return {"correction": report, "status": c.snapshot()}


@app.get("/api/trust")
def trust() -> dict:
    """The learned source-trust ledger: per (source, relation class) track
    records — good/bad marks, witness weight, standing. This is how the
    creature discriminates: a source caught wrong about legs is taken with a
    grain of salt about legs, while its colour testimony stays ordinary."""
    return {"trust": _fresh_creature().trust_report()}


@app.get("/api/wonders")
def wonders() -> dict:
    """The curiosity ledger (docs/spec-curiosity.md): what the creature
    currently wonders about — conflicts to arbitrate, provisional facts one
    witness short, questions it was asked and couldn't answer — plus what it
    has given up on (parked) and settled (resolved). Read-only; the batch
    answering happens in ``relweb-wonder --tick``."""
    from .. import curiosity as CU

    return CU.ledger(_fresh_creature())


@app.post("/api/ask")
def ask(body: AskIn) -> dict:
    return _fresh_creature().answer(body.text)


@app.post("/api/say")
def say(body: SayIn) -> dict:
    return {"sentences": _fresh_creature().say(body.referent)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "relweblearner.serve:app",
        host=os.environ.get("RELWEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("RELWEB_PORT", "9000")),
        reload=bool(os.environ.get("RELWEB_RELOAD")),
    )


if __name__ == "__main__":
    main()
