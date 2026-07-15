# T4 — hidden-world identifiability from separating coverage

*Written 2026-07-15, after T0-T3 were discharged. This note is the first
theorem in the chain that mentions external truth. It keeps the distinction
established by T0: T1-T3 classify supported model extensions, while T4 asks
when those extensions determine a hidden-world semantic target. The answer is
conditional on an explicit hidden-state class, exact witnessed answers,
separating coverage, a model/semantic bridge, and known automorphisms. Imagined
states remain hypotheses until observation or deduction supplies support.*

## 1. Status

**Status: discharged after referee review.** For a typed semantic target `Y`,
T4 defines a hidden fiber `Fib_H^Y(A)`, a finite family of covered witness
queries, and a semantics map from scoped T1 outputs to hidden orbits. Under the
assumptions in §5 it proves:

```
Out_M^Y(A) / G_Y  ~=  Fib_H^Y(A) / Gamma_Y  =  { [h_*]_Gamma_Y }.
```

The exact theorem is conditional. It does not claim that the current benches
or a deployment satisfy its coverage, independence, or model-adequacy
assumptions. Section 8 gives a separately scoped probabilistic certificate for
the coverage event; it is not a model-free truth guarantee.

The quotient construction under H3-H5 is standard. T4's substantive
identifiability step is the separating-witness lemma: an application must
construct a witness basis from its hidden model, show the run covered it, and
prove the model/semantic bridge rather than assuming the desired truth label.

## 2. Inputs inherited from T0-T3

Fix:

- a finite T0 view model `M` and finite observation family `A`;
- the canonical T1 support scope `W` or another explicitly declared finite
  scope containing it;
- the supported constraint system `C_M^W(A)` and its finite solution set;
- a typed target `Y` inside `W`, such as one region identity, one vocabulary
  seam, one rule, or another declared output object;
- a target projection `pi_Y` from scoped solutions to finite model outputs.

Define the model-output set:

```
Out_M^Y(A) = { pi_Y(X) : X in Sol(C_M^W(A)) }.
```

Let `Gsol_Y` be a finite subgroup of the T3 automorphisms acting on
`Sol(C_M^W(A))`. To induce an action on outputs, require the target projection
to respect the action's equivalence classes:

```
pi_Y(X) = pi_Y(X')
  => pi_Y(g.X) = pi_Y(g.X')      for every g in Gsol_Y.
```

Then each `g in Gsol_Y` induces a well-defined output permutation:

```
g_Y(pi_Y(X)) = pi_Y(g.X).
```

The inverse of `g_Y` is `(g^{-1})_Y`, because applying their definitions gives
`pi_Y(g^{-1}.g.X) = pi_Y(X)`. Let `G_Y` be the image of `Gsol_Y` in
`Sym(Out_M^Y(A))`. By construction, `G_Y` acts on `Out_M^Y(A)` and `pi_Y` is
equivariant. Only this induced output group appears in the quotient
`Out_M^Y(A) / G_Y`. Proving the projection congruence above is part of an
application's T4 representation obligations; declaring a T3 automorphism
harmless is not enough by itself.

T4 does not replace the T1 trichotomy:

- if `Sol(C_M^W(A))` is empty, T2 has priority and there is no model output to
  identify;
- if it is singleton, the output is determined by the view model but may
  still have demonstrated hidden multiplicity or uncertified hidden
  identifiability;
- if it is many, T3 may organize some or all of the variation into `G_Y`
  orbits, and T4 asks whether the quotient has one semantic meaning.

P1 remains an external commitment policy. T4 identifiability can permit a
truth claim without forcing P1 to commit, and P1 support cannot substitute for
the assumptions below.

## 3. Hidden states and witness queries

For target `Y`, declare a finite hidden-state class `H_Y`. It is part of the
theorem statement, not data available to the learner. Its elements are
possible hidden-world semantic structures at the same object level as `Y`.

