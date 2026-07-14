# The rule_20 diagnosis (E5) — flip table, winner trace, probes

Pre-registered: docs/rule20-diagnosis-plan.md (committed before this code; §6b checklist implemented in full). Probes are diagnostic counterfactuals — NOT system capabilities. Trace marks are MARKERS; the heal/break probes are the causal reading.

Consistency gate: recomputed {'view-alone': 0.358, 'ensemble': 0.659, 'gold-pooled': 0.752, 'graded': 0.317} vs frozen {'view-alone': 0.358, 'ensemble': 0.659, 'gold-pooled': 0.752, 'graded': 0.317}; diag copy prediction-identical: True — PASS.

## §4a Flip table (seed 0, paired per episode)

```json
{
 "both_wrong": 312,
 "torn": 371,
 "both_right": 288,
 "healed": 29
}
```

## §4a Winner trace over 371 torn episodes (marks)

```json
{
 "cross_fired": 314,
 "commit_pooled": 365,
 "beam_starved": 52,
 "sum_outvoted": 4,
 "wrong_commit_involved": 17
}
```

## §4b Probes (each vs the frozen graded baseline; heal/break sets)

### P-commits (H2)

```json
{
 "minus_wrong_commits": {
  "acc": 0.317,
  "heals": 0,
  "breaks": 0,
  "healed_idx": [],
  "broken_idx": []
 },
 "anchors_only": {
  "acc": 0.318,
  "heals": 1,
  "breaks": 0,
  "healed_idx": [
   509
  ],
  "broken_idx": []
 },
 "n_wrong_commits": 2
}
```

### P-ident (H1)

```json
{
 "acc": 0.358,
 "heals": 73,
 "breaks": 32,
 "healed_idx": [
  9,
  35,
  51,
  56,
  82,
  101,
  103,
  110,
  122,
  226,
  238,
  248,
  262,
  268,
  270,
  289,
  293,
  300,
  312,
  329
 ],
 "broken_idx": [
  42,
  65,
  97,
  123,
  143,
  189,
  200,
  228,
  264,
  295,
  309,
  337,
  338,
  387,
  398,
  444,
  467,
  505,
  512,
  517
 ]
}
```

### P-sum (H3)

```json
{
 "max": {
  "acc": 0.276,
  "heals": 45,
  "breaks": 86,
  "healed_idx": [
   6,
   35,
   86,
   110,
   119,
   121,
   138,
   219,
   230,
   237,
   250,
   262,
   268,
   299,
   300,
   312,
   321,
   382,
   386,
   394
  ],
  "broken_idx": [
   5,
   19,
   24,
   42,
   52,
   73,
   75,
   83,
   93,
   94,
   97,
   105,
   114,
   125,
   136,
   154,
   163,
   173,
   206,
   215
  ]
 },
 "count": {
  "acc": 0.183,
  "heals": 6,
  "breaks": 140,
  "healed_idx": [
   623,
   711,
   858,
   866,
   917,
   981
  ],
  "broken_idx": [
   8,
   18,
   19,
   24,
   39,
   40,
   60,
   65,
   83,
   105,
   106,
   114,
   139,
   143,
   144,
   149,
   151,
   154,
   155,
   169
  ]
 }
}
```

### P-beam (H4, bounded — can support, never exclude)

```json
{
 "top_k_16": {
  "acc": 0.317,
  "heals": 0,
  "breaks": 0,
  "healed_idx": [],
  "broken_idx": []
 },
 "top_k_32": {
  "acc": 0.317,
  "heals": 0,
  "breaks": 0,
  "healed_idx": [],
  "broken_idx": []
 },
 "act_min_0.001": {
  "acc": 0.317,
  "heals": 0,
  "breaks": 0,
  "healed_idx": [],
  "broken_idx": []
 },
 "act_min_0": {
  "acc": 0.317,
  "heals": 0,
  "breaks": 0,
  "healed_idx": [],
  "broken_idx": []
 }
}
```

## §4c Robustness (seeds 1–4)

