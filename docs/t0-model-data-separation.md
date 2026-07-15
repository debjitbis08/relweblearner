# T0 — model/data separation for the multi-web descent structure

*Written 2026-07-15. This is the first theory deliverable after
docs/design-problem.md: it fixes the objects that T1-T3 will reason about.
It deliberately proves no extension theorem. Its job is to prevent the next
proofs from sliding between the model, the observed webs, and the evaluation
gold.*

## 1. Status

**Status: discharged after second referee pass.** The project now has explicit
answers to the four T0 questions from design-problem §8:

- local state objects are finite structured state spaces over view and
  overlap indices;
- observations are assignments into those state spaces, never the state
  spaces themselves;
- overlaps are represented by span-valued partial maps, not total
  identifications;
- a global section denotes different objects at the knowledge and linear
  layers, specified below.

T1-T3 must use these definitions rather than replacing them with
bench-specific thresholds. T1, including its scoped-counting and
supported-candidate amendments, is discharged in
docs/t1-extension-classification.md; T2 is discharged in
docs/t2-incompatibility.md; T3 is discharged in
docs/t3-underdetermination.md.

## 2. The index object: the cover nerve

For a run with views `V = {0, ..., K-1}`, define a finite cover category
`N(V)`:

- objects are non-empty finite subsets `S <= V`;
- `S -> T` exists when `S <= T`.

Singleton objects `{i}` are view charts. Pair objects `{i,j}` are measured
overlaps. Larger index sets are smaller geometric charts: `{i,j,k}` is the
triple overlap. This convention makes arrows point in the restriction
direction used below: data on `{i}` and `{j}` must agree after both restrict
to `{i,j}`.

The cover category is part of the **model**. A sampled web is not a cover
object; it is an observed assignment at one or more cover objects.

## 3. T0-D1: partiality as spans

Partial identity evidence is represented by overlap charts whose restriction
legs are spans in a chosen category of finite structured objects:

```
X_i <- O_ij -> X_j
```

`X_i = M({i})` is the state object for view `i`; `O_ij = M({i,j})` is the
overlap state object carrying only co-witnessed or legally propagated identity
evidence. The two legs are the span presentation of the restrictions from
the view charts to the overlap chart: a restriction is defined only on the
subobject named by the span apex, and the map out of the apex is total.

Thus the two presentations are the same in T0:

- as an indexed model, the pair object `{i,j}` has state object `M({i,j})`;
- as a partial-map picture, that same state object is the apex `O_ij` of the
  span between the two singleton state objects.

For higher overlaps, `M({i,j,k})` is the common domain on which the pairwise
overlap identifications must cohere.

This is the first D1 choice:

- restrictions are not total functions `X_i -> X_ij`;
- absence from `O_ij` means "not in the overlap domain";
- conflicting images in `O_ij` are incompatibility candidates for T2;
- fresh-node forgeries and solo truths both have empty or insufficient
  overlap domain, so their canonical scoped state is determined-as-solo and
  their non-commitment is a P1 case, not a T2 or T3 case.

Operational anchors, structural extensions, and GraphLog vocabulary seams are
all observations of these span legs. They are never allowed to become hidden
total bijections.

## 4. T0-D2: what local states carry

The value category for the knowledge layer is `Str`, whose objects are finite
opaque-id structures with provenance:

- weighted undirected graphs for bench-multiweb regions;
- finite directed labeled multigraphs or semicategories for GraphLog-style
  composition;
- optional exact negative predicates, such as absent edge/path facts, only
  when a named assumption or measured discharge admits them into the model;
- optional typing/provenance fields used only to audit which observations
  support an edge, rule, anchor, or restriction.

State-space exclusion axiom: no legal state may contain both a positive fact
and its declared exact negation on the same support.

Morphisms in `Str` are partial structure-preserving maps, represented by
spans as above. They must preserve:

- node identity only where overlap evidence exists;
- edge incidence and orientation;
- edge labels or rule bodies when the state object carries them;
- weights only through declared predicates such as "backbone", not by
  assuming equal numeric scales across views;
- exact negative predicates and the state-space exclusion axiom;
- provenance monotonicity: a map may forget support when restricting, but may
  not invent support.

This is the D2 choice needed for T1-T3. The legal-map constraints in §6 are
exactly these morphism constraints, specialized to candidate assignments. A
plain sheaf of sets is too weak
because it forgets graph/semicategory structure; a full stack may still be
needed for T3's automorphism quotient, but T0 starts with the site and the
span-valued structured restriction object that such a stack would refine.

## 5. Model objects versus observed assignments

For each cover object `S`, the model supplies a state object `M(S)` in
`Str`. `M(S)` is the space of legal local states at that chart or overlap.
It is not populated by evaluation gold.

