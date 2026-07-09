"""el — reading & writing (PL): language as a separate, one-way-dependent web.

The standalone language phase (`docs/spec-read-write.md`), off the numbered
dev-doc roadmap (whose P9 is Perception & data feed). Runs the six layers on the
synthetic corpus and reports the headline metrics: segmentation degradation
curve, closed-class discovery, grounding up to the concept web's automorphism
orbits, the ostension cascade, single-exposure fast-mapping, and the
write = inverse + read-back adjunction laws.

Writes results/el_readwrite.csv and results/el_readwrite.png.
Run: ``poetry run python experiments/el_readwrite.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner import language as L
from relweblearner.datasets import language as D

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
N_UTT = 300


def _segmentation_curve():
    rows = []
    for shared in range(len(D._STRESS_SWAPS) + 1):
        word = D.stress_words(shared)
        units, gold = D.stream_of(N_UTT, word=word, seed=3)
        _words, bounds = L.segment(units)
        prec, rec = L.boundary_prf(bounds, gold, len(units))
        rows.append((shared, prec, rec))
    return rows


def run():
    # ---- L1/L2: segment the clean stream, discover the closed class
    units, gold = D.stream_of(N_UTT, seed=3)
    words, bounds = L.segment(units)
    prec, rec = L.boundary_prf(bounds, gold, len(units))
    lex_exact = set(words) == D.surface_forms()
    frame_words = L.discover_frame_words(words)
    utts = L.chunk(words, frame_words)
    regularity = L._frame_regularity(utts, frame_words)
    markers_truth = {D.WORD["HC"], D.WORD["GO"]}

    print("=" * 68)
    print("A/B. SEGMENTATION + CLOSED-CLASS DISCOVERY (from raw syllables)")
    print("=" * 68)
    print(f"boundary precision {prec:.2f}, recall {rec:.2f}; "
          f"lexicon {len(set(words))} types, exact recovery: {lex_exact}")
    curve = _segmentation_curve()
    print("degradation curve (precision as value-words reuse fruit syllables):")
    for shared, p, r in curve:
        print(f"  shared={shared}: precision {p:.2f}, recall {r:.2f}")
    print(f"closed class DISCOVERED (not given): {sorted(frame_words)} "
          f"== markers: {frame_words == markers_truth}; frame-shape {regularity:.0%}")

    # ---- L3: grounding by structure alone, up to automorphism orbits
    tok_web = L.token_web(utts, frame_words)
    con_edges = D.concept_edges()
    g0 = L.ground(tok_web, con_edges)
    acc0 = all(D.WORD[c] == t for t, c in g0.map.items())
    orbits_bf = [o for o in L.automorphism_orbits(con_edges) if len(o) > 1]
    orbit_concepts = {c for o in orbits_bf for c in o}
    unresolved = {c for _tt, cc in g0.orbits for c in cc}

    print("\n" + "=" * 68)
    print("C. GROUNDING BY STRUCTURE ALONE (up to automorphism orbits)")
    print("=" * 68)
    print(f"edge-type bijection: {g0.markers}")
    print(f"grounded uniquely {len(g0.map)}/11, all correct: {acc0}")
    print(f"unresolved set {sorted(unresolved)} == brute-force orbits "
          f"{sorted(sorted(o) for o in orbits_bf)}: {unresolved == orbit_concepts}")
    print("-> resolution stops EXACTLY at the concept web's automorphism orbits")
    print("   (the gavagai limit): no text volume separates interchangeable concepts.")

    # ---- L4: ostension cascade (one pointing per orbit)
    cascade = [len(g0.map)]
    g1 = L.ground(tok_web, con_edges, seeds={"bavu": "mango"})
    cascade.append(len(g1.map))
    g2 = L.ground(tok_web, con_edges, seeds={"bavu": "mango", "runi": "apple"})
    cascade.append(len(g2.map))
    acc2 = all(D.WORD[c] == t for t, c in g2.map.items())

    print("\n" + "=" * 68)
    print("D. OSTENSION: one pointing per orbit; the partner grounds for free")
    print("=" * 68)
    print(f"ostension budget = #orbits = {L.ostension_budget(g0.orbits)}")
    print(f"grounded cascade {cascade[0]}/11 -> {cascade[1]}/11 -> {cascade[2]}/11, "
          f"all correct: {acc2}")

    # ---- L5: fast-map a novel word from one exposure
    relations = {"HC": dict(D.HC), "GO": dict(D.GO)}
    relations["HC"]["fig"] = "red"
    relations["GO"]["fig"] = "herb"
    con_edges2 = {r: set(t.items()) for r, t in relations.items()}
    grounding = dict(g2.map)
    markers = g2.markers
    lexicon = {t: D.SYL[t] for t in grounding}
    for m in frame_words:
        lexicon[m] = D.SYL[m]
    novel = D.SYL[D.WORD["HC"]] + ["wu", "mi"] + D.SYL[D.WORD["red"]]
    new_word, concept, cands = L.fast_map(novel, lexicon, grounding, markers, con_edges2)
    grounding[new_word] = concept

    print("\n" + "=" * 68)
    print("E. FAST-MAPPING A NOVEL WORD (one exposure, subtraction + mutual excl.)")
    print("=" * 68)
    print(f"perception adds a fig (red, herb); novel word segmented by subtraction "
          f"-> '{new_word}'")
    print(f"fast-mapped '{new_word}' -> {concept} (candidates {cands})")

    # ---- L6: writing = inverse + read-back; refusal + adjunction laws
    inv0 = L.invert(g0.map)
    marker_inv = {r: t for t, r in markers.items()}
    _d, pre_verdict = L.write(
        ("GO", "mango", "tree"), inv0, marker_inv, lambda u: L.read(u, g0.map, g0.markers)
    )
    report = L.adjunction_report(relations, grounding, markers)

    print("\n" + "=" * 68)
    print("F. WRITING = INVERSE MAP + READ-BACK BEFORE COMMIT")
    print("=" * 68)
    print(f"pre-ostension write of an orbit word (mango): {pre_verdict}")
    print(f"adjunction over the full expressible set ({report['expressible']} facts): "
          f"read(write)={report['write_read_ok']}, write(read)={report['read_write_ok']}, "
          f"violation rate {report['violation_rate']:.2f}")

    # ---- record
    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "el_readwrite.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["seg_precision_clean", f"{prec:.3f}"])
        w.writerow(["seg_recall_clean", f"{rec:.3f}"])
        w.writerow(["lexicon_exact", int(lex_exact)])
        for shared, p, _r in curve:
            w.writerow([f"seg_precision@shared{shared}", f"{p:.3f}"])
        w.writerow(["frame_class_discovered", int(frame_words == markers_truth)])
        w.writerow(["grounded_structural", f"{len(g0.map)}/11"])
        w.writerow(["orbits_match_bruteforce", int(unresolved == orbit_concepts)])
        w.writerow(["ostension_budget", L.ostension_budget(g0.orbits)])
        w.writerow(["grounded_after_ostension", f"{cascade[-1]}/11"])
        w.writerow(["fastmap_correct", int(concept == "fig")])
        w.writerow(["adjunction_violation_rate", f"{report['violation_rate']:.3f}"])
    _plot(curve, cascade, os.path.join(RESULTS, "el_readwrite.png"))
    print(f"\nwrote {csv_path}")


def _plot(curve, cascade, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    shared = [c[0] for c in curve]
    ax1.plot(shared, [c[1] for c in curve], "-o", color="#c0392b", label="boundary precision")
    ax1.plot(shared, [c[2] for c in curve], "-s", color="#2c3e50", label="boundary recall")
    ax1.set_title("L1 segmentation: a measurable ceiling\n(precision degrades as words share syllables)")
    ax1.set_xlabel("value-words reusing fruit syllables")
    ax1.set_ylabel("score")
    ax1.set_ylim(0, 1.05)
    ax1.set_xticks(shared)
    ax1.legend(fontsize=8)

    n_ost = list(range(len(cascade)))
    ax2.plot(n_ost, cascade, "-o", color="#2c3e50")
    ax2.axhline(11, ls="--", color="#7f8c8d", lw=1)
    for x, y in zip(n_ost, cascade):
        ax2.annotate(f"{y}/11", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8)
    ax2.set_title("L3/L4 grounding: structural limit + ostension\n(one pointing per orbit; partner grounds free)")
    ax2.set_xlabel("ostension events")
    ax2.set_ylabel("content words grounded")
    ax2.set_xticks(n_ost)
    ax2.set_ylim(0, 12)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
