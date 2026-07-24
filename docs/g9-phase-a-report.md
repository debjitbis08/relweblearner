# G9 Phase A report — anti-propagation mechanism analysis (draft)

Status: SEALED — the §4.5 adversarial review completed 2026-07-24
(ACCEPT-WITH-REVISIONS, ~90 values verified against the
hash-verified output of record; all required revisions applied,
including the §8.1 coefficient amendment the ruling required). This
report and `scripts/g9_phase_a_analysis.py` (at the sealing commit)
are the Phase A record; the script digest is quoted in the Phase B
manifest. Phase A makes no claims (plan §4): every number below is
determined by sealed data, and this report's role is measurement,
hypothesis-selection disclosure, and the fixing of the Phase B
constants §5.4–§5.5 assign to it.

## 0. Provenance and faithfulness

- Plan: `docs/g9-anti-propagation-plan.md` (§8.1 numerics closed
  2026-07-24, referee-gated). Script:
  `scripts/g9_phase_a_analysis.py` (authored `cfe2353`, round-2
  estimator `cef1baa`); synthetic selftest 15/15, no sealed data in
  any test path.
- Runs (human-gated, 2026-07-24): round 1 output sha256 `29dc768d…`
  (schema v1), round 2 output sha256 `4fe027a4…` (schema v2, both
  estimators, `round_disclosure` block). Round 2 is the analysis of
  record; round 1 is retained inside it.
- Faithfulness, all enforced before any number was emitted: for all
  9 conditioned worlds in both seed families, the reconstruction
  reproduced the sealed G7 conditional-separation certificate AND
  the sealed G8 interior-decisiveness overlay certificate to
  canonical-digest equality; every non-pivot attribution reproduced
  the sealed field within the certified solver bound (max delta
  9.60·10⁻⁷, mean 1.04·10⁻⁷, against a ceiling of solver_bound
  dressed with the frozen 10⁻⁹ slacks).
- Populations: 91 evaluated records (G8 seed 71, G7 seed 20); 26
  pivot records (can never cross, excluded from the predictor
  population per plan claim 4); 65 non-pivot records carrying all 26
  crossings.

## 1. Attribution (deliverable §4.1)

The exact decomposition `e_c = −Σ_j G_cj r_j` was computed for all 65
non-pivot records and verified per record as above.

- **Crossings are moderately opposing-dominated, not cleanly split.**
  The toward-opposing fraction of gross attributed mass is
  0.548–0.885 (mean 0.647) on crossed records versus mean 0.582
  (range 0.336–0.818) on non-crossed records. A gross-split
  threshold (crossed iff fraction > 0.5) classifies at balanced
  accuracy only 0.538 — even with solve-side information, the
  discriminator is the **net signed depth** of the pull, not the
  direction of the gross mass split. Hedging and anti-propagation
  are the same tug-of-war at different net displacements.
- **Attribution is moderately concentrated**: the top single residual
  site carries on average 44.5% of a crossed record's gross mass
  (range 22.6%–85.7%) — few-site frontier pulls, not diffuse
  averages, but rarely one-site stories either.

## 2. Predictor (deliverable §4.2) — selection disclosure and results

### 2.1 Hypothesis rounds (disclosed in full)

- **Round 1 — degree-3 Jacobi iterate: failed, instrument-level.**
  Pooled balanced accuracy 0.551 (vs the branch≠0 naive baseline
  0.756), diagnostic Spearman 0.131, predicted-vs-observed depth
  correlation −0.325. Root cause measured, not conjectured: the
  Jacobi iteration **diverges** on every sealed system —
  ρ(I − D⁻¹H_uu) = 1.979–2.842 (§2.4) — because the interior
  operators are near-clique unions, not diagonally dominant. The
  round-1 estimator is retained in the sealed output for the record.
- **Round 2 — degree-3 Chebyshev semi-iteration: selected.** Same
  polynomial degree; the change is placement, not power. Design
  interval `[b/κ_design, b]` with `b` the Gershgorin upper bound on
  the spectrum of `D^(−1/2)H_uu D^(−1/2)` (1-hop row-sum data) and
  `κ_design = 30` a **fixed constant**, chosen after observing round
  1's measured preconditioned condition numbers 18.4–65.1 — a
  disclosed, Phase-A-legitimate use of sealed measurements to design
  the next hypothesis; Phase B freezes it as a preregistered
  constant. The Chebyshev residual polynomial satisfies |C(λ)| ≤ 1
  on (0, b], so no mode is ever amplified (Gershgorin guarantees
  containment), and the in-interval worst-case error factor at
  κ_design = 30 is 1/T₄(θ₀) ≈ 0.434 — structurally far from
  solve-grade. (That figure is the optimal-polynomial bound; the
  implemented recurrence is selftest-verified for Krylov membership
  and contraction, not for achieving optimality — it is a design
  description, not a certified property.)

