# G8 plan: interior decisiveness under the exact-contraction bound (draft)

Status: DRAFT for review — not preregistered, no manifest authored, no
execution enabled. Two-part successor to the sealed G7 block; the G7
result stands unchanged (SEPARATING_CONDITIONAL in rule_2/3/7 via the
pinned pivot fallback, `interior_separated_pair_count = 0` everywhere).

## 1. Motivation — what the sealed G7 block and its autopsy showed

G7 (§9 of `docs/g7-conditional-commitment-plan.md`) certified conditional
separation in all three ambiguous worlds, but never at an interior
witness: the shipped localized bound `‖row_c(H_uu⁻¹)‖₂ · ‖r‖₂` (3.1–5.8
per side) dwarfs the exact gap γ = 1.0, so every pair fell back to the
pivot. The post-hoc bound-gap analysis of the sealed block (2026-07-22,
read-only; reconstruction verified bitwise-identical to the sealed
certificates by an adversarial review) established:

1. **The coarseness is exactly Cauchy–Schwarz.** The interior error
   satisfies `H_uu e = −r` with `r = H_uu y_u + H_ub b`, hence
   `e_c = −row_c(H_uu⁻¹)·r` **exactly**. The shipped bound relaxes
   `|g·r|` to `‖g‖·‖r‖`; the measured alignment `|g·r|/(‖g‖‖r‖)` is
   5·10⁻³–0.13, an 8–200× overshoot. `|g·r|` matches the observed field
   error to ~10⁻⁵ (solver noise). This is a decomposition true by
   construction, not an empirical finding.
2. **The exact contraction certifies interior separation on the sealed
   draws, 3/3, one witness each**: rule_2 `X:8:4` margin +0.384, rule_3
   `X:8:1` +0.301, rule_7 `X:14:4` +0.023.
3. **Per-coordinate decisiveness genuinely fails elsewhere.** At the
   non-certifying disputed coordinates the failure is truth, not bound
   slack: conditioned fields hedge (e.g. rule_2 `X:6:9`, fields
   0.67/0.61), and in one case **anti-propagate** — rule_2 branch 1 at
   `X:5:8` settles at −0.007 against its own cochain value 1, i.e. the
   field commits to the *opposing* branch's value. G7 §3.2's "hedging
   disappears" is therefore false as a per-coordinate claim, and
   §3.4(b)'s "the field reports the fork" does not describe a field
   asserting the wrong branch.
4. **The margins are knife-edge, draw-specific facts.** Non-certifying
   interior margins were −0.030 and −0.006 against the certifying
   +0.023–+0.384. "Exactly one decisive coordinate per world" is a fact
   about these draws, not structure of the rules, and must not be
   preregistered as a general property.

## 2. Design principle — why two parts

The exact-contraction bound was **chosen after observing the sealed data
it certifies on**, and because it equals the true error to solver
tolerance, its outcome on the G7 draws is **already computed to the
float**. A single "G8" on the reused draws could not make the assertion
G7's amendment truthfully made (`g7_outputs_or_scores_observed: false`);
it would be postdiction dressed as preregistration. The study therefore
splits:

- **Part I — verification block** (reused G7 draws, outcomes disclosed
  as precomputed): certifies that the frozen harness reproduces the
  precomputed margins. Replication value only; zero discovery content by
  declaration.
- **Part II — test block** (fresh draws, outcomes unobserved): the real
  preregistered test, with predictions at the *mechanism* level only.

Part I seals before Part II is preregistered; Part I observes nothing
about Part II's draws.

## 3. Mechanism — the exact-contraction localized bound

Replace, in the separation role only, the Cauchy–Schwarz step of
`localized_error_bounds`:

```
bound_c = |row_c(H_uu⁻¹) · r| · (1 + LOCAL_BOUND_RELATIVE_SLACK)
          + solver_error_bound
          + LOCAL_BOUND_ABSOLUTE_SLACK
```

- **Soundness argument is unchanged in kind.** For the true Dirichlet
  solution the identity is exact; the computed field differs from it by
  at most the certified solver bound (an L2 residual over a certified
  λ_min lower bound, which dominates every per-coordinate error via
  `‖·‖_∞ ≤ ‖·‖₂`). Same objects, same slack constants, one inequality
  removed.
- **Disclosure (applies equally to the shipped G7 bound):** the
  residual and Green's-row solves are floating-point without certified
  interval arithmetic; the 10⁻⁹ slacks cover the estimated rounding
  contamination (~2·10⁻¹⁰ at the measured condition numbers 86–348) by
  a ~5–10× margin under standard LU forward-error heuristics, not by a
  proof. G7 had ~10 orders of magnitude of headroom here; G8's tight
  bound has ~5–10×. This is stated in the manifest, not hidden.
- **Criterion shape is unchanged**: a pair separates preferentially at
  an interior witness (`γ_c − bound_L − bound_R > 0`), otherwise at the
  always-sound pinned pivot fallback. Witness exclusion
  (`observed_within_bound`) is retained; under the tight bound it can
  never falsely fire, since bound ≥ observed by construction.
- **Everything else is pinned.** Pivot discovery, conditioned branches,
  hedge localization, the G7/G6 base layers, and all thresholds are
  reused bitwise. The G8 layer is additive: a new
  `g8-t6-interior-decisiveness.json` artifact beside the reproduced G7
  artifacts, never a modification of a pinned module.

## 4. Part I — precomputed verification on the G7 draws

