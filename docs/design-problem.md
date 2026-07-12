# The design problem — a precise statement of the math this project now needs

*Written 2026-07-12, after the graded-ensemble runs. This document builds
nothing. It fixes the objects, states the invariances any designed
structure must respect, translates one day's empirical findings into
boundary conditions, and lists the theorems that would have to be proved
for the structure to count as DESIGNED rather than found. It is written to
be handed to a mathematician — possibly a future us reading slowly — and
to make "we cannot invent this" into a bounded, attackable claim about
which existing mathematics has to be learned and applied, rather than a
dead end.*

## 1. The thesis being formalized

Thinking occurs as dynamics in opaque geometric webs. Concepts and
semantic knowledge are projections of stable structures within and between
those webs. Multiple webs arise as different views of one hidden world;
their combination — not any single web — is where understanding lives.

Three benches now exist as the falsification harness for any candidate
formalization (all pre-registered, all with held-out results):

- **bench-multiweb** — categorical knowledge: stable regions, cross-view
  correspondence, coherent forgery, solo-truth control.
- **multiweb-graphlog** — compositional thinking: aspect-partial views of
  external rule worlds, discovered correspondence, split-brain measurement.
- **graded-ensemble** — the two-timescale attempt: soft coupling for
  thinking, hard commits for knowledge; guard passed, headline failed.

## 2. The candidate framework, stated as a conjecture

**Conjecture.** The correct formalization is a cellular sheaf (possibly
of sets for the knowledge layer, with a linearization for the thinking
layer) over the nerve of the view cover.

The dictionary that motivates it — every entry to be verified, none to be
assumed:

| this project | sheaf language |
|---|---|
| a view's web | stalk over a vertex of the nerve |
| anchors / co-witnessed events | data on the overlap (edge) cells |
| partial cross-web mapping | restriction maps (see D1: partiality) |
| semantic projection (concepts) | global sections |
| provisional structure (solo truth) | local section that does not extend |
| coherent forgery | obstructed gluing — a nonzero class in H¹ |
| destructive interference | coboundary residual / consistency radius |
| graded thinking field | harmonic extension in the linearized sheaf |
| anchor-seeded zero-init | Dirichlet boundary conditions |
| within-web relabeling invariance | isomorphism-invariance of the sheaf |

Two entries deserve emphasis because they were discovered empirically
before being recognized:

- The **zero-init finding** (graded plan §4b.3) — identity mass may only
  flow outward from co-witnessed events — is exactly the statement that
  the thinking field is the solution of a Dirichlet problem: harmonic
  extension of overlap data, not relaxation from a uniform prior. The
  uniform prior manufactured sections; the boundary-value problem cannot.
- The **provisional/false distinction** the forgery bench needed is a
  distinction sheaf theory already makes: a local section that extends to
  no larger cover (unglued, provisional) is a different object from a
  cocycle with nonzero class (obstructed, non-corresponding). No tuned
  threshold separates them; their types do.

Nearest existing work, in order of likely relevance: Hansen & Ghrist,
*Toward a spectral theory of cellular sheaves* (2019); Michael Robinson's
sheaf-based data fusion and **consistency radius** (the closest thing to
our destructive-interference measure in the literature); Curry's thesis
(2014) for the foundations; sheaf neural networks (Hansen–Gebhart,
Bodnar et al.) for learned linearizations.

## 3. Design decisions the framework must fix (not tune)

- **D1. Partiality.** Our restriction maps are partial (mappings never
  total, and must not be). Options: sheaves valued in relations or
  partial functions; stalks restricted over overlap cells; or spans.
  This is the first real decision — exactness properties differ.
- **D2. What stalks carry.** For bench-multiweb, stalks are weighted
  graphs (regions = their stable structure). For GraphLog, stalks carry
  composition — a semicategory / operad-like object, not a set. The
  sheaf must be valued in the category where that structure lives, so
  that identity across webs is structure-preserving by construction.
- **D3. The linearization functor.** The thinking layer needs vector
  spaces (free on node/token sets is the obvious move) and an operator.
  The requirement that dissolves the "which algebra?" question: the
  propagation/reduction semiring must be DERIVED from the linearization
  functor, not chosen. Sum-product vs max-product vs max-min (the
  rule_20 question) becomes a property of the functor; if the framework
  leaves it free, the framework has not done its job.
- **D4. The commitment rule.** When does soft become hard? Needed: a
  theorem of the form "if harmonic mass concentrates within ε of an
  exact section, committing to that section is sound" — replacing
  HARD_SIM = 0.5 with a bound that carries its own proof.

## 4. Invariances (non-negotiable, inherited from the project)

- **I1.** Within-web relabeling of opaque ids changes nothing (the house
  gauge invariance, already property-tested in the one-web system).
- **I2.** Identity evidence is local: it originates only in co-witnessed
  events and propagates only along genuine structure (the backbone and
  zero-init findings, promoted from patches to axioms).
