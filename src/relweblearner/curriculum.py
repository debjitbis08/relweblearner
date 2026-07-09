"""Curriculum reading — frame induction and the book path (R2).

Extends ``docs/spec-read-write.md`` along the reading ladder: the creature is
taught from picture-book-style content, and READING is the compounding rate on
all future content. This module is the R2 rung — frame INDUCTION and
frontier-triggered template growth — sitting on top of the PL language layer.
Reference implementation of every number: ``experiment0n_frames.py``.

Like :mod:`~relweblearner.language`, this module is CONCEPT-AGNOSTIC and
one-way-dependent on the concept web: it imports nothing concept-side, takes the
concept web as its typed-edge projection, and its grounding step DELEGATES to
:mod:`~relweblearner.language` — "grounding through frames is the unchanged
machinery" (spec §2). Deleting the concept web makes grounding fail; the
induction/coverage layer stands alone.

The pipeline:

  * **L2′ frame induction** — group captions by length, mark each position FIXED
    when one token DOMINATES (>= ``dominance``) and a SLOT otherwise; a frame
    needs >= ``min_anchors`` fixed tokens (reject degenerate all-slot skeletons).
    Captions matching no skeleton are REJECTED to the FRONTIER — never
    force-parsed. Grouping by length *alone* (exact-constancy, no anchor floor)
    lets off-frame captions pollute the skeleton into all-slots; the dominance
    threshold + anchor minimum + rejection is the fix, and it is parameterised
    here so a CI test can reproduce the failure without it.
  * **frontier as trigger** — when a frontier subset itself shows
    repetition-with-substitution, re-inducing on it grows the NEXT frame
    (obstruction -> growth, as everywhere else): :func:`grow_frames`.
  * **grounding through frames** — a frame is a multi-word relation marker and its
    slot-fillers are the arguments; the pictured referent orients each fact, and
    the existing WL alignment + iterative picture taps ground the fillers.
  * **fast-map / assimilation / metrics** — one page + one tap yields a
    committed-eligible fact with book provenance; coverage, assimilation rate,
    taps-per-book, frontier census and a comprehension check are the path metrics
    (spec §6).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import NamedTuple

from . import language as L

# ============================================================ L2′ — induction


class Frame(NamedTuple):
    id: str
    skeleton: tuple            # per-position token or "_" for a slot
    slots: tuple               # slot positions (the argument positions)
    anchors: tuple             # fixed positions (the multi-word relation marker)


def _induce_one(group: list[tuple], dominance: float, min_anchors: int):
    """Induce a skeleton from one equal-length group by per-position dominance.

    A position is FIXED (an anchor) when its most common token covers at least a
    ``dominance`` fraction of the group, else it is a SLOT. Returns
    ``(skeleton, slots, anchors)`` or ``None`` when the anchor count is below
    ``min_anchors`` (the degenerate all-slot skeleton is refused, not emitted).
    """
    n, width = len(group), len(group[0])
    skel, slots, anchors = [], [], []
    for i in range(width):
        tok, cnt = Counter(s[i] for s in group).most_common(1)[0]
        if cnt / n >= dominance:
            skel.append(tok)
            anchors.append(i)
        else:
            skel.append("_")
            slots.append(i)
    if len(anchors) < min_anchors:
        return None
    return tuple(skel), tuple(slots), tuple(anchors)


def induce_frames(
    sentences: list[list[str]],
    *,
    min_group: int = 10,
    dominance: float = 0.8,
    min_anchors: int = 2,
    prefix: str = "F",
) -> dict[str, Frame]:
    """Induce one frame per length class with enough support.

    ``dominance`` and ``min_anchors`` are the discipline that keeps off-frame
    captions from polluting a skeleton (see module docstring); lowering the bar
    (``dominance`` toward 0 with ``min_anchors=0``) reproduces the over-general
    all-slot failure. Frame ids are ``f"{prefix}{width}"``.
    """
    by_len: dict[int, list[tuple]] = defaultdict(list)
    for s in sentences:
        by_len[len(s)].append(tuple(s))
    frames: dict[str, Frame] = {}
    for width, group in sorted(by_len.items()):
        if len(group) < min_group:
            continue
        res = _induce_one(group, dominance, min_anchors)
        if res is not None:
            skel, slots, anchors = res
            fid = f"{prefix}{width}"
            frames[fid] = Frame(fid, skel, slots, anchors)
    return frames


def parse(tokens: list[str], frames: dict[str, Frame]):
    """Match a caption against the induced frames (most-specific first — the frame
    with the most anchors wins a tie). Returns ``(frame_id, filler_tuple)`` or
    ``None`` (rejected to the frontier — a language-layer defect, never a crash).
    """
    toks = tuple(tokens)
    for f in sorted(frames.values(), key=lambda fr: -len(fr.anchors)):
        if len(toks) == len(f.skeleton) and all(
            s == "_" or s == t for s, t in zip(f.skeleton, toks)
        ):
            return f.id, tuple(toks[i] for i in f.slots)
    return None


def parse_pages(pages: list[dict], frames: dict[str, Frame]):
    """Parse every page, keeping the page alongside its result."""
    return [(p, parse(p["tokens"], frames)) for p in pages]


def frontier(pages: list[dict], frames: dict[str, Frame]) -> list[dict]:
    """The unparsed pages — the induction queue."""
    return [p for p in pages if parse(p["tokens"], frames) is None]


def coverage(pages: list[dict], frames: dict[str, Frame]):
    """Fraction of pages parsed by induced frames; returns ``(coverage, frontier)``
    (frontier size is the complement and the induction queue, spec §6)."""
    fr = frontier(pages, frames)
    cov = 1 - len(fr) / len(pages) if pages else 0.0
    return cov, fr


def grow_frames(
    pages: list[dict],
    *,
    min_group: int = 10,
    dominance: float = 0.8,
    min_anchors: int = 2,
):
    """Frontier-triggered induction: induce, reject unparsed to the frontier, and
    RE-INDUCE on the frontier while a fresh (new-skeleton) frame keeps emerging.

    This is the obstruction->growth pattern: an unparsed subset that itself shows
    repetition-with-substitution triggers the next frame. Returns
    ``(frames, residual_frontier)``.
    """
    frames: dict[str, Frame] = {}
    pool = list(pages)
    rnd = 0
    while pool:
        induced = induce_frames(
            [p["tokens"] for p in pool],
            min_group=min_group,
            dominance=dominance,
            min_anchors=min_anchors,
            prefix=f"G{rnd}_",
        )
        added = False
        for f in induced.values():
            if not any(e.skeleton == f.skeleton for e in frames.values()):
                frames[f.id] = f
                added = True
        if not added:
            break
        pool = frontier(pool, frames)
        rnd += 1
    return frames, pool


# ==================================================== grounding through frames


def _orient(fillers: tuple, picture: str):
    """Orient a frame's two slot-fillers into ``(source, target)`` using the
    PICTURE channel: the pictured (tapped) referent is the relation's source
    argument, the other filler its target. Joint attention is the symmetry-breaker
    (spec §0), and orienting by the picture removes any need to know slot roles a
    priori. Falls back to token order if the picture is not among the fillers.
    """
    if len(fillers) == 2 and picture in fillers:
        src = picture
        tgt = fillers[0] if fillers[1] == picture else fillers[1]
        return src, tgt
    return fillers[0], fillers[1]


def frame_token_web(pages: list[dict], frames: dict[str, Frame], relation: str = "names"):
    """Build the token web from parsed pages: each fact is a picture-oriented edge
    ``(w:source, w:target)`` in the ``w:``-prefixed surface namespace (no id shared
    with the concept web). The frame is the relation marker; all frames collapse
    onto the one relation they express, so this is a drop-in ``tok_web`` for
    :func:`relweblearner.language.ground`.
    """
    edges = set()
    for p, r in parse_pages(pages, frames):
        if r is not None and len(r[1]) == 2:
            src, tgt = _orient(r[1], p["picture"])
            edges.add((f"w:{src}", f"w:{tgt}"))
    return {relation: edges}


def ground_with_taps(tok_web: dict[str, set], con_edges: dict[str, set], max_taps: int | None = None):
    """Ground slot-fillers by structure, then break the residual symmetry with
    iterative PICTURE TAPS (ostension): one tap per remaining orbit, smallest
    orbit first (maximally informative — the partner grounds by elimination).

    Delegates the WL alignment to :func:`relweblearner.language.ground` — the
    unchanged machinery. Returns ``(grounding, taps, trace)`` where ``trace`` is
    the per-tap ``(concept, n_grounded, n_orbits_left)`` cascade.
    """
    seeds: dict[str, str] = {}
    taps, trace = 0, []
    g = L.ground(tok_web, con_edges, seeds)
    while g.orbits:
        orbit = min(g.orbits, key=lambda o: (len(o[0]), sorted(o[0])))
        token = sorted(orbit[0])[0]        # a token node, e.g. "w:bear"
        concept = token[2:]                 # tap the pictured referent -> its concept
        seeds[token] = concept
        taps += 1
        g = L.ground(tok_web, con_edges, seeds)
        trace.append((concept, len(g.map), len(g.orbits)))
        if max_taps is not None and taps >= max_taps:
            break
    return g, taps, trace


def grounding_accuracy(grounding_map: dict[str, str]) -> bool:
    """Every uniquely grounded ``w:x`` maps to concept ``x`` (word-namespace)."""
    return all(w == f"w:{c}" for w, c in grounding_map.items())


# ================================================================ fast-mapping


def fast_map_page(page: dict, frames: dict[str, Frame]):
    """Fast-map from ONE page: parse the caption in a known frame, orient by the
    picture, and read off the fact whose novel argument the tap grounds in a
    single exposure. Returns ``(fact, provenance, frame_id)`` — a
    committed-ELIGIBLE fact carrying its book provenance — or ``None`` if the page
    matches no frame.
    """
    r = parse(page["tokens"], frames)
    if r is None or len(r[1]) != 2:
        return None
    fact = _orient(r[1], page["picture"])   # (novel_referent, known_colour)
    return fact, {page["book"]}, r[0]


# ==================================================================== metrics


def collect_facts(pages: list[dict], frames: dict[str, Frame]) -> dict[tuple, set]:
    """Every parsed fact ``(source, target)`` with the set of books it appears in
    (repetition-with-substitution accrues origins, spec §0.3)."""
    facts: dict[tuple, set] = defaultdict(set)
    for p, r in parse_pages(pages, frames):
        if r is not None and len(r[1]) == 2:
            facts[_orient(r[1], p["picture"])].add(p["book"])
    return facts


def committed_facts(facts: dict[tuple, set], k: int = 2) -> set:
    """Facts with >= ``k`` book origins — commit-eligible under the standard
    k-threshold policy (text/pages are claims that accrue provenance)."""
    return {f for f, books in facts.items() if len(books) >= k}


def assimilation_rate(pages: list[dict], frames: dict[str, Frame], k: int = 2):
    """Committed, NON-REDUNDANT facts per sentence read (raw facts/sentence
    saturates on small worlds — this counts distinct committed facts, spec §6).
    Returns ``(rate, committed, facts)``.
    """
    facts = collect_facts(pages, frames)
    committed = committed_facts(facts, k)
    rate = len(committed) / len(pages) if pages else 0.0
    return rate, committed, facts


def taps_per_book(pages: list[dict], frames: dict[str, Frame], con_edges: dict[str, set]):
    """Ostension cost: the number of picture taps the orbit structure requires to
    ground the book's fillers (should fall as the concept web grows — more
    structure, fewer orbits)."""
    tok_web = frame_token_web(pages, frames)
    _g, taps, _trace = ground_with_taps(tok_web, con_edges)
    return taps


def frontier_census(frontier_pages: list[dict]) -> dict[int, list[tuple]]:
    """Cluster unparsed captions by length — the reading layer's "what confuses
    me" view and the induction queue (a product feature for free, spec §6)."""
    clusters: dict[int, list[tuple]] = defaultdict(list)
    for p in frontier_pages:
        clusters[len(p["tokens"])].append(tuple(p["tokens"]))
    return {length: sorted(v) for length, v in sorted(clusters.items())}


def comprehension_check(committed: set, truth: dict[str, str]) -> dict:
    """Comprehension verified by USE, not echo: pose one question per known
    referent in a known frame (``the <animal> is _``), answer it from the concept
    web (the committed facts), and score against the world's hidden truth.

    ``truth`` is passed in (the module stays concept-agnostic). Returns question
    count, correct count and accuracy.
    """
    web = {a: c for (a, c) in committed}
    questions = sorted(web)
    correct = sum(1 for a in questions if truth.get(a) == web[a])
    return {
        "questions": len(questions),
        "correct": correct,
        "accuracy": correct / len(questions) if questions else 0.0,
    }
