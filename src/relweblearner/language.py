"""Reading & writing — language as a separate, one-way-dependent web (PL).

The standalone language phase from ``docs/spec-read-write.md``, off the numbered
dev-doc roadmap (whose P9 is Perception & data feed — unrelated).

Language is a SEPARATE web that reads the concept web through a learned
interface; the concept web never references language (spec §0). This module is
therefore concept-agnostic: it imports nothing concept-specific and takes the
concept web as its typed-edge projection ``{rel: {(x, y), ...}}`` — exactly what
a :class:`~relweblearner.web.Web` exposes. Deleting language leaves every
concept-web test passing; the reading/writing here cannot ground without a
concept web (both directions are CI-tested in ``test_pl_language``).

Six layers, each a pure function of its inputs (seed the caller, not the module):

  * **L1 segmentation** — word boundaries from transition-probability dips
    (Saffran); a novel word heard once is segmented by SUBTRACTION.
  * **L2 utterance structure** — the closed (frame) class is *discovered* as the
    word count that maximises frame-shape regularity, never given.
  * **L3 grounding** — align the token web to the concept web by STRUCTURE
    ALONE (joint Weisfeiler–Leman refinement + frame↔relation bijection search).
    THE STRUCTURAL LIMIT: distributional grounding resolves meanings exactly up
    to the **automorphism orbits** of the concept web; structurally
    interchangeable concepts cannot be told apart by any volume of text. This is
    the formal content of the gavagai problem — checked against a brute-force
    orbit computation (:func:`automorphism_orbits`).
  * **L4 ostension** — joint attention seeds identical WL colours on both webs;
    one pointing per orbit breaks the symmetry, the partner grounds for free.
  * **L5 reading** — a grounded utterance maps to a concept edge: confirm /
    teach / fast-map an unknown word / refuse a false claim.
  * **L6 writing** — inverse map then READ THE DRAFT BACK before committing; the
    adjunction laws ``read(write(f)) == f`` and ``write(read(u)) ~ u`` are the
    correctness discipline of the layer.
"""

from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from typing import NamedTuple

# ============================================================ L1 — segmentation


def transition_table(units: list[str]) -> dict[str, Counter]:
    """Incremental bigram counts over the unit stream."""
    trans: dict[str, Counter] = defaultdict(Counter)
    for a, b in zip(units, units[1:]):
        trans[a][b] += 1
    return trans


def segment(units: list[str], theta: float = 0.9):
    """Split the stream where the forward transition probability dips below
    ``theta`` (within-word transitions are near-deterministic, cross-word ones
    diluted). Returns ``(words, boundaries)`` — ``words`` joined syllables,
    ``boundaries`` the set of split positions (1-indexed unit offsets).
    """
    trans = transition_table(units)

    def prob(a: str, b: str) -> float:
        return trans[a][b] / sum(trans[a].values())

    words, cur, bounds, pos = [], [units[0]], set(), 1
    for a, b in zip(units, units[1:]):
        if prob(a, b) < theta:
            words.append("".join(cur))
            bounds.add(pos)
            cur = [b]
        else:
            cur.append(b)
        pos += 1
    words.append("".join(cur))
    return words, bounds


def boundary_prf(bounds: set[int], gold: set[int], n_units: int):
    """Precision/recall of recovered boundaries against gold. The final
    end-of-stream boundary is not a decision point, so it is excluded.
    """
    gold_internal = gold - {n_units}
    tp = len(bounds & gold_internal)
    prec = tp / len(bounds) if bounds else 0.0
    rec = tp / len(gold_internal) if gold_internal else 0.0
    return prec, rec


def _match_end(units: list[str], by_syls: dict, *, prefix: bool, max_len: int = 4):
    """Longest known word matching the prefix (or suffix) of ``units``.

    Returns ``(token, length)`` or ``(None, 0)``.
    """
    for length in range(min(max_len, len(units)), 0, -1):
        seg = tuple(units[:length]) if prefix else tuple(units[-length:])
        if seg in by_syls:
            return by_syls[seg], length
    return None, 0


def segment_by_subtraction(units: list[str], lexicon: dict[str, list[str]]):
    """Segment a novel word heard once: strip known words from both ends; the
    residue is the candidate new word (transition statistics are silent for a
    once-heard word). ``lexicon`` maps known token -> its syllable list.

    Returns ``(residue, left_token, right_token)``.
    """
    by_syls = {tuple(s): t for t, s in lexicon.items()}
    left, lf = _match_end(units, by_syls, prefix=True)
    right, ls = _match_end(units, by_syls, prefix=False)
    residue = "".join(units[lf : len(units) - ls])
    return residue, left, right


