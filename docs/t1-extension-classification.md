# T1 — extension classification over the T0 descent model

*Written 2026-07-15, after T0 was discharged by second referee pass. This
note proves only the classification layer: for a finite family of observed
assignments `A`, the raw extension set is a finite, explicitly defined
compatibility solution set, and its cardinality gives the three
design-problem states.
It does not itself prove the T2 zero-extension criterion or the T3
automorphism/torsor criterion.*

## 1. Status

**Status: discharged after referee review; scoped-counting and
supported-candidate amendments accepted in the T3 review.** Given the T0 data
`(N(V), M, Assign, legal maps)`, T1 defines a
finite constraint system `C_M^W(A)` for any finite observation family `A` and
declared finite scope `W`, and proves:

```
Ext_raw^W(A) ~= Sol(C_M^W(A))
```

Therefore exactly one of the three cases holds:

- `Sol(C_M^W(A)) = empty`: obstructed / incompatible in scope `W`;
- `|Sol(C_M^W(A))| = 1`: determined relative to the view model in `W`;
- `|Sol(C_M^W(A))| > 1`: underdetermined / provisional in `W`.

This is model-relative. It says nothing about external truth; T4 carries that.
It also counts raw sections before quotienting by invisible automorphisms; T3
classifies the quotient/torsor structure.

## 2. Inputs inherited from T0

Fix:

- a finite cover category `N(V)`, with `S -> T` when `S <= T`;
- a span-valued structured restriction pseudofunctor
  `M: N(V) -> Span(Str)`;
- finite structured state objects `M(S)` for each chart or overlap `S`;
- observed assignments `a_S` as total subobject embeddings or span-valued
  partial correspondences;
- legal maps as provenance-preserving partial homomorphisms in `Str`;
- raw compatibility: restriction agreement along every arrow plus the triple
  cocycle condition on `{i,j,k}` where all terms are defined.

All these objects are finite in the benches and in the first theory target.
If a later model allows infinite state spaces, T1 must be replaced by a
compactness or decidability theorem; this note does not cover that case.

## 3. Observation families, scopes, and candidate states

Let `A = {(S_alpha, s_alpha)}` be a finite family of observed assignments,
possibly at several charts and overlaps. The singleton case from T0 is the
special case `A = {(S0, s)}`. E2b-style situations use the general case:
view assignments and overlap evidence enter the same containment list.

Let `W <= N(V)` be a finite subdiagram, called the **counting scope**. It must
contain the support closure of `A`: the least subdiagram containing every
chart carrying an observation, every chart reached by repeated declared legal
restriction/span propagation from those observations, and every higher
overlap needed by the resulting cocycle checks. The canonical scope is this
support closure; larger scopes may be declared when a theorem intentionally
asks about a larger object level.

Raw extension counting is relative to `W`. Variation outside `W` is ignored:
two global solutions with the same restriction to `W` are one element of
`Ext_raw^W(A)`. The old unscoped notation is the special case `W = N(V)` and
should not be used for commitment claims.

T1 now separates observed assignments from model-side candidates and excludes
unsupported padding.

For each `S in W`, define `Prop_M^W(A; S)` to be the least set of supported
atomic facts in `M(S)` such that:

- every atomic fact in an observation `(S, s_alpha) in A` belongs to it with
  its observed provenance;
- if a supported fact can be carried to another chart in `W` by a declared
  legal restriction, span leg, or structural propagation rule from T0, its
  image belongs to the target set with the derivation provenance attached;
- the rule is iterated to closure inside `W`.

This is a deductive support closure, not a hypothesis generator. Mere
membership in an ambient state object `M(S)`, an unused model atom, or an
imagined hidden-world state does not enter `Prop_M^W(A; S)`. Such hypotheses
belong to T4 and cannot count as observed or derived support.

For each `S in W`, define `Cand_M^W(A; S)` to be the finite set of supported
candidate local states at `S`:

- finite legal subobjects of `M(S)` whose every atomic fact belongs to
  `Prop_M^W(A; S)` with matching observed or derivation provenance;
- finite legal span subobjects internal to `M(S)` for partial
  correspondences at overlap charts, subject to the same support condition;
- the empty candidate.

