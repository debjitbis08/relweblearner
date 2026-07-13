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
Ext = ∅ instance of T2. rev 2 is preserved in git history. This document
builds nothing. It fixes the objects, states the
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
identical (both unglued/underdetermined), exactly as the bench's own
honest-limit paragraph (P-D) had already stated before the v1 document
forgot it. The v1 claim "forgery = nonzero H¹" was wrong.

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
  flags sit on correctly mapped direct anchors). So E2b establishes a
  reliable, typed, cross-view **disagreement separation** — not yet literal
  incompatibility (Ext = ∅): that identification is T2's standing proof
  obligation (§8), requiring an explicit semantics for absent edges. Two
  calibration lessons: gate the residual on a COUNT, not a dilution-prone
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
  selector experiment between enrichments, not a bug to patch. The E6
  diagnosis added a second selector datum (results/rule27-diagnosis): the
  graded layer FOUND and COMMITTED the hub identity (S = 0.62, mutual
  argmax) and still could not use it — multiplicative similarity taxes
  every bridged span, so a discovered identity decays toward the
  activation floor with derivation depth. The enrichment decides whether
  identity, once discovered, is CASHABLE.
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
- **I3.** Refusal is typed by Ext(s) (§4), not thresholded. Any ε in a
  refusal decision carries a D4-style stability bound.
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
  may be read as Ext = ∅ (T2, §8).

## 7. Boundary conditions — what the experiments require

- **E1** (revised): the fresh-node coherent forgery is non-committed
  50/50 — by P1 over an underdetermined extension set, NOT by
  obstruction. The formalism must reproduce it as such.
- **E2**: the solo truth is non-committed 50/50 — the SAME state as E1
  (settled, §2). Any framework that makes E1 and E2 differ without an
  overlap-forgery-style signal or provenance is claiming more than the
  data.
- **E2b** (RUN, held-out, passed; interpretation bounded per round-2
  referee): the overlap forgery is separated from E1/E2 by a disjoint
  cross-view disagreement residual (≥ 2 contradicted backbone edges in
  1.00 of seeds, min 5, vs exactly 0), read under P2; P1 alone would
  have committed it in 41/50 seeds. Any formalism must derive this
  rejection from overlap disagreement, not support counting; equating
  the residual with Ext = empty awaits T2's soundness argument — see §2
  and results/bench-multiweb-overlap.
- **E3**: zero real mispairings across 44 worlds; all errors orphan
  merges — identity underdetermined exactly up to overlap-visible
  automorphism (T3's content).
- **E4**: the split-brain tax (0.79 × gold, knowledge 97% present) —
  the measured cost of refusing to glue; the linear layer must recover
  it and say by how much.
- **E5**: graded bimodality — heals rule_26/30/42, rule_32 above
  gold-pooled, tears rule_20 — the D3 selector data.
- **E6** (DIAGNOSED, results/rule27-diagnosis): rule_27's "immunity"
  (100/103 rules present, 0.163 under discrete and graded) is a
  catastrophic view DRAW, not a world property — the same world clears
  0.41–0.80 at seeds 1–4 — and not a harness artifact (zero pathless
  failures). Under the bad draw the failure is the SEAM: 38% of failures
  die on imported A-blind vocabulary; oracle identity repair (0.496),
  oracle rule-inventory patch (0.503), and both combined (0.503) hit the
  same ceiling — split vocabulary and missing rules are two faces of one
  failure, and 6 of the 15 missing gold rules are cross-blind, unmineable
  by ANY single view. The graded layer found and committed the hub
  identity yet could not cash it (D3, §5). The formalism must reproduce
  the seam as the binding constraint and say what the residual
  (0.50 → 0.83, unattributed) is. "0.163 exactly" under graded was a
  count coincidence (22 healed, 22 broken), not immobility.
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
  global section denotes in each layer (§3).
- **T1 Extension classification.** Characterize when a local assignment
  has zero, one, or many global extensions.
- **T2 Incompatibility.** Incompatible overlap data implies Ext = empty.
  (E2b measures its candidate signal; identifying the E2b residual with
  Ext = empty additionally requires the P2 discharge — an explicit
  semantics for absent co-occurrence edges and a soundness argument
  connecting the operational detector to incompatibility, §6.)
- **T3 Underdetermination.** Insufficient overlap yields many
  extensions, characterized by the automorphism group / quotient visible
  to the cover (orphan merges and provisional states live here).
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
  the result is a disagreement separation under P2, not yet literal
  Ext = ∅ — a bounded interpretation carried as T2's proof obligation
  (§8), not a triggered falsifier. This falsifier is retired.
- Every admissible enrichment fails some of E5's healed/torn worlds
  simultaneously — the bimodality is not an enrichment question.
- ~~rule_27 (E6) turns out to be a harness artifact (e.g. path-horizon) —
  reclassify: it constrains the benches, not the theory.~~ **DID NOT
  TRIGGER** (results/rule27-diagnosis): zero failing episodes lack a
  witnessing path, and the world clears 0.41–0.80 at other seeds. Not an
  artifact — a view-draw catastrophe at the vocabulary seam (§7 E6).
  Retired.

## 10. Discipline

No implementation until T0–T3 are proved for the chosen D1/D2, at
whatever rigor we can genuinely sustain; the first implementation ships
with pre-registered predictions for all three benches. One theory-side
obligation, added by the round-2 referee, precedes any use of E2b as
T2's formal boundary condition: the **P2 discharge** (§6, §8) — an
explicit semantics for absent co-occurrence edges and a soundness
argument connecting the disagreement detector to incompatibility.
Empirical work licensed meanwhile, in priority order:

1. ~~**E2b, the overlap forgery**~~ — **DONE** (§2): the referee's decisive
   experiment passed held-out; the overlap forgery IS separated as a
   different measured type, and the geometry vs P1 attribution is
   answered — P1 alone would have passed the forgery in 41/50 seeds
   (plan §8a), so the detector is necessary over the scored block, not
   just independent. Interpretation bounded per the round-2 referee: a
   disagreement separation under P2 — T2's candidate anchor, pending the
   P2 discharge above.
2. ~~**E6, rule_27**~~ — **DONE** (results/rule27-diagnosis, pre-registered
   in docs/rule27-diagnosis-plan.md): not a harness artifact, not a wall —
   a view-draw catastrophe at the vocabulary seam; repairs converge at a
   0.50 ceiling; the graded layer discovers but cannot cash the hub
   identity. Feeds E5/D3 directly. Open residual: the unattributed
   0.50 → 0.83 gap, licensed as a follow-up cell if pursued.
3. **E5, rule_20** — now the head of the queue: the enrichment selector
   needs a mechanism-level account of the collapse, and E6 has sharpened
   the question it must answer — the enrichment decides whether discovered
   identity is cashable (rule_27's committed-but-unusable hub, §5 D3).

Reading: Hansen & Ghrist, *Toward a spectral theory of cellular sheaves*
(2019); Michael Robinson's sheaf-based sensor fusion and consistency
radius (the model/data separation and the nearest existing machinery);
Curry's thesis (2014); stacks/descent at the level of Vistoli's notes,
only as far as T3 requires.