### 2.2 The frozen candidate predictor (explicit formula)

Inputs: `H_uu`, its diagonal `D`, the branch residual
`r = H_uu y_u + H_ub b`, the branch cochain value `own_c`, and the
opposing cochain values at the coordinate. All coefficients are the
fixed constants (degree 3, κ_design = 30) and the 1-hop Gershgorin
aggregate; no solve output enters the formula.

1. `ê = ChebyshevSemiIteration(D⁻¹H_uu, −D⁻¹r; [b/30, b], 4 steps)`
   — a polynomial of degree exactly 3 in `D⁻¹H_uu` applied to
   `D⁻¹r` (§8.1 class; Krylov membership asserted by selftest).
2. Predicted field `f̂_c = own_c + ê_c`.
3. **Predict crossed iff** `f̂_c` is strictly past the own/nearest-
   opposing midpoint toward the nearest opposing value — the exact
   mirror of the pinned `anti_propagation` rule, including strict
   inequality and nearest-opposing tie-breaking.

The continuous score for the §8.1 diagnostic is `ê_c` itself — the
raw budgeted linear estimate, before any thresholding, as the plan
requires.

### 2.3 Results on the sealed populations

| metric | Jacobi (round 1) | **Chebyshev (round 2)** |
|---|---|---|
| pooled balanced accuracy (non-pivot, 65) | 0.551 | **0.910** |
| confusion (tp/fp/tn/fn) | 6/5/34/20 | **22/1/38/4** |
| g7-seed family | 0.458 | **1.000** |
| g8-seed family | 0.577 | **0.884** |
| per-branch BA (0 / 1 / 2) | 0.44 / 0.54 / 0.67 | **0.98 / 0.89 / 1.00** |
| worst single world (LOWO analogue) | 0.0 (rule_7) | **0.600 (rule_8)** |
| diagnostic Spearman (vs true signed error) | 0.131 | **0.968** |
| depth Spearman on crossings | −0.325 | **0.222** |

Naive baselines (populations per plan §5.4(a)): majority 0.5;
**crossed-iff-branch≠0 0.756** (non-pivot); crossed-iff-non-pivot 0.7
(full population). The selected predictor beats the strongest
baseline by 0.154 in-sample.

Error anatomy — the misses invert the pre-run expectation (shallow
crossings were predicted to be the hard tail; the opposite is true):

- **All shallow crossings were caught** (depths 0.519–0.593, the
  hedge-lean regime closest to the midpoint).
- **All four false negatives are deep crossings in one branch**:
  rule_8 branch 1, depths 0.900–0.968, where the estimate carries
  the right sign but only ≈31–42% of the magnitude (ê 0.28–0.41
  against true 0.90–0.97). rule_8 branch 1 is also the branch
  farthest from the unconditioned field in its world (L2 2.083).
- **One false positive**: rule_5 branch 0 at `X:6:14` — a true
  near-crossing (net depth 0.408) overshot to a predicted 0.533.

### 2.4 Spectra (§8.1 measurement obligation)

Branch systems within a world share `H_uu` exactly (pivot pinning
changes boundary data, not the interior operator), so one row per
world:

| family | world | κ(H_uu) | λ_min | κ(D^(−1/2)HD^(−1/2)) | ρ(I−D⁻¹H) |
|---|---|---|---|---|---|
| g7 | rule_2 | 347.5 | 3.17·10⁻⁴ | 65.1 | 2.842 |
| g7 | rule_3 | 86.0 | 6.32·10⁻⁴ | 24.9 | 2.290 |
| g7 | rule_7 | 133.6 | 9.12·10⁻⁴ | 50.8 | 1.979 |
| g8 | rule_2 | 215.2 | 1.99·10⁻⁴ | 63.6 | 2.198 |
| g8 | rule_5 | 363.3 | 2.11·10⁻⁴ | 30.4 | 2.526 |
| g8 | rule_6 | 87.4 | 5.47·10⁻⁴ | 26.5 | 2.528 |
| g8 | rule_8 | 152.7 | 5.78·10⁻⁴ | 49.1 | 2.291 |
| g8 | rule_9 | 210.5 | 2.74·10⁻⁴ | 29.2 | 2.500 |
| g8 | rule_12 | 148.2 | 5.54·10⁻⁴ | 18.4 | 2.157 |

