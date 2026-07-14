# The P2 discharge — a semantics for absent edges and the soundness of the disagreement detector

*Written 2026-07-14, BEFORE the validation script exists or runs. This note
discharges the standing obligation of design-problem §6 (P2) and the E2b
round-2 referee: an explicit semantics for ABSENT co-occurrence edges and a
soundness argument connecting the operational disagreement detector
(multiweb_overlap, `contra ≥ OBS_MIN_CONTRA`) to genuine incompatibility
(Ext = ∅, T2). The argument is MODEL-RELATIVE: it holds under the declared
generative view model of bench-multiweb (assumption A1 below), which is true
by construction for the bench and becomes a named per-domain assumption in
any deployment — exactly parallel to T4's coverage/independence assumptions.
Every quantity below is computable from the frozen world constants with NO
free parameters; §5 pre-registers how the computation is validated against a
held-out seed block (2000–2049, untouched by any prior run) before the
discharge is claimed. Per the §10 process rule, §7 maps every promised
quantity to its implementing function.*

## 1. The obligation

The E2b detector reads a strong (backbone) edge of view i whose mapped image
in view j is absent or weak as CONTRADICTED. The referee's correction, now
§6 P2: in a finite sample, absence is non-observation, not observed negative
evidence — treating it as refutation is an epistemic policy until a
completeness axiom or a statistical soundness argument is supplied. Without
the discharge, E2b's result is a "reliable disagreement separation," not an
empirical instance of T2.

## 2. Setting and assumptions

Fix the frozen constants (multiweb.py): 6 communities of 10 entities
(community 5 solo in view 0), K = 3 views, per-entity visibility 0.8,
400 episodes per view of which a fraction 0.08 are noise (3 uniform visible
entities) and the rest draw 3 or 4 members of one uniformly-chosen eligible
community; backbone threshold 0.5 × the web's median edge weight;
`OBS_MIN_CONTRA = 2`; a region's residual is the max over other views.

- **A1 (generative view model).** Each web is produced by exactly this
  process, independently across views given the hidden communities. True by
  construction on the bench; the deployment-facing assumption.
- **A2 (mapping correctness, with an error term).** Checkable edges are
  those whose endpoints the partial mapping maps. A2 does not assume the
  mapping perfect: the soundness statement carries an explicit ε_map term
  for contradictions manufactured by wrongly-mapped endpoints (measured:
  1 of the 15 collateral flags in the frozen E2b block; the E2b §9 re-run
  obligation — witness-independent counting — targets exactly this term).

**The idealized object.** Let B\*_j = {(u,v) : u,v co-membered in the hidden
world, both visible to view j} — view j's TRUE backbone. Under one hidden
world, the B\*_j are jointly consistent by construction: a pair cannot be
co-membered for one view and not for another. Incompatibility of a trial
identification with B\*_j is therefore genuine T2-antecedent material: a
region asserting "u,v co-membered" whose image pair is absent from B\*_j
admits NO hidden-world configuration consistent with both views — no global
section extends the local data. Ext = ∅.

## 3. The semantics of an absent edge

The finite web G_j is a sample, and the backbone test is a statistical
reading of B\*_j. Two error rates, both computable from A1 with no free
parameters:

- **p_miss** = P(an intra-community pair, both endpoints visible in j,
  scores below j's backbone threshold). Sources: the Binomial thinning of
  ~368 non-noise episodes over ~5–6 eligible communities and pair-inclusion
  odds 9/(n(n−1)) for visible community size n, against a threshold of half
  the web median. This is the probability that ABSENCE IS AN ACCIDENT.
- **δ_x** = P(a cross-community pair scores at or above the threshold) —
  noise co-occurrences (expected pair weight ≈ 0.09 at these constants)
  reaching backbone strength. The probability that PRESENCE IS AN ACCIDENT.

An absent backbone edge is then evidence of absence with likelihood ratio
(1 − δ_x)/p_miss — a quantitative semantics in place of the smuggled axiom.
One honest structural caveat, stated rather than hidden: the separation is a
FINITE-SAMPLE property of the operating regime. As episodes → ∞ with noise
fraction fixed, every cross pair eventually accretes weight, the median
migrates to the cross mass, and the relative backbone threshold stops
separating — the detector is an instrument for the sparse-noise regime
(expected distinct noise edges well below the intra edge count), which the
frozen constants satisfy and which A1 must certify in any deployment.

## 4. The soundness statement (T2-operational)

Under A1 + A2, for a true region R in view i with m_j checkable strong
edges into view j (j ranging over the other views), and for the E2b merged
region with b_j ≥ 2 checkable bridge edges:

1. **False alarm.** Idealized contradictions on a true region are zero
   (§2), so observed ones arise only from sampling or mapping error:
   P(R falsely obstructed) ≤ P(max_j Bin(m_j, p_miss) ≥ 2) + ε_map ≕ α(R).
2. **Detection.** A bridge pair is cross-community, so its idealized image
   edge is absent; a checkable bridge fails to register as contradicted
   only if noise makes the image strong (δ_x) — hence
   P(merged region obstructed) ≥ 1 − P(Bin(b_j, 1 − δ_x) ≤ 1) ≈ 1 for
   b_j ≥ 2 and small δ_x.
3. **The reading.** "Obstructed" is a statistical test of the Ext = ∅
   condition with computable error rates (α, β): what survives of P2 as
   POLICY is only the choice of tolerance (`OBS_MIN_CONTRA = 2`, whose
   false-alarm consequences α makes explicit) — the same residue any
   statistical test carries. The count gate's rationale is also made
   honest here: the §3a "independence" language was corrected by the E6-
   style review (one wrong-mapped node can supply several contradictions),
   which is why ε_map is a separate term and the re-run obligation stands.

Proof burden: (1) and (2) are immediate from §2's idealized-consistency
observation plus the definitions of p_miss, δ_x, ε_map; the substantive
content is NUMERICAL — that p_miss and δ_x at the frozen constants are
small enough for α, β to match the observed world. That is §5's job.

## 5. Pre-registered validation (frozen with this note)

The quantities p_miss and δ_x are computed by sampling the DECLARED MODEL
itself — the frozen `generate()` on fresh seeds 10000–10199, reading edge
weights against per-web thresholds; no artifact is an input, and the
formulas above have zero adjustable parameters (the vacuity check for this
plan: there is nothing to fit). Validation then has a disclosed-retrodiction
half and a genuinely held-out half:

- **V1 (edge level, held out).** On seeds 2000–2049 run the frozen E2b
  pipeline and enumerate every checkable true-region backbone edge with
  CORRECTLY-mapped endpoints: the observed contradiction rate must fall
  within the model p_miss's 95% band widened by a factor of 2 (the
  tolerance absorbs the mixture over community sizes and thresholds).
  Wrong-mapped-endpoint contradictions are reported separately as the
  measured ε_map, never pooled.
- **V2 (region level, held out).** Using each true region's MEASURED m_j
  and the model p_miss: predicted falsely-obstructed instance count
  Σ_R P(max_j Bin(m_j, p_miss) ≥ 2), compared to observed within a factor
  of 2.5 (small-count regime).
- **V3 (detection, held out).** E2b merged regions with ≥ 2 correctly-
  anchored checkable bridges are obstructed at rate ≥ 0.98, and the
  per-checkable-bridge contradiction rate is ≥ 1 − δ_x − 2·p_pair-noise
  (≈ 0.99 at the frozen constants).
- **V4 (retrodiction, disclosed as such).** The same quantities against
  the frozen block 1000–1049, whose outcomes (15/650 instances, contra
  histogram, E2b min contra 5) are already known to the authors — reported
  for completeness, carrying no confirmatory weight on its own.

Failure routing, fixed now: if V1 or V2 fails, the A1-derived semantics
does not describe the bench (a derivation or independence error), P2 stays
UNDISCHARGED, and this note is amended to say so with the failure — not
patched until the discrepancy is diagnosed. If only V3 fails, the false-
alarm semantics stands but the detection bound is wrong; T2's anchor
weakens accordingly. Tolerances are declared above BEFORE the validator
exists; they cannot be widened after.

## 6. What the discharge achieves — and does not

Achieved, if §5 passes: within A1 worlds, "obstructed" verdicts read as
Ext = ∅ up to computed error rates, so E2b's separation becomes T2's
empirical instance RELATIVE TO THE NAMED MODEL, and P2 leaves the policy
list (§6) for the assumption list, alongside T4's. Not achieved, ever, by
this route: a model-free license to read absence as refutation. In any
deployment A1 is a per-domain empirical claim (sampling regime, noise
sparsity, view independence) that must be validated there. The E2b §9
re-run obligations are unchanged; ε_map remains a measured, not assumed,
term.

## 7. Plan-to-code checklist (audited before the validator runs — §10 process rule)

| promised quantity / step | implementing function in `bench/p2_validate.py` |
|---|---|
| model p_miss, δ_x, threshold distribution (seeds 10000–10199) | `model_rates()` |
| V1 edge-level held-out measurement + ε_map split | `edge_rates(block)` |
| V2 region-level predicted vs observed false obstructions | `region_alpha(block)` |
| V3 detection side (rates + per-bridge) | `detection(block)` |
| V4 retrodiction on 1000–1049 | same three functions, `--block 1000` |
| verdict against §5 tolerances | `verdict()` |

Each row must exist and run before results are read; a dropped row is
reported as dropped in the bring-up commit, not discovered by a referee.

## 8. Validation outcome (2026-07-14, after the run) — P2 NOT DISCHARGED

*Written after the §5 validation ran (results/p2-discharge). The §5
tolerances were applied verbatim; per the frozen failure routing, this
section records the failure rather than patching it.*

