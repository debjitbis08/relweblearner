"""The overlap forgery (E2b) — the decisive geometric-obstruction test.

Pre-registration: docs/multiweb-overlap-forgery-plan.md (committed before this
code; §3a amendment committed before the bring-up run). design-problem.md §10's
#1 licensed diagnosis and the only §9 falsifier of the conjecture itself.

bench-multiweb settled (design-problem §2) that the fresh-node forgery (E1) and
the solo truth (E2) are geometrically IDENTICAL: neither touches the overlap, so
`correspondence()` returns 0 for both and P1 (the closed-world policy) — not
geometry — keeps them out. This module asks the open question: is there a
forgery rejected by GEOMETRY, as a genuinely different TYPE, with no appeal to
P1? The instrument is an OVERLAP forgery — a false MERGE wiring strong bridge
edges between two multi-covered, anchored communities in view 0 only, so the lie
lands on co-witnessed nodes the other views can refute edge by edge.

The detector is `agreement()` from multiweb_graphlog, read on co-occurrence
edges: a trial gluing whose CONTRADICTED residual (a strong edge here whose
mapped image is absent there) is the "genuine residual of an attempted
extension" of design-problem §2. Per the §3a amendment a region is OBSTRUCTED
when that residual reaches OBS_MIN_CONTRA refuting backbone edges — a count, not
the dilution-prone weight ratio.

The frozen bench-multiweb is reused UNCHANGED and never perturbed: the false
merge is layered onto a generated world after `generate()` returns, so the E1
and E2 arms stay byte-identical.

Usage:  relweb-multiweb-overlap [--seeds N] [--out results/bench-multiweb-overlap]
        relweb-multiweb-overlap --bringup 5     # Q-A diagnostics, not scored
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

from .multiweb import (
    CORR_MIN_IMG,
    EXT_BACKBONE,
    FORGE_N,
    K_VIEWS,
    N_COM,
    SOLO_COM,
    all_mappings,
    generate,
    project,
    stable_regions,
)

# ------------------------------------------------------------------- constants
MERGE_FRAC = 0.6      # bridge density over anchored A x B pairs (Q-A tune, then frozen)
OBS_MIN_CONTRA = 2    # §3a: refuting backbone edges to call a region obstructed
OBS_THETA = 0.5       # reported secondary ratio only (ported EXT_AGREE), NOT the gate


# --------------------------------------------------- the overlap forgery arm

def add_overlap_forgery(world, seed: int) -> dict:
    """Layer a false MERGE onto view 0's web AFTER generate(): wire strong bridge
    edges between two multi-covered, anchored communities A and B that share a
    witness view j, so both endpoints of every bridge map into the same other web
    (checkable) and land in SEPARATE true regions there (refutable). Weights are
    sampled from view 0's own intra-community distribution — coherence matched by
    construction, exactly as E1. Mutates world.webs[0]; returns an eval-only info
    dict (never read by the pipeline)."""
    rng = random.Random(seed ^ 0xB1A5)
    com_of = {e: c for c, com in enumerate(world.communities) for e in com}
    label0 = {e: n for n, e in world.hidden[0].items()}
    G0 = world.webs[0]

    # empirical intra-community weight distribution of web 0 (mirrors E1)
    intra_w = [d["weight"] for u, v, d in G0.edges(data=True)
               if world.hidden[0].get(u) is not None
               and world.hidden[0].get(v) is not None
               and com_of[world.hidden[0][u]] == com_of[world.hidden[0][v]]]

    # anchored view-0 members of community c into other view j
    def anchored(c: int, j: int) -> list[str]:
        keys = world.anchors.get((0, j), {})
        return [label0[e] for e in sorted(world.communities[c])
                if e in label0 and label0[e] in keys]

    cand = [c for c in range(N_COM) if c != SOLO_COM and len(world.covered[c]) >= 2]

    # choose (A, B, j): a common witness view where both clear CORR_MIN_IMG
    best = None
    for j in range(1, K_VIEWS):
        anc = {c: anchored(c, j) for c in cand}
        rich = [c for c in cand if len(anc[c]) >= CORR_MIN_IMG]
        for a, b in combinations(sorted(rich, key=lambda c: (-len(anc[c]), c)), 2):
            score = min(len(anc[a]), len(anc[b]))
            if best is None or score > best[0]:
                best = (score, a, b, j, anc[a], anc[b])

    if best is None:
        return {"constructible": False}
    _score, A, B, j, anc_a, anc_b = best

    # Wire the false merge across the FULL view-0 memberships of A and B (a
    # coherent single block, so Louvain actually merges them), weights sampled
    # from the true intra distribution. The anchored subsets (anc_a/anc_b) are a
    # subset of these, so a MERGE_FRAC fraction of anchored x anchored pairs is
    # bridged too — those are the CHECKABLE edges the obstruction detector reads.
    fa = [label0[e] for e in sorted(world.communities[A]) if e in label0]
    fb = [label0[e] for e in sorted(world.communities[B]) if e in label0]
    added = 0
    for u in fa:
        for v in fb:
            if rng.random() < MERGE_FRAC:
                w = rng.choice(intra_w) if intra_w else 1
                G0.add_edge(u, v, weight=(G0[u][v]["weight"] + w
                                          if G0.has_edge(u, v) else w))
                added += 1
    if added == 0 and fa and fb:                       # keep the seam connected
        w = rng.choice(intra_w) if intra_w else 1
        G0.add_edge(fa[0], fb[0], weight=w)
        added = 1

    return {"constructible": True, "A": A, "B": B, "witness": j,
            "bridge_edges": added,
            "bridged_a": frozenset(fa), "bridged_b": frozenset(fb),
            "merge_nodes": frozenset(fa) | frozenset(fb)}


# ------------------------------------------------------- the obstruction detector

def _backbone(G):
    med = statistics.median(d["weight"] for _u, _v, d in G.edges(data=True))
    return EXT_BACKBONE * med


def obstruction_pair(region, GA, mapping, GB) -> tuple[int, float]:
    """Trial gluing of region into GB via `mapping` (ported agreement()): count
    the region's strong (backbone) edges whose mapped image is NOT a strong edge
    in GB. Returns (contradicted_count, contradicted_weight_ratio)."""
    if GA.number_of_edges() == 0 or GB.number_of_edges() == 0:
        return 0, 0.0
    bb_a, bb_b = _backbone(GA), _backbone(GB)
    matched_w = contra_w = 0.0
    contra_n = 0
    for u in region:
        if u not in mapping or u not in GA:
            continue
        for v, d in GA[u].items():
            if v not in region or not (u < v) or v not in mapping:
                continue
            if d["weight"] < bb_a:                     # only strong claims of web i
                continue
            mu, mv = mapping[u], mapping[v]
            if GB.has_edge(mu, mv) and GB[mu][mv]["weight"] >= bb_b:
                matched_w += min(d["weight"], GB[mu][mv]["weight"])
            else:
                contra_w += d["weight"]
                contra_n += 1
    denom = matched_w + contra_w
    return contra_n, (contra_w / denom if denom > 0 else 0.0)


def region_obstruction(region, i, world, maps) -> tuple[int, float]:
    """The region's residual = the strongest single refuting view (§3)."""
    best_n, best_r = 0, 0.0
    for j in range(K_VIEWS):
        if j == i:
            continue
        n, r = obstruction_pair(region, world.webs[i], maps[(i, j)], world.webs[j])
        if n > best_n or (n == best_n and r > best_r):
            best_n, best_r = n, r
    return best_n, best_r


