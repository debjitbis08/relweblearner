# Authors' response to the E6 referee report — all six findings accepted

*2026-07-14. The report (docs/rule27-diagnosis-referee-report.md) is
preserved verbatim. Before acceptance, every episode-level number the
referee computed was independently reproduced: topology identity 1000/1000;
identity repair heals 333 (all 315 split + 18 wrong-argmax) and breaks 0;
the rule patch heals 1 of the 71 "missing-rule" episodes; un-merge changes
all 89 orphan-tainted episodes and fixes 18 of them at net +6 (our
decomposition counts heals 20 / breaks 14 vs the referee's 18 / 12 — two
episodes apart with identical net; recorded as a minor open variance);
repair vs patch differ on 197 predictions with correct-set symmetric
difference 27; the combined probe's predictions coincide with the patch's
on all 1,000. Corrections are worked into the results report ("Referee
corrections" section), design-problem §5/§7/§9/§10, and — for finding
3.2 — settled by new measurement rather than wording.*

## 3.1 (major) — the no-path cell was guaranteed zero. ACCEPTED.

Correct, and it is a plan-design fault of exactly the class our own
discipline is supposed to catch pre-run: the hide sets are disjoint, so the
ensemble rendering emits every edge and preserves topology; H1's
discriminator was vacuous by construction. The H1 conclusion is narrowed
everywhere to what is supported — the seed-0 failure is not loss of a
witnessing path, seed-robustness argues against a stable artifact — and
§9's falsifier is retired only in its stated path-horizon form, with
broader harness interactions explicitly kept live inside the open
0.50 → 0.83 residual (design-problem §9, results report).

## 3.2 (major) — the pre-registered activation trace was not implemented. ACCEPTED, then MEASURED.

The same failure class as E2b's Q-D — a pre-registered measurement silently
dropped — and we accept the finding that `failing_fell_back_to_majority`
traces nothing reliable. Rather than soften wording, we ran the trace and
the referee's suggested causal interventions
(results/rule27-diagnosis/graded-causal.json): committed identities read as
EXACT similarity recover 0.163 → 0.168; translated onto rule inputs,
0.166; zero episodes have an empty graded reduction, while 72% of bridged
rule applications are sim-killed. **The referee's skepticism was vindicated
beyond the report's own claim: the multiplicative-decay account is not
merely unmeasured — it is false as the cause.** "Committed but not
sufficient" stands; the decay explanation is withdrawn; the D3 datum is
replaced by the measured statement that the enrichment changes WHICH
constraint binds (identity for discrete: +0.333 heals-only; not for
graded: +0.005), and the graded mechanism joins the open cells
(design-problem §5, §7, §10).

## 3.3 — attribution cells are markers, not causal shares. ACCEPTED.

The cells are relabeled as precedence markers, and the causal reading is
now the jointly-verified counterfactual table (results report): the split
cell is strongly causal (heals-only, complete), the missing-rule cell is a
marker whose oracle repairs 1/71, and the orphan cell measures
counterfactual sensitivity (net +6), not an 11% causal share.

## 3.4 — "100/103 rules present" and the probe's name. ACCEPTED.

Corrected to "100 ensemble rules vs 103 gold; 15 missing bodies, 15 extra
keys, 6 wrong heads under the chosen translation" in the results report and
design-problem §7. The probe is renamed a MISSING-BODY oracle under the
existing rendered vocabulary, with the non-injectivity caveat recorded
(the resident orphan merge indeed makes two raw labels collide on one
rendered token).

## 3.5 — equal aggregate scores hide different episode behavior. ACCEPTED.

The "two faces" claim is restated at episode level: both interventions heal
the same 315 split-dead episodes (the real mechanistic overlap), differ on
197 predictions, and the combined probe coincides with the patch under this
construction. The aggregate-ceiling phrasing — made two sections after our
own report demonstrated that equal aggregates can hide offsetting changes —
is withdrawn.

## 3.6 — the authenticity claim overreaches. ACCEPTED.

The provenance note now says what is true: the fetched data and frozen code
reproduce all four frozen aggregate accuracies exactly — a strong
regression check, not a byte-level authenticity proof; no independently
published checksum is available.

## On the recommendation

Adopted in full: the accepted conclusions are the seed-draw finding and the
deterministic heals-only hub repair; the H1 retirement is narrowed to path
preservation; the D3 promotion is corrected by measurement; the rule
inventory language is fixed; and both residuals — the discrete 0.50 → 0.83
gap and the now-open graded failure mechanism — are recorded as open,
licensed cells (design-problem §10).