An application may declare a stricter finite **completion convention** on
this supported family, provided the convention is fixed and serialized as
part of the theorem instance. The variable domain `D_S^W(A)` below then uses
the selected candidates. For example, the GraphLog T5-T7 instance orders
supported partial overlap maps by inclusion and retains only maximal legal
maps containing every anchor. Operationally its non-anchored relation
variables have an explicit `UNMAPPED` value and a completed assignment is
kept exactly when no legal supported identity pair can be added without
changing an existing pair. This is not ambient totalization: unsupported
Cartesian-product pairs never enter a domain, and anchored variables cannot
be unmapped. Without a declared completion convention, `Cand_M^W(A; S)` has
the inclusive meaning stated above.

Two presentations with different external sample objects but the same image
subobject or same span image inside `M(S)`, with the same provenance labels,
are one candidate. T1 therefore counts model-side raw states, not syntactic
sample presentations. This is the commitment-relevant choice: presentation
multiplicity never turns a singleton model state into `|Ext_raw| > 1`.

`Prop_M^W(A; S)` and `Cand_M^W(A; S)` are finite because `W` and every `M(S)`
are finite, the declared propagation rules operate inside those finite
objects, and T0 normalizes provenance to finite source-observation and rule-id
support rather than retaining arbitrarily repeated derivation paths. In
particular, a candidate cannot be enlarged by an atom that has no provenance
path from `A`.

A raw scoped extension of `A` over `W` is a family `(x_S)_{S in W}` with one
candidate local state (after any declared completion convention) for every
cover object `S` in `W`, such that:

- each `x_S` lies in `Cand_M^W(A; S)`;
- every observed `s_alpha` at chart `S_alpha` is contained in `x_{S_alpha}`
  as an image subobject or span image;
- every restriction arrow `S -> T` carries `x_S` to the same candidate
  substate as `x_T` on their common domain;
- every triple overlap satisfies the T0 cocycle condition.

To classify these extensions, introduce one finite variable `X_S` for each
cover object `S in W`. The domain of `X_S` is the finite set:

```
D_S^W(A) = { x in Cand_M^W(A; S) : x contains every observed s_alpha in A
           with S_alpha = S }.
```

For charts in `W` not directly touched by `A`, this domain contains only
candidates assembled from facts legally propagated there from `A`, together
with the empty candidate. Scoped but unsupported charts and higher overlaps
therefore have only the empty candidate and never obstruct by mere absence of
observation. Charts outside `W` are not counted at all.

## 4. The constraint system C_M^W(A)

`C_M^W(A)` is the conjunction of four finite constraint families, restricted
to variables and arrows in `W`.

**Containment.** For every observed assignment `(S_alpha, s_alpha) in A`,
`X_{S_alpha}` contains `s_alpha`.

**Restriction agreement.** For every arrow `S -> T` in `W`, the two restricted
assignments agree on the common defined domain:

```
res_{S,T}(X_S)|_C = X_T|_C,   C = dom(res_{S,T}(X_S)) intersect dom(X_T)
```

where `res_{S,T}` is represented by T0's span-valued restriction. Equality is
equality of structured assignments with provenance, not equality of hidden
gold ids.

**Cocycle coherence.** For every triple `{i,j,k}`, all defined composites of
the pairwise restrictions into `M({i,j,k})` agree. This is the finite
descent condition that detects loop/holonomy-style failures once the relevant
triple data are in scope.

**Legality.** Every map used by a variable or restriction satisfies T0 §6:
it preserves identity only on supported overlap domains, preserves incidence,
orientation, labels/rule bodies where present, declared edge predicates such
as backbone, and provenance monotonicity.

No P1 threshold, P2 statistical reading, or evaluation gold appears in
`C_M^W(A)`. P2 enters only by changing which sampled detector verdicts are
admitted as measured evidence for an exact overlap conflict in T2.

## 5. The theorem

**Theorem T1.** For every finite T0 model `M`, every finite observation family
`A`, and every declared finite scope `W` containing the support closure of
`A`, there is a canonical bijection:

```
Ext_raw^W(A) <-> Sol(C_M^W(A)).
```

**Proof.**

Forward map. Take a raw scoped extension `e in Ext_raw^W(A)`. By the
definition above, `e` is a family of candidate local states over `W`, contains
every observation in `A`, agrees under all restrictions in `W`, and satisfies
the triple cocycle condition required in `W`. Reading its components as
values of the variables `X_S` gives a satisfying solution of `C_M^W(A)`.