def classify(contra: int, corroboration: int) -> str:
    """The §3a typed refusal, no P1 counting involved."""
    if contra >= OBS_MIN_CONTRA:
        return "obstructed"
    if corroboration >= 1:
        return "committed"
    return "unsupported"


# ----------------------------------------------------------------- evaluation

def _region_for(world, view, regions, entities) -> frozenset | None:
    """The stable region of `view` holding the plurality of `entities`."""
    inv = {e: n for n, e in world.hidden[view].items()}
    nodes = {inv[e] for e in entities if e in inv}
    best, best_ov = None, 0
    for r in regions[view]:
        ov = len(r & nodes)
        if ov > best_ov:
            best, best_ov = r, ov
    return best if best_ov >= CORR_MIN_IMG else None


def run_seed(seed: int) -> dict:
    world = generate(seed)
    info = add_overlap_forgery(world, seed)

    regions = [stable_regions(w, seed * 31 + k) for k, w in enumerate(world.webs)]
    maps = all_mappings(world)
    rows = project(regions, maps)
    for r in rows:
        r["contra"], r["ratio"] = region_obstruction(r["region"], r["view"], world, maps)
        r["type"] = classify(r["contra"], r["corroboration"])

    com_of = {e: c for c, com in enumerate(world.communities) for e in com}

    def majority_com(row):
        votes = Counter(com_of.get(world.hidden[row["view"]].get(n)) for n in row["region"])
        return votes.most_common(1)[0][0]

    multi_covered = {c for c in range(N_COM) if len(world.covered[c]) >= 2}

    # --- the three arms, side by side in the same worlds ---
    forged_rows = [r for r in rows if r["view"] == 0
                   and len(r["region"] & world.forged) >= FORGE_N // 2]
    solo_rows = [r for r in rows if r["view"] == 0 and not r["region"] & world.forged
                 and majority_com(r) == SOLO_COM]

    def arm(rowset):
        if not rowset:
            return None
        r = max(rowset, key=lambda x: x["contra"])   # worst-case residual of the arm
        return {"contra": r["contra"], "ratio": round(r["ratio"], 3),
                "corr": r["corroboration"], "type": r["type"]}

    e1, e2 = arm(forged_rows), arm(solo_rows)

    out = {"seed": seed, "constructible": info.get("constructible", False),
           "e1": e1, "e2": e2, "e2b": None,
           "merge_stable": False, "merge_separate": None,
           "bridge_edges": info.get("bridge_edges"),
           "true_contras": [], "true_types": [], "recall": None, "purity": None}

    if info.get("constructible"):
        ba, bb = info["bridged_a"], info["bridged_b"]
        merged = [r for r in rows if r["view"] == 0
                  and len(r["region"] & ba) >= CORR_MIN_IMG
                  and len(r["region"] & bb) >= CORR_MIN_IMG]
        out["merge_stable"] = bool(merged)
        out["e2b"] = arm(merged)
        # Q1: are A and B SEPARATE stable regions in the other views?
        A, B = info["A"], info["B"]
        sep = {}
        for v in range(1, K_VIEWS):
            ra = _region_for(world, v, regions, world.communities[A])
            rb = _region_for(world, v, regions, world.communities[B])
            sep[v] = (ra is not None and rb is not None and ra != rb)
        out["merge_separate"] = all(sep.values())

    # --- true-region collateral (Q-E) and projection quality ---
    merged_regions = set()
    if out["e2b"] is not None:
        merged_regions = {id(r) for r in rows if r["view"] == 0
                          and len(r["region"] & info["bridged_a"]) >= CORR_MIN_IMG
                          and len(r["region"] & info["bridged_b"]) >= CORR_MIN_IMG}
    true_rows = [r for r in rows
                 if not (r["view"] == 0 and r["region"] & world.forged)
                 and id(r) not in merged_regions
                 and majority_com(r) in multi_covered]
    out["true_contras"] = [r["contra"] for r in true_rows]
    out["true_types"] = [r["type"] for r in true_rows]

    concepts = [r for r in rows if r["corroboration"] >= 1 and r["type"] != "obstructed"]
    recovered = {majority_com(r) for r in concepts} & multi_covered
    out["recall"] = len(recovered) / len(multi_covered) if multi_covered else None
    purities = []
    for r in concepts:
        votes = Counter(com_of.get(world.hidden[r["view"]].get(n)) for n in r["region"])
        top = max((cnt for c, cnt in votes.items() if c is not None), default=0)
        purities.append(top / len(r["region"]))
    out["purity"] = statistics.mean(purities) if purities else None
    return out


# ------------------------------------------------------------------ reporting

def _frac(pred, rows):
    rows = [r for r in rows if r is not None]
    return sum(1 for r in rows if pred(r)) / len(rows) if rows else float("nan")


def _dist(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n/a"
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return f"{m:.2f} +/- {s:.2f} (min {min(vals):.2f}, max {max(vals):.2f})"


def summarize(rows: list[dict]) -> dict:
    con = [r for r in rows if r["constructible"]]
    e2b = [r["e2b"] for r in con if r["e2b"] is not None]
    e1 = [r["e1"] for r in rows if r["e1"] is not None]
    e2 = [r["e2"] for r in rows if r["e2"] is not None]
    true_contras = [c for r in rows for c in r["true_contras"]]
    true_types = [t for r in rows for t in r["true_types"]]

    def type_frac(arms, t):
        return _frac(lambda a: a["type"] == t, arms)

    return {
        "seeds": len(rows),
        "constructible_frac": len(con) / len(rows) if rows else float("nan"),
        # Q-A
        "QA_merge_stable": _frac(lambda r: r["merge_stable"], con),
        "QA_merge_separate": _frac(lambda r: bool(r["merge_separate"]), con),
        # Q-B: residual separation (the decisive prediction)
        "QB_e2b_contra_ge_min": _frac(lambda a: a["contra"] >= OBS_MIN_CONTRA, e2b),
        "QB_e1_contra_zero": _frac(lambda a: a["contra"] == 0, e1),
        "QB_e2_contra_zero": _frac(lambda a: a["contra"] == 0, e2),
        "QB_e2b_contra_dist": _dist([a["contra"] for a in e2b]),
        "QB_e2b_ratio_dist": _dist([a["ratio"] for a in e2b]),
        "QB_e1_contra_dist": _dist([a["contra"] for a in e1]),
        # Q-C: typed cross-tabulation
        "QC_e2b_obstructed": type_frac(e2b, "obstructed"),
        "QC_e1_unsupported": type_frac(e1, "unsupported"),
        "QC_e2_unsupported": type_frac(e2, "unsupported"),
        # Q-D: policy independence
        "QD_e2b_geometric": _frac(lambda a: a["contra"] >= OBS_MIN_CONTRA, e2b),
        # Q-E: collateral
        "QE_true_false_obstructed": (sum(1 for t in true_types if t == "obstructed")
                                     / len(true_types) if true_types else float("nan")),
        "QE_true_contra_dist": _dist(true_contras),
        "QE_recall": _dist([r["recall"] for r in rows]),
        "QE_purity": _dist([r["purity"] for r in rows]),
    }


def _report_md(summ: dict) -> str:
    def g(k):
        v = summ[k]
        return f"{v:.2f}" if isinstance(v, float) else str(v)
    return "\n".join([
        "# The overlap forgery (E2b) — results", "",
        f"{summ['seeds']} seeds. Pre-registered design and predictions: "
        "docs/multiweb-overlap-forgery-plan.md (frozen before this run; §3a "
        "amendment frozen before the bring-up).", "",
        f"Constructible seeds: {g('constructible_frac')}.", "",
        "## The typed cross-tabulation (the headline)", "",
        "| arm | classified as | rate |",
        "|---|---|---|",
        f"| E2b overlap forgery | obstructed | {g('QC_e2b_obstructed')} |",
        f"| E1 fresh forgery | unsupported | {g('QC_e1_unsupported')} |",
        f"| E2 solo truth | unsupported | {g('QC_e2_unsupported')} |", "",
        "## Q-A — the merge is a coherent overlap forgery", "",
        "| quantity | value |",
        "|---|---|",
        f"| merge stable as one region in web 0 | {g('QA_merge_stable')} |",
        f"| A, B separate stable regions in other views | {g('QA_merge_separate')} |", "",
        "## Q-B — obstruction residual separation (decisive)", "",
        "| quantity | value |",
        "|---|---|",
        f"| E2b contra >= {OBS_MIN_CONTRA} | {g('QB_e2b_contra_ge_min')} |",
        f"| E1 contra == 0 | {g('QB_e1_contra_zero')} |",
        f"| E2 contra == 0 | {g('QB_e2_contra_zero')} |",
        f"| E2b contra distribution | {g('QB_e2b_contra_dist')} |",
        f"| E2b ratio (secondary, OBS_THETA={OBS_THETA}) | {g('QB_e2b_ratio_dist')} |",
        f"| E1 contra distribution | {g('QB_e1_contra_dist')} |", "",
        "## Q-D / Q-E — policy independence and collateral", "",
        "| quantity | value |",
        "|---|---|",
        f"| E2b rejected geometrically (no P1) | {g('QD_e2b_geometric')} |",
        f"| true regions FALSELY obstructed | {g('QE_true_false_obstructed')} |",
        f"| true-region contra distribution | {g('QE_true_contra_dist')} |",
        f"| concept recall | {g('QE_recall')} |",
        f"| concept purity | {g('QE_purity')} |", ""])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--start", type=int, default=1000,
                    help="first seed; the scored run is HELD OUT from the "
                         "bring-up block (seeds 0-11) by default")
    ap.add_argument("--bringup", type=int, default=0,
                    help="run N seeds from 0 and print Q-A diagnostics, not scored")
    ap.add_argument("--out", default="results/bench-multiweb-overlap")
    args = ap.parse_args(argv)

    if args.bringup:
        for s in range(args.bringup):
            r = run_seed(s)
            e2b = r["e2b"]
            print(f"seed {s}: constructible={r['constructible']} "
                  f"bridges={r['bridge_edges']} merge_stable={r['merge_stable']} "
                  f"separate={r['merge_separate']} "
                  f"e2b={e2b} e1={r['e1']} e2={r['e2']}")
        return

    t0 = time.time()
    rows = [run_seed(s) for s in range(args.start, args.start + args.seeds)]
    dt = time.time() - t0
    summ = summarize(rows)
    summ["elapsed_s"] = round(dt, 1)
    summ["seed_block"] = [args.start, args.start + args.seeds - 1]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(
        {"summary": summ, "per_seed": rows}, indent=2, default=list))
    (out / "report.md").write_text(_report_md(summ))
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
