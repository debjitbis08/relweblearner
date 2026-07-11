"""What does the creature wonder about — and let it go find out.

``--show`` prints the open-question ledger: the standing conflicts it would
like arbitrated, the provisional facts one independent witness short of
belief, and the questions it was asked but could not answer (each minted onto
its episode log the moment the answer came up empty). ``--tick`` runs ONE
budgeted curiosity batch (docs/spec-curiosity.md): route each open wonder to
the declared oracles (``corpus/oracles.json``), ingest whatever comes back as
ordinary testimony — k-witness gated, per-domain trusted, replay-retractable —
and put the outcome (resolved / sought / parked) on the record.

    relweb-wonder --show                  # what is it curious about right now?
    relweb-wonder --tick                  # one batch: ask the oracles, ingest, resolve
    relweb-wonder --tick --budget 4       # a smaller batch

Shares the creature lock with the cron trainer and the serving app, so a tick
never interleaves with a scheduled run. Designed for cron via
``scripts/wonder_tick.sh``, the sibling of ``train_tick.sh``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import curiosity as CU
from .creature import Creature
from .episodelog import JsonlEpisodeLog, creature_lock
from .train import _log_path, _root, _store_path


def _load(name: str) -> Creature:
    path = _store_path(name)
    if not path.exists():
        raise SystemExit(f"no trained creature '{name}' at {path}")
    return Creature.load(path, log=JsonlEpisodeLog(_log_path(name)))


def _print_ledger(led: dict) -> None:
    if not led["open"] and not led["parked"]:
        print("   (nothing — no open questions, nothing parked)")
    for w in led["open"]:
        q = w.get("phrase") or (f"{w['subject']} -> {w['object']} ?" if w.get("object")
                                else f"{w['subject']} ({' '.join(w['anchors'])}) ?")
        print(f"   [{w['qkind']:9s}] {q:44s} sought={w['sought']}")
    for w in led["parked"]:
        print(f"   [parked   ] {w.get('phrase') or w['subject']:44s} sought={w['sought']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Show or batch-answer the creature's open questions.")
    ap.add_argument("--name", default="scholar")
    ap.add_argument("--show", action="store_true", help="print the wonder ledger and exit")
    ap.add_argument("--tick", action="store_true", help="run one budgeted curiosity batch")
    ap.add_argument("--oracles", default=None, metavar="PATH",
                    help="oracle registry (default: corpus/oracles.json)")
    ap.add_argument("--budget", type=int, default=8, help="wonders attempted per tick")
    ap.add_argument("--corroborate", type=int, default=2,
                    help="oracles consulted per wonder (2 = commit is possible)")
    ap.add_argument("--max-attempts", type=int, default=3,
                    help="fruitless attempts before a wonder is parked")
    args = ap.parse_args()

    c = _load(args.name)
    if args.show or not args.tick:
        led = CU.ledger(c)
        print(f"\n'{args.name}' wonders about ({len(led['open'])} open, "
              f"{len(led['parked'])} parked, {len(led['resolved'])} resolved):")
        _print_ledger(led)
        c.close()
        return 0

    path = Path(args.oracles) if args.oracles else _root() / "corpus" / "oracles.json"
    oracles = CU.oracles_from_json(path)
    # exclude the trainer's and the serving app's writes for the whole batch
    with creature_lock(_store_path(args.name).parent):
        out = CU.tick(c, oracles, budget=args.budget, corroborate=args.corroborate,
                      max_attempts=args.max_attempts)
        c.save(_store_path(args.name))
    print(f"\ntick for '{args.name}': attempted {len(out['attempted'])}, "
          f"resolved {len(out['resolved'])}, parked {len(out['parked'])}, "
          f"{out['open']} still open")
    for wid in out["resolved"]:
        print(f"   resolved: {wid}  [{c.resolved_wonders.get(wid, '?')}]")
    for wid in out["parked"]:
        print(f"   parked:   {wid}")
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
