# Authors' response to the E5 referee report — all eight findings accepted

*2026-07-14. The report (docs/rule20-diagnosis-referee-report.md) is
preserved verbatim. The referee's 2×2 arithmetic was verified before
acceptance (marginals 0.000 / 0.267 / 0.075 / 0.342, interaction 0.267 —
reproduced exactly by the committed factorial). Findings 3.1 and 3.2 are
answered by new committed measurement rather than wording; the rest are
corrected in the results report and design-problem §5/§7/§10.*

## 3.1 (major) — the decomposition is order-dependent. ACCEPTED, and replaced by a factorial.

The published "−0.267 commits + −0.075 bridging" walked one ladder order
through an interacting system and is withdrawn as a decomposition. The
committed 2⁴ factorial (factors: R rules translated, D rendering
translated, S similarity exact, C the 2 wrong commits removed) reports all
16 cells with full heal/break sets, the explicit 2×2 the referee computed,
and the Shapley allocation the referee suggested: **R 0.183, C 0.139,
S 0.021, D 0.000** (sum 0.342). The factorial also found structure the
ladder could not: D is inert in every context; the interaction is
specifically C×R (commit removal is worth 0.000 without translated rules
and +0.298 with them); and the best cell is **C+R at 0.669 — above the
discrete ensemble's 0.659** — so the frozen soft similarity is mildly
beneficial once the two faults are repaired, sharpening the D3 selector
datum in a direction the withdrawn decomposition obscured. The
design-problem language now carries the Shapley numbers and the
interaction, not a path-dependent split.

## 3.2 (major) — the essential work was not in the repository. ACCEPTED.

Indefensible one session after adopting the plan-to-code rule. The
exactification is now a committed reproducer: `rule20_diag.py --exactify`
(`factorial()`, `preregistered_full_sets()`), writing factorial.json and
episode-sets.json. Every number previously reported from uncommitted
scripts reproduces exactly from the committed code, including the
0.317 / 0.358 / 0.371 / 0.392 / 0.659 cells and the 1000/1000 prediction
identities. The empirical queue's closure now rests on committed,
re-runnable artifacts.

## 3.3 — the promised episode sets were truncated. ACCEPTED.

`audit()` stored `[:20]` of each list. It now stores the full sets;
episode-sets.json carries the complete heal/break lists for all
pre-registered probes (deterministic regeneration, disclosed); the frozen
results.json is left as committed with the truncation noted in the report.

## 3.4 — "every single-factor probe was near-inert" is inaccurate. ACCEPTED.

Only P-commits and the beam settings are prediction-inert; P-ident changed
105 predictions (+0.041) and the aggregation probes 131 and 146 (both
negative). The masking lesson is restated at its measured width: it is a
fact about the commits factor (zero marginal at the frozen configuration,
+0.298 conditional on rule translation), not about single-factor
counterfactuals generally. Corrected in the report and design-problem.

## 3.5 — exactification is not exoneration. ACCEPTED.

"The two-timescale architecture per se is exonerated" is withdrawn. The
supported statements: full recovery under discrete exactification
(prediction-identical endpoint), and the factorial's sharper positive —
the frozen soft machinery slightly exceeds discrete once rules are
translated and the false commits removed. The losses live in the missing
translation layer and the hardening gate; that is where E5 points D3/T6,
without any claim that the architecture as originally configured is sound.

## 3.6 — the rule_27 companion narrows, not closes. ACCEPTED.

"Closed" and "no distinct mechanism" are withdrawn. Supported: the graded
system's rule_27 predictions coincide with discrete on 956/1000 episodes,
so the E6 residual is substantially narrowed to the 44 flipped episodes,
which carry no causal probe and are recorded as a licensed follow-up.

## 3.7 — the draw-level conclusion is scoped to rule_20. ACCEPTED.

No other world was rerun across view draws; the design problem no longer
generalizes the bimodality claim beyond rule_20.

## 3.8 — marker limitations. ACCEPTED.

The two additional caveats (`cross_fired` does not distinguish correct
correspondence from spurious firing; `beam_starved` is span-level, not
derivation-critical) are recorded alongside the anchor-pooling caveat.
Markers support nothing beyond the probes. The beam re-check from
committed code also refines "changes nothing" to "no accuracy effect;
3/1000 predictions wobble at the frozen configuration."

## On the recommendation

Adopted in full. The gate, flip table, draw sensitivity (rule_20-scoped),
the negative-net native soft bridge on the frozen draw, and the large
conditional commit interaction stand as the accepted results. The queue
closure now satisfies the referee's stated condition: the experiment that
carries E5's mechanism is reproducible from committed code, and the
interaction is represented as measured — Shapley plus explicit 2×2 —
rather than as one path through the ladder.
