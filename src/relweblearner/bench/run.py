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
from .. import transport as TR
from ..creature import Creature
from ..holonomy import defects as _web_defects
from ..episodelog import InMemoryEpisodeLog
from . import world as W
from .baselines import GoldKB, InducedRules, Lookup, bench_oracle

PARAMS = dict(commit_k=2, min_group=10, induction_interval=40, buffer_cap=4000)
FAMILIES = ["F1-memory", "F2-invert-step", "F3-skip-transfer",
            "F4-invert-skip", "F5-refuse-color", "F6-plural-likes"]
P_FAMILY = "P7-junkcomp"        # scored on the LIE arm (the forgeries live there)
P8_FAMILY = "P8-coherent-forgery"   # lie arm; correspondence-honest answer: refuse
SYSTEMS = ["lookup", "induced-rules", "oracle-rules", "relweb", "relweb-noderive"]


def _train(episodes: list[dict], seed: int) -> Creature:
    c = Creature(f"bench-{seed}", log=InMemoryEpisodeLog(), seed=seed, **PARAMS)
    c.ingest(episodes)
    return c


def _belief_pairs(c: Creature) -> frozenset:
    """The full committed belief set as (source, target) pairs — class labels
    excluded on purpose (frame ids are induction-order-dependent)."""
    return frozenset(p for pairs in c._class_maps().values() for p in pairs)


