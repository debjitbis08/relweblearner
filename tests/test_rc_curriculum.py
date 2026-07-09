"""R2 acceptance: curriculum reading — frame induction and the book path.

The R2 rung of the reading ladder (``docs/spec-curriculum-reading.md``), built on
the PL language layer. Tests the spec's acceptance criteria: frame INDUCTION with
the required pollution failure-mode reproduced in CI (§1), frontier-triggered
template growth (§1), grounding slot-fillers through frames with iterative picture
taps and single-page fast-mapping (§2), the path metrics (§6), and the
disjoint-namespace / one-way-dependency CI properties inherited from
SPEC_READWRITE.
"""

from __future__ import annotations

import pytest

from relweblearner import curriculum as C
from relweblearner.datasets import curriculum as D


@pytest.fixture(scope="module")
def base():
    pages = D.base_corpus()
    frames = C.induce_frames([p["tokens"] for p in pages])
    return {"pages": pages, "frames": frames}


# ---------------------------------------------------- §0/§1 CI: namespaces / deps


def test_surface_and_concept_namespaces_are_disjoint(base):
    # nothing on the language side (the w:-prefixed token web) string-matches a
    # concept id — the disjoint-namespace property from SPEC_READWRITE §1.
    tok_web = C.frame_token_web(base["pages"], base["frames"])
    tok_nodes = {n for es in tok_web.values() for e in es for n in e}
    assert tok_nodes & D.concept_ids() == set()
    assert all(n.startswith("w:") for n in tok_nodes)


def test_module_is_one_way_dependent_on_concepts():
    # the curriculum module reads the concept web through the interface; it never
    # imports anything concept-side (enforced structurally, as for language.py).
    import inspect

    src = inspect.getsource(C)
    assert "datasets" not in src
    # and grounding cannot proceed without a concept web
    with pytest.raises((KeyError, ValueError, IndexError)):
        C.ground_with_taps({"names": {("w:a", "w:b")}}, {})


# ------------------------------------------------------------- §1 frame induction


def test_both_frames_recovered_and_offframe_in_frontier(base):
    frames = base["frames"]
    skeletons = {f.skeleton for f in frames.values()}
    assert skeletons == {("the", "_", "is", "_"), ("i", "see", "a", "_", "_")}

    cov, fr = C.coverage(base["pages"], frames)
    assert round(cov, 2) == 0.98  # reference run
    # exactly the two off-frame captions land in the frontier — and only those
    assert {tuple(p["tokens"]) for p in fr} == D.BASE_FRONTIER


def test_pollution_failure_mode_reproduced_then_fixed():
    # REQUIRED failure-mode test (spec §1): grouping by length alone with
    # exact-constancy and no anchor floor lets off-frame captions pollute the
    # skeleton into ALL-SLOTS, which force-parses everything (frontier empty —
    # the pollution is hidden as false full coverage).
    pages = D.pollution_corpus()
    toks = [p["tokens"] for p in pages]
    broken = C.induce_frames(toks, min_group=5, dominance=1.0, min_anchors=0)
    assert any(set(f.skeleton) == {"_"} for f in broken.values())  # all-slots
    bcov, bfr = C.coverage(pages, broken)
    assert bcov == 1.0 and bfr == []  # over-generalized: nothing rejected

    # the fix — dominance>=0.8 + anchor minimum + rejection — recovers the frame
    # and pushes exactly the off-frame captions to the frontier.
    fixed = C.induce_frames(toks, min_group=5, dominance=0.8, min_anchors=2)
    assert {f.skeleton for f in fixed.values()} == {("the", "_", "is", "_")}
    fcov, ffr = C.coverage(pages, fixed)
    assert fcov < 1.0 and len(ffr) == 4
    assert all(p["tokens"][0] != "the" or p["tokens"][2] != "is" for p in ffr)


def test_frontier_triggers_next_frame_induction():
    # FRONTIER AS TRIGGER (spec §1): the first pass recovers F4/F5 and rejects the
    # repeated question pattern; re-inducing on the frontier grows the next frame.
    pages = D.frontier_trigger_corpus()
    frames, residual = C.grow_frames(pages)
    skeletons = {f.skeleton for f in frames.values()}
    assert ("where", "is", "the", "_") in skeletons  # the grown frame
    assert ("the", "_", "is", "_") in skeletons and ("i", "see", "a", "_", "_") in skeletons
    # only the lone narrative line remains unparsed
    assert {tuple(p["tokens"]) for p in residual} == D.FRONTIER_TRIGGER_RESIDUAL


# ------------------------------------------------------ §2 grounding through frames


def test_slot_grounding_10_of_10_at_the_orbit_tap_budget(base):
    tok_web = C.frame_token_web(base["pages"], base["frames"])
    con_edges = D.concept_edges()
    g, taps, _trace = C.ground_with_taps(tok_web, con_edges)
    # all fillers grounded, all correct, at the tap count the orbit structure
    # requires: a 4-orbit + three 2-orbits world -> 4 taps (reference §2).
    assert len(g.map) == 10
    assert C.grounding_accuracy(g.map)
    assert taps == 4


def test_fast_map_one_page_one_tap(base):
    # a novel word on one page with one tap yields a committed-eligible fact with
    # book provenance (spec §2).
    fact, provenance, fid = C.fast_map_page(D.novel_page(), base["frames"])
    assert fact == ("zebu", "red")
    assert provenance == {"B2"}
    assert fid == "F5"


# --------------------------------------------------------------------- §6 metrics


def test_assimilation_rate_committed_and_correct(base):
    rate, committed, _facts = C.assimilation_rate(base["pages"], base["frames"])
    assert round(rate, 3) == 0.049  # reference (saturation on a small world)
    assert committed == set(D.HIDDEN_COLOUR.items())  # every fact, >=2 book origins
    assert all(D.HIDDEN_COLOUR[a] == c for a, c in committed)


def test_taps_per_book_matches_orbit_structure(base):
    assert C.taps_per_book(base["pages"], base["frames"], D.concept_edges()) == 4


def test_frontier_census_clusters_the_unparsed(base):
    _cov, fr = C.coverage(base["pages"], base["frames"])
    census = C.frontier_census(fr)
    # the two length-4 off-frame captions cluster together under "length 4"
    assert set(census) == {4}
    assert len(census[4]) == 2


def test_comprehension_verified_by_use(base):
    _rate, committed, _facts = C.assimilation_rate(base["pages"], base["frames"])
    report = C.comprehension_check(committed, D.truth())
    assert report["questions"] == 6
    assert report["accuracy"] == 1.0