Per-class status of the §8.1 worst-case argument: the raw class
retains ≥ 0.71 min-max error at degree 3 (κ 86–363) — argument
stands. The Jacobi member of the preconditioned class diverges
everywhere — empirically incapable, the co-equal diagnostic was never
needed for it. The Chebyshev member is convergent by construction
with ≈ 0.43 in-interval worst-case damping — the diagnostic carries
the instance-level burden for it, as designed. The pinned certificate
λ_min lower bounds (2–6·10⁻⁴) turn out close to the measured λ_min
(2.0–9.1·10⁻⁴).

### 2.5 The diagnostic margin, discussed honestly

The selected predictor's diagnostic Spearman is **0.968** — under the
0.99 ceiling (not rejected as the solve in disguise) but **above**
the "honest mechanism ≈ 0.7–0.9" band the §8.1 rationale predicted.
The anti-smuggling weight is carried by provenance plus three facts
in the sealed output, not by the 0.968 < 0.99 scalar alone:

1. **The crossings-only depth Spearman is 0.222.** A solve output,
   under any monotone transform, would rank crossing depths
   near-perfectly; this predictor cannot.
2. **Deep-tail magnitude recovery is ≈31–42%**, not ~10⁻⁶: the four
   deepest errors (0.90–0.97) are estimated at 0.28–0.41.
3. **The four false negatives sit at depths 0.90–0.97** — misses a
   solve-possessing predictor cannot make.

Additionally, the pooled population's true |errors| span 0.025–1.014
(median 0.38): with that dynamic range, a high *pooled* rank
correlation is cheap for any **convergent** damped filter capturing
dominant local residual mass — round 1's divergent filter at 0.131
shows that convergence, not solve access, is the differentiator. And
the estimate's provenance is an auditable closed formula in the
sealed script, with the diagnostic pinned (per §8.1) to that raw
linear estimate, so a rank-coarsened solve cannot substitute for it.
What the high rank correlation actually reveals is itself a
mechanism observation: the **rank ordering** of interior errors is
largely determined by mid-spectrum, locally-visible structure that a
degree-3 filter legitimately captures; only magnitudes (and one
world's deep tail) depend on the bottom modes. The §4.5 review
stress-tested and upheld this reading; the 0.7–0.9 band in §8.1's
rationale was a misprediction about where rank information lives, not
evidence of smuggling. The ceiling stays 0.99; nothing widens.

## 3. Branch-asymmetry adjudication (deliverable §4.3)

Adjudication inputs are distance-based (the plan's "e.g." permutation
check was not implemented — disclosed limitation; the adjudication
below rests on distances alone):

- **In every world where crossings concentrate at all (5 of 9),
  they concentrate in the branch farther from the unconditioned
  field**: rule_3 (0 vs 2), rule_6 (0/2/3, monotone in distance),
  rule_8 (1 vs 4), rule_9 (0 at L2 0.496 vs 4 at 1.806), rule_12
  (0 vs 4). The other four worlds carry no concentration signal:
  g7 rule_5 and rule_7 tie 1–1 with the nearer branch included,
  g7 rule_2's distances are nearly tied (1.127 vs 1.137, crossings
  1–1), and g8 rule_2 has zero crossings (vacuous).
- Branch 0 is the nearest branch in 7 of 9 worlds — so branch index
  is a **partial enumeration proxy** for the distance covariate, not
  a mechanism variable.

**Adjudication: no branch-asymmetry claim is licensed for Phase B.**
The signal is real but correlational, has counterexamples, and its
natural carrier (distance-to-unconditioned) is a covariate Phase B
may *report*, never a preregistered claim. This closes the §1.4
question in the only honest direction available from these inputs.

## 4. Decode-decisiveness report (deliverable §4.4)

All 11 sealed certifying interior witnesses, frozen threshold 0.1:

| classification | count | witnesses |
|---|---|---|
| DECODE_DECISIVE_BOTH | **0** | — |
| DECODE_DECISIVE_ONE | 4 | g7 rule_3 `X:8:1`; g8 rule_5 `X:10:1`, rule_8 `X:6:5`, rule_9 `X:8:9` |
| DISTINGUISHABLE_ONLY | 7 | g7 rule_2 `X:8:4`, rule_7 `X:14:4`; g8 rule_2 `X:4:10` (both pairs), rule_6 `X:10:13`, `X:11:14`, rule_12 `X:13:3` |

Interior separation never once certified two fields that both decode
to their own branch values — in either seed family, at any witness.
Distinguishability and decodability are empirically different
properties everywhere, not just at the rule_8-style extremes.

## 5. The mechanism picture (hypothesis generation, no claims)

