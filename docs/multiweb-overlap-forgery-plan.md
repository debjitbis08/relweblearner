# The overlap forgery (E2b) — pre-registration of the decisive experiment

*Written 2026-07-14, BEFORE any E2b code is run. The predictions in §6 are
frozen with this document; whatever the run says is what gets reported. This
experiment is the #1 licensed diagnosis of docs/design-problem.md §10, and the
only one §9 lists as able to falsify the conjecture itself. It shares the world
generator, stable-region finder, and partial-mapping machinery of
docs/multiweb-plan.md / `src/relweblearner/bench/multiweb.py`; it adds one new
world arm and one new detector, both specified here.*

## 1. The question this settles

design-problem.md §2 established, from the code, that the original
coherent-forgery success was NOT geometry. `project()` in bench-multiweb emits
exactly two states — corroborated or not — and the fresh-node forgery (E1) and
the solo truth (E2) both land in the SAME "not corroborated" state:
`correspondence()` returns 0 for both because neither touches the overlap. E1
was rejected by the closed-world projection **policy P1** (only ≥ 2-view
structure commits), not by any incompatibility. No view ever contradicted the
forgery; no view *could* — it was built from fresh, never-co-witnessed nodes.

The open question, and the pivot of the whole framework (§9): **is there a
forgery that is rejected by GEOMETRY — as a genuinely different TYPE — with no
appeal to P1?** design-problem.md predicts yes, and names the instrument: an
**overlap forgery**, where liars wire a false pattern among CO-WITNESSED nodes,
so that view agreement is violated *on the overlap itself*. If such a lie is
detected as an extension/gluing failure (Ext = empty, §4) and cleanly separated
from E1/E2 (which produce no residual at all), then the geometric-obstruction
half of the conjecture carries real weight in the ensemble setting. If it is
NOT — if the overlap contradiction is indistinguishable from mere lack of
support — then obstruction adds nothing over P1 + provenance, and the geometric
half deflates to the linear thinking layer only (§9). This experiment is the
empirical content of **theorem T2** (incompatible overlap data ⇒ Ext = ∅).

The obstruction machinery already exists elsewhere in this project and is
ported, not invented: the graphlog **destructive-interference gate**
(`multiweb_graphlog.py`, `agreement()`, `EXT_AGREE = 0.5`) does a *trial
gluing* and counts CONTRADICTED evidence — triples present on one side whose
image is absent on the other — killing confabulated identifications. E2b asks
whether the same residual-of-an-attempted-extension test separates an overlap
forgery in the bench-multiweb setting.

## 2. The world modification

Everything in `generate()` is unchanged (60 entities, 6 communities of 10,
K = 3 views, coverage 0.8, anchor rate 0.4, the fresh-node forgery E1, the
solo control E2). One arm is ADDED, so a single seed now carries all three
diagnostics side by side:

**The overlap forgery — a false merge on co-witnessed nodes.** Pick two true
communities **A** and **B** that are BOTH *multi-covered* (visible in ≥ 2 views,
so both are genuinely on the overlap and anchorable — the property E1's fresh
nodes lack by construction). In **view 0's web only**, add a dense bundle of
strong bridge edges between a subset of A and a subset of B:

- endpoints are drawn preferentially from nodes that carry a cross-view **anchor**
  (so the lie lands where agreement can be checked, not on view-0-private nodes);
- `MERGE_FRAC` of the cross pairs (a-node, b-node) are wired;
- bridge weights are sampled from the SAME empirical intra-community weight
  distribution used for E1 (`intra_w`), so the merged A∪B block is internally
  statistically indistinguishable from one real community — coherence is
  matched by construction, exactly as for the fresh-node forgery.

The intent, tuned before the scored run and then frozen: in **view 0** Louvain
merges A and B into ONE stable region (it passes `STAB_TAU`); in **views 1, 2**
A and B remain SEPARATE stable regions. The falsehood is now a claim about the
overlap — "these co-witnessed things are one community" — that the other views
directly refute, edge by edge, on nodes they too can see.

