"""The P2 discharge validator (docs/p2-discharge.md §5, §7).

Computes the model quantities p_miss and delta_x by sampling the DECLARED
generative process (frozen generate(), fresh seeds 10000+; no artifact is an
input; zero free parameters), then validates the pre-registered predictions
V1-V3 on the held-out seed block 2000-2049 and reports the frozen block
1000-1049 as disclosed retrodiction (V4). Tolerances are the note's; they
are applied, never adjusted here.

Plan-to-code checklist (note §7): model_rates() edge_rates() region_alpha()
detection() verdict() — all present and run by main().

Usage:  relweb-p2-validate [--out results/p2-discharge]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from .multiweb import (
    CORR_MIN_IMG, EXT_BACKBONE, K_VIEWS, N_COM,
    all_mappings, generate, project, stable_regions,
)
from .multiweb_overlap import (
    OBS_MIN_CONTRA, _backbone, add_overlap_forgery, classify, region_obstruction,
)

MODEL_SEEDS = range(10_000, 10_200)     # declared-process sampling (note §5)
HELD_OUT = range(2000, 2050)            # V1-V3, untouched by any prior run
RETRO = range(1000, 1050)               # V4, the frozen E2b block (disclosed)

# Discovered during bring-up: the frozen generate() CRASHES on worlds where
# an eligible community has exactly 3 visible members and an episode draws
# size 4 (multiweb.py:122, rng.sample larger than population). No frozen
# artifact is affected — a crashing seed can never have produced a result —
# so every previously benched block is implicitly conditioned on the process
# completing. The validator applies the SAME conditioning: crashing seeds
# are skipped and RECORDED, never silently dropped. Fixing generate() is a
# bench amendment that needs its own pre-registration; not done here.
SKIPPED: dict[str, list] = {"model": [], "held_out": [], "retro": []}


def _generate_or_skip(seed: int, tag: str):
    try:
        return generate(seed)
    except ValueError:
        SKIPPED[tag].append(seed)
        return None


# ------------------------------------------------------------ model quantities

def model_rates(seeds=MODEL_SEEDS) -> dict:
    """p_miss / delta_x per note §3: enumerate ALL intra- and cross-community
    pairs visible to each view of each declared-process world, against that
    web's backbone threshold. Absent edges count weight 0."""
    per_world_miss, per_world_x, thresholds = [], [], []
    valid, seed = 0, seeds.start
    while valid < len(seeds) and seed < seeds.start + 2 * len(seeds):
        world = _generate_or_skip(seed, "model")
        seed += 1
        if world is None:
            continue
        valid += 1
        com_of = {e: c for c, com in enumerate(world.communities) for e in com}
        for j in range(K_VIEWS):
            G = world.webs[j]
            bb = _backbone(G)
            thresholds.append(bb)
            nodes = [n for n in G.nodes if world.hidden[j].get(n) is not None]
            miss = tot_i = strong_x = tot_x = 0
            for a in range(len(nodes)):
                for b in range(a + 1, len(nodes)):
                    u, v = nodes[a], nodes[b]
                    w = G[u][v]["weight"] if G.has_edge(u, v) else 0
                    same = com_of[world.hidden[j][u]] == com_of[world.hidden[j][v]]
                    if same:
                        tot_i += 1
                        miss += w < bb
                    else:
                        tot_x += 1
                        strong_x += w >= bb
            per_world_miss.append(miss / tot_i)
            per_world_x.append(strong_x / tot_x)
    q = lambda vals, p: sorted(vals)[int(p * (len(vals) - 1))]
    return {"n_world_views": len(per_world_miss),
            "p_miss_mean": statistics.mean(per_world_miss),
            "p_miss_q025": q(per_world_miss, 0.025),
            "p_miss_q975": q(per_world_miss, 0.975),
            "delta_x_mean": statistics.mean(per_world_x),
            "delta_x_q975": q(per_world_x, 0.975),
            "threshold_mean": statistics.mean(thresholds),
            "p_miss_samples": per_world_miss}      # F, for the v2 mixture (note §9)


# ------------------------------------------------------- per-block measurement

