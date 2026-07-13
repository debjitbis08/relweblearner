# The design problem — a precise statement of the math this project now needs

*Written 2026-07-12; **revision 2 same day, after external referee.** The
referee's corrections are accepted in full and worked in rather than
appended: the v1 text promoted the coherent-forgery exclusion to a
cohomological obstruction it never was, and the referee's decisive
question ("why exactly was the forgery excluded while the solo truth
remained provisional?") turned out to be answerable from the
implementation in one grep — see §2. v1 is preserved in git history
(eb96448). This document builds nothing. It fixes the objects, states the
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
- **The decisive bench was missing; it has now been run, and it holds.** An
  **overlap forgery** — liars wire a false pattern among CO-WITNESSED nodes, so
  view agreement is violated on the overlap itself — was pre-registered
  (docs/multiweb-overlap-forgery-plan.md) and run held-out (50 seeds,
  results/bench-multiweb-overlap). A false MERGE bridging two co-witnessed
  communities is rejected as a genuinely different TYPE than the fresh-node
  forgery: **obstructed** (contradicted backbone residual ≥ 2, in 1.00 of seeds;
  E1/E2 residual exactly 0) vs **unsupported**, detected as an extension failure
  with NO closed-world policy invoked (Q-D geometric rejection 1.00), and true
  regions almost untouched (0.02 falsely obstructed, recall 0.99). So the
  geometric-obstruction half of the framework carries **real weight** in the
  ensemble setting — the §9 falsifier did not trigger. This is the empirical
  content of T2; it fixes the type distinction the T1–T3 statements must now
  reproduce, and one calibration lesson: the residual must be gated on a COUNT,
  not a weight ratio (the ratio mean was 0.49, straddling the naive 0.5 gate).

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
  selector experiment between enrichments, not a bug to patch.
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
  geometry and must never be presented as such.

## 7. Boundary conditions — what the experiments require

- **E1** (revised): the fresh-node coherent forgery is non-committed
  50/50 — by P1 over an underdetermined extension set, NOT by
  obstruction. The formalism must reproduce it as such.
- **E2**: the solo truth is non-committed 50/50 — the SAME state as E1
  (settled, §2). Any framework that makes E1 and E2 differ without an
  overlap-forgery-style signal or provenance is claiming more than the
  data.
- **E2b** (RUN, held-out, passed): the overlap forgery is rejected as
  Ext = empty (obstructed, 1.00 of seeds), a genuinely different type from
  E1/E2 (unsupported) — see §2 and results/bench-multiweb-overlap.
- **E3**: zero real mispairings across 44 worlds; all errors orphan
  merges — identity underdetermined exactly up to overlap-visible
  automorphism (T3's content).
- **E4**: the split-brain tax (0.79 × gold, knowledge 97% present) —
  the measured cost of refusing to glue; the linear layer must recover
  it and say by how much.
- **E5**: graded bimodality — heals rule_26/30/42, rule_32 above
  gold-pooled, tears rule_20 — the D3 selector data.
- **E6**: rule_27 immunity (100/103 rules, 0.163 under discrete AND
  graded). **Undiagnosed; diagnosis licensed and prerequisite.**
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
  (E2b is its experiment.)
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
  TRIGGER** (§2): E2b was run held-out and the type distinction is clean
  (obstructed 1.00 vs unsupported, geometric rejection 1.00). The geometric
  half stands; this falsifier is retired.
- Every admissible enrichment fails some of E5's healed/torn worlds
  simultaneously — the bimodality is not an enrichment question.
- rule_27 (E6) turns out to be a harness artifact (e.g. path-horizon) —
  reclassify: it constrains the benches, not the theory.

## 10. Discipline

No implementation until T0–T3 are proved for the chosen D1/D2, at
whatever rigor we can genuinely sustain; the first implementation ships
with pre-registered predictions for all three benches. Empirical work
licensed meanwhile, in priority order:

1. ~~**E2b, the overlap forgery**~~ — **DONE** (§2): the referee's decisive
   experiment passed held-out; incompatible overlap data IS rejected as a
   different TYPE, and the geometry vs P1 question is answered — obstruction
   carries weight, and it fires without P1. T2 now has its empirical anchor.
2. **E6, rule_27** — now the head of the queue: diagnose before formalizing;
   a theory built to explain misdiagnosed data is designed wrong.
3. **E5, rule_20** — the enrichment selector needs a mechanism-level
   account of the collapse.

Reading: Hansen & Ghrist, *Toward a spectral theory of cellular sheaves*
(2019); Michael Robinson's sheaf-based sensor fusion and consistency
radius (the model/data separation and the nearest existing machinery);
Curry's thesis (2014); stacks/descent at the level of Vistoli's notes,
only as far as T3 requires.