Selection detail declared up front to avoid a binomial-arithmetic failure of
the kind that forced the multiweb-plan §2 anchor-rate amendment: A and B are
chosen among multi-covered communities whose co-visible members clear the
`CORR_MIN_IMG = 2` mapped-member floor in at least one other view under the
0.4 anchor rate; a seed where no such pair exists is recorded as
`e2b_constructible = False` and excluded from the E2b rates (reported
explicitly, never silently dropped).

## 3. The obstruction detector (the new machinery)

bench-multiweb's `correspondence()` measures only image *concentration* — how
tightly a region's mapped image lands in a single region of the other web. That
metric alone would reject the false merge too, but only as *low concentration*
(the split image lands ~half in A's region, ~half in B's) — **the same reading
it gives E1, and therefore no evidence of a different type.** E2b adds a
distinct, policy-free test.

For a stable region **R** in web *i*, and each other web *j*, using the existing
partial mapping `maps[(i, j)]` and the same backbone rule (`EXT_BACKBONE`) that
governs identity evidence everywhere else:

- iterate the **backbone edges** (u, v) of web *i* with both u, v ∈ R and both
  mapped into web *j*;
- if web *j* carries a backbone edge (M[u], M[v]): `matched += min(w_i, w_j)`;
- otherwise (the mapped images are NOT strongly connected in *j*):
  `contradicted += w_i`.
- **obstruction_j(R) = contradicted / (matched + contradicted)**, defined 0 when
  the denominator is 0 (nothing was checkable).
- **R is OBSTRUCTED** iff max_j obstruction_j(R) ≥ `OBS_THETA` (frozen at 0.5,
  the ported `EXT_AGREE` value — a trial gluing that disagrees on at least half
  its checkable weight is an extension failure, not a mapping gap).

This is `agreement()` read on co-occurrence edges instead of composition
triples: identical logic (present-here-absent-there evidence under a trial
identification), identical threshold, applied in the bench-multiweb substrate.

The typed classifier, aligning each arm with the Ext(s) table of
design-problem.md §4 — evaluated per region, no P1 counting involved:

| signal | Ext(s) | type | which arm |
|---|---|---|---|
| obstruction ≥ OBS_THETA | empty | **obstructed** | overlap forgery (E2b) |
| obstruction < OBS_THETA, corroboration ≥ 1 | singleton | **committed** | true multi-covered regions |
| obstruction < OBS_THETA, corroboration 0 | larger | **unsupported** | fresh forgery (E1), solo truth (E2) |

The decisive property to check: E1 and E2 have **no mapped backbone edges to
contradict** (E1's nodes have no anchors; E2 is single-view), so their
obstruction is identically 0 — they can only ever be *unsupported*, never
*obstructed*. If E2b lands in a cell E1/E2 provably cannot reach, obstruction is
a real, typed, policy-free signal.

## 4. Metrics (50 seeds, held out — frozen tune first, then the scored run)

- **Q1 merge stability** — the A∪B false merge is discovered as ONE stable
  region of web 0 (coherence + stability do not filter it), and A, B are TWO
  separate stable regions in webs 1 and 2 (the refutation is available).
- **Q2 obstruction score** — distribution of the E2b merged region's
  max_j obstruction_j, against the same score computed for (a) E1's forged
  region, (b) E2's solo region, (c) true multi-covered regions.
- **Q3 typed outcome** — each of {E2b, E1, E2, true} classified into
  {obstructed, committed, unsupported} by §3; the cross-tabulation is the
  headline result.
- **Q4 policy independence** — E2b's rejection is attributed: obstructed (no P1
  appeal) vs would-need-P1 (obstruction < OBS_THETA and rejected only by the
  ≥ 2-view rule). Fraction of E2b rejections that are geometric, not policy.
- **Q5 collateral** — concept recall and purity on the true communities,
  recomputed with the E2b arm present, vs the bench-multiweb baseline; and the
  false-positive rate of the obstruction detector on true corroborated regions.

## 5. Frozen predictions

