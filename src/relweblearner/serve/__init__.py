"""The hand-training application layer — a FastAPI service over :class:`Reader`.

``python -m relweblearner.serve`` (or ``uvicorn relweblearner.serve:app``) starts
the reading app: feed phrases, tap the pictured referent, and the creature reads,
commits beliefs and talks back. State persists to an append-only JSONL log
(``RELWEB_DATA``), so the session survives restarts and is deploy-ready as a
single container with one data volume.
"""

from .app import app

__all__ = ["app"]
