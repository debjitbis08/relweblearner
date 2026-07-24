# G9 plan: the mechanism of anti-propagation (draft)

Status: DRAFT for review — not preregistered, no manifest authored, no
execution enabled, Phase A not yet run. Successor to the sealed G8
blocks; the G8 results stand unchanged (§9 of
`docs/g8-interior-decisiveness-plan.md`).

## 1. Motivation — what the sealed G8 measurement left unexplained

G8 Part II measured, without predicting, two phenomena that its own
discipline flagged as open (plan §9.5):

1. **Anti-propagation recurred**: 20 of 71 evaluated branch–coordinate
   records crossed — a conditioned branch's field settling strictly
   closer to an opposing branch's cochain value than to its own — in
   five of the six conditioned worlds (19 unique coordinates; per-world
   record counts 0, 2, 5, 5, 4, 4). The sealed G7 draws show the same
   phenomenon: 20 evaluated records, 6 crossed (2 per conditioned
   world, the counts pinned as Part I expectations). Total sealed
   population across both seed families: **91 evaluated records, 26
   crossings**.
2. **Certifying margins were knife-edge in exactly three worlds**:
   rule_8 +0.037, rule_9 +0.088, rule_12 +0.011.

These two phenomena are linked by an instrument identity plus an
observed regularity, and the two must not be conflated. The identity:
under the tight bound the certified per-coordinate bound equals the
true error `e_c = |row_c(H_uu⁻¹)·r|` to solver tolerance, so at the
selected witness, up to ~2·10⁻⁶ float slack,

```
remaining_margin(c) = γ_c − e_L(c) − e_R(c)
```

— a thin margin *is* a large summed true error. The relation to
crossing, however, is directional and strictly weaker: a crossing is
a **signed** excursion — the field strictly past the own/opposing
midpoint *toward* the nearest opposing value (the pinned
`anti_propagation` definition) — so a large unsigned error on the
away side is not a crossing, a thin margin can arise from two
sub-midpoint hedges with no crossing at all, and a crossing does not
force a thin margin (sealed counterexample: rule_6 pair 0–2 certifies
at `X:11:14` with fat margin +0.171 while branch 2 has crossed there,
depth 0.540). What the sealed data show is an **observed
regularity**, not an identity: every thin-margin world certified at a
witness that is itself a crossing coordinate for the counterpart
branch — rule_8 at `X:6:5` (branch 1 field +0.8995 against own
cochain 0), rule_9 at `X:8:9` (+0.8182 against 0), rule_12 at
`X:13:3` (+0.6720 against 0) — while every fat-margin witness
(0.171–0.699) has at most one crossing in its pair. The G8 criterion
is honest but weak here: it certifies that the two branch fields
provably *differ* at the witness, not that either field decodes to
its own branch's value. rule_8's certificate is the sharpest example:
interior separation holds at `X:6:5` precisely because branch 0's
field sits within 0.0634 of its cochain while branch 1's field has
crossed almost all the way to branch 0's value — distinguishable, but
only one of the two fields is decodable there.

Two further measured facts sharpen the question:

3. **Crossing depth is a spread, not modes.** The 20 fresh-draw
   crossing depths `|field_c − own_c|` range 0.519–1.014 with no
   gap larger than 0.063 anywhere in the sorted list (max gap
   0.0622): shallow
   hedge-leans just past the midpoint, deep wrong-commitments near
   the full opposing value, and everything between. A mechanism
   story must predict a continuous depth, or explicitly scope
   itself to the crossing bit alone; it may not assume distinct
   regimes.
4. **Crossings are branch-asymmetric.** 18 of 20 fresh-draw records
   sit in branches other than branch 0 (per-branch histogram
   2/15/3). Whether branch index is mechanistically meaningful
   (e.g. correlates with distance from the unconditioned solution)
   or an enumeration artifact of pivot discovery is itself an open
   question Phase A must answer before any asymmetry claim is
   preregistered.

## 2. The question

**What determines, from the operator and the branch cochain alone,
where a conditioned branch's true Dirichlet solution commits to the
opposing branch's value?**

