# G8 plan: interior decisiveness under the exact-contraction bound

Status: COMPLETED — both parts preregistered, executed, sealed, and
archived 2026-07-23; the execution outcome is recorded in §9. Two-part
successor to the sealed G7 block; the G7 result stands unchanged
(SEPARATING_CONDITIONAL in rule_2/3/7 via the pinned pivot fallback,
`interior_separated_pair_count = 0` everywhere).

Sections 1–8 are the plan as preregistered, kept verbatim; §9 was
added after both blocks sealed.

## 1. Motivation — what the sealed G7 block and its autopsy showed

G7 (§9 of `docs/g7-conditional-commitment-plan.md`) certified conditional
separation in all three ambiguous worlds, but never at an interior
witness: the shipped localized bound `‖row_c(H_uu⁻¹)‖₂ · ‖r‖₂` (3.1–5.8
per side at the best interior witnesses; up to 37.2 across all disputed
coordinates) dwarfs the exact gap γ = 1.0, so every pair fell back to
the pivot. The post-hoc bound-gap analysis of the sealed block (2026-07-22,
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
4. **The margins are knife-edge, draw-specific facts.** The full set of
   non-certifying tight interior margins is −0.194 (rule_2 `X:5:8`),
   −0.057 (rule_2 `X:6:9`), −0.030 (rule_7 `X:14:2`), −0.006 (rule_3
   `X:5:12`), against the certifying +0.023, +0.301, +0.384. Two of the
   seven sit within ±0.03 of zero. "Exactly one decisive coordinate per
   world" is a fact about these draws, not structure of the rules, and
   must not be preregistered as a general property.

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
- **Part II — measurement block** (fresh draws, outcomes unobserved): a
  preregistered *calibrated measurement* (§5) — instrument claims that
  are theorems, empirical claims that can genuinely fail, and the
  interior-decisiveness distribution reported without prediction.

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
  (`observed_within_bound`) is retained; under the tight bound it
  cannot falsely fire *in exact arithmetic* (bound ≥ observed by the
  triangle inequality, solver-error sign absorbed) — in float it holds
  only up to the disclosed heuristic slack, so any firing is a genuine
  slack-breach alarm signalling an implementation defect, not a
  discarded witness.
- **Everything else is pinned.** Pivot discovery, conditioned branches,
  hedge localization, the G7/G6 base layers, and all thresholds are
  reused bitwise. The G8 layer is additive: a new
  `g8-t6-interior-decisiveness.json` artifact beside the reproduced G7
  artifacts, never a modification of a pinned module.

## 4. Part I — precomputed verification on the G7 draws

- **Cohort and draws**: the 44 G7 draws, reused verbatim.
- **Governance**: the manifest's `draw_provenance` must state, in the
  pattern G7 set but stronger: draws reused, sealed G7 outcomes
  observed, **and the Part I outcome itself precomputed**. The
  `change_scope` is a loader-validated literal (G7's loader checks the
  exact string), fixed at manifest-authoring time as
  `bound_replacement_outcome_precomputed_on_reused_draws`. Part I
  cannot truthfully carry G7's loader-enforced
  `g?_outputs_or_scores_observed: false` attestation; its amendment
  schema instead enforces a non-empty outcome-disclosure field naming
  the precomputation record, so the disclosure is mechanical, not
  discretionary.
- **Precomputed expectations (published in the manifest before the
  run)**: rule_2/3/7 interior-separate with witnesses `X:8:4`, `X:8:1`,
  `X:14:4` and margins 0.3837413504669355, 0.3010490853163964,
  0.023287620838464473 — **full precision, emitted by the sealed §7.1
  precomputation script** (whose summation order is authoritative; an
  independent recomputation differed in the last ulp on rule_2), never
  rounded quotes (a 5-decimal quote of
  the rule_7 margin differs from the true value by 2.4·10⁻⁶ and would
  fail its own tolerance on a perfect rerun). Tolerance per margin:
  2 × `field_tolerance` (= 2·10⁻⁶, the *guaranteed* solver ceiling; the
  sealed 9.9·10⁻⁷ bounds are outcomes, not guarantees) plus an explicit
  small cross-platform reproducibility allowance; Part I additionally
  records whether the same-host rerun was bit-identical. Byte-identity
  is asserted per reproduced G7-layer artifact (receipts excluded —
  they carry the G8 receipt schema and list the overlay); conditioned
  worlds get the interior-decisiveness certificate, all other worlds an
  explicit passthrough overlay record. Zero bound-soundness violations.
  Part I overlay statuses use a distinct vocabulary
  (`VERIFIED_PRECOMPUTED`, not any `SEPARATING*` string) so a sealed
  Part I artifact cannot be miscited as a finding.
- **Interpretation rule, fixed now**: any deviation is an
  implementation defect, not evidence about the mechanism. Part I
  failing blocks Part II until diagnosed; Part I passing licenses
  nothing beyond "the machinery computes what the analysis computed."

## 5. Part II — preregistered calibrated measurement, on fresh draws

Part II is honestly a **preregistered calibrated measurement**, not a
hypothesis test in the classical mold. Its instrument claims are
exact-arithmetic theorems (below); their preregistration certifies the
*instrument*, and the scientific content is the measured distribution of
interior decisiveness under fresh draws, reported without prediction.

- **Cohort**: the same 44 literal worlds (extension deferred — open
  question 8.2). **Draws**: a fresh master seed through the frozen
  G6/G7 derivation (`SHA-256(master_seed ‖ world_name)`).
- **Seed-minting ceremony (mechanism, not honesty assertion):** the
  master seed is minted by a single disclosed invocation (the G7
  `master_seed_generation` pattern: `openssl rand -hex 32`, after the
  freeze commit, before any expansion), logged in the amendment chain
  with an attestation that **no other master seed was ever expanded**;
  any remint requires a disclosed amendment stating why. Preferred
  hardening (open question 8.1): derive the seed from a named public
  randomness beacon pulse committed to before it exists. Deriving from
  the Part I block digest is NOT acceptable — Part I's outputs are
  precomputable by design. The sealed margins sit within ±0.03 of zero
  at two of seven coordinates, so seed shopping could plausibly move
  the headline count; the ceremony exists to make that impossible, not
  merely disavowed.
- **Instrument claims (preregistered; exact-arithmetic theorems whose
  only empirical content is the float-slack heuristic):**
  1. *Soundness*: zero bound-soundness violations under the tight
     bound. (Theorem: obs ≤ |g·r| + solver_bound ≤ bound, triangle
     inequality; can fail only via implementation defect or slack
     breach.)
  2. *Tightness*: at every evaluated interior witness,
     `bound_c − observed_c ≤ 2·solver_bound + slacks`. (Derivable a
     priori — the form is analytically forced, not tuned on sealed
     data; it guarantees the instrument reads the oracle margin to
     ~2·10⁻⁶, which is precisely what makes the measured counts below
     trustworthy.)
  A failure of either is an implementation/float defect: block release,
  defect investigation, the G7 `failure_action` pattern.
- **Empirical claims (preregistered, genuinely falsifiable):**
  3. *Hedge localization holds on fresh draws*: for every conditioned
     world the unconditioned field's mean absolute error on agreeing
     coordinates is ≤ 0.1 (the one G7 acceptance rule with real
     empirical teeth on new draws; it can genuinely fail).
  4. *Conditions invented iff `|S| > 1`*, with the G7 cap and overflow
     semantics (`AMBIGUITY_OVERFLOW` is a reported outcome, not a
     defect — fresh seeds may organically exercise multibit paths never
     run under any seed; the synthetic tests are the only prior
     validation, and that is disclosed).
- **Non-vacuity clause (fixed now):** if fewer than **2** worlds have
  `|S| > 1` under the fresh draws, the block is reported *empirically
  uninformative for interior decisiveness* and no mechanism claim of
  any strength is made — the G7 `non_vacuity` rule's failure_action
  pattern. Ambiguity incidence was 3/44 under one seed; zero is a live
  possibility and must not read as success.
- **Acceptance rules are rewritten, not imported.** G7's `no_regression`
  rule (byte-identity with the sealed G6 block) is unsatisfiable and
  meaningless on fresh draws; G7's loader hard-requires the G6 draws.
  The Part II manifest carries its own acceptance-rule set scoped to
  whichever fresh worlds turn out ambiguous, and the G8 loader performs
  its own seed-derivation/expansion self-validation instead of the G7
  loader's cross-check against G6.
- **Explicitly NOT predicted**: the number of ambiguous worlds under
  fresh seeds, the number that interior-separate, per-world outcomes,
  or "exactly one decisive coordinate" (the sealed non-certifying
  margins −0.194, −0.057, −0.030, −0.006 against certifying +0.023,
  +0.301, +0.384 show these are draw-specific facts). All are
  **measured outcomes** under the secondary-report discipline G7 used
  for `interior_separated_pair_count`. Secondary reports include: the
  interior-decisiveness count, per-witness margins, the
  anti-propagation count (disputed coordinates where a conditioned
  field crosses to the opposing branch's value — promoted from open
  question to preregistered secondary metric), and the max (not just
  mean) off-scope field error, since sealed rule_2 hides a 1.10
  pointwise excursion under a passing 0.016 mean.
- **Failure semantics**: a world where no interior witness certifies
  but the pivot fallback separates is *not* a failure of any
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
  `/data/graphlog-certified/` destination-verified, as g6/g7. Both
  need literal `.gitignore` entries (the `.g*.partial` staging pattern
  already covers both).
- **Ordering link**: the Part II manifest pins the sha256 of the sealed
  Part I `study-index.json`, turning "Part I seals before Part II is
  preregistered" from prose into a checkable fact. (This is an
  ordering witness only — it must not be the seed source, per §5.)