Let `Gamma_Y` be the known group of semantically harmless hidden-world
automorphisms. T4 can identify at most an orbit `[h]_Gamma_Y`; opaque-id
renamings, coordinate gauge, or another declared semantic symmetry must not be
reported as distinct truths.

Declare a finite witness-query family `Q_Y`. A query `q in Q_Y` has a finite
answer set and a hidden answer:

```
sig_h(q) in Ans(q),  h in H_Y.
```

Examples include:

- whether two co-witnessed nodes denote the same hidden entity;
- whether a target edge/path or its exact negation holds;
- the label or composite of a declared rule/path;
- whether two vocabulary positions share one hidden semantic role.

Queries must be invariant under `Gamma_Y`, precisely:

```
sig_{gamma.h}(q) = sig_h(q)
  for every gamma in Gamma_Y, h in H_Y, and q in Q_Y.
```

They ask about semantic structure, not hidden benchmark ids or a preferred
representative. This invariance makes `Fib_H^Y(A)` a union of `Gamma_Y` orbits,
so its quotient is well-defined. Together with H1, it also places the entire
true orbit `Gamma_Y.h_*` in the hidden fiber.

The observation and legal-propagation pipeline determines a subset
`Cov_A <= Q_Y` of **covered queries** and an answer `ans_A(q)` for each
`q in Cov_A`. A covered answer must be pinned by observed or legally propagated
provenance in the T1 scope. An unsupported guess, a score threshold by itself,
or an imagined state is not a covered answer. The declared observation model
also states how many provenance-distinct views or origins are required before
a query enters `Cov_A`; this is `k_q` in §8.

The hidden fiber consistent with those exact answers is:

```
Fib_H^Y(A) = {
  h in H_Y : sig_h(q) = ans_A(q) for every q in Cov_A
}.
```

This is an analysis object. Computing it may be impossible in a deployment;
the theorem only states what follows if the declared hidden class and witness
semantics are valid.

## 4. Imagined states

The system may maintain a hypothesis set `Hyp_H^Y(A)` containing hidden states
that could explain the current observations. In the exact finite setting it
may use `Fib_H^Y(A)`; a generative implementation may attach likelihoods or
include a broader prior-supported set.

Hypotheses have provenance class `hypothetical`, distinct from:

- `observed`: produced directly by the declared observation pipeline;
- `derived`: obtained by a declared truth-preserving T0 propagation rule.

Hypothetical facts may guide simulation, prediction, or selection of the next
view/query. They do not enter `Prop_M^W(A; S)`, do not enlarge
`Cand_M^W(A; S)`, do not count as P1 support, and do not become commitments.
A hypothesis is promoted only when a new observation supplies its fact or a
declared deductive rule derives it; the resulting fact receives new observed
or derived provenance.

This adds a hidden-world certification axis alongside the T1 trichotomy. Two
reports must remain distinct:

```
model determined, hidden multiplicity demonstrated
model determined, hidden identifiability uncertified
```

The first requires an exhibited result
`|Fib_H^Y(A) / Gamma_Y| > 1`. The second means the system cannot establish the
H1-H2 certificate or the H3-H5 bridge; it makes no cardinality claim about an
uncomputed hidden fiber. E1/E2 require the uncertified report at runtime. A
deployment must not turn failure to certify singleton into proof of
multiplicity.

## 5. T4 assumptions

Fix an actual hidden state `h_* in H_Y`. T4 uses assumptions named `H1-H5` to
avoid collision with the E2b process's assumption `A1`.

**H1. Well-specified realization.** The observation family `A` was generated
from `h_*` by the declared observation process, and every covered answer is
exact:

```
ans_A(q) = sig_{h_*}(q),  q in Cov_A.
```

If an operational detector has measured false-positive or false-negative
rates, H1 holds only on its declared correctness event. P2's measured E2b
discharge is not silently promoted to an exact universal premise.

**H2. Separating coverage.** This assumption is the conjunction of two
clauses. First, the declared hidden model supplies a finite separating basis
`Q_sep(h_*) <= Q_Y`, fixed independently of which queries the run happens to
cover, such that:

```
for every h in H_Y with h notin Gamma_Y.h_*,
there exists q in Q_sep(h_*) such that sig_h(q) != sig_{h_*}(q).
```

Second, the run satisfies the coverage event:

```
Q_sep(h_*) <= Cov_A.
```

This is weaker than observing the whole hidden world: only a predeclared
distinguishing witness family is required. It is stronger than merely seeing
the target once. An application must construct this basis from its hidden-state
model, not select it after consulting evaluation outcomes.

**H3. Model semantic soundness.** There is a well-defined semantics map:

```
rho_Y: Out_M^Y(A) -> Fib_H^Y(A) / Gamma_Y
```

and every model output maps to a hidden orbit consistent with the covered
answers. This forbids a structurally compatible T1 output from being assigned
a semantic interpretation that the declared hidden model cannot realize.

**H4. Model semantic completeness.** Every hidden orbit in
`Fib_H^Y(A) / Gamma_Y` is represented by at least one model output. This says
the chosen T0 state objects and target projection can express every
observation-compatible semantic alternative in the declared hidden class.

**H5. Automorphism alignment.** For outputs `y, y' in Out_M^Y(A)`:

```
rho_Y(y) = rho_Y(y')  iff  y' is in G_Y.y.
```

Thus the fibers of `rho_Y` are exactly the model automorphism orbits declared
semantically harmless. A larger `G_Y` would collapse genuinely different
meanings; a smaller one would report coordinate or opaque-id choices as
different truths.

H3-H5 are model-validation obligations. They cannot be established with
evaluation gold inserted into `M`; they require a separate proof that the T0
representation and target projection implement the declared witness
semantics.

## 6. Separating-witness lemma

**Lemma.** Under H1 and H2:

```
Fib_H^Y(A) = Gamma_Y.h_*,
Fib_H^Y(A) / Gamma_Y = { [h_*]_Gamma_Y }.
```

**Proof.** H1 gives `h_* in Fib_H^Y(A)`. Query invariance then gives
`Gamma_Y.h_* <= Fib_H^Y(A)`. Suppose another `h in Fib_H^Y(A)` is not in that
orbit. H2's separation clause supplies `q in Q_sep(h_*)` with
`sig_h(q) != sig_{h_*}(q)`, and H2's coverage clause gives `q in Cov_A`. Since
both states are in the hidden fiber, each answer must equal `ans_A(q)`,
contradicting the inequality. Therefore no state outside the true orbit lies
in the fiber, proving both displayed equalities.

The lemma's content is the separating witness. It does not assume an injective
observation map under another name; an application must exhibit the covered
query that distinguishes each competing orbit or prove a finite family does.

## 7. Modular results and the theorem

**Proposition: model/semantic quotient bridge.** Under H3-H5, without assuming
H1 or H2, the declared semantics map induces a bijection:

```
bar(rho_Y): Out_M^Y(A) / G_Y -> Fib_H^Y(A) / Gamma_Y.
```

**Proof.** H3 makes `rho_Y` a well-defined map into the hidden-orbit fiber.
H4 makes it surjective. H5 says precisely that two model outputs have the same
image exactly when they lie in the same `G_Y` orbit, so `rho_Y` descends to an
injective map on the quotient. The induced map is therefore a bijection.

Here H4 is essential: before separating coverage is imposed, the hidden fiber
may contain several semantic orbits, and H4 requires the T0/T1 output language
to represent all of them. H3-H5 are reusable representation results; they do
not identify which orbit is true.

**Theorem T4: hidden-world identifiability.** Under H1-H5, combine the quotient
bridge with the separating-witness lemma to obtain:

```
Out_M^Y(A) / G_Y
  ~= Fib_H^Y(A) / Gamma_Y
  = { [h_*]_Gamma_Y }.
```

**Proof.** The proposition identifies the model quotient with the hidden
fiber quotient under H3-H5. The lemma identifies that hidden quotient with the
singleton true orbit under H1-H2.