An observed run supplies a finite structured datum `sample_S`: a provenance-
labeled finite graph, path/rule fragment, anchor table, or overlap witness
whose support was actually produced by the run at chart `S`. Formally,
`sample_S` is an object of `Str` equipped with its own provenance; it is
chosen by the declared observation pipeline, not by evaluation gold.

An assignment is a provenance-preserving monomorphism or partial homomorphism:

```
a_S in Assign(S) =
  TotalMono_Str(sample_S, M(S))     for observed local substructures
  SpanHom_Str(sample_S, M(S))       for observed partial correspondences
```

When the datum is a region, edge set, or rule body, read this as a
distinguished finite subobject of `M(S)` with provenance, embedded by a total
structure-preserving monomorphism. When it is an anchor or partial
correspondence, read it as a span-valued partial homomorphism into the
relevant overlap object. T1 classifies completions of these observed partial
substructures, not arbitrary points of a hidden stalk and not total view
states.

T1 may use only **supported candidates**: every atomic fact in a candidate
must either occur in an observed assignment or be legally propagated from one
through the declared restriction spans and structural rules, with the
provenance chain retained. Ambient atoms in `M(S)` with no such support are
model possibilities, not candidate extensions. Abductive or imagined states
belong to T4 and do not enter T1-T3 extension counts unless a later observation
or deductive rule supplies support.

Examples:

- a Louvain-stable region in view `i` is an assignment at `{i}`;
- a partial anchor map between views `i` and `j` is an assignment at
  `{i,j}`;
- a GraphLog imported rule body is an assignment in the semicategory object
  for its view;
- an obstruction detector's counted contradicted edges are diagnostics of
  whether the assignments at `{i}` and `{j}` can restrict to one assignment
  at `{i,j}`.

Gold hidden communities, true entity ids, and generated labels in benchmark
dataclasses are evaluation instruments. They are not elements of `M(S)`, and
they are not legal maps in the model.

## 6. Legal maps

A legal map is a provenance-preserving partial homomorphism in `Str`.
Concretely, a candidate map `f: X_i partial-> X_j` is legal only on a domain
`D_f <= X_i` for which the model has overlap support. It must satisfy all
declared structure predicates on that domain, matching §4:

- mapped endpoints of a declared edge predicate such as "backbone" must land
  on a structurally compatible edge predicate when both sides are observed;
- mapped GraphLog paths must preserve composition where both sides are
  defined;
- map extension can propagate through backbone-supported neighborhoods, but
  unobserved nodes remain unmapped;
- automorphisms inside an overlap-invisible component are legal alternatives,
  not errors.

Every propagation rule used by T1 must be declared as a finite relation on
atomic facts in the relevant `M(S)`. A legal propagation step requires
supported input facts, checks the rule's structural preconditions, produces
only facts already available in the target model object, and records the
source observations and rule identifiers in normalized finite provenance.
Repeated traversal of a propagation cycle does not create a new provenance
label. Legal propagation is the least fixed point of those finite rules.
Scores, unused ambient atoms, and abductive or imagined hypotheses are not
propagation steps.

Illegal maps are not merely low-score maps. They are outside the assignment
space and cannot be used by T1-T3.

P2/A1 is not part of map legality. It is a statistical semantics for reading
a sampled missing edge as evidence for an exact negative edge fact in the
overlap object, with measured error, and enters only when T2 interprets an
E2b detector verdict as an exact overlap conflict under the declared process.

## 7. Global sections by layer

T0 fixes the overloaded phrase "global section" as follows.

**Knowledge layer.** A raw global knowledge section is a family
`(a_S)_S` of discrete structured assignments over the cover nerve satisfying
the restriction and cocycle conditions:

- for every arrow `S -> T`, the restriction of `a_S` along the declared
  span-valued restriction equals `a_T` on their common observed domain;
- for every triple `{i,j,k}`, the two composites from view data through
  `{i,j}` and `{j,k}` into `{i,j,k}` agree with the direct restriction to
  `{i,j,k}` where all are defined.

The second clause is the descent/cocycle condition. If a bench or proof
intentionally truncates to pair overlaps, it must say so and state that loop
holonomy and destructive-interference phenomena are out of that theorem's
scope.

A raw global knowledge section denotes one cross-view concept, rule, identity
seam, or complete knowledge state depending on which state object is under
discussion. T1-T3 must state the object level explicitly: region-level,
rule-level, seam-level, or whole-state.

**Extension-set layer.** For a local assignment `s`, `Ext_raw(s)` is the set
of raw global knowledge sections whose restriction contains `s`. This is the
cardinality that controls design-problem §4 and T1-T3:

- `Ext_raw(s) = empty` means obstructed/incompatible;
- `|Ext_raw(s)| = 1` means determined relative to the model;
- `|Ext_raw(s)| > 1` means underdetermined/provisional.