- Two-manifest structure means **two full repository preflights and two
  archive/symlink/destination-verify steps**; the G7 refuse-resume rule
  for environmentally killed runs (amendment-3 disposition pattern:
  delete the partial unobserved, amend, relaunch — never resume) is
  inherited explicitly for both parts.

## 7. Pre-preregistration obligations (from the adversarial review)

Fixes owed before any of this becomes a sealed artifact:

1. Upgrade the bound-gap analysis script's faithfulness check from
   (condition id + one witness) to the full-certificate bitwise
   comparison the review performed, and correct its "bit-for-bit"
   docstring; the corrected script becomes the Part I precomputation
   record and the source of §4's full-precision expectations.
2. **Seal a pre-committed Part II analysis script** (the §7.1 harness
   parameterized over fresh draws), so the post-hoc analysis of G8 is
   itself preregistered. Promoted from open question: the entire G8
   motivation is that an un-preregistered post-hoc analysis chose the
   next bound, and leaving the analysis loop open reopens exactly that
   for G9.
3. State the heuristic float-slack status for both the shipped and
   tight bounds in the Part I and Part II manifests (§3).
4. Carry the anti-propagation finding (§1.3) into the motivation
   honestly: the claim under measurement is "conditioning makes at
   least one disputed coordinate decisive", not "conditioned fields
   snap into their valleys".