This is a mechanism question, not an existence question — G8 already
established existence prospectively. Because the field solve is
deterministic given the draw, the crossing set is *computable* in
principle from `(H, boundary, cochain)`; the scientific content of G9
is therefore a **compressed structural account**: a predictor built
from local/structural quantities, fixed before fresh draws exist, that
classifies fresh crossing records well. "We can recompute the solve"
predicts everything and explains nothing; the preregistered predictor
must be strictly weaker than the solve, stated as an explicit formula
over declared inputs, so that its success is informative and its
failure is genuine.

The natural starting decomposition is exact: `e_c = −row_c(H_uu⁻¹)·r`
with `r = H_uu y_u + H_ub b` supported where the branch's own cochain
is non-harmonic (the disputed frontier). Attribution of `e_c` over
residual sites — which frontier mass, weighted by the Green's row,
pulls coordinate `c` across — is Phase A's first task, and any
candidate predictor (e.g. a Green-weighted own-side/opposing-side mass
ratio with a fixed threshold, or a locality-radius claim) must be
derived from it rather than fitted.

## 3. Design principle — inherit the G8 split, close the loop first

The G8 lesson applies verbatim: any hypothesis formed by looking at
sealed data has its outcome on those draws already computed, so the
plan splits:

- **Phase A — post-hoc mechanistic analysis** (sealed G7 + G8 blocks,
  read-only, disclosed): hypothesis generation. Its deliverables and
  its analysis script are sealed before Phase B is authored, so the
  analysis loop G8 §7.2 closed stays closed.
- **Phase B — preregistered test** (fresh beacon-seeded draws): the
  predictor, its threshold, and its evaluation script are all frozen
  pre-pulse; outcomes unobserved until the pre-committed report runs.

A Part-I-style verification block (predictor outcome precomputed on
the sealed draws, disclosed as such) is included iff Phase A's
predictor is cheap to precompute — expected yes, since it must be
strictly weaker than the solve. It carries the same
replication-only/zero-discovery declaration as G8 Part I.

## 4. Phase A — post-hoc analysis of the sealed blocks (read-only)

Inputs: the sealed G8 Part II block (71 evaluated records: 20
crossing, 51 non-crossing, six conditioned worlds), the sealed G8
Part I / G7 blocks (20 evaluated records: 6 crossing, 14
non-crossing), and the pinned operators and cochains reachable from
them — 91 evaluated records, 26 crossings in all. No new draws, no
new solves beyond reconstruction of sealed state with pinned code
and the §4.1 attribution's Green-row solves (ground truth is
analysis-side; the budget constrains only the predictor). The
G7-autopsy pattern, which the bound-gap analysis validated.

Deliverables, in order:

1. **Exact attribution table**: for every sealed crossing and
   non-crossing record, the decomposition of `e_c` over residual sites
   `e_c = −Σ_j G_cj r_j`, verified to reproduce the sealed
   `field_value − own_value` to solver tolerance (faithfulness check
   at full precision, the corrected bound-gap-script standard: full
   comparison, not spot checks).
2. **A candidate structural predictor** of `crossed_to_opposing`,
   with: declared inputs (a subset of `(H, boundary, cochain)`
   strictly weaker than the full solve, inside the complexity budget
   preregistered in §8.1 — fixed in this plan up to the §8.1
   confirmation, never drawn in Phase A), an explicit formula, and a
   fixed decision threshold.
   Its confusion matrix on all 91 sealed records is reported in
   full, including performance as a function of crossing depth
   (§1.3, a continuous covariate, not modes), per-branch performance
   (§1.4), and separately for the pivot-coordinate records that can
   never cross (§5's claim-4 population excludes them; both
   populations are reported). Phase A must also run the
   solve-equivalence diagnostic of §8.1: a predictor whose score
   reproduces the true signed error too faithfully is rejected as
   the solve in disguise, however well it classifies.
3. **A branch-asymmetry adjudication**: whether branch index is
   enumeration artifact or mechanism (e.g. by permuting enumeration
   order in reconstruction), settled before Phase B may mention
   asymmetry at all.