# ======================================================= L2 — utterance structure


def chunk(words: list[str], frame_words: set[str]) -> list[list[str]]:
    """Chunk the word stream into utterances, breaking before each frame word."""
    utts, cur = [], []
    for w in words:
        if w in frame_words and cur:
            utts.append(cur)
            cur = []
        cur.append(w)
    if cur:
        utts.append(cur)
    return utts


def _frame_regularity(utts: list[list[str]], frame_words: set[str]) -> float:
    """Fraction of chunks with the frame shape: constant length, frame-initial.

    The modal chunk length defines "the shape"; a chunk conforms iff it has that
    length and begins with a frame word. This is the signal that lets the closed
    class be *discovered* rather than given.
    """
    if not utts:
        return 0.0
    modal_len = Counter(len(u) for u in utts).most_common(1)[0][0]
    ok = sum(1 for u in utts if len(u) == modal_len and u[0] in frame_words)
    return ok / len(utts)


def discover_frame_words(words: list[str], max_k: int = 4) -> set[str]:
    """Discover the closed (frame) class from the recovered lexicon.

    Frame words are frequency outliers (the Zipf head) that begin every
    utterance. The *count* of frame words is not given: we take the top-``k``
    most frequent words for each ``k`` and keep the ``k`` whose induced chunking
    is most regular (ties broken toward the smaller, more parsimonious class).
    """
    freq = Counter(words)
    ranked = [w for w, _ in freq.most_common()]
    best_k, best_score = 1, -1.0
    for k in range(1, min(max_k, len(ranked)) + 1):
        cand = set(ranked[:k])
        score = _frame_regularity(chunk(words, cand), cand)
        if score > best_score + 1e-9:  # strict improvement keeps k minimal
            best_k, best_score = k, score
    return set(ranked[:best_k])


# ============================================================== L3 — grounding


class Grounding(NamedTuple):
    map: dict[str, str]        # surface token -> concept id (uniquely resolved)
    orbits: list               # unresolved (token-group, concept-group) pairs
    markers: dict[str, str]    # frame token -> concept relation name


def token_web(utts: list[list[str]], frame_words: set[str]) -> dict[str, set]:
    """Build the token web: each utterance ``[frame, a, b]`` contributes an edge
    ``(a, b)`` typed by its frame word.
    """
    edges: dict[str, set] = {m: set() for m in frame_words}
    for u in utts:
        if u[0] in frame_words and len(u) == 3:
            edges[u[0]].add((u[1], u[2]))
    return edges


def wl_signatures(nodes: set, typed_edges: dict[str, set], seeds: dict, rounds: int = 4):
    """Weisfeiler–Leman colour refinement over a typed directed graph.

    ``seeds`` (ostension) tag nodes with an initial colour shared across webs;
    the signature folds in each node's typed in/out neighbour colours.
    """
    sig = {n: str(seeds.get(n, "x")) for n in nodes}
    for _ in range(rounds):
        nxt = {}
        for n in nodes:
            out = sorted(("o", t, sig[v]) for t, es in typed_edges.items() for (u, v) in es if u == n)
            inc = sorted(("i", t, sig[u]) for t, es in typed_edges.items() for (u, v) in es if v == n)
            nxt[n] = str(seeds.get(n, "")) + str(out + inc)
        sig = nxt
    return sig


def ground(tok_web: dict[str, set], con_edges: dict[str, set], seeds: dict | None = None) -> Grounding:
    """Ground = align the token web to the concept web by structure alone.

    Searches the small space of frame-token ↔ relation-name bijections; for each,
    runs joint WL refinement on both webs. Unique signature matches ground;
    equal-signature groups of size > 1 are ORBITS (the automorphism residue).
    ``seeds`` are ostension events ``{token: concept}`` tagging both sides.
    """
    seeds = seeds or {}
    frame_tokens = sorted(tok_web)
    rel_names = sorted(con_edges)
    if len(frame_tokens) != len(rel_names):
        raise ValueError("frame-word count must match relation count to ground")

    tok_nodes = {n for es in tok_web.values() for e in es for n in e}
    con_nodes = {n for es in con_edges.values() for e in es for n in e}
    items = sorted(seeds.items())
    tseed = {t: f"S{i}" for i, (t, _c) in enumerate(items)}
    cseed = {c: f"S{i}" for i, (_t, c) in enumerate(items)}

    best = None
    for perm in itertools.permutations(rel_names):
        te = {f"R{j}": tok_web[frame_tokens[j]] for j in range(len(frame_tokens))}
        ce = {f"R{j}": con_edges[perm[j]] for j in range(len(frame_tokens))}
        ts = wl_signatures(tok_nodes, te, tseed)
        cs = wl_signatures(con_nodes, ce, cseed)
        groups: dict = defaultdict(lambda: ([], []))
        for n, s in ts.items():
            groups[s][0].append(n)
        for n, s in cs.items():
            groups[s][1].append(n)
        g = {t: c[0] for (tt, c) in groups.values() if len(tt) == 1 and len(c) == 1 for t in tt}
        orbits = [(sorted(tt), sorted(c)) for (tt, c) in groups.values() if len(tt) == len(c) > 1]
        markers = {frame_tokens[j]: perm[j] for j in range(len(frame_tokens))}
        if best is None or len(g) > best[0]:
            best = (len(g), g, orbits, markers)
    return Grounding(best[1], best[2], best[3])


