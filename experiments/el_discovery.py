"""el-discovery — grounding on DISCOVERED relation types (PL′; closes I3).

The concept web is handed to the learner LABEL-FREE. P2′ (disjointness
compression) recovers its relation types; the read/write grounding then aligns
frame words to the *discovered* types, and every relation type it uses traces
back to a discovery record. This pays the last structuralist debt the phase-1
verification named: relation types are no longer given at the language boundary.

Writes results/el_discovery.csv.
Run: ``poetry run python experiments/el_discovery.py``
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from relweblearner import language as L
from relweblearner.datasets import language as DL


def run():
    # 1. a raw syllable stream over the richer world (no boundaries, gensym words)
    word = DL.make_surface_forms()
    syl = DL.syllabify(word)
    units, _gold = DL.stream_of(600, facts=DL.rich_facts(), word=word, syl=syl, seed=3)
    words, _b = L.segment(units)
    fw = L.discover_frame_words(words)
    tok_web = L.token_web(L.chunk(words, fw), fw)

    # 2. hand the concept web in LABEL-FREE; P2′ recovers the relation types
    disc = L.discover_relation_types(DL.unlabeled_edges())

    # 3. ground on the DISCOVERED types (keys T1/T2, never HC/GO)
    g = L.ground(tok_web, disc.edges_by_type)
    correct = all(word[c] == t for t, c in g.map.items())
    trace = L.type_provenance(g.markers, disc)

    # 4. the same grounding under given labels, to show discovery only adds provenance
    given = {r: set(t.items()) for r, t in DL.RICH_RELATIONS.items()}
    same = L.ground(tok_web, given).map == g.map

    print("=" * 66)
    print("GROUNDING ON DISCOVERED TYPES (concept web handed in label-free)")
    print("=" * 66)
    print(f"P2′ recovered {len(disc.edges_by_type)} relation types from unlabeled edges: "
          f"{ {t: len(es) for t, es in disc.edges_by_type.items()} }")
    print(f"frame words discovered: {len(fw)}")
    print(f"grounded {len(g.map)} words uniquely, all correct: {correct}")
    print(f"markers align frame words to DISCOVERED types: {g.markers}")
    print(f"unresolved automorphism orbits: {len(g.orbits)}")
    print(f"type traceability: {trace}  -> no smuggled labels: "
          f"{all(v == 'discovered' for v in trace.values())}")
    print(f"discovery changes provenance, not the answer (map identical): {same}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "..", "results", "el_discovery.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["types_discovered", len(disc.edges_by_type)])
        w.writerow(["frame_words", len(fw)])
        w.writerow(["grounded_words", len(g.map)])
        w.writerow(["all_correct", int(correct)])
        w.writerow(["smuggled_labels", sum(1 for v in trace.values() if v != "discovered")])
        w.writerow(["map_identical_to_given", int(same)])
    print(f"\nwrote {path}")


if __name__ == "__main__":
    run()
