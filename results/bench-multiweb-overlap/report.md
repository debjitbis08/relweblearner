# The overlap forgery (E2b) — results

50 seeds. Pre-registered design and predictions: docs/multiweb-overlap-forgery-plan.md (frozen before this run; §3a amendment frozen before the bring-up).

Constructible seeds: 1.00.

## The typed cross-tabulation (the headline)

| arm | classified as | rate |
|---|---|---|
| E2b overlap forgery | obstructed | 1.00 |
| E1 fresh forgery | unsupported | 1.00 |
| E2 solo truth | unsupported | 1.00 |

## Q-A — the merge is a coherent overlap forgery

| quantity | value |
|---|---|
| merge stable as one region in web 0 | 1.00 |
| A, B separate stable regions in other views | 1.00 |

## Q-B — obstruction residual separation (decisive)

| quantity | value |
|---|---|
| E2b contra >= 2 | 1.00 |
| E1 contra == 0 | 1.00 |
| E2 contra == 0 | 1.00 |
| E2b contra distribution | 10.48 +/- 4.50 (min 5.00, max 26.00) |
| E2b ratio (secondary, OBS_THETA=0.5) | 0.49 +/- 0.08 (min 0.28, max 0.70) |
| E1 contra distribution | 0.00 +/- 0.00 (min 0.00, max 0.00) |

## Q-D / Q-E — policy independence and collateral

| quantity | value |
|---|---|
| E2b rejected geometrically (no P1) | 1.00 |
| true regions FALSELY obstructed | 0.02 |
| true-region contra distribution | 0.12 +/- 0.50 (min 0.00, max 8.00) |
| concept recall | 0.99 +/- 0.04 (min 0.80, max 1.00) |
| concept purity | 1.00 +/- 0.00 (min 1.00, max 1.00) |

## Post-run review (2026-07-14) — from the frozen results.json, plus deterministic same-seed diagnostics (provenance marked per claim; plan §8)

*This section was added by hand after an audit of the implementation and the
scored artifacts (plan §8; provenance wording corrected per round-2 referee
point 6). The scored numbers above are untouched.*

**The P1 attribution (the pre-registered Q4 the QD metric did not implement).**
The `QD` line above is the same predicate as the Q-B/Q-C lines (`contra >= 2`),
so it shows that the detector fires — not what P1 would have done. The recorded
per-seed data answers that directly. The E2b merged region's own corroboration:

| E2b merged region corroboration | seeds |
|---|---|
| 0 | 9 |
| 1 | 35 |
| 2 | 6 |

Under P1 alone (`concept = corroboration >= 1`, the frozen bench-multiweb
rule), the false merge would have been **committed as a concept in 41/50
seeds** and kept provisional in 9 — its mapped image concentrates past
CORR_THETA = 0.6 in one side's region of another view. The detector catches
all 50, is uniquely responsible for rejection in the 41 P1-committing seeds,
and is therefore necessary for complete rejection over the scored block
(plan §8a; wording per round-2 referee point 3).

**Q-E against the baseline.** bench-multiweb baseline (seeds 0–49): recall
0.964, purity 1.00. This run: 0.99 / 1.00 — within noise (a same-seed
comparison against the unmodified benchmark gives identical recall and purity
in all 50 seeds); the prediction's "preserved within noise of the baseline"
holds. The 0.02 false-obstruction rate is per region-instance (15/650 pooled
true-region rows; the corroborated-only rate the frozen prediction names is
15/616 = 2.44%, also under the gate — round-2 referee point 7); per seed,
13/50 seeds have at least one falsely-obstructed true region, worst single
region contra = 8 (seed 1030). See plan §8b and §9.

**World construction.** The bridge spans the FULL view-0 memberships of A and
B (a licensed Q-A bring-up retune, frozen before this scored run) — see plan
§2a, which backfills the pre-registration text. Round-2 referee point 5: 179
of 2,092 wired bridge pairs (8.6%) had a pre-existing noise edge whose weight
was ADDED to rather than replaced, so those bridge weights are shifted
samples, slightly stronger than the plan's distribution-matching claim —
recorded with the other corrections in plan §9.

**Round-2 referee (2026-07-14, accepted in full).** The headline is bounded:
the detector reads an ABSENT backbone edge in another sampled view as a
contradiction, which is an epistemic policy (P2, design-problem §6) for
finite co-occurrence data, not observed negative evidence — 14 of the 15
collateral flags sit on correctly mapped direct anchors (sampling variance).
This run therefore establishes a disjoint cross-view **disagreement
separation** (E2b ≥ 5 contradictions on correct direct anchors in every
seed; E1/E2 exactly 0), not yet literal Ext = ∅; that identification awaits
the P2 discharge (design-problem §8 T2). Full report:
docs/multiweb-overlap-forgery-referee-report.md; response:
docs/multiweb-overlap-forgery-referee-response.md; corrections: plan §9.