def _pipeline(seed: int, tag: str = "held_out") -> dict | None:
    """The frozen E2b pipeline, opened up for edge-level reading. Returns
    None (recorded in SKIPPED) where the frozen generator crashes."""
    world = _generate_or_skip(seed, tag)
    if world is None:
        return None
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
    ba = info.get("bridged_a", frozenset())
    bb_ = info.get("bridged_b", frozenset())
    merged_ids = {id(r) for r in rows if r["view"] == 0
                  and len(r["region"] & ba) >= CORR_MIN_IMG
                  and len(r["region"] & bb_) >= CORR_MIN_IMG}
    true_rows = [r for r in rows
                 if not (r["view"] == 0 and r["region"] & world.forged)
                 and id(r) not in merged_ids
                 and majority_com(r) in multi_covered]
    merged_rows = [r for r in rows if id(r) in merged_ids]
    return {"world": world, "info": info, "maps": maps,
            "true_rows": true_rows, "merged_rows": merged_rows}


def _edges_of(row, world, maps):
    """Checkable strong edges of a region into each other view, mirroring
    obstruction_pair exactly, with mapping-correctness and anchor tags."""
    i = row["view"]
    GA = world.webs[i]
    bb_a = _backbone(GA)
    out = []
    for j in range(K_VIEWS):
        if j == i:
            continue
        m = maps[(i, j)]
        GB = world.webs[j]
        if GA.number_of_edges() == 0 or GB.number_of_edges() == 0:
            continue
        bb_b = _backbone(GB)
        if (i, j) in world.anchors:
            seedmap = world.anchors[(i, j)]
        else:
            seedmap = {v: u for u, v in world.anchors[(j, i)].items()}

        def ok(u):
            ei, ej = world.hidden[i].get(u), world.hidden[j].get(m[u])
            return ei is not None and ei == ej
        for u in row["region"]:
            if u not in m or u not in GA:
                continue
            for v, d in GA[u].items():
                if v not in row["region"] or not (u < v) or v not in m:
                    continue
                if d["weight"] < bb_a:
                    continue
                mu, mv = m[u], m[v]
                contra = not (GB.has_edge(mu, mv) and GB[mu][mv]["weight"] >= bb_b)
                out.append({"j": j, "u": u, "v": v, "contra": contra,
                            "correct": ok(u) and ok(v),
                            "anchored": u in seedmap and v in seedmap})
    return out


def edge_rates(block, tag="held_out") -> dict:
    """V1: per-edge contradiction rate on TRUE regions, split by mapping
    correctness (the correct-endpoint rate tests p_miss; the wrong-endpoint
    counts are the measured epsilon_map)."""
    cc = cn = wc = wn = 0
    per_region_m = []          # (list of m_j, observed contra>=2?) for V2
    obs_false = obs_false_correct_only = n_true = 0
    for seed in block:
        p = _pipeline(seed, tag)
        if p is None:
            continue
        for row in p["true_rows"]:
            n_true += 1
            edges = _edges_of(row, p["world"], p["maps"])
            m_by_j = Counter(e["j"] for e in edges if e["correct"])
            per_region_m.append(sorted(m_by_j.values()))
            contra_by_j = Counter(e["j"] for e in edges if e["contra"])
            correct_contra_by_j = Counter(e["j"] for e in edges
                                          if e["contra"] and e["correct"])
            if contra_by_j and max(contra_by_j.values()) >= OBS_MIN_CONTRA:
                obs_false += 1
            if correct_contra_by_j and max(correct_contra_by_j.values()) >= OBS_MIN_CONTRA:
                obs_false_correct_only += 1
            for e in edges:
                if e["correct"]:
                    cn += 1
                    cc += e["contra"]
                else:
                    wn += 1
                    wc += e["contra"]
    return {"n_true_regions": n_true,
            "checkable_correct": cn, "contradicted_correct": cc,
            "edge_rate_correct": cc / cn if cn else None,
            "checkable_wrong_mapped": wn, "contradicted_wrong_mapped": wc,
            "epsilon_map_edges": wc,
            "observed_false_obstructed": obs_false,
            "observed_false_obstructed_correct_only": obs_false_correct_only,
            "_per_region_m": per_region_m}


