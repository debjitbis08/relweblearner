# T2 — incompatibility implies empty raw extension set

*Written 2026-07-15, after T0 and T1 were discharged. This note proves the
zero-extension side of the classification: when an observation family forces
incompatible structured facts in a common overlap object, the T1 constraint
system has no solution. It does not prove the statistical P2/A1 bridge; that
bridge is already discharged at the measured tier in docs/p2-discharge.md.*

## 1. Status

**Status: discharged after referee review.** Given the discharged T0/T1
setup, T2 states a domain-pinned structural conflict predicate
`Conflict_M^W(A; T)` at an overlap chart `T` and proves:

```
Conflict_M^W(A; T)  =>  Sol(C_M^W(A)) = empty  =>  Ext_raw^W(A) = empty.
```

This is an exact model theorem. It contains no P1 support counting, no
evaluation gold, and no sampling assumption. For E2b, P2/A1 is used only
before T2: it licenses treating a sampled missing backbone edge as measured
evidence for an exact absent edge fact in the overlap object, with the error
rates recorded in docs/p2-discharge.md.

## 2. Inputs inherited from T0/T1

Fix a finite T0 model `M`, a finite observation family `A`, a declared scope
`W`, and the T1 constraint system `C_M^W(A)`.

T2 uses only:

- supported candidate local states `Cand_M^W(A; S)` as model-side image
  subobjects or span images inside finite `M(S)`;
- restriction agreement along arrows `S -> T`;
- triple cocycle coherence where triple overlaps are in scope;
- legality in T0 §6;
- T1's bijection `Ext_raw^W(A) ~= Sol(C_M^W(A))`.

T2 does not inspect hidden benchmark entities, view labels, correspondence
scores, P1 thresholds, or P2 sampling rates.

## 3. Exact structured facts

For a chart or overlap `T`, let a **fact** of `M(T)` be an atomic structured
predicate carried by `Str`, with provenance erased for compatibility:

- node identity on a supported overlap domain;
- edge incidence, orientation, and declared edge predicates such as
  `backbone`;
- exact negative predicates, such as absent edge/path facts, when admitted
  into `M(T)` by a named assumption or measured discharge;
- edge labels or rule/path bodies where the state object carries them;
- composition equations in a semicategory object.

Two facts `p` and `q` in `M(T)` are **incompatible**, written `p #_T q`, when
no legal local state subobject of `M(T)` can contain both. This definition is
structural and independent of the observation family; supported candidates
are a subset of these legal local states. Examples:

- the same supported source node maps to two distinct target nodes;
- a required edge/path fact and an exact absent-edge/path fact concern the
  same endpoints/body;
- two labels on the same oriented edge disagree in a functional label
  component;
- two composed paths force distinct results in a semicategory object.

This is a structural predicate in `Str`. It is not a low score and not a
policy verdict.

## 4. Forced facts

An observation family `A` **forces** a fact `p` at chart `T` if every solution
of the containment, restriction-agreement, and restriction-legality
constraints must include `p` in `X_T`.

For T2 it is enough to use two syntactic forcing cases:

**Direct forcing.** `(T, s) in A` and `s` contains `p`.

**Domain-pinned restriction forcing.** `(S, s) in A`, there is an arrow
`S -> T`, the span-valued restriction of `s` to `T` is defined on the support
of `p` and contains `p`, and the support of `p` is pinned in `T` by a directly
forced fact `r` at `T` whose support contains the support of `p`.

The pinning condition is necessary because T1's restriction agreement is
symmetric on the common defined domain: if `X_T` may omit the support of `p`,
agreement is vacuous there. A directly forced fact at `T` pins that support
inside `dom(X_T)`, so restriction agreement forces `p` into `X_T`.

More elaborate closure rules may be added later, but they must remain
structural consequences of T0 restrictions and legal maps. They may not use
P1 or P2 as inference rules.

## 5. The conflict predicate

For an overlap chart `T`, define:

```
Conflict_M^W(A; T)
```

to mean that there exist facts `p` and `q` in `M(T)` such that:

- `T` is in the scope `W`;
- `A` forces `p` at `T`;
- `A` forces `q` at `T`;
- `p #_T q`.

For triple conflicts, take `T = {i,j,k}` only when the incompatible facts are
directly forced or domain-pinned-restriction forced there. Pairwise-compatible
but cocycle-incoherent gluings that require deriving new composed facts need
an additional composition-closure forcing rule; that extension is named in
§9 and is not part of T2 v1.

## 6. The theorem

**Theorem T2.** If `Conflict_M^W(A; T)` holds for some overlap chart `T`, then:

```
Sol(C_M^W(A)) = empty.
```

By T1, `Ext_raw^W(A) = empty`.

**Proof.**

Assume for contradiction that `X in Sol(C_M^W(A))`.