## 8. Open questions — all resolved 2026-07-23, before Part II authoring

1. Seed-source hardening (§5): **RESOLVED — beacon.** The master seed
   derives from a named future NIST beacon pulse (chain 2, first pulse
   at or after 2026-07-23T03:20:00Z) committed to before it existed in
   `results/graphlog-certified/g8-seed-commitment.json`; the commit
   containing that document predates the pulse. Operational cost was
   measured (one HTTP fetch, service reachable) and accepted.
2. Cohort extension: **RESOLVED — keep the 44 worlds**, as the
   standing call already stated; fresh seeds may organically produce
   `|S| > 2`, which §5's claim 4 handles (reported outcome,
   synthetic-only prior validation disclosed).
3. Slack constants: **RESOLVED — keep the G7 10⁻⁹ pair, disclosed.**
   Part I verified the instrument bit-identically with these exact
   constants (imported from the pinned G7 module); widening for
   Part II would re-freeze code and forfeit "Part I verified the same
   instrument Part II measures with." The ~5–10× heuristic headroom
   stays disclosed in both manifests' `float_slack_status`.

## 9. Execution outcome — sealed blocks (2026-07-23)

Both parts ran exactly once, in the preregistered order, each fully
detached with the harness log ending in an atomic `PROMOTED` rename.
Every quantitative statement below is read from the sealed blocks, the
pre-committed Part II report, or the pinned manifests; nothing here
amends the preregistered sections above.

### 9.1 Part I — verification block (`g8-verification`)

Study `sha256:e8679fb8…`, amendment chain `sha256:cc17e5b7…` (disabled)
→ `sha256:d251d9b9…` (enabling, adapter `execute_phase_verification`).
PROMOTED after 393.0 minutes; 220/220 sealed units (5 phases × 44
worlds), log clean.