def region_alpha(edge_out: dict, p_miss: float) -> dict:
    """V2: predicted falsely-obstructed count from each region's measured
    m_j and the model p_miss: sum of P(max_j Bin(m_j, p_miss) >= 2)."""
    def tail2(m, p):
        return 1 - (1 - p) ** m - m * p * (1 - p) ** (m - 1)
    pred = 0.0
    for ms in edge_out["_per_region_m"]:
        keep = 1.0
        for m in ms:
            keep *= 1 - tail2(m, p_miss)
        pred += 1 - keep
    return {"predicted_false_obstructed": round(pred, 2),
            "observed_false_obstructed": edge_out["observed_false_obstructed"],
            "observed_correct_only": edge_out["observed_false_obstructed_correct_only"]}


def detection(block, tag="held_out") -> dict:
    """V3: merged regions with >= 2 correctly-anchored checkable bridges are
    obstructed; per-checkable-bridge contradiction rate."""
    eligible = obstructed = 0
    bridges = bridges_contra = 0
    constructible = 0
    for seed in block:
        p = _pipeline(seed, tag)
        if p is None or not p["info"].get("constructible") or not p["merged_rows"]:
            continue
        constructible += 1
        row = max(p["merged_rows"], key=lambda r: r["contra"])
        ba, bb_ = p["info"]["bridged_a"], p["info"]["bridged_b"]
        edges = _edges_of(row, p["world"], p["maps"])
        br = [e for e in edges
              if (e["u"] in ba and e["v"] in bb_) or (e["u"] in bb_ and e["v"] in ba)]
        good = [e for e in br if e["correct"] and e["anchored"]]
        bridges += len(good)
        bridges_contra += sum(e["contra"] for e in good)
        if len(good) >= 2:
            eligible += 1
            obstructed += row["contra"] >= OBS_MIN_CONTRA
    return {"constructible": constructible, "eligible_ge2_bridges": eligible,
            "obstructed": obstructed,
            "obstructed_rate": obstructed / eligible if eligible else None,
            "checkable_bridges": bridges,
            "bridge_contra_rate": bridges_contra / bridges if bridges else None}


# --------------------------------------------- v2 amendment (note §9)

def _tail2(m, p):
    return 1 - (1 - p) ** m - m * p * (1 - p) ** (m - 1)


def region_alpha_v2(edge_out: dict, f_samples: list) -> dict:
    """Note §9: the rate-mixture false-alarm bound. Primary (gating): one
    p ~ F shared across a region's views. Secondary (reported): independent
    per-view draws. F = raw per-world-view p_miss samples from the declared
    process; no test-block artifact is an input."""
    pred_shared = pred_indep = 0.0
    n = len(f_samples)
    for ms in edge_out["_per_region_m"]:
        s = 0.0
        for p in f_samples:
            keep = 1.0
            for m in ms:
                keep *= 1 - _tail2(m, p)
            s += 1 - keep
        pred_shared += s / n
        keep = 1.0
        for m in ms:
            keep *= 1 - sum(_tail2(m, p) for p in f_samples) / n
        pred_indep += 1 - keep
    return {"predicted_shared_p": round(pred_shared, 2),
            "predicted_indep_p": round(pred_indep, 2),
            "observed_correct_only": edge_out["observed_false_obstructed_correct_only"],
            "observed_total": edge_out["observed_false_obstructed"]}


def verdict_v2(model: dict, e: dict, ra2: dict, det: dict) -> dict:
    """Note §9 gates, verbatim: V2' (mixture bound vs correct-only observed,
    x2.5), V1 replication (original band), V3 replication."""
    v1_lo = model["p_miss_q025"] / 2
    v1_hi = model["p_miss_q975"] * 2
    v1 = (e["edge_rate_correct"] is not None
          and v1_lo <= e["edge_rate_correct"] <= v1_hi)
    pred, obs = ra2["predicted_shared_p"], ra2["observed_correct_only"]
    v2 = pred / 2.5 <= obs <= pred * 2.5
    v3 = (det["obstructed_rate"] is not None and det["obstructed_rate"] >= 0.98
          and det["bridge_contra_rate"] is not None
          and det["bridge_contra_rate"] >= 0.99)
    return {"V2prime_mixture": {"pass": v2,
                                "band": [round(pred / 2.5, 2), round(pred * 2.5, 2)],
                                "predicted_shared_p": pred,
                                "predicted_indep_p": ra2["predicted_indep_p"],
                                "observed_correct_only": obs,
                                "observed_total": ra2["observed_total"]},
            "V1_replication": {"pass": v1, "band": [round(v1_lo, 5), round(v1_hi, 5)],
                               "observed": round(e["edge_rate_correct"], 5)},
            "V3_replication": {"pass": v3,
                               "obstructed_rate": det["obstructed_rate"],
                               "bridge_contra_rate": round(det["bridge_contra_rate"], 4)},
            "discharged": v1 and v2 and v3}