**Corollary: output soundness needs less than correspondence.** Under H1, H2,
and H3, every existing model output maps to `[h_*]_Gamma_Y`. H4 and H5 are
needed for the coverage-independent quotient bridge, not merely to show that
an existing semantically sound output has the identified meaning.

**Corollary: raw-many can still be semantically identified.** If T3 gives
multiple raw outputs but they form one `G_Y` orbit and H1-H5 hold, T4
identifies one hidden semantic orbit. Raw multiplicity remains visible for
audit; it is not erased before T3/T4 establish why the quotient is harmless
for `Y`.

**Non-corollary: singleton is not truth.** If T1 gives one model output but H1,
H2, or H3-H5 fail, no hidden-world identification follows. Structural
uniqueness and semantic identifiability are different claims.

## 8. Probabilistic coverage certificate

The exact theorem conditions on H1-H2. A sampling model may provide a
probability that those conditions hold, but the model and its scope must be
named.

Use the finite separating witness basis `Q_sep(h_*)` declared in H2. Its
separation property is a fact about the hidden-state model; sampling determines
whether the run covers it.

For each witness `q`, let `V_q` be the views capable of observing it. Let
`Z_{i,q}` indicate that view `i` produces a valid, provenance-distinct witness
and that the declared pipeline ingests it. Let `k_q` be the required number of
distinct views. P1-style corroboration uses `k_q = 2`; another theorem may
declare a different requirement. Pipeline completeness for this certificate
is the implication:

```
sum_{i in V_q} Z_{i,q} >= k_q  =>  q in Cov_A.
```

If `Z_{i,q}` is defined before ingestion, the sampling model must include a
dropout term; otherwise the coverage-failure bound below is optimistic.

Assume only that, for each fixed `q`, the variables `(Z_{i,q})_{i in V_q}` are
conditionally independent given `h_*` and the declared sampling regime, with:

```
P(Z_{i,q} = 1 | h_*) = p_{i,q}.
```

Then the probability that `q` fails its coverage requirement is the
Poisson-binomial lower tail:

```
m_q = P(sum_{i in V_q} Z_{i,q} < k_q | h_*).
```

No independence across different queries is required. By the union bound:

```
P(some q in Q_sep(h_*) is not covered | h_*)
  <= sum_{q in Q_sep(h_*)} m_q.
```

If exact-answer soundness fails with probability at most `delta_sound`, then:

```
P(T4's H1-H2 certificate fails | h_*)
  <= delta_sound + sum_q m_q.
```

This is a sufficient bound, not an equality and not a claim about the current
benches. Shared episodes, shared owners, adaptive selection, or correlated
view failures invalidate the conditional-independence calculation unless the
declared process models them. Distinct view labels are not enough; provenance
must establish distinct information origins.

The bound certifies only H1-H2. H3-H5 remain separate representation proofs;
no sampling probability can establish model soundness, completeness, or
automorphism alignment.

All displayed probabilities are conditional on the unknown `h_*` and are not
directly reportable as one deployment number. A deployable certificate must
either use one uniform separating basis valid for every `h in H_Y`, or declare
the family `{Q_sep(h)}_{h in H_Y}` and report a uniform bound such as:

```
sup_{h in H_Y} [ delta_sound(h) + sum_{q in Q_sep(h)} m_q(h) ].
```

A plug-in bound for one favored hypothesis is hypothesis-conditional, not a
uniform identifiability certificate, and must be labeled accordingly.

If a witness is observable in fewer than `k_q` genuinely independent views,
then `m_q = 1`. T4 cannot certify that target under that policy. This is the
formal cost of P1's deliberate refusal of unshared truths.

## 9. Boundary cases

**T2 empty case.** If `Sol(C_M^W(A)) = empty`, `Out_M^Y(A)` is empty and T4
does not manufacture a hidden interpretation. For E2b, the P2/A1 bridge keeps
its measured error and intervention scope.

**T1 singleton with demonstrated hidden multiplicity.** A singleton supported
solo reading can coexist with several hidden orbits when those alternatives
are explicitly exhibited in `Fib_H^Y(A)`. That is hidden multiplicity despite
model determination.