```json
[
 {
  "seed": 1,
  "discrete_acc": 0.733,
  "graded_acc": 0.727,
  "cells": {
   "both_right": 694,
   "both_wrong": 234,
   "healed": 33,
   "torn": 39
  }
 },
 {
  "seed": 2,
  "discrete_acc": 0.593,
  "graded_acc": 0.293,
  "cells": {
   "both_wrong": 321,
   "torn": 386,
   "both_right": 207,
   "healed": 86
  }
 },
 {
  "seed": 3,
  "discrete_acc": 0.633,
  "graded_acc": 0.703,
  "cells": {
   "both_right": 609,
   "both_wrong": 273,
   "healed": 94,
   "torn": 24
  }
 },
 {
  "seed": 4,
  "discrete_acc": 0.692,
  "graded_acc": 0.708,
  "cells": {
   "both_right": 608,
   "both_wrong": 208,
   "torn": 84,
   "healed": 100
  }
 }
]
```

## Supplementary: the exactification ladder (post-plan, same day — supplementary.json)

All four pre-registered hypotheses measured causally near-inert at the
frozen configuration, leaving the 0.342 tear unattributed. The ladder
replaces graded components with their discrete counterparts one at a time
(provenance (b), seed 0):

| configuration | acc | identical to |
|---|---|---|
| frozen graded | 0.317 | — |
| native rules, identity sim | 0.358 | view-alone **1000/1000** |
| translated rules + rendering, identity sim | 0.392 | discrete-ens 733/1000 |
| … + beam removed (TOP_K 10⁶, ACT_MIN 0) | 0.392 | unchanged |
| … + merge empty / anchors-only / **minus the 2 wrong commits** | **0.659** | discrete-ens **1000/1000** |
| … + merge ONLY the 2 wrong commits | 0.392 | discrete-ens 733/1000 |

## Findings

1. **The tear decomposes exactly, and the dominant cause is two FALSE
   graded commits.** The hardening gate (mutual argmax + HARD_SIM = 0.5)
   committed R_4_- ↔ R_0_- and R_5_- ↔ R_6_- (both orphan-type,
   precision 0.6 recorded in the frozen artifact); pooling output mass
   through them costs **−0.267**. The remaining **−0.075** is the graded
   architecture's replacement of translation (rules and seam rendering
   through the discovered mapping) by runtime soft bridging — worth
   negative net value on this draw. Fully exactified graded is
   prediction-identical to discrete CYK on all 1,000 episodes: the
   decomposition is exhaustive.
2. **Every pre-registered single-factor probe measured ~zero for the
   dominant factor — total masking.** P-commits at the frozen
   configuration: 0 heals, 0 breaks for the same two commits that cost
   0.267 once translation is restored. A system sitting at a compound
   floor renders single-factor counterfactuals uninformative; factorial
   exactification must be pre-registered for compound systems (process
   lesson, recorded in supplementary.json).
3. **The soft bridge is the graded system's only ensemble mechanism, and
   here it subtracts value.** Identity-sim graded is view-alone to the
   prediction (1000/1000); the frozen soft field lands 0.041 BELOW that.
   H1's cross-firing exists (314/371 torn episodes carry a bridged winning
   factor) but removing it recovers little — the marks were markers
   indeed.
4. **H3 and H4 are refuted outright.** Sum is the best of the three
   aggregations (max 0.276, count 0.183); the beam changes nothing in any
   tested configuration including exact-uniform activations.
5. **The bimodality is draw-level, not world-level.** rule_20 tears at
   seeds 0 and 2 and heals or holds at 1, 3, 4. Whether seed 2 shares the
   wrong-commit mechanism is a licensed follow-up.
6. **E6's open residual is closed (§4d).** rule_27's graded predictions
   coincide with discrete on 956/1000 episodes; there is no distinct
   graded mechanism there — the seam catastrophe is inherited, and soft
   bridging cannot repair it.

## Referee corrections (accepted in full) and the committed factorial