Verification (same day, read-only): 220/220 receipts re-hashed against
their declared `byte_size`/`sha256` artifact records (G8 receipt
schema); manifest chain recomputed via `canonical_digest`; overlay
vocabulary clean — exactly rule_2/rule_3/rule_7 carry
`VERIFIED_PRECOMPUTED`, the other 41 `VERIFIED_PRECOMPUTED_PASSTHROUGH`,
and no overlay status carries a `SEPARATING*`/`INTERIOR*` success
string (the manifest's `status_vocabulary` rule; the bitwise-reproduced
G7-layer artifacts in rule_2/3/7 legitimately retain their own
`SEPARATING_CONDITIONAL` status, and the overlay's carryover field
quotes it).
All `part1_precomputed_expectations` matched with margins
**bit-identical** to the precomputed values (delta 0.0 against a
tolerance of 2·10⁻⁶ + 10⁻⁹): rule_2 `X:8:4` +0.384, rule_3 `X:8:1`
+0.301, rule_7 `X:14:4` +0.023, pivots `X:3:4`/`X:0:4`/`X:2:13` exact.

As declared in §2 and §4, Part I licenses no scientific claim. Its
completion (a) certifies that the frozen harness reproduces the
precomputed tight-bound margins on the G7 draws, and (b) unblocked
Part II, whose manifest pins the sha256 of the sealed Part I
`study-index.json` (`b86f258b…`) as the §6 ordering witness.

### 9.2 Part II — measurement block (`g8`): provenance

Study `sha256:851f28d2…`, amendment chain `sha256:a8e48683…` (disabled)
→ `sha256:af931c86…` (enabling, adapter `execute_phase_test`).

- **Seed ceremony (§5, resolved §8.1):** the selection rule — first
  NIST beacon chain-2 pulse at or after 2026-07-23T03:20:00Z, master
  seed = SHA-256 of the hex-decoded `outputValue` — was committed in
  `g8-seed-commitment.json` at 03:01:09Z (commit `0c762dc`), nineteen
  minutes **before the pulse existed**. The realized pulse is index
  1871520; per-world draws derive via the frozen
  `SHA-256(master_seed ‖ world_name)` expansion, validated by the
  loader's self-check. Honesty scope: the pre-pulse ordering rests on
  local evidence (commit header, reflog, and git object mtime agree to
  the second) — the commit was not pushed to a public remote before
  the pulse, so an external verifier gets a corroborated attestation,
  not a public anchor. The pulse itself is externally checkable: the
  beacon's published `outputValue` for pulse 1871520 reproduces the
  manifest's master seed and all 44 per-world expansions.
- **Analysis precommitment (§7.2):** `scripts/g8_part2_report.py` was
  pinned in the same pre-pulse commit and never modified after it
  (byte-identical at HEAD). That it was the **first read** of the
  sealed block after promotion is a process attestation, as are
  "single launch, no remint, no resume" below. All numbers in
  §9.3–§9.4 are from its output
  (`record_type: g8-part2-preregistered-report/v1`).
- **Run:** PROMOTED after 419.5 minutes; 220/220 sealed units; log
  clean; no `.partial` staging remnants; single launch, no remint, no
  resume.
- **Post-seal verification:** 220/220 receipts re-hashed OK (G8 schema,
  directory contents equal to artifact records, byte sizes match);
  manifest chain recomputed via `canonical_digest` with all parent and
  study links consistent. Both blocks archived to
  `/data/graphlog-certified/` with a destination re-hash (220/220 OK)
  and full file-listing comparison performed while both copies still
  existed — the sealed Part II `study-index.json` hashed identically
  at source and destination before the local copy was replaced by a
  symlink — and the pre-committed report reproduces semantically
  identical output through the symlinked path.

### 9.3 Part II — preregistered claims: all four passed

Instrument claims (exact-arithmetic theorems; a failure would have been
an implementation/float defect blocking release):

1. **Tight-bound soundness**: zero bound-soundness violations across
   all evaluated witnesses in all 44 worlds.
2. **Tight-bound tightness**: zero witness-exclusion alarms — under the
   tight bound `observed_within_bound` can only fire on a float-slack
   breach, and it never fired.

Empirical claims (genuinely falsifiable on fresh draws):

3. **Hedge localization**: passed in every conditioned world — mean
   absolute error of the unconditioned field on agreeing coordinates
   0.0166–0.0213 against the 0.1 threshold (agreeing-coordinate counts
   193–251 per world).
4. **Conditions iff ambiguous**: zero iff-violations; conditions were
   invented in exactly the worlds with `|S| > 1`, and no
   `AMBIGUITY_OVERFLOW` occurred.

**Non-vacuity (§5): met.** Six of 44 fresh draws were ambiguous —
`rule_2, rule_5, rule_6, rule_8, rule_9, rule_12` — against the
preregistered minimum of 2, so the block is empirically informative
for interior decisiveness.

### 9.4 Part II — measured outcomes (secondary report; none predicted)

Under the §5 discipline, everything in this subsection is a measured
outcome: none of these numbers was predicted, and none licenses a
claim beyond its own value.

