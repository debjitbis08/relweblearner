"""Transport — the fixed algebra put back under the creature's streamed facts.

The scale substrate (:mod:`~relweblearner.creature`, :mod:`~relweblearner.store`)
distils episodes into provenance-counted edges, but an edge that carries no
algebra value cannot be composed, so a learner over that store alone can only
RECALL single taught facts — it cannot think. This module closes that gap with
the core machinery, unchanged:

  * **P2 sector inference over relation classes.** Every committed converse
    pair ``s -[R1]-> t``, ``t -[R2]-> s`` is a loop observation: its closure
    forces ``g(R1) + g(R2) = 0`` over the frozen ``IntegerGroup``. A class
    converse to ITSELF on most pairs is symmetric (``2g = 0`` → ``g = 0``); a
    class converse to a DISTINCT partner is half of an antisymmetric generator
    pair (``g, -g``; the magnitude and sign are gauge, fixed to ±1
    deterministically); a class with no loop evidence stays UNCONSTRAINED (its
    value is pure gauge, so nothing may be derived along it — deriving there
    is exactly the P4 "algebra too strong → hallucinated inverses" failure);
    a class whose loop evidence is self-contradictory beyond the exception
    budget is NON-HOMOGENEOUS — a motif carrying no transport (the P2
    ``double`` verdict, under the description-length exception rule).
  * **The web projection.** Eligible facts become a
    :class:`~relweblearner.web.Web` per CONSTRAINT GROUP — algebra-valued,
    holonomy-checkable. Groups stay separate because transports across groups
    are mutually ungauged (the P4′ sector-preserving-gauge amendment): mixing
    them would manufacture fake defects and false inverses.
  * **Defects.** :func:`defect_report` runs :mod:`~relweblearner.holonomy`
    over the group webs, so a committed contradiction (a poisoned converse
    pair) is a genuine nonzero-holonomy loop the creature can SEE — invariant
    #9's signal, restored. Classes defective beyond the exception budget are
    demoted to motifs (:func:`non_homogeneous_by_defect`).
  * **Derivation = transport composition.** :func:`derive` walks a group web
    composing values (converses via dagger); the answer to a never-taught
    question is the node whose composed transport equals the class transport.
    This is the P3 discipline — exactness by construction, zero shot.
  * **Growth on walk-off.** A derivable question with no witnessing node is
    the P1 obstruction; :class:`SectorGrowth` is the stock
    :class:`~relweblearner.growth.GrowthEngine` (relabel proved futile,
    fork-scored rewire first, persistence-gated minimal grow) with
    creature-scoped fresh names, so a posited node is unique across every
    group web and survives reload.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .algebra import IntegerGroup
from .growth import GrowthEngine
from .holonomy import defect_mass, defects
from .sectors import ANTISYMMETRIC, NON_HOMOGENEOUS, SYMMETRIC, RelationSector
from .web import Web

#: no loop evidence constrains this class: its transport is a gauge choice
#: (kept so its web is holonomy-checkable) and supports NO derivation.
UNCONSTRAINED = "unconstrained"

__all__ = [
    "ANTISYMMETRIC", "NON_HOMOGENEOUS", "SYMMETRIC", "UNCONSTRAINED",
    "RelationSector", "SectorGrowth", "Web",
    "build_group_webs", "defect_report", "derive", "infer",
    "non_homogeneous_by_defect", "simulate_fission", "simulate_merge",
]


def _mine_compositions(cmaps: dict[str, set], eligible: list,
                       exception_fraction: float) -> list[tuple]:
    """Candidate 3-cycle constraints ``g(head) = g(a) + g(b)``, by triangle
    support: committed ``(s,m) in a``, ``(m,t) in b``, ``(s,t) in head`` is a
    loop whose closure ties the three transports. The floor bounds compute and
    junk; the SEMANTIC vetting is the defect gate in :func:`infer` — a mined
    candidate is only a hypothesis until the fork-projection clears it.
    Deterministic: strongest support first, names break ties."""
    out_idx: dict[str, dict] = {r: defaultdict(set) for r in eligible}
    for r in eligible:
        for s, t in cmaps[r]:
            out_idx[r][s].add(t)
    cands = []
    for a in eligible:
        for b in eligible:
            for head in eligible:
                if head in (a, b):
                    continue
                support = sum(
                    1 for (s, t) in cmaps[head] if s != t and any(
                        m not in (s, t) and t in out_idx[b].get(m, ())
                        for m in out_idx[a].get(s, ()))
                )
                if support >= max(2, round(exception_fraction * len(cmaps[head]))):
                    cands.append((-support, head, a, b))
    cands.sort()
    return [(h, a, b) for _s, h, a, b in cands]


def _solve(classes: list, links: list, comps: list, symmetric: set,
           motif: set) -> tuple[dict, object]:
    """The homogeneous loop-constraint system, solved by propagation.

    Variables: one transport per live class. Equations: ``g_b = -g_a`` per
    converse link, ``g_h = g_a + g_b`` per accepted composition, ``g_s = 0``
    per symmetric class. The system is homogeneous, so each constraint
    component carries one free scale; a conflict forces that scale to 0 (the
    old odd-cycle rule, generalized). Solutions are scaled to minimal
    integers with the alphabetically-first nonzero class positive — the same
    gauge convention as before, which the 2-cycle-only case reproduces
    exactly (±1). Where propagation stalls (an underdetermined composition),
    the first unknown is re-seeded: any solution of a homogeneous
    underdetermined system is a valid gauge choice, and the seed order makes
    it deterministic. Returns ``(coeff, find)``: integer transport per live
    class and the component-root function."""
    from fractions import Fraction
    from math import gcd, lcm

    live = [r for r in classes if r not in motif]
    parent = {r: r for r in live}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        if find(a) != find(b):
            parent[find(a)] = find(b)
    for h, a, b in comps:
        for x in (a, b):
            if find(h) != find(x):
                parent[find(h)] = find(x)

    members: dict[str, list] = defaultdict(list)
    for r in live:
        members[find(r)].append(r)

    coeff: dict[str, int] = {}
    for root in sorted(members):
        ms = sorted(members[root])
        clinks = [(a, b) for a, b in links if find(a) == root]
        ccomps = [(h, a, b) for h, a, b in comps if find(h) == root]
        c: dict[str, Fraction] = {m: Fraction(0) for m in ms if m in symmetric}
        conflict = False
        while not conflict and len(c) < len(ms):
            c[next(m for m in ms if m not in c)] = Fraction(1)
            changed = True
            while changed and not conflict:
                changed = False
                for a, b in clinks:
                    for x, y in ((a, b), (b, a)):
                        if x in c:
                            v = -c[x]
                            if y not in c:
                                c[y], changed = v, True
                            elif c[y] != v:
                                conflict = True
                for h, a, b in ccomps:
                    # g_h - g_a - g_b = 0, as coefficients per DISTINCT class
                    # (a == b folds to -2, so g_h = 2*g_a solves either way)
                    k: dict[str, int] = {}
                    for cls, kk in ((h, 1), (a, -1), (b, -1)):
                        k[cls] = k.get(cls, 0) + kk
                    unknown = [cls for cls, kk in k.items() if kk and cls not in c]
                    if len(unknown) > 1:
                        continue
                    if not unknown:
                        if sum(kk * c[cls] for cls, kk in k.items() if kk) != 0:
                            conflict = True
                        continue
                    u = unknown[0]
                    rest = sum(kk * c[cls] for cls, kk in k.items() if kk and cls != u)
                    c[u], changed = Fraction(-rest, k[u]), True
                if any(m in symmetric and c.get(m, Fraction(0)) != 0 for m in ms):
                    conflict = True
        if conflict:
            c = {m: Fraction(0) for m in ms}      # over-constrained: magnitude 0
        nz = [v for m in ms if (v := c.get(m, Fraction(0))) != 0]
        if nz:
            scale = Fraction(gcd(*(abs(v.numerator) for v in nz)),
                             lcm(*(v.denominator for v in nz)))
            if next(v for m in ms if (v := c.get(m, Fraction(0))) != 0) < 0:
                scale = -scale
            c = {m: v / scale for m, v in c.items()}
        for m in ms:
            coeff[m] = int(c.get(m, Fraction(0)))
    return coeff, find


def infer(cmaps: dict[str, set], exception_fraction: float = 0.2,
          compositions: bool = True):
    """Per-relation-class transports over Z from LOOP evidence.

    ``cmaps`` maps relation class → set of eligible ``(source, target)``
    pairs. Returns ``(sectors, groups)`` where ``sectors[r]`` is a
    :class:`~relweblearner.sectors.RelationSector` and ``groups[r]`` is the
    class's constraint-group root — classes share a group only when loop
    evidence ties their transports together.

    Two kinds of loop are detectable without coordinates:

    * **2-cycles** (converse pairs): each is an equation ``g(R1) + g(R2) = 0``.
    * **3-cycles** (compositions): committed triangles witness
      ``g(head) = g(a) + g(b)`` — how a skip relation is DISCOVERED to be two
      steps. Candidates are mined by support (:func:`_mine_compositions`) but
      admitted only through a DEFECT GATE, one at a time strongest-first: the
      constraint set is fork-solved and re-projected, and the candidate is
      refused if any previously-antisymmetric class degrades (a junk
      composition that zeroes or demotes a live group) or if the projection's
      defect count rises past the head class's exception budget. A sub-budget
      rise is ACCEPTED — a lie among the head's edges becomes a visible
      defect, which must not veto a true composition (the standing P2 rule:
      sub-budget contradiction is reported noise, never a classification
      flip). This is the geometric answer to threshold rule-mining: the
      miner proposes, the gauge geometry disposes.

    What the constraints cannot fix — one scale and sign per constraint
    component — is gauge, set deterministically (minimal integers,
    alphabetically-first class positive): a lone converse pair is ±1 exactly
    as before; a composed skip comes out ±2 in the SAME group as its steps.
    All thresholds follow the P2 exception rule: a sub-budget minority of
    contrary pairs is noise to be REPORTED as defects, never enough to flip a
    classification (the repeat-lie discipline)."""
    classes = sorted(cmaps)
    owner: dict[tuple, set] = defaultdict(set)
    for r in classes:
        for e in cmaps[r]:
            owner[e].add(r)

    self_conv: Counter = Counter()   # directed edges whose converse is in the SAME class
    link_w: Counter = Counter()      # sorted class pair -> directed converse witnesses
    for r in classes:
        for (s, t) in cmaps[r]:
            if s == t:
                continue
            for r2 in owner.get((t, s), ()):
                if r2 == r:
                    self_conv[r] += 1
                else:
                    link_w[tuple(sorted((r, r2)))] += 1

    n_edges = {r: len(cmaps[r]) for r in classes}
    frac_sym = {r: (self_conv[r] / n_edges[r]) if n_edges[r] else 0.0 for r in classes}

    symmetric = {r for r in classes if frac_sym[r] >= 1.0 - exception_fraction}
    motif = {r for r in classes
             if exception_fraction < frac_sym[r] < 1.0 - exception_fraction}

    # significant converse links union classes into constraint groups; a link
    # below the budget floor is noise. floor >= 2: the docstring's own rule,
    # enforced — with a floor of 1 (which max(1, ...) yields for any class
    # under ~8 edges) a SINGLE committed pair — one k-corroborated lie whose
    # converse happens to land in another class — welds two gauge groups, and
    # a weld poisons every transport in both (their magnitudes are mutually
    # gauged).
    links: list[tuple] = []
    for (a, b), w in sorted(link_w.items()):
        if a in motif or b in motif:
            continue
        floor = max(2, round(exception_fraction * min(n_edges[a], n_edges[b])))
        if w // 2 >= floor:                       # w counts both directions per pair
            links.append((a, b))

    def assemble(comps: list) -> tuple[dict, dict]:
        coeff, find = _solve(classes, links, comps, symmetric, motif)
        touched = set(symmetric) | {x for l in links for x in l} \
            | {x for cc in comps for x in cc}
        sectors: dict[str, RelationSector] = {}
        groups: dict[str, str] = {}
        for r in classes:
            n = n_edges[r]
            if r in motif:
                groups[r] = r
                sectors[r] = RelationSector(r, NON_HOMOGENEOUS, None, frac_sym[r], n)
                continue
            groups[r] = find(r)
            if r not in touched:
                sectors[r] = RelationSector(r, UNCONSTRAINED, 1, 1.0, n)
            elif coeff[r] == 0:
                support = frac_sym[r] if r in symmetric else 1.0
                sectors[r] = RelationSector(r, SYMMETRIC, 0, support, n)
            else:
                sectors[r] = RelationSector(r, ANTISYMMETRIC, coeff[r],
                                            1.0 - frac_sym[r], n)
        return sectors, groups

    sectors, groups = assemble([])
    if not compositions:
        return sectors, groups

    eligible = [r for r in classes if r not in motif]
    accepted: list[tuple] = []
    base_count, base_anti = None, None
    for h, a, b in _mine_compositions(cmaps, eligible, exception_fraction):
        # extend KNOWN structure: both body classes must already carry a
        # constrained transport. An UNCONSTRAINED head is fine — being
        # constrained by the composition is the point (a skip class whose
        # converse frame never induced still joins the step group here).
        if any(sectors[x].sector not in (ANTISYMMETRIC, SYMMETRIC) for x in (a, b)):
            continue
        if sectors[h].sector == NON_HOMOGENEOUS:
            continue
        if base_count is None:
            base_webs = build_group_webs(cmaps, sectors, groups, name="infer:gate")
            base_count = defect_report(base_webs)["count"]
            base_anti = {r for r, s in sectors.items() if s.sector == ANTISYMMETRIC}
        ts, tg = assemble(accepted + [(h, a, b)])
        if any(ts[r].sector != ANTISYMMETRIC for r in base_anti):
            continue                              # degrades a live group: refused
        twebs = build_group_webs(cmaps, ts, tg, name="infer:gate")
        tcount = defect_report(twebs)["count"]
        budget = exception_fraction * max(1, n_edges[h])
        if tcount - base_count > budget:
            # Attribute before refusing: an EXISTING culprit — a committed lie
            # already on display — explains MORE fundamental cycles once the
            # merge densifies its group, but it is the same one edge, not new
            # contradiction. Charge culprits; refuse only if the candidate
            # itself brings over-budget new ones.
            cap = int(exception_fraction * sum(n_edges.values())) + 1
            base_cul = sum(sum(_peel(w, cap).values()) for w in base_webs.values())
            trial_cul = sum(sum(_peel(w, cap).values()) for w in twebs.values())
            if trial_cul - base_cul > budget:
                continue                          # over-budget new culprits: refused
        accepted.append((h, a, b))
        sectors, groups = ts, tg
        base_webs, base_count = twebs, tcount
        base_anti = {r for r, s in sectors.items() if s.sector == ANTISYMMETRIC}
    return sectors, groups


def build_group_webs(
    cmaps: dict[str, set],
    sectors: dict[str, RelationSector],
    groups: dict[str, str],
    name: str = "creature",
    journal=None,
    cf: bool = False,
) -> dict[str, Web]:
    """One algebra-valued :class:`Web` per constraint group.

    Motif (non-homogeneous) classes carry no transport and are left out —
    their edges remain in the store as facts; they are simply not composable.
    Insertion order is fully sorted so the projection is deterministic.

    ``journal``/``cf`` thread through to :class:`Web`. The creature's CACHED
    projections pass neither: re-deriving a projection from already-committed
    facts is bookkeeping whose constituting acts are already on the bus, and
    re-emitting thousands of ``add_edge`` traces per staleness rebuild would
    bury the act stream. SIMULATION webs (:func:`simulate_merge`) do ride the
    shared bus, ``cf``-flagged — imagined episodes are episodes (invariant #8).
    """
    members: dict[str, list[str]] = defaultdict(list)
    for r, gid in groups.items():
        if sectors[r].transport is not None:
            members[gid].append(r)
    webs: dict[str, Web] = {}
    for gid, rs in sorted(members.items()):
        w = Web(IntegerGroup(), name=f"{name}:{gid}", journal=journal, cf=cf)
        for r in sorted(rs):
            g = sectors[r].transport
            for (s, t) in sorted(cmaps[r]):
                w.add_edge(s, t, r, g)
        webs[gid] = w
    return webs


def simulate_merge(
    cmaps: dict[str, set],
    class_a: str,
    class_b: str,
    exception_fraction: float = 0.2,
    journal=None,
    name: str = "sim",
) -> dict:
    """Fork-score-discard for a relation-class merge (invariant #8).

    A merge of two relation classes is a consequential move: it changes which
    loops exist and which transports are forced. So it is IMAGINED first — the
    class maps are re-inferred and re-projected twice, once as they stand and
    once with ``class_b`` folded into ``class_a`` — and the verdict compares
    the two counterfactual projections. The real projection is never touched;
    both trial builds ride the shared ``journal`` ``cf``-flagged, so the
    imagining itself is on the record and can never enter belief
    (:func:`relweblearner.simulate.committed_has_no_cf` holds by construction).

    Scoring is restricted to the constraint groups ``class_a`` and ``class_b``
    belong to: a merge only rewires loop evidence through its own classes'
    gauge groups, so distant groups cannot change verdict-relevant mass — the
    restriction is an efficiency statement, not an approximation of policy.

    REFUSED iff either:

      * the merged class comes out NON-HOMOGENEOUS when neither part was — the
        merge destroys composability (a motif demotion is a worsening even
        though a motif web carries no holonomy to count); or
      * defect mass over the touched groups strictly increases — the merge
        manufactures contradictions.

    Returns ``{"commit", "reason", "defect_delta", "degrades"}``.
    """
    base_sectors, base_groups = infer(cmaps, exception_fraction)
    ga = base_groups.get(class_a, class_a)
    gb = base_groups.get(class_b, class_b)
    touched = {r for r, g in base_groups.items() if g in (ga, gb)}
    base_slice = {r: cmaps[r] for r in touched if r in cmaps}

    bs, bg = infer(base_slice, exception_fraction)
    bwebs = build_group_webs(base_slice, bs, bg, name=f"{name}:base", journal=journal, cf=True)
    base_mass = defect_report(bwebs)["mass"]

    trial_slice = {r: set(e) for r, e in base_slice.items() if r != class_b}
    trial_slice[class_a] = trial_slice.get(class_a, set()) | cmaps.get(class_b, set())
    ts, tg = infer(trial_slice, exception_fraction)
    twebs = build_group_webs(trial_slice, ts, tg, name=f"{name}:trial", journal=journal, cf=True)
    trial_mass = defect_report(twebs)["mass"]

    was_motif = any(
        base_sectors[r].sector == NON_HOMOGENEOUS
        for r in (class_a, class_b) if r in base_sectors
    )
    merged = ts.get(class_a)
    degrades = merged is not None and merged.sector == NON_HOMOGENEOUS and not was_motif
    delta = trial_mass - base_mass
    if degrades:
        return {"commit": False, "degrades": True, "defect_delta": delta,
                "reason": "merged class loses homogeneity (motif demotion)"}
    if delta > 0:
        return {"commit": False, "degrades": False, "defect_delta": delta,
                "reason": f"defect mass would rise by {delta}"}
    return {"commit": True, "degrades": False, "defect_delta": delta, "reason": "clean"}


def simulate_fission(
    cmaps: dict[str, set],
    moves: dict[tuple, tuple],
    exception_fraction: float = 0.2,
    journal=None,
    name: str = "sim",
) -> dict:
    """Fork-score-discard for a node fission (invariant #8) — merge's dagger.

    ``moves`` maps a committed ``(src, tgt)`` pair to its post-split key (one
    endpoint re-bound to a sense node). Like :func:`simulate_merge`, the class
    maps are re-inferred and re-projected twice — as they stand and with the
    moves applied — on cf-flagged trial webs riding the shared ``journal``,
    and scoring is restricted to the constraint groups whose classes contain a
    moved pair (the only groups whose loop evidence the split rewires).

    REFUSED iff either:

      * a class that was composable comes out NON-HOMOGENEOUS — the split
        destroys composability; or
      * defect mass fails to STRICTLY drop — a fission that removes no
        contradiction is a free node the growth discipline must not pay for.

    Returns ``{"commit", "reason", "defect_delta", "degrades"}``.
    """
    _sectors, base_groups = infer(cmaps, exception_fraction)
    moved_pairs = set(moves)
    touched_classes = {r for r, pairs in cmaps.items() if pairs & moved_pairs}
    gids = {base_groups.get(r, r) for r in touched_classes}
    touched = {r for r, g in base_groups.items() if g in gids}
    base_slice = {r: cmaps[r] for r in touched if r in cmaps}

    bs, bg = infer(base_slice, exception_fraction)
    bwebs = build_group_webs(base_slice, bs, bg, name=f"{name}:base", journal=journal, cf=True)
    base_mass = defect_report(bwebs)["mass"]

    trial_slice = {r: {moves.get(p, p) for p in pairs} for r, pairs in base_slice.items()}
    ts, tg = infer(trial_slice, exception_fraction)
    twebs = build_group_webs(trial_slice, ts, tg, name=f"{name}:trial", journal=journal, cf=True)
    trial_mass = defect_report(twebs)["mass"]

    degrades = any(
        ts[r].sector == NON_HOMOGENEOUS and bs[r].sector != NON_HOMOGENEOUS
        for r in trial_slice if r in ts and r in bs
    )
    delta = trial_mass - base_mass
    if degrades:
        return {"commit": False, "degrades": True, "defect_delta": delta,
                "reason": "split demotes a composable class to a motif"}
    if delta >= 0:
        return {"commit": False, "degrades": False, "defect_delta": delta,
                "reason": "split would remove no defect mass"}
    return {"commit": True, "degrades": False, "defect_delta": delta, "reason": "clean"}


def _web_without(web: Web, drop: set) -> Web:
    """A fresh, journal-free copy of ``web`` minus the ``(u, v, rel)`` keys in
    ``drop`` — trial bookkeeping for the culprit peel, never belief (converses
    re-derive from the primaries, as always)."""
    w = Web(web.algebra, name=f"{web.name}:trial")
    for e in web.edges():
        if (e.u, e.v, e.rel) not in drop:
            w.add_edge(e.u, e.v, e.rel, e.value)
    return w


def _peel(web: Web, cap: int) -> Counter:
    """Greedy culprit attribution for one group web: the class-charged size of
    an (approximately) minimal edge set explaining every defect. One lying
    edge that smears residuals across many fundamental cycles charges its
    class ONCE; whatever no peel explains charges its own edge's class.
    Deterministic (sorted candidate order); trial webs are journal-free
    bookkeeping. Shared by :func:`non_homogeneous_by_defect` (demotion) and
    :func:`infer`'s composition gate (admission)."""
    charged: Counter = Counter()
    trial, ds = web, defects(web)
    while ds and sum(charged.values()) < cap:
        best_e, best_n = None, len(ds)
        for e in sorted(trial.edges(), key=lambda e: (repr(e.u), repr(e.v), e.rel)):
            n = len(defects(_web_without(trial, {(e.u, e.v, e.rel)})))
            if n < best_n:
                best_e, best_n = e, n
        if best_e is None:
            break                                  # no single edge explains anything more
        trial = _web_without(trial, {(best_e.u, best_e.v, best_e.rel)})
        charged[best_e.rel] += 1
        ds = defects(trial)
    for d in ds:
        charged[d.edge.rel] += 1
    return charged


def non_homogeneous_by_defect(
    cmaps: dict[str, set], webs: dict[str, Web], exception_fraction: float = 0.2
) -> set:
    """Classes whose edges are defective beyond the exception budget: no
    constant transport explains them (P2's ``double`` verdict, read off the
    actual holonomy rather than a residual fit). The caller demotes these to
    motifs and rebuilds; a sub-budget defect stays VISIBLE as a defect.

    Counting raw defects is not enough: one lying edge that lands ON the BFS
    spanning tree smears its residual across every fundamental cycle through
    it, so a single adversarial page could read as class-wide incoherence and
    demote a true transport — precisely what the exception rule forbids ("one
    mislabeled example cannot flip the classification"). So when the naive
    count exceeds a class's budget, the defects are attributed first: CULPRIT
    edges are peeled greedily (each removal charged to the culprit's own
    class, removals capped by the summed budgets), and a class is demoted only
    if culprits-plus-remaining-defects still exceed its budget. A lie explains
    all its cycles with one peel and stays a reported defect; a genuinely
    non-homogeneous class (``double``) loses at most one defect per peel and
    still demotes. Trial webs are plain bookkeeping (no journal): the peel
    imagines nothing the record needs."""
    bad: set = set()
    for w in webs.values():
        ds = defects(w)
        if not ds:
            continue
        budget = {r: exception_fraction * max(1, len(cmaps.get(r, ())))
                  for r in {e.rel for e in w.edges()}}
        naive = Counter(d.edge.rel for d in ds)
        if not any(c > budget.get(r, exception_fraction) for r, c in naive.items()):
            continue
        charged = _peel(w, cap=int(sum(budget.values())) + 1)
        for r, c in charged.items():
            if c > budget.get(r, exception_fraction):
                bad.add(r)
    return bad


def defect_report(webs: dict[str, Web]) -> dict:
    """Defect census over the group webs — independent nonzero-holonomy classes
    and total defect mass (invariant #9's objective, made visible)."""
    count, mass, examples = 0, 0.0, []
    for gid, w in sorted(webs.items()):
        ds = defects(w)
        count += len(ds)
        mass += defect_mass(w)
        examples += [
            {"group": gid, "class": d.edge.rel,
             "edge": [d.edge.u, d.edge.v], "residual": d.residual}
            for d in ds[:4]
        ]
    return {"count": count, "mass": mass, "examples": examples[:8]}


def derive(web: Web, start, value, max_depth: int = 6) -> list:
    """Nodes whose composed transport from ``start`` equals ``value``.

    Breadth-first over :meth:`Web.neighbors` (converse edges enter via the
    dagger, so a taught ``ten -[after]-> nine`` witnesses the never-taught
    ``nine is before ten``), accumulating the composed value along the BFS
    tree. Deterministic (sorted expansion); depth-bounded; ``start`` itself is
    never an answer. Pure — the walk emits nothing and mutates nothing."""
    if start not in web.nodes:
        return []
    algebra = web.algebra
    acc = {start: algebra.identity}
    frontier, hits = [start], []
    for _ in range(max_depth):
        nxt = []
        for u in sorted(frontier, key=repr):
            for v, g, _eid in web.neighbors(u):
                if v in acc:
                    continue
                a = algebra.compose(acc[u], g)
                if a is None:                    # undefined transport (partial algebra)
                    continue
                acc[v] = a
                if a == value:
                    hits.append(v)
                nxt.append(v)
        frontier = nxt
        if not frontier:
            break
    return sorted(hits)


class SectorGrowth(GrowthEngine):
    """The stock P1 growth discipline with creature-scoped fresh names.

    ``alloc`` yields globally fresh opaque ids (the creature owns the
    sequence), so a node posited in one group web can never collide with a
    posit in another, nor with any surface word, across reloads."""

    def __init__(self, P: int, alloc):
        super().__init__(P=P)
        self._alloc = alloc

    def _fresh_names(self, web: Web, count: int) -> list[str]:
        names: list[str] = []
        while len(names) < count:
            cand = self._alloc()
            if cand not in web.nodes:
                names.append(cand)
        return names