def _admissions(c: Creature) -> list[tuple]:
    """Gate-accepted composition constraints, rendered through the classes'
    templates so the audit reads as language, not frame ids."""
    tr: dict = {}
    TR.infer(c._class_maps(), c.exception_fraction, trace=tr)
    tmpl = {r["class"]: "/".join(r["templates"]) for r in c._sector_rows()}
    return [(tmpl.get(h, h), tmpl.get(a, a), tmpl.get(b, b))
            for h, a, b in tr.get("accepted", [])]


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

    # F6 as SET retrieval: many-valued relations need precision/recall over
    # the full returned answer set, not single-answer membership
    f6q = next(q for q in w.queries if q["family"] == "F6-plural-likes")
    expect = set(f6q["expect"])

    def _pr(got: set) -> dict:
        tp = len(got & expect)
        return {"precision": tp / len(got) if got else 1.0,
                "recall": tp / len(expect)}
    f6_set = {name: _pr(b.answer_set(f6q["rel"], f6q["subject"]))
              for name, b in baselines.items()}
    r6 = creature.query(f6q["phrase"])
    f6_set["relweb"] = _pr({a["answer"] for a in r6.get("answers", [])})

    # false positives: a clean world must raise no alarms anywhere — and the
    # ADMISSION LOG is audited directly, not inferred from downstream errors:
    # on the clean arm every gate-accepted composition must be the true
    # structure (a skip head over step bodies).
    clean_flags = {name: len(b.flags()) for name, b in baselines.items()}
    clean_defects = len(_relweb_defects(creature))
    clean_flags["relweb"] = clean_defects + sum(
        1 for x in CU.wonders(creature) if x.get("qkind") == "arbitrate")
    # every admission must be CONSISTENT with the world's true offsets —
    # entailed compositions (step+ = skip+ ∘ step-, i.e. +1 = +2 - 1) are
    # true and count as such; only an offset-inconsistent admission is junk
    admissions = _admissions(creature)
    offsets = {"comes right after": 1, "is just before": -1,
               "sits two past": 2, "lies two shy of": -2}

    def _off(tmpl: str) -> int | None:
        return next((g for k, g in offsets.items() if k in tmpl), None)
    admissions_ok = all(
        None not in (_off(h), _off(a), _off(b)) and _off(h) == _off(a) + _off(b)
        for h, a, b in admissions)

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
        # the CAUSAL tie, not bool(any defect): the lie arm must carry MORE
        # defects than this seed's clean projection (0), and retraction must
        # clear them again (checked under unlearn below)
        "d2": len(ds) > clean_defects,
        "d2_lie_arm_defects": len(ds),
        "d2_clean_arm_defects": clean_defects,
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

    # P8, the COHERENT forgery (lie arm): a consistent phantom world taught
    # only by the liars. Coherence is not correspondence: the gate is
    # PREDICTED to admit it with zero extra defects, and the creature to
    # DERIVE the held-out fabricated fact. The correspondence-honest answer
    # is refusal; the recovery story is provenance (retraction), measured
    # under unlearn below.
    p8_probe = next(q for q in w.queries if q["family"] == P8_FAMILY)
    fab = w.forged["p8"]["fabricated_answer"]
    p8: dict[str, dict] = {}
    for name, b in b_lie.items():
        got = b.answer(p8_probe["rel"], p8_probe["subject"])
        p8[name] = {"refused": got is None, "derived_fabrication": got == fab}
    got = _relweb_answer(c_lie, p8_probe["phrase"])
    fake_admitted = any("vaults beyond" in h for h, _a, _b in _admissions(c_lie))
    p8["relweb"] = {"refused": got is None, "derived_fabrication": got == fab,
                    "structure_admitted": fake_admitted,
                    "extra_defects": len(ds) - 1}   # beyond the D2 loop lie's own

    # U1 exact unlearning: retract the liars; answers AND the full committed
    # belief set must match the clean arm (probe equality alone is too weak)
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
               "belief_set_match": _belief_pairs(c_lie) == _belief_pairs(creature),
               "p8_refused_after": _relweb_answer(c_lie, p8_probe["phrase"]) is None,
               "baselines_exact": base_un}

    return {"seed": seed, "families": fam, "f6_set": f6_set,
            "clean_flags": clean_flags, "admissions": admissions,
            "admissions_ok": admissions_ok,
            "discovered": discovered, "detect": detect, "poisoned": poisoned,
            "p7": p7, "p8": p8, "unlearn": unlearn,
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
            correct = sum(sum(r["families"][system][f]) for r in runs)
            total = sum(len(r["families"][system][f]) for r in runs)
            out["summary"][system][f] = {
                "mean": round(statistics.mean(accs), 4),
                "sd": round(statistics.stdev(accs), 4) if len(accs) > 1 else 0.0,
                "pooled": [correct, total],       # raw counts: n is small per seed
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
    out["summary"]["p8"] = {
        s: {"refused": round(statistics.mean(
                1.0 if r["p8"][s]["refused"] else 0.0 for r in runs), 4),
            "derived_fabrication": round(statistics.mean(
                1.0 if r["p8"][s]["derived_fabrication"] else 0.0 for r in runs), 4)}
        for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    out["summary"]["p8"]["relweb"]["structure_admitted"] = round(statistics.mean(
        1.0 if r["p8"]["relweb"]["structure_admitted"] else 0.0 for r in runs), 4)
    out["summary"]["f6_set"] = {
        s: {"precision": round(statistics.mean(
                r["f6_set"][s]["precision"] for r in runs), 4),
            "recall": round(statistics.mean(
                r["f6_set"][s]["recall"] for r in runs), 4)}
        for s in ("lookup", "induced-rules", "oracle-rules", "relweb")}
    out["summary"]["admissions_all_true"] = all(r["admissions_ok"] for r in runs)
    out["summary"]["unlearn_belief_set_match"] = round(statistics.mean(
        1.0 if r["unlearn"]["belief_set_match"] else 0.0 for r in runs), 4)
    out["summary"]["unlearn_p8_refused_after"] = round(statistics.mean(
        1.0 if r["unlearn"]["p8_refused_after"] else 0.0 for r in runs), 4)
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
        "P8 coherent forgery (lie arm; a consistent phantom world taught only "
        "by the liars — coherence is not correspondence, and this arm exists "
        "to measure that limit, which is SHARED):",
        "",
        "| system | refused (honest) | derived the fabrication |",
        "|---|---|---|",
    ] + [
        f"| {x} | {s['p8'][x]['refused']:.2f} | "
        f"{s['p8'][x]['derived_fabrication']:.2f} |"
        for x in ("lookup", "induced-rules", "oracle-rules", "relweb")
    ] + [
        "",
        f"RelWeb admitted the phantom structure through the gate: "
        f"{s['p8']['relweb']['structure_admitted']:.2f} of seeds "
        f"(predicted 1.00 — zero-defect coherent structure is invisible from "
        f"inside; recovery is provenance: post-retraction refusal "
        f"{s['unlearn_p8_refused_after']:.2f}).",
        "",
        "F6 as set retrieval (mean precision / recall over the full answer "
        "set): " + ", ".join(
            f"{x} {s['f6_set'][x]['precision']:.2f}/{s['f6_set'][x]['recall']:.2f}"
            for x in ("lookup", "induced-rules", "oracle-rules", "relweb")),
        "",
        "Poisoning (committed lie repeated when asked): " + ", ".join(
            f"{x} {s['poisoned'][x]:.2f}" for x in
            ("lookup", "induced-rules", "oracle-rules", "relweb")),
        "",
        f"U1 exact unlearning: relweb answer-match vs liar-free control "
        f"{s['unlearn_relweb_match']:.2f}; full committed-belief-set match "
        f"{s['unlearn_belief_set_match']:.2f}; baselines exact by "
        f"construction: {all(r['unlearn']['baselines_exact'] for r in runs)}",
        "",
        f"False alarms on the clean arm (total over seeds): "
        + ", ".join(f"{k} {v}" for k, v in s["clean_false_alarms"].items())
        + f"; every clean-arm gate admission audited true: "
          f"{s['admissions_all_true']}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=50)
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
