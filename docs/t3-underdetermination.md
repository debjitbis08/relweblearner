# T3 — underdetermination from overlap-invisible automorphisms

*Written 2026-07-15, after T0, T1, and T2 were discharged; revised after
referee review exposed the need for scoped counting and supported candidate
states. This note proves the many-extension side of the classification: an
ambient automorphism of the scoped model that fixes observations, preserves
their deductive support closure, and is invisible to overlap restrictions
carries scoped solutions to scoped solutions. If its action is nontrivial,
the scoped raw extension set has more than one element. It does not identify
raw extensions with external truth; T4 carries that.*

## 1. Status

**Status: discharged after referee review.** Given the discharged T0/T2 setup
and T1's scoped-counting and supported-candidate amendments, T3 states an
ambient unpinned-automorphism predicate `UnpinnedAut_M^W(A; G)` and proves:

```
X in Sol(C_M^W(A)) and nontrivial g in G
  => g.X in Sol(C_M^W(A)) and g.X != X
  => |Sol(C_M^W(A))| > 1
  => |Ext_raw^W(A)| > 1.
```

This is an exact model theorem. It contains no P1 support counting, no
evaluation gold, and no claim that the quotient class is externally true.
P1 may still refuse commitment when the scoped raw set has many elements.

## 2. Inputs inherited from T0/T1/T2

Fix a finite T0 model `M`, a finite observation family `A`, a declared scope
`W`, and the T1 constraint system `C_M^W(A)`.

T3 uses:

- supported candidate local states `Cand_M^W(A; S)` for `S in W`;
- scoped raw solution families `X = (X_S)_{S in W} in Sol(C_M^W(A))`;
- restriction agreement and cocycle coherence from T1;
- exact incompatibility only negatively: if T2 gives
  `Sol(C_M^W(A)) = empty`, there is no solution for T3 to move;
- raw-before-quotient counting from T0/T1.

T3 assumes at least one scoped raw solution exists. It proves many, not
existence.

## 3. Ambient automorphisms over a scope

For a scope `W`, an **ambient automorphism family** is a family:

```
g = (g_S: M(S) -> M(S))_{S in W}
```

where each `g_S` is a structure-preserving automorphism of the ambient state
object `M(S)`.

`g` is legal over `W` when it preserves every structure carried by `Str`:

- incidence, orientation, labels/rule bodies, declared edge predicates, and
  exact negative predicates;
- provenance labels on observed support;
- composition facts where the state object carries them;
- every declared restriction, span-leg, and structural propagation rule,
  including its provenance transformation.

Because `g` fixes the observed support and commutes with each propagation
rule, induction on finite derivations gives:

```
g_S(Prop_M^W(A; S)) = Prop_M^W(A; S).
```

Consequently `g_S` sends each supported candidate in `Cand_M^W(A; S)` to
another supported candidate. Candidate preservation is therefore a
consequence of ambient structural preservation, not a restatement of solution
preservation.

The action on a scoped solution is:

```
(g.X)_S = g_S(X_S).
```

This fixes the type error in the first T3 draft: `g_S` is not a bijection
from one candidate to another; it is an automorphism of the ambient state
object that sends candidate image subobjects/span images to candidate
image subobjects/span images.

## 4. Invisible to the cover

An ambient automorphism family `g` is **invisible to the cover in scope W**
when:

- for every observation `(S_alpha, s_alpha) in A`, `g_{S_alpha}` fixes the
  image support and provenance labels of `s_alpha` pointwise;
- for every restriction arrow `S -> T` in `W`, `g_S` and `g_T` commute with
  the span-valued restriction on every common defined domain:

  ```
  res_{S,T}(g_S(x))|_C = g_T(res_{S,T}(x))|_C
  ```

  for every candidate `x`, with `C` the common defined domain used by T1;
- on every pinned overlap support, `g_T` is the identity;
- for every triple overlap in `W`, the induced maps commute with the two
  composites used in the T1 cocycle condition.

These clauses are structural and locally checkable from the support of `g`.
They imply that applying `g` cannot change any observed support, span apex
domain, pinned overlap fact, or cocycle comparison inside `W`.

## 5. The predicate

For a finite group `G <= Product_{S in W} Aut(M(S))`, define:

```
UnpinnedAut_M^W(A; G)
```

to mean:

- every `g in G` is legal over `W`;
- every `g in G` is invisible to the cover in `W`;
- there exists a solution `X in Sol(C_M^W(A))`;
- the action is nontrivial on scoped raw solutions: for some `g in G` and
  some solution `X`, `g.X != X` as a model-side image subobject/span-image
  family, counted by T1's sample-presentation convention.

The groupoid option from the earlier draft is dropped. T3 needs only a
subgroup of ambient automorphisms over the declared scope.

## 6. Preservation lemma

**Lemma.** If `UnpinnedAut_M^W(A; G)` holds, `X in Sol(C_M^W(A))`, and
`g in G`, then:

```
g.X in Sol(C_M^W(A)).
```

**Proof.**

Containment: `X` contains every observation in `A`. Since `g` fixes every
observed image support and provenance label pointwise, `g.X` contains the
same observations.

Restriction agreement: for every arrow `S -> T` in `W`, `X` satisfies T1's
symmetric agreement on the common defined domain `C`. Since automorphisms
carry domains to domains, the common defined domain for the pair
`(res_{S,T}((g.X)_S), (g.X)_T)` is `g_T(C)`; commutation with the span-valued
restriction then transports the agreement equality from `C` to `g_T(C)`.

Cocycle coherence: for every triple overlap in `W`, `X` satisfies the T1
cocycle condition. Since `g` commutes with the relevant composites, the
transformed family `g.X` satisfies the same condition.

