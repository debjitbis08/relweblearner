"""ec — curriculum reading (R2): frame induction and the book path.

The R2 rung of the reading ladder (``docs/spec-curriculum-reading.md``), built on
the PL language layer. Runs the pipeline on the synthetic pattern-book corpus and
reports the headline metrics: frame induction with coverage and the frontier, the
pollution failure-mode (grouping by length alone vs the dominance/anchor/rejection
fix), frontier-triggered template growth, grounding slot-fillers through frames
with iterative picture taps, single-page fast-mapping, and the path metrics
(assimilation, taps, frontier census, comprehension).

Writes results/ec_curriculum.csv and results/ec_curriculum.png.
Run: ``poetry run python experiments/ec_curriculum.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from relweblearner import curriculum as C
from relweblearner.datasets import curriculum as D

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def run():
    pages = D.base_corpus()

    # ---- L2′: frame induction, coverage, frontier
    frames = C.induce_frames([p["tokens"] for p in pages])
    cov, fr = C.coverage(pages, frames)
    census = C.frontier_census(fr)

    print("=" * 68)
    print("A. FRAME INDUCTION (dominance-thresholded skeletons)")
    print("=" * 68)
    for fid, f in frames.items():
        print(f"  induced {fid}: {' '.join(f.skeleton)}  (slots {list(f.slots)})")
    print(f"coverage {cov:.2f}; frontier (logged defects): {list(census.values())}")

    # ---- the required pollution failure-mode: length-grouping alone vs the fix
    poll = D.pollution_corpus()
    ptoks = [p["tokens"] for p in poll]
    broken = C.induce_frames(ptoks, min_group=5, dominance=1.0, min_anchors=0)
    bcov, bfr = C.coverage(poll, broken)
    fixed = C.induce_frames(ptoks, min_group=5, dominance=0.8, min_anchors=2)
    fcov, ffr = C.coverage(poll, fixed)

    print("\n" + "=" * 68)
    print("B. POLLUTION FAILURE-MODE (found the hard way)")
    print("=" * 68)
    print(f"length-grouping alone (exact-constancy, no anchor floor): "
          f"skeleton {list(broken.values())[0].skeleton}, coverage {bcov:.2f}, "
          f"frontier {len(bfr)} -> off-frame captions force-parsed (pollution)")
    print(f"dominance>=0.8 + anchor min + rejection: skeleton "
          f"{list(fixed.values())[0].skeleton}, coverage {fcov:.2f}, "
          f"frontier {len(ffr)} -> off-frame captions rejected")

    # ---- frontier as trigger: re-inducing on the frontier grows the next frame
    ft = D.frontier_trigger_corpus()
    grown, residual = C.grow_frames(ft)

    print("\n" + "=" * 68)
    print("C. FRONTIER AS TRIGGER (obstruction -> the next frame)")
    print("=" * 68)
    for fid, f in grown.items():
        print(f"  {fid}: {' '.join(f.skeleton)}")
    print(f"residual frontier: {[tuple(p['tokens']) for p in residual]}")

    # ---- grounding through frames + iterative picture taps
    tok_web = C.frame_token_web(pages, frames)
    con_edges = D.concept_edges()
    g, taps, trace = C.ground_with_taps(tok_web, con_edges)
    cascade = [0] + [n for (_c, n, _o) in trace]

    print("\n" + "=" * 68)
    print("D. SLOT GROUNDING + ITERATIVE PICTURE TAPS")
    print("=" * 68)
    for concept, grounded, left in trace:
        print(f"  tap on '{concept}' -> grounded {grounded}, orbits left {left}")
    print(f"final: {len(g.map)}/10 correct with {taps} taps "
          f"(orbit structure: a 4-orbit + three 2-orbits)")

    # ---- fast-map + assimilation + comprehension
    fact, prov, fid = C.fast_map_page(D.novel_page(), frames)
    rate, committed, _facts = C.assimilation_rate(pages, frames)
    comp = C.comprehension_check(committed, D.truth())

    print("\n" + "=" * 68)
    print("E. FAST-MAP, ASSIMILATION, COMPREHENSION")
    print("=" * 68)
    print(f"fast-map one page + one tap -> fact {fact}, provenance {prov} (via {fid})")
    print(f"assimilation {rate:.3f} facts/sentence; {len(committed)} committed "
          f"(>=2 book origins), all correct: "
          f"{all(D.HIDDEN_COLOUR[a] == c for a, c in committed)}")
    print(f"comprehension (answered from the web, not echoed): "
          f"{comp['correct']}/{comp['questions']} = {comp['accuracy']:.0%}")

    # ---- record
    os.makedirs(RESULTS, exist_ok=True)
    csv_path = os.path.join(RESULTS, "ec_curriculum.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["frames_induced", len(frames)])
        w.writerow(["coverage", f"{cov:.3f}"])
        w.writerow(["frontier_size", len(fr)])
        w.writerow(["pollution_broken_coverage", f"{bcov:.3f}"])
        w.writerow(["pollution_fixed_coverage", f"{fcov:.3f}"])
        w.writerow(["frontier_trigger_frames", len(grown)])
        w.writerow(["frontier_trigger_residual", len(residual)])
        w.writerow(["grounded", f"{len(g.map)}/10"])
        w.writerow(["taps", taps])
        w.writerow(["fastmap_fact", f"{fact[0]}->{fact[1]}"])
        w.writerow(["assimilation_rate", f"{rate:.3f}"])
        w.writerow(["comprehension_accuracy", f"{comp['accuracy']:.3f}"])
    _plot(cascade, taps, cov, fcov, os.path.join(RESULTS, "ec_curriculum.png"))
    print(f"\nwrote {csv_path}")


def _plot(cascade, taps, cov, fixed_cov, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    n_tap = list(range(len(cascade)))
    ax1.plot(n_tap, cascade, "-o", color="#2c3e50")
    ax1.axhline(10, ls="--", color="#7f8c8d", lw=1)
    for x, y in zip(n_tap, cascade):
        ax1.annotate(f"{y}/10", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8)
    ax1.set_title("Grounding through frames: iterative picture taps\n"
                  "(4-orbit + three 2-orbits -> 4 taps)")
    ax1.set_xlabel("picture taps (ostension)")
    ax1.set_ylabel("slot-fillers grounded")
    ax1.set_xticks(n_tap)
    ax1.set_ylim(0, 11)

    labels = ["induced\nframes", "length-\ngrouping\nalone"]
    ax2.bar(labels, [cov, fixed_cov], color=["#27ae60", "#c0392b"])
    ax2.set_title("Coverage: the dominance/anchor/rejection fix\n"
                  "(length-grouping alone over-generalizes)")
    ax2.set_ylabel("coverage (real frames)")
    ax2.set_ylim(0, 1.05)
    for i, v in enumerate([cov, fixed_cov]):
        ax2.annotate(f"{v:.2f}", (i, v), textcoords="offset points", xytext=(0, 6),
                     ha="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"wrote {path}")


if __name__ == "__main__":
    run()