def automorphism_orbits(con_edges: dict[str, set]) -> list[frozenset]:
    """Brute-force automorphism orbits of the concept web (relation-preserving).

    The ground truth the L3 structural limit is measured against: two concepts
    share an orbit iff some automorphism of the typed concept graph maps one to
    the other. Uses networkx VF2 (a dev-doc-sanctioned dependency).
    """
    import networkx as nx
    from networkx.algorithms.isomorphism import (
        MultiDiGraphMatcher,
        categorical_multiedge_match,
    )

    g = nx.MultiDiGraph()
    for rel, es in con_edges.items():
        for u, v in es:
            g.add_edge(u, v, rel=rel)

    parent = {n: n for n in g.nodes()}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    matcher = MultiDiGraphMatcher(g, g, edge_match=categorical_multiedge_match("rel", None))
    for mapping in matcher.isomorphisms_iter():  # G↔G ⇒ automorphisms
        for a, b in mapping.items():
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

    orbits: dict = defaultdict(set)
    for n in g.nodes():
        orbits[find(n)].add(n)
    return [frozenset(s) for s in orbits.values()]


# ------------------------------------------- L3′ — discovered (not given) types
class DiscoveredConceptWeb(NamedTuple):
    edges_by_type: dict   # {discovered_type_id: {(x, y), ...}} — feeds ``ground``
    provenance: dict      # the discovery record every used type must trace back to


def discover_relation_types(unlabeled_edges, hub_threshold: int = 3) -> DiscoveredConceptWeb:
    """Recover the concept web's relation types from UNLABELED edges (P2′), and
    key the typed-edge projection by the *discovered* type ids.

    This is what closes the last structuralist debt: the concept web is handed in
    label-free, `types.discover_types` (disjointness compression) partitions it
    into structural types, and the returned ``edges_by_type`` is a drop-in for
    :func:`ground`'s ``con_edges`` — so grounding aligns frame words to types the
    learner *discovered*, never to given labels. ``provenance`` is the discovery
    record (method, params, member edges per type) that :func:`type_provenance`
    traces every grounded relation type back to.
    """
    from .types import discover_types

    disc = discover_types(list(unlabeled_edges), hub_threshold=hub_threshold)
    edges_by_type = {t: set(es) for t, es in disc.items() if es}
    provenance = {
        "method": "P2'-disjointness-compression",
        "hub_threshold": hub_threshold,
        "types": {t: sorted(tuple(e) for e in es) for t, es in edges_by_type.items()},
    }
    return DiscoveredConceptWeb(edges_by_type, provenance)


def type_provenance(markers: dict, discovered: DiscoveredConceptWeb) -> dict:
    """Trace each relation type used in grounding back to a discovery record.

    Returns ``{type_id: "discovered" | "SMUGGLED"}``. A ``"SMUGGLED"`` entry is a
    type that grounding uses but that no discovery event produced — the exact
    thing the I3 audit exists to catch.
    """
    return {
        t: ("discovered" if t in discovered.provenance["types"] else "SMUGGLED")
        for t in set(markers.values())
    }


# ============================================================== L4 — ostension


def ostension_budget(orbits: list) -> int:
    """One pointing per nontrivial orbit suffices (the partner grounds by
    elimination). The budget is exactly the number of orbits.
    """
    return len(orbits)


# ================================================================ L5 — reading