**Headline measurement: all six ambiguous worlds certified
`INTERIOR_SEPARATING`** (interior-decisiveness count 6/6; the status
requires at least one branch pair separated at an interior witness).
Every branch pair in every conditioned world separated; 8 of the 10
pairs separated at interior witnesses:

| world   | branches | pivots           | pairs interior / total | interior margins (per pair)  | hedge mean / max err | anti-prop coords |
|---------|----------|------------------|------------------------|------------------------------|----------------------|------------------|
| rule_2  | 3        | `X:4:1`, `X:4:7` | 2 / 3                  | 0.419, 0.429                 | 0.019 / 0.449        | 0                |
| rule_5  | 2        | `X:1:1`          | 1 / 1                  | 0.699                        | 0.021 / 0.980        | 2                |
| rule_6  | 3        | `X:0:8`, `X:0:13`| 2 / 3                  | 0.420, 0.171 (third −0.128)  | 0.017 / 0.465        | 5                |
| rule_8  | 2        | `X:0:13`         | 1 / 1                  | 0.037                        | 0.017 / 0.902        | 5                |
| rule_9  | 2        | `X:1:6`          | 1 / 1                  | 0.088                        | 0.018 / 0.593        | 4                |
| rule_12 | 2        | `X:1:15`         | 1 / 1                  | 0.011                        | 0.020 / 1.004        | 4                |

The two non-interior pairs differ in kind: rule_2 pair 0–1 separated
directly at the pinned pivot `X:4:1` (witness kind `pinned`; no
interior margin was evaluated for that pair — its per-pair margin is
null in the report), while rule_6 pair 1–2 fell back to the pivot
`X:0:13` (witness kind `pinned_fallback`) after its best interior
margin came out negative (−0.128). Neither is a failure of any
preregistered claim (§5 failure semantics).

Measured facts worth recording:

1. **The fresh conditioned set is different.** rule_2/5/6/8/9/12 versus
   the sealed G7 draws' rule_2/3/7 — only rule_2 is common, and
   ambiguity incidence doubled (6/44 vs 3/44). Which worlds condition
   is a draw-level fact, exactly as §5 anticipated by refusing to
   predict it; claim 4 held on both sides of the change.
2. **Multibit conditioning ran on organic draws for the first time.**
   rule_2 and rule_6 each drew three exact solutions (two pivot
   coordinates, three realized branches) — a path previously exercised
   only by the synthetic tests, as §5's claim-4 disclosure flagged. It
   ran within the cap, with no overflow and no iff-violation.
3. **Margins remain knife-edge in places.** The certifying interior
   margins span 0.011–0.699; rule_12 (+0.011) and rule_8 (+0.037) are
   the fresh-draw analogues of the sealed +0.023, and rule_6's third
   pair shows a negative best interior margin (−0.128) alongside two
   certifying pairs. The §1.4 warning — decisive coordinates are
   draw-specific facts, not rule structure — survives contact with new
   data.
4. **Anti-propagation recurred**: 20 branch–coordinate crossing
   records across five of the six worlds (per-world counts 0, 2, 5, 5,
   4, 4; 19 unique coordinates — one rule_6 coordinate crosses in two
   branches) where a conditioned field crosses to the opposing
   branch's value. The §7.4
   framing is confirmed as the honest one: conditioning makes at least
   one disputed coordinate decisive; it does not snap conditioned
   fields into their valleys.
5. **Means hide excursions, as disclosed.** Max off-scope pointwise
   errors run 0.449–1.004 while every mean stays ≤ 0.0214 — the sealed
   rule_2 pattern (a 1.10 excursion under a 0.016 mean) generalizes;
   the max was preregistered as a secondary metric for exactly this
   reason.

### 9.5 What is licensed, and what is not

The instrument is now validated prospectively: the tight bound read
fresh-draw interior margins with zero soundness violations and zero
tightness alarms, under seeds that could not have been shopped and
outcomes that were not observed before the pre-committed report ran.
Hedge localization is a replicated empirical regularity (G7 sealed
draws and now fresh draws). The 6/6 interior-decisiveness result is a
measured distribution under one fresh master seed — honest evidence
that the sealed-draw 3/3 was not an artifact of those draws, but by
this block's own discipline it is a point estimate, not a universal
claim. The open threads it sharpens: a mechanism-level account of
anti-propagation, the distribution of near-zero margins under further
seeds, and rule-generalization beyond the frozen 44-world cohort
(§8.2, deliberately deferred).