4. **The decode-decisiveness vocabulary** (§6) applied retroactively
   to the sealed certificates as a *report* (not a re-certification):
   which sealed interior witnesses were decode-decisive for both
   branches, one, or neither.
5. **Adversarial review** of 1–4 (the referee pattern used for the
   bound-gap analysis and the G8 §9 write-up), then the Phase A
   script sealed by commit, its digest quoted in the Phase B
   manifest.

Phase A makes no claims. Its report is hypothesis-generation
disclosure, and every number in it is already determined by sealed
data.

## 5. Phase B — preregistered test on fresh draws

Same cohort (the 44 frozen worlds), fresh master seed via the beacon
ceremony (§7). Structure mirrors G8 Part II: instrument claims that
are theorems, empirical claims that can genuinely fail, everything
else measured-only.

- **Instrument claims (theorems up to disclosed float slack):**
  1. *Crossing-set reproducibility*: the crossing records the harness
     emits equal the records recomputed from `(H, boundary, cochain)`
     by the pre-committed report script, exactly (ambiguous-band
     records per claim 3 compared as `AMBIGUOUS_CROSSING`, not as a
     bit).
  2. *Margin–error identity*: `|remaining_margin − (γ − tight_L −
     tight_R)| ≤ float slack` at every interior witness the report
     script evaluates — the script recomputes the tight bounds for
     **all** evaluated witnesses of every pair (the certificate
     records the tuple only for the selected best witness, so the
     claim is checked by recomputation, and the evaluation procedure
     is the pre-committed script itself, not the certificate alone).
  3. *Crossing guard band*: every record counted as crossed has
     midpoint distance `|field_c − (own_c + nearest_opposing_c)/2|`
     greater than the disclosed solver ceiling (2·10⁻⁶ + slacks; one
     field is involved so 1·10⁻⁶ would suffice — the 2× is stated
     conservatism). On the frozen cohort all cochain values are
     binary so this midpoint is 0.5; the invariant form is
     preregistered so the claim survives any future cohort. The band
     is computed by the G9 overlay/report layer — the pinned
     `anti_propagation` bit is unchanged — and records inside the
     band are reported `AMBIGUOUS_CROSSING`, a reported outcome, not
     a defect. Ambiguous records are excluded from claim 4's ground
     truth **and** from the non-vacuity count, and reported
     separately. (Fresh draws may sit arbitrarily close to the
     midpoint; the sealed minimum distance was 0.019, a
     draw-specific fact.)
- **Empirical claims (preregistered, falsifiable):**
  4. *Predictor accuracy*: the Phase A predictor, frozen with its
     threshold, classifies fresh-draw non-pivot records (pivot
     records can never cross and are excluded as free negatives)
     with balanced accuracy ≥ the preregistered floor. The floor is
     fixed in the sealed Phase A report, before any Phase B seed
     exists, and must satisfy all of: (a) it exceeds every named
     naive baseline by a stated δ, each evaluated on its stated
     population — majority class and "crossed iff branch ≠ 0" on
     the non-pivot (claim-4) population, "crossed iff non-pivot" on
     the full population (the only population where it is
     non-degenerate); (b) its generalization
     allowance is anchored by cross-seed-family validation (fit
     interpretation on the G8-seed records, evaluate on the G7-seed
     records, and leave-one-world-out), not chosen freely against
     the in-sample number; (c) the pass rule is sample-size aware —
     stated as a function of the realized positive count (e.g. an
     exact binomial lower-confidence-bound form), so a low-base-rate
     block cannot pass or fail on binomial noise.
  5. *Predictor calibration direction* (only if Phase A licenses it):
     predicted crossing depth rank-correlates with observed depth at
     ≥ a preregistered level. The licensing criterion is written:
     Phase A must state, in the sealed report, whether the predictor
     emits a continuous score, the sealed-data rank correlation that
     justifies inclusion, and the preregistered level — or state
     that the claim is dropped. Either way the fork closes,
     verifiably, before Phase B authoring; never invented post hoc.
- **Non-vacuity**: fewer than a preregistered minimum of
  unambiguous crossing records (§8.4) or fewer than 2 conditioned
  worlds ⇒ the block is *empirically uninformative for the mechanism
  claim*, reported as such, no claim of any strength made.
