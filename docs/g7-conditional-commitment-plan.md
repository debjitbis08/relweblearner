# G7 plan: conditional commitments for ambiguous worlds (draft)

Status: DRAFT for review — not preregistered, no manifest authored, no execution
enabled. Successor study to the sealed G6 block; the G6 result stands unchanged
as a preregistered negative on separation.

## 1. Motivation — what the sealed G6 block showed

The G6 block (`results/graphlog-certified/g6`, study
`sha256:8b31eac9…`, amendment chain tip `sha256:112cfe12…`) is complete and
verified: 220/220 receipts sealed. Its separation findings:

- 41/44 worlds passed T6 separation **vacuously** (`INSUFFICIENT_BEHAVIORS`:
  a unique identity extension, nothing to separate).
- The only three worlds with genuine twofold ambiguity — rule_2, rule_3,
  rule_7 — all failed with `BUDGET_CONSUMED`: witness gap γ = 1.0 against
  summed budgets of 19.2–27.5.

Post-hoc analysis of the sealed artifacts (read-only; no draws or scores
re-used) established the causal chain:

1. The winning witness is always the single-node `decode_identity`
   derivation, so the budget is exactly the T5 **global** field error bound.
2. With `boundary_mismatch = 0` in every world, that bound reduces to
   `κ_δ · ‖δy‖ = (1/√λ_min) · naturality_defect` — about 7× above the
   measured global error (bounds 8.7–14.1 vs actual 1.28–2.08).
3. The mismatch is structural, not numeric: γ is a **3–4 coordinate sup-norm
   disagreement** while the budget is an **L2 bound over the full ~200-
   coordinate cochain**. Even the *actual* global error (~1.8/side) exceeds
   γ = 1.0, so no bound tightening alone can certify separation.
4. Per-coordinate inspection at the disagreement coordinates splits the
   three failures into two causes:
   - **rule_3** — the shared field is locally decisive (errors 0.07–0.23
     toward extension 0 at all three disputed coordinates). Failure is pure
     certificate coarseness; a localized bound rescues it.
   - **rule_2, rule_7** — the shared field genuinely hedges (values 0.25–
     0.62 at disputed coordinates, leaning toward *different* extensions at
     different coordinates). One relaxed state cannot represent a
     disjunction; averaging is intrinsic, not a defect.
5. In all three worlds the disputed coordinates flip **together**: the
   ambiguity is exactly one bit (two global solutions), never several
   independent ones.

## 2. Design principle

Reify ambiguity instead of averaging over it or forcing a choice. When the
exact solution set contains more than one extension, the web **grows a named
condition** (a pivot hypothesis stated in its own vocabulary) and produces
**conditional answers**: `A if C, B if ¬C`. Conditions are invented only when
required (one bit per surviving twofold ambiguity), remain first-class,
queryable, and dischargeable by future evidence, and the certification
criteria are restated per branch.

## 3. Mechanism

### 3.1 Pivot discovery (exact layer; deterministic, no tuning)

Input: the enumerated solution set `S = {y_0, …, y_{k-1}}` of encoded
extension cochains (already produced by the existing extension solver).

- Disputed set `D` = coordinates on which not all members of `S` agree.
- A **pivot set** `P ⊆ D` is minimal such that the projection `y ↦ y|_P` is
  injective on `S`. For `k = 2` any single disputed coordinate suffices;
  the rule is: choose the **lowest coordinate in canonical
  `core.coordinate_ids` order**. Deterministic, preregistrable, no scoring.
- Condition `C` = "pivot coordinate has value 1" (equivalently, the disputed
  identity atom holds, e.g. `a9 ↔ b13` in rule_7). Each branch `b` is one
  member of `S` restricted through its pivot values.

Growth/parsimony policy ("invent only if required"):

- Invent conditions iff `|S| > 1`; number of bits = `⌈log₂|S|⌉`.
- Hard cap: 3 bits (8 branches) per world. Overflow ⇒ report
  `AMBIGUITY_OVERFLOW` as an explicit reported failure; never grow past the
  cap. (G6 data: all observed worlds need 0 or 1 bit.)
- Conditions are **scope-local**: each condition records the coordinate set
  it pivots. Joint branches are materialized only for conditions with
  overlapping scopes; independent conditions keep independent branch pairs.

### 3.2 Conditioned fields (T5 layer)

The T5 field is a Dirichlet solve with pinned boundary values. Conditioning
uses the same machinery with no new solver:

- For branch `b`, move the pivot coordinates (full disputed scope of the
  condition) from `interior_indices` to `boundary_indices`, pinned to
  `y_b`'s values, and re-solve.
- Consistency: both extensions already agree with the original boundary
  (`boundary_mismatch = 0` in all 44 worlds), so each branch system remains
  exactly consistent with its own cochain ⇒ per-branch
  `boundary_mismatch = 0` is preserved by construction.
- Bound improvement is *provable*: enlarging the Dirichlet boundary shrinks
  the interior, and λ_min of the Dirichlet Laplacian is monotone under
  domain restriction, so `κ_δ(branch) ≤ κ_δ(shared)`. Conditioning can only
  tighten the spectral constant.
