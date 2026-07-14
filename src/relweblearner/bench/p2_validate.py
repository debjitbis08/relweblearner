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


# --------------------------------------------- v3 amendment (note §12)
# Direct simulation: no analytic composition, no pristine/mutated mismatch.
# The false-alarm behavior of the ACTUAL detector is measured by running the
# full frozen pipeline on the declared model block; world-level bootstrap
# predictive intervals carry all within-world clustering by construction.

V3_MODEL_SEEDS = range(10_000, 10_400)   # exactly as declared; crashers recorded
V3_FRESH = range(4000, 4050)             # virgin gating block
V3_BOOT_N = 20_000
V3_BOOT_SEED = 4242


def _world_stats(seed: int, tag: str) -> dict | None:
    """One world through the full frozen pipeline: false-obstruction and
    edge-level tallies for true regions, plus the per-view detection cell."""
    p = _pipeline(seed, tag)
    if p is None:
        return None
    world, maps = p["world"], p["maps"]
    st = {"n_true": 0, "false_obs_total": 0, "false_obs_correct_only": 0,
          "cc": 0, "cn": 0, "wc": 0, "wn": 0,
          "det_eligible": 0, "det_success": 0}
    for row in p["true_rows"]:
        st["n_true"] += 1
        edges = _edges_of(row, world, maps)
        contra_by_j = Counter(e["j"] for e in edges if e["contra"])
        correct_by_j = Counter(e["j"] for e in edges
                               if e["contra"] and e["correct"])
        if contra_by_j and max(contra_by_j.values()) >= OBS_MIN_CONTRA:
            st["false_obs_total"] += 1
        if correct_by_j and max(correct_by_j.values()) >= OBS_MIN_CONTRA:
            st["false_obs_correct_only"] += 1
        for e in edges:
            if e["correct"]:
                st["cn"] += 1
                st["cc"] += e["contra"]
            else:
                st["wn"] += 1
                st["wc"] += e["contra"]
    # detection, per-view and bridge-attributable (note §12 V3''')
    if p["info"].get("constructible") and p["merged_rows"]:
        row = max(p["merged_rows"], key=lambda r: r["contra"])
        ba, bb_ = p["info"]["bridged_a"], p["info"]["bridged_b"]
        good_by_j, contra_good_by_j = Counter(), Counter()
        for e in _edges_of(row, world, maps):
            is_br = ((e["u"] in ba and e["v"] in bb_)
                     or (e["u"] in bb_ and e["v"] in ba))
            if is_br and e["correct"] and e["anchored"]:
                good_by_j[e["j"]] += 1
                if e["contra"]:
                    contra_good_by_j[e["j"]] += 1
        elig = [j for j, n in good_by_j.items() if n >= 2]
        if elig:
            st["det_eligible"] = 1
            st["det_success"] = int(any(contra_good_by_j[j] >= OBS_MIN_CONTRA
                                        for j in elig))
    return st


def direct_model(seeds=V3_MODEL_SEEDS) -> list[dict]:
    """Note §12: per-world stats over EXACTLY the declared block."""
    SKIPPED.setdefault("v3_model", [])
    out = []
    for seed in seeds:
        st = _world_stats(seed, "v3_model")
        if st is not None:
            out.append(st)
    return out


def bootstrap_pi(worlds: list[dict], block_size: int = 50,
                 n: int = V3_BOOT_N, seed: int = V3_BOOT_SEED) -> dict:
    """Predictive intervals for a block's total false-obstruction count and
    pooled correct-endpoint edge rate. Two variants (round-2 referee,
    finding 2): the plain block bootstrap treats the model sample as the
    known distribution; the PREDICTION-ERROR bootstrap outer-resamples the
    model worlds first, so estimation uncertainty from the finite model
    sample is included. The prediction-error intervals are the GATING ones;
    the plain ones are reported for continuity with the frozen v3 artifact."""
    import random as _random

    def _draw(rng, pool):
        block = [pool[rng.randrange(len(pool))] for _ in range(block_size)]
        cn = sum(w["cn"] for w in block)
        return (sum(w["false_obs_total"] for w in block),
                sum(w["cc"] for w in block) / cn if cn else 0.0)

    q = lambda vals, p: vals[min(len(vals) - 1, int(p * len(vals)))]
    out = {}
    for name, outer in (("plain", False), ("pe", True)):
        rng = _random.Random(seed)
        counts, rates = [], []
        for _ in range(n):
            pool = ([worlds[rng.randrange(len(worlds))]
                     for _ in range(len(worlds))] if outer else worlds)
            c, r = _draw(rng, pool)
            counts.append(c)
            rates.append(r)
        counts.sort()
        rates.sort()
        out[f"count_pi99_{name}"] = [q(counts, 0.005), q(counts, 0.995)]
        out[f"rate_pi99_{name}"] = [round(q(rates, 0.005), 5),
                                    round(q(rates, 0.995), 5)]
        if name == "pe":
            out["count_mean"] = round(statistics.mean(counts), 2)
            out["rate_mean"] = round(statistics.mean(rates), 5)
    return out