Backward map. Take a solution of `C_M^W(A)`. Its variable values are candidate
local states, contain every observation in `A`, agree under every restriction,
and satisfy the cocycle condition. By §3's definition of raw global extension
— T0's raw global knowledge section, read modulo sample presentation — these
values are exactly a raw scoped section over `W` whose restrictions contain
`A`; hence they define an element of `Ext_raw^W(A)`.

The two constructions forget and recover no data: both are the same indexed
family, once read through T0's names. They are inverse.

**Corollary: finite classification and computability.** `Ext_raw^W(A)` is
finite and computable by exhaustive search over:

```
Product_{S in W} D_S^W(A).
```

The product is finite because `W` is finite and each
`D_S^W(A) <= Cand_M^W(A; S)` is finite. Computing the finite support closure
and checking containment, restriction agreement, cocycle coherence, and
legality are finite structural operations inside finite `Str` objects.
Consequently exactly one of the three states in design-problem §4 applies in
scope `W`: empty, singleton, or many.

## 6. What this does and does not discharge

T1 discharges the classification mechanism:

- there is a precise object `Ext_raw^W(A)` for T2 and T3 to quantify over;
- "empty", "singleton", and "many" are not thresholds or scores;
- quotienting by invisible automorphisms is not performed before counting;
- compatibility includes triple cocycle coherence unless a theorem explicitly
  declares a pairwise-truncated scope.

T1 does not discharge:

- **T2:** a structural sufficient condition for `Ext_raw^W(A) = empty`, such
  as incompatible overlap edge/path facts inside `W`;
- **T3:** a structural sufficient condition for `|Ext_raw^W(A)| > 1`, such as
  an unpinned automorphism torsor inside `W`;
- **T4:** correspondence between raw extensions and hidden-world truth;
- **T5-T7:** any claim about the linear thinking field or hardening.

## 7. Bench translations

**E1 fresh-node forgery.** The support closure contains the observed region at
`{0}` but no cross-view identity fact for its fresh nodes. In the canonical
E1 scope the unique supported solution is therefore the observed solo region
with empty overlap components: determined-as-solo, not obstructed and not a
T3 many case. P1 still refuses commitment because cross-view support is
absent. Hypotheses that another view merely failed to sample a counterpart
belong to T4 and do not pad the T1 candidate set.

**E2 solo truth.** Same T1 type as E1: the canonical scoped extension set is
determined-as-solo, while P1 refuses for lack of cross-view support. Whether
the solo reading is externally true is unavailable until T4.

**E2b overlap forgery.** After P2/A1 admits the sampled absent edges as
measured evidence for exact overlap conflicts, T2 shows that the
corresponding `C_M^W(A)` has no solution for any scope `W` containing the
conflict chart. T1 supplies the target statement: `Sol(C_M^W(A)) = empty`.

**E3 orphan merges.** If an overlap-invisible automorphism can move an orphan
merge while preserving all constraints in the relevant scope, `C_M^W(A)` has
multiple raw solutions.
T3 must identify the acting group and quotient inside the relevant scope;
T1 only counts the raw solutions before quotienting.

**E6 vocabulary seam.** A seam repair changes `C_M^W(A)` by adding or
changing span legs between rule/vocabulary objects in the seam scope. The
discrete improvement is a change in the scoped raw solution set, not a
statement about the graded field.

## 8. Downstream results

T2 discharges the zero-solution lemma:

> If two local assignments force incompatible structured facts in a common
> overlap object in `W`, then `Sol(C_M^W(A)) = empty`.

T3 discharges the many-solution lemma:

> If some component has a nontrivial automorphism that is invisible to all
> overlap restrictions and preserves every observed assignment in `A`, then
> `Sol(C_M^W(A))` contains the corresponding orbit, so
> `|Ext_raw^W(A)| > 1`.

These are the first non-tautological mathematical tests of the T0 setup. T2
and T3 prove them in docs/t2-incompatibility.md and
docs/t3-underdetermination.md. T4's identifiability bridge to hidden-world
semantics is discharged after referee review in docs/t4-identifiability.md as
a conditional theorem schema.
