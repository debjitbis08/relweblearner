# T1 — extension classification over the T0 descent model

*Written 2026-07-15, after T0 was discharged by second referee pass. This
note proves only the classification layer: for a finite family of observed
assignments `A`, the raw extension set is a finite, explicitly defined
compatibility solution set, and its cardinality gives the three
design-problem states.
It does not yet prove the T2 zero-extension criterion or the T3
automorphism/torsor criterion.*

## 1. Status

**Status: discharged after referee review.** Given the T0 data
`(N(V), M, Assign, legal maps)`, T1 defines a finite constraint system
`C_M(A)` for any finite observation family `A` and proves:

```
Ext_raw(A) ~= Sol(C_M(A))
```

Therefore exactly one of the three cases holds:

- `Sol(C_M(A)) = empty`: obstructed / incompatible;
- `|Sol(C_M(A))| = 1`: determined relative to the view model;
- `|Sol(C_M(A))| > 1`: underdetermined / provisional.

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

## 3. Observation families and candidate states

Let `A = {(S_alpha, s_alpha)}` be a finite family of observed assignments,
possibly at several charts and overlaps. The singleton case from T0 is the
special case `A = {(S0, s)}`. E2b-style situations use the general case:
view assignments and overlap evidence enter the same containment list.

T1 now separates observed assignments from model-side candidates.

For each cover object `S`, define `Cand_M(S)` to be the finite set of
candidate local states at `S`:

- finite legal subobjects of the finite state object `M(S)`, with provenance
  inherited from observed support where present;
- finite legal span subobjects internal to `M(S)` for partial
  correspondences at overlap charts;
- the empty candidate.

Two presentations with different external sample objects but the same image
subobject or same span image inside `M(S)`, with the same provenance labels,
are one candidate. T1 therefore counts model-side raw states, not syntactic
sample presentations. This is the commitment-relevant choice: presentation
multiplicity never turns a singleton model state into `|Ext_raw| > 1`.

`Cand_M(S)` is finite because `M(S)` is finite: it has finitely many
subobjects, finitely many span-image subobjects, and finitely many provenance
labels in the finite observation family under consideration.

A raw global extension of `A` is a family `(x_S)_S` with one candidate local
state for every cover object `S`, such that:

- each `x_S` lies in `Cand_M(S)`;
- every observed `s_alpha` at chart `S_alpha` is contained in `x_{S_alpha}`
  as an image subobject or span image;
- every restriction arrow `S -> T` carries `x_S` to the same candidate
  substate as `x_T` on their common domain;
- every triple overlap satisfies the T0 cocycle condition.

To classify these extensions, introduce one finite variable `X_S` for each
cover object `S`. The domain of `X_S` is the finite set:

```
D_S(A) = { x in Cand_M(S) : x contains every observed s_alpha in A
           with S_alpha = S }.
```

For charts not touched by `A`, this is just `Cand_M(S)`. Every `Cand_M(S)`
contains the empty candidate, so unused charts and higher overlaps never
obstruct by mere absence of observation.

## 4. The constraint system C_M(A)

`C_M(A)` is the conjunction of four finite constraint families.

**Containment.** For every observed assignment `(S_alpha, s_alpha) in A`,
`X_{S_alpha}` contains `s_alpha`.

**Restriction agreement.** For every arrow `S -> T` in `N(V)`, the two
restricted assignments agree on the common defined domain:

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
`C_M(A)`. P2 enters only by changing which sampled detector verdicts are
admitted as measured evidence for an exact overlap conflict in T2.

## 5. The theorem

**Theorem T1.** For every finite T0 model `M` and every finite observation
family `A`, there is a canonical bijection:

```
Ext_raw(A) <-> Sol(C_M(A)).
```

**Proof.**

Forward map. Take a raw global extension `e in Ext_raw(A)`. By the definition
above, `e` is a family of candidate local states over the cover nerve,
contains every observation in `A`, agrees under all restrictions, and
satisfies the triple cocycle condition. Reading its components as values of
the variables `X_S` gives a satisfying solution of `C_M(A)`.

Backward map. Take a solution of `C_M(A)`. Its variable values are candidate
local states, contain every observation in `A`, agree under every restriction,
and satisfy the cocycle condition. By §3's definition of raw global extension
— T0's raw global knowledge section, read modulo sample presentation — these
values are exactly a raw global section whose restrictions
contain `A`; hence they define an element of `Ext_raw(A)`.

The two constructions forget and recover no data: both are the same indexed
family, once read through T0's names. They are inverse.

**Corollary: finite classification and computability.** `Ext_raw(A)` is
finite and computable by exhaustive search over:

```
Product_S D_S(A).
```

The product is finite because `N(V)` is finite and each `D_S(A) <= Cand_M(S)`
is finite. Checking containment, restriction agreement, cocycle coherence,
and legality is finite structural comparison inside finite `Str` objects.
Consequently exactly one of the three states in design-problem §4 applies:
empty, singleton, or many.

## 6. What this does and does not discharge

T1 discharges the classification mechanism:

- there is a precise object `Ext_raw(A)` for T2 and T3 to quantify over;
- "empty", "singleton", and "many" are not thresholds or scores;
- quotienting by invisible automorphisms is not performed before counting;
- compatibility includes triple cocycle coherence unless a theorem explicitly
  declares a pairwise-truncated scope.

T1 does not discharge:

- **T2:** a structural sufficient condition for `Ext_raw(A) = empty`, such as
  incompatible overlap edge/path facts;
- **T3:** a structural sufficient condition for `|Ext_raw(A)| > 1`, such as
  an unpinned automorphism torsor;
- **T4:** correspondence between raw extensions and hidden-world truth;
- **T5-T7:** any claim about the linear thinking field or hardening.

## 7. Bench translations

**E1 fresh-node forgery.** `C_M(A)` has no contradiction constraints because
the forged nodes have no overlap-domain assignments. Its non-commitment is
not a T1 empty case; it is classified as many if the unobserved cross-view
placements vary, and P1 then refuses commitment.

**E2 solo truth.** Same T1 type as E1: no contradiction constraints and many
raw completions relative to the view model. Truth is unavailable until T4.

**E2b overlap forgery.** After P2/A1 admits the sampled absent edges as
measured evidence for exact overlap conflicts, T2 should show that the
corresponding `C_M(A)` has no solution. T1 supplies the target statement:
`Sol(C_M(A)) = empty`.

**E3 orphan merges.** If an overlap-invisible automorphism can move an orphan
merge while preserving all constraints, `C_M(A)` has multiple raw solutions.
T3 must identify the acting group and quotient; T1 only counts the raw
solutions before quotienting.

**E6 vocabulary seam.** A seam repair changes `C_M(A)` by adding or changing
span legs between rule/vocabulary objects. The discrete improvement is a
change in the raw solution set, not a statement about the graded field.

## 8. Immediate next proof obligations

T2 should prove a zero-solution lemma:

> If two local assignments force incompatible structured facts in a common
> overlap object, then `Sol(C_M(A)) = empty`.

T3 should prove a many-solution lemma:

> If some component has a nontrivial automorphism that is invisible to all
> overlap restrictions and preserves every observed assignment in `A`, then
> `Sol(C_M(A))` contains the corresponding orbit, so `|Ext_raw(A)| > 1`.

Those are the first non-tautological mathematical tests of the T0 setup.
