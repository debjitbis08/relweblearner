"""The falsification benchmark runner (docs/falsification-plan.md).

Per seed, TWO arms trained on the same generated world:

* the CLEAN arm (liar pages filtered) scores the capability families F1-F6 —
  capability is measured without adversarial noise so one confound cannot
  contaminate every family;
* the LIE arm (full stream, two colluding liar books) scores the detection
  probes D1/D2, the poisoning probe, and exact unlearning U1 (retract the
  liars, compare every answer against the clean arm).

Every system consumes the identical stream. The creature reads raw pages; the
baselines read gold parses (a handicap AGAINST RelWeb — stated in the plan).

Usage:  relweb-bench [--seeds N] [--out results/bench]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from .. import curiosity as CU
from ..creature import Creature
from ..holonomy import defects as _web_defects
from ..episodelog import InMemoryEpisodeLog
from . import world as W
from .baselines import GoldKB, InducedRules, Lookup, bench_oracle

PARAMS = dict(commit_k=2, min_group=10, induction_interval=40, buffer_cap=4000)
FAMILIES = ["F1-memory", "F2-invert-step", "F3-skip-transfer",
            "F4-invert-skip", "F5-refuse-color", "F6-plural-likes"]
P_FAMILY = "P7-junkcomp"      # scored on the LIE arm (the forgeries live there)
SYSTEMS = ["lookup", "induced-rules", "oracle-rules", "relweb", "relweb-noderive"]


def _train(episodes: list[dict], seed: int) -> Creature:
    c = Creature(f"bench-{seed}", log=InMemoryEpisodeLog(), seed=seed, **PARAMS)
    c.ingest(episodes)
    return c


def _relweb_answer(c: Creature, phrase: str, derive: bool = True) -> str | None:
    r = c.query(phrase)
    if not (r.get("kind") == "answer" and r.get("known") and r.get("answers")):
        return None
    if derive:
        return r["answers"][0]["answer"]
    hits = [a for a in r["answers"] if a["status"] == "committed"]
    return hits[0]["answer"] if hits else None


def _correct(got: str | None, expect) -> bool:
    if expect is None:
        return got is None
    if isinstance(expect, (set, frozenset)):
        return got in expect
    return got == expect


def _score(w: W.World, answer_fn, families: list[str] = FAMILIES) -> dict[str, list[bool]]:
    per: dict[str, list[bool]] = {f: [] for f in families}
    for q in w.queries:
        if q["family"] in per:
            per[q["family"]].append(_correct(answer_fn(q), q["expect"]))
    return per


def _relweb_defects(c: Creature) -> list:
    return [d for web in c.concept_webs().values() for d in _web_defects(web)]


def run_seed(seed: int) -> dict:
    w = W.generate(seed)
    clean = [(ep, g) for ep, g in zip(w.episodes, w.gold)
             if ep["book"] not in w.liar_books]

    # ---------------- clean arm: capability
    kb = GoldKB([(ep["book"], g) for ep, g in clean])
    baselines = {"lookup": Lookup(kb), "induced-rules": InducedRules(kb),
                 "oracle-rules": bench_oracle(kb)}
    creature = _train([ep for ep, _ in clean], seed)

    fam: dict[str, dict] = {}
    for name, b in baselines.items():
        fam[name] = _score(w, lambda q, b=b: b.answer(q["rel"], q["subject"]))
    fam["relweb"] = _score(w, lambda q: _relweb_answer(creature, q["phrase"]))
    fam["relweb-noderive"] = _score(
        w, lambda q: _relweb_answer(creature, q["phrase"], derive=False))

    # false positives: a clean world must raise no alarms anywhere
    clean_flags = {name: len(b.flags()) for name, b in baselines.items()}
    clean_flags["relweb"] = len(_relweb_defects(creature)) + sum(
        1 for x in CU.wonders(creature) if x.get("qkind") == "arbitrate")

    # what the creature actually discovered (for the report)
    discovered = [{"class": r["class"], "sector": r["sector"],
                   "transport": r["transport"], "templates": r["templates"]}
                  for r in creature._sector_rows()]

    # ---------------- lie arm: detection, poisoning, unlearning
    kb_lie = GoldKB([(ep["book"], g) for ep, g in zip(w.episodes, w.gold)])
    b_lie = {"lookup": Lookup(kb_lie), "induced-rules": InducedRules(kb_lie),
             "oracle-rules": bench_oracle(kb_lie)}
    c_lie = _train(list(w.episodes), seed)

    detect: dict[str, dict] = {}
    for name, b in b_lie.items():
        fl = b.flags()
        detect[name] = {
            "d1": any(f["kind"] == "double-target" and f["subject"] == w.d1["subject"]
                      for f in fl),
            "d2": any(f["kind"] == "derived-conflict" and f["subject"] == w.d2["subject"]
                      for f in fl),
            "spurious": sum(1 for f in fl
                            if f["subject"] not in (w.d1["subject"], w.d2["subject"])),
        }
    ds = _relweb_defects(c_lie)
    arb = [x for x in CU.wonders(c_lie) if x.get("qkind") == "arbitrate"]
    detect["relweb"] = {
        "d1": any(x.get("subject") == w.d1["subject"] for x in arb),
        "d2": bool(ds),
        "d2_localized": any({d.edge.u, d.edge.v} & {w.d2["subject"], w.d2["wrong"]}
                            for d in ds),
        "spurious": sum(1 for x in arb if x.get("subject") != w.d1["subject"]),
    }

    # poisoning: with the lie committed, who repeats it?
    poison_q = W.ASK["step+"].format(s=w.d2["subject"])
    poisoned = {name: b.answer("step+", w.d2["subject"]) == w.d2["wrong"]
                for name, b in b_lie.items()}
    poisoned["relweb"] = _relweb_answer(c_lie, poison_q) == w.d2["wrong"]

    # P7, the poisoned-composition attack (lie arm): who admits the forged
    # rule step+ = near∘near, and who derives garbage on the clean chains?
    p7: dict[str, dict] = {}
    for name, b in b_lie.items():
        scored = _score(w, lambda q, b=b: b.answer(q["rel"], q["subject"]),
                        families=[P_FAMILY])[P_FAMILY]
        rule = tuple(w.forged["rule"])
        p7[name] = {"accuracy": _accuracy(scored),
                    "junk_admitted": rule in getattr(b, "compositions", [])}
    scored = _score(w, lambda q: _relweb_answer(c_lie, q["phrase"]),
                    families=[P_FAMILY])[P_FAMILY]
    step_row = next(r for r in c_lie._sector_rows()
                    if any("comes right after" in t for t in r["templates"]))
    p7["relweb"] = {"accuracy": _accuracy(scored),
                    # admitted junk would zero the live step generator
                    "junk_admitted": not (step_row["sector"] == "antisymmetric"
                                          and step_row["transport"] not in (0, None))}

    # U1 exact unlearning: retract the liars, answers must match the clean arm
    for liar in w.liar_books:
        c_lie.retract_source(liar)
    probes = [(q["phrase"],) for q in w.queries] + [(poison_q,)]
    matches = sum(_relweb_answer(c_lie, p) == _relweb_answer(creature, p)
                  for (p,) in probes)
    kb_un = GoldKB([(ep["book"], g) for ep, g in zip(w.episodes, w.gold)],
                   excluded_books=frozenset(w.liar_books))
    base_un = all(InducedRules(kb_un).answer(q["rel"], q["subject"])
                  == baselines["induced-rules"].answer(q["rel"], q["subject"])
                  for q in w.queries)
    unlearn = {"relweb_match": matches / len(probes),
               "relweb_defects_after": len(_relweb_defects(c_lie)),
               "baselines_exact": base_un}

    return {"seed": seed, "families": fam, "clean_flags": clean_flags,
            "discovered": discovered, "detect": detect, "poisoned": poisoned,
            "p7": p7, "unlearn": unlearn,
            "n_episodes": len(w.episodes), "n_queries": len(w.queries)}


# ------------------------------------------------------------------ reporting

def _accuracy(rows: list[bool]) -> float:
    return sum(rows) / len(rows) if rows else float("nan")


def aggregate(runs: list[dict]) -> dict:
    out: dict = {"per_seed": runs, "summary": {}}
    for system in SYSTEMS:
        out["summary"][system] = {}
        for f in FAMILIES:
            accs = [_accuracy(r["families"][system][f]) for r in runs]
            out["summary"][system][f] = {
                "mean": round(statistics.mean(accs), 4),
                "sd": round(statistics.stdev(accs), 4) if len(accs) > 1 else 0.0,
                "per_seed": [round(a, 4) for a in accs],
            }
    for probe in ("d1", "d2"):
        out["summary"][f"detect_{probe}"] = {
            s: round(statistics.mean(1.0 if r["detect"][s][probe] else 0.0
                                     for r in runs), 4)
            for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    out["summary"]["d2_localized"] = round(statistics.mean(
        1.0 if r["detect"]["relweb"].get("d2_localized") else 0.0 for r in runs), 4)
    out["summary"]["poisoned"] = {
        s: round(statistics.mean(1.0 if r["poisoned"][s] else 0.0 for r in runs), 4)
        for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    out["summary"]["unlearn_relweb_match"] = round(statistics.mean(
        r["unlearn"]["relweb_match"] for r in runs), 4)
    out["summary"]["p7"] = {
        s: {"accuracy": round(statistics.mean(r["p7"][s]["accuracy"] for r in runs), 4),
            "junk_admitted": round(statistics.mean(
                1.0 if r["p7"][s]["junk_admitted"] else 0.0 for r in runs), 4)}
        for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    out["summary"]["clean_false_alarms"] = {
        s: sum(r["clean_flags"][s] for r in runs)
        for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    return out


def report_md(agg: dict, elapsed: float) -> str:
    runs = agg["per_seed"]
    lines = [
        "# Falsification benchmark — results",
        "",
        f"{len(runs)} seeds, ~{runs[0]['n_episodes']} pages and "
        f"{runs[0]['n_queries']} queries each; {elapsed:.0f}s total. "
        "Pre-registered design and predictions: docs/falsification-plan.md "
        "(written before this run).",
        "",
        "Accuracy, mean +/- sd over seeds:",
        "",
        "| family | " + " | ".join(SYSTEMS) + " |",
        "|---|" + "---|" * len(SYSTEMS),
    ]
    for f in FAMILIES:
        row = [f]
        for s in SYSTEMS:
            m = agg["summary"][s][f]
            row.append(f"{m['mean']:.2f} +/- {m['sd']:.2f}")
        lines.append("| " + " | ".join(row) + " |")
    s = agg["summary"]
    lines += [
        "",
        "Detection (rate over seeds):",
        "",
        "| probe | lookup | induced-rules | oracle-rules | relweb |",
        "|---|---|---|---|---|",
        "| D1 direct conflict | " + " | ".join(
            f"{s['detect_d1'][x]:.2f}" for x in
            ("lookup", "induced-rules", "oracle-rules", "relweb")) + " |",
        "| D2 loop lie | " + " | ".join(
            f"{s['detect_d2'][x]:.2f}" for x in
            ("lookup", "induced-rules", "oracle-rules", "relweb")) + " |",
        "",
        f"RelWeb D2 localization (defect touches the lie's endpoints): "
        f"{s['d2_localized']:.2f}",
        "",
        "P7 poisoned composition (lie arm; forged rule step+ = near∘near):",
        "",
        "| system | junk rule admitted | refusal accuracy on clean chains |",
        "|---|---|---|",
    ] + [
        f"| {x} | {s['p7'][x]['junk_admitted']:.2f} | {s['p7'][x]['accuracy']:.2f} |"
        for x in ("lookup", "induced-rules", "oracle-rules", "relweb")
    ] + [
        "",
        "Poisoning (committed lie repeated when asked): " + ", ".join(
            f"{x} {s['poisoned'][x]:.2f}" for x in
            ("lookup", "induced-rules", "oracle-rules", "relweb")),
        "",
        f"U1 exact unlearning: relweb answer-match vs liar-free control "
        f"{s['unlearn_relweb_match']:.2f}; baselines exact by construction: "
        f"{all(r['unlearn']['baselines_exact'] for r in runs)}",
        "",
        f"False alarms on the clean arm (total over seeds): "
        + ", ".join(f"{k} {v}" for k, v in s["clean_false_alarms"].items()),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="results/bench")
    args = ap.parse_args()
    t0 = time.time()
    runs = []
    for seed in range(args.seeds):
        runs.append(run_seed(seed))
        print(f"seed {seed} done ({time.time() - t0:.0f}s)")
    agg = aggregate(runs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(agg, indent=1, default=str))
    md = report_md(agg, time.time() - t0)
    (out / "report.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