- **Q-A (merge is coherent & stable, ≥ 0.90 of constructible seeds):** the false
  merge passes `STAB_TAU` as one region in web 0, and A, B are separate in
  webs 1, 2, in ≥ 0.90 of seeds. If not, the bridge is too weak or too strong
  to constitute an overlap forgery — retune before the scored run and report the
  tune. (Parallels multiweb-plan P-A: the lie must survive the one-web test, or
  the ensemble test is unmotivated here.)
- **Q-B (obstruction separation — the decisive prediction):** the E2b merged
  region has max_j obstruction_j ≥ `OBS_THETA` in ≥ 0.90 of constructible
  seeds, while E1's forged region and E2's solo region have obstruction < 0.10
  in ≥ 0.95 of seeds (expected exactly 0 — no checkable edges). The
  distributions are essentially disjoint: the overlap forgery produces a
  contradiction residual; the fresh forgery and solo truth produce none.
- **Q-C (typed rejection, ≥ 0.90):** E2b is classified **obstructed** while
  E1 and E2 are classified **unsupported**, in ≥ 0.90 of seeds — a genuinely
  different TYPE, the property design-problem E2b/E2 demand.
- **Q-D (policy independence, ≥ 0.90):** ≥ 0.90 of E2b rejections are geometric
  (obstruction ≥ OBS_THETA), i.e. they do NOT require P1. This is the claim that
  the geometric half carries weight: the overlap forgery would be caught even if
  the closed-world policy were switched off.
- **Q-E (no collateral):** the obstruction detector flags true corroborated
  regions in < 0.05 of cases; concept recall ≥ 0.80 and purity ≥ 0.90 are
  preserved within noise of the bench-multiweb baseline (the detector does not
  buy type-separation by corrupting real semantics).

## 6. Falsification criteria (mapped to design-problem.md §9)

- **The conjecture-level falsifier.** If Q-B fails — E2b's obstruction
  distribution overlaps E1/E2's (both near 0), or E2b's is not reliably above
  OBS_THETA — then incompatible overlap data is NOT detected as a different type
  in practice. Per design-problem §9, obstruction then adds nothing over P1 +
  provenance, and **the geometric half of the conjecture deflates to the linear
  thinking layer only.** This outcome is reported with the full prominence of a
  headline result, not as a bug to be patched: it would redirect T1–T3 away from
  the geometric obstruction machinery. (A tempting move — strengthen the bridge
  until Q-B passes — is disallowed after the §5 freeze except as a declared,
  separately-reported retune of the *world*, never of `OBS_THETA`.)
- If Q-A fails (no stable coherent merge can be built), E2b is inconstructible
  in this substrate and the experiment is inconclusive here, not a refutation —
  report the construction failure and what it implies about the world model.
- If Q-C passes but Q-D fails (E2b is obstructed *and* would also be caught by
  P1 in most seeds), the geometric signal is real but redundant with policy in
  this world; report the overlap that P1 and obstruction share, since it bounds
  how decisive the geometric half is.
- If Q-E fails (true regions flagged obstructed), the detector's backbone/
  mapping reading is leaking — an implementation fault, fixed before Q-B/Q-C are
  interpreted, exactly as the P-D weight-1 leak was handled in multiweb-plan §7b.

## 7. Relation to what exists

E2b is an extension of `src/relweblearner/bench/multiweb.py`: one arm added to
`generate()` (the false merge), one detector added alongside `correspondence()`
(the obstruction score), one classifier and five metrics added to `run_seed()`.
It reuses `stable_regions`, `all_mappings`, `extend_mapping`, `EXT_BACKBONE`,
`STAB_TAU`, `CORR_THETA`, and the anchor machinery unchanged. It introduces
exactly one new constant, `OBS_THETA = 0.5`, ported from the graphlog
`EXT_AGREE` gate and frozen here.

Discipline (design-problem.md §10): E2b runs before T1–T3 are attempted, because
its outcome determines whether the geometric-obstruction half of the framework
is worth formalizing at all. It is empirical work licensed on the existing
benches — it neither validates nor requires the T0 model/data separation, and it
ships its result (pass or fail) with pre-registered predictions, like every
other bench in this project.
