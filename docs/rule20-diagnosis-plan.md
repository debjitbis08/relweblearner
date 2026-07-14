# The rule_20 diagnosis (E5) — pre-registered diagnostic plan

*Written 2026-07-14, BEFORE any diagnostic code is run. A DIAGNOSIS, not a
bench: no scored pass/fail predictions; the deliverable is a torn-episode
attribution with causal (heal/break) probes. Pre-committed so hypotheses,
discriminators, and priors are frozen before data can steer them. E5 is the
head of design-problem §10's empirical queue, and D3/T6 wait on it: the
graded arm is the project's only two-timescale attempt, and rule_20 is where
it TEARS. This plan applies every E6 lesson: each discriminator gets a
data-free vacuity check (§6a) after E6's H1 proved structurally vacuous;
attribution is designed as counterfactual heal/break sets from the start,
never precedence labels presented as causal shares; a plan-to-code checklist
(§6b) is audited before bring-up, after referees twice caught pre-registered
measurements dropped in implementation; seed-robustness is mandatory after
E6's "immunity" dissolved across draws; provenance vocabulary (a)/(b) as in
multiweb-overlap-forgery-plan.md §8.*

## 1. The question this settles

The graded ensemble (multiweb_graded, the D4/two-timescale attempt) is
bimodal on the 44 held-out GraphLog worlds: it heals rule_26 (0.29→0.64),
rule_30, rule_42, pushes rule_32 above gold-pooled — and TEARS rule_20 from
0.659 to 0.317, BELOW the single view's 0.358. The graded-ensemble report
asserted a mechanism ("soft cross-firing adds competing wrong activations
that win argmaxes") but never measured it; E6's revision then showed how
dangerous asserted graded mechanisms are — our multiplicative-decay account
of rule_27 was refuted the day it was tested. Meanwhile E6 left an open
cell that this diagnosis can close: on rule_27 the graded failure is NOT
identity (commits-exact moved 0.163 only to 0.168), mechanism undiagnosed.

The question: **what, mechanically, does soft coupling break on rule_20
that hard identity had already solved — and is it the same mechanism as
rule_27's graded failure?** D3 (enrichment exposure) and T6 (enrichment
soundness: graded derivations approximate exact ones with stated error)
need the answer before any enrichment is formalized: rule_20 is the world
where the approximation error is catastrophic and selector-grade.

## 2. The frozen facts (provenance (a))

From results/multiweb-graphlog/results.json and
results/graded-ensemble/graphlog.json, world rule_20, seed 0:

- Discrete: view-alone 0.358, ensemble 0.659, gold-pooled 0.752
  (cyk-oracle 0.856; majority prior 0.177). The discrete mapping is
  PERFECT: 6 anchors + 7 extended, ext_precision 1.0, zero wrong pairs,
  coverage 0.8125. Rules: 74 alone / 95 ensemble / 91 gold — the ensemble
  inventory is LARGER than gold's (so at least 4 ensemble keys are not
  gold's; counted properly per the E6-referee containment lesson, §4).
- Graded: **0.317** — a 0.342 tear below discrete, 0.041 below the single
  view. Graded hardened() made 5 new commits at precision 0.6: **2 wrong,
  both orphan-type** (a token committed to a counterpart invisible to the
  other view). Contrast rule_27: graded commits there were 4/5 correct.
- Both runs used seed 0 and identical views/anchors (the graded bench
  reuses MG.make_views/pick_anchors), so per-episode discrete-vs-graded
  comparison is exact and paired.
- Arithmetic floor for the attribution: accuracies 0.659 vs 0.317 mean
  ≥ 342 of 1,000 episodes flip right→wrong net; the torn set is large by
  construction, so per-episode attribution has plenty of signal (this is
  the §6a non-vacuity check for the flip table).

## 3. Hypotheses, with declared priors

Distinct mechanisms by which graded reduction can lose what discrete
reduction had; not exclusive. Declared priors: **H1 and H3 elevated** (the
report's own asserted mechanism, and the one thing E6 measured about graded
reduction — massive wrong-mass tolerance: zero empty reductions with 72% of
bridged applications sim-killed on rule_27); H2 is cheap and must be
excluded first (it is the only hypothesis with a visibly wrong recorded
input: the 2 wrong commits); H4 last.

