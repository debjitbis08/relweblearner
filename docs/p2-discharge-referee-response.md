# Authors' response to the P2-discharge referee report — all six findings accepted

*2026-07-14. The report (docs/p2-discharge-referee-report.md) is preserved
verbatim. Every numeric claim was independently reproduced before
acceptance: the forgery mutation shifts view-0's mean intra miss rate
0.03048 → 0.03794 and threshold 3.000 → 3.234 on 23/48 fresh worlds
(digit-for-digit); the exact declared model block (198 worlds) gives
α₂ = 5.67 vs the shipped 5.64 with seeds 10200–10201 confirmed leaked; the
stronger per-view V3 condition holds on 48/48 fresh and 50/50 held-out
cases. The v2 "DISCHARGED" status is WITHDRAWN (note §11; design-problem
§6/§7/§8/§10 rolled back), and findings 1+2 are answered by a
route change rather than a patch (note §12).*

**Finding 1 (High) — α₂ is not a bound. ACCEPTED; the analytic route is
abandoned.** The composition of conditionally-independent binomial tails
was never licensed by A1, and a ×1.95 underprediction inside a ×2.5
tolerance is calibration, not a computed error rate. Rather than model the
clustering term, v3 stops composing per-edge probabilities altogether: the
false-alarm rate of the ACTUAL detector is measured by running the full
frozen pipeline on the declared model block, and its transfer to unseen
blocks is gated through world-level bootstrap predictive intervals — which
carry all within-world clustering by construction. The claim tier is
renamed honestly: MEASURED error rates under A1, never "computed"/bounded;
the assumption ledger now carries the bounded / measured / calibrated
distinction explicitly.

**Finding 2 (High) — model ≠ pipeline. ACCEPTED.** F was measured on
pristine worlds while the evaluated worlds carry the forgery mutation in
view 0. v3's direct simulation runs `add_overlap_forgery` before
measuring, so the model quantity is the evaluated quantity by
construction.

**Finding 3 — ε_map never became a probability. ACCEPTED.** In v3 the
mapping-error contribution is inside the measured rate (the simulation
draws mapping errors from the same process), and the split is still
reported with denominators, with a rule-of-three 95% upper bound whenever
a cell is zero.

**Finding 4 — V3's eligibility and causality were weaker than stated.
ACCEPTED.** v3's detection gate requires ≥ 2 correctly-anchored checkable
bridges in a SINGLE view and ≥ 2 of those same bridges contradicted in
that view (bridge-attributable). The referee's replay showing the stronger
condition holds on all 98 current cases is gratefully adopted as evidence
the fix changes bookkeeping, not history.

**Finding 5 — the model sampler left its declared block. ACCEPTED.** The
v1/v2 artifacts are left frozen with the inaccuracy recorded (note §11);
the sampler is fixed to the declared block exactly (crashers recorded,
never replaced from outside), and v3 declares 10000–10399.

**Finding 6 — V1's gate was weak and aggregation-mismatched. ACCEPTED.**
v3 gates the pooled edge rate against a 99% bootstrap predictive interval
for a 50-world block's pooled rate — the same aggregation level on both
sides. We note, as the referee's own framing allows, that the three-block
agreement with the derived p_miss (0.0188 / 0.0204 / 0.0215 vs 0.0207) is
substantively strong evidence for the edge-level semantics even though the
gate that certified it was too loose to deserve the credit.

**Environment note.** pytest is indeed absent from the project venv; the
validators are CLI-driven and were run directly. Adding a test harness is
out of scope for this response.
