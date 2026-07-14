"""The rule_20 diagnosis (E5) — why does soft coupling tear?

Pre-registration: docs/rule20-diagnosis-plan.md (committed before this code).
A DIAGNOSIS, not a bench. The frozen machinery (graphlog, multiweb_graphlog,
multiweb_graded) is reused unchanged; probe variants pass their own values as
arguments, no frozen constant is modified. The consistency gate refuses to
attribute anything until the frozen discrete triple AND the frozen graded
accuracy reproduce exactly, and until this module's parameterized copy of the
graded predictor is prediction-identical to the frozen one on every episode.

Plan §6b checklist — each row implemented by the named function:
  gate() flip_table() winner_trace() probe_commits() probe_identity_sim()
  probe_aggregation() probe_beam() robust_seeds() companion_rule27() audit()

Probes are diagnostic counterfactuals (evaluation-side gold where needed),
never system capabilities.

Usage:  relweb-rule20-diag [--out results/rule20-diagnosis]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from . import multiweb_graded as GR
from . import multiweb_graphlog as MG
from .graphlog import load_world
from .rule27_diag import _predict

WORLD = "rule_20"
FROZEN = {
    "rule_20": {"view-alone": 0.358, "ensemble": 0.659, "gold-pooled": 0.752,
                "graded": 0.317},
    "rule_27": {"view-alone": 0.133, "ensemble": 0.163, "gold-pooled": 0.828,
                "graded": 0.163},
}


# ------------------------------------------------------------------ the setup

def setup(world: str, seed: int = 0, n_train: int = 150) -> dict:
    """Both pipelines' internals, exactly as frozen (MG.run_world and
    GR.run_graphlog_world, same call order, same seed)."""
    w = load_world(world, n_train)
    labels = sorted({r for g in w["train"] + w["test"] for _u, _v, r in g["edges"]}
                    | {g["target"] for g in w["train"]}
                    | {g["query"][2] for g in w["test"]})
    views = MG.make_views(w["train"], labels, seed)
    votes_a = MG.triangle_votes(views["a"])
    votes_b = MG.triangle_votes(views["b"])
    anchors = MG.pick_anchors(w["train"], views, votes_a)

    # discrete side
    mapping = MG.extend_mapping(votes_a, votes_b, anchors)
    rules_alone = MG._threshold(votes_a)
    rules_b = MG._threshold(votes_b)
    rules_ens = MG.project(votes_a, votes_b, mapping)
    rules_gold = MG._threshold(MG.triangle_votes(w["train"]))

    # graded side
    ia, ib, S = GR.token_similarity(votes_a, votes_b, anchors)
    commits = GR.hardened(ia, ib, S, anchors)
    merge_of = {y: x for x, y in commits.items()}
    rules_g = ([(p, q, h) for (p, q), h in rules_alone.items()]
               + [(p, q, h) for (p, q), h in rules_b.items()])
    a_rules = {(p, q, h) for (p, q), h in rules_alone.items()}

    inv_a = {v: k for k, v in views["perm_a"].items()}
    inv_b = {v: k for k, v in views["perm_b"].items()}
    prior_a = Counter(r for g in views["a"] for _u, _v, r in g["edges"])
    maj_a = max(prior_a, key=lambda r: (prior_a[r], r))
    true_map = {views["perm_a"][l]: views["perm_b"][l] for l in labels}
    wrong_commits = {(x, y) for x, y in commits.items()
                     if x not in anchors and true_map.get(x) != y}

    def sim(rule_tok: str, path_tok: str) -> float:
        if rule_tok == path_tok:
            return 1.0
        a, b = ((rule_tok, path_tok) if rule_tok in ia else
                (path_tok, rule_tok) if path_tok in ia else (None, None))
        if a is None or b not in ib:
            return 0.0
        return float(S[ia[a], ib[b]])

    return {"world": world, "w": w, "views": views, "anchors": anchors,
            "mapping": mapping, "rules_alone": rules_alone,
            "rules_ens": rules_ens, "rules_gold": rules_gold,
            "rules_g": rules_g, "a_rules": a_rules,
            "commits": commits, "merge_of": merge_of,
            "wrong_commits": wrong_commits, "sim": sim,
            "inv_a": inv_a, "inv_b": inv_b, "maj_a": maj_a,
            "back": lambda t: inv_a.get(t, inv_b.get(t, t)),
            "targets": [rec["query"][2] for rec in w["test"]]}


def _graded_edges(ctx: dict, rec: dict) -> list:
    """GR.run_graphlog_world's test rendering, verbatim (seam left in path)."""
    v = ctx["views"]
    edges = []
    for u, vv, r in rec["edges"]:
        if r not in v["hide_a"]:
            edges.append((u, vv, v["perm_a"][r]))
        elif r not in v["hide_b"]:
            edges.append((u, vv, v["perm_b"][r]))
    return edges