- **H1 — spurious cross-firing.** Rules from web B fire on A-token spans
  through NONZERO similarity between non-counterpart tokens
  (S is a dense softassign field; sim > 0 does not mean identity), and the
  summed wrong-head activation outruns the exact derivation's. The tear
  should then concentrate where B-rules with sub-identity sim factors win
  the argmax.
- **H2 — wrong commits pollute aggregation.** The 2 wrong orphan commits
  enter merge_of, so distinct output symbols pool their activation under
  one name at the argmax. Cheap, visible, and testable by removing exactly
  those two entries.
- **H3 — aggregation semantics (sum vs count).** Discrete counts one vote
  per (path, reduction); graded SUMS graded activation across paths and
  spans. A wrong label reachable many soft ways can outweigh a right label
  derived exactly once, even with a perfect similarity field. If H3 binds,
  the tear survives even under an exact-identity similarity.
- **H4 — beam and floor artifacts.** TOP_K = 8 / ACT_MIN = 0.01 pruning
  drops correct low-activation intermediates in favor of dense wrong mass.

## 4. The instrument

A new module `src/relweblearner/bench/rule20_diag.py`, reusing the frozen
graphlog / multiweb_graphlog / multiweb_graded machinery unchanged; no
frozen constant is modified (probe variants pass their own values as
arguments). All numbers below are provenance (b) unless read from the
artifacts. Output to `results/rule20-diagnosis/`. Consistency gate first,
as in E6: recompute discrete 0.358 / 0.659 / 0.752 AND graded 0.317 at
seed 0; refuse to attribute on any mismatch.

**4a. The flip table with winner trace (the core).** Paired per-episode
outcomes: {both-right, both-wrong, torn (discrete right → graded wrong),
healed (discrete wrong → graded right)}. For every torn episode, a traced
`graded_predict` (the E6 `traced_reduce` pattern, extended) records the
provenance of the WINNING wrong label's strongest contribution: which rule
fired at the top application (A-web or B-web rule), the two sim factors
(1.0 = exact, < 1 = bridged), whether a committed merge pooled the winning
mass (and whether one of the 2 wrong commits is involved), and the number
of paths contributing to winner vs to the discrete-correct label. Each torn
episode is then MARKED (not causally attributed — E6 lesson) as
cross-fired (some winning factor < 1), commit-pooled (merge_of moved mass
onto the winner), sum-outvoted (all factors exactly 1, no commit involved —
H3's signature cell), or beam-starved (the correct label was pruned at some
span: present pre-prune, absent post-prune).

**4b. Causal probes — each reported as (accuracy, heals, breaks) episode
sets, never aggregate-only (E6-referee lesson 3.5):**

- *P-commits (H2):* remove exactly the 2 wrong commits from merge_of (and
  from the sim shortcut if committed pairs receive one), all else frozen.
  Also the anchors-only variant (no hardened commits at all).
- *P-ident (H1):* similarity replaced by the exact-identity indicator
  (1 iff same token, else 0), keeping both-web rules, sum aggregation,
  beams, and merge_of. This removes ALL soft cross-firing while preserving
  the graded aggregation semantics — by §6a it is NOT equivalent to the
  discrete system, so a residual tear here is H3's direct evidence, and
  full recovery to ~0.659 is H1's.
- *P-sum (H3):* aggregation ablation, similarity frozen: replace
  `total[s] += a` with max-pooling across paths, and separately with the
  discrete count-of-reductions vote. If H3 binds, these recover what
  P-ident does not.
- *P-beam (H4):* bounded ablations holding everything else frozen:
  TOP_K ∈ {16, 32}, ACT_MIN ∈ {0.001, 0}; declared bounded (no unbounded
  beam — cost), so H4 can only be SUPPORTED or left open, never fully
  excluded, and the report must say so.

**4c. Robustness (mandatory after E6).** The flip table at seeds 1–4: does
the tear survive other view draws, or was rule_20's collapse — like
rule_27's immunity — a property of the draw? Reported separately, never
pooled.

