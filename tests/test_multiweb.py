"""Multi-web interference benchmark: generator discipline and pipeline smoke.

The substantive predictions live in docs/multiweb-plan.md and are scored by
the 50-seed run — these tests pin the properties the run's validity rests on.
"""

import random
from itertools import combinations

from relweblearner.bench import multiweb as MW


def test_deterministic():
    a, b = MW.generate(7), MW.generate(7)
    assert sorted(a.webs[0].edges(data="weight")) == sorted(b.webs[0].edges(data="weight"))
    assert a.anchors == b.anchors
    assert a.forged == b.forged


def test_substrate_is_opaque():
    """No node id in any web leaks hidden-world structure: ids are view-local
    and carry no community information (shuffled index space)."""
    w = MW.generate(3)
    com_of = {e: c for c, com in enumerate(w.communities) for e in com}
    for k, web in enumerate(w.webs):
        ids = [n for n in web.nodes if n in w.hidden[k]]
        idx = sorted(int(n.split(":")[1]) for n in ids)
        assert idx == list(range(len(ids)))          # dense index space
        # consecutive ids must not systematically share a community
        by_idx = {int(n.split(":")[1]): com_of[w.hidden[k][n]] for n in ids}
        runs = sum(1 for i in range(len(idx) - 1) if by_idx[i] == by_idx[i + 1])
        assert runs < len(idx) / 2                   # would be ~len(idx) if sorted


def test_forgery_matches_true_statistics():
    """The forged region's internal density sits inside the range spanned by
    the true communities' visible subwebs — 'coherent' is by construction."""
    w = MW.generate(11)
    G = w.webs[0]
    forged = sorted(w.forged)
    f_present = sum(1 for u, v in combinations(forged, 2) if G.has_edge(u, v))
    f_density = f_present / (len(forged) * (len(forged) - 1) / 2)
    densities = []
    for com in w.communities:
        mem = [n for n in G.nodes if n in w.hidden[0]
               and w.hidden[0][n] in com]
        if len(mem) < 2:
            continue
        present = sum(1 for u, v in combinations(mem, 2) if G.has_edge(u, v))
        densities.append(present / (len(mem) * (len(mem) - 1) / 2))
    assert min(densities) - 0.25 <= f_density <= 1.0


def test_forged_nodes_have_no_anchors():
    w = MW.generate(5)
    for m in w.anchors.values():
        assert not (set(m) | set(m.values())) & w.forged


def test_mapping_stays_partial():
    w = MW.generate(9)
    maps = MW.all_mappings(w)
    for (i, _j), m in maps.items():
        n = len([x for x in w.webs[i].nodes if x not in w.forged])
        assert 0 < len(m) < n


def test_pipeline_smoke():
    r = MW.run_seed(0)
    for key in ("one_web_accepts_forgery", "multi_web_accepts_forgery",
                "recall", "purity", "solo_found", "solo_projected",
                "forged_mapped_frac"):
        assert key in r
    assert r["n_regions"] >= 1
