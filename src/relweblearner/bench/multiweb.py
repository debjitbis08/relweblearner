"""Multi-web interference benchmark (docs/multiweb-plan.md).

The original hypothesis, tested minimally and with no Creature code:

    thinking = dynamics in opaque geometric webs;
    concepts = projections of stable structures within and BETWEEN webs.

A hidden world of entities in communities is experienced only through opaque
co-occurrence episodes, seen by K views that each produce their own opaque
weighted web (view-local ids, no labels anywhere). Stable regions are found
independently per web (Louvain + persistence under edge dropout); partial
cross-web mappings (sparse anchors + conservative structural extension) let
each region be checked for CORRESPONDENCE in the other webs; regions that
correspond somewhere project to concepts, the rest stay provisional.

A coherent forgery — 8 fresh nodes wired with the true communities' own
internal statistics — is inserted into view 0's web only. The decisive
comparison: the one-web system (stability alone) accepts it; the multi-web
system finds it corresponds nowhere and keeps it out of the projection. The
solo control (a TRUE community visible only in view 0) is the pre-registered
honest limit: it too stays provisional, because interference measures
correspondence, not truth.

Usage:  relweb-multiweb [--seeds N] [--out results/bench-multiweb]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import networkx as nx
from networkx.algorithms.community import louvain_communities

# ------------------------------------------------------------ world constants
N_COM = 6             # hidden communities ...
COM_SIZE = 10         # ... of this many entities
SOLO_COM = 5          # visible ONLY in view 0 (the honest-limit control)
K_VIEWS = 3
COVERAGE = 0.8        # per-entity per-view visibility (solo com: view 0 only, full)
N_EPISODES = 400      # per view
EP_NOISE = 0.08       # fraction of episodes drawing entities across communities
ANCHOR_RATE = 0.4     # per co-visible entity per view pair
FORGE_N = 8           # forged nodes, view 0 only

# ------------------------------------------------------ stability / interference
MIN_REGION = 4        # smaller regions are crumbs
PERTURB = 5           # stability re-detections
DROPOUT = 0.2         # edge dropout per re-detection
STAB_TAU = 0.6        # mean best-Jaccard to count as stable
CORR_MIN_IMG = 2      # region needs >= this many mapped members to be checkable
CORR_THETA = 0.6      # image concentration to count as corresponding
EXT_ROUNDS = 3        # structural mapping extension passes
EXT_SUPPORT = 2       # distinct mapped neighbours that must back a candidate
EXT_MARGIN = 1.5      # best candidate strength vs runner-up
EXT_BACKBONE = 0.5    # edges below this fraction of the web's median weight
                      # carry no identity evidence (post-P-D-leak amendment)


@dataclass
class MultiWorld:
    """One seeded instance. ``hidden``/``communities`` are EVAL-ONLY gold —
    nothing in the pipeline below ``evaluate`` may touch them."""
    seed: int
    webs: list                                   # nx.Graph per view, opaque ids
    hidden: list[dict]                           # per view: node id -> entity
    communities: list[frozenset] = field(default_factory=list)
    anchors: dict = field(default_factory=dict)  # (i, j) i<j -> {node_i: node_j}
    forged: frozenset = frozenset()              # view-0 forged node ids
    covered: list[set] = field(default_factory=list)  # per com: views with >=3 visible


def generate(seed: int = 0) -> MultiWorld:
    rng = random.Random(seed)
    entities = list(range(N_COM * COM_SIZE))
    communities = [frozenset(range(c * COM_SIZE, (c + 1) * COM_SIZE))
                   for c in range(N_COM)]
    com_of = {e: c for c, com in enumerate(communities) for e in com}

    # visibility: solo com only (and fully) in view 0; everything else p=COVERAGE
    visible: list[set] = []
    for k in range(K_VIEWS):
        vis = set()
        for e in entities:
            if com_of[e] == SOLO_COM:
                if k == 0:
                    vis.add(e)
            elif rng.random() < COVERAGE:
                vis.add(e)
        visible.append(vis)

    # opaque per-view ids: a shuffled index space, nothing shared across views
    hidden: list[dict] = []
    label: list[dict] = []
    for k in range(K_VIEWS):
        order = sorted(visible[k])
        rng.shuffle(order)
        lab = {e: f"w{k}:{i}" for i, e in enumerate(order)}
        label.append(lab)
        hidden.append({v: e for e, v in lab.items()})

    # episodes -> co-occurrence webs
    webs: list[nx.Graph] = []
    for k in range(K_VIEWS):
        G = nx.Graph()
        G.add_nodes_from(label[k][e] for e in sorted(visible[k]))
        by_com = [sorted(com & visible[k]) for com in communities]
        eligible = [c for c in range(N_COM) if len(by_com[c]) >= 3]
        vis_sorted = sorted(visible[k])
        for _ in range(N_EPISODES):
            if rng.random() < EP_NOISE:
                members = rng.sample(vis_sorted, 3)
            else:
                c = rng.choice(eligible)
                members = rng.sample(by_com[c], rng.choice((3, 4)))
            for a, b in combinations(members, 2):
                u, v = label[k][a], label[k][b]
                G.add_edge(u, v, weight=G[u][v]["weight"] + 1 if G.has_edge(u, v) else 1)
        webs.append(G)

    # ---- the coherent forgery, view 0 only: internal statistics SAMPLED from
    # the true communities of that same web, so coherence is matched by
    # construction. No anchors — a fabrication was never co-witnessed.
    G0 = webs[0]
    intra_w, inter_w, ext_deg = [], [], []
    intra_present = intra_possible = 0
    for c in range(N_COM):
        mem = [label[0][e] for e in sorted(communities[c] & visible[0])]
        intra_possible += len(mem) * (len(mem) - 1) // 2
        mset = set(mem)
        for u in mem:
            ext = 0
            for v, d in G0[u].items():
                if v in mset:
                    if u < v:
                        intra_present += 1
                        intra_w.append(d["weight"])
                else:
                    ext += 1
                    inter_w.append(d["weight"])
            ext_deg.append(ext)
    density = intra_present / max(1, intra_possible)
    real0 = sorted(G0.nodes)
    forged = [f"w0:{len(real0) + i}" for i in range(FORGE_N)]
    G0.add_nodes_from(forged)
    for u, v in combinations(forged, 2):
        if rng.random() < density:
            G0.add_edge(u, v, weight=rng.choice(intra_w))
    for u in forged:                              # keep the phantom connected
        if not any(v in forged for v in G0[u]):
            v = rng.choice([x for x in forged if x != u])
            G0.add_edge(u, v, weight=rng.choice(intra_w))
    for u in forged:                              # plausible attachment edges
        for v in rng.sample(real0, min(rng.choice(ext_deg), len(real0))):
            if not G0.has_edge(u, v):
                G0.add_edge(u, v, weight=rng.choice(inter_w or [1]))

    # ---- sparse given anchors per view pair (simultaneity story)
    anchors: dict = {}
    for i, j in combinations(range(K_VIEWS), 2):
        m = {}
        for e in sorted(visible[i] & visible[j]):
            if rng.random() < ANCHOR_RATE:
                m[label[i][e]] = label[j][e]
        anchors[(i, j)] = m

    covered = [{k for k in range(K_VIEWS)
                if len(com & visible[k]) >= 3} for com in communities]
    return MultiWorld(seed=seed, webs=webs, hidden=hidden,
                      communities=communities, anchors=anchors,
                      forged=frozenset(forged), covered=covered)


# --------------------------------------------------------------- stable regions

def stable_regions(G: nx.Graph, seed: int) -> list[frozenset]:
    """Louvain candidates that persist under edge dropout — the operational
    reading of 'stable structures of the dynamics'. Web-local; no cross-web
    information enters here."""
    if G.number_of_edges() == 0:
        return []
    base = [frozenset(c) for c in louvain_communities(G, weight="weight", seed=seed)
            if len(c) >= MIN_REGION]
    rng = random.Random(seed ^ 0x5F5F)
    reruns = []
    for p in range(PERTURB):
        H = nx.Graph()
        H.add_nodes_from(G)
        H.add_weighted_edges_from((u, v, d["weight"]) for u, v, d in G.edges(data=True)
                                  if rng.random() > DROPOUT)
        reruns.append([set(c) for c in
                       louvain_communities(H, weight="weight", seed=seed + p + 1)])
    out = []
    for c in base:
        js = [max((len(c & p) / len(c | p) for p in parts), default=0.0)
              for parts in reruns]
        if sum(js) / len(js) >= STAB_TAU:
            out.append(c)
    return out


# ------------------------------------------------------------ partial mappings

def extend_mapping(GA: nx.Graph, GB: nx.Graph, seed_map: dict) -> dict:
    """Conservative structural propagation of the anchor map. A node is mapped
    only when >= EXT_SUPPORT already-mapped neighbours back one candidate and
    it beats the runner-up by EXT_MARGIN; inside a near-symmetric community
    that rarely resolves — the mapping is MEANT to stay partial.

    Identity evidence rides only the structural backbone: edges lighter than
    EXT_BACKBONE x the web's median edge weight are skipped (web-local, label
    free). Without this, weight-1 noise edges hallucinate images for nodes
    that were never co-witnessed — the P-D leak of the first run."""
    m = dict(seed_map)
    used = set(m.values())
    if GA.number_of_edges() == 0 or GB.number_of_edges() == 0:
        return m
    med_a = statistics.median(d["weight"] for _u, _v, d in GA.edges(data=True))
    med_b = statistics.median(d["weight"] for _u, _v, d in GB.edges(data=True))
    for _ in range(EXT_ROUNDS):
        additions: dict = {}
        for u in sorted(GA.nodes):
            if u in m:
                continue
            support: Counter = Counter()
            strength: Counter = Counter()
            for nb, d in GA[u].items():
                if nb not in m or m[nb] not in GB:
                    continue
                if d["weight"] < EXT_BACKBONE * med_a:
                    continue
                for v, db in GB[m[nb]].items():
                    if v in used or db["weight"] < EXT_BACKBONE * med_b:
                        continue
                    support[v] += 1
                    strength[v] += min(d["weight"], db["weight"])
            ranked = sorted(strength, key=lambda v: (-strength[v], v))
            if not ranked or support[ranked[0]] < EXT_SUPPORT:
                continue
            best = ranked[0]
            if len(ranked) > 1 and strength[best] < EXT_MARGIN * strength[ranked[1]]:
                continue
            if best in additions and strength[best] <= additions[best][0]:
                continue
            additions[best] = (strength[best], u)
        if not additions:
            break
        for v, (_s, u) in additions.items():
            m[u] = v
            used.add(v)
    return m


def all_mappings(world: MultiWorld) -> dict:
    """Directed partial mapping for every ordered view pair."""
    maps = {}
    for (i, j), m in world.anchors.items():
        maps[(i, j)] = extend_mapping(world.webs[i], world.webs[j], m)
        maps[(j, i)] = extend_mapping(world.webs[j], world.webs[i],
                                      {v: u for u, v in m.items()})
    return maps


# ------------------------------------------------- interference and projection

def correspondence(region: frozenset, mapping: dict,
                   regions_other: list[frozenset]) -> float:
    """How well this region's mapped image concentrates in a single stable
    region of the other web. 0.0 when fewer than CORR_MIN_IMG members map."""
    img = {mapping[n] for n in region if n in mapping}
    if len(img) < CORR_MIN_IMG:
        return 0.0
    best = max((len(img & rb) for rb in regions_other), default=0)
    return best / len(img)


def project(regions: list[list[frozenset]], maps: dict) -> list[dict]:
    """The semantic projection: every stable region, scored for cross-web
    corroboration. ``concept`` = corresponds in >= 1 other web (i.e. the
    structure is agreed between >= 2 webs); otherwise provisional."""
    rows = []
    for i, regs in enumerate(regions):
        for r in regs:
            scores = {j: correspondence(r, maps[(i, j)], regions[j])
                      for j in range(len(regions)) if j != i}
            corr = sum(1 for s in scores.values() if s >= CORR_THETA)
            rows.append({"view": i, "region": r, "scores": scores,
                         "corroboration": corr, "concept": corr >= 1})
    return rows


# ----------------------------------------------------------------- evaluation

def run_seed(seed: int) -> dict:
    world = generate(seed)
    regions = [stable_regions(w, seed * 31 + k) for k, w in enumerate(world.webs)]
    maps = all_mappings(world)
    rows = project(regions, maps)

    com_of = {e: c for c, com in enumerate(world.communities) for e in com}

    def majority_com(row):
        """The region's hidden majority community; forged members vote None."""
        votes = Counter(com_of.get(world.hidden[row["view"]].get(n)) for n in row["region"])
        return votes.most_common(1)[0][0]

    forged_rows = [r for r in rows
                   if r["view"] == 0 and len(r["region"] & world.forged) >= FORGE_N // 2]
    forged_stable = bool(forged_rows)
    forged_best = max((max(r["scores"].values()) for r in forged_rows), default=None)
    forged_concept = any(r["concept"] for r in forged_rows)

    multi_covered = {c for c in range(N_COM) if len(world.covered[c]) >= 2}
    true_scores = [max(r["scores"].values()) for r in rows
                   if r not in forged_rows and majority_com(r) in multi_covered]

    concepts = [r for r in rows if r["concept"]]
    recovered = {majority_com(r) for r in concepts} & multi_covered
    recall = len(recovered) / len(multi_covered) if multi_covered else None

    purities = []
    for r in concepts:
        votes = Counter(com_of.get(world.hidden[r["view"]].get(n)) for n in r["region"])
        top = max((cnt for c, cnt in votes.items() if c is not None), default=0)
        purities.append(top / len(r["region"]))
    purity = statistics.mean(purities) if purities else None

    solo_rows = [r for r in rows if r["view"] == 0 and not r["region"] & world.forged
                 and majority_com(r) == SOLO_COM]
    solo_found = bool(solo_rows)
    solo_concept = any(r["concept"] for r in solo_rows)

    mapped_forged = {n for n in world.forged
                     if any(n in maps[(0, j)] for j in range(1, K_VIEWS))}

    return {"seed": seed,
            "one_web_accepts_forgery": forged_stable,
            "forged_best_corr": forged_best,
            "multi_web_accepts_forgery": forged_concept,
            "true_scores": true_scores,
            "recall": recall,
            "purity": purity,
            "solo_found": solo_found,
            "solo_projected": solo_concept,
            "forged_mapped_frac": len(mapped_forged) / FORGE_N,
            "n_concepts": len(concepts),
            "n_regions": len(rows)}


# ------------------------------------------------------------------ reporting

def _rate(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return sum(vals) / len(vals) if vals else float("nan")


def _meansd(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n/a"
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return f"{m:.2f} +/- {s:.2f}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--out", default="results/bench-multiweb")
    args = ap.parse_args(argv)

    t0 = time.time()
    rows = [run_seed(s) for s in range(args.seeds)]
    dt = time.time() - t0

    all_true = [s for r in rows for s in r["true_scores"]]
    checkable = [s for s in all_true if s > 0.0]
    forged_scores = [r["forged_best_corr"] for r in rows
                     if r["forged_best_corr"] is not None]
    summary = {
        "seeds": args.seeds,
        "elapsed_s": round(dt, 1),
        "P-A_one_web_accepts_forgery": _rate(rows, "one_web_accepts_forgery"),
        "P-B_forged_below_theta": (sum(1 for s in forged_scores if s < CORR_THETA)
                                   / len(forged_scores) if forged_scores else None),
        "P-B_forged_corr_mean": (statistics.mean(forged_scores)
                                 if forged_scores else None),
        "P-B_true_corr_mean": statistics.mean(all_true) if all_true else None,
        "P-B_true_corr_checkable_mean": (statistics.mean(checkable)
                                         if checkable else None),
        "P-C_multi_web_rejects_forgery": 1 - _rate(rows, "multi_web_accepts_forgery"),
        "P-C_concept_recall": _rate(rows, "recall"),
        "P-C_concept_purity": _rate(rows, "purity"),
        "P-D_solo_found": _rate(rows, "solo_found"),
        "P-D_solo_kept_provisional": 1 - _rate(rows, "solo_projected"),
        "P-E_forged_mapped_frac": _rate(rows, "forged_mapped_frac"),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(
        {"summary": summary, "per_seed": rows}, indent=2, default=list))

    lines = ["# Multi-web interference — results", "",
             f"{args.seeds} seeds, {dt:.0f}s. Pre-registered design and "
             "predictions: docs/multiweb-plan.md (committed before this run).", "",
             "The decisive comparison (rates over seeds):", "",
             "| outcome | one-web | multi-web |",
             "|---|---|---|",
             f"| coherent forgery accepted as concept | "
             f"{summary['P-A_one_web_accepts_forgery']:.2f} | "
             f"{1 - summary['P-C_multi_web_rejects_forgery']:.2f} |", "",
             "Correspondence (the interference signal):", "",
             "| quantity | value |",
             "|---|---|",
             f"| forged region best cross-web score | "
             f"{_meansd(forged_scores)} |",
             f"| true-region score, all | {_meansd(all_true)} |",
             f"| true-region score, checkable (>=2 mapped members) | "
             f"{_meansd(checkable)} |",
             f"| forged below theta={CORR_THETA} | "
             f"{summary['P-B_forged_below_theta']:.2f} |", "",
             "Projection quality and the honest limit:", "",
             "| quantity | value |",
             "|---|---|",
             f"| concept recall (>=2-view communities) | "
             f"{_meansd([r['recall'] for r in rows])} |",
             f"| concept purity | {_meansd([r['purity'] for r in rows])} |",
             f"| solo-truth region found stable | "
             f"{summary['P-D_solo_found']:.2f} |",
             f"| solo-truth kept provisional (NOT a concept) | "
             f"{summary['P-D_solo_kept_provisional']:.2f} |",
             f"| forged nodes given images by extension | "
             f"{summary['P-E_forged_mapped_frac']:.2f} |", ""]
    (out / "report.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
