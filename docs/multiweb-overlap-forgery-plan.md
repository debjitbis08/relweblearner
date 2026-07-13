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

### 2a. Bring-up world retune (made before the scored run at commit `8ed73c1`; recorded here in the 2026-07-14 post-run review)

The Q-A bring-up (seeds 0–11) found the §2 spec as written too weak to
constitute an overlap forgery: bridging only the ~3 anchored members of each
community left Louvain unmerged (merge_stable 2/8) — the bulk of each ~8-node
community stayed uncrossed. The licensed fix (§5 Q-A: "retune before the
scored run and report the tune"): the bridge is wired across the **full
view-0 memberships** of A and B, uniformly at `MERGE_FRAC = 0.6`, with **no
anchored preference** — the anchored members are included as a subset, so the
checkable anchored-pair edges the detector reads are supplied as before.
`MERGE_FRAC` itself was never changed. This is a world-tune under Q-A's
explicit license, frozen before any scored seed; it was reported in the
implementation commit message but this document was not amended at the time —
this subsection backfills the record so the plan and the code agree. Two
smaller operational details, disclosed for the same reason: the (A, B, j)
triple is chosen by MAXIMIZING the smaller anchored count over a common
witness view (not sampled among qualifying pairs — a mild tilt toward
checkability; every qualifying pair already clears the ≥ 2 floor), and
`merge_stable` is operationalized as one web-0 stable region containing
≥ `CORR_MIN_IMG` members of EACH side (looser than "A∪B as one region" —
though in the scored data the merged region in fact contains 100% of both
memberships in every seed inspected).

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
- record, per web *j*: `contra_j(R)` = the COUNT of contradicted backbone edges,
  and the weight ratio `ratio_j(R) = contradicted / (matched + contradicted)`
  (defined 0 when nothing was checkable);
- the region's residual is `contra(R) = max_j contra_j(R)` (the strongest single
  refuting view), with `ratio(R)` its companion ratio.

This is `agreement()` read on co-occurrence edges instead of composition
triples: identical logic (present-here-absent-there evidence under a trial
identification), applied in the bench-multiweb substrate.

### 3a. Pre-run amendment (2026-07-14, BEFORE any E2b code was run)

The v1 §3 gated OBSTRUCTED on the weight *ratio* ≥ `OBS_THETA = 0.5` (ported
`EXT_AGREE`). An arithmetic check *before writing the detector* — the same class
of check that forced the multiweb-plan §2 anchor amendment — shows this
miscalibrated. At coverage 0.8 / anchor rate 0.4 a community has ~3 anchored
view-0 members per other view, so the merged region carries ~3 A-internal + ~3
B-internal *matched* backbone edges (real structure that transports) diluting
~5 A–B *contradicted* bridges: ratio ≈ 5/11 ≈ 0.45, **below 0.5 for a purely
combinatorial reason** unrelated to the hypothesis. Raising the bridge count to
clear 0.5 would be world-tuning toward the prediction (disallowed, §6); lowering
`OBS_THETA` would look like weakening to force a pass.