If a fact is directly forced at `T`, containment gives that fact in `X_T`.
If a fact is domain-pinned-restriction forced from some `S`, containment gives
the source fact in `X_S` and the pinning fact in `X_T`; hence the support of
the restricted fact lies in the common defined domain of
`res_{S,T}(X_S)` and `X_T`. T1's restriction-agreement clause then gives the
restricted fact in `X_T`.

Applying this to the two facts in `Conflict_M^W(A; T)`, we get `p in X_T` and
`q in X_T`.

But `p #_T q` means no legal local state in `M(T)` can contain both `p` and
`q`. T1 requires `X_T in Cand_M^W(A; T)`, and every supported candidate is a
legal local state. Contradiction. Therefore no solution exists. T1's
bijection then gives `Ext_raw^W(A) = empty`.

The triple-overlap case is identical when the facts are already forced in
the triple chart by direct or domain-pinned restriction forcing.

## 7. Boundary cases

**Absence of overlap is not conflict.** If no restriction domain reaches the
support of `p`, then `p` is not forced at the overlap chart. E1 fresh-node
forgeries and E2 solo truths therefore do not satisfy `Conflict_M`; their
canonical scoped state is determined-as-solo and their refusal remains P1,
not T2 or T3.

**Unmapped alternatives are not conflict.** Two candidate placements in an
overlap-invisible component may be distinct without being incompatible. That
is the T3 many-extension case.

**Policy readings are upstream.** P2/A1 may turn a sampled detector verdict
into an exact absent-edge fact with measured error. Once that exact fact is
admitted into `A`, T2 is structural. Without that admission, a missing sampled
edge is not a T2 conflict.

**Composed facts are not automatic.** T2 v1 does not derive new path or
composition facts from several observations. If a GraphLog or holonomy case
needs such derived facts, the observation family must already contain them or
a later composition-closure forcing rule must be added.

**Quotients do not rescue conflict.** T2 is about `Ext_raw^W(A)`. If no raw
section exists, quotienting by invisible automorphisms cannot create one.

**Scope monotonicity.** If a conflict occurs inside a scope `W`, then every
larger scope `W'` containing the same conflict chart is empty as well. The
same direct or domain-pinned forcing witnesses remain present in `W'`, and
the structural incompatibility in `M(T)` is unchanged, so T2 applies directly
in `W'`. This argument does not rely on unsupported variation outside `W`.

## 8. Bench translations

**E1 fresh-node forgery.** No overlap chart is forced to contain facts about
the forged nodes. `Conflict_M^W` is false. T2 does not reject it; P1 refuses
commitment for absent cross-view support after T1 classifies the canonical
scoped state as determined-as-solo.

**E2 solo truth.** Same T2 type as E1. The solo truth has no forced conflict
in an overlap object, so T2 is silent.

**E2b overlap forgery.** The false merge forces bridge facts through the
overlap mapping. Under the measured P2/A1 semantics, the sampled absent
backbone image is admitted as an exact absent-edge fact in the target overlap
object. The required bridge edge and exact absent-edge fact are incompatible,
and the exact absent-edge fact directly pins the same overlap support, so
`Conflict_M^W(A; {i,j})` holds for every scope `W` containing `{i,j}`, and T2
gives `Ext_raw^W(A) = empty` at the measured tier of the declared E2b process.

**GraphLog destructive interference.** A proposed gluing that makes composed
paths assert contradicted triples is covered by T2 v1 only when the
incompatible path/composition facts are already present as exact observed or
domain-pinned restricted facts. If they must be derived by composing several
forced facts, that is the composition-closure extension named in §9.

**D2 loop lie / holonomy.** When loop data force incompatible composed facts
inside the relevant chart or triple overlap as exact observed facts, the same
theorem applies. If the loop is represented only in the later linear layer,
or if the contradiction requires an unproved composition-closure rule, T2 v1
does not see it until the discrete structured facts are present in `A`.

## 9. Relation to T3 and the open composition extension

T2 proves only the zero case. T3 now proves the corresponding sufficient
condition for the many case:

> If the overlap restrictions fail to pin a component and a nontrivial
> automorphism preserves every forced fact in scope, then `Ext_raw^W(A)` has multiple raw
> sections.

That is discharged in docs/t3-underdetermination.md. In particular, T2 must
not be used to reject fresh-node
forgeries, solo truths, or orphan alternatives that lack a forced
incompatible fact in an overlap object.

One T2-side extension also remains open: a composition-closure forcing rule
for semicategory and holonomy cases. It should say that candidates in the
relevant structured objects are closed under declared composition, so
composites of already forced facts are themselves forced. Because that
closure changes `Prop_M^W(A; S)` and `Cand_M^W(A; S)`, it needs a T1
compatibility check, not just a T2 addendum. Until that rule is stated and
reviewed, T2 v1 covers exact direct and domain-pinned restriction conflicts
only.