T1 reads this modulo sample presentation: two observations with the same
image subobject or span image inside `M(S)`, and the same provenance labels,
contribute one raw extension, not two syntactic presentations.

T1 also reads extension counts relative to a declared scope `W`: by default
the support closure of the observation family. Variation outside `W` is not
counted. This prevents irrelevant untouched charts from making every
observation family many by default; T1 writes the scoped set as
`Ext_raw^W(A)`.

Inside `W`, T1 counts only supported candidates as fixed in §5. Unsupported
padding is not an extension: adding an unused atom of `M(S)` with no observed
or legally propagated provenance does not turn a singleton into a many case.

Only after this raw set is defined may we quotient by invisible
automorphisms. Let `Aut_cover^W(A)` act on `Ext_raw^W(A)` by changing choices
inside supported components not pinned by overlap spans. The quotient
`Ext_raw^W(A) / Aut_cover^W(A)` records semantic equivalence classes. Raw
cardinality supplies the structural state before this quotient, while P1
independently evaluates its declared cross-view support requirement.
Singleton is therefore only structural permission to commit; P1 may still
refuse. This keeps E3 orphan merges in the many-extension case: they may be
one quotient class while still having multiple raw extensions, while E1/E2
remain singleton solo readings that P1 declines to commit.

**Linear thinking layer.** A global linear section is a compatible field in a
linearization `L(M)` of the structured model, with boundary values supplied
by anchors or committed assignments. It denotes a graded thinking field, not a
belief by itself. T5-T7, not T1-T3, determine when such a field is unique,
stable, and safe to harden.

These meanings must not be interchanged. In particular, a low linear residual
does not prove a unique raw knowledge extension unless T6/T7 supply that
bridge.

## 8. Bench translation checks

The existing empirical facts translate into T0 as follows.

**E1 fresh-node forgery.** The forged region is a valid assignment at `{0}`
with no overlap-domain assignment at `{0,j}`. Supported-candidate counting
gives the canonical scoped state a unique solo extension. Its refusal is P1
over absent cross-view support, not incompatibility or T3 underdetermination.

**E2 solo truth.** The solo community has the same T0 type as E1: a valid,
determined-as-solo single-view assignment with insufficient overlap support
for P1 commitment. Any claim that this solo reading is externally true, or
that another view merely failed to sample it, must enter through T4
assumptions, not through T0.

**E2b overlap forgery.** The false merge asserts a local assignment whose
mapped bridge edges conflict with the overlap object when the detector's
sampled missing edges are interpreted under the P2/A1 semantics. This is the
empirical input T2 must formalize as `Ext_raw = empty` relative to the
declared process and measured error rates.

**E3 orphan merges.** Multiple assignments differ only by automorphisms not
seen by the overlap span. They remain multiple raw extensions even if they
collapse to one quotient class. T3 must characterize the torsor/quotient
rather than choosing a representative.

**E6 vocabulary seam.** A seam is a partial span between rule/vocabulary
objects. Repairing two identities changes the discrete compatible-family
problem; making a graded hub identity exact need not affect the knowledge
extension set unless the structured map changes.

## 9. What T1-T3 may now assume

The next proofs may assume:

- a finite cover nerve `N(V)`;
- a span-valued structured restriction pseudofunctor
  `M: N(V) -> Span(Str)`, where the arrows of `N(V)` are already oriented
  as restrictions and span composition is by pullback, associative up to
  canonical isomorphism;
- observed assignments with explicit provenance;
- legal partial maps as defined in §6;
- P1 as a commitment policy external to extension existence;
- P2/A1 as the measured semantics for absent backbone edges only in the
  declared E2b operating process.

They may not assume:

- hidden benchmark entity ids as model data;
- total view-to-view bijections;
- thresholded support counts as extension classification;
- linear harmonic agreement as discrete compatibility;
- truth in the external world without T4 coverage and independence
  assumptions.

## 10. T0-T3 outcome

T1 is discharged, including the scoped-counting and supported-candidate
amendments, in docs/t1-extension-classification.md: finite observation
families are classified by the finite solution set `Sol(C_M^W(A))`, with raw
sections counted modulo sample presentation, relative to a declared scope
`W`, and without unsupported model padding.

T2 is discharged in docs/t2-incompatibility.md: exact incompatible facts
forced in a common overlap object imply `Sol(C_M^W(A)) = empty` for every
scope `W` containing that conflict. The P2 discharge supplies the measured
bridge from sampled absent edges to this exact overlap conflict for E2b.

T3 is discharged in docs/t3-underdetermination.md: nontrivial automorphism
orbits invisible to the cover inside `W` imply `|Ext_raw^W(A)| > 1`, with
quotienting kept separate from raw cardinality. This is where supported orphan
alternatives belong; E1/E2 are instead determined-as-solo P1 cases.