The principled fix, faithful to design-problem §2 (the signal is "a genuine
**residual** of an attempted extension") and to the graphlog/carrier mining-floor
precedents: gate on the residual COUNT, not the diluted ratio. The three-way
type separation lives in the pair `(matched, contradicted)`, not their ratio:

- **R is OBSTRUCTED** iff `contra(R) ≥ OBS_MIN_CONTRA` (frozen at **2**, mirroring
  `CORR_MIN_IMG` — at least two independent refuting backbone edges, so one noisy
  mapping cannot manufacture a type). `ratio(R)` and `OBS_THETA = 0.5` are
  retained as REPORTED secondaries, not the classifier gate.

Only the gate changes; the detector, the arms, and the Q-A…Q-E structure are
otherwise as frozen at commit `eeec1d1`. No E2b run has occurred; this is a
data-free correction, re-committed before the bring-up.

The typed classifier, aligning each arm with the Ext(s) table of
design-problem.md §4 — evaluated per region, no P1 counting involved:

| signal | Ext(s) | type | which arm |
|---|---|---|---|
| contra ≥ OBS_MIN_CONTRA | empty | **obstructed** | overlap forgery (E2b) |
| contra < OBS_MIN_CONTRA, corroboration ≥ 1 | singleton | **committed** | true multi-covered regions |
| contra < OBS_MIN_CONTRA, corroboration 0 | larger | **unsupported** | fresh forgery (E1), solo truth (E2) |

The decisive property to check: E1 and E2 have **no mapped backbone edges to
contradict** (E1's nodes have no anchors; E2 is single-view), so their
obstruction is identically 0 — they can only ever be *unsupported*, never
*obstructed*. If E2b lands in a cell E1/E2 provably cannot reach, obstruction is
a real, typed, policy-free signal.

## 4. Metrics (50 seeds, held out — frozen tune first, then the scored run)

- **Q1 merge stability** — the A∪B false merge is discovered as ONE stable
  region of web 0 (coherence + stability do not filter it), and A, B are TWO
  separate stable regions in webs 1 and 2 (the refutation is available).
- **Q2 obstruction residual** — distribution of the E2b merged region's
  `contra` (and companion `ratio`), against the same measured for (a) E1's
  forged region, (b) E2's solo region, (c) true multi-covered regions.
- **Q3 typed outcome** — each of {E2b, E1, E2, true} classified into
  {obstructed, committed, unsupported} by §3a; the cross-tabulation is the
  headline result.
- **Q4 policy independence** — E2b's rejection is attributed: obstructed (no P1
  appeal) vs would-need-P1 (contra < OBS_MIN_CONTRA and rejected only by the
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
  region has `contra ≥ OBS_MIN_CONTRA` (≥ 2 refuting backbone edges) in ≥ 0.90
  of constructible seeds, while E1's forged region and E2's solo region have
  `contra = 0` in ≥ 0.98 of seeds (expected exactly 0 — no mapped backbone edges
  to refute). The distributions are essentially disjoint: the overlap forgery
  produces a contradiction residual; the fresh forgery and solo truth produce
  none. (Reported alongside the companion `ratio` distributions for context.)
- **Q-C (typed rejection, ≥ 0.90):** E2b is classified **obstructed** while
  E1 and E2 are classified **unsupported**, in ≥ 0.90 of seeds — a genuinely
  different TYPE, the property design-problem E2b/E2 demand.
- **Q-D (policy independence, ≥ 0.90):** ≥ 0.90 of E2b rejections are geometric
  (`contra ≥ OBS_MIN_CONTRA`), i.e. they do NOT require P1. This is the claim
  that the geometric half carries weight: the overlap forgery would be caught
  even if the closed-world policy were switched off.
- **Q-E (no collateral):** the obstruction detector flags true corroborated
  regions in < 0.05 of cases; concept recall ≥ 0.80 and purity ≥ 0.90 are
  preserved within noise of the bench-multiweb baseline (the detector does not
  buy type-separation by corrupting real semantics).

## 6. Falsification criteria (mapped to design-problem.md §9)

- **The conjecture-level falsifier.** If Q-B fails — E2b's `contra` residual
  overlaps E1/E2's (either E2b rarely reaches OBS_MIN_CONTRA, or true/E1/E2
  regions often do through mapping noise) — then incompatible overlap data is
  NOT detected as a different type
  in practice. Per design-problem §9, obstruction then adds nothing over P1 +
  provenance, and **the geometric half of the conjecture deflates to the linear
  thinking layer only.** This outcome is reported with the full prominence of a
  headline result, not as a bug to be patched: it would redirect T1–T3 away from
  the geometric obstruction machinery. (A tempting move — strengthen the bridge
  until Q-B passes — is disallowed after the §5 freeze except as a declared,
  separately-reported retune of the *world*, never of `OBS_MIN_CONTRA`.)
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

E2b is a NEW module `src/relweblearner/bench/multiweb_overlap.py` that imports
and reuses bench-multiweb's machinery UNCHANGED — `generate`, `stable_regions`,
`all_mappings`, `extend_mapping`, `project`, `correspondence`, `EXT_BACKBONE`,
`STAB_TAU`, `CORR_THETA`, `CORR_MIN_IMG`, and the anchor machinery — so the
frozen bench-multiweb (results already reported) is not perturbed. It layers the
false merge onto a generated world *after* `generate()` returns (leaving the E1
fresh-node and E2 solo arms byte-identical), adds the obstruction detector
alongside `correspondence()`, and adds the §3a classifier and §4 metrics in its
own `run_seed`. It introduces two new constants: `OBS_MIN_CONTRA = 2` (the §3a
residual gate) and `MERGE_FRAC` (the bridge density, tuned once for Q-A during
bring-up then frozen); `OBS_THETA = 0.5` is retained only as a reported
secondary ratio.

Discipline (design-problem.md §10): E2b runs before T1–T3 are attempted, because
its outcome determines whether the geometric-obstruction half of the framework
is worth formalizing at all. It is empirical work licensed on the existing
benches — it neither validates nor requires the T0 model/data separation, and it
ships its result (pass or fail) with pre-registered predictions, like every
other bench in this project.

## 8. Post-run review notes (2026-07-14, after the scored run)

*Findings from an audit of the frozen implementation and the scored
artifacts. Nothing here changes the scored numbers, and no code was changed.
Provenance is of two kinds, marked per claim (wording corrected per round-2
referee point 6 — the original preamble said "no re-run", which conflated
them): (a) facts read directly from the frozen `results.json`; (b)
deterministic diagnostic recomputations — re-executing the frozen module on
individual scored seeds (same seeds, same code, bit-for-bit reproducible) for
facts the artifact does not store, such as region memberships and
correspondence scores. They are listed so the referee sees them from us
first.*

### 8a. Q-D as implemented is tautological — and the pre-registered attribution, computed post hoc, shows something STRONGER than predicted

As coded, `QD_e2b_geometric` is the identical predicate to
`QB_e2b_contra_ge_min` and to `QC_e2b_obstructed` (all three are
`contra >= OBS_MIN_CONTRA` on the same arm rows), so §6's third branch
("Q-C passes but Q-D fails — geometric but redundant with P1") was
unreachable as coded. The §4 Q4 attribution — obstructed vs would-need-P1 —
was NOT implemented. It is, however, answerable from the recorded per-seed
data, because the merged region's own `corroboration` was saved:

| E2b merged region corroboration | seeds (of 50) |
|---|---|
| 0 | 9 |
| 1 | 35 |
| 2 | 6 |

Under the frozen bench-multiweb projection rule (`concept = corroboration
>= 1`, i.e. **P1 alone**), the false merge would have been **COMMITTED as a
concept in 41/50 = 0.82 of seeds** (corroboration counts: provenance (a);
that the merged region is the full A∪B and `concept = True` with
correspondence scores up to 0.75: provenance (b) — these facts are not
stored in the artifact). The mechanism: with lopsided anchored counts, the
merged region's mapped image concentrates ≥ `CORR_THETA = 0.6` in ONE
side's region of another view, clearing the concentration test.

Consequence, with the denominators retained (wording corrected per round-2
referee point 3 — an earlier draft of this paragraph said P1 "does not
catch the overlap forgery at all", which overstated): the worry §6
enumerated (obstruction real but redundant with P1) is not merely
un-triggered — the opposite holds. **P1 is not a reliable defense against
the overlap forgery: it commits the false merge in 41/50 seeds and keeps it
provisional in only 9. The detector catches all 50, is uniquely responsible
for rejection in the 41 P1-committing seeds, and is therefore necessary for
complete rejection over the scored block.** The closed-world policy's
rejection of the fresh-node forgery does not generalize to forgeries that
land on the overlap; bench-multiweb's P-C ("the multi-web system rejects
the coherent forgery") is now known to be a statement about fresh-node
forgeries only. Any future scored run should implement Q-D as this
attribution (fraction of E2b regions with `corroboration >= 1`, i.e.
P1-would-commit), not as a copy of the Q-B predicate.

### 8b. Q-E: the baseline comparison the prediction demands, and the denominators

The Q-E prediction was "within noise of the bench-multiweb baseline"; the
report gave the run's numbers without quoting the baseline. Baseline
(results/bench-multiweb, seeds 0–49): recall **0.964**, purity **1.00**.
This run (seeds 1000–1049): recall 0.99 ± 0.04, purity 1.00 ± 0.00 — passes
(the seed blocks differ, so the small recall difference is noise, not
improvement). The false-obstruction rate 0.02 is **per region-instance**:
15 of 650 true-region rows pooled across seeds. Per SEED, 13/50 seeds
(0.26) have at least one falsely-obstructed true region; the worst single
region reached contra = 8 (seed 1030). The pre-registered gate reads
per-region and passes; the per-seed rate is reported here so the gate's
denominator is explicit. One further note: the implemented "true regions"
pool includes uncorroborated regions, slightly broader than §5's "true
corroborated regions" — immaterial to the pass, disclosed for exactness.

## 9. Round-2 referee corrections (2026-07-14, accepted in full)

*The round-2 referee report (docs/multiweb-overlap-forgery-referee-report.md,
preserved verbatim) raised seven points; all are accepted — response in
docs/multiweb-overlap-forgery-referee-response.md. Every diagnostic the
referee computed was independently reproduced exactly before acceptance.
The frozen sections §1–§7 above are left untouched; corrections to our own
post-run notes (§8) were made in place with per-point attributions, and the
substantive findings are recorded here. Referee point 2 (Q-D tautology) was
already §8a; point 6 (provenance) is fixed in the §8 preamble; point 3
(overstated P1 conclusion) is fixed in §8a; the remaining points:*

- **Point 1 (major, reinterpretation of the headline).** The detector counts
  a mapped backbone edge as CONTRADICTED when the other view lacks a strong
  counterpart — but each web is a finite 400-episode sample, so absence is
  non-observation, not negative evidence. Reading it as refutation is itself
  an epistemic policy, now named **P2** (design-problem §6), distinct from
  P1. The referee's diagnostic makes the cost concrete, and we reproduce it:
  14 of the 15 falsely-obstructed true region-instances sit on correctly
  mapped DIRECT anchors — sampling variance, not mapping error. The E2b
  result is therefore a reliable cross-view **disagreement separation**
  (every seed's E2b region carries ≥ 5 contradictions on correct direct
  anchors; E1/E2 carry none), NOT yet literal incompatibility / Ext = ∅ /
  a policy-free instance of T2. That identification awaits the P2 discharge:
  an explicit semantics for absent co-occurrence edges plus a soundness
  argument (design-problem §8 T2, §10). Headline language weakened
  accordingly in design-problem §2/§7/§9/§10 and the results report.
- **Point 4 (gate rationale falsified as stated).** §3a's justification for
  `OBS_MIN_CONTRA = 2` — "two INDEPENDENT refuting backbone edges, so one
  noisy mapping cannot manufacture a type" — is falsified by the code it
  describes: the gate counts edges, not independent witnesses, and one
  mis-mapped node can supply several contradicted edges. Scored instance,
  reproduced: seed 1029, node `w1:17` is wrongly mapped and produces BOTH
  counted contradictions, falsely obstructing a genuine region. This does
  not touch the E2b headline (whose residuals ride on correct direct
  anchors, ≥ 5 per seed) but it does explain one collateral error. The
  frozen §3a text stands as written; re-run obligation: require
  contradictions from independent witnesses (e.g. disjoint, directly
  anchored endpoint pairs), and restate the rationale to match.
- **Point 5 (bridge weights not exactly distribution-matched).** For a
  selected A–B pair that already carries a noise edge, the implementation
  ADDS the sampled intra weight to the existing weight instead of replacing
  it. Reproduced: 179 of 2,092 wired bridge pairs across the scored block
  (8.6%) were pre-existing, so their final weights are shifted samples —
  systematically stronger than §2's "sampled from the SAME empirical
  intra-community weight distribution" claim, slightly favoring merge
  formation and backbone survival. Unlikely to explain the separation
  (magnitude and the direct-anchor floor argue against), but a real
  construction mismatch. Re-run obligation: replace rather than add, or
  declare the shift.
- **Point 7 (Q-E denominator, quantified).** The corroborated-only rate the
  frozen prediction names is 15/616 = 2.44% (reproduced) vs the stored
  broad-denominator 15/650 = 2.31%; the < 0.05 gate passes under both. The
  machine metric remains mislabeled relative to the pre-registration (§8b);
  re-run obligation: compute both denominators explicitly.