- **Explicitly NOT predicted**: number of ambiguous worlds, number or
  depth distribution of crossings, per-world outcomes, branch
  asymmetry (unless Phase A adjudicated it mechanistic and a claim
  was preregistered), margins, or decode-decisiveness counts. All are
  measured outcomes under the G8 secondary-report discipline.
- **Relationship to G8 claims**: G8's four claims are not re-asserted
  and their machinery is reused pinned. The failure paths split by
  claim kind: a breach of a G8 *instrument* claim (soundness,
  tightness) surfacing in a G9 run is an implementation defect and
  blocks release. A failure of a G8 *empirical* regularity (hedge
  localization, conditions-iff-ambiguous) on fresh G9 draws is a
  scientific finding: it is reported as a measured outcome, it may
  block interpretation of G9's own claims where they depend on it,
  and it never blocks release of the sealed evidence — suppressing a
  negative result is the one outcome the discipline exists to
  prevent. G9's success criteria are 1–5 above only.

## 6. Vocabulary upgrade — decisiveness vs distinguishability

G9 adds a reported (not certified-success) refinement of the G8
overlay vocabulary, computed per interior witness. The decode
threshold is fixed **here**, not in Phase A, so its retroactive
application to sealed certificates (§4.4) involves no choice made
while looking at sealed fields: a branch is *decodable* at a witness
iff `|field_c − own_c| ≤ 0.1` — the frozen G7 hedge-localization
threshold, reused rather than minted, so no new constant is tuned.

- `DECODE_DECISIVE_BOTH`: each branch's field within 0.1 of its own
  cochain value at the witness.
- `DECODE_DECISIVE_ONE`: exactly one branch decodable there (the
  rule_8 `X:6:5` situation).
- `DISTINGUISHABLE_ONLY`: margin positive but neither field decodes.

`INTERIOR_SEPARATING` keeps its G8 meaning (distinguishability); the
new strings are report fields, never acceptance criteria, so G8
comparability is preserved and no success vocabulary is inflated.

## 7. Governance sketch

Inherits the full G8 chain: two-manifest structure (if the
verification part is included), disabled→enabling amendment chains
with pinned adapters, repository preflight, refuse-resume with the
amendment-disposition pattern, atomic staging/rename, pre-committed
report script as mandatory first read, archive to `/data`
destination-verified with symlink replacement, and the beacon seed
ceremony — with one upgrade forced by the G8 §9 referee: the
pre-pulse commitment commit (seed rule + report script + frozen
predictor) must be **confirmed on the public remote before the pulse
time**, so the pre-pulse ordering has a public anchor rather than
local-evidence-only. The rule is deterministic, with no discretionary
branch: if the push is not confirmed (the commit fetchable from the
public remote) before the committed pulse time T, the T-pulse is
**burned unexpanded** — a new future time T′ is committed and
confirmed-pushed before T′, disclosed by amendment; proceeding on
local evidence after a failed push is not an option, because a
post-pulse choice between proceeding and reminting is itself a
shopping-shaped decision. The enabling amendment records the
remote's own **ordering** evidence — the hosting service's
push-event record or API response for that sha, or a third-party
timestamp of it — not a self-reported push time and not mere commit
presence, which a later fetch cannot place before the pulse.
History is never rewritten (the chain pins commits by sha).

## 8. Open questions (to resolve before Phase B authoring)

