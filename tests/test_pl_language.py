"""PL acceptance: reading & writing (language as a separate web).

Language is a skill atop concepts: a one-way-dependent web that reads the
concept web through a learned interface. The six layers are tested against the
spec's acceptance criteria, including the two CI properties from §0/§1
(one-way dependency, disjoint namespaces) and the structural grounding limit
checked against a brute-force automorphism computation.
"""

from __future__ import annotations

import pytest

from relweblearner import language as L
from relweblearner.datasets import language as D

N_UTT = 300


@pytest.fixture(scope="module")
def pipeline():
    """Run L1/L2 once; return the recovered words, frame class, and utterances."""
    units, gold = D.stream_of(N_UTT, seed=3)
    words, bounds = L.segment(units)
    frame_words = L.discover_frame_words(words)
    utts = L.chunk(words, frame_words)
    return {
        "units": units,
        "gold": gold,
        "words": words,
        "bounds": bounds,
        "frame_words": frame_words,
        "utts": utts,
    }


# ------------------------------------------------------------ §0/§1 CI properties


def test_surface_forms_and_concept_ids_are_disjoint():
    # nothing a learner recovers from the stream string-matches a concept id
    assert D.surface_forms() & D.concept_ids() == set()


def test_language_module_is_one_way_dependent_on_concepts():
    # the language web reads the concept web; the concept web never references
    # language. Enforced structurally: language.py imports nothing concept-side.
    import inspect

    src = inspect.getsource(L)
    assert "datasets" not in src and "import" in src
    # and grounding cannot proceed without a concept web (deleting it fails L3)
    with pytest.raises((KeyError, ValueError, IndexError)):
        L.ground({"m": {("a", "b")}}, {})


# --------------------------------------------------------------- L1 segmentation


def test_clean_segmentation_is_exact(pipeline):
    prec, rec = L.boundary_prf(pipeline["bounds"], pipeline["gold"], len(pipeline["units"]))
    assert prec == 1.0 and rec == 1.0
    assert set(pipeline["words"]) == D.surface_forms()  # exact lexicon recovery


def test_segmentation_degrades_gracefully_with_a_logged_ceiling():
    # a measurable ceiling, not a failure: precision falls as words share units,
    # recall stays perfect, and the curve is monotone non-increasing.
    precisions = []
    for shared in range(len(D._STRESS_SWAPS) + 1):
        units, gold = D.stream_of(N_UTT, word=D.stress_words(shared), seed=3)
        _w, bounds = L.segment(units)
        prec, rec = L.boundary_prf(bounds, gold, len(units))
        assert rec == 1.0
        precisions.append(prec)
    assert precisions[0] == 1.0
    assert precisions[-1] < precisions[0]
    assert all(a >= b - 1e-9 for a, b in zip(precisions, precisions[1:]))


def test_novel_word_segmented_by_subtraction():
    lexicon = {t: D.SYL[t] for t in (D.WORD["HC"], D.WORD["red"])}
    novel = D.SYL[D.WORD["HC"]] + ["wu", "mi"] + D.SYL[D.WORD["red"]]
    residue, left, right = L.segment_by_subtraction(novel, lexicon)
    assert residue == "wumi"
    assert left == D.WORD["HC"] and right == D.WORD["red"]


# ----------------------------------------------------------- L2 closed-class


def test_closed_class_is_discovered_not_given(pipeline):
    # the frame-word count is not hardcoded: it is the k maximising frame-shape
    # regularity. It must recover exactly the two relation markers.
    assert pipeline["frame_words"] == {D.WORD["HC"], D.WORD["GO"]}


def test_all_chunks_have_the_frame_shape(pipeline):
    utts, fw = pipeline["utts"], pipeline["frame_words"]
    assert all(len(u) == 3 and u[0] in fw for u in utts)


# ------------------------------------------------------------- L3 grounding


def test_grounding_correct_and_stops_exactly_at_automorphism_orbits(pipeline):
    tok_web = L.token_web(pipeline["utts"], pipeline["frame_words"])
    con_edges = D.concept_edges()
    g = L.ground(tok_web, con_edges)

    # every uniquely grounded word is correct
    assert all(D.WORD[c] == t for t, c in g.map.items())
    assert len(g.map) == 7  # reference: 7/11 grounded structurally

    # the unresolved residue equals the concept web's automorphism orbits,
    # compared against a brute-force computation (the structural limit)
    unresolved = {c for _tt, cc in g.orbits for c in cc}
    orbits_bf = {c for o in L.automorphism_orbits(con_edges) if len(o) > 1 for c in o}
    assert unresolved == orbits_bf
    assert unresolved == {"mango", "lemon", "apple", "cherry"}


