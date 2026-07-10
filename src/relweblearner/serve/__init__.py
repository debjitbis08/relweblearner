"""The application layer — a FastAPI service over a persistent :class:`Creature`.

``python -m relweblearner.serve`` (or ``uvicorn relweblearner.serve:app``) starts
the reading app over the SAME trained creature ``relweb-train`` produces: feed
phrases, tap the pictured referent, and the creature reads, commits beliefs and
talks back — live teaching on top of the corpus it already read. State is the
creature's distilled geometry at ``data/creatures/<name>.json`` (``RELWEB_CREATURE``
/ ``RELWEB_DATA``), so the session survives restarts and ships as a single
container with one data volume.
"""

from .app import app

__all__ = ["app"]
