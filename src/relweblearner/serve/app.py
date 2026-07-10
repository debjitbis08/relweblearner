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
from ..episodelog import JsonlEpisodeLog
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


@app.get("/api/status")
def status() -> dict:
    return _fresh_creature().snapshot()


@app.get("/api/mindmap")
def mindmap() -> dict:
    """The mind's learned geometry — concepts at the coordinates the fixed machinery
    computes for them (relational MDS of the concept web). The data behind the
    latent-space visual."""
    return _fresh_creature().mind_map()


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
        c = _fresh_creature()                     # apply teaching on top of the latest trained state
        observation = c.observe(tokens, picture=pic, source=body.book, marks=marks)
        c.commit()
        c.save(DATA)
        _mtime = DATA.stat().st_mtime             # our own write; don't treat it as an external change
        return {"observation": observation, "status": c.snapshot()}


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
