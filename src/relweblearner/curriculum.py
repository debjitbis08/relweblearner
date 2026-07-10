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

import itertools
import math
from collections import Counter, defaultdict
from typing import NamedTuple

from . import language as L

# ============================================================ L2′ — induction
#
# A frame is an ANCHORED SUBSEQUENCE: an ordered pattern of fixed anchor tokens
# with VARIABLE-WIDTH slots between them (a slot absorbs one *or more* tokens).
# This replaces the earlier "same word-count + fixed positions" model, which
# conflated two different templates that shared a length (``bird has two legs``
# vs ``legs let us walk``) and split one template whose slot varied in width
# (``the cow eats grass`` vs ``the horse eats a banana tree``). Aligning on
# shared anchors — the spec's "constructions are motifs over the sequence web" —
# is immune to both: templates separate by their anchor set, and a slot swallows
# a multi-word filler whole.

LIT = "L"   # a fixed anchor token:  ("L", "has")
SLOT = "S"  # a variable-width slot (>= 1 token):  ("S",)


class Frame(NamedTuple):
    id: str
    pattern: tuple             # ordered elements: ("L", tok) | ("S",)

    @property
    def anchors(self) -> tuple:
        """The fixed anchor tokens — the multi-word relation marker."""
        return tuple(e[1] for e in self.pattern if e[0] == LIT)

    @property
    def n_slots(self) -> int:
        return sum(1 for e in self.pattern if e[0] == SLOT)

    @property
    def slots(self) -> tuple:
        """Element indices that are slots (the argument positions)."""
        return tuple(i for i, e in enumerate(self.pattern) if e[0] == SLOT)

    @property
    def skeleton(self) -> tuple:
        """Per-element token or ``"_"`` for a slot (the surface skeleton; for a
        frame with only single-token slots this is the old per-position form)."""
        return tuple(e[1] if e[0] == LIT else "_" for e in self.pattern)

    @property
    def template(self) -> str:
        return " ".join("___" if e[0] == SLOT else e[1] for e in self.pattern)


def _match(pattern: tuple, tokens: list[str]):
    """Match a token sequence against a frame pattern; slots are ``+`` (one or
    more tokens, matched lazily so anchors bind as early as possible). Returns the
    list of slot fillers (each a space-joined span, in slot order) or ``None``.
    """
    fillers: list[str] = []

    def rec(pi: int, ti: int) -> bool:
        if pi == len(pattern):
            return ti == len(tokens)
        kind = pattern[pi]
        if kind[0] == LIT:
            return ti < len(tokens) and tokens[ti] == kind[1] and rec(pi + 1, ti + 1)
        for take in range(1, len(tokens) - ti + 1):   # slot: >=1 token, shortest first
            fillers.append(" ".join(tokens[ti : ti + take]))
            if rec(pi + 1, ti + take):
                return True
            fillers.pop()
        return False

    return list(fillers) if rec(0, 0) else None


def pattern_from_marks(tokens: list[str], slot_spans: list[tuple]) -> tuple:
    """Build a frame PATTERN from a human-marked breakup of one phrase.

    ``slot_spans`` are ``(start, end)`` half-open token index ranges the reader
    marked as SLOTS (the varying fillers); every other token is an anchor. This is
    the scaffold path (product direction): the reader supplies the segmentation the
    model has not yet learned to induce, yielding the same :class:`Frame` pattern
    :func:`induce_frames` produces from repetition — but from a SINGLE example, and
    crucially able to separate ADJACENT fillers the auto-inducer would merge (mark
    ``red`` and ``bear`` as two spans and ``i see a red bear`` becomes a two-slot
    frame). Each span is its own slot even when spans abut; overlaps are rejected.
    """
    spans = sorted(tuple(s) for s in slot_spans)
    for (a, b), (c, _d) in zip(spans, spans[1:]):
        if b > c:
            raise ValueError(f"overlapping slot spans: {spans}")
    pattern: list = []
    i, k = 0, 0
    while i < len(tokens):
        if k < len(spans) and i == spans[k][0]:
            pattern.append((SLOT,))
            i = spans[k][1]
            k += 1
        else:
            pattern.append((LIT, tokens[i]))
            i += 1
    return tuple(pattern)


def _signature(tokens: list[str], anchor_vocab: set) -> tuple:
    """The anchor skeleton of a sentence: anchor tokens kept as literals, maximal
    runs of non-anchor tokens collapsed to a single variable-width slot."""
    pattern: list = []
    for tok in tokens:
        if tok in anchor_vocab:
            pattern.append((LIT, tok))
        elif not pattern or pattern[-1] != (SLOT,):
            pattern.append((SLOT,))
    return tuple(pattern)


def _promote_constant_slots(pat: tuple, member_sentences: list, dominance: float) -> tuple:
    """Promote a SLOT back to an anchor when its fillers are a constant single
    token across the cluster. The relative anchor threshold demotes frequent
    fillers (good) but also a RARE frame-word (``where`` in ``where is the __``,
    swamped by a common frame); this pass recovers it — a column that is always
    the same word IS structure, however globally rare. Only single-token constant
    fillers promote (a multi-word slot like ``a banana tree`` stays a slot)."""
    slot_positions = [i for i, e in enumerate(pat) if e[0] == SLOT]
    if not slot_positions:
        return pat
    fills: dict[int, list] = {si: [] for si in range(len(slot_positions))}
    for toks in member_sentences:
        m = _match(pat, toks)
        if m is None:
            continue
        for si, f in enumerate(m):
            fills[si].append(f)
    new = list(pat)
    changed = False
    for si, elem_pos in enumerate(slot_positions):
        vals = fills[si]
        if not vals:
            continue
        top, cnt = Counter(vals).most_common(1)[0]
        if " " not in top and cnt / len(vals) >= dominance:
            new[elem_pos] = (LIT, top)
            changed = True
    return tuple(new) if changed else pat


