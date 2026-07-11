"""Mastery-gated curriculum training.

The creature works through a graded curriculum (``corpus/sources.json`` -> ``stages``,
math & science first). For each stage it READS the stage's sources, then SITS the
stage's worksheet — a set of ``(question, answer)`` problems drawn from the grounded
worlds' hidden truth, phrased in the frames it was taught. It only ADVANCES to the
next stage when it scores above the stage's pass-mark; otherwise it holds and re-sits
next run. Every attempt is appended to ``data/progress.jsonl`` so progression is a
visible curve, and ``--progress`` prints a report card.

Because state (geometry + ledger + passed stages) is persisted and resumable, this
is safe to run on a schedule: one tick teaches (by default) the next single stage and
grades it; when the whole curriculum is mastered, a tick is a no-op.

    poetry run relweb-train                 # teach + grade the next stage
    poetry run relweb-train --all           # run the whole curriculum now
    poetry run relweb-train --progress      # report card: stages mastered, latest scores
    poetry run relweb-train --reset --all   # start the curriculum over for 'scholar'
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .creature import Creature, _slug
from .datasets import registry as R
from .datasets import syllabus as SYL
from .episodelog import JsonlEpisodeLog, creature_lock
from .store import open_store, store_files

# real prose needs a wide induction window; the slot cap keeps clause-wide real
# slots out of the concept web while grounded single-token facts commit cleanly.
_PARAMS = dict(commit_k=2, min_group=12, induction_interval=1500,
               buffer_cap=30000, max_slot_tokens=2)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _store_path(name: str) -> Path:
    d = _root() / "data" / "creatures"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{_slug(name)}.json"


def _log_path(name: str) -> Path:
    """The durable episode log next to the checkpoint (invariant #5: the
    checkpoint is a projection of this, not the other way around)."""
    return _store_path(name).with_suffix(".episodes.jsonl")


def _edges_base(name: str) -> Path:
    """Base path (no extension) for a durable edge store's files."""
    return _store_path(name).with_suffix(".edges")


def _checkpoint_spec(path: Path) -> str | None:
    """The store spec a checkpoint on disk says its concept web lives in
    (``None`` for inline geometry / no readable checkpoint)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))["geometry"]["concept_web"].get("external")
    except (OSError, ValueError, KeyError):
        return None


def _store_spec(cli: str | None = None, checkpoint: Path | None = None) -> str:
    """Which EdgeStore backs the creature: --store flag, else RELWEB_STORE,
    else whatever the existing checkpoint says it needs (a migrated creature
    keeps working with no env set — the state knows its own backend), else
    in-memory (geometry inline in the JSON checkpoint, as always). An explicit
    flag/env that differs from the checkpoint is a deliberate migration."""
    explicit = cli or os.environ.get("RELWEB_STORE")
    if explicit:
        return explicit
    if checkpoint is not None:
        return _checkpoint_spec(checkpoint) or "memory"
    return "memory"


def _progress_path() -> Path:
    return _root() / "data" / "progress.jsonl"


def load_or_create(name: str, reset: bool = False, store_spec: str | None = None, **kw) -> Creature:
    path = _store_path(name)
    lpath = _log_path(name)
    spec = _store_spec(store_spec, checkpoint=None if reset else path)
    if reset:
        # a reset starts a new history; the old log and edge database are
        # rotated aside, never deleted
        ts = time.strftime("%Y%m%d-%H%M%S")
        for f in ([lpath] if lpath.exists() else []) + store_files(spec, _edges_base(name)):
            f.rename(f.parent / (f.name + f".{ts}.bak"))
    log = JsonlEpisodeLog(lpath)
    store = open_store(spec, _edges_base(name))
    if path.exists() and not reset:
        c = Creature.load(path, log=log, store=store)   # replays any tail past the checkpoint
        print(f"resumed '{c.name}' — {len(c.passed_stages)} stage(s) mastered, "
              f"{c.episodes_seen} episodes [{spec} store]")
        return c
    print(f"created new creature '{name}' [{spec} store]")
    c = Creature(name, created=time.strftime("%Y-%m-%d"), log=log, store=store, **kw)
    if len(log):                                  # a log with no checkpoint: replay it all
        c.catch_up()
    return c


def open_creature(name: str, store_spec: str | None = None) -> Creature:
    """Open an EXISTING creature with its log and configured store — the one
    loader every CLI (correct, wonder, serve helpers) shares, so they all
    honour RELWEB_STORE the same way."""
    path = _store_path(name)
    if not path.exists():
        raise SystemExit(f"no trained creature '{name}' at {path}")
    spec = _store_spec(store_spec, checkpoint=path)
    return Creature.load(path, log=JsonlEpisodeLog(_log_path(name)),
                         store=open_store(spec, _edges_base(name)))


def teach_stage(creature: Creature, stage: dict, registry: list[dict]):
    """Read the stage's un-read sources, then sit its worksheet."""
    ingested = []
    for sid in stage.get("sources", []):
        if sid in creature.read_sources:
            continue
        entry = R.source_by_id(registry, sid)
        if entry is None:
            continue
        try:
            eps = R.source_episodes(entry)
        except Exception as e:                       # unavailable source -> skip, keep going
            print(f"   ✗ {sid} skipped ({e})")
            continue
        creature.ingest_source(sid, eps)
        ingested.append((sid, len(eps)))
    # a stage only clears when ALL its sources actually loaded — so a source that
    # failed this run (e.g. a rate-limited Wikidata fetch) holds the stage and is
    # retried next tick, rather than the stage passing on partial/empty content.
    all_read = all(sid in creature.read_sources for sid in stage.get("sources", []))
    report = SYL.run_exam(creature, SYL.stage_worksheet(stage, registry))
    passed = all_read and report["score"] >= stage.get("pass", 0.8)
    if passed:
        creature.passed_stages.add(stage["id"])
    return ingested, report, passed, all_read