def read(utt_tokens: list[str], grounding: dict[str, str], markers: dict[str, str]):
    """Map a grounded utterance through the interface to a concept-web edge
    ``(relation, x, y)``; unresolved tokens read as ``None``.
    """
    return (
        markers[utt_tokens[0]],
        grounding.get(utt_tokens[1]),
        grounding.get(utt_tokens[2]),
    )


def comprehend(utt_tokens: list[str], grounding: dict[str, str], markers: dict[str, str], relations: dict):
    """Classify a read utterance into one of the four L5 outcomes.

    * ``("unknown", token)`` — an ungrounded content word (route to fast-map);
    * ``("confirm", fact)``  — the edge already holds (a free coherence check);
    * ``("teach", fact)``    — a new coherent edge (commit via commitment policy);
    * ``("false", fact)``    — contradicts an existing functional edge (refuse).
    """
    for t in utt_tokens[1:]:
        if t not in grounding:
            return "unknown", t
    rel = markers[utt_tokens[0]]
    x, y = grounding[utt_tokens[1]], grounding[utt_tokens[2]]
    table = relations[rel]
    if x in table:
        return ("confirm", (rel, x, y)) if table[x] == y else ("false", (rel, x, y))
    return "teach", (rel, x, y)


def fast_map(units, lexicon, grounding, markers, con_edges):
    """Fast-map a novel word from a single exposure (L5 path 3).

    Segment the utterance by subtraction (known words flank the novel word),
    read the frame position and grounded remainder, and resolve the residue by
    mutual exclusivity against the unworded concepts standing in that relation.

    Returns ``(new_word, concept, candidates)``; ``concept`` is ``None`` unless a
    single candidate remains.
    """
    residue, left, right = segment_by_subtraction(units, lexicon)
    rel = markers.get(left)
    target = grounding.get(right)
    worded = set(grounding.values())
    cands = sorted(x for (x, y) in con_edges[rel] if y == target and x not in worded)
    concept = cands[0] if len(cands) == 1 else None
    return residue, concept, cands


# ================================================================ L6 — writing


def invert(grounding: dict[str, str]) -> dict[str, str]:
    """Concept -> surface token (the inverse interface)."""
    return {c: t for t, c in grounding.items()}


def write(fact, inv: dict[str, str], marker_inv: dict[str, str], read_fn):
    """Express a concept fact, rehearsing the draft before committing.

    Draft the token sequence via the inverse interface, then READ IT BACK
    through ``read_fn``; commit only if the reconstruction equals the target.
    A concept with no word (or an unresolved orbit) forces a refusal — an
    ambiguous draft is never emitted silently.

    Returns ``(draft, verdict)``.
    """
    r, x, y = fact
    if x not in inv or y not in inv:
        return None, "no word (refuse)"
    draft = [marker_inv[r], inv[x], inv[y]]
    if read_fn(draft) == fact:
        return draft, "commit"
    return draft, "read-back mismatch (refuse)"


def expressible_facts(relations: dict, grounding: dict[str, str]) -> list:
    """Every fact both of whose arguments have a resolved word."""
    worded = set(grounding.values())
    return [
        (rel, x, y)
        for rel, table in relations.items()
        for x, y in table.items()
        if x in worded and y in worded
    ]


def adjunction_report(relations: dict, grounding: dict[str, str], markers: dict[str, str]) -> dict:
    """Check both adjunction laws over the full expressible set.

    * ``read(write(f)) == f`` for every expressible fact;
    * ``write(read(u))`` is fact-equivalent to ``u`` for every grounded
      utterance (paraphrase allowed, meaning drift not).

    Returns counts and the violation rate (must be 0 for commit-eligible drafts).
    """
    inv = invert(grounding)
    marker_inv = {r: t for t, r in markers.items()}

    def rd(u):
        return read(u, grounding, markers)

    facts = expressible_facts(relations, grounding)
    write_read_ok = 0
    for f in facts:
        draft, verdict = write(f, inv, marker_inv, rd)
        if verdict == "commit" and rd(draft) == f:
            write_read_ok += 1

    utts = [[marker_inv[r], inv[x], inv[y]] for (r, x, y) in facts]
    read_write_ok = 0
    for u in utts:
        f = rd(u)
        draft, verdict = write(f, inv, marker_inv, rd)
        if verdict == "commit" and rd(draft) == f:
            read_write_ok += 1

    n = len(facts)
    violations = (n - write_read_ok) + (n - read_write_ok)
    return {
        "expressible": n,
        "read_write_ok": write_read_ok,
        "write_read_ok": read_write_ok,
        "violation_rate": violations / (2 * n) if n else 0.0,
    }
