# Graded ensemble — results (both arms)

Pre-registered design and predictions: docs/graded-ensemble-plan.md
(committed at 198ae38 before bring-up; §4b bring-up amendments committed
before the scored runs). GraphLog arm: 44 held-out worlds, identical
views/anchors as the discrete run, discrete comparator joined. Forgery arm:
50 seeds, identical generator as bench-multiweb run 2.

## Scorecard against the frozen predictions

| prediction | measured | verdict |
|---|---|---|
| P-G1 graded ≥ 0.90 × gold-pooled | **0.83** (discrete: 0.79) | **FAIL** |
| P-G2 improved worlds ≥ 0.75 | **0.59** | **FAIL** |
| P-G2 mean improvement ≥ +0.05 | **+0.021** | **FAIL** |
| P-G3 commit precision ≥ 0.90 | **0.81** (40 orphan, **2 real**) | **FAIL** |
| P-G4 forgery excluded ≥ 0.95 | 1.00 (50/50) | PASS |
| P-G5 recall ≥ 0.90 / purity ≥ 0.90 / solo ≥ 0.95 | 1.00 / 1.00 / 1.00 | PASS |

Means: graded 0.536, discrete 0.514, gold-pooled 0.648. No §6 kill line was
crossed (graded > discrete on the mean; forgery admitted 0/50; commit
precision above 0.75) — but every GraphLog-arm prediction failed. The
graded claim at its predicted effect size is NOT supported.

## What actually happened on the GraphLog arm

The effect is real but **bimodal** — soft coupling heals some seams and
tears others, netting +0.02:

- Healed: rule_26 0.29→0.64, rule_30 0.44→0.72, rule_42 0.45→0.71, and
  rule_32 0.62→0.88 — ABOVE gold-pooled 0.78: rules firing from both webs
  at similarity strength act as a smoothed ensemble, not just a repair.
- Torn: rule_20 0.66→0.32, rule_34 0.85→0.68, rule_40 0.72→0.61 — where
  hard identity was already sufficient, soft cross-firing adds competing
  wrong activations that win argmaxes.
- Unmoved where it mattered most: rule_27, the poster split-brain world
  (knowledge 100/103 present, discrete 0.163), stayed at 0.163 exactly.
  Whatever blocks its derivations, graded similarity did not bridge it —
  the split-brain diagnosis of the discrete run is necessary but evidently
  not sufficient there.
- The commit layer produced the project's first two REAL mispairings
  (mutual-argmax + 0.5 floor is a weaker gate than the discrete
  destructive-evidence test, which had zero in 44 worlds).

## The forgery arm: the guard held, and improved

Forgery excluded 50/50, solo-truth provisional 50/50, and recall rose to
1.00 (discrete: 0.96) at purity 1.00 — the soft field corroborates true
regions whose anchor draw fell below the discrete two-member floor.
Gradedness, once disciplined (§4b: absolute-evidence gate, backbone rule,
anchor-seeded zero init), bought sensitivity without buying hallucination.

## Reading

1. **The two-timescale guard is the solid result.** Three bring-up
   findings (§4b) now have scored confirmation: graded coupling
   hallucinates by construction — competitive normalisation manufactures
   confidence, uniform priors seed confabulation — unless identity mass
   can only flow outward from co-witnessed events along the structural
   backbone. Under that discipline, soft interference strictly dominates
   discrete interference on the categorical bench (recall 0.96→1.00 at
   equal refusal).
2. **For compositional thinking, similarity is not the missing piece —
   or not alone.** The split-brain gap (0.79× gold) was real, but healing
   it by soft symbol identity recovered only a tenth of it (0.83×), broke
   as many worlds as it fixed, and left the worst world untouched. The
   next diagnosis must explain rule_20's collapse and rule_27's immunity
   before any further mechanism is added.
3. Per house rules this failure is reported at the same prominence as the
   bench-multiweb and forgery-arm passes. The graded-thinking hypothesis
   for the GraphLog arm goes back to diagnosis; the discrete run remains
   the reference result for that arm.