def _mergeable(a: tuple, b: tuple, min_anchors: int) -> bool:
    """Two signatures belong to the same frame if they have the same element
    length and agree on at least ``min_anchors`` anchor columns (identical literal
    in the same position). Columns where they disagree — a literal that varies, or
    a literal facing a slot — are the slots. This is what keeps ``_ has _ legs``
    and ``legs let us _`` apart (0 shared anchors) while collapsing a filler that
    was mistaken for an anchor (e.g. a reused number) into a slot."""
    if len(a) != len(b):
        return False
    shared = sum(1 for ea, eb in zip(a, b) if ea[0] == LIT and eb[0] == LIT and ea[1] == eb[1])
    return shared >= min_anchors


def induce_frames(
    sentences: list[list[str]],
    *,
    min_group: int = 10,
    dominance: float = 0.8,
    min_anchors: int = 2,
    min_support: int | None = None,
    anchor_frac: float = 0.1,
    prefix: str = "F",
) -> dict[str, Frame]:
    """Induce frames by ANCHOR-ALIGNED clustering (not length bucketing).

    1. **anchor vocabulary** — tokens recurring in >= ``min_support`` sentences.
       ``min_support`` defaults to ``max(min_group, ceil(anchor_frac * N))`` — it
       SCALES with the corpus, because the closed frame-word class is a large
       *fraction* of sentences (``the``/``is`` in ~25–50%) while an open-class
       filler is a small one (a given animal in a few %), even though on a big
       corpus that filler's raw count is high. A purely absolute floor lets a
       reused filler masquerade as an anchor and — via the transitive merge below
       — bridge and collapse distinct frames; the relative floor prevents it.
    2. **signatures** — each sentence maps to its anchor skeleton
       (:func:`_signature`), collapsing filler runs to variable-width slots.
    3. **merge + dominance** — signatures sharing >= ``min_anchors`` anchor
       columns are unioned; within a cluster a column stays an anchor only if one
       token covers >= ``dominance`` of it, else it becomes a slot. A cluster with
       >= ``min_anchors`` surviving anchors, >= 1 slot, and >= ``min_group``
       sentences is a frame; everything else is left for the frontier.
    """
    sentences = [list(s) for s in sentences]
    if not sentences:
        return {}
    if min_support is None:
        min_support = max(min_group, math.ceil(anchor_frac * len(sentences)))

    df: Counter = Counter()
    for s in sentences:
        df.update(set(s))
    anchor_vocab = {t for t, c in df.items() if c >= min_support}

    sigs = [_signature(s, anchor_vocab) for s in sentences]
    by_sig: dict[tuple, list[int]] = defaultdict(list)
    for i, sg in enumerate(sigs):
        by_sig[sg].append(i)

    distinct = list(by_sig)
    parent = list(range(len(distinct)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # Union signatures that agree on >= min_anchors anchor columns, via an inverted
    # index instead of the O(D^2) all-pairs scan: each signature emits a key for
    # every min_anchors-sized combination of its (position, token) anchor columns
    # (blocked by length), and signatures colliding on a key are unioned. Two
    # signatures share a key IFF they agree on those exact columns, so the induced
    # clusters are identical to the pairwise :func:`_mergeable` closure — but the
    # cost is O(D · C(anchors, min_anchors)), near-linear for real frames.
    buckets: dict[tuple, int] = {}
    for idx, sg in enumerate(distinct):
        anchor_cols = [(pos, e[1]) for pos, e in enumerate(sg) if e[0] == LIT]
        for combo in itertools.combinations(anchor_cols, min_anchors):
            key = (len(sg),) + combo
            other = buckets.setdefault(key, idx)
            if other != idx:
                parent[find(idx)] = find(other)

    clusters: dict[int, list[int]] = defaultdict(list)
    for idx, sg in enumerate(distinct):
        clusters[find(idx)].extend(by_sig[sg])

    frames: dict[str, Frame] = {}
    seen: set = set()
    for members in clusters.values():
        if len(members) < min_group:
            continue
        member_sigs = [sigs[i] for i in members]
        width = len(member_sigs[0])
        pattern: list = []
        for col in range(width):
            top, cnt = Counter(sg[col] for sg in member_sigs).most_common(1)[0]
            pattern.append(top if top[0] == LIT and cnt / len(member_sigs) >= dominance else (SLOT,))
        pat = tuple(pattern)
        pat = _promote_constant_slots(pat, [sentences[i] for i in members], dominance)
        n_anchors = sum(1 for e in pat if e[0] == LIT)
        n_slots = sum(1 for e in pat if e[0] == SLOT)
        if n_anchors < min_anchors or n_slots < 1 or pat in seen:
            continue
        seen.add(pat)
        fid = f"{prefix}{len(frames)}_{'_'.join(e[1] for e in pat if e[0] == LIT)}"
        frames[fid] = Frame(fid, pat)
    return frames


def parse(tokens: list[str], frames: dict[str, Frame]):
    """Match a caption against the induced frames (most-specific first — the frame
    with the most anchors wins a tie). Returns ``(frame_id, filler_tuple)`` or
    ``None`` (rejected to the frontier — a language-layer defect, never a crash).
    """
    toks = list(tokens)
    for f in sorted(frames.values(), key=lambda fr: (-len(fr.anchors), fr.id)):
        m = _match(f.pattern, toks)
        if m is not None:
            return f.id, tuple(m)
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