# -------------------------------------------------------------- L4 ostension


def test_ostension_budget_equals_orbit_count_and_grounds_fully(pipeline):
    tok_web = L.token_web(pipeline["utts"], pipeline["frame_words"])
    con_edges = D.concept_edges()
    g0 = L.ground(tok_web, con_edges)
    assert L.ostension_budget(g0.orbits) == 2

    # one pointing per orbit; each elimination grounds the partner for free
    g1 = L.ground(tok_web, con_edges, seeds={"bavu": "mango"})
    g2 = L.ground(tok_web, con_edges, seeds={"bavu": "mango", "runi": "apple"})
    assert len(g0.map) == 7 and len(g1.map) == 9 and len(g2.map) == 11
    assert all(D.WORD[c] == t for t, c in g2.map.items())  # full, correct


# ---------------------------------------------------------------- L5 reading


def _fully_grounded(pipeline):
    tok_web = L.token_web(pipeline["utts"], pipeline["frame_words"])
    con_edges = D.concept_edges()
    g = L.ground(tok_web, con_edges, seeds={"bavu": "mango", "runi": "apple"})
    return dict(g.map), g.markers


def test_reading_confirm_teach_false_paths(pipeline):
    grounding, markers = _fully_grounded(pipeline)
    relations = {"HC": dict(D.HC), "GO": dict(D.GO)}
    inv = L.invert(grounding)
    marker_inv = {r: t for t, r in markers.items()}

    def u(rel, x, y):
        return [marker_inv[rel], inv[x], inv[y]]

    # the edge exists -> confirm (free coherence check)
    assert L.comprehend(u("HC", "mango", "yellow"), grounding, markers, relations)[0] == "confirm"
    # a claim contradicting a functional edge -> refuse
    assert L.comprehend([marker_inv["HC"], inv["mango"], inv["red"]], grounding, markers, relations)[0] == "false"
    # a new coherent edge -> teach (commit-eligible)
    del relations["HC"]["mango"]
    assert L.comprehend(u("HC", "mango", "yellow"), grounding, markers, relations)[0] == "teach"


def test_fast_map_single_exposure(pipeline):
    grounding, markers = _fully_grounded(pipeline)
    relations = {"HC": dict(D.HC), "GO": dict(D.GO)}
    relations["HC"]["fig"] = "red"
    relations["GO"]["fig"] = "herb"
    con_edges = {r: set(t.items()) for r, t in relations.items()}
    lexicon = {t: D.SYL[t] for t in grounding}
    for m in pipeline["frame_words"]:
        lexicon[m] = D.SYL[m]

    novel = D.SYL[D.WORD["HC"]] + ["wu", "mi"] + D.SYL[D.WORD["red"]]
    new_word, concept, cands = L.fast_map(novel, lexicon, grounding, markers, con_edges)
    assert new_word == "wumi" and concept == "fig" and cands == ["fig"]


# ---------------------------------------------------------------- L6 writing


def test_writer_refuses_ungrounded_orbit_word(pipeline):
    tok_web = L.token_web(pipeline["utts"], pipeline["frame_words"])
    con_edges = D.concept_edges()
    g0 = L.ground(tok_web, con_edges)  # pre-ostension: mango is an orbit
    inv = L.invert(g0.map)
    marker_inv = {r: t for t, r in g0.markers.items()}
    _draft, verdict = L.write(
        ("GO", "mango", "tree"), inv, marker_inv, lambda utt: L.read(utt, g0.map, g0.markers)
    )
    assert verdict == "no word (refuse)"


def test_adjunction_laws_hold_over_full_expressible_set(pipeline):
    grounding, markers = _fully_grounded(pipeline)
    relations = {"HC": dict(D.HC), "GO": dict(D.GO)}
    report = L.adjunction_report(relations, grounding, markers)
    assert report["expressible"] == 12
    assert report["read_write_ok"] == report["expressible"]
    assert report["write_read_ok"] == report["expressible"]
    assert report["violation_rate"] == 0.0
