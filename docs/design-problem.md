# The design problem — a precise statement of the math this project now needs

*Written 2026-07-12; **revision 2 same day, after external referee.** The
referee's corrections are accepted in full and worked in rather than
appended: the v1 text promoted the coherent-forgery exclusion to a
cohomological obstruction it never was, and the referee's decisive
question ("why exactly was the forgery excluded while the solo truth
remained provisional?") turned out to be answerable from the
implementation in one grep — see §2. v1 is preserved in git history
(eb96448). **Revision 3, 2026-07-14, after the round-2 referee report on
E2b** (docs/multiweb-overlap-forgery-referee-report.md; all seven points
accepted in full — response in
docs/multiweb-overlap-forgery-referee-response.md). The chief round-2
correction repeats rev 2's lesson one level down: the E2b detector reads
an ABSENT overlap edge in a finite sampled view as refutation, and that
reading is itself an epistemic policy — now named P2 (§6) rather than
smuggled as geometry, exactly as P1 was named in rev 2 — so E2b's result
is stated as a statistical disagreement separation, not yet a literal
Ext = ∅ instance of T2. rev 2 is preserved in git history. **Revision 4,
2026-07-15, after T1-T3 review,** adopts supported-candidate counting: E1/E2
are determined-as-solo in the scoped discrete model and refused by P1, while
imagined sampling alternatives move to T4. This document builds nothing. It
fixes the objects, states the
invariances and policies any designed structure must respect, translates
the empirical findings into boundary conditions, and lists the theorems
required for the structure to count as DESIGNED rather than found.*

## 1. The thesis being formalized

Thinking occurs as dynamics in opaque geometric webs. Concepts and
semantic knowledge are projections of stable structures within and between
those webs. Multiple webs arise as different views of one hidden world;
their combination — not any single web — is where understanding lives.

Three benches exist as the falsification harness for any candidate
formalization (all pre-registered, all with held-out results):
**bench-multiweb** (categorical knowledge, forgery + solo controls),
**multiweb-graphlog** (compositional thinking, split-brain measurement),
**graded-ensemble** (two-timescale attempt: guard passed, headline failed).

## 2. The settled question: why the forgery was actually excluded

The referee asked the decisive question, and the code answers it plainly:
`project()` in bench-multiweb emits exactly TWO states — corroborated
(concept) or not. The forged region and the solo-truth region both scored
corroboration 0 and landed in the SAME state. The distinction between
"excluded" and "provisional" existed only in the evaluation's gold labels.

So: **the forgery was rejected by absence of overlap support under a
closed-world projection policy, not by incompatibility.** No view ever
contradicted it; no view could — it was built from fresh, never
co-witnessed nodes, so it touches no overlap. E1 and E2 are geometrically
identical: both have the same unique supported solo reading in the scoped
discrete model, and P1 declines both because neither has cross-view support.
The multiplicity one may imagine — for example, that another view simply did
not sample a counterpart — is a hidden-world hypothesis for T4, not a T1-T3
extension. The bench's own honest-limit paragraph (P-D) already required the
same treatment before the v1 document forgot it. The v1 claim "forgery =
nonzero H¹" was wrong.

Two consequences, one of each kind:

- **A policy must be named, not smuggled.** The projection rule "only
  structure supported by ≥ 2 views commits" is an epistemic policy — the
  ensemble lift of the one-web system's k-witness commitment rule
  (commit_k = 2), not a fact of geometry. It goes into the framework as
  an explicit axiom (P1, §6) with the honest gloss: it rejects
  fabrications and unshared truths alike, by design.
- **Incompatibility detection exists in this project's data — elsewhere.**
  The destructive-interference gate (multiweb-graphlog bring-up) rejected
  confabulated identifications because the trial gluing produced
  CONTRADICTED triples on both sides — that is a genuine residual of an
  attempted extension. And bench v3's D2 loop lie was detected as
  holonomy — incompatibility inside one web. The obstruction machinery
  has empirical support; the coherent-forgery exclusion is just not an
  instance of it.
- **The decisive bench was missing; it has now been run — the separation
  holds, under a policy the run itself exposed.** An **overlap forgery** —
  liars wire a false pattern among CO-WITNESSED nodes, so view agreement is
  violated on the overlap itself — was pre-registered
  (docs/multiweb-overlap-forgery-plan.md) and run held-out (50 seeds,
  results/bench-multiweb-overlap). The false MERGE is separated from the
  fresh-node forgery as a different measured type in every seed: a
  cross-view disagreement residual of ≥ 2 contradicted backbone edges
  (min 5, and ≥ 5 per seed on correctly mapped direct anchors), while E1/E2
  have residual exactly 0 — they present no checkable edges at all. True
  regions are almost untouched (0.02 of instances falsely flagged; recall
  and purity identical to the unmodified benchmark on the same seeds). The
  policy attribution (plan §8a): **P1 alone would have COMMITTED the false
  merge in 41/50 seeds** and kept it provisional in 9 — the merged region's
  mapped image concentrates past CORR_THETA in one side's region of another
  view — so the detector is uniquely responsible for rejection in those 41
  seeds and necessary for complete rejection over the block; P1's
  fresh-node exclusion does not generalize to lies on the overlap. What the
  round-2 referee then correctly bounded: the detector reads an ABSENT
  backbone edge in another sampled view as a contradiction, and in a finite
  co-occurrence sample absence is non-observation, not negative evidence —
  that reading is itself an epistemic policy (**P2**, §6), and its false
  positives are exactly its sampling-variance cost (14 of the 15 collateral
  flags sit on correctly mapped direct anchors). The later P2 discharge
  (§6; docs/p2-discharge.md §13–§14) supplies that explicit semantics at
  the MEASURED tier for the declared E2b process, so E2b now stands as a
  reliable, typed, cross-view **disagreement separation** whose detector
  verdict reads as raw Ext = ∅ within that process. T2's remaining
  obligation is the exact proof over the chosen D1/D2. Two calibration
  lessons: gate the residual on a COUNT, not a dilution-prone
  weight ratio (ratio mean 0.49, straddling the naive 0.5 gate) — and the
  count is of edges, not independent witnesses (one mis-mapped node
  produced both counted contradictions in one collateral case; re-run
  obligation, plan §9).

## 3. The conjecture, v2 (broadened per referee)

> The correct framework is a **descent structure over the nerve of the
> view cover** — of which ordinary sheaves, category-valued sheaves,
> spans, and stacks are candidate instances — whose **linear shadow is a
> cellular sheaf** supporting harmonic dynamics.

With the model/data separation made explicit (Robinson): the sheaf-like
object models the VIEW SYSTEM — stalks are the *possible local states* at
a view or overlap, restriction/descent data say what views jointly
witness. An observed web is an **assignment** (a candidate local section)
to that model, not a stalk. "Global section" must also be disambiguated:
a compatible family of local assignments may represent one cross-view
concept instance, one complete interpretation, or a whole knowledge
state — T0 fixes which of these each layer uses.

Why possibly a stack rather than a sheaf of sets: the knowledge layer
must glue graphs/semicategories, identify structure only up to
automorphism (orphan merges, E3), and remember alternative identifications
— which a sheaf of sets forgets and descent/stack language is built for.
"Identity determined up to the automorphisms visible to the cover" is the
same lemma family as polysemy fission, run in reverse.

The composite picture:

    structured descent/stack --linearization--> cellular sheaf
                             --harmonic dynamics--> thinking field

Knowledge is the discrete compatible structure recovered through descent;
thinking is the evolving graded field used to find it.

## 4. Epistemic states are extension sets

For a local structure s, define Ext(s) = the set of global compatible
structures extending s. The three states, and the typed refusal they
induce:

| Ext(s) | state | system behaviour |
|---|---|---|
| empty | obstructed / incompatible | reject as inconsistent |
| singleton | determined by available views | commitment permitted (P1 still applies) |
| larger | underdetermined / provisional | refuse to commit |

This replaces v1's H¹ talk as the working language for T1–T3. Note
"unique extension" means uniquely determined BY THE VIEW MODEL — not true
of the external world; truth needs the identifiability theorem (T4) and
its assumptions. H¹ enters, if at all, only after the coefficient object
is constructed and the claim proved: until then E-type failures are
called **failure of compatible extension / failure of descent**. (For the
linear layer: a nonzero residual δx of an assignment is not yet a nonzero
H¹ class — cocycles and coboundaries first.)

## 5. Design decisions the framework must fix or expose

- **D1. Partiality.** Restriction/descent data are partial and must stay
  so. Candidates: relations/partial functions as the value category;
  overlap-restricted stalks; spans. First real decision; exactness
  properties differ.
- **D2. What stalks carry.** bench-multiweb: weighted graphs with their
  stable structure. GraphLog: composition-carrying objects
  (semicategories). The value category must make cross-web identity
  structure-preserving by construction — this is where the stack option
  becomes live.
- **D3. The enrichment is a choice to expose, not eliminate.** (Revised
  per referee — v1 overpromised.) Linearization cannot derive its own
  semantics: free vector spaces already choose additive superposition;
  max-plus needs tropical enrichment. The honest requirement: the
  invariances (§6), boundary conditions (§7) and soundness theorem (T6)
  must restrict the admissible enrichments enough that the surviving
  candidates — linear, tropical, probabilistic, set-valued — are
  FALSIFIABLE against each other. rule_20's collapse (E5) is then a
  selector experiment between enrichments, not a bug to patch — and it is
  now DIAGNOSED, with the causal structure measured by a committed 2⁴
  factorial after the E5 referee rejected a single-ladder decomposition
  as order-dependent (results/rule20-diagnosis/factorial.json). The
  order-independent Shapley allocation of the seed-0 tear: rule
  translation 0.183, removal of the 2 false hardening-gate commits 0.139,
  similarity exactness 0.021, rendering translation exactly 0 — dominated
  by a commit×translation INTERACTION (0.267: the false commits cost
  nothing at the frozen configuration and −0.298 once rules are
  translated). The selector datum is sharper than first stated: with
  rules translated and the false commits removed, the frozen SOFT
  similarity slightly exceeds the discrete ensemble (0.669 vs 0.659), and
  exactifying it away lands prediction-identical to discrete. So on this
  draw the graded similarity semantics are NOT what E5 selects against;
  the losses live in (i) the missing translation layer
  (bridge-at-derivation-time in place of translate-then-derive) and
  (ii) the weak hardening gate (a P1-family commit-policy failure) — and
  they compound. This is recovery under discrete exactification, not an
  exoneration of the two-timescale architecture, and it is scoped to
  rule_20's tearing draw. The E6 datum stands as corrected after its
  referee (results/rule27-diagnosis/graded-causal.json): identity
  exactness recovers nothing on rule_27 — the graded system there
  predominantly inherits the discrete seam catastrophe (956/1000
  predictions coincide; the 44 flipped episodes remain unattributed).
- **D4. Stable commitment, relative to the view model.** (Renamed per
  referee.) The needed theorem: the soft field lies near one exact
  compatible section and small perturbations do not change which — a
  stability statement. It cannot and does not establish truth; external
  soundness is T4's job under explicit coverage/independence assumptions.
  This bound replaces HARD_SIM = 0.5 or it does not exist.

## 6. Invariances and policies (separated, both explicit)

Invariances (facts the formalism must respect):

- **I1.** Within-web relabeling of opaque ids changes nothing.
- **I2.** Identity evidence is local: it originates in co-witnessed
  events and propagates only along genuine structure (zero-init and
  backbone findings, promoted to axioms).
- **I3.** Structural status is typed by Ext(s) (§4), not by a score. Empty
  rejects and many is structurally provisional; singleton permits but does
  not force commitment because named policies such as P1 may still refuse.
  Any ε in a scored policy decision carries a D4-style stability bound.
- **I4.** The knowledge layer is auditable: discrete, provenanced,
  exactly retractable commitments (event-sourcing is orthogonal to the
  redesign and survives it).

Policies (epistemic choices, named so they can be varied):

- **P1. Closed-world projection.** Only structure with ≥ k-view support
  commits (currently k = 2 — the ensemble lift of commit_k). This is
  what rejects fresh-node forgeries AND unshared truths (§2); it is not
  geometry and must never be presented as such. Its scope is now also
  measured: P1 alone would have committed E2b's false merge in 41/50
  scored seeds and kept it provisional in only 9 (§2, plan §8a) — the
  closed-world policy is not a reliable defense against lies on the
  overlap; there, rejection comes from the disagreement detector, which
  operates under P2.
- **P2. Overlap non-observation as refutation.** The E2b obstruction
  detector counts a strong backbone edge whose mapped image is absent
  (or weak) in another view as CONTRADICTED. In a finite sampled
  co-occurrence world, absence is non-observation, not observed negative
  evidence — so this reading is an epistemic policy, distinct from P1,
  named per the round-2 referee rather than presented as geometry. Its
  measured cost is pure sampling variance: 0.02 of true region-instances
  falsely flagged, 14 of those 15 on correctly mapped direct anchors.
  Discharging P2 — a per-view completeness axiom for backbone edges, or
  a statistical soundness argument connecting the detector to genuine
  incompatibility — is the standing obligation before detector verdicts
  may be read as Ext = ∅ (T2, §8). **Status: DISCHARGED at the MEASURED
  tier, under the declared E2b evaluation process** — A1 worlds PLUS the
  pre-registered overlap-forgery intervention, per the round-2 referee's
  scope correction (docs/p2-discharge.md §13–§14) — of the ledger's
  three-way
  distinction — bounded (proved) / MEASURED (simulated under the named
  model, validated on virgin data) / calibrated (fit within a
  tolerance). The path there is part of the record: a v1 analytic bound
  failed its own held-out test; v2's mixture correction passed but was
  withdrawn per referee (it composed independence A1 does not supply and
  its model mismatched the evaluated pipeline, §11); v3 abandoned
  analytic composition for direct simulation of the actual detector
  under the actual process, and passed all virgin-block gates centered
  (false-obstruction count 9 vs predicted 8.22 in prediction-error
  PI99 [2, 17]; edge
  rate 0.01753 vs 0.01884; detection 50/50 under the strict per-view
  bridge-attributable gate; gating intervals are prediction-error
  bootstrap, detection carries β ≤ 0.0076 world-level, never β = 0).
  Within the declared E2b process, "obstructed" reads as Ext = ∅ with
  MEASURED error rates; the bounded tier stays open to
  whoever wants the clustering-aware inequality. In deployment A1 is a
  per-domain empirical claim — never a model-free license to read
  absence as refutation.

## 7. Boundary conditions — what the experiments require

- **E1** (revised): the fresh-node coherent forgery is non-committed
  50/50 — by P1 over absent cross-view support, NOT by obstruction or
  underdetermination. In the canonical scoped discrete model its supported
  extension set is the singleton solo reading.
- **E2**: the solo truth is non-committed 50/50 — the SAME state as E1
  (settled, §2): determined-as-solo in scope, with P1 refusal for absent
  cross-view support. Any framework that makes E1 and E2 differ without an
  overlap-forgery-style signal or provenance is claiming more than the data;
  hidden-world sampling alternatives belong to T4.
- **E2b** (RUN, held-out, passed; interpretation bounded per round-2
  referee): the overlap forgery is separated from E1/E2 by a disjoint
  cross-view disagreement residual (≥ 2 contradicted backbone edges in
  1.00 of seeds, min 5, vs exactly 0), read under P2; P1 alone would
  have committed it in 41/50 seeds. Any formalism must derive this
  rejection from overlap disagreement, not support counting. P2 is
  discharged at the measured tier under the declared E2b evaluation
  process (§6), so the residual reads as Ext = empty with MEASURED error
  rates within that process — see §2, §6 P2, and
  results/bench-multiweb-overlap.
- **E3**: zero real mispairings across 44 worlds; all errors orphan
  merges — identity underdetermined exactly up to overlap-visible
  automorphism (T3's content).
- **E4**: the split-brain tax (0.79 × gold, knowledge 97% present) —
  the measured cost of refusing to glue; the linear layer must recover
  it and say by how much.
- **E5** (DIAGNOSED, results/rule20-diagnosis; corrected per its referee,
  accepted in full): the graded bimodality on rule_20 is DRAW-dependent —
  it tears at 2 of 5 seeds and heals or holds at the rest (scoped to
  rule_20; other worlds were not rerun across draws). On the frozen
  tearing draw the causal structure is a measured factorial
  (factorial.json), not a ladder: Shapley — rule translation 0.183,
  false-commit removal 0.139, similarity exactness 0.021, rendering 0 —
  with a 0.267 commit×translation interaction; the false commits' single-
  factor probe read exactly zero at the frozen configuration (the masking
  lesson, now stated at its measured width: it applies to that factor,
  while other single-factor probes moved 105–146 predictions without
  recovering). With both faults fixed the frozen soft similarity slightly
  exceeds discrete (0.669 vs 0.659); full exactification is
  prediction-identical to discrete. The formalism's D3/T6 story must
  reproduce the interaction, the draw-dependence, and the sign flip of
  the soft bridge (negative net at the frozen configuration, mildly
  positive once translation and the commit gate are repaired).
- **E6** (DIAGNOSED, results/rule27-diagnosis; corrected per its referee
  report, accepted in full): rule_27's "immunity" (100 ensemble rules vs
  103 gold — 15 missing, 15 extra under translation — at 0.163 under
  discrete and graded) is a catastrophic view DRAW, not a world property:
  the same world clears 0.41–0.80 at seeds 1–4. The failure is not loss
  of a witnessing path (structural: the rendering preserves topology);
  broader harness interactions remain candidates only inside the open
  residual. Under the bad draw the causally validated constraint is the
  SEAM: oracle repair of two identities heals 333 failing episodes and
  breaks none (0.163 → 0.496), including ALL 315 that die on imported
  vocabulary; the missing-body rule patch overlaps it heavily (both heal
  the same 315; they differ on 197 predictions) and 6 of the 15 missing
  gold rule bodies are cross-blind, unmineable by ANY single view. The
  orphan merge is counterfactually sensitive (89 predictions change) but
  nearly causally neutral (net +6). On the SAME world, making the graded
  layer's committed hub identity exact recovers almost nothing
  (0.163 → 0.168): identity binds the discrete semantics, not the graded
  one (D3, §5). The formalism must reproduce the seam as the discrete
  binding constraint and say what the two open residuals are — the
  discrete 0.50 → 0.83 gap and the graded failure mechanism. "0.163
  exactly" under graded was a count coincidence (22 healed, 22 broken),
  not immobility.
- **E7**: the confabulation trilogy — should reduce to "the field is a
  boundary-value problem" (I2).
- **E8**: interference cannot cross rule-web components; anchors needed
  per component. Per referee: this is not colour, it is likely the
  UNIQUENESS CONDITION of T5 (anchors in every relevant component;
  positive-definite Dirichlet Laplacian; no uncontrolled kernel).
- **E9**: the one-web frozen-algebra ceiling was real and measurable
  (carrier ladder), and the ensemble cleared it (0.13 → 0.51). The
  formalism should locate where representational capacity now lives so
  the old ceiling provably does not rebind.

## 8. The theorems (revised list, referee's T0–T4 adopted)

- **T0 Model/data separation.** Define the local state objects,
  observations-as-assignments, overlaps, and legal maps; say what a
  global section denotes in each layer (§3). **Status: discharged after
  second referee pass in docs/t0-model-data-separation.md; T1-T3 must use
  that span-valued structured-overlap setup rather than bench thresholds.**
- **T1 Extension classification.** Characterize when a finite observation
  family has zero, one, or many raw global extensions before quotienting
  by invisible automorphisms. **Status: discharged after referee review in
  docs/t1-extension-classification.md; the scoped-counting and
  supported-candidate amendments were accepted in the T3 review. Candidates
  contain only observed facts or facts legally propagated from them, so
  unsupported model padding cannot manufacture a many case.**
- **T2 Incompatibility.** Incompatible overlap data implies raw Ext = empty.
  (P2 discharged at the measured tier under the declared E2b evaluation
  process — docs/p2-discharge.md §13–§14 — so E2b's separation stands as
  T2's empirical instance relative to that named process, with measured
  rather than analytically bounded error rates. T2's
  exact theorem is docs/t2-incompatibility.md, with A1 as the bridge to
  data.) **Status: discharged after referee review; E2b now has its exact
  theorem at the measured tier. Composition-closure forcing remains open.**
- **T3 Underdetermination.** A nontrivial supported automorphism orbit that is
  invisible to the cover yields many extensions, characterized before and
  after quotienting (orphan merges live here; mere absence of overlap does
  not). **Status: discharged after referee review in
  docs/t3-underdetermination.md.**
- **T4 Identifiability.** Under explicit coverage and independence
  conditions, global extensions correspond to hidden-world semantic
  structure up to known automorphisms. (This, plus P1, is where any
  claim about TRUTH lives.)
- **T5 The thinking operator.** The graded field is the harmonic
  extension of anchor data in the linearized object: existence,
  uniqueness (hypotheses = E8), locality, convergence — retiring
  annealing, backbone thresholds and init choices as theorems or
  hypotheses.
- **T6 Enrichment soundness.** For each admissible D3 enrichment, graded
  derivations approximate exact ones with stated error; E5 selects.
- **T7 Stable commitment.** The D4 bound. Two-timescale as a theorem,
  explicitly relative to the view model.

## 9. What would falsify the conjecture itself

- Partiality (D1) cannot be accommodated without losing the exactness
  T1–T3 need.
- ~~E2b comes out indistinguishable from E1/E2 — overlap incompatibility
  is NOT detected as a different type in practice; then obstruction adds
  nothing over policy P1 + provenance, and the geometric half of the
  conjecture deflates to the linear thinking layer only.~~ **DID NOT
  TRIGGER** (§2): E2b ran held-out and the residual separation is clean
  (detector fires in 1.00 of seeds vs E1/E2 exactly 0), and the
  redundancy question resolved in the opposite direction — P1 alone
  would have committed the forgery in 41/50 seeds, so the detector is
  necessary, not merely independent (plan §8a). Per the round-2 referee
  and the later P2 discharge, the result is a disagreement separation
  whose detector verdict reads as raw Ext = ∅ at the measured tier under
  the declared E2b process; T2's remaining proof obligation is the exact
  statement over the chosen D1/D2 (§8), not a triggered falsifier. This
  falsifier is retired.
- Every admissible enrichment fails some of E5's healed/torn worlds
  simultaneously — the bimodality is not an enrichment question.
- ~~rule_27 (E6) turns out to be a harness artifact (e.g. path-horizon) —
  reclassify: it constrains the benches, not the theory.~~ **DID NOT
  TRIGGER, in its stated (path-horizon) form** (results/rule27-diagnosis;
  scope narrowed per the E6 referee): path loss is excluded structurally —
  the ensemble rendering preserves topology, so the check was vacuous by
  construction — and the world clears 0.41–0.80 at other seeds, against
  any stable artifact. The path-horizon falsifier is retired; broader
  harness interactions (path voting, tie-breaking, seam-recrossing
  intermediate symbols) remain candidates INSIDE the open 0.50 → 0.83
  residual and are not retired with it. The positive finding stands: a
  view-draw catastrophe at the vocabulary seam (§7 E6).

## 10. Discipline

The T0-T3 definition and classification gate has survived review, including
T1's scoped-counting and supported-candidate amendments. The next theory
obligation is T4; the first implementation still ships with pre-registered
predictions for all three benches. The theory-side
obligation added by the round-2 referee — the **P2 discharge** — is
**DONE at the measured tier, scoped to the declared E2b evaluation
process** (docs/p2-discharge.md §13–§14; the record includes one failed
analytic bound, one withdrawn calibrated claim, and the direct-simulation
validation that passed centered on a virgin block and survived a second
referee round with corrections applied); E2b reaches T2 as its empirical
instance under that named process (§6, §8).
Process rule, added after referees twice caught the same plan-to-code
leak (E2b's Q-D attribution, E6's activation trace): every plan ships a
**plan-to-code checklist** mapping each pre-registered metric and probe
to the function implementing it, audited before bring-up — see
docs/rule27-diagnosis-referee-response.md §3.2 for the second instance.
Empirical work licensed meanwhile, in priority order:

1. ~~**E2b, the overlap forgery**~~ — **DONE** (§2): the referee's decisive
   experiment passed held-out; the overlap forgery IS separated as a
   different measured type, and the geometry vs P1 attribution is
   answered — P1 alone would have passed the forgery in 41/50 seeds
   (plan §8a), so the detector is necessary over the scored block, not
   just independent. Interpretation bounded per the round-2 referee and
   the measured P2 discharge above: a disagreement separation under P2
   that now serves as T2's empirical instance relative to the declared
   E2b process.
2. ~~**E6, rule_27**~~ — **DONE** (results/rule27-diagnosis, pre-registered
   in docs/rule27-diagnosis-plan.md; referee corrections accepted in
   full): not a path-horizon artifact, not a wall — a view-draw
   catastrophe at the vocabulary seam; identity repair heals-only to
   0.496; the graded layer commits the hub identity yet gains nothing
   from its exactness (0.168). Feeds E5/D3 directly. Open residuals: the
   unattributed discrete 0.50 → 0.83 gap (where broader harness
   interactions also remain candidates) and the undiagnosed graded
   failure mechanism — both licensed as follow-up cells if pursued.
3. ~~**E5, rule_20**~~ — **DONE** (results/rule20-diagnosis,
   pre-registered in docs/rule20-diagnosis-plan.md; referee corrections
   accepted in full, factorial committed): the tear is an interacting
   pair — missing rule translation and two false hardening-gate commits
   (Shapley 0.183 / 0.139, interaction 0.267, factorial.json) — with the
   soft similarity itself mildly beneficial once both are repaired
   (0.669 vs discrete 0.659). Draw-dependent, scoped to rule_20. E6's
   graded residual is substantially NARROWED by the companion cell
   (956/1000 predictions coincide with discrete), not closed — the 44
   flipped episodes are unattributed. Licensed follow-ups if pursued:
   those 44; the seed-2 mechanism check; whether healing worlds' gains
   come from correct bridging.

The empirical queue is now EMPTY on the referee's own condition — the
supplementary experiment that carries E5's conclusion is a committed
reproducer (factorial.json, episode-sets.json) and the interaction is
represented as measured, not as a chosen ladder order. E2b, E6, and E5
are run, refereed, and folded in. The head of the project is now T4 over the
discharged T0-T3 setup
(docs/t0-model-data-separation.md; docs/t1-extension-classification.md;
docs/t2-incompatibility.md; docs/t3-underdetermination.md), with the measured
P2/A1 semantics gating T2's use of E2b and with imagined hidden-world states
kept in T4 rather than counted as T1 candidates. D3's admissible-enrichment
set remains constrained by measured selector data from both diagnoses.

Reading: Hansen & Ghrist, *Toward a spectral theory of cellular sheaves*
(2019); Michael Robinson's sheaf-based sensor fusion and consistency
radius (the model/data separation and the nearest existing machinery);
Curry's thesis (2014); stacks/descent at the level of Vistoli's notes,
only as far as T3 requires.