def run_v2(out_dir: Path) -> dict:
    model = model_rates()
    f = model["p_miss_samples"]
    blocks = {}
    for name, block, tag in (("fresh_3000", range(3000, 3050), "fresh_3000"),
                             ("retro_2000", HELD_OUT, "retro_2000")):
        SKIPPED.setdefault(tag, [])
        e = edge_rates(block, tag)
        ra2 = region_alpha_v2(e, f)
        det = detection(block, tag)
        e.pop("_per_region_m")
        blocks[name] = {"edges": e, "region_alpha_v2": ra2, "detection": det}
    fresh = blocks["fresh_3000"]
    v = verdict_v2(model, fresh["edges"], fresh["region_alpha_v2"],
                   fresh["detection"])
    out = {"model": {k: v_ for k, v_ in model.items() if k != "p_miss_samples"},
           "blocks": blocks, "verdict": v,
           "skipped_crashing_seeds": SKIPPED}
    (out_dir / "v2-validation.json").write_text(json.dumps(out, indent=2))
    h, r = blocks["fresh_3000"], blocks["retro_2000"]
    (out_dir / "v2-report.md").write_text("\n".join([
        "# The P2 discharge, amendment v2 — validation results", "",
        "Pre-registered: docs/p2-discharge.md §9 (committed before this code "
        "or any computation touched seed block 3000–3049). Gating block: "
        "3000–3049 (virgin). The 2000 block is V2-retrodiction, disclosed.", "",
        "| check | fresh 3000 (gating) | 2000 (retro) |", "|---|---|---|",
        f"| edge rate, correct endpoints | {h['edges']['edge_rate_correct']:.4f} "
        f"({h['edges']['contradicted_correct']}/{h['edges']['checkable_correct']}) | "
        f"{r['edges']['edge_rate_correct']:.4f} "
        f"({r['edges']['contradicted_correct']}/{r['edges']['checkable_correct']}) |",
        f"| α₂ predicted (shared / indep) vs observed correct-only | "
        f"{h['region_alpha_v2']['predicted_shared_p']} / "
        f"{h['region_alpha_v2']['predicted_indep_p']} vs "
        f"{h['region_alpha_v2']['observed_correct_only']} | "
        f"{r['region_alpha_v2']['predicted_shared_p']} / "
        f"{r['region_alpha_v2']['predicted_indep_p']} vs "
        f"{r['region_alpha_v2']['observed_correct_only']} |",
        f"| detection: obstructed / per-bridge | "
        f"{h['detection']['obstructed_rate']:.2f} / {h['detection']['bridge_contra_rate']:.4f} | "
        f"{r['detection']['obstructed_rate']:.2f} / {r['detection']['bridge_contra_rate']:.4f} |",
        "", f"Verdict (fresh block): ```{json.dumps(v, indent=1)}```", ""]))
    return out


# ------------------------------------------------------------------- verdict

def verdict(model: dict, e: dict, ra: dict, det: dict) -> dict:
    """The note §5 tolerances, applied verbatim."""
    v1_lo = model["p_miss_q025"] / 2
    v1_hi = model["p_miss_q975"] * 2
    v1 = (e["edge_rate_correct"] is not None
          and v1_lo <= e["edge_rate_correct"] <= v1_hi)
    pred, obs = ra["predicted_false_obstructed"], ra["observed_false_obstructed"]
    v2 = pred / 2.5 <= obs <= pred * 2.5
    v3 = (det["obstructed_rate"] is not None and det["obstructed_rate"] >= 0.98
          and det["bridge_contra_rate"] is not None
          and det["bridge_contra_rate"] >= 0.99)
    return {"V1_edge_rate": {"pass": v1, "band": [round(v1_lo, 5), round(v1_hi, 5)],
                             "observed": round(e["edge_rate_correct"], 5)},
            "V2_region_count": {"pass": v2, "band": [round(pred / 2.5, 2), round(pred * 2.5, 2)],
                                "predicted": pred, "observed": obs},
            "V3_detection": {"pass": v3,
                             "obstructed_rate": det["obstructed_rate"],
                             "bridge_contra_rate": round(det["bridge_contra_rate"], 4)},
            "discharged": v1 and v2 and v3}