**4d. The rule_27 companion cell (closes E6's open residual).** Run 4a
(flip table + winner trace) on rule_27 seed 0 unchanged. E6 established
its graded failure is not identity; the trace says what it is, and whether
rule_20 and rule_27 share a mechanism — the exact question §10's E5 entry
now poses for D3.

## 5. Outcome routing (fixed now)

- **Mostly H1 (cross-fired cells dominate, P-ident recovers most of the
  tear)** → the multiplicative-similarity enrichment admits unbounded
  false inference mass; D3's admissible-enrichment set must exclude it or
  add competition control; T6's error bound gets its counterexample world.
- **Mostly H3 (sum-outvoted cells; P-sum recovers what P-ident does not)**
  → the linearization itself (sum-pooling over paths) is the wrong shadow;
  feeds the cellular-sheaf linear-layer choice directly (§3): the harmonic
  object must not conflate multiplicity with evidence.
- **Mostly H2 (P-commits recovers the tear)** → the graded commit gate
  (mutual argmax + HARD_SIM) is weaker than the discrete
  destructive-evidence gate in exactly the way the graded bench's forgery
  arm warned; a policy-layer finding (P1-family), not an enrichment one.
- **Mostly H4** → bench/parameter constraint; report as such, do not
  formalize around it.
- **Tear disappears at seeds 1–4** → draw-specific, the E6 precedent; the
  selector datum weakens accordingly and D3 must not be built on rule_20
  alone.
- **rule_27 companion shares the dominant mechanism** → one graded failure
  mode, two worlds; E6's open cell closes into E5's account. If it does
  NOT share it, both mechanisms go to D3 as separate selector data.

Whatever the outcome ships in results/rule20-diagnosis/ and is folded into
design-problem §5 D3 / §7 E5 / §10 by the established convention.

## 6. Discipline

### 6a. Vacuity checks (data-free, done at plan time — the E6 §3.1 lesson)

- *Flip table*: non-vacuous by arithmetic — the 0.342 accuracy gap forces
  ≥ 342 net torn episodes (§2).
- *P-ident vs discrete*: NOT structurally equivalent — under exact-identity
  similarity the graded system still differs from discrete CYK in rule
  pool (both webs' rules), aggregation (activation sums across paths and
  splits vs one vote per path-reduction), beams (TOP_K/ACT_MIN), and
  merge_of pooling. A tear surviving P-ident is therefore meaningful (H3
  evidence), not a tautology. Conversely P-ident CANNOT separate H3 from
  H4; that is P-sum's and P-beam's job.
- *P-commits*: non-vacuous — the 2 wrong commits are recorded in the
  frozen artifact; removing them changes merge_of by construction.
- *P-beam*: bounded by declaration; can support but never exclude H4.
- *Winner trace cells*: exhaustive and disjoint by construction
  (factor < 1 | commit-pooled | all-exact-no-commit | pruned-correct); an
  episode can carry several marks, and marks are NOT causal shares — the
  probes are.

### 6b. Plan-to-code checklist (audited before bring-up — the §10 process rule)

| plan item | implementing function in rule20_diag.py |
|---|---|
| consistency gate (discrete triple + graded 0.317) | `gate()` |
| §4a flip table | `flip_table()` |
| §4a winner trace + episode marks | `winner_trace()` (traced reduce/predict) |
| §4b P-commits (both variants) | `probe_commits()` |
| §4b P-ident | `probe_identity_sim()` |
| §4b P-sum (both aggregations) | `probe_aggregation()` |
| §4b P-beam (four settings) | `probe_beam()` |
| §4c seeds 1–4 flip tables | `robust_seeds()` |
| §4d rule_27 companion | `companion_rule27()` |
| heal/break episode sets for every probe | `audit()` shared helper |

The bring-up commit must state that each row above exists and runs; a row
dropped for any reason is reported as dropped BEFORE results are read, not
discovered by a referee after.

### 6c. The usual rules

Probes are diagnostic counterfactuals using evaluation-side gold where
needed; none is a system capability. No frozen artifact is rewritten; any
bench bug found gets its own pre-registered fix plan. Diagnosis before
formalization: D3/T6 language changes only after this run, citing it.
