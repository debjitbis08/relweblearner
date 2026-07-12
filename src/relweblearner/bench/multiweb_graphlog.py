"""Multi-web GraphLog (docs/multiweb-graphlog-plan.md, incl. §2b amendment).

The core-thesis test on external data: two views read every training episode
of a GraphLog world, each blind to its own 15% of relation types and each
through its own opaque vocabulary. Each mines its own composition web; a
partial correspondence is discovered (6 curiosity-placed co-witnessed edges
as anchors + structural extension by triangle interference); B's evidence is
projected through the mapping — including imported vocabulary for relations
A cannot perceive — and queries are answered by CYK path reduction over the
projected invariants.

Knowledge = the rule structure the webs agree on THROUGH the discovered
mapping. Thinking = composing transformations along paths and reducing them
with those invariants. The old single-web structure's wall on this data
(frozen-Z transport, mean 0.134) is the joined reference.

Usage: relweb-multiweb-graphlog [--worlds ...] [--out results/multiweb-graphlog]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from .graphlog import load_world, cyk_predict

HIDE_FRAC = 0.15      # relation types each view is blind to (disjoint sets)
ANCHOR_BUDGET = 6     # co-witnessed single edges
MIN_SUPPORT = 2       # identical floors to graphlog.mine_rules
MIN_CONF = 0.5
EXT_SCORE = 2         # matched-triangle weight a pair needs
EXT_MARGIN = 1.5      # over the runner-up, in both row and column
EXT_AGREE = 0.5       # matched / (matched + contradicted) evidence, both webs
PRIOR_RESULTS = Path("results/graphlog-heldout/results.json")

HELDOUT = ["rule_1", "rule_2", "rule_3", "rule_4", "rule_5", "rule_6",
           "rule_7", "rule_8", "rule_9", "rule_10", "rule_11", "rule_12",
           "rule_13", "rule_14", "rule_15", "rule_16", "rule_17", "rule_20",
           "rule_23", "rule_24", "rule_25", "rule_26", "rule_27", "rule_28",
           "rule_29", "rule_30", "rule_31", "rule_32", "rule_33", "rule_34",
           "rule_35", "rule_36", "rule_37", "rule_38", "rule_39", "rule_40",
           "rule_41", "rule_42", "rule_45", "rule_46", "rule_47", "rule_48",
           "rule_49", "rule_50"]


# ------------------------------------------------------------------ the views

def make_views(train: list[dict], labels: list[str], seed: int) -> dict:
    """Aspect-partial views: both views read every episode, each blind to its
    own disjoint HIDE_FRAC of relation types, each through its own opaque
    seeded bijection. Below evaluation, nothing sees a gold label."""
    rng = random.Random(seed)
    n_hide = max(2, round(HIDE_FRAC * len(labels)))
    hidden = rng.sample(labels, 2 * n_hide)
    hide_a, hide_b = set(hidden[:n_hide]), set(hidden[n_hide:])

    def perm(tag: str) -> dict:
        order = list(labels)
        rng.shuffle(order)
        return {lab: f"{tag}{i}" for i, lab in enumerate(order)}

    perm_a, perm_b = perm("a"), perm("b")

    def rendered(hide: set, p: dict) -> list[dict]:
        return [{"edges": [(u, v, p[r]) for u, v, r in g["edges"]
                           if r not in hide]} for g in train]

    return {"a": rendered(hide_a, perm_a), "b": rendered(hide_b, perm_b),
            "hide_a": hide_a, "hide_b": hide_b,
            "perm_a": perm_a, "perm_b": perm_b}


# ------------------------------------------------------- webs and interference

def triangle_votes(graphs: list[dict]) -> dict[tuple, Counter]:
    """The composition web: support-counted triangle evidence (a, b) -> c,
    exactly the counting inside graphlog.mine_rules, kept as raw votes so
    projection can pool evidence before thresholding."""
    votes: dict[tuple, Counter] = defaultdict(Counter)
    for g in graphs:
        out_idx: dict[int, list] = defaultdict(list)
        direct: dict[tuple, list] = defaultdict(list)
        for u, v, rel in g["edges"]:
            out_idx[u].append((v, rel))
            direct[(u, v)].append(rel)
        for u, v, rel in g["edges"]:
            for m, r2 in out_idx[v]:
                for r3 in direct.get((u, m), ()):
                    if m != u:
                        votes[(rel, r2)][r3] += 1
    return dict(votes)


def _threshold(votes: dict[tuple, Counter]) -> dict[tuple, str]:
    rules: dict[tuple, str] = {}
    for body, heads in votes.items():
        head = max(heads, key=lambda h: (heads[h], h))
        n = heads[head]
        if n >= MIN_SUPPORT and n / sum(heads.values()) >= MIN_CONF:
            rules[body] = head
    return rules


def _triples(votes: dict[tuple, Counter]) -> list[tuple]:
    """(a, b, c, support) list of the web's triangle evidence."""
    return [(a, b, c, n) for (a, b), heads in votes.items()
            for c, n in heads.items()]


