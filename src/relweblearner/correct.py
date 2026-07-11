"""Fix a mistake in a trained creature — WITHOUT retraining from scratch.

The episode log is immutable and append-only (invariant #5); a wrong belief is
corrected the way the paradigm prescribes (invariant #6): the lying episodes
are FLAGGED excluded — never deleted — and the model is rebuilt by
replay-with-exclusions. That is orders of magnitude cheaper than
``relweb-train --reset --all`` (no re-fetching, no worksheets, no re-reading the
whole corpus) and it is claim-granular, so one bad fact goes without taking the
good facts around it.

    relweb-correct --retract owl four                 # un-teach "owl has four legs"
    relweb-correct --fix owl four two                 # retract + teach "owl has two legs"
    relweb-correct --show owl                          # what does it currently believe about owl?

Shares the creature lock with the cron trainer and the serving app, so a fix
never interleaves with a scheduled run. The corrected checkpoint is saved in
place; the rotated-aside log a ``--reset`` would create is untouched.
"""

from __future__ import annotations

import argparse

from .creature import Creature
from .episodelog import JsonlEpisodeLog, creature_lock
from .train import _log_path, _store_path


def _load(name: str) -> Creature:
    path = _store_path(name)
    if not path.exists():
        raise SystemExit(f"no trained creature '{name}' at {path}")
    return Creature.load(path, log=JsonlEpisodeLog(_log_path(name)))


def _show(c: Creature, referent: str) -> None:
    r = c.about(referent)
    if not r["beliefs"]:
        print(f"   (nothing believed about '{referent}')")
        return
    for b in r["beliefs"]:
        print(f"   {referent} -> {b['target']:16s} [{b['status']}]  "
              f"{b['sentence'] or ''}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix a mistake without retraining from scratch.")
    ap.add_argument("--name", default="scholar")
    ap.add_argument("--retract", nargs=2, metavar=("SOURCE", "TARGET"),
                    help="un-teach the fact SOURCE -> TARGET (e.g. owl four)")
    ap.add_argument("--fix", nargs=3, metavar=("SOURCE", "WRONG", "RIGHT"),
                    help="retract SOURCE -> WRONG and teach SOURCE -> RIGHT")
    ap.add_argument("--show", metavar="REFERENT", help="print current beliefs about REFERENT and exit")
    args = ap.parse_args()

    c = _load(args.name)
    if args.show:
        print(f"\nBeliefs about '{args.show}':")
        _show(c, args.show)
        return 0
    if not (args.retract or args.fix):
        ap.error("give --retract, --fix, or --show")

    # exclude the serving app's writes for the whole fix (same lock it takes)
    with creature_lock(_store_path(args.name).parent):
        if args.retract:
            src, tgt = (x.strip().lower() for x in args.retract)
            print(f"\nBefore — beliefs about '{src}':")
            _show(c, src)
            rep = c.retract_claim(src, tgt)
            if rep["matched"] == 0:
                print(f"\n   no episode taught '{src} -> {tgt}' — nothing to retract.")
            else:
                print(f"\n   retracted '{src} -> {tgt}': excluded {rep['matched']} episode(s), "
                      f"{rep['uncommitted']} committed fact(s) uncommitted (collateral).")
        if args.fix:
            src, wrong, right = (x.strip().lower() for x in args.fix)
            rep = c.correct(src, wrong, right)
            m = f"excluded {rep['matched']} episode(s)" if rep["matched"] else "nothing to retract"
            print(f"\n   fixed '{src}': {m}; taught '{rep['taught'] or '(could not voice)'}' "
                  f"[{rep['status']}]")
            if rep["note"]:
                print(f"   note: {rep['note']}")
        c.commit()
        c.save(_store_path(args.name))
        print(f"\nAfter — beliefs about '{(args.fix or args.retract)[0].strip().lower()}':")
        _show(c, (args.fix or args.retract)[0].strip().lower())
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