1. **Predictor input boundary — the complexity budget is fixed here,
   pending only the numeric review at authoring.** A syntactic ban
   ("no linear solves against `H_uu`") is circumventable: truncated
   Neumann/Jacobi series, Chebyshev filters, or CG iterations
   converge to `H_uu⁻¹r`, and with unbounded order the predictor
   *is* the solve and claim 4 passes vacuously. Note a *locality*
   budget cannot do this work: `H = δᵀδ` couples every coordinate
   pair co-appearing in a residual block, and the measured sealed
   `H_uu` sparsity graphs are unions of near-cliques — max degree
   24–29, exactly 4 connected components per conditioned world
   (sizes 9–30), graph diameter 1–2 — so any hop-radius constraint
   reaches an entire component immediately and excludes nothing
   (the 14×14–16×16 vertex grids' 26–30-edge diameters are a
   property of the wrong graph). The budget is therefore
   **spectral, not local**: the predictor may use matrix
   polynomials in `H_uu` of degree ≤ k with **k = 2 or 3**, plus
   global scalars already pinned in certificates (γ, the branch
   spectral lower bounds — nothing else is pinned per-certificate;
   condition numbers live only in the bound-gap analysis prose).
   The degree cap's justification is an empirical-spectrum
   argument, not a certificate: the pinned branch spectral lower
   bounds (2·10⁻⁴–6·10⁻⁴) are *lower* bounds on λ_min, which alone
   bound the condition number only from *above*, so Phase A must
   measure and report the actual spectra (λ_min/λ_max per
   conditioned system, as the bound-gap analysis measured condition
   numbers on the G7 systems); under the measured spectra a
   degree-k polynomial is far from `H_uu⁻¹` in the Chebyshev worst
   case over the spectral interval. The worst case is also not the
   instance: a degree-k polynomial can still reproduce `H_uu⁻¹r`
   for a *specific* residual whose spectral content concentrates on
   well-approximated eigenvalues. For both reasons — no structural
   separation of the predictor's support from the solve's, and no
   instance-level guarantee from the worst-case bound — the
   **solve-equivalence diagnostic is co-equal and load-bearing,
   not a backstop**: if the predictor's continuous score reproduces
   the true signed error across the 91 sealed records with rank
   correlation above 0.99, it is rejected as the solve in disguise
   regardless of classification accuracy, and Phase A must report
   the diagnostic either way. Open only: the exact degree (2 vs 3) and the 0.99
   ceiling, to be confirmed with a written rationale before Phase A
   runs — never widened after.

   **Numeric confirmation (2026-07-24, closes this question):**

   - **Degree k = 3**, and the admitted polynomial class is stated
     precisely: `p(H_uu)` with `deg p ≤ 3`, and the
     diagonally-preconditioned family `q(D⁻¹H_uu)·D⁻¹` with
     `deg q ≤ 3` where `D = diag(H_uu)` — the standard
     polynomial-method class (Neumann/Jacobi iterates and truncated
     Chebyshev filters live here), admitted because `D` is
     per-coordinate data, not solve output. Coefficients must be
     fixed constants, pinned certificate scalars, or explicitly
     declared closed-form aggregates of 1-hop operator data
     (diagonals, row sums — e.g. Gershgorin bounds) — never fitted
     quantities, never functions of solve output. (The 1-hop
     aggregate clause was added pre-seal on the §4.5 referee's
     ruling: the class already admits `D` inside the operator, a
     row-sum scalar carries strictly less information than `D`, and
     the degree cap and in-interval worst-case floor are unchanged —
     letter aligned with spirit, no material widening.) Rationale: the
     support argument is dead (near-clique components — degree 1
     already reaches everything), so degree matters only spectrally.
     Under the measured G7-system condition numbers 86–348
     (bound-gap analysis), the best degree-3 approximation to `λ⁻¹`
     on the spectral interval retains worst-case relative error at
     least `((√κ−1)/(√κ+1))⁴ ≈ 0.42–0.65` (the exact Chebyshev
     min-max is larger, ≈ 0.71–0.91) — even the full budget cannot
     mimic the solve in the worst case *for the raw class*. Those
     condition numbers do not govern the diagonally-preconditioned
     class, whose operative spectrum is that of
     `D^(−1/2)·H_uu·D^(−1/2)`; Phase A must therefore measure and
     report, per conditioned system, both the raw spectrum
     (λ_min/λ_max) and the preconditioned spectrum (together with
     the spectral radius of `I − D⁻¹H_uu`, which also reveals
     whether the degree-3 Jacobi iterate smooths or diverges), and
     the worst-case argument stands or falls per class on those
     measurements — the co-equal diagnostic carries the
     instance-level guarantee either way. **Composition closure:**
     admitted operators may not be chained — the end-to-end linear
     map from the declared data vectors (residual, cochain,
     indicators) to every budgeted intermediate must have total
     degree ≤ 3; applying one admitted operator to another's output
     is outside the budget (iterated chaining is the solve). k = 2
     would forfeit the third moment (three independent smoothing
     steps is the minimum a mechanism formula distinguishing
     "shallow local pull" from "component-wide consensus" plausibly
     needs) while buying no honesty the co-equal diagnostic does
     not already enforce instance-wise.
   - **Ceiling 0.99**, Spearman rank correlation between the
     predictor's **finest-grained budgeted linear estimate of the
     signed error** — the raw polynomial output feeding the
     decision rule, before any thresholding, quantization, or
     rank-coarsening (a coarsened score evading the ceiling while
     classifying at solve grade is exactly the smuggling this
     pinning forbids) — and the true signed error, computed over
     every sealed record where the budgeted estimate is defined
     (non-pivot records; pivot coordinates are Dirichlet-pinned in
     the branch systems, so no interior estimate exists there —
     this scopes the "91 sealed records" phrase above to the
     estimable subpopulation, consistently with claim 4's
     population) and reported pooled and per seed family.
     Rationale for the line: a disguised solve reproduces `e_c` to
     solver tolerance (~10⁻⁶ absolute against sealed depths ≥ 0.5),
     landing at rank correlation 1 − O(float) > 0.999; the
     strongest honest compressed mechanism we would credit explains
     sign and coarse magnitude (plausibly ρ ≈ 0.7–0.9). 0.99 sits
     above any creditable mechanism and below the solve's float
     band, an order of magnitude of disagreement on each side.
   - Both numbers are now closed and may narrow but never widen.