def _components(votes: dict[tuple, Counter]) -> dict[str, int]:
    """Token -> component id of the web (triples as cliques). Web-local and
    label-free: this is what the curiosity rule for anchor placement reads."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, c, _n in _triples(votes):
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[rc] = ra
    roots = sorted({find(t) for t in parent})
    idx = {r: i for i, r in enumerate(roots)}
    return {t: idx[find(t)] for t in parent}


def pick_anchors(train: list[dict], views: dict,
                 votes_a: dict) -> dict[str, str]:
    """Curiosity-placed co-witnessing, ANCHOR_BUDGET single edges. The first
    co-perceivable edge in the stream anchors first; every further anchor is
    spent on the component of A's own mined web that currently has the
    fewest anchors (largest first) — the learner notices an unanchored
    island and asks for one shared experience there. Label-free: reads only
    A's web components and the edge stream."""
    perm_a, perm_b = views["perm_a"], views["perm_b"]
    hide = views["hide_a"] | views["hide_b"]
    stream = [r for g in train for _u, _v, r in g["edges"] if r not in hide]
    comp_of = _components(votes_a)
    comp_size = Counter(comp_of.values())
    anchors: dict[str, str] = {}
    anchored_rels: set = set()
    for _ in range(ANCHOR_BUDGET):
        n_anch = Counter(comp_of[perm_a[r]] for r in anchored_rels
                         if perm_a[r] in comp_of)
        ranked = sorted(comp_size, key=lambda c: (n_anch[c], -comp_size[c], c))
        pick = None
        for comp in ranked:
            pick = next((r for r in stream if r not in anchored_rels
                         and comp_of.get(perm_a[r]) == comp), None)
            if pick:
                break
        if pick is None:                     # islands exhausted: spread anyway
            pick = next((r for r in stream if r not in anchored_rels), None)
        if pick is None:
            break
        anchors[perm_a[pick]] = perm_b[pick]
        anchored_rels.add(pick)
    return anchors


def extend_mapping(votes_a: dict, votes_b: dict, anchors: dict,
                   signature_seed: bool = False) -> dict[str, str]:
    """Interference: grow the token correspondence by matched triangles.
    A candidate pair (x, y) scores the summed min-support of A-triples
    containing x whose other two positions, mapped through the current m,
    form a B-triple with y in x's position. Best pairs accepted only at
    score >= EXT_SCORE with EXT_MARGIN over the runner-up in both their row
    and column; repeat to fixpoint. Label-free and deterministic.

    signature_seed=True (the exploratory S=0 arm) starts from the single
    best positional-degree-signature pair instead of anchors."""
    ta, tb = _triples(votes_a), _triples(votes_b)
    m = dict(anchors)
    if signature_seed and not m:
        toks_a = sorted({t for tr in ta for t in tr[:3]})
        toks_b = sorted({t for tr in tb for t in tr[:3]})

        def sig(toks, triples):
            s = {t: [0, 0, 0, 0] for t in toks}
            for a, b, c, n in triples:
                s[a][0] += n; s[b][1] += n; s[c][2] += n
                s[a][3] += 1; s[b][3] += 1; s[c][3] += 1
            return s
        sa, sb = sig(toks_a, ta), sig(toks_b, tb)
        if toks_a and toks_b:
            best = min(((x, y) for x in toks_a for y in toks_b),
                       key=lambda p: (sum(abs(u - v) for u, v in
                                          zip(sa[p[0]], sb[p[1]])), p))
            m[best[0]] = best[1]
    while True:
        used = set(m.values())
        row_best: dict[str, list] = defaultdict(lambda: [0, 0, None])
        col_best: dict[str, list] = defaultdict(lambda: [0, 0, None])
        pair_score: Counter = Counter()
        for a, b, c, n in ta:
            unmapped = [t for t in (a, b, c) if t not in m]
            if len(unmapped) != 1:
                continue
            x = unmapped[0]
            pos = (a, b, c).index(x)
            want = [m[t] for t in (a, b, c) if t != x]
            for a2, b2, c2, n2 in tb:
                other = [(a2, b2, c2)[i] for i in range(3) if i != pos]
                y = (a2, b2, c2)[pos]
                if other == want and y not in used:
                    pair_score[(x, y)] += min(n, n2)
        if not pair_score:
            break
        for (x, y), s in pair_score.items():
            for best, key in ((row_best[x], y), (col_best[y], x)):
                if s > best[0]:
                    best[0], best[1], best[2] = s, best[0], key
                elif s > best[1]:
                    best[1] = s
        def agreement(x: str, y: str, s: float) -> float:
            """Destructive interference: evidence on either side that finds
            no counterpart under the pairing counts against it. Confabulated
            pairs (tokens with no true counterpart married off to each
            other) die here — their webs disagree almost everywhere."""
            trial = dict(m, **{x: y})
            inv = {v: k for k, v in trial.items()}
            contradicted = 0.0
            for a, b2, c, n in ta:
                if x in (a, b2, c) and all(t in trial for t in (a, b2, c)):
                    if (trial[a], trial[b2], trial[c]) not in \
                            {(p, q, r) for p, q, r, _n in tb}:
                        contradicted += n
            for a, b2, c, n in tb:
                if y in (a, b2, c) and all(t in inv for t in (a, b2, c)):
                    if (inv[a], inv[b2], inv[c]) not in \
                            {(p, q, r) for p, q, r, _n in ta}:
                        contradicted += n
            return s / (s + contradicted)

        accepted: dict[str, str] = {}
        for (x, y), s in sorted(pair_score.items(),
                                key=lambda kv: (-kv[1], kv[0])):
            rb, cb = row_best[x], col_best[y]
            if (s >= EXT_SCORE and rb[2] == y and cb[2] == x
                    and s >= EXT_MARGIN * max(rb[1], cb[1])
                    and x not in accepted and y not in set(accepted.values())
                    and agreement(x, y, s) >= EXT_AGREE):
                accepted[x] = y
        if not accepted:
            break
        m.update(accepted)
    return m


