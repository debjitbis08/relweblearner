"""The carrier-ladder ORACLE FEASIBILITY sweep over GraphLog (plan §7¼).

For every train-split world: solve the TRUE rules over each finite carrier
(S3, I3, B3 — see ``carriers``), decode the world's real test queries with
the found assignment, and report the referee's diagnostics. The Z reference
(transport-oracle) and the CYK references are pulled from the existing runs
(results/graphlog, results/graphlog-heldout) so every row shares one query
set. NO learning happens here: a carrier whose oracle cannot outperform Z
is dead before discovery begins; rule_51-56 (GraphLog's valid/test world
splits) stay untouched for the eventual discovery phase.

Usage: relweb-carriers [--worlds ...] [--out results/carriers]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from . import carriers as CR
from .graphlog import load_world

LADDER = ["S3", "I3", "B3"]


def _existing_reference() -> dict:
    """majority / Z transport-oracle / cyk accuracies from the frozen runs."""
    ref = {}
    for path in ("results/graphlog/results.json",
                 "results/graphlog-heldout/results.json"):
        p = Path(path)
        if p.exists():
            for r in json.loads(p.read_text()):
                ref[r["world"]] = r["accuracy"]
    return ref


def run_world(name: str, ref: dict) -> dict:
    w = load_world(name, n_train=150)
    prior = Counter(r["target"] for r in w["train"])
    majority = max(prior, key=lambda r: (prior[r], r))
    out = {"world": name, "reference": ref.get(name, {}),
           "carriers": {}}
    for cname in LADDER:
        carrier = CR.CARRIERS[cname]()
        assign, sat = CR.solve_rules(w["rules"], carrier,
                                     seed=hash((name, cname)) & 0xFFFF)
        acc = sum(CR.decode(rec, assign, majority, prior) == rec["query"][2]
                  for rec in w["test"]) / len(w["test"])
        out["carriers"][cname] = {
            # heuristic lower bound (min-conflicts), not a true oracle
            "oracle_accuracy": round(acc, 4),
            **CR.audit(assign, sat, len(w["rules"])),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worlds", default=",".join(f"rule_{i}" for i in range(51)))
    ap.add_argument("--out", default="results/carriers")
    args = ap.parse_args()
    t0 = time.time()
    ref = _existing_reference()
    results = []
    for name in args.worlds.split(","):
        r = run_world(name.strip(), ref)
        c = r["carriers"]
        print(f"{r['world']}: Z={r['reference'].get('transport-oracle', float('nan')):.3f}  "
              + "  ".join(f"{k}={c[k]['oracle_accuracy']:.3f}"
                          f"{'*' if c[k]['exact'] else ''}" for k in LADDER)
              + f"  cyk={r['reference'].get('cyk-oracle', float('nan')):.3f}"
              + f"  ({time.time() - t0:.0f}s)", flush=True)
        results.append(r)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))
    lines = ["# Carrier ladder: heuristic feasibility accuracy using true rules (no learning)",
             "",
             f"{len(results)} worlds; {time.time() - t0:.0f}s. '*' = every true "
             "rule satisfied by the found assignment (local search: exactness "
             "is proven, infeasibility is not).",
             "",
             "| world | majority | Z | S3 | I3 | B3 | cyk-oracle | "
             "B3 sat | B3 distinct |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        ref_a = r["reference"]
        c = r["carriers"]
        lines.append(
            f"| {r['world']} | {ref_a.get('majority', float('nan')):.3f} | "
            f"{ref_a.get('transport-oracle', float('nan')):.3f} | "
            + " | ".join(f"{c[k]['oracle_accuracy']:.3f}"
                         f"{'*' if c[k]['exact'] else ''}" for k in LADDER)
            + f" | {ref_a.get('cyk-oracle', float('nan')):.3f} | "
            f"{c['B3']['satisfied'][0]}/{c['B3']['satisfied'][1]} | "
            f"{c['B3']['distinct_elements']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:10]))


if __name__ == "__main__":
    main()
