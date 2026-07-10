"""Fact sources — turn REAL structured knowledge into grounded lessons.

The hand-authored generators (``mathbooks`` etc.) are finite; this is how the
curriculum *expands* from external, growing sources. A fact source yields
``(subject, object)`` triples for one relation — WordNet hypernyms (``a dog is a
mammal``), Wikidata properties (``france has capital paris``) — and this module
renders them, through a configurable frame, into the SAME joint episodes the
generators emit (picture = the subject, so the parsed fact is oriented) plus an
auto-generated WORKSHEET (blank the object; the object is the answer key). So every
learned fact — and every exam question — traces back to the source, and adding a
new relation or a bigger slice grows the creature's knowledge with no new code.

A frame is a token list with ``{s}``/``{o}`` placeholders, e.g. ``["a", "{s}", "is",
"a", "{o}"]``. Only single-token subjects/objects are kept, so facts commit cleanly.
"""

from __future__ import annotations

import random
import urllib.parse
import urllib.request

_UA = {"User-Agent": "relweblearner/0.1 (research; grounded-fact ingestion)"}


# ------------------------------------------------------------------ rendering
def _clean(label: str) -> str | None:
    """A usable single-token concept id, or None. Lower-cased; multi-word,
    punctuated or numeric labels are dropped so slot fillers stay single tokens."""
    s = label.strip().lower()
    return s if (s.isalpha() and " " not in s) else None


def clean_triples(triples) -> list[tuple[str, str]]:
    """Keep single-token (subject, object) pairs, de-duplicated by subject so each
    subject has one worksheet answer (a functional slice of the relation)."""
    out, seen = [], set()
    for s, o in triples:
        cs, co = _clean(s), _clean(o)
        if cs and co and cs != co and cs not in seen:
            seen.add(cs)
            out.append((cs, co))
    return out


def episodes_from_triples(triples, frame, source_tag, *, n_episodes, seed=0):
    """Render triples into ``{book, tokens, picture, marks}`` episodes. ``frame`` is a
    token template with ``{s}``/``{o}``; the subject is the picture (grounds the fact)."""
    rng = random.Random(seed)
    triples = list(triples)
    if not triples:
        return []
    eps = []
    for i in range(n_episodes):
        s, o = rng.choice(triples)
        tokens = [s if t == "{s}" else o if t == "{o}" else t for t in frame]
        eps.append({"book": f"{source_tag}-{i // 40:05d}", "tokens": tokens,
                    "picture": s, "marks": None})
    return eps


def worksheet_from_triples(triples, frame) -> list[tuple[str, str]]:
    """Auto-worksheet: each triple becomes a question (frame with the object blanked
    to ``?``) whose answer key is the object."""
    q_tokens = [t if t != "{o}" else "?" for t in frame]
    items = []
    for s, o in triples:
        q = " ".join(s if t == "{s}" else t for t in q_tokens)
        items.append((q, o))
    return items


# ------------------------------------------------------------------ WordNet
def wordnet_triples(root: str, max_n: int = 150) -> list[tuple[str, str]]:
    """``(concept, immediate-hypernym)`` is-a pairs under a WordNet synset — real
    taxonomy (``a poodle is a dog``). Requires the ``wordnet`` corpus (nltk)."""
    from nltk.corpus import wordnet as wn  # lazy: only when a wordnet source is used

    base = wn.synset(root)
    out = []
    for syn in base.closure(lambda s: s.hyponyms()):
        hyp = syn.hypernyms()
        if not hyp:
            continue
        out.append((syn.lemmas()[0].name(), hyp[0].lemmas()[0].name()))
        if len(out) >= max_n * 3:            # over-fetch; _clean drops many
            break
    return clean_triples(out)[:max_n]


# ------------------------------------------------------------------ Wikidata
# Named relations -> (SPARQL, description). SPARQL returns ?sL (subject label) and
# ?oL (object label / literal). Kept small and cache-once (endpoint is rate-limited).
WIKIDATA_QUERIES = {
    "capitals": (
        'SELECT ?sL ?oL WHERE { ?s wdt:P31 wd:Q6256 ; wdt:P36 ?o . '
        '?s rdfs:label ?sL FILTER(LANG(?sL)="en"). ?o rdfs:label ?oL FILTER(LANG(?oL)="en"). } LIMIT 400',
        "countries and their capital cities",
    ),
    "elements": (
        'SELECT ?sL ?oL WHERE { ?s wdt:P31 wd:Q11344 ; wdt:P246 ?oL . '
        '?s rdfs:label ?sL FILTER(LANG(?sL)="en"). } LIMIT 200',
        "chemical elements and their symbols",
    ),
}


def wikidata_triples(relation: str, max_n: int = 200) -> list[tuple[str, str]]:
    """``(subject, object)`` pairs for a named Wikidata relation, via the public
    SPARQL endpoint. Raises on network/rate-limit errors so the caller can skip and
    retry later (the endpoint throttles aggressively — fetch once, then cache)."""
    if relation not in WIKIDATA_QUERIES:
        raise LookupError(f"unknown wikidata relation {relation!r}")
    query = WIKIDATA_QUERIES[relation][0]
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={**_UA, "Accept": "application/sparql-results+json"})
    import json
    data = json.load(urllib.request.urlopen(req, timeout=40))
    rows = [(b["sL"]["value"], b["oL"]["value"]) for b in data["results"]["bindings"]]
    return clean_triples(rows)[:max_n]