def log_progress(creature: Creature, stage: dict, report: dict, passed: bool) -> None:
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": stage["id"],
           "name": stage["name"], "score": round(report["score"], 3),
           "correct": report["correct"], "total": report["total"], "passed": passed,
           "episodes": creature.episodes_seen,
           "facts": creature.snapshot()["committed_count"]}
    p = _progress_path(); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def report_card(stage: dict, ingested: list, report: dict, passed: bool) -> None:
    print("\n" + "=" * 64)
    print(f"STAGE {stage['id']} — {stage['name']}")
    print("=" * 64)
    for sid, n in ingested:
        print(f"   read {sid:18s} {n:>6} episodes")
    if report["total"]:
        mark = "PASSED ✓" if passed else "NOT YET ✗"
        print(f"   worksheet: {report['correct']}/{report['total']} "
              f"= {report['score']:.0%}   →   {mark}")
        for q, want, got in report["wrong"][:5]:
            print(f"      missed:  {q:30s} said {str(got)!r}, wanted {want!r}")
    else:
        print("   (reading stage — no worksheet)")


def run_curriculum(name: str, *, reset: bool, drain: bool, max_stages: int,
                   store_spec: str | None = None) -> Creature:
    registry, stages = R.load_registry(), R.load_stages()
    with creature_lock(_store_path(name).parent):   # exclude the serving app's writes
        return _run_curriculum_locked(name, registry, stages, reset=reset,
                                      drain=drain, max_stages=max_stages,
                                      store_spec=store_spec)


def _run_curriculum_locked(name: str, registry, stages, *, reset: bool,
                           drain: bool, max_stages: int,
                           store_spec: str | None = None) -> Creature:
    c = load_or_create(name, reset=reset, store_spec=store_spec, **_PARAMS)
    path = _store_path(name)
    advanced = 0
    while True:
        stage = SYL.next_stage(stages, c.passed_stages)
        if stage is None:
            print("\n🎓 curriculum complete — every stage mastered.")
            break
        print(f"\n▶ teaching: {stage['name']}")
        ingested, report, passed, all_read = teach_stage(c, stage, registry)
        log_progress(c, stage, report, passed)
        c.save(path)
        report_card(stage, ingested, report, passed)
        advanced += 1
        if not passed:
            why = ("some sources didn't load — retrying next run"
                   if not all_read else "until its worksheet is mastered — re-sits next run")
            print(f"\n   holding at '{stage['name']}' {why}.")
            break
        if not drain and advanced >= max_stages:
            break
    if advanced and os.environ.get("RELWEB_AUTOSNAP", "1") != "0":
        # snapshot the post-tick state (auto-<log position>, pruned to the
        # newest RELWEB_AUTOSNAP_KEEP) — last night's state is one
        # `relweb-version --rollback` away. We already hold the creature lock.
        from .version import autosnap
        autosnap(name, c.log_position,
                 keep=int(os.environ.get("RELWEB_AUTOSNAP_KEEP", "5")), take_lock=False)
    return c


def print_progress(name: str) -> None:
    stages = R.load_stages()
    c = load_or_create(name)
    passed = c.passed_stages
    current = SYL.next_stage(stages, passed)
    cur_id = current["id"] if current else None
    print(f"\nREPORT CARD — '{c.name}': {len(passed)}/{len(stages)} stages mastered\n")
    for st in stages:
        state = "✓ mastered" if st["id"] in passed else ("→ current " if st["id"] == cur_id else "· locked  ")
        print(f"   [{state}] {st['name']}")
    # latest worksheet scores from the progress log
    p = _progress_path()
    if p.exists():
        rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            print("\n   recent worksheets:")
            for r in rows[-6:]:
                print(f"      {r['time']}  {r['name'][:34]:34s} {r['score']:.0%} "
                      f"{'PASS' if r['passed'] else 'hold'}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mastery-gated curriculum training.")
    ap.add_argument("--name", default="scholar")
    ap.add_argument("--reset", action="store_true", help="start the curriculum over")
    ap.add_argument("--all", dest="drain", action="store_true", help="run the whole curriculum now")
    ap.add_argument("--max-stages", type=int, default=1, help="stages to attempt this run (a tick)")
    ap.add_argument("--progress", action="store_true", help="print the report card and exit")
    ap.add_argument("--store", default=None, metavar="SPEC",
                    help="edge-store backend: memory (default) | sqlite | sharded[:N]; "
                         "RELWEB_STORE sets the same thing for every relweb command")
    args = ap.parse_args()

    if args.progress:
        print_progress(args.name)
        return 0

    c = run_curriculum(args.name, reset=args.reset, drain=args.drain,
                       max_stages=args.max_stages, store_spec=args.store)
    c.close()
    return 0


def progress_main() -> int:
    """Console entry: ``relweb-progress`` — the report card."""
    ap = argparse.ArgumentParser(description="Curriculum report card.")
    ap.add_argument("--name", default="scholar")
    print_progress(ap.parse_args().name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