- Expected behavior (from the rule_3 evidence): each conditioned field
  snaps into its branch's valley; hedging disappears because the solve is
  no longer interrogated about a disjunction.

### 3.3 Localized decode contracts (T6 layer)

Independent of conditioning, replace the whole-cochain `decode_identity`
readout in the *separation role* with per-coordinate witnesses:

- New operation `decode_identity_at(c)` for each disputed coordinate `c`:
  exact output = the single cochain entry; enriched output = the single
  field value; output type is a 1-dimensional carrier with sup norm.
- Leaf/defect budget = a certified **per-coordinate** field error bound.
  Conservative v1: the interior Dirichlet residual bound restricted to `c`
  (any sound localization ≤ global bound is acceptable; the global L2 bound
  remains the fallback and upper envelope).
- The whole-cochain `decode_identity` contract is retained unchanged for
  every other role, so unambiguous worlds are bitwise unaffected in T5 and
  in all non-separation certificates.

### 3.4 New T6 separation criterion (branch-conditional)

For a world with branches `b_0, b_1` (per condition):

- **(a) Branch decisiveness.** For each branch `b_i`, the conditioned field
  must separate `y_i` from the sibling `y_j` at some pivot-scope witness:
  `γ_local = 1.0 > budget_i(c) + budget_j(c)` with localized budgets, i.e.
  each side certified below 0.5 at that coordinate.
- **(b) Hedge localization.** The *unconditioned* shared field's per-
  coordinate error to the branch envelope must be small away from the
  disputed scope (threshold preregistered; G6 data shows ~0.02 mean
  off-scope). This certifies the hedge is *located exactly at the declared
  ambiguity* — the field correctly reports the fork rather than being
  globally sloppy.
- Unambiguous worlds keep the existing criterion, now evaluated with
  localized witnesses as well; `INSUFFICIENT_BEHAVIORS` remains explicitly
  labeled vacuous and is never cited as capacity evidence.
- Status vocabulary gains `SEPARATING_CONDITIONAL` and
  `AMBIGUITY_OVERFLOW`.

### 3.5 Conditional commitments (T7 layer)

Extend `CommitmentOutcome` with `COMMIT_CONDITIONAL`:

- Carried on the ledger with: condition id, pivot atom, per-branch
  committed values, and the branch-conditional T6 certificate ids.
- Permitted only when both branch certificates in 3.4(a) hold; otherwise
  the existing `ABSTAIN` applies unchanged.
- **Discharge rule:** a later observation that fixes the pivot atom
  resolves the condition; the ledger appends a discharge event, the losing
  branch is pruned, and the surviving branch's commitments become plain
  `COMMIT` entries. Growth and resolution are symmetric; replay must
  reproduce both directions.

### 3.6 Accuracy phase scoring of conditional answers

The sealed evaluation key (reconstructed only after the global T7 barrier,
as in G6) resolves every condition to its true branch:

- A conditional answer scores as the answer of the **true branch**.
- False-positive accounting: a `COMMIT_CONDITIONAL` is a false positive iff
  the true branch's committed value is wrong. Hedging across branches is
  never scored as correct by itself — credit flows only through the branch
  the key selects.

## 4. Governance

- The G6 block is immutable and is **not** amended; its `BUDGET_CONSUMED`
  results remain the preregistered finding that motivated this design.
- G7 is a **new study manifest** (`graphlog-certified-g7`), fresh output
  root `results/graphlog-certified/g7`, same G0–G5 freeze commit/tree, same
  44-world cohort and paired draws, `analysis_order` unchanged
  (`structural, T5, T6, T7_safety, accuracy`).
- A new validation-amendment chain (same schema,
  `graphlog-certified-g6-validation-amendment/v1` successor) pins the
  implementation files, executor, and tests; execution stays disabled until
  the review record is complete, mirroring the G6 process. `change_scope`
  is `criterion_extension_reused_draws_disclosed` (the exact string the
  loader validates) — the T6 criterion changes, so this cannot ride the
  G6 chain as implementation-only.
- No G6 draws, scores, or evaluation keys are reused for development;
  smoke tests use the non-preregistered rule_20 seed-0 world as before.

## 5. Acceptance rules (sketch, to be frozen in the manifest)

- `certificate_soundness`: as in G6, plus every `COMMIT_CONDITIONAL`
  carries valid branch certificates and a replayable discharge rule; zero
  evaluation-confirmed false-positive commits, conditional included.
- `conditional_separation`: rule_2, rule_3, rule_7 each reach
  `SEPARATING_CONDITIONAL` (this is the headline hypothesis of G7).
- `no_regression`: all 41 previously-vacuous worlds retain their G6 phase
  outcomes; structural/T5 artifacts for them are digest-identical where the
  implementation is untouched.
- `hedge_localization`: 3.4(b) holds in all three ambiguous worlds.
- `primary_usefulness`: unchanged macro-mean comparison, with conditional
  answers scored per 3.6.

## 6. Verification plan before enabling execution

