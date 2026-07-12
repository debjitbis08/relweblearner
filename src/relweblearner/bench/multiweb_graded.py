"""Graded ensemble (docs/graded-ensemble-plan.md): two-timescale webs.

Thinking is graded: cross-web identity is a similarity field computed by
coupled propagation on the product of the webs (no votes, no translation),
and path reduction fires rules from either web at matched-similarity
strength. Knowledge stays discrete: identities harden into audited
commitments only where the coupled dynamics is unambiguous, and the forgery
arm checks that gradedness does not reintroduce the one-web failure mode.

Two arms:
  --arm graphlog   44 held-out worlds, same views/anchors as the discrete
                   run (joined comparator: results/multiweb-graphlog)
  --arm forgery    50 seeds of the multiweb world, soft region
                   correspondence with a mass floor (comparator: bench-multiweb)

Usage: relweb-multiweb-graded [--arm graphlog|forgery] [--out ...]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import multiweb as MW
from . import multiweb_graphlog as MG
from .graphlog import load_world

ROUNDS = 8            # coupled-propagation iterations
HARD_SIM = 0.5        # mutual-argmax floor for a committed identity
TOP_K = 8            # graded-reduction beam per span
ACT_MIN = 0.01        # activation floor per span entry
MASS_FLOOR = 0.15     # forgery arm: mean cross-mass per region member
DISCRETE_GRAPHLOG = Path("results/multiweb-graphlog/results.json")


# ---------------------------------------------------- coupled propagation

def _sinkhorn(S: np.ndarray, clamp: list[tuple[int, int]],
              beta: float = 1.0) -> np.ndarray:
    """Competitive normalisation with softassign sharpening (graduated
    assignment, Gold & Rangarajan 1996): raising beta over the rounds lets
    mutual matches saturate while contested pairs are suppressed — the
    sharpening is part of the coupled dynamics, not a post-hoc rescale."""
    if S.size == 0:
        return S
    S = (S / max(S.max(), 1e-12)) ** beta
    for i, j in clamp:
        S[i, :] = 0.0
        S[:, j] = 0.0
        S[i, j] = 1.0
    for _ in range(5):
        S = S / np.maximum(S.sum(1, keepdims=True), 1e-12)
        S = S / np.maximum(S.sum(0, keepdims=True), 1e-12)
    S = np.minimum(S / max(S.max(), 1e-12), 1.0)
    for i, j in clamp:
        S[i, :] = 0.0
        S[:, j] = 0.0
        S[i, j] = 1.0
    return S


def token_similarity(votes_a: dict, votes_b: dict,
                     anchors: dict) -> tuple[dict, dict, np.ndarray]:
    """The similarity field over token pairs: coupled propagation on the
    product of the two triangle webs. A pair's similarity is the propagated
    similarity of the company it keeps — the product of S over the other
    two positions of every co-positioned triangle pair, support-weighted."""
    ta, tb = MG._triples(votes_a), MG._triples(votes_b)
    toks_a = sorted({t for tr in ta for t in tr[:3]})
    toks_b = sorted({t for tr in tb for t in tr[:3]})
    ia = {t: i for i, t in enumerate(toks_a)}
    ib = {t: i for i, t in enumerate(toks_b)}
    A = np.array([[ia[a], ia[b], ia[c], n] for a, b, c, n in ta], dtype=np.int64)
    B = np.array([[ib[a], ib[b], ib[c], n] for a, b, c, n in tb], dtype=np.int64)
    clamp = [(ia[x], ib[y]) for x, y in anchors.items()
             if x in ia and y in ib]
    S = np.full((len(toks_a), len(toks_b)), 1.0 / max(len(toks_b), 1))
    S = _sinkhorn(S, clamp)
    others = {0: (1, 2), 1: (0, 2), 2: (0, 1)}
    for k in range(ROUNDS):
        raw = np.zeros_like(S)
        for pos, (o1, o2) in others.items():
            for a1, a2, a3, n in A:
                arow = (a1, a2, a3)
                w = np.minimum(n, B[:, 3]).astype(float)
                contrib = S[arow[o1], B[:, o1]] * S[arow[o2], B[:, o2]] * w
                np.add.at(raw[arow[pos]], B[:, pos], contrib)
        S = _sinkhorn(raw, clamp, beta=1.0 + (k + 1) / ROUNDS)
    return ia, ib, S


def hardened(ia: dict, ib: dict, S: np.ndarray,
             anchors: dict) -> dict[str, str]:
    """The projection layer's commitments: mutual argmax at S >= HARD_SIM.
    Anchors are commitments by construction."""
    ra = {i: t for t, i in ia.items()}
    rb = {j: t for t, j in ib.items()}
    m = dict(anchors)
    if S.size == 0:
        return m
    for i in range(S.shape[0]):
        j = int(S[i].argmax())
        if (S[i, j] >= HARD_SIM and int(S[:, j].argmax()) == i
                and ra[i] not in m and rb[j] not in m.values()):
            m[ra[i]] = rb[j]
    return m


# ---------------------------------------------------- graded reduction (CYK)

def _prune(acts: dict) -> dict:
    top = sorted(acts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_K]
    return {s: a for s, a in top if a >= ACT_MIN}


def graded_reduce(labels: tuple, rules: list, sim, _memo) -> dict:
    """All graded single-symbol reductions of a label sequence: rules from
    either web fire on any symbol pair at matched-similarity strength."""
    if labels in _memo:
        return _memo[labels]
    if len(labels) == 1:
        out = {labels[0]: 1.0}
    else:
        acts: dict = defaultdict(float)
        for i in range(1, len(labels)):
            left = graded_reduce(labels[:i], rules, sim, _memo)
            right = graded_reduce(labels[i:], rules, sim, _memo)
            for s1, a1 in left.items():
                for s2, a2 in right.items():
                    base = a1 * a2
                    if base < ACT_MIN:
                        continue
                    for p, q, h in rules:
                        w = sim(p, s1) * sim(q, s2)
                        if w > 0:
                            acts[h] = max(acts[h], base * w)
        out = _prune(dict(acts))
    _memo[labels] = out
    return out


def graded_predict(rec: dict, rules: list, sim, merge_of: dict,
                   majority: str, max_len: int = 5) -> str:
    """Path search u->v, graded reduction, activation summed across paths;
    committed identity classes aggregate before the argmax — the only place
    the hard layer touches thinking."""
    u0, v0, _ = rec["query"]
    out_idx: dict[int, list] = defaultdict(list)
    for u, v, rel in rec["edges"]:
        out_idx[u].append((v, rel))
    total: dict = defaultdict(float)
    memo: dict = {}
    stack = [(u0, ())]
    while stack:
        node, labels = stack.pop()
        if node == v0 and labels:
            for s, a in graded_reduce(labels, rules, sim, memo).items():
                total[merge_of.get(s, s)] += a
            continue
        if len(labels) >= max_len:
            continue
        for y, rel in out_idx[node]:
            stack.append((y, labels + (rel,)))
    if not total:
        return majority
    return max(total, key=lambda s: (total[s], s))


# ---------------------------------------------------------- GraphLog arm

def run_graphlog_world(name: str, n_train: int = 150, seed: int = 0) -> dict:
    w = load_world(name, n_train)
    labels = sorted({r for g in w["train"] + w["test"] for _u, _v, r in g["edges"]}
                    | {g["target"] for g in w["train"]}
                    | {g["query"][2] for g in w["test"]})
    views = MG.make_views(w["train"], labels, seed)
    votes_a = MG.triangle_votes(views["a"])
    votes_b = MG.triangle_votes(views["b"])
    anchors = MG.pick_anchors(w["train"], views, votes_a)

    ia, ib, S = token_similarity(votes_a, votes_b, anchors)
    commits = hardened(ia, ib, S, anchors)
    merge_of = {y: x for x, y in commits.items()}      # B symbol -> A symbol

    def sim(rule_tok: str, path_tok: str) -> float:
        if rule_tok == path_tok:
            return 1.0
        a, b = ((rule_tok, path_tok) if rule_tok in ia else
                (path_tok, rule_tok) if path_tok in ia else (None, None))
        if a is None or b not in ib:
            return 0.0
        return float(S[ia[a], ib[b]])

    rules = ([(p, q, h) for (p, q), h in MG._threshold(votes_a).items()]
             + [(p, q, h) for (p, q), h in MG._threshold(votes_b).items()])

    inv_a = {v: k for k, v in views["perm_a"].items()}
    inv_b = {v: k for k, v in views["perm_b"].items()}
    back = lambda t: inv_a.get(t, inv_b.get(t, t))
    prior_a = Counter(r for g in views["a"] for _u, _v, r in g["edges"])
    maj_a = max(prior_a, key=lambda r: (prior_a[r], r))

    hit = 0
    for rec in w["test"]:
        edges = []
        for u, v, r in rec["edges"]:
            if r not in views["hide_a"]:
                edges.append((u, v, views["perm_a"][r]))
            elif r not in views["hide_b"]:
                edges.append((u, v, views["perm_b"][r]))   # seam left in path
        got = graded_predict({"edges": edges, "query": rec["query"]},
                             rules, sim, merge_of, maj_a)
        hit += back(got) == rec["query"][2]

    true_map = {views["perm_a"][l]: views["perm_b"][l] for l in labels}
    new = {x: y for x, y in commits.items() if x not in anchors}
    wrong = [(x, y) for x, y in new.items() if true_map.get(x) != y]
    orphan = sum(1 for x, y in wrong
                 if inv_a[x] in views["hide_b"] or inv_b[y] in views["hide_a"])
    return {"world": name,
            "graded": round(hit / len(w["test"]), 4),
            "commits": {"n": len(new),
                        "precision": (sum(true_map.get(x) == y
                                          for x, y in new.items()) / len(new))
                                     if new else None,
                        "wrong_orphan": orphan,
                        "wrong_real": len(wrong) - orphan}}


def run_graphlog(out: Path) -> None:
    disc = {r["world"]: r for r in
            json.loads(DISCRETE_GRAPHLOG.read_text())["worlds"]}
    t0 = time.time()
    rows = []
    for name in MG.HELDOUT:
        r = run_graphlog_world(name)
        d = disc[name]
        r["discrete"] = d["accuracy"]["ensemble"]
        r["view_alone"] = d["accuracy"]["view-alone"]
        r["gold"] = d["accuracy"]["gold-pooled"]
        print(f"{name}: graded={r['graded']:.3f} discrete={r['discrete']:.3f} "
              f"gold={r['gold']:.3f} (commits {r['commits']['n']}, "
              f"{time.time() - t0:.0f}s)", flush=True)
        rows.append(r)
    g = [r["graded"] for r in rows]
    d = [r["discrete"] for r in rows]
    gold = [r["gold"] for r in rows]
    summary = {
        "arm": "graphlog", "worlds": len(rows),
        "elapsed_s": round(time.time() - t0, 1),
        "mean_graded": statistics.mean(g),
        "mean_discrete": statistics.mean(d),
        "mean_gold_pooled": statistics.mean(gold),
        "P-G1_graded_over_gold": statistics.mean(g) / statistics.mean(gold),
        "P-G2_worlds_improved": sum(x >= y for x, y in zip(g, d)) / len(rows),
        "P-G2_mean_improvement": statistics.mean(g) - statistics.mean(d),
        "P-G3_commit_precision": statistics.mean(
            [r["commits"]["precision"] for r in rows
             if r["commits"]["precision"] is not None]),
        "commit_wrong_orphan": sum(r["commits"]["wrong_orphan"] for r in rows),
        "commit_wrong_real": sum(r["commits"]["wrong_real"] for r in rows),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "graphlog.json").write_text(json.dumps(
        {"summary": summary, "worlds": rows}, indent=1))
    print(json.dumps(summary, indent=2))


# ---------------------------------------------------------- forgery arm

def node_similarity(GA, GB, anchors: dict) -> tuple[dict, dict, np.ndarray]:
    """Coupled diffusion M ~ W_A S W_B^T, anchors clamped. Two quantities
    live here and must not be conflated (bring-up finding, plan §4b):
    the BALANCED field S drives the iteration's competition, but Sinkhorn
    balancing forces every node — forged ones included — to place mass ~1
    somewhere, and sharpening then concentrates it: competitive
    normalisation manufactures confidence out of crumbs (the hallucination
    mechanism in miniature). What is returned is therefore the ABSOLUTE
    propagated mass M of the final round, self-calibrated so an anchored
    node's row mass is ~1: evidence that cannot be invented by
    normalisation. Adjacencies are globally scaled (one scalar per web) so
    weak attachments propagate weakly."""
    na, nb = sorted(GA.nodes), sorted(GB.nodes)
    ia = {t: i for i, t in enumerate(na)}
    ib = {t: i for i, t in enumerate(nb)}

    def norm_adj(G, idx):
        W = np.zeros((len(idx), len(idx)))
        for u, v, d in G.edges(data=True):
            W[idx[u], idx[v]] = W[idx[v], idx[u]] = d["weight"]
        # identity evidence rides only the structural backbone — the same
        # EXT_BACKBONE rule the discrete bench pre-registered. Without it,
        # weight-1 noise/attachment edges feed unanchored islands and the
        # annealing loop confabulates a consistent placement for them.
        med = np.median(W[W > 0]) if (W > 0).any() else 0.0
        W[W < 0.5 * med] = 0.0
        return W / max(W.sum(1).max(), 1e-12)      # global scale, not per-row

    WA, WB = norm_adj(GA, ia), norm_adj(GB, ib)
    clamp = [(ia[x], ib[y]) for x, y in anchors.items()
             if x in ia and y in ib]
    # zero-init, anchors only: cross-web identity mass can ONLY flow outward
    # from co-witnessed events. A uniform init is a confabulation seed — it
    # hands every unanchored island mass that the annealing loop then
    # sharpens into a consistent, wholly invented placement (bring-up seeds
    # 1000/1004).
    S = np.zeros((len(na), len(nb)))
    S = _sinkhorn(S, clamp)
    M = S
    for k in range(ROUNDS):
        M = WA @ S @ WB.T
        for i, j in clamp:
            M[i, :] = 0.0
            M[:, j] = 0.0
            M[i, j] = 1.0
        S = _sinkhorn(M.copy(), clamp, beta=1.0 + (k + 1) / ROUNDS)
    if clamp:
        scale = float(np.median([M[i].sum() for i, _j in clamp]))
        M = M / max(scale, 1e-12)
    return ia, ib, M


def soft_correspondence(region: frozenset, ia: dict, ib: dict, M: np.ndarray,
                        regions_other: list[frozenset]) -> float:
    """Concentration of the region's ABSOLUTE evidence mass in one stable
    region of the other web, gated by the mass floor (in anchored-node
    units): crumbs cannot corroborate however concentrated they are."""
    idx = [ia[n] for n in region if n in ia]
    if not idx:
        return 0.0
    mass = float(M[idx].sum())
    # the TYPICAL member must carry evidence: a region whose mass lives in
    # two absorbed anchored nodes is not corroborated AS a region (bring-up
    # seed 1000: the forged region swallowed real anchored members and their
    # mass alone cleared a mean-based floor).
    member_mass = M[idx].sum(axis=1)
    if float(np.median(member_mass)) < MASS_FLOOR or len(idx) < len(region) / 2:
        return 0.0
    best = 0.0
    for rb in regions_other:
        cols = [ib[n] for n in rb if n in ib]
        if cols:
            best = max(best, float(M[np.ix_(idx, cols)].sum()) / mass)
    return best


def run_forgery_seed(seed: int) -> dict:
    world = MW.generate(seed)
    regions = [MW.stable_regions(w, seed * 31 + k)
               for k, w in enumerate(world.webs)]
    fields = {}
    for (i, j), anch in world.anchors.items():
        fields[(i, j)] = node_similarity(world.webs[i], world.webs[j], anch)
        fields[(j, i)] = node_similarity(world.webs[j], world.webs[i],
                                         {v: u for u, v in anch.items()})
    rows = []
    for i, regs in enumerate(regions):
        for r in regs:
            scores = {}
            for j in range(len(regions)):
                if j == i:
                    continue
                ia, ib, S = fields[(i, j)]
                scores[j] = soft_correspondence(r, ia, ib, S, regions[j])
            corr = sum(1 for s in scores.values() if s >= MW.CORR_THETA)
            rows.append({"view": i, "region": r, "scores": scores,
                         "concept": corr >= 1})

    com_of = {e: c for c, com in enumerate(world.communities) for e in com}

    def majority_com(row):
        votes = Counter(com_of.get(world.hidden[row["view"]].get(n))
                        for n in row["region"])
        return votes.most_common(1)[0][0]

    forged_rows = [r for r in rows if r["view"] == 0
                   and len(r["region"] & world.forged) >= MW.FORGE_N // 2]
    concepts = [r for r in rows if r["concept"]]
    multi = {c for c in range(MW.N_COM) if len(world.covered[c]) >= 2}
    recovered = {majority_com(r) for r in concepts} & multi
    purities = []
    for r in concepts:
        votes = Counter(com_of.get(world.hidden[r["view"]].get(n))
                        for n in r["region"])
        top = max((k for c, k in votes.items() if c is not None), default=0)
        purities.append(top / len(r["region"]))
    solo_rows = [r for r in rows if r["view"] == 0
                 and not r["region"] & world.forged
                 and majority_com(r) == MW.SOLO_COM]
    return {"seed": seed,
            "forged_stable": bool(forged_rows),
            "forged_concept": any(r["concept"] for r in forged_rows),
            "recall": len(recovered) / len(multi) if multi else None,
            "purity": statistics.mean(purities) if purities else None,
            "solo_projected": any(r["concept"] for r in solo_rows)}


def run_forgery(out: Path, seeds: list[int]) -> None:
    t0 = time.time()
    rows = [run_forgery_seed(s) for s in seeds]
    n = len(rows)
    summary = {
        "arm": "forgery", "seeds": n, "elapsed_s": round(time.time() - t0, 1),
        "forged_stable_rate": sum(r["forged_stable"] for r in rows) / n,
        "P-G4_forgery_excluded": 1 - sum(r["forged_concept"] for r in rows) / n,
        "P-G5_recall": statistics.mean([r["recall"] for r in rows
                                        if r["recall"] is not None]),
        "P-G5_purity": statistics.mean([r["purity"] for r in rows
                                        if r["purity"] is not None]),
        "P-G5_solo_provisional": 1 - sum(r["solo_projected"] for r in rows) / n,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "forgery.json").write_text(json.dumps(
        {"summary": summary, "per_seed": rows}, indent=1, default=list))
    print(json.dumps(summary, indent=2))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=["graphlog", "forgery"], required=True)
    ap.add_argument("--worlds", default=None, help="graphlog arm world override")
    ap.add_argument("--seeds", default=None, help="forgery arm seeds, e.g. 0-49")
    ap.add_argument("--out", default="results/graded-ensemble")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if args.arm == "graphlog":
        if args.worlds:                        # dev bring-up path
            for name in args.worlds.split(","):
                print(json.dumps(run_graphlog_world(name.strip()), indent=1))
        else:
            run_graphlog(out)
    else:
        lo, hi = (args.seeds or "0-49").split("-")
        run_forgery(out, list(range(int(lo), int(hi) + 1)))


if __name__ == "__main__":
    main()