2. **Accuracy floor and its allowance.** The *mechanism* is now fixed
   in §5.4 (naive-baseline dominance, cross-seed-family anchoring,
   sample-size-aware pass rule); open is only the δ over the best
   naive baseline. Note the baselines are strong: "crossed iff
   branch ≠ 0" already captures 18 of 20 fresh-seed positives, so a
   predictor that cannot beat it is not a mechanism account.
   **RESOLVED 2026-07-24 by the sealed Phase A report §6: δ = 0.02,
   floor F = 0.776, pass rule = mean of one-sided Jeffreys lower
   bounds (the 0.20 quantile of Beta(s+½, f+½)) ≥ F.**
3. **Verification part: include or skip?** Include iff the predictor
   precomputes cheaply on sealed draws; skipping loses the
   replication anchor, but a predictor too expensive to precompute
   would already violate the §8.1 budget. **RESOLVED 2026-07-24 —
   included, realized without a second execution block: the
   pre-committed Phase B report script carries a `verification` mode
   that reads the ALREADY-SEALED G8 Part II block (outcomes
   precomputed by Phase A, disclosed as such), checks instrument
   claims 1–3 on it, and verifies the pinned predictor module
   reproduces Phase A round 2's per-record estimates bit-for-bit.
   Full replication anchor, no new run; it executes after the
   commitment commit and before the fresh block's first read.**
4. **Non-vacuity minimum.** Observed base rates: 20 unambiguous
   crossing records under the G8 seed, 6 under the G7 seed — so a
   minimum of 8 would be failed by one of the only two seeds ever
   observed, making informativeness the coin flip the rationale is
   supposed to avoid. Default: minimum **5** unambiguous crossing
   records (both observed seeds pass) alongside the ≥2
   conditioned-worlds floor, with the final number fixed at
   authoring by a written rationale that confronts this arithmetic
   explicitly. **RESOLVED 2026-07-24 by the sealed Phase A report
   §6: minimum 5 unambiguous crossing records, ≥2 conditioned
   worlds.**
5. **Cohort.** The 44 frozen worlds again, or the long-deferred
   rule-generalization extension (G8 §8.2)? Extending the cohort in
   the same block that tests the predictor conflates two
   generalizations; the conservative default is same-cohort G9 with
   rule extension deferred to G10. **RESOLVED 2026-07-24 — same
   44-world cohort; rule extension deferred to G10, as the
   conservative default argued.**