What the attribution, spectra, and predictor jointly suggest — stated
as the hypothesis Phase B will test, not as findings: a conditioned
branch's field at a disputed coordinate is a tug-of-war between
few-site frontier pulls; anti-propagation is the net displacement
crossing the midpoint, and hedging is the same displacement stopping
short. Most of that net displacement — enough to rank-order errors
and classify 22 of 26 crossings — is **mid-spectrum, locally visible
structure** reachable by a degree-3 damped polynomial. The residue
the budget cannot see is **bottom-spectrum collective consensus**,
and it is not noise: it carries the magnitude of the deepest
crossings in the most-displaced branch (rule_8 branch 1), where the
cubic keeps the sign but loses 60% of the depth.

## 6. Phase B constants fixed by this report (§5.4, §5.5)

- **Claim 4 floor and pass rule** (mechanism per plan §5.4, numbers
  fixed here): floor **F = 0.776** = strongest naive baseline
  (branch≠0, 0.756) + δ with **δ = 0.02**. Anchors: in-sample pooled
  0.910 (selected on these records, optimistically biased by
  construction); cross-seed-family transfer 1.000 (g7) / 0.884 (g8);
  worst single world 0.600 (rule_8). Pass rule (sample-size aware):
  from the realized unambiguous non-pivot counts, compute for TPR
  (successes s = true positives, failures f = false negatives) and
  TNR (s = true negatives, f = false positives) the one-sided
  Jeffreys lower bound **LB = the 0.20 quantile of
  Beta(s + ½, f + ½)**; **claim 4 passes iff (TPR_LB + TNR_LB)/2 ≥
  F**. This average of two marginal lower bounds is a preregistered
  *decision statistic*, not a calibrated confidence bound on
  balanced accuracy (the conjunction of two 80% bounds is not
  itself 80%) — it is fixed here as the rule. Checked against the
  observed data: cross-family transfer passes at both base-rate
  scales (g7-scale 6/0/8/0 → 0.891; g8-scale 16/1/30/4 → 0.821);
  perfect performance at the non-vacuity minimum of 5 positives
  passes (0.914); the branch≠0 baseline replayed as a predictor on
  the sealed G8 pattern fails (0.715). Rationale: δ is small
  because the baseline is already strong and the confidence-bound
  form (not the point estimate) absorbs low-positive-count noise —
  at the G7-scale base rate (6 positives) the rule is deliberately
  hard to pass by luck; at the G8-scale rate (26) it is comfortably
  passable by the observed transfer performance.
- **Claim 5 (depth calibration): DROPPED**, per the plan's written
  licensing criterion. The predictor does emit a continuous score,
  but its sealed predicted-vs-observed depth rank correlation on
  crossings is **0.222** — below any level worth preregistering. The
  fork closes here, verifiably, before Phase B authoring;
  classification-only is the predictor's honest scope.
- **Non-vacuity**: the plan's default minimum of 5 unambiguous
  crossing records stands (§8.4; both observed seeds pass at 20 and
  6). No sealed record is midpoint-ambiguous (minimum midpoint
  distances 0.0194 / 0.0933 per family).

## 7. Disclosures and limitations

1. Two hypothesis rounds were run; the first failed and is retained
   in the sealed output. Nothing outside the two rounds was
   evaluated against sealed data.
2. κ_design = 30 was chosen after observing sealed measurements
   (disclosed above); Phase B freezes it as a preregistered constant.
3. The Gershgorin aggregate in the predictor's coefficients is 1-hop
   row-sum data. The §4.5 referee ruled: §8.1's letter as originally
   confirmed was violated, its spirit was not, and the fix was a
   pre-seal amendment to §8.1 admitting declared closed-form 1-hop
   aggregates (never fitted, never solve output) — applied, with the
   referee's no-material-widening assessment recorded there.
4. The diagnostic margin (0.968 vs 0.99) is discussed in §2.5; the
   §4.5 review stress-tested and upheld the mid-spectrum-rank
   reading, with the triangulating facts now cited there.
5. Branch-asymmetry adjudication is distance-based only; the
   permutation check was not implemented. The adjudication outcome
   (no claim licensed) is the conservative one, so the limitation
   cannot have manufactured a claim.
6. In-sample performance numbers are selection-biased by
   construction; the §6 floor leans on transfer and confidence-bound
   anchors, not on 0.910.

## 8. Next steps

§4.5 adversarial review of this report and the script → seal both by
commit (script digest quoted in the Phase B manifest) → author
Phase B against §5 with the §6 constants → beacon ceremony with the
§7 public-anchor rule → run.