def project(votes_a: dict, votes_b: dict, m: dict[str, str]) -> dict[tuple, str]:
    """Knowledge as projection: B's votes translated through the mapping and
    pooled with A's, then the standard floors. Unmapped B tokens survive as
    IMPORTED vocabulary — knowledge about aspects A cannot perceive, named
    in B's terms until (if ever) a correspondence is found."""
    inv = {y: x for x, y in m.items()}
    tr = lambda t: inv.get(t, t)
    pooled: dict[tuple, Counter] = defaultdict(Counter)
    for body, heads in votes_a.items():
        pooled[body].update(heads)
    for (a, b), heads in votes_b.items():
        for c, n in heads.items():
            pooled[(tr(a), tr(b))][tr(c)] += n
    return _threshold(dict(pooled))


# ------------------------------------------------------------------ evaluation

def _render_test(rec: dict, views: dict, inv_map: dict, ensemble: bool) -> dict:
    """A test episode as the system perceives it: A's rendering, plus (for
    the ensemble) the co-witnessed B rendering of A-blind edges, translated
    through the discovered mapping where possible, imported otherwise."""
    edges = []
    for u, v, r in rec["edges"]:
        if r not in views["hide_a"]:
            edges.append((u, v, views["perm_a"][r]))
        elif ensemble and r not in views["hide_b"]:
            t = views["perm_b"][r]
            edges.append((u, v, inv_map.get(t, t)))
    return {"edges": edges, "query": rec["query"]}


def run_world(name: str, n_train: int = 150, seed: int = 0) -> dict:
    w = load_world(name, n_train)
    labels = sorted({r for g in w["train"] + w["test"] for _u, _v, r in g["edges"]}
                    | {g["target"] for g in w["train"]}
                    | {g["query"][2] for g in w["test"]})
    views = make_views(w["train"], labels, seed)
    votes_a = triangle_votes(views["a"])
    votes_b = triangle_votes(views["b"])

    anchors = pick_anchors(w["train"], views, votes_a)
    mapping = extend_mapping(votes_a, votes_b, anchors)
    inv_map = {y: x for x, y in mapping.items()}
    rules_alone = _threshold(votes_a)
    rules_ens = project(votes_a, votes_b, mapping)
    rules_gold = _threshold(triangle_votes(w["train"]))

    inv_a = {v: k for k, v in views["perm_a"].items()}
    inv_b = {v: k for k, v in views["perm_b"].items()}
    back = lambda t: inv_a.get(t, inv_b.get(t, t))
    prior_a = Counter()
    for g in views["a"]:
        for _u, _v, r in g["edges"]:
            prior_a[r] += 1
    maj_a = max(prior_a, key=lambda r: (prior_a[r], r))

    def acc(rules, mode: str) -> float:
        hit = 0
        for rec in w["test"]:
            if mode == "gold":
                got = cyk_predict(rec, rules, back(maj_a))
            else:
                r = _render_test(rec, views, inv_map, mode == "ensemble")
                got = back(cyk_predict(r, rules, maj_a))
            hit += got == rec["query"][2]
        return hit / len(w["test"])

    # alignment audit (evaluation-only gold)
    true_map = {views["perm_a"][l]: views["perm_b"][l] for l in labels}
    ext_pairs = {x: y for x, y in mapping.items() if x not in anchors}
    ext_prec = (sum(true_map.get(x) == y for x, y in ext_pairs.items())
                / len(ext_pairs)) if ext_pairs else None
    # wrong-pair split: an "orphan" merge pairs tokens whose true counterpart
    # is invisible to the other web (defensible projection); "real" mispairs
    # two mutually visible tokens (a genuine alignment error).
    wrong = [(x, y) for x, y in ext_pairs.items() if true_map.get(x) != y]
    orphan = sum(1 for x, y in wrong
                 if inv_a[x] in views["hide_b"] or inv_b[y] in views["hide_a"])
    b_occ = Counter()
    for a, b, c, _n in _triples(votes_b):
        for t in (a, b, c):
            b_occ[t] += 1
    eligible = {t for t, k in b_occ.items() if k >= 2}
    coverage = (len(eligible & set(mapping.values())) / len(eligible)
                if eligible else None)

    m0 = extend_mapping(votes_a, votes_b, {}, signature_seed=True)
    m0_prec = (sum(true_map.get(x) == y for x, y in m0.items()) / len(m0)
               if m0 else None)

    return {"world": name, "seed": seed,
            "accuracy": {"view-alone": round(acc(rules_alone, "alone"), 4),
                         "ensemble": round(acc(rules_ens, "ensemble"), 4),
                         "gold-pooled": round(acc(rules_gold, "gold"), 4)},
            "alignment": {"anchored": len(anchors),
                          "extended": len(ext_pairs),
                          "ext_precision": ext_prec,
                          "wrong_orphan": orphan,
                          "wrong_real": len(wrong) - orphan,
                          "coverage": coverage},
            "s0": {"mapped": len(m0), "precision": m0_prec},
            "rules": {"alone": len(rules_alone), "ensemble": len(rules_ens),
                      "gold": len(rules_gold)},
            "n_labels": len(labels)}