# ------------------------------------------------------------------ reporting

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", action="store_true",
                    help="run ONLY the note-§9 v2 amendment validation "
                         "(fresh block 3000–3049 gating; 2000 as "
                         "retrodiction); writes v2-validation.json + "
                         "v2-report.md, leaves v1 outputs untouched")
    ap.add_argument("--out", default="results/p2-discharge")
    args = ap.parse_args(argv)

    if args.v2:
        o = Path(args.out)
        o.mkdir(parents=True, exist_ok=True)
        out = run_v2(o)
        print(json.dumps(out["verdict"], indent=2))
        print("skipped:", out["skipped_crashing_seeds"])
        return

    t0 = time.time()
    model = model_rates()
    blocks = {}
    for name, block in (("held_out_2000", HELD_OUT), ("retro_1000", RETRO)):
        tag = "held_out" if name.startswith("held") else "retro"
        e = edge_rates(block, tag)
        ra = region_alpha(e, model["p_miss_mean"])
        det = detection(block, tag)
        e.pop("_per_region_m")
        blocks[name] = {"edges": e, "region_alpha": ra, "detection": det}
    v = verdict(model,
                {**blocks["held_out_2000"]["edges"],
                 "edge_rate_correct": blocks["held_out_2000"]["edges"]["edge_rate_correct"]},
                blocks["held_out_2000"]["region_alpha"],
                blocks["held_out_2000"]["detection"])
    out = {"model": model, "blocks": blocks, "verdict": v,
           "skipped_crashing_seeds": SKIPPED,
           "elapsed_s": round(time.time() - t0, 1)}

    o = Path(args.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "validation.json").write_text(json.dumps(out, indent=2))
    lines = [
        "# The P2 discharge — validation results", "",
        "Pre-registered: docs/p2-discharge.md (note and tolerances committed "
        "before this script existed). Model quantities from the declared "
        "process, seeds 10000–10199; V1–V3 on the HELD-OUT block 2000–2049; "
        "the frozen block 1000–1049 is retrodiction (V4), disclosed as such.", "",
        f"Model: p_miss = {model['p_miss_mean']:.4f} "
        f"[{model['p_miss_q025']:.4f}, {model['p_miss_q975']:.4f}], "
        f"delta_x = {model['delta_x_mean']:.5f}.", "",
        "| check | held-out (V1–V3) | retro (V4) |", "|---|---|---|"]
    h, r = blocks["held_out_2000"], blocks["retro_1000"]
    lines += [
        f"| edge rate, correct endpoints | {h['edges']['edge_rate_correct']:.4f} "
        f"({h['edges']['contradicted_correct']}/{h['edges']['checkable_correct']}) | "
        f"{r['edges']['edge_rate_correct']:.4f} "
        f"({r['edges']['contradicted_correct']}/{r['edges']['checkable_correct']}) |",
        f"| epsilon_map contradicted edges | {h['edges']['epsilon_map_edges']} | "
        f"{r['edges']['epsilon_map_edges']} |",
        f"| false-obstructed: predicted vs observed | "
        f"{h['region_alpha']['predicted_false_obstructed']} vs "
        f"{h['region_alpha']['observed_false_obstructed']} | "
        f"{r['region_alpha']['predicted_false_obstructed']} vs "
        f"{r['region_alpha']['observed_false_obstructed']} |",
        f"| detection: obstructed rate / per-bridge | "
        f"{h['detection']['obstructed_rate']:.2f} / {h['detection']['bridge_contra_rate']:.4f} | "
        f"{r['detection']['obstructed_rate']:.2f} / {r['detection']['bridge_contra_rate']:.4f} |",
        "", f"Verdict (held-out): ```{json.dumps(v, indent=1)}```", ""]
    (o / "report.md").write_text("\n".join(lines))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