- **Cohort and draws**: the 44 G7 draws, reused verbatim.
- **Governance**: the manifest's `draw_provenance` must state, in the
  pattern G7 set but stronger: draws reused, sealed G7 outcomes
  observed, **and the Part I outcome itself precomputed** — a truthful
  `change_scope` on the order of
  `bound_replacement_outcome_precomputed_on_reused_draws`. Part I
  cannot and does not assert unobserved outputs.
- **Precomputed expectations (published in the manifest before the
  run)**: rule_2/3/7 interior-separate with witnesses `X:8:4`, `X:8:1`,
  `X:14:4` and margins +0.38374, +0.30105, +0.02329 each within
  ±2·10⁻⁶ (two solver bounds); all 41 UNIQUE worlds byte-identical to
  their G7 artifacts; zero bound-soundness violations.
- **Interpretation rule, fixed now**: any deviation is an
  implementation defect, not evidence about the mechanism. Part I
  failing blocks Part II until diagnosed; Part I passing licenses
  nothing beyond "the machinery computes what the analysis computed."

## 5. Part II — the test, on fresh draws

- **Cohort**: the same 44 literal worlds (optionally extended — open
  question 8.3). **Draws**: a fresh master seed minted by the frozen
  G6/G7 derivation (`SHA-256(master_seed ‖ world_name)`), committed in
  the manifest before any Part II computation touches it. Nothing
  conditional on the new draws is computed before sealing the
  preregistration.
- **Preregistered claims (falsifiable, mechanism-level):**
  1. *Soundness*: zero bound-soundness violations under the tight
     bound across all worlds and branches.
  2. *Tightness*: at every evaluated interior witness,
     `bound_c − observed_c ≤ 2·solver_bound + slacks` — the bound
     tracks the true error to solver tolerance, so interior
     certification occurs **iff** the oracle margin is positive, up to
     ~2·10⁻⁶.
  3. *Conditional layer unchanged*: conditions invented iff `|S| > 1`;
     hedge localization and the G7 acceptance rules hold as in G7.
- **Explicitly NOT predicted**: the number of ambiguous worlds under
  fresh seeds, the number that interior-separate, per-world outcomes,
  or "exactly one decisive coordinate". The sealed margins straddle
  zero within ±0.03; the count is a **measured outcome**, reported with
  the same secondary-report discipline G7 used for
  `interior_separated_pair_count`. Ambiguity incidence itself may
  change under fresh seeds and is likewise a measured outcome.
- **Failure semantics**: claim 1 or 2 failing falsifies the
  exact-contraction mechanism (block release, defect investigation —
  the G7 `failure_action` pattern). A world where no interior witness
  certifies but the pivot fallback separates is *not* a failure of any
  preregistered claim; it lands in the secondary report.

## 6. Implementation and governance sketch

Mirrors the G7 chain end-to-end, twice (one manifest + amendment chain +
sealed block per part):

- `src/relweblearner/bench/graphlog_g8_conditional.py` — the tight
  `localized_error_bounds` variant plus the interior-decisiveness
  certificate; validated on synthetic systems only (the G7 §7.3 rule:
  no smoke runs on preregistered worlds — for Part II's fresh draws
  this is load-bearing, for Part I it is moot but kept for symmetry).
- `src/relweblearner/bench/graphlog_g8.py` — manifest/amendment
  loading, receipt schema `graphlog-certified-g8-receipt/v1`, execution
  gate disabled until an enabling amendment pins the freeze commit and
  adapter (the three-step G6/G7 chain).
- `src/relweblearner/bench/graphlog_g8_executor.py` — delegates every
  phase to the pinned G7 executor, then appends the G8 overlay artifact
  in T6.
- Output roots: `results/graphlog-certified/g8-verification` (Part I)
  and `results/graphlog-certified/g8` (Part II); archive to
  `/data/graphlog-certified/` destination-verified, as g6/g7.

## 7. Pre-preregistration obligations (from the adversarial review)

Fixes owed before any of this becomes a sealed artifact:

1. Upgrade the bound-gap analysis script's faithfulness check from
   (condition id + one witness) to the full-certificate bitwise
   comparison the review performed, and correct its "bit-for-bit"
   docstring; the corrected script becomes the Part I precomputation
   record.
2. State the heuristic float-slack status for both the shipped and
   tight bounds in the Part I and Part II manifests (§3).
3. Carry the anti-propagation finding (§1.3) into the motivation
   honestly: the claim under test is "conditioning makes at least one
   disputed coordinate decisive", not "conditioned fields snap into
   their valleys".

## 8. Open questions

1. Whether Part II should also seal a *pre-committed analysis script*
   (the Part I precomputation harness re-run on fresh draws) so the
   post-hoc analysis of G8 is itself preregistered.
2. Slack constants for the tight bound: keep the G7 10⁻⁹ pair with the
   ~5–10× heuristic headroom disclosed, or widen (e.g. 10⁻⁸ absolute)
   to restore G7-scale margin at no cost to the +0.023-scale decisions.
3. Whether Part II extends the cohort (held-out GraphLog rules or
   higher-|S| synthetic worlds) to probe multibit conditions and
   `AMBIGUITY_OVERFLOW`, which G6/G7 seeds never exercised — at the
   cost of a larger untested surface inside a preregistered run.
4. Whether the anti-propagation phenomenon (§1.3) deserves its own
   secondary metric in Part II (count of disputed coordinates where a
   conditioned field crosses to the opposing branch value) so the
   §3.2-correction is measured, not anecdotal.
