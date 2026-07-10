"""The creature's episode log — belief as a replayable projection (invariant #5).

The streaming creature originally distilled episodes and DISCARDED them
(``experiment0p``'s "no episode is stored anywhere"; ``experiment0q`` measured
what that costs: a frame induced late can never re-read what was thrown away,
and no belief can be re-derived or revoked by replay). This module restores the
event-sourcing invariant at the substrate level, with the same seam pattern as
the :class:`~relweblearner.store.EdgeStore`:

  * **Append-only.** Everything that mutates the creature is an entry: a WORLD
    episode (``observe``) or a committed ACT (a P1 grow/rewire move). Entries
    are never deleted; retraction FLAGS an entry excluded and rebuilds by
    replay-with-exclusions (invariant #6), at the granularity decrement
    retraction cannot reach — "this one page of an otherwise-good source was
    wrong" now retracts cleanly.
  * **Checkpoint + tail.** The distilled creature state is a CHECKPOINT of a
    replay, not the belief source: ``save()`` records how far into the log the
    state has distilled (``log_position``); ``load()`` restores the checkpoint
    and replays any tail the log has grown past it. Replaying from zero
    reproduces the whole model (the reproducibility half of invariant #5).
  * **Bounded RAM, honest disk.** At scale the log lives in a file
    (:class:`JsonlEpisodeLog`) and is only ever STREAMED, so the creature's
    memory stays O(world) while history is O(experience) — on disk, where it
    belongs. :class:`InMemoryEpisodeLog` is the programmatic/test default.
  * **Opt-out is explicit.** :class:`NullEpisodeLog` is the 0p mode taken
    knowingly: distill-and-discard, decrement-only retraction, no replay. It
    exists so that giving up the invariant is a visible constructor argument,
    never a silent property of the architecture.

World entries are the creature's joint-episode format (``tokens`` / ``picture``
/ ``source`` / ``marks``); act entries record the committed move. Folding both
onto the one bare-episode bus (invariant #4's single format) is the remaining
seam, deferred to the trace-emission work.
"""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def creature_lock(directory: str | Path, blocking: bool = True):
    """Cross-process mutual exclusion for one creature's log + checkpoint.

    The trainer (cron tick) and the serving app are separate processes writing
    the same JSONL log and checkpoint; interleaved appends would mint colliding
    sequence numbers. Both take this lock — the trainer BLOCKING for the whole
    run, the server NON-blocking per feed (yielding ``False`` means training is
    underway right now; refuse politely rather than corrupt). Advisory
    ``flock`` on ``<directory>/.lock`` — POSIX-only, like the cron script."""
    path = Path(directory) / ".lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = path.open("w")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        yield True
        fcntl.flock(fh, fcntl.LOCK_UN)
    finally:
        fh.close()


class EpisodeLog:
    """Interface: an append-only, exclusion-flagging log of entries."""

    def append(self, entry: dict) -> int:
        """Append one entry; return its sequence number."""
        raise NotImplementedError

    def entries(self, start: int = 0) -> Iterator[tuple[int, dict]]:
        """Stream ``(seq, entry)`` pairs from ``start`` on, excluded or not
        (the REPLAYER consults :meth:`excluded`; the log never hides data)."""
        raise NotImplementedError

    def exclude(self, seq: int, reason: str = "") -> None:
        """Flag an entry excluded-from-replay. Never deletes it."""
        raise NotImplementedError

    def excluded(self) -> set[int]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


class NullEpisodeLog(EpisodeLog):
    """No retention — the explicit 0p amendment mode.

    Observation is distill-and-discard; retraction is decrement-only (the edge
    aggregates); replay is impossible. Appends are counted in-process so the
    checkpoint's ``log_position`` still advances coherently, but nothing is
    kept and nothing can be excluded."""

    def __init__(self):
        self._n = 0

    def append(self, entry: dict) -> int:
        seq = self._n
        self._n += 1
        return seq

    def entries(self, start: int = 0) -> Iterator[tuple[int, dict]]:
        return iter(())

    def exclude(self, seq: int, reason: str = "") -> None:
        raise LookupError("NullEpisodeLog retains no episodes: retraction is "
                          "decrement-only (retract_source); replay is impossible")

    def excluded(self) -> set[int]:
        return set()

    def __len__(self) -> int:
        return 0                     # nothing replayable


class InMemoryEpisodeLog(EpisodeLog):
    """List-backed log — small worlds, tests, programmatic use."""

    def __init__(self):
        self._entries: list[dict] = []
        self._excluded: dict[int, str] = {}

    def append(self, entry: dict) -> int:
        self._entries.append(dict(entry))
        return len(self._entries) - 1

    def entries(self, start: int = 0) -> Iterator[tuple[int, dict]]:
        for seq in range(start, len(self._entries)):
            yield seq, dict(self._entries[seq])

    def exclude(self, seq: int, reason: str = "") -> None:
        if not 0 <= seq < len(self._entries):
            raise LookupError(f"no log entry {seq}")
        self._excluded[seq] = reason

    def excluded(self) -> set[int]:
        return set(self._excluded)

    def __len__(self) -> int:
        return len(self._entries)


class JsonlEpisodeLog(EpisodeLog):
    """One append-only JSONL file: entry lines and exclusion-flag lines.

    ``{"op": "entry", "seq": n, "data": {...}}`` records an entry;
    ``{"op": "exclude", "seq": n, "reason": ...}`` flags one — appended, so the
    file itself is the full immutable history, exclusions included. Reads
    STREAM the file (a fresh handle per scan); only the count and the
    exclusion set are cached in RAM, so memory stays O(1) in the log length.
    Appends are line-buffered single writes (atomic enough for the one-writer-
    plus-reader layout of the trainer and the serving app)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._count = 0
        self._excluded: dict[int, str] = {}
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec["op"] == "entry":
                        self._count = max(self._count, rec["seq"] + 1)
                    else:
                        self._excluded[rec["seq"]] = rec.get("reason", "")
        self._fh = self.path.open("a", encoding="utf-8")

    def _write(self, rec: dict) -> None:
        self._fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

    def append(self, entry: dict) -> int:
        seq = self._count
        self._write({"op": "entry", "seq": seq, "data": entry})
        self._count += 1
        return seq

    def entries(self, start: int = 0) -> Iterator[tuple[int, dict]]:
        self._fh.flush()
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["op"] == "entry" and rec["seq"] >= start:
                    yield rec["seq"], rec["data"]

    def exclude(self, seq: int, reason: str = "") -> None:
        if not 0 <= seq < self._count:
            raise LookupError(f"no log entry {seq}")
        self._write({"op": "exclude", "seq": seq, "reason": reason})
        self._fh.flush()
        self._excluded[seq] = reason

    def refresh(self) -> None:
        """Re-scan the file for entries another PROCESS appended (the trainer
        writing under a running server), so this handle's next sequence number
        never collides. Content sync is already replay's job (checkpoint +
        tail); this keeps only the counter and exclusion set honest."""
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["op"] == "entry":
                    self._count = max(self._count, rec["seq"] + 1)
                else:
                    self._excluded[rec["seq"]] = rec.get("reason", "")

    def excluded(self) -> set[int]:
        return set(self._excluded)

    def __len__(self) -> int:
        return self._count

    def commit(self) -> None:
        self._fh.flush()

    def close(self) -> None:
        self._fh.flush()
        self._fh.close()