# --------------------------------------- parameterized graded reduce / predict

def _prune_p(acts: dict, top_k: int, act_min: float) -> dict:
    top = sorted(acts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
    return {s: a for s, a in top if a >= act_min}


def _greduce(labels, rules, sim, memo, meta, top_k, act_min,
             is_correct=None, prune_log=None):
    """GR.graded_reduce, verbatim semantics, with parameterized prune and
    optional provenance: meta[labels][sym] = (bridged_any, top_app) where
    top_app = (p, q, h, w1, w2) of the max-setting application."""
    if labels in memo:
        return memo[labels]
    if len(labels) == 1:
        out = {labels[0]: 1.0}
        if meta is not None:
            meta[labels] = {labels[0]: (False, None)}
    else:
        acts: dict = defaultdict(float)
        m_here: dict = {}
        for i in range(1, len(labels)):
            left = _greduce(labels[:i], rules, sim, memo, meta, top_k, act_min,
                            is_correct, prune_log)
            right = _greduce(labels[i:], rules, sim, memo, meta, top_k, act_min,
                             is_correct, prune_log)
            for s1, a1 in left.items():
                for s2, a2 in right.items():
                    base = a1 * a2
                    if base < act_min:
                        continue
                    for p, q, h in rules:
                        w1, w2 = sim(p, s1), sim(q, s2)
                        w = w1 * w2
                        if w > 0:
                            val = base * w
                            if val > acts[h]:
                                acts[h] = val
                                if meta is not None:
                                    br = (w < 1.0
                                          or meta[labels[:i]][s1][0]
                                          or meta[labels[i:]][s2][0])
                                    m_here[h] = (br, (p, q, h, w1, w2))
        pruned = _prune_p(dict(acts), top_k, act_min)
        if prune_log is not None and is_correct is not None:
            if any(is_correct(s) for s in acts if s not in pruned):
                prune_log["starved"] = True
        out = pruned
        if meta is not None:
            meta[labels] = {s: m_here.get(s, (False, None)) for s in out}
    memo[labels] = out
    return out


def _gpredict(ctx, rec, rules, sim, merge_of, agg="sum",
              top_k=GR.TOP_K, act_min=GR.ACT_MIN, trace=False, edges=None):
    """GR.graded_predict, verbatim semantics, parameterized on aggregation
    and beam, with optional winner-provenance trace. `edges` overrides the
    default graded rendering (used by the factorial's rendering factor)."""
    if edges is None:
        edges = _graded_edges(ctx, rec)
    u0, v0, _ = rec["query"]
    target = rec["query"][2]
    back = ctx["back"]
    is_correct = lambda s: back(merge_of.get(s, s)) == target
    out_idx: dict[int, list] = defaultdict(list)
    for u, vv, rel in edges:
        out_idx[u].append((vv, rel))
    total: dict = defaultdict(float)
    memo: dict = {}
    meta: dict | None = {} if trace else None
    prune_log: dict = {}
    contrib: dict = defaultdict(lambda: defaultdict(float))   # merged -> src -> mass
    best_src: dict = {}                                       # merged -> (a, src, span_meta)
    paths_of: Counter = Counter()
    stack = [(u0, ())]
    while stack:
        node, labs = stack.pop()
        if node == v0 and labs:
            red = _greduce(labs, rules, sim, memo, meta, top_k, act_min,
                           is_correct if trace else None,
                           prune_log if trace else None)
            for s, a in red.items():
                m = merge_of.get(s, s)
                if agg == "sum":
                    total[m] += a
                elif agg == "max":
                    total[m] = max(total[m], a)
                elif agg == "count":
                    total[m] += 1
                if trace:
                    contrib[m][s] += a
                    paths_of[m] += 1
                    if m not in best_src or a > best_src[m][0]:
                        best_src[m] = (a, s, meta[labs][s])
            continue
        if len(labs) >= 5:
            continue
        for y, rel in out_idx[node]:
            stack.append((y, labs + (rel,)))
    if not total:
        got = ctx["maj_a"]
        return (got, None) if trace else got
    got = max(total, key=lambda s: (total[s], s))
    if not trace:
        return got
    winner_m = got
    correct_mass = sum(a for m, a in total.items() if back(m) == target)
    a_star, src, (bridged, app) = best_src[winner_m]
    origin = ("A" if app and (app[0], app[1], app[2]) in ctx["a_rules"] else
              "B" if app else "leaf")
    pooled_srcs = [s for s in contrib[winner_m] if s != winner_m]
    tr = {"winner": back(winner_m), "winner_mass": round(total[winner_m], 4),
          "correct_mass": round(correct_mass, 4),
          "paths_winner": paths_of[winner_m],
          "paths_correct": sum(n for m, n in paths_of.items() if back(m) == target),
          "top_app_origin": origin,
          "top_app_factors": ([round(app[3], 3), round(app[4], 3)] if app else None),
          "cross_fired": bool(bridged),
          "commit_pooled": bool(pooled_srcs),
          "wrong_commit_involved": any((winner_m, s) in ctx["wrong_commits"]
                                       for s in pooled_srcs),
          "beam_starved": prune_log.get("starved", False)}
    tr["sum_outvoted"] = not tr["cross_fired"] and not tr["commit_pooled"]
    return got, tr


# ----------------------------------------------------------- gate and helpers

def _discrete_preds(ctx, rules, mode) -> list:
    v, back = ctx["views"], ctx["back"]
    inv_map = {y: x for x, y in ctx["mapping"].items()}
    out = []
    for rec in ctx["w"]["test"]:
        if mode == "gold":
            out.append(_predict(rec["edges"], rec, rules, back(ctx["maj_a"])))
        else:
            r = MG._render_test(rec, v, inv_map, ensemble=(mode == "ensemble"))
            out.append(back(_predict(r["edges"], rec, rules, ctx["maj_a"])))
    return out


def _graded_frozen_preds(ctx) -> list:
    return [ctx["back"](GR.graded_predict(
                {"edges": _graded_edges(ctx, rec), "query": rec["query"]},
                ctx["rules_g"], ctx["sim"], ctx["merge_of"], ctx["maj_a"]))
            for rec in ctx["w"]["test"]]


def _acc(preds, targets):
    return sum(p == t for p, t in zip(preds, targets)) / len(targets)


def gate(ctx: dict) -> dict:
    """Plan §6b row 1: frozen discrete triple + frozen graded accuracy must
    reproduce, and the diag copy must be prediction-identical to frozen GR."""
    t = ctx["targets"]
    rec = {"view-alone": round(_acc(_discrete_preds(ctx, ctx["rules_alone"], "alone"), t), 3),
           "ensemble": round(_acc(_discrete_preds(ctx, ctx["rules_ens"], "ensemble"), t), 3),
           "gold-pooled": round(_acc(_discrete_preds(ctx, ctx["rules_gold"], "gold"), t), 3)}
    frozen_g = _graded_frozen_preds(ctx)
    rec["graded"] = round(_acc(frozen_g, t), 3)
    copy_g = [ctx["back"](_gpredict(ctx, r, ctx["rules_g"], ctx["sim"],
                                    ctx["merge_of"]))
              for r in ctx["w"]["test"]]
    frozen = FROZEN[ctx["world"]]
    return {"frozen": frozen, "recomputed": rec,
            "diag_copy_identical": copy_g == frozen_g,
            "pass": rec == frozen and copy_g == frozen_g,
            "_graded_preds": frozen_g}


def audit(base_preds, alt_preds, targets) -> dict:
    """Plan §4b/§6b row 10: heal/break episode sets vs the graded baseline.
    The FULL sets are stored (the first frozen run truncated them to 20 —
    referee finding 3.3; results.json is left frozen, episode-sets.json and
    factorial.json carry the complete lists)."""
    heal = [i for i, t in enumerate(targets)
            if base_preds[i] != t and alt_preds[i] == t]
    brk = [i for i, t in enumerate(targets)
           if base_preds[i] == t and alt_preds[i] != t]
    return {"acc": round(_acc(alt_preds, targets), 4),
            "heals": len(heal), "breaks": len(brk),
            "healed_idx": heal, "broken_idx": brk}


# ------------------------------------------------------------- §4a flip table

def flip_table(ctx: dict, graded_preds: list) -> dict:
    disc = _discrete_preds(ctx, ctx["rules_ens"], "ensemble")
    t = ctx["targets"]
    cats = Counter()
    torn, healed = [], []
    for i in range(len(t)):
        d, g = disc[i] == t[i], graded_preds[i] == t[i]
        cats["both_right" if d and g else "torn" if d else
             "healed" if g else "both_wrong"] += 1
        if d and not g:
            torn.append(i)
        if g and not d:
            healed.append(i)
    return {"cells": dict(cats), "torn_idx": torn, "healed_idx": healed,
            "discrete_acc": round(_acc(disc, t), 4),
            "graded_acc": round(_acc(graded_preds, t), 4)}


def winner_trace(ctx: dict, torn_idx: list) -> dict:
    """Plan §6b row 3: per torn episode, the winning wrong label's
    provenance and the four marks. Marks are MARKERS, not causal shares —
    the probes are the causal reading (plan §6a)."""
    marks = Counter()
    records = []
    for i in torn_idx:
        rec = ctx["w"]["test"][i]
        _got, tr = _gpredict(ctx, rec, ctx["rules_g"], ctx["sim"],
                             ctx["merge_of"], trace=True)
        if tr is None:
            marks["fallback_empty"] += 1
            continue
        for k in ("cross_fired", "commit_pooled", "wrong_commit_involved",
                  "beam_starved", "sum_outvoted"):
            if tr[k]:
                marks[k] += 1
        records.append({"i": i, **tr})
    return {"n_torn": len(torn_idx), "marks": dict(marks),
            "episodes": records}


# ------------------------------------------------------------------ §4b probes

def probe_commits(ctx: dict, base: list) -> dict:
    t = ctx["targets"]
    m_nowrong = {y: x for x, y in ctx["commits"].items()
                 if (x, y) not in ctx["wrong_commits"]}
    m_anchors = {y: x for x, y in ctx["anchors"].items()}
    out = {}
    for name, m in (("minus_wrong_commits", m_nowrong),
                    ("anchors_only", m_anchors)):
        preds = [ctx["back"](_gpredict(ctx, r, ctx["rules_g"], ctx["sim"], m))
                 for r in ctx["w"]["test"]]
        out[name] = audit(base, preds, t)
    out["n_wrong_commits"] = len(ctx["wrong_commits"])
    return out


def probe_identity_sim(ctx: dict, base: list) -> dict:
    ident = lambda a, b: 1.0 if a == b else 0.0
    preds = [ctx["back"](_gpredict(ctx, r, ctx["rules_g"], ident,
                                   ctx["merge_of"]))
             for r in ctx["w"]["test"]]
    return audit(base, preds, ctx["targets"])


def probe_aggregation(ctx: dict, base: list) -> dict:
    out = {}
    for agg in ("max", "count"):
        preds = [ctx["back"](_gpredict(ctx, r, ctx["rules_g"], ctx["sim"],
                                       ctx["merge_of"], agg=agg))
                 for r in ctx["w"]["test"]]
        out[agg] = audit(base, preds, ctx["targets"])
    return out


def probe_beam(ctx: dict, base: list) -> dict:
    out = {}
    for name, tk, am in (("top_k_16", 16, GR.ACT_MIN),
                         ("top_k_32", 32, GR.ACT_MIN),
                         ("act_min_0.001", GR.TOP_K, 0.001),
                         ("act_min_0", GR.TOP_K, 0.0)):
        preds = [ctx["back"](_gpredict(ctx, r, ctx["rules_g"], ctx["sim"],
                                       ctx["merge_of"], top_k=tk, act_min=am))
                 for r in ctx["w"]["test"]]
        out[name] = audit(base, preds, ctx["targets"])
    return out


# ------------------------------- factorial exactification (post-referee 3.1/3.2)
# The E5 referee (findings 3.1 and 3.2) required the supplementary
# exactification cells to be (a) committed as a reproducer and (b) analyzed
# as a genuine factorial with interactions, not a single ladder order. Four
# binary factors, each replacing one graded operational choice with its
# discrete counterpart:
#   R  rules:      native both-web rules      -> translated rules_ens
#   D  rendering:  seam left in B tokens      -> inv_map-translated rendering
#   S  similarity: frozen soft field          -> exact identity indicator
#   C  commits:    full hardened merge_of     -> the 2 wrong commits removed
# The beam is NOT a factor: measured inert at both extremes in the frozen
# run and re-checked here as two extra recorded cells.

FACTORS = ("R", "D", "S", "C")


def factorial(ctx: dict, base: list) -> dict:
    """All 2^4 cells, each with full heal/break sets vs the frozen graded
    baseline, plus prediction-identity counts against the frozen graded,
    discrete-ensemble, and view-alone prediction vectors, plus Shapley
    values over accuracy (the order-independent allocation the referee
    asked for) and the full main-effect/interaction table."""
    t = ctx["targets"]
    inv_map = {y: x for x, y in ctx["mapping"].items()}
    rules_trans = [(p, q, h) for (p, q), h in ctx["rules_ens"].items()]
    ident = lambda a, b: 1.0 if a == b else 0.0
    m_minus = {y: x for x, y in ctx["commits"].items()
               if (x, y) not in ctx["wrong_commits"]}
    disc = _discrete_preds(ctx, ctx["rules_ens"], "ensemble")
    alone = _discrete_preds(ctx, ctx["rules_alone"], "alone")

    def cell_preds(on: frozenset) -> list:
        rules = rules_trans if "R" in on else ctx["rules_g"]
        sim = ident if "S" in on else ctx["sim"]
        merge = m_minus if "C" in on else ctx["merge_of"]
        preds = []
        for rec in ctx["w"]["test"]:
            edges = (MG._render_test(rec, ctx["views"], inv_map,
                                     ensemble=True)["edges"]
                     if "D" in on else None)
            preds.append(ctx["back"](_gpredict(ctx, rec, rules, sim, merge,
                                               edges=edges)))
        return preds

    cells, acc = {}, {}
    for bits in range(16):
        on = frozenset(f for i, f in enumerate(FACTORS) if bits >> i & 1)
        key = "+".join(sorted(on)) or "none"
        preds = cell_preds(on)
        a = audit(base, preds, t)
        a["identical_to_frozen_graded"] = sum(p == b for p, b in zip(preds, base))
        a["identical_to_discrete_ens"] = sum(p == d for p, d in zip(preds, disc))
        a["identical_to_view_alone"] = sum(p == v for p, v in zip(preds, alone))
        cells[key] = a
        acc[on] = a["acc"]

    # Shapley values over the 4 factors (v = cell accuracy)
    from itertools import permutations
    shap = {f: 0.0 for f in FACTORS}
    perms = list(permutations(FACTORS))
    for order in perms:
        cur: frozenset = frozenset()
        for f in order:
            nxt = cur | {f}
            shap[f] += (acc[nxt] - acc[cur]) / len(perms)
            cur = nxt
    # 2x2 summary the referee computed, kept explicit: E = R+D+S jointly
    e_full = frozenset("RDS")
    two_by_two = {
        "commits_marginal_at_frozen": round(acc[frozenset("C")] - acc[frozenset()], 4),
        "commits_marginal_after_exactification":
            round(acc[e_full | {"C"}] - acc[e_full], 4),
        "exactification_marginal_with_commits":
            round(acc[e_full] - acc[frozenset()], 4),
        "exactification_marginal_without_commits":
            round(acc[e_full | {"C"}] - acc[frozenset("C")], 4),
        "interaction": round((acc[e_full | {"C"}] - acc[e_full])
                             - (acc[frozenset("C")] - acc[frozenset()]), 4)}

    # the beam, re-checked as recorded cells (not a factor: inert)
    beam_cells = {}
    for name, tk, am in (("frozen+no_beam", 10**6, 0.0),
                         ("exactified+no_beam", 10**6, 0.0)):
        on = frozenset() if name.startswith("frozen") else frozenset("RDSC")
        rules = rules_trans if "R" in on else ctx["rules_g"]
        sim = ident if "S" in on else ctx["sim"]
        merge = m_minus if "C" in on else ctx["merge_of"]
        preds = []
        for rec in ctx["w"]["test"]:
            edges = (MG._render_test(rec, ctx["views"], inv_map,
                                     ensemble=True)["edges"]
                     if "D" in on else None)
            preds.append(ctx["back"](_gpredict(ctx, rec, rules, sim, merge,
                                               top_k=tk, act_min=am,
                                               edges=edges)))
        ref = base if "R" not in on else None
        beam_cells[name] = {"acc": round(_acc(preds, t), 4),
                            "identical_to_beam_on":
                                sum(p == q for p, q in zip(
                                    preds, cell_preds(on)))}

    return {"factors": {"R": "rules translated (rules_ens)",
                        "D": "rendering translated (inv_map seam)",
                        "S": "similarity exact-identity",
                        "C": "2 wrong hardened commits removed"},
            "cells": cells,
            "shapley_over_accuracy": {f: round(v, 4) for f, v in shap.items()},
            "two_by_two": two_by_two,
            "beam_recheck": beam_cells}


def preregistered_full_sets(ctx: dict, base: list) -> dict:
    """Referee 3.3: the pre-registered probes re-run with COMPLETE heal/break
    episode sets (results.json is frozen with the truncated lists; this
    artifact carries the full ones — deterministic regeneration)."""
    return {"p_commits": probe_commits(ctx, base),
            "p_ident": probe_identity_sim(ctx, base),
            "p_agg": probe_aggregation(ctx, base),
            "p_beam": probe_beam(ctx, base)}


# ------------------------------------------------- §4c / §4d secondary cells

def robust_seeds(world: str, n: int = 4) -> list:
    out = []
    for s in range(1, n + 1):
        c = setup(world, seed=s)
        g = _graded_frozen_preds(c)
        ft = flip_table(c, g)
        out.append({"seed": s, "discrete_acc": ft["discrete_acc"],
                    "graded_acc": ft["graded_acc"], "cells": ft["cells"]})
    return out


def companion_rule27() -> dict:
    """Plan §4d: the same flip table + winner trace on rule_27 seed 0 —
    closes E6's open graded-mechanism residual."""
    c = setup("rule_27", seed=0)
    g = gate(c)
    if not g["pass"]:
        return {"gate": {k: v for k, v in g.items() if k != "_graded_preds"},
                "error": "companion gate failed"}
    ft = flip_table(c, g["_graded_preds"])
    wt = winner_trace(c, ft["torn_idx"])
    return {"gate": {k: v for k, v in g.items() if k != "_graded_preds"},
            "flip": {k: v for k, v in ft.items()
                     if k not in ("torn_idx", "healed_idx")},
            "trace_marks": wt["marks"], "n_torn": wt["n_torn"]}


# ------------------------------------------------------------------ reporting

def _report_md(out: dict) -> str:
    g = out["gate"]
    ft, wt = out["flip"], out["trace"]
    lines = [
        "# The rule_20 diagnosis (E5) — flip table, winner trace, probes", "",
        "Pre-registered: docs/rule20-diagnosis-plan.md (committed before this "
        "code; §6b checklist implemented in full). Probes are diagnostic "
        "counterfactuals — NOT system capabilities. Trace marks are MARKERS; "
        "the heal/break probes are the causal reading.", "",
        f"Consistency gate: recomputed {g['recomputed']} vs frozen "
        f"{g['frozen']}; diag copy prediction-identical: "
        f"{g['diag_copy_identical']} — {'PASS' if g['pass'] else 'FAIL'}.", "",
        "## §4a Flip table (seed 0, paired per episode)", "",
        f"```json\n{json.dumps(ft['cells'], indent=1)}\n```", "",
        f"## §4a Winner trace over {wt['n_torn']} torn episodes (marks)", "",
        f"```json\n{json.dumps(wt['marks'], indent=1)}\n```", "",
        "## §4b Probes (each vs the frozen graded baseline; heal/break sets)", "",
        "### P-commits (H2)", "",
        f"```json\n{json.dumps(out['p_commits'], indent=1)}\n```", "",
        "### P-ident (H1)", "",
        f"```json\n{json.dumps(out['p_ident'], indent=1)}\n```", "",
        "### P-sum (H3)", "",
        f"```json\n{json.dumps(out['p_agg'], indent=1)}\n```", "",
        "### P-beam (H4, bounded — can support, never exclude)", "",
        f"```json\n{json.dumps(out['p_beam'], indent=1)}\n```", "",
        "## §4c Robustness (seeds 1–4)", "",
        f"```json\n{json.dumps(out['robust'], indent=1)}\n```", "",
        "## §4d rule_27 companion (closes E6's open residual)", "",
        f"```json\n{json.dumps(out['companion'], indent=1)}\n```", ""]
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exactify", action="store_true",
                    help="run ONLY the post-referee factorial exactification "
                         "(2^4 cells, Shapley, full episode sets) and the "
                         "pre-registered probes with complete heal/break "
                         "lists; writes factorial.json + episode-sets.json, "
                         "leaves the frozen outputs untouched")
    ap.add_argument("--out", default="results/rule20-diagnosis")
    args = ap.parse_args(argv)

    if args.exactify:
        ctx = setup(WORLD, seed=0)
        g = gate(ctx)
        if not g["pass"]:
            raise SystemExit("consistency gate FAILED")
        base = g["_graded_preds"]
        o = Path(args.out)
        o.mkdir(parents=True, exist_ok=True)
        fact = factorial(ctx, base)
        (o / "factorial.json").write_text(json.dumps(fact, indent=2))
        (o / "episode-sets.json").write_text(json.dumps(
            preregistered_full_sets(ctx, base), indent=2))
        slim = {k: (v if k != "cells" else
                    {c: {kk: vv for kk, vv in a.items()
                         if kk not in ("healed_idx", "broken_idx")}
                     for c, a in v.items()})
                for k, v in fact.items()}
        print(json.dumps(slim, indent=2))
        return

    t0 = time.time()
    ctx = setup(WORLD, seed=0)
    g = gate(ctx)
    if not g["pass"]:
        print(json.dumps({k: v for k, v in g.items() if k != "_graded_preds"},
                         indent=2))
        raise SystemExit("consistency gate FAILED — attribution would be "
                         "about the wrong system")
    base = g["_graded_preds"]

    ft = flip_table(ctx, base)
    wt = winner_trace(ctx, ft["torn_idx"])
    out = {"world": WORLD,
           "gate": {k: v for k, v in g.items() if k != "_graded_preds"},
           "flip": {k: v for k, v in ft.items() if k != "healed_idx"},
           "trace": wt,
           "p_commits": probe_commits(ctx, base),
           "p_ident": probe_identity_sim(ctx, base),
           "p_agg": probe_aggregation(ctx, base),
           "p_beam": probe_beam(ctx, base),
           "robust": robust_seeds(WORLD),
           "companion": companion_rule27()}
    out["elapsed_s"] = round(time.time() - t0, 1)

    o = Path(args.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "results.json").write_text(json.dumps(out, indent=2, default=list))
    out_slim = dict(out)
    out_slim["flip"] = {k: v for k, v in out["flip"].items() if k != "torn_idx"}
    out_slim["trace"] = {"n_torn": wt["n_torn"], "marks": wt["marks"]}
    (o / "report.md").write_text(_report_md(out))
    print(json.dumps(out_slim, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