- **I3.** Refusal is typed, not thresholded: "no section exists" and
  "section exists but is unglued" must be answers the formalism can give
  exactly. Any ε or floor appearing in a refusal decision must come with
  the D4-style bound that justifies it.
- **I4.** The knowledge layer is auditable: commitments are discrete,
  provenanced, and exactly retractable (event-sourcing survives the
  redesign; it is orthogonal to it).

## 5. Boundary conditions — what one day of experiments requires

Any designed structure must reproduce, ideally as theorems, all of:

- **E1** (bench-multiweb): the coherent forgery is excluded 50/50 — must
  be derivable as an obstruction, with the forgery's statistical
  coherence irrelevant by construction.
- **E2**: the solo truth is provisional 50/50 — unglued, not obstructed
  (see §2); the formalism must produce different objects for E1 and E2.
- **E3** (multiweb-graphlog): zero real mispairings across 44 worlds in
  the discrete extension, with all errors orphan merges — identity is
  underdetermined exactly up to isomorphism of what the overlap can see.
  Needed: a characterization (automorphism/quotient) of WHEN identity is
  underdetermined — this is also the polysemy-fission story in reverse,
  and should be the same lemma.
- **E4**: the split-brain tax (0.79 × gold with knowledge 97% present) —
  in the formalism, the cost of refusing to glue; harmonic extension
  should recover it, and the framework must say by how much.
- **E5** (graded-ensemble): bimodality — soft coupling healed rule_26/30/42,
  pushed rule_32 ABOVE gold-pooled, and tore rule_20 (0.66→0.32). The
  D3 functor must explain both directions or the design is wrong.
- **E6**: rule_27's immunity — 100/103 rules present, discrete and graded
  both 0.163, unmoved by every mechanism. **Open diagnosis; cheap
  empirical work that should precede formalization** — a designed theory
  must predict it, so we must first know what it is.
- **E7**: the confabulation trilogy (normalization manufactures
  confidence; noise edges carry no identity; uniform priors seed
  invention) — should fall out as: the field is a boundary-value problem
  (I2), full stop.
- **E8** (rule_0 bring-up): triangle interference cannot cross rule-web
  components; anchors are needed per component — in sheaf terms,
  connectivity of the base/stalk structure bounds what overlap data can
  determine. Should become the coverage hypothesis of the representation
  theorem T1.
- **E9** (carrier ladder, bench v3): a frozen one-web algebra has
  measurable representational ceilings, and the ensemble cleared one
  (0.13 → 0.51). The formalism should locate WHERE algebraic capacity
  now lives (in the stalks? the gluing? the linearization?) such that
  the old ceiling provably does not rebind.

## 6. The theorems needed (the "preliminary math", enumerated)

- **T1 Representation.** Under stated coverage conditions (E8), the
  global sections of the view-sheaf recover the hidden world's semantic
  structure. Without coverage, characterize what is recoverable.
- **T2 Obstruction.** A pattern with no overlap support admits no global
  section; the forgery bench's 50/50 becomes a corollary, not a result.
- **T3 Provisional ≠ false.** Unglued and obstructed are distinct,
  decidable types (E2 vs E1).
- **T4 Identity underdetermination.** Identity across webs is determined
  exactly up to the automorphisms of what overlaps see; orphan merges
  (E3) are the quotient, and fission on new evidence is its inverse.
- **T5 The thinking operator.** The graded field is the harmonic
  extension of anchor data in the linearized sheaf: existence,
  uniqueness, locality, and convergence — retiring annealing schedules,
  backbone thresholds and init choices as constants (they become
  hypotheses or corollaries).
- **T6 Functorial reduction.** The derivation semantics (rule_20's
  sum-vs-max) is determined by D3, with a soundness statement: graded
  derivations approximate exact ones with bounded error.
- **T7 Sound commitment.** The D4 bound: concentration implies safe
  hardening. This is the two-timescale claim as a theorem, and the only
  acceptable replacement for HARD_SIM.

## 7. What would falsify the conjecture itself

- Partiality (D1) cannot be accommodated without losing the exactness
  that makes T2/T3 work.
- E1 and E2 turn out NOT to be type-distinct in any sheaf formulation —
  i.e., the provisional/false distinction genuinely needs provenance,
  not geometry.
- The D3 functor exists but leaves the reduction semiring free after
  all — then the algebra question returns as a free parameter and the
  framework has merely renamed the problem.
- rule_27 (E6), once diagnosed, is something no gluing story touches —
  e.g., a path-search horizon artifact — in which case it constrains
  the benches, not the theory, and must be reclassified.

## 8. Doing this honestly

The failure mode this document exists to prevent has a name in this
repo's history: mechanism-search wearing better vocabulary. The rule for
the design phase, matching the falsification culture: **no
implementation until T1–T3 are actually proved for the chosen D1/D2**,
at whatever level of rigor we can genuinely sustain — and the first
implementation ships with its predictions for all three benches written
down before it runs. The empirical work that IS licensed meanwhile:
diagnosing E6 (rule_27) and the rule_20 collapse, because a theory built
to explain misdiagnosed data is designed wrong from the start.
