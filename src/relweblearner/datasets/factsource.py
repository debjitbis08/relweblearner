"""Fact sources — turn REAL structured knowledge into grounded lessons.

The hand-authored generators (``mathbooks`` etc.) are finite; this is how the
curriculum *expands* from external, growing sources. A fact source yields
``(subject, object)`` triples for one relation — WordNet hypernyms (``a dog is a
mammal``), Wikidata properties (``france has capital paris``) — and this module
renders them into the SAME joint episodes the generators emit (picture = the
subject, so the parsed fact is oriented) plus an auto-generated WORKSHEET (blank
the object; the object is the answer key). So every learned fact — and every
exam question — traces back to the source, and adding a new relation or a
bigger slice grows the creature's knowledge with no new code.

The P9 label discipline: **the episode stream carries no relation label** —
types are left for the learner to discover; the source's label survives only as
the worksheet's answer key. Rendering every fact through ONE fixed template
would quietly undo that (the surface form becomes a perfect proxy for the
stripped label, and "discovery" is a tautology), so a source renders each fact
through one of several PARAPHRASES — distinct constructions, including
reversed-argument ones (``paris is the capital of france``: the picture/tap
orients the fact, not token order). The creature must then induce each frame
from repetition and discover, by relation unification over the committed edge
sets (evidence-gated, simulate-gated), that the constructions express one
relation — before a worksheet phrased across all of them can be passed.

A frame is a token list with ``{s}``/``{o}`` placeholders, e.g. ``["a", "{s}",
"is", "a", "{o}"]``; ``frames`` arguments accept one or a list. Only
single-token subjects/objects are kept, so facts commit cleanly.
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


def _as_frames(frames) -> list[list[str]]:
    """Accept one frame (a token list) or a list of paraphrase frames."""
    return [frames] if frames and isinstance(frames[0], str) else list(frames)


def episodes_from_triples(triples, frames, source_tag, *, n_episodes, seed=0):
    """Render triples into ``{book, tokens, picture, marks}`` episodes.

    ``frames`` is one template or a list of paraphrases; each episode draws a
    fact AND a construction, so every fact recurs in several surface forms and
    relation identity is left to be discovered. The subject is the picture
    (grounds and orients the fact — token order carries no burden)."""
    rng = random.Random(seed)
    triples = list(triples)
    frames = _as_frames(frames)
    if not triples:
        return []
    eps = []
    for i in range(n_episodes):
        s, o = rng.choice(triples)
        frame = rng.choice(frames)
        tokens = [s if t == "{s}" else o if t == "{o}" else t for t in frame]
        eps.append({"book": f"{source_tag}-{i // 40:05d}", "tokens": tokens,
                    "picture": s, "marks": None})
    return eps


def worksheet_from_triples(triples, frames) -> list[tuple[str, str]]:
    """Auto-worksheet: each triple becomes a question (a frame with the object
    blanked to ``?``) whose answer key is the object. Questions ROTATE through
    the paraphrases, so passing the worksheet requires the constructions to
    have unified — the exam itself checks the relation was discovered."""
    frames = _as_frames(frames)
    items = []
    for i, (s, o) in enumerate(triples):
        frame = frames[i % len(frames)]
        q = " ".join("?" if t == "{o}" else s if t == "{s}" else t for t in frame)
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


def wordnet_lookup(word: str, max_n: int = 4) -> list[tuple[str, str]]:
    """The targeted twin of :func:`wordnet_triples` — the immediate hypernyms
    of ONE word, for a curiosity tick asking "what is a {word}?". Offline
    (requires the ``wordnet`` nltk corpus, like the bulk fetcher)."""
    from nltk.corpus import wordnet as wn  # lazy: only when a wordnet oracle is asked

    out = []
    for syn in wn.synsets(word, pos="n"):
        for hyp in syn.hypernyms():
            out.append((word, hyp.lemmas()[0].name()))
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


def wikidata_lookup(subject: str, prop: str, max_n: int = 4) -> list[tuple[str, str]]:
    """The targeted twin of :func:`wikidata_triples` — ONE entity's one
    property (``wikidata_lookup("france", "P36")`` -> capital), for a
    curiosity tick. Resolves the surface word through the EntitySearch API
    (labels are case-normalized there; a bare rdfs:label match would scan).
    Raises on network/rate-limit errors so the caller can treat the attempt
    as fruitless and retry a later tick (the endpoint throttles aggressively)."""
    query = (
        'SELECT ?oL WHERE { SERVICE wikibase:mwapi { '
        'bd:serviceParam wikibase:endpoint "www.wikidata.org" ; '
        'wikibase:api "EntitySearch" ; '
        f'mwapi:search "{subject}" ; mwapi:language "en" . '
        '?s wikibase:apiOutputItem mwapi:item . } '
        f'?s wdt:{prop} ?o . '
        '?o rdfs:label ?oL FILTER(LANG(?oL)="en") . } '
        f'LIMIT {max_n * 3}'
    )
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={**_UA, "Accept": "application/sparql-results+json"})
    import json
    data = json.load(urllib.request.urlopen(req, timeout=40))
    rows = [(subject, b["oL"]["value"]) for b in data["results"]["bindings"]]
    return clean_triples(rows)[:max_n]
