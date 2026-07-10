"""FastAPI app wrapping a single persistent :class:`~relweblearner.reader.Reader`.

Thin by design: every endpoint is a direct call into the Reader, which owns all
learning and persistence. A process-wide lock serialises writes (the append-only
log is the source of truth; one reader, one log)."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..reader import Reader, tokenize

DATA = Path(os.environ.get("RELWEB_DATA", "data/session.jsonl"))
DATA.parent.mkdir(parents=True, exist_ok=True)

_STATIC = Path(__file__).parent / "static"
_lock = threading.Lock()
_reader = Reader.load(DATA)

app = FastAPI(title="relweblearner — reading app", version="0.1.0")


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
    return _reader.snapshot()


@app.get("/api/tokenize")
def tok(text: str) -> dict:
    """Tokenise a phrase so the UI can render one chip per word for tapping the
    pictured referent (single source of truth for word boundaries)."""
    return {"tokens": tokenize(text)}


@app.post("/api/feed")
def feed(body: FeedIn) -> dict:
    with _lock:
        try:
            observation = _reader.feed(
                body.text, picture=body.picture, book=body.book, marks=body.marks
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"observation": observation, "status": _reader.snapshot()}


@app.post("/api/ask")
def ask(body: AskIn) -> dict:
    return _reader.answer(body.text)


@app.post("/api/say")
def say(body: SayIn) -> dict:
    return {"sentences": _reader.say(body.referent)}


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
