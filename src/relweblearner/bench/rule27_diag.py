"""The rule_27 diagnosis (E6) — per-episode failure attribution + 4 probes.

Pre-registration: docs/rule27-diagnosis-plan.md (committed before this code).
This is a DIAGNOSIS, not a bench: no scored predictions; the deliverable is
the attribution table of §4a and the counterfactual probes of §4b. All frozen
machinery (graphlog, multiweb_graphlog, multiweb_graded) is imported and
reused UNCHANGED; no constant is touched. The module refuses to attribute
anything until it has reproduced the frozen per-world accuracies exactly
(view-alone 0.133 / ensemble 0.163 / gold-pooled 0.828 at seed 0) — the
consistency gate of plan §6.

Counterfactual probes (oracle identities, rule patches, un-merges) are
diagnostic instruments ONLY — they use evaluation-side gold and must never be
reported as system capabilities.

Usage:  relweb-rule27-diag [--seeds-robust 4] [--out results/rule27-diagnosis]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from . import multiweb_graded as GR
from . import multiweb_graphlog as MG
from .graphlog import MAX_PATH, _reduce, load_world

WORLD = "rule_27"
FROZEN = {"view-alone": 0.133, "ensemble": 0.163, "gold-pooled": 0.828}


# ------------------------------------------------------------------ the setup

def setup(seed: int = 0, n_train: int = 150) -> dict:
    """Recompute run_world's internals for WORLD, exactly as frozen
    (multiweb_graphlog.run_world, same call order, same seed)."""
    w = load_world(WORLD, n_train)
    labels = sorted({r for g in w["train"] + w["test"] for _u, _v, r in g["edges"]}
                    | {g["target"] for g in w["train"]}
                    | {g["query"][2] for g in w["test"]})
    views = MG.make_views(w["train"], labels, seed)
    votes_a = MG.triangle_votes(views["a"])
    votes_b = MG.triangle_votes(views["b"])
    anchors = MG.pick_anchors(w["train"], views, votes_a)
    mapping = MG.extend_mapping(votes_a, votes_b, anchors)

    inv_a = {v: k for k, v in views["perm_a"].items()}
    inv_b = {v: k for k, v in views["perm_b"].items()}
    prior_a = Counter(r for g in views["a"] for _u, _v, r in g["edges"])
    maj_a = max(prior_a, key=lambda r: (prior_a[r], r))
    true_map = {views["perm_a"][l]: views["perm_b"][l] for l in labels}
    ext_pairs = {x: y for x, y in mapping.items() if x not in anchors}
    wrong = [(x, y) for x, y in ext_pairs.items() if true_map.get(x) != y]
    orphans = [(x, y) for x, y in wrong
               if inv_a[x] in views["hide_b"] or inv_b[y] in views["hide_a"]]

    return {"w": w, "labels": labels, "views": views,
            "votes_a": votes_a, "votes_b": votes_b,
            "anchors": anchors, "mapping": mapping,
            "rules_alone": MG._threshold(votes_a),
            "rules_gold": MG._threshold(MG.triangle_votes(w["train"])),
            "inv_a": inv_a, "inv_b": inv_b, "maj_a": maj_a,
            "true_map": true_map, "wrong": wrong, "orphans": orphans}


def score(ctx: dict, mapping: dict, rules_override: dict | None = None,
          mode: str = "ensemble") -> float:
    """run_world's acc(), parameterized on the mapping/rules under a
    counterfactual. mode 'gold' scores rules_gold on the raw rendering."""
    w, views, maj_a = ctx["w"], ctx["views"], ctx["maj_a"]
    back = lambda t: ctx["inv_a"].get(t, ctx["inv_b"].get(t, t))
    if mode == "gold":
        rules = rules_override if rules_override is not None else ctx["rules_gold"]
        hit = sum(_predict(rec["edges"], rec, rules, back(maj_a)) == rec["query"][2]
                  for rec in w["test"])
        return hit / len(w["test"])
    inv_map = {y: x for x, y in mapping.items()}
    rules = (rules_override if rules_override is not None
             else MG.project(ctx["votes_a"], ctx["votes_b"], mapping))
    hit = 0
    for rec in w["test"]:
        r = MG._render_test(rec, views, inv_map, ensemble=(mode == "ensemble"))
        hit += back(_predict(r["edges"], rec, rules, maj_a)) == rec["query"][2]
    return hit / len(w["test"])


def _predict(edges, rec, rules, majority) -> str:
    """graphlog.cyk_predict, verbatim logic, on pre-rendered edges."""
    u0, v0, _ = rec["query"]
    out_idx: dict[int, list] = defaultdict(list)
    for u, v, rel in edges:
        out_idx[u].append((v, rel))
    results: Counter = Counter()
    stack = [(u0, [])]
    while stack:
        node, labels = stack.pop()
        if node == v0 and labels:
            for r in _reduce(tuple(labels), rules):
                results[r] += 1
            continue
        if len(labels) >= MAX_PATH:
            continue
        for y, rel in out_idx[node]:
            stack.append((y, labels + [rel]))
    if not results:
        return majority
    return max(results, key=lambda r: (results[r], r))


# ---------------------------------------------------- §4a failure attribution

def _paths(edges, u0, v0) -> list[tuple]:
    """All witnessing label sequences u0->v0, length <= MAX_PATH (the same
    census cyk_predict walks)."""
    out_idx: dict[int, list] = defaultdict(list)
    for u, v, rel in edges:
        out_idx[u].append((v, rel))
    found, stack = [], [(u0, ())]
    while stack:
        node, labels = stack.pop()
        if node == v0 and labels:
            found.append(labels)
            continue
        if len(labels) >= MAX_PATH:
            continue
        for y, rel in out_idx[node]:
            stack.append((y, labels + (rel,)))
    return found


def _missing_keys(labels: tuple, rules: dict, memo: dict) -> set[tuple]:
    """The blocking frontier of a non-reducing sequence: (a, b) span pairs
    that WOULD chain if a rule existed. Recurses into spans that themselves
    fail to reduce."""
    if len(labels) <= 1:
        return set()
    out: set = set()
    for i in range(1, len(labels)):
        left = _reduce(labels[:i], rules, memo)
        right = _reduce(labels[i:], rules, memo)
        if left and right:
            out |= {(a, b) for a in left for b in right if (a, b) not in rules}
        if not left:
            out |= _missing_keys(labels[:i], rules, memo)
        if not right:
            out |= _missing_keys(labels[i:], rules, memo)
    return out


def attribute(ctx: dict) -> dict:
    """Per failing test episode, the FIRST blocking cause (plan §4a):
    no-path | cyk-dead (split-token / missing-rule / other) |
    wrong-argmax (orphan-tainted / other). Also records accidental majority
    hits and the H1 path census per failure."""
    w, views = ctx["w"], ctx["views"]
    mapping, maj_a = ctx["mapping"], ctx["maj_a"]
    inv_map = {y: x for x, y in mapping.items()}
    rules_ens = MG.project(ctx["votes_a"], ctx["votes_b"], mapping)
    back = lambda t: ctx["inv_a"].get(t, ctx["inv_b"].get(t, t))
    is_b = lambda t: t in ctx["inv_b"] and t not in ctx["inv_a"]

    # un-merged rules once, for the wrong-argmax orphan-taint test
    m_unmerged = {x: y for x, y in mapping.items()
                  if (x, y) not in set(ctx["orphans"])}
    rules_unm = MG.project(ctx["votes_a"], ctx["votes_b"], m_unmerged)
    inv_unm = {y: x for x, y in m_unmerged.items()}

    episodes, cells = [], Counter()
    for idx, rec in enumerate(w["test"]):
        r = MG._render_test(rec, views, inv_map, ensemble=True)
        u0, v0, gold_t = rec["query"]
        ens_paths = _paths(r["edges"], u0, v0)
        gold_paths = _paths(rec["edges"], u0, v0)
        ep = {"i": idx, "target": gold_t,
              "ens_shortest": min((len(p) for p in ens_paths), default=None),
              "gold_shortest": min((len(p) for p in gold_paths), default=None)}

        if not ens_paths:
            got = back(maj_a)
            ep["cause"] = ("accidental-majority-hit" if got == gold_t
                           else "no-path")
        else:
            memo: dict = {}
            results: Counter = Counter()
            for p in ens_paths:
                for h in _reduce(p, rules_ens, memo):
                    results[h] += 1
            if not results:
                got = back(maj_a)
                if got == gold_t:
                    ep["cause"] = "accidental-majority-hit"
                else:
                    keys = set()
                    for p in ens_paths:
                        keys |= _missing_keys(p, rules_ens, memo)
                    split = sorted(k for k in keys if is_b(k[0]) or is_b(k[1]))
                    in_gold = sorted(k for k in keys - set(split)
                                     if (back(k[0]), back(k[1])) in ctx["rules_gold"])
                    ep["cause"] = ("cyk-dead-split" if split else
                                   "cyk-dead-missing-rule" if in_gold else
                                   "cyk-dead-other")
                    ep["missing_split"] = split[:8]
                    ep["missing_in_gold"] = in_gold[:8]
            else:
                got = back(max(results, key=lambda h: (results[h], h)))
                if got == gold_t:
                    ep["cause"] = "correct"
                else:
                    r2 = MG._render_test(rec, views, inv_unm, ensemble=True)
                    got2 = back(_predict(r2["edges"], rec, rules_unm, maj_a))
                    ep["cause"] = ("wrong-argmax-orphan-tainted"
                                   if got2 != got else "wrong-argmax-other")
                    ep["got"] = got
        cells[ep["cause"]] += 1
        episodes.append(ep)

    n = len(w["test"])
    fails = n - cells["correct"] - cells["accidental-majority-hit"]
    return {"n_test": n, "n_correct": cells["correct"],
            "n_failing": fails, "cells": dict(cells),
            "h1_gold_path_only": sum(1 for e in episodes
                                     if e["cause"] == "no-path"
                                     and e["gold_shortest"] is not None),
            "episodes": episodes}


# ---------------------------------------------------- §4b counterfactual probes

def probe_unmerge(ctx: dict) -> dict:
    """H4: remove the wrong orphan pair(s), re-project, re-score."""
    base = score(ctx, ctx["mapping"])
    m2 = {x: y for x, y in ctx["mapping"].items()
          if (x, y) not in set(ctx["orphans"])}
    return {"orphan_pairs": [[x, y, ctx["inv_a"].get(x), ctx["inv_b"].get(y)]
                             for x, y in ctx["orphans"]],
            "acc_base": round(base, 4),
            "acc_unmerged": round(score(ctx, m2), 4)}


def repair_candidates(ctx: dict) -> list[str]:
    """Mutually visible labels whose identity the mapping lacks or has wrong."""
    v = ctx["views"]
    return [l for l in ctx["labels"]
            if l not in v["hide_a"] and l not in v["hide_b"]
            and ctx["mapping"].get(v["perm_a"][l]) != v["perm_b"][l]]


def probe_repair_curve(ctx: dict) -> list[dict]:
    """H3: greedy oracle repair, best-first by accuracy gain. Adding a true
    pair evicts any current pair using either token (that eviction IS part
    of the repair and is recorded)."""
    v = ctx["views"]
    cur = dict(ctx["mapping"])
    todo = repair_candidates(ctx)
    curve = [{"repaired": None, "acc": round(score(ctx, cur), 4)}]
    while todo:
        best = None
        for l in todo:
            xa, yb = v["perm_a"][l], v["perm_b"][l]
            m2 = {x: y for x, y in cur.items() if x != xa and y != yb}
            m2[xa] = yb
            a = score(ctx, m2)
            if best is None or (a, l) > (best[0], best[1]):
                best = (a, l, m2)
        a, l, m2 = best
        evicted = [[x, y] for x, y in cur.items()
                   if (x == v["perm_a"][l] or y == v["perm_b"][l])
                   and m2.get(x) != y]
        cur = m2
        todo.remove(l)
        curve.append({"repaired": l, "evicted": evicted, "acc": round(a, 4)})
    return curve


def probe_rule_patch(ctx: dict) -> dict:
    """H2: gold rules absent from the ensemble inventory — patch them in
    (translated to the ensemble vocabulary) and re-score; ablate them from
    gold and re-score gold."""
    v, mapping = ctx["views"], ctx["mapping"]
    inv_map = {y: x for x, y in mapping.items()}
    ens_tok = lambda l: (v["perm_a"][l] if l not in v["hide_a"]
                         else inv_map.get(v["perm_b"][l], v["perm_b"][l]))
    rules_ens = MG.project(ctx["votes_a"], ctx["votes_b"], mapping)
    missing = {(ra, rb): rh for (ra, rb), rh in ctx["rules_gold"].items()
               if (ens_tok(ra), ens_tok(rb)) not in rules_ens}
    patched = dict(rules_ens)
    for (ra, rb), rh in missing.items():
        patched[(ens_tok(ra), ens_tok(rb))] = ens_tok(rh)
    ablated = {k: h for k, h in ctx["rules_gold"].items() if k not in missing}
    return {"n_missing": len(missing),
            "missing_raw": sorted([ra, rb, rh] for (ra, rb), rh in missing.items()),
            "acc_base": round(score(ctx, mapping), 4),
            "acc_patched": round(score(ctx, mapping, rules_override=patched), 4),
            "acc_gold": round(score(ctx, mapping, mode="gold"), 4),
            "acc_gold_ablated": round(score(ctx, mapping, mode="gold",
                                            rules_override=ablated), 4)}


def probe_graded(ctx: dict, attribution: dict) -> dict:
    """H3/H4 mechanism: the frozen graded machinery's view of the implicated
    tokens, and whether graded predictions moved on the discrete failures."""
    v, anchors = ctx["views"], ctx["anchors"]
    ia, ib, S = GR.token_similarity(ctx["votes_a"], ctx["votes_b"], anchors)
    commits = GR.hardened(ia, ib, S, anchors)
    merge_of = {y: x for x, y in commits.items()}

    implicated = sorted({t for e in attribution["episodes"]
                         for k in e.get("missing_split", []) for t in k
                         if t in ib and t not in ia}
                        | {y for _x, y in ctx["orphans"]})
    tokens = []
    for y in implicated:
        raw = ctx["inv_b"].get(y)
        xt = v["perm_a"][raw] if raw is not None and raw not in v["hide_a"] else None
        row = {"b_token": y, "raw": raw, "true_a": xt,
               "committed_to": merge_of.get(y)}
        if xt is not None and xt in ia and y in ib:
            j = ib[y]
            row["sim_true"] = round(float(S[ia[xt], j]), 4)
            row["col_argmax_is_true"] = bool(S[:, j].argmax() == ia[xt])
            row["row_argmax_is_true"] = bool(S[ia[xt]].argmax() == j)
            row["clears_hard_sim"] = bool(S[ia[xt], j] >= GR.HARD_SIM)
        tokens.append(row)

    def sim(rule_tok, path_tok):
        if rule_tok == path_tok:
            return 1.0
        a, b = ((rule_tok, path_tok) if rule_tok in ia else
                (path_tok, rule_tok) if path_tok in ia else (None, None))
        if a is None or b not in ib:
            return 0.0
        return float(S[ia[a], ib[b]])

    rules = ([(p, q, h) for (p, q), h in MG._threshold(ctx["votes_a"]).items()]
             + [(p, q, h) for (p, q), h in MG._threshold(ctx["votes_b"]).items()])
    back = lambda t: ctx["inv_a"].get(t, ctx["inv_b"].get(t, t))
    fail_idx = {e["i"] for e in attribution["episodes"]
                if e["cause"] not in ("correct", "accidental-majority-hit")}
    hit = moved = fell_back = 0
    for idx, rec in enumerate(ctx["w"]["test"]):
        edges = []
        for u, vv, r in rec["edges"]:
            if r not in v["hide_a"]:
                edges.append((u, vv, v["perm_a"][r]))
            elif r not in v["hide_b"]:
                edges.append((u, vv, v["perm_b"][r]))
        got = GR.graded_predict({"edges": edges, "query": rec["query"]},
                                rules, sim, merge_of, ctx["maj_a"])
        if back(got) == rec["query"][2]:
            hit += 1
        if idx in fail_idx:
            if got == ctx["maj_a"]:
                fell_back += 1
            if back(got) != rec["query"][2]:
                moved += 0          # still wrong: unmoved in outcome
            else:
                moved += 1
    return {"graded_acc": round(hit / len(ctx["w"]["test"]), 4),
            "graded_commits_n": len({x: y for x, y in commits.items()
                                     if x not in anchors}),
            "failing_healed_by_graded": moved,
            "failing_fell_back_to_majority": fell_back,
            "implicated_tokens": tokens}


# ------------------------------------------------------------------ reporting

def _report_md(out: dict) -> str:
    a, gate = out["attribution"], out["consistency_gate"]
    lines = [
        "# The rule_27 diagnosis (E6) — attribution and probes", "",
        "Pre-registered: docs/rule27-diagnosis-plan.md (committed before this "
        "code). Counterfactual probes are diagnostic instruments using "
        "evaluation-side gold — NOT system capabilities.", "",
        f"Consistency gate (plan §6): recomputed accuracies "
        f"{gate['recomputed']} vs frozen {gate['frozen']} — "
        f"{'PASS' if gate['pass'] else 'FAIL — attribution void'}.", "",
        "## §4a Failure attribution (seed 0)", "",
        f"{a['n_test']} test episodes: {a['n_correct']} correct, "
        f"{a['cells'].get('accidental-majority-hit', 0)} accidental majority "
        f"hits, {a['n_failing']} failing.", "",
        "| cause | episodes |", "|---|---|"]
    for cause, n in sorted(a["cells"].items(), key=lambda kv: -kv[1]):
        if cause != "correct":
            lines.append(f"| {cause} | {n} |")
    lines += ["",
              f"H1 cell (no ensemble path but gold path exists): "
              f"{a['h1_gold_path_only']}", "",
              "## §4b Probes", "",
              "### Un-merge (H4)", "",
              f"```json\n{json.dumps(out['unmerge'], indent=1)}\n```", "",
              "### Oracle repair curve (H3)", "",
              f"```json\n{json.dumps(out['repair_curve'], indent=1)}\n```", "",
              "### Rule patch (H2)", "",
              f"```json\n{json.dumps({k: v for k, v in out['rule_patch'].items() if k != 'missing_raw'}, indent=1)}\n```", "",
              "### Graded post-mortem (H3/H4 mechanism)", "",
              f"```json\n{json.dumps(out['graded'], indent=1)}\n```", ""]
    if out.get("robustness"):
        lines += ["## §4c Robustness (secondary, seeds 1+)", "",
                  "| seed | ensemble acc | cells |", "|---|---|---|"]
        for r in out["robustness"]:
            lines.append(f"| {r['seed']} | {r['acc']:.3f} | {r['cells']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds-robust", type=int, default=4,
                    help="additional seeds (1..N) for §4c attribution shares")
    ap.add_argument("--out", default="results/rule27-diagnosis")
    args = ap.parse_args(argv)

    t0 = time.time()
    ctx = setup(seed=0)
    recomputed = {"view-alone": round(score(ctx, ctx["mapping"], rules_override=ctx["rules_alone"], mode="alone"), 3),
                  "ensemble": round(score(ctx, ctx["mapping"]), 3),
                  "gold-pooled": round(score(ctx, ctx["mapping"], mode="gold"), 3)}
    gate = {"frozen": FROZEN, "recomputed": recomputed,
            "pass": recomputed == FROZEN}
    out: dict = {"world": WORLD, "consistency_gate": gate}
    if not gate["pass"]:
        print(json.dumps(gate, indent=2))
        raise SystemExit("consistency gate FAILED — frozen run not reproduced; "
                         "attribution would be about the wrong system")

    attribution = attribute(ctx)
    out["attribution"] = attribution
    out["unmerge"] = probe_unmerge(ctx)
    out["repair_curve"] = probe_repair_curve(ctx)
    out["rule_patch"] = probe_rule_patch(ctx)
    out["graded"] = probe_graded(ctx, attribution)

    robust = []
    for s in range(1, args.seeds_robust + 1):
        c = setup(seed=s)
        att = attribute(c)
        robust.append({"seed": s, "acc": score(c, c["mapping"]),
                       "cells": {k: v for k, v in att["cells"].items()
                                 if k != "correct"}})
    out["robustness"] = robust
    out["elapsed_s"] = round(time.time() - t0, 1)

    o = Path(args.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "results.json").write_text(json.dumps(out, indent=2, default=list))
    (o / "report.md").write_text(_report_md(out))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("attribution",)}
                     | {"attribution_cells": attribution["cells"],
                        "h1_gold_path_only": attribution["h1_gold_path_only"]},
                     indent=2, default=str))


if __name__ == "__main__":
    main()
