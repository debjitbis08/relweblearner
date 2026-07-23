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
(the G7-autopsy pattern, which the bound-gap analysis validated).

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
     naive baseline — majority class, "crossed iff branch ≠ 0",
     "crossed iff non-pivot" — by a stated δ; (b) its generalization
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
2. **Accuracy floor and its allowance.** The *mechanism* is now fixed
   in §5.4 (naive-baseline dominance, cross-seed-family anchoring,
   sample-size-aware pass rule); open is only the δ over the best
   naive baseline. Note the baselines are strong: "crossed iff
   branch ≠ 0" already captures 18 of 20 fresh-seed positives, so a
   predictor that cannot beat it is not a mechanism account.
3. **Verification part: include or skip?** Include iff the predictor
   precomputes cheaply on sealed draws; skipping loses the
   replication anchor, but a predictor too expensive to precompute
   would already violate the §8.1 budget.
4. **Non-vacuity minimum.** Observed base rates: 20 unambiguous
   crossing records under the G8 seed, 6 under the G7 seed — so a
   minimum of 8 would be failed by one of the only two seeds ever
   observed, making informativeness the coin flip the rationale is
   supposed to avoid. Default: minimum **5** unambiguous crossing
   records (both observed seeds pass) alongside the ≥2
   conditioned-worlds floor, with the final number fixed at
   authoring by a written rationale that confronts this arithmetic
   explicitly.
5. **Cohort.** The 44 frozen worlds again, or the long-deferred
   rule-generalization extension (G8 §8.2)? Extending the cohort in
   the same block that tests the predictor conflates two
   generalizations; the conservative default is same-cohort G9 with
   rule extension deferred to G10.