**Coverage certificate unavailable.** Failure to establish H1-H2 does not by
itself exhibit a second hidden orbit. The correct report is hidden
identifiability uncertified, not hidden multiplicity demonstrated.

**T3 orbit.** Multiple raw extensions can identify one semantic orbit only
when H5 aligns the entire relevant T3 orbit with `Gamma_Y`. Merely calling an
automorphism "invisible" is insufficient.

**Coherent lie or collusion.** If shared-origin witnesses fail the declared
provenance-distinctness gate, the separating basis is not covered and H2
fails. If colluding witnesses pass that gate but report a false covered answer,
H1 fails. Conditional independence belongs only to §8's probability
certificate, not to H2 itself.

**Model misspecification.** If the true state is not in `H_Y`, H1 fails. If
the T0 objects cannot represent an admissible hidden alternative, H4 fails.
Neither failure may be repaired by deleting the alternative from the model
after seeing evaluation gold.

**Adaptive sensing.** A view or query selected from earlier observations may
still be valid, but the probability model must condition on that selection.
Naive iid witness counts are not licensed.

**Object level.** Coverage of one region does not identify a whole knowledge
state. Every T4 claim must name `Y`, `W`, `H_Y`, `Q_Y`, and both automorphism
groups.

## 10. Bench translations

**E1 fresh-node forgery.** T1 gives the singleton solo reading and P1 refuses.
T4 cannot call the region true: relative to the hidden benchmark semantics,
the forged local structure violates at least the well-specified-realization or
model-semantic bridge assumptions, but that fact is visible only to
evaluation. Runtime observations provide no separating witness, so the runtime
report is hidden identifiability uncertified, not demonstrated multiplicity.

**E2 solo truth.** T1 again gives the singleton solo reading and P1 refuses.
The actual region is true in evaluation, but a `k = 2` coverage certificate is
impossible for a genuinely single-view target, so T4 reports hidden
identifiability uncertified rather than demonstrated multiplicity. E1 and E2
therefore remain operationally identical.

**E2b overlap forgery.** Under the declared E2b process, T2 gives an empty
extension set at measured error rates. T4 is downstream and silent; it does
not turn that measured process-specific result into universal truth.

**E3 orphan merges.** T3 supplies multiple supported raw extensions. T4 may
identify the hidden target up to automorphism only if the orphan orbit is the
full fiber of `rho_Y` and matches the declared semantic group `Gamma_Y` as H5
requires. The recorded zero real mispairings are evidence for that model, not
a proof of H5.

**E6 vocabulary seam.** A catastrophic view draw can miss every witness for a
semantic distinction. Then H2 fails and T4 reports hidden identifiability
uncertified; graded agreement or a low residual cannot replace the missing
witness.

## 11. What T4 does and does not discharge

T4 supplies:

- a typed hidden fiber separate from T1's model extension set;
- a concrete separating-witness condition for hidden identifiability;
- an explicit quotient bridge between model and semantic automorphisms;
- a probabilistic coverage certificate with its independence scope exposed;
- a formal home for imagined states that does not contaminate T1-T3 support.

T4 does not supply:

- a universal coverage theorem for the existing benches or deployment;
- validation of `H_Y`, `Q_Y`, `rho_Y`, `Gamma_Y`, or conditional independence;
- a model-free guarantee that corroboration is true rather than collusive;
- the T2 composition-closure extension;
- any T5-T7 claim about the linear thinking field, enrichment, or hardening.

T4 is discharged as a conditional theorem schema. Each application must still
instantiate and validate H1-H5; no bench, deployment, or other external-truth
claim is discharged merely by this theorem-level result.

T5's anchored harmonic thinking operator is discharged after referee review in
docs/t5-thinking-operator.md. T6 enrichment soundness is discharged after
referee review in docs/t6-enrichment-soundness.md. T7 stable commitment is
discharged after referee review in docs/t7-stable-commitment.md. The designed
T0-T7 theory chain is closed, subject to application-level instantiation.
