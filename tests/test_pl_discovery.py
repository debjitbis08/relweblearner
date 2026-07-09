"""PL′ — grounding on DISCOVERED relation types (closes the I3 traceability gap).

The read/write layer previously grounded words against a concept web whose
relation types were *given* (HC/GO). Here the concept web is handed in
label-free; P2′ discovers its types; grounding aligns frame words to the
*discovered* types; and every relation type in the grounding traces back to a
discovery record. This is the last unpaid structuralist debt from the report.
"""

from __future__ import annotations

import random

from relweblearner import language as L
from relweblearner.datasets import language as DL


def _corpus(n_utt=600, seed=3):
    word = DL.make_surface_forms()
    syl = DL.syllabify(word)
    facts = DL.rich_facts()
    units, _gold = DL.stream_of(n_utt, facts=facts, word=word, syl=syl, seed=seed)
    words, _b = L.segment(units)
    fw = L.discover_frame_words(words)
    tok_web = L.token_web(L.chunk(words, fw), fw)
    return word, tok_web


def test_p2prime_discovers_the_concept_types_with_a_record():
    disc = L.discover_relation_types(DL.unlabeled_edges())
    # two attribute types recovered from label-free edges, each fully witnessed
    assert set(disc.edges_by_type) == {"T1", "T2"}
    assert all(len(es) == 9 for es in disc.edges_by_type.values())
    assert disc.provenance["method"] == "P2'-disjointness-compression"
    assert set(disc.provenance["types"]) == {"T1", "T2"}


def test_grounding_consumes_discovered_types_and_is_correct():
    word, tok_web = _corpus()
    disc = L.discover_relation_types(DL.unlabeled_edges())
    g = L.ground(tok_web, disc.edges_by_type)

    # every uniquely grounded word is correct
    assert g.map and all(word[c] == t for t, c in g.map.items())
    # markers align frame words to DISCOVERED type ids (T1/T2), not given labels
    assert set(g.markers.values()) <= {"T1", "T2"}
    assert "HC" not in g.markers.values() and "GO" not in g.markers.values()


def test_every_grounded_type_traces_to_a_discovery_event():
    word, tok_web = _corpus()
    disc = L.discover_relation_types(DL.unlabeled_edges())
    g = L.ground(tok_web, disc.edges_by_type)

    trace = L.type_provenance(g.markers, disc)
    assert trace and all(v == "discovered" for v in trace.values())   # nothing smuggled


def test_smuggled_label_is_detected():
    # a marker using a type with no discovery record is flagged, not silently used
    disc = L.discover_relation_types(DL.unlabeled_edges())
    trace = L.type_provenance({"someword": "GIVEN_LABEL"}, disc)
    assert trace["GIVEN_LABEL"] == "SMUGGLED"


def test_discovery_does_not_change_what_grounds_only_its_provenance():
    # grounding the SAME web by given labels vs discovered types resolves the
    # same token->concept map — discovery adds traceability, not a different answer
    word, tok_web = _corpus()
    disc = L.discover_relation_types(DL.unlabeled_edges())
    given = {r: set(t.items()) for r, t in DL.RICH_RELATIONS.items()}
    g_disc = L.ground(tok_web, disc.edges_by_type)
    g_given = L.ground(tok_web, given)
    assert g_disc.map == g_given.map