- Unit tests: pivot discovery (uniqueness, determinism, overflow cap);
  conditioned Dirichlet consistency (`boundary_mismatch = 0` per branch);
  λ_min monotonicity check; localized budget soundness
  (per-coordinate ≤ global); ledger replay including discharge.
- Property test: for synthetic worlds with a planted `k`-fold ambiguity,
  `⌈log₂ k⌉` conditions are invented and branch answers reproduce all `k`
  exact solutions.
- Dry run on rule_20 seed 0 (unambiguous: must be bitwise-stable) and on a
  synthetic ambiguous world (must reach `SEPARATING_CONDITIONAL`).
- Full suite green; then author manifest + amendment, review, flip
  `execution.enabled`, single preregistered run.

## 7. Implementation staged (2026-07-21)

The concrete artifacts now exist, all behind the disabled base amendment:

- `src/relweblearner/bench/graphlog_g7_conditional.py` — pivot discovery
  (canonical greedy, 3-bit cap), conditioned Dirichlet branches via
  `BoundarySpec` augmentation into the pinned T5 solver, localized
  Green's-row error bounds, branch-conditional separation certificate,
  hedge localization.
- `src/relweblearner/bench/graphlog_g7.py` — G7 control harness: manifest
  and amendment loaders (new schemas, extended acceptance-rule set,
  draw-provenance disclosure replacing the virginity proof), preflight,
  and the receipt/index-validated `execute_study`.
- `src/relweblearner/bench/graphlog_g7_executor.py` — phase adapter:
  structural/T5 delegate verbatim to the pinned G6 executor (bitwise
  no-regression by construction); T6 reproduces the pinned base body then
  adds the conditional layer; T7 and accuracy delegate and append the
  conditional-commitment and evaluation-join overlay artifacts.
- `results/graphlog-certified/g7-validation-manifest.json` — manifest id
  `sha256:02b479ab…`; same cohort, seeds, and freeze as G6; adds
  `draw_provenance` (G6 outcomes observed, post-hoc analysis disclosed),
  `conditional_protocol`, and the three new acceptance rules.
- `results/graphlog-certified/g7-validation-amendment.json` — base
  amendment `sha256:137d8c4b…`, `execution.enabled: false`, empty freeze
  commit by design; an enabling amendment-2 must pin a real commit after
  review, mirroring the G6 three-step chain.
- `tests/test_graphlog_g7.py` — 11 tests: discovery
  (unique/twofold/multibit/overflow/determinism), conditioned-branch
  pinning and spectral non-loosening, localized-bound soundness plus an
  end-to-end certified separation on a synthetic chain, pinned-only
  separation, hedge-localization threshold, witness interiority guard,
  manifest draw-reuse and disclosure, disabled-execution gate, and G7/G6
  receipt-schema separation.

Refinements made during implementation, superseding the sketch text above:

1. **Conditional commitments are an overlay, not an enum change** (§3.5):
   `certification/t7.py` is frozen G0–G5 source, so `COMMIT_CONDITIONAL`
   exists only in the G7 overlay artifacts
   (`g7-conditional-commitments.json`), which reference the base T7
   decisions they conditionally refine.  The certified ledger vocabulary
   is untouched.
2. **Only pivot bits are pinned; other disputed coordinates stay interior**
   (§3.2/§3.4): the conditioned solve must *propagate* the hypothesis to
   the non-pivot disputed coordinates, which is what branch decisiveness
   then certifies at localized interior witnesses.  A pair differing only
   at pinned coordinates separates by construction (`witness_kind:
   pinned`).
3. **No smoke run on the ambiguous preregistered worlds**: exercising the
   conditional certificate on rule_2/3/7's sealed state would observe the
   G7 headline outcome before preregistration.  The conditional path is
   validated on synthetic systems only; the unambiguous paths reuse the
   pinned G6 computation.  This is deliberate and should be preserved in
   review.

Known environmental note: the pinned
`test_graphlog_g6.py::test_manifest_load_is_literal_complete_and_does_not_create_output`
now fails because the sealed `g6` output block exists; the test predates
execution and its file hash is frozen by the G6 amendment, so it cannot be
amended.  Full suite: 485 passed, 1 skipped, plus that one pre-existing
failure.

Path to execution: review the three modules and this plan → commit →
author enabling amendment-2 with the real freeze commit, executor
`src/relweblearner/bench/graphlog_g7_executor.py` /
`execute_phase`, and a completed review record → single preregistered run
into `results/graphlog-certified/g7`.

## 8. Open questions

1. Exact form of the localized per-coordinate bound (interior residual
   restriction vs. discrete Green's-function column bound); v1 may ship
   with the conservative choice and record both.
2. Whether 3.4(b)'s off-scope threshold should be absolute (e.g. 0.25) or
   quantile-based; must be fixed before preregistration either way.
3. Whether `T7_safety` needs a distinct exclusion rule for conditions whose
   pivot atom is itself an anchor (should be impossible — anchors are
   observed — but needs a test, not an assumption).
4. Presentation surface: how conditional answers appear in downstream
   replacement predictions (`A if a9↔b13 else B`) without perturbing the
   frozen prediction-format contract — likely a parallel artifact rather
   than a change to the existing one.