Legality: each `g_S` preserves the `Str` structure and the declared
propagation rules. The support-closure argument in §3 therefore sends
supported candidates to supported candidates. Thus every component of `g.X`
lies in the appropriate `Cand_M^W(A; S)`.

Therefore `g.X` satisfies all clauses of `C_M^W(A)`.

## 7. The theorem

**Theorem T3.** If `UnpinnedAut_M^W(A; G)` holds and the action is nontrivial,
then:

```
|Sol(C_M^W(A))| > 1.
```

By T1, `|Ext_raw^W(A)| > 1`.

**Proof.**

By nontriviality, choose `X in Sol(C_M^W(A))` and `g in G` with `g.X != X`.
By the preservation lemma, `g.X in Sol(C_M^W(A))`. Thus `X` and `g.X` are two
distinct scoped raw solutions. Hence `|Sol(C_M^W(A))| > 1`, and T1 gives
`|Ext_raw^W(A)| > 1`.

## 8. Orbit and quotient

For a solution `X`, the orbit:

```
G.X = { g.X : g in G }
```

is a subset of `Sol(C_M^W(A))`. If the action is free and transitive on a
fiber of some quotient map, that fiber is a `G`-torsor. T3 does not require
transitivity; it only requires a nontrivial scoped orbit to prove many raw
extensions.

The quotient:

```
Sol(C_M^W(A)) / G
```

records semantic equivalence classes visible after ignoring the unpinned
automorphism. It is not the set P1 counts by default. T0/T1 count scoped raw
solutions first; quotienting is descriptive unless a later theorem proves the
whole scoped raw fiber is harmless for a specified output.

## 9. Boundary cases

**No solution, no T3.** If T2 has proved `Sol(C_M^W(A)) = empty`, no
automorphism can produce underdetermination. T2 wins before T3.

**Out-of-scope variation does not count.** If an automorphism only moves
charts outside `W`, it witnesses nothing about `Ext_raw^W(A)`. This is the
reason T1 introduced scoped counting.

**Unsupported movement does not count.** An ambient automorphism may move
unused atoms of `M(S)`, but if those atoms have no observed or legally
propagated provenance from `A`, they do not occur in
`Cand_M^W(A; S)` and cannot create a raw extension orbit. Imagined
hidden-world alternatives remain T4 hypotheses.

**Trivial automorphism, no many-extension claim.** A symmetry that fixes the
scoped raw model-side image family is not enough. T1 already quotients sample
presentations, so syntactic renamings of the same image subobject do not
create many raw extensions.

**Pinned overlap, no T3 movement.** If moving a component changes a forced
fact in an overlap chart or violates a span leg inside `W`, the automorphism
is not invisible to the cover. The candidate is either illegal or a T2
conflict, not a T3 orbit.

**Truth is still T4.** Many scoped raw extensions mean the view model has not
determined one raw section in `W`. They do not mean all alternatives are
equally true in the hidden world.

## 10. Bench translations

**E1 fresh-node forgery.** T2 is silent because no overlap chart is forced to
contain facts about the forged nodes. The observed fresh nodes generate no
supported cross-view placement, and every T3 automorphism fixes their observed
support pointwise. The canonical scoped extension is therefore the singleton
solo reading; T3 makes no many-extension claim. P1 refuses commitment because
cross-view support is absent.

**E2 solo truth.** Same formal type as E1: determined-as-solo in the scoped
discrete model, with P1 refusal for absent cross-view support. The hidden-world
hypothesis that another view failed to sample a counterpart belongs to T4.

**E2b overlap forgery.** T2 gives `Ext_raw^W(A) = empty` at the measured tier
of the declared E2b process for every scope containing the conflict chart. T3
is silent because there is no scoped raw solution to move.

**E3 orphan merges.** Orphan alternatives are the intended T3 case. The
scope is the region/seam in which the orphan component lives, not the whole
cover. The competing identifications are legally propagated from the same
observed orphan support, so both lie in the T1 support closure. The
overlap-visible structure is fixed, but an unpinned ambient automorphism moves
the orphan component without changing any forced fact. The scoped raw orbit
has multiple elements even if the quotient has one semantic class.

**E6 vocabulary seam.** A seam identity repair pins part of the
rule/vocabulary span. Before repair, the seam scope may admit nontrivial
unpinned automorphisms; after repair, those automorphisms may be killed by
the new span legs. T3 describes the underdetermination side, not the graded
failure mechanism.

## 11. What T0-T3 discharge

- T0 fixes the model/data separation and raw-before-quotient section
  semantics;
- T1 classifies finite observation families by the finite scoped solution set
  `Sol(C_M^W(A))`;
- T2 gives a structural sufficient condition for the zero case;
- T3 gives a structural sufficient condition for the many case.

This gives the formal hooks needed to distinguish the measured cases:

- E1/E2: singleton, determined-as-solo in the canonical scope; T2 and T3 are
  silent, and P1 refuses because cross-view support is absent;
- E2b: empty/incompatible under the measured P2/A1 bridge;
- E3: many scoped raw extensions organized by an unpinned automorphism orbit.

T4's hidden-world identifiability bridge is discharged after referee review in
docs/t4-identifiability.md as a conditional theorem schema. T5's anchored
harmonic operator is discharged after referee review in
docs/t5-thinking-operator.md. T6's local enrichment-comparison theorem is
discharged after referee review in docs/t6-enrichment-soundness.md. The
T7's stable-commitment theorem is discharged after referee review in
docs/t7-stable-commitment.md, closing the designed T0-T7 chain. The named
composition-closure extension remains open if GraphLog/holonomy composed facts
are to be folded into T2 rather than supplied as exact observations.