*The E5 referee report (docs/rule20-diagnosis-referee-report.md, preserved
verbatim; response in docs/rule20-diagnosis-referee-response.md) raised
eight findings; all are accepted. Where this section contradicts the
"Findings" section above or supplementary.json, THIS section supersedes.
The factorial reproducer is committed (`rule20_diag.py --exactify`,
functions `factorial()` / `preregistered_full_sets()`); its artifacts are
factorial.json (16 cells, full heal/break sets, Shapley) and
episode-sets.json (the pre-registered probes with COMPLETE episode lists —
finding 3.3; the frozen results.json retains the truncated ones). Every
cell previously reported from uncommitted scripts reproduces exactly from
the committed code: 0.317 / 0.358 / 0.371 / 0.392 / 0.659, and the
1000/1000 identities.*

**The order-independent analysis (finding 3.1).** The published
"−0.267 commits + −0.075 bridging" was one path through an interacting
system and is WITHDRAWN as a decomposition. The 2⁴ factorial over
R (rules translated), D (rendering translated), S (similarity exact),
C (2 wrong commits removed):

| quantity | value |
|---|---|
| Shapley: R / C / S / D | **0.183 / 0.139 / 0.021 / 0.000** |
| commits marginal at frozen config | 0.000 |
| commits marginal after R+D+S exactification | +0.267 |
| the 2×2 interaction | 0.267 |
| best cell: **C+R** (frozen soft sim retained) | **0.669 — above discrete 0.659** |
| C+R+S (soft sim also removed) | 0.659, ≡ discrete 1000/1000 |

Three facts the single ladder missed: **D is inert everywhere** (rendering
translation changes nothing in any context); the interaction is
specifically **C×R** (commit removal is worth 0.000 without translated
rules and +0.298 with them); and with both faults fixed, the frozen soft
similarity is mildly BENEFICIAL (+0.010 over discrete). Beam re-check from
committed code: no accuracy effect; at the frozen config 3 of 1,000
predictions wobble with accuracy unchanged (refining the earlier "changes
nothing").

**Corrected claims.**
- Finding 2's "every pre-registered single-factor probe measured ~zero"
  is WITHDRAWN (finding 3.4): only P-commits and the beam settings are
  prediction-inert; P-ident changed 105 predictions (+0.041) and the
  aggregation probes 131 and 146 (both negative). The masking lesson is
  narrowed to what is measured: the commits factor alone has zero marginal
  effect at the frozen configuration and a large conditional effect after
  rule translation.
- "The two-timescale architecture per se is exonerated" is WITHDRAWN
  (finding 3.5). Supported: full recovery under discrete exactification
  (prediction-identical endpoint), and — stronger, from the factorial —
  the frozen soft machinery slightly exceeds discrete once rules are
  translated and the false commits removed. The tear lives in the missing
  translation layer and the weak hardening gate, not in graded similarity
  semantics, ON THIS DRAW.
- "E6's residual is CLOSED / no distinct graded mechanism on rule_27" is
  narrowed (finding 3.6): 956/1000 predictions coincide, so the residual
  is substantially narrowed to 44 flipped episodes, which remain
  unattributed (no causal probe was run on them).
- The draw-level bimodality conclusion is SCOPED to rule_20 (finding
  3.7); no other world was rerun across draws.
- Marker caveats extended (finding 3.8): `cross_fired` does not
  distinguish correct cross-view correspondence from spurious firing;
  `beam_starved` marks any pruned target-mapped symbol at any visited
  span. Markers support nothing beyond the probes.

## §4d rule_27 companion (E6's residual, substantially narrowed — see corrections above)

```json
{
 "gate": {
  "frozen": {
   "view-alone": 0.133,
   "ensemble": 0.163,
   "gold-pooled": 0.828,
   "graded": 0.163
  },
  "recomputed": {
   "view-alone": 0.133,
   "ensemble": 0.163,
   "gold-pooled": 0.828,
   "graded": 0.163
  },
  "diag_copy_identical": true,
  "pass": true
 },
 "flip": {
  "cells": {
   "both_wrong": 815,
   "both_right": 141,
   "healed": 22,
   "torn": 22
  },
  "discrete_acc": 0.163,
  "graded_acc": 0.163
 },
 "trace_marks": {
  "commit_pooled": 17,
  "beam_starved": 17,
  "sum_outvoted": 5,
  "cross_fired": 2
 },
 "n_torn": 22
}
```