def fresh_block_v3(block, tag: str) -> dict:
    """The gating measurements on a 50-seed block."""
    SKIPPED.setdefault(tag, [])
    worlds = [st for seed in block
              if (st := _world_stats(seed, tag)) is not None]
    cn = sum(w["cn"] for w in worlds)
    wn = sum(w["wn"] for w in worlds)
    wc = sum(w["wc"] for w in worlds)
    elig = sum(w["det_eligible"] for w in worlds)
    return {"n_worlds": len(worlds),
            "n_true": sum(w["n_true"] for w in worlds),
            "false_obs_total": sum(w["false_obs_total"] for w in worlds),
            "false_obs_correct_only": sum(w["false_obs_correct_only"] for w in worlds),
            "edge_rate_correct": round(sum(w["cc"] for w in worlds) / cn, 5) if cn else None,
            "checkable_correct": cn,
            "eps_map_rate": (round(wc / wn, 5) if wn else None),
            # DESCRIPTIVE zero-cell figure only (round-2 referee, finding 3):
            # wrong-mapped edges share nodes and worlds, so 3/n is not a
            # bound here; the gating verdict absorbs mapping errors via the
            # total false-obstruction count.
            "eps_map_zero_cell_descriptive": (round(3 / wn, 5)
                                              if wn and wc == 0 else None),
            "detection_eligible": elig,
            "detection_success": sum(w["det_success"] for w in worlds),
            "detection_rate": (round(sum(w["det_success"] for w in worlds) / elig, 4)
                               if elig else None)}


def verdict_v3(pi: dict, fresh: dict, model_eligible: int = 0,
               model_success: int = 0) -> dict:
    """Note §12 gates, with the round-2 corrections: gating intervals are
    the prediction-error bootstrap's; detection carries a world-level
    zero-failure upper bound (worlds are iid by construction, so the
    rule of three is legitimate at world level), never beta = 0."""
    v2 = pi["count_pi99_pe"][0] <= fresh["false_obs_total"] <= pi["count_pi99_pe"][1]
    v1 = pi["rate_pi99_pe"][0] <= fresh["edge_rate_correct"] <= pi["rate_pi99_pe"][1]
    v3 = fresh["detection_rate"] is not None and fresh["detection_rate"] >= 0.98
    beta_upper = (round(3 / model_eligible, 5)
                  if model_eligible and model_success == model_eligible else None)
    return {"V2ppp_count": {"pass": v2, "pi99_pe": pi["count_pi99_pe"],
                            "pi99_plain": pi["count_pi99_plain"],
                            "predicted_mean": pi["count_mean"],
                            "observed": fresh["false_obs_total"]},
            "V1ppp_rate": {"pass": v1, "pi99_pe": pi["rate_pi99_pe"],
                           "pi99_plain": pi["rate_pi99_plain"],
                           "predicted_mean": pi["rate_mean"],
                           "observed": fresh["edge_rate_correct"]},
            "V3ppp_detection": {"pass": v3,
                                "eligible": fresh["detection_eligible"],
                                "rate": fresh["detection_rate"],
                                "beta_upper_rule3_world_level": beta_upper},
            "discharged_measured_tier": v1 and v2 and v3}