- **V1 PASSED.** Held-out per-edge false-contradiction rate on
  correctly-mapped endpoints: 0.0188 (64/3,405) against model
  p_miss = 0.0207 — the likelihood-ratio semantics of §3 is confirmed at
  the edge level. Measured ε_map: 3 contradicted wrong-mapped edges.
- **V3 PASSED.** Detection 1.00 (50/50 eligible merged regions
  obstructed); per-checkable-bridge contradiction rate 1.0000; δ_x
  measured at 0.00046.
- **V2 FAILED.** Falsely-obstructed region instances: 10 observed
  (9 on correct endpoints only) against 3.4 predicted — outside the
  frozen ×2.5 band [1.36, 8.5]. **P2 therefore remains undischarged.**

**Diagnosis (labeled post-run diagnostic, not a repair).** The §4
false-alarm bound plugged the GLOBAL MEAN p_miss into independent
per-region binomials. The model's own output already showed a wide rate
spread across world-views ([0.000, 0.062]); the false-alarm tail
P(Bin(m, p) ≥ 2) is convex in p, so by Jensen's inequality the mean
underpredicts under a mixture. Recomputing the same prediction with each
world-view's OWN measured p_miss gives 7.44 vs the observed 10 (and 9 on
correct endpoints — within ~1σ of Poisson counting noise). The failure is
exactly the "independence error" the §5 routing anticipated: contradiction
events are correlated through the world-level rate, not independent across
regions.

**What a v2 amendment must do before discharge can be claimed:** replace
the §4 false-alarm bound with a rate-mixture form (per-world-view p_miss,
or a fitted-free hierarchical bound derived from the declared process),
pre-register it as an amendment to this note, and validate on a FRESH
held-out block (e.g. 3000–3049) — the 2000-block is now spent for V2.
V1 and V3 stand as validated and are not re-litigated by the amendment.

**Also discovered during bring-up:** the frozen `generate()` crashes on
worlds where an eligible community has exactly 3 visible members and an
episode draws size 4 (multiweb.py:122; model-block seeds 10145 and 10191).
No frozen artifact is affected — a crashing seed can never have produced a
result — so all benched blocks are implicitly conditioned on the process
completing, and the validator applies the same conditioning (skipped seeds
recorded, never silent). A fix to `generate()` is a bench amendment
requiring its own pre-registration; the latent-crash rate (~1% of seeds)
is now a known property of the declared process.

## 9. Amendment v2 (2026-07-14, pre-registered BEFORE the fresh block is run)

*Committed before `region_alpha_v2` exists and before ANY computation
touches seed block 3000–3049, which no prior run of anything has used.
Nothing here is fitted: the only inputs to the v2 bound are the declared
process (model seeds 10000+) and each region's measured m_j.*

**The corrected false-alarm bound.** Replace §4(1)'s global-mean plug-in
with the rate mixture the §8 diagnosis identified. Let F be the empirical
distribution of per-world-view p_miss sampled from the declared process
(the same model block; raw samples, not the mean). For a true region R
with checkable-correct edge counts m_j:

    α₂(R) = E_{p ~ F} [ 1 − Π_j (1 − τ(m_j, p)) ],   τ(m, p) = P(Bin(m, p) ≥ 2)

with ONE p shared across the region's views — the maximal within-world
rate correlation, the conservative choice; the independent-per-view-draw
variant is computed and REPORTED as a sensitivity, but does not gate.

**Verdict criteria (frozen now):**
- **V2′** — on fresh block 3000–3049: the observed falsely-obstructed
  count on CORRECT-endpoint contradictions only must lie within a factor
  2.5 of Σ_R α₂(R). (v1's verdict compared the α part against the TOTAL
  observed count, conflating the ε_map term that §4 explicitly separates;
  the split is declared here, before the block is seen. ε_map-driven
  obstructions are reported alongside, never pooled.)
- **V1 replication (gating)** — the 3000-block correct-endpoint edge rate
  must lie in the ORIGINAL V1 band (§5); the semantics must replicate,
  not merely have passed once.
- **V3 replication (gating)** — thresholds as in §5.

**Failure routing, fixed now:** if V2′ fails again, world-level rate
sharing does not capture the within-region correlation (node-level
clustering — a weakly-visible endpoint degrading several edges at once —
is the next named candidate); P2 stays undischarged, the failure is
recorded in §10, and no third attempt is made without a diagnosis-backed
model change pre-registered first.

**Checklist additions (§7):** `region_alpha_v2()` (the mixture bound, both
variants), `verdict_v2()`, and a `--v2` CLI mode running blocks 3000–3049
(gating) and 2000–2049 (now retrodiction for V2′, disclosed as such);
`model_rates()` gains a raw-samples return for F. Vacuity: the 3000 block
is virgin; F never sees it; the tolerance factor is unchanged from v1 —
the model is corrected, not the bar.