# ------------------------------------------------------------------ runner

def _mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worlds", default=",".join(HELDOUT))
    ap.add_argument("--n-train", type=int, default=150)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/multiweb-graphlog")
    args = ap.parse_args(argv)

    prior = {}
    if PRIOR_RESULTS.exists():
        prior = {r["world"]: r["accuracy"]
                 for r in json.loads(PRIOR_RESULTS.read_text())}

    t0 = time.time()
    rows = []
    for name in args.worlds.split(","):
        r = run_world(name.strip(), args.n_train, args.seed)
        r["prior"] = prior.get(r["world"], {})
        a, al = r["accuracy"], r["alignment"]
        fmt = lambda v: "n/a" if v is None else f"{v:.2f}"
        print(f"{r['world']}: alone={a['view-alone']:.3f} ens={a['ensemble']:.3f} "
              f"gold={a['gold-pooled']:.3f} "
              f"transport={r['prior'].get('transport', float('nan')):.3f} "
              f"(ext {al['extended']} prec {fmt(al['ext_precision'])}, "
              f"cov {fmt(al['coverage'])}, {time.time() - t0:.0f}s)", flush=True)
        rows.append(r)

    ens = [r["accuracy"]["ensemble"] for r in rows]
    alone = [r["accuracy"]["view-alone"] for r in rows]
    gold = [r["accuracy"]["gold-pooled"] for r in rows]
    trans = [r["prior"].get("transport") for r in rows]
    closures = [(r["accuracy"]["ensemble"] - r["accuracy"]["view-alone"])
                / (r["accuracy"]["gold-pooled"] - r["accuracy"]["view-alone"])
                for r in rows
                if r["accuracy"]["gold-pooled"] - r["accuracy"]["view-alone"] >= 0.02]
    summary = {
        "worlds": len(rows), "elapsed_s": round(time.time() - t0, 1),
        "mean_view_alone": _mean(alone), "mean_ensemble": _mean(ens),
        "mean_gold_pooled": _mean(gold), "mean_transport_prior": _mean(trans),
        "P-K1_ext_precision": _mean([r["alignment"]["ext_precision"] for r in rows]),
        "P-K1_coverage": _mean([r["alignment"]["coverage"] for r in rows]),
        "wrong_orphan_total": sum(r["alignment"]["wrong_orphan"] for r in rows),
        "wrong_real_total": sum(r["alignment"]["wrong_real"] for r in rows),
        "P-K2_ensemble_over_gold": (_mean(ens) / _mean(gold)) if _mean(gold) else None,
        "P-T1_ensemble_minus_transport": (_mean(ens) - _mean(trans))
                                         if _mean(trans) is not None else None,
        "P-T2_gap_closure": _mean(closures),
        "P-T2_worlds_with_gap": len(closures),
        "s0_precision": _mean([r["s0"]["precision"] for r in rows]),
        "s0_mapped_mean": _mean([r["s0"]["mapped"] for r in rows]),
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(
        {"summary": summary, "worlds": rows}, indent=1))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
