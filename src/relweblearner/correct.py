"""Fix a mistake in a trained creature — by TEACHING it better, not retraining.

``--fix`` asserts the right fact in the owner's fiat voice (ONE honest
``correction`` episode) and the creature adjudicates the resulting conflict
itself (``Creature.revise``): it prefers the decree, flags the outweighed
episodes excluded — never deleted (invariant #5) — rebuilds by
replay-with-exclusions, and the sources that taught the lie LOSE TRUST in that
relation class, so their future word there is taken with a grain of salt
(``--trust`` shows the ledger). ``--retract`` remains the surgical half of
invariant #6: disqualify testimony outright when there is no better fact to
teach. Either way the fix is orders of magnitude cheaper than
``relweb-train --reset --all`` and claim-granular, so one bad fact goes without
taking the good facts around it.

    relweb-correct --fix owl four two       # teach "owl has two legs"; it drops "four" itself
    relweb-correct --retract owl four       # un-teach "owl has four legs" (no replacement)
    relweb-correct --show owl               # what does it currently believe about owl?
    relweb-correct --trust                  # whose word does it weigh, where, and why?

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
                    help="teach SOURCE -> RIGHT with correction authority; "
                         "the creature retracts SOURCE -> WRONG itself")
    ap.add_argument("--show", metavar="REFERENT", help="print current beliefs about REFERENT and exit")
    ap.add_argument("--trust", action="store_true",
                    help="print the learned per-source, per-relation-class trust ledger and exit")
    args = ap.parse_args()

    c = _load(args.name)
    if args.show:
        print(f"\nBeliefs about '{args.show}':")
        _show(c, args.show)
        return 0
    if args.trust:
        rows = c.trust_report()
        print(f"\nTrust ledger for '{args.name}' (weight 1 = one ordinary witness):")
        if not rows:
            print("   (no track records yet — nothing corroborated, nothing excluded)")
        for r in rows:
            print(f"   {r['source']:20s} {r['class']:30s} good={r['good']:<3d} "
                  f"bad={r['bad']:<3d} weight={r['weight']:<6.3f} [{r['standing']}]")
        return 0
    if not (args.retract or args.fix):
        ap.error("give --retract, --fix, --show, or --trust")

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
            print(f"\n   fixed '{src}': taught '{rep['taught'] or '(could not voice)'}' "
                  f"[{rep['status']}]; the creature {m}")
            for r in (rep.get("revision") or {}).get("resolved", []):
                print(f"   revised: kept '{r['source_node']} -> {r['kept']}', dropped "
                      f"'{r['source_node']} -> {r['dropped']}' ({r['episodes']} episode(s))")
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