def run_v3(out_dir: Path) -> dict:
    worlds = direct_model()
    pi = bootstrap_pi(worlds)
    model_summary = {
        "n_worlds": len(worlds),
        "declared_block": [V3_MODEL_SEEDS.start, V3_MODEL_SEEDS.stop - 1],
        "false_obs_rate_per_region": round(
            sum(w["false_obs_total"] for w in worlds)
            / sum(w["n_true"] for w in worlds), 5),
        "pooled_edge_rate": round(
            sum(w["cc"] for w in worlds) / sum(w["cn"] for w in worlds), 5),
        "eps_map_rate": round(
            sum(w["wc"] for w in worlds) / max(1, sum(w["wn"] for w in worlds)), 5),
        "detection": f"{sum(w['det_success'] for w in worlds)}"
                     f"/{sum(w['det_eligible'] for w in worlds)}",
        **pi}
    blocks = {}
    for name, block in (("fresh_4000", V3_FRESH),
                        ("retro_3000", range(3000, 3050)),
                        ("retro_2000", range(2000, 2050)),
                        ("retro_1000", range(1000, 1050))):
        blocks[name] = fresh_block_v3(block, f"v3_{name}")
    v = verdict_v3(pi, blocks["fresh_4000"],
                   model_eligible=sum(w["det_eligible"] for w in worlds),
                   model_success=sum(w["det_success"] for w in worlds))
    out = {"model": model_summary, "blocks": blocks, "verdict": v,
           "skipped_crashing_seeds": {k: sorted(set(s)) for k, s in SKIPPED.items() if s}}
    (out_dir / "v3-validation.json").write_text(json.dumps(out, indent=2))
    rows = ["| block | false-obs total (correct-only) | edge rate | detection |",
            "|---|---|---|---|"]
    for name, b in blocks.items():
        rows.append(f"| {name} | {b['false_obs_total']} ({b['false_obs_correct_only']}) | "
                    f"{b['edge_rate_correct']} | {b['detection_success']}/{b['detection_eligible']} |")
    (out_dir / "v3-report.md").write_text("\n".join([
        "# The P2 discharge, amendment v3 — direct-simulation validation", "",
        "Pre-registered: docs/p2-discharge.md §12; round-2 referee "
        "corrections applied (§14): gating intervals are prediction-error "
        "bootstrap. SCOPE: the measured rates are properties of the declared "
        "E2b evaluation process — A1 worlds PLUS the pre-registered overlap-"
        "forgery intervention — not of A1 alone. Model = that full pipeline "
        "on the declared block "
        f"{model_summary['declared_block']} ({model_summary['n_worlds']} valid "
        "worlds); 99% predictive intervals by world-level bootstrap "
        f"(n={V3_BOOT_N}, seed {V3_BOOT_SEED}). Gating block: 4000–4049 "
        "(virgin). Other blocks are retrodiction.", "",
        f"Model: per-region false-obstruction rate "
        f"{model_summary['false_obs_rate_per_region']}, pooled edge rate "
        f"{model_summary['pooled_edge_rate']}, eps_map rate "
        f"{model_summary['eps_map_rate']}, detection {model_summary['detection']}; "
        f"block-count PI99 pe {pi['count_pi99_pe']} / plain "
        f"{pi['count_pi99_plain']} (mean {pi['count_mean']}), rate PI99 pe "
        f"{pi['rate_pi99_pe']} / plain {pi['rate_pi99_plain']}.", "",
        *rows, "",
        f"Verdict (fresh 4000): ```{json.dumps(v, indent=1)}```", ""]))
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
    ap.add_argument("--v3", action="store_true",
                    help="run ONLY the note-§12 v3 direct-simulation "
                         "validation (virgin block 4000–4049 gating); writes "
                         "v3-validation.json + v3-report.md")
    ap.add_argument("--v2", action="store_true",
                    help="run ONLY the note-§9 v2 amendment validation "
                         "(fresh block 3000–3049 gating; 2000 as "
                         "retrodiction); writes v2-validation.json + "
                         "v2-report.md, leaves v1 outputs untouched")
    ap.add_argument("--out", default="results/p2-discharge")
    args = ap.parse_args(argv)

    if args.v3:
        o = Path(args.out)
        o.mkdir(parents=True, exist_ok=True)
        out = run_v3(o)
        print(json.dumps(out["verdict"], indent=2))
        print("model:", json.dumps(out["model"], indent=2))
        print("skipped:", out["skipped_crashing_seeds"])
        return

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
