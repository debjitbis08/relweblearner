# T7 — certified stable commitment

*Written 2026-07-15, after T0-T6 were discharged. This note states the stable
hardening theorem promised by design-problem D4/T7. It combines target-level
extension classification, the T5/T6 approximation budget, a decision-region
margin, and named policy gates. The result is relative to the declared view
model. It is not an external-truth theorem and does not certify the repository's
current `HARD_SIM` implementation.*

## 1. Status

**Status: discharged after referee review.** T7 proves that a model-permitted
discrete target is unchanged by a declared family of numerical perturbations
when:

```
T6 approximation error + perturbation radius
  < exact decision-region margin.
```

Empty or target-ambiguous extension sets are handled before this inequality.
P1 and other declared policies may still refuse a target that is structurally
determined. T4 premises are still required before calling a stable commitment
externally true.

## 2. The commitment target is structural

Fix a finite observation family `A`, scope `W`, and a declared commitment type
`Y`. Examples are one region identity, one rule head, one path composite, or
one semantic orbit. Let `K_Y` be the finite set of discrete commitments of that
type and let:

```
c_Y: Ext_raw^W(A) -> K_Y
```

be a typed projection from exact supported extensions. The projection must be
invariant under every T3 automorphism declared harmless for `Y`. A preferred
opaque-id representative is not an invariant target.

Define the target set:

```
Tar_Y(A) = {
  c_Y(a) : a in Ext_raw^W(A)
}.
```

This is T1 classification at the object level being committed:

- `Tar_Y(A) = empty`: reject or report obstruction; no score may rescue it;
- `Tar_Y(A) = {k_*}`: `Y` is determined by the view model;
- `|Tar_Y(A)| > 1`: keep `Y` provisional; no score may choose an alternative.

The singleton target case can occur when whole-state extensions differ only
outside `Y` or by automorphisms invisible at `Y`. It does not authorize a more
specific representative. For an orphan orbit, for example, an orbit-level
statement may be determined while a particular cross-view pairing remains
many and uncommittable.

This is a target-level refinement of D4. T7 does not claim that the thinking
field lies near one unique whole-state section when T1 reports many; it requires
the T6 output comparison and exact decision margin to hold uniformly over all
extensions at the committed target.

Let:

```
Permit_P(A, W, Y, k_*) in {false, true}
```

be the conjunction of all declared epistemic policy gates. P1's required
cross-view support belongs here. P2 acts upstream when exact negative overlap
facts are admitted and may make the extension set empty through T2. Neither
policy is inferred from a graded score.

Hypothetical T4 states are not elements of `Ext_raw^W(A)`, do not enlarge
`Tar_Y(A)`, and do not satisfy `Permit_P`. They may guide sensing but cannot be
hardened without new observed or legally derived provenance.

## 3. Decision regions and the exact margin

Fix one T6 derivation DAG `d_Y` whose enriched root lies in a metric output
space `(Z_Y, dist_Y)`. A hardener is a declared map:

```
H_Y: Z_Y -> K_Y union {bottom},
```

where `bottom` means abstain. Its commitment regions are:

```
R_k = {z in Z_Y : H_Y(z) = k}.
```

Assume `Tar_Y(A) = {k_*}`. For each exact extension define its encoded exact
reference output:

```
q_a = iota_Y(Eval_exact(d_Y, a)),

Q_*(A, Y) = {q_a : a in Ext_raw^W(A)}.
```

The exact target margin is:

```
m_Y(A) = Inf_{q in Q_*(A, Y)} distance(q, Z_Y minus R_{k_*}).
```

A positive margin asserts both that every exact reference belongs to the
correct decision region and that it lies away from that region's boundary. It
is uniform over all exact extensions compatible with `A`; selecting the
easiest extension is forbidden.

Let the discharged T6 theorem provide the uniform root approximation budget:

```
E_Y(A) = Sup_{a in Ext_raw^W(A)} E_root(d_Y; a, b).
```

The unperturbed graded output is certified only if:

```
E_Y(A) < m_Y(A).
```

This is already stronger than a fixed score threshold: it includes structural
target determination, exact-reference placement, every T6 comparison defect,
and the distance to every competing or abstaining region.

## 4. Perturbation budgets

T7 permits only perturbations with a proved output-space radius. The radius may
combine field, solver, and evaluator changes, but each term must be named.

### 4.1 Boundary perturbations

For a fixed unique T5 operator and boundary change `db`, T5 §6 gives:

```
||dx_U|| <= kappa_B ||db||,

kappa_B = ||Delta_UU^{-1} Delta_UB||.
```

Because the full field also contains the changed boundary coordinates:

```
||dx|| <= sqrt(1 + kappa_B^2) ||db||.
```

An application whose readers use only interior coordinates may use the sharper
interior bound; the general T7 field radius uses the full-field bound.

Any finite-iteration solver error is added to this field budget using T5 §7's
geometric convergence bound or a certified residual-to-error bound. A round
count alone is not a radius.

### 4.2 Operator perturbations

Write the base Dirichlet system as:

```
A x_U = f,

A = Delta_UU,
f = -Delta_UB b.
```

Suppose a dimension-preserving model perturbation gives:

```
(A + H) x'_U = f + g
```

and:

```
h = ||A^{-1} H|| < 1.
```

Then `A + H` is invertible and:

```
||x'_U - x_U||
  <= ||A^{-1}|| / (1 - h)
     (||g|| + ||H|| ||x_U||).
```

**Proof.** Subtract the two systems:

```
(A + H)(x'_U - x_U) = g - H x_U.
```

The Neumann-series bound gives:

```
||(A + H)^{-1}|| <= ||A^{-1}|| / (1 - ||A^{-1}H||).
```

Apply it and the triangle inequality. A valid perturbed T5 sheaf operator must
also preserve self-adjoint positive definiteness; the norm condition alone is
the invertibility argument, not a license for arbitrary nonsymmetric matrices.

If dimensions, support scope, or the boundary/interior decomposition change,
this formula does not apply without an explicit comparison map between the two
systems.

### 4.3 Evaluator perturbations

Let `r_field` bound the full field change. For a leaf reader, declare:

```
R_ell = A_ell r_field + zeta_ell,
```

where `A_ell` is its field Lipschitz constant and `zeta_ell` bounds changes to
the reader itself. For an internal operation `c`, assume on the same T6 tube:

```
d(tilde_mu'_c(z), tilde_mu_c(z)) <= zeta_c.
```

Define in topological order over the derivation DAG:

```
R_n = zeta_c + Sum_j L_{c,j} R_{n_j}.
```

The same induction as T6 gives:

```
dist_Y(Eval'_E(d_Y, x'), Eval_E(d_Y, x)) <= R_root.
```

The argument requires the **joint** approximation-and-perturbation budget to
remain inside the declared T6 tubes. At every node used as argument, the ball
of radius:

```
E_n + R_n
```

around its encoded exact value must lie in the relevant tube; equivalently, at
an operation `c`, the product of child balls with radii
`E_{n_j} + R_{n_j}` must lie in `c`'s tube. Separate checks on `E` and `R` do
not imply this joint condition. If the combined ball crosses a top-k,
threshold, support, or scope boundary without a separate margin proof, no
radius is certified.

Set:

```
r_Y = R_root.
```

This radius may include the fixed-operator, operator-change, and solver terms,
but they must not be counted twice.

## 5. Stable commitment theorem

**Theorem T7: certified model-relative commitment.** Assume:

1. `Tar_Y(A) = {k_*}`;
2. `Permit_P(A, W, Y, k_*) = true`;
3. T5 has a unique field and T6 supplies a valid uniform budget `E_Y(A)`;
4. the hardener has exact target margin `m_Y(A) > 0`;
5. a declared perturbation family has certified output radius `r_Y`, and every
   node's combined budget `E_n + R_n` stays inside every T6 tube in which that
   node is used;
6. the strict certificate inequality holds:

```
E_Y(A) + r_Y < m_Y(A).
```

Then the base and every certified perturbed output harden to `k_*`:

```
H_Y(Eval_E(d_Y, x)) = k_*,

H_Y(Eval'_E(d_Y, x')) = k_*.
```

**Proof.** For every exact extension `a`, T6 puts the base output within
`E_Y(A)` of `q_a`. The perturbation bound puts the perturbed output within
`r_Y` of the base output. Hence it lies within `E_Y(A) + r_Y` of every
corresponding exact reference. The strict inequality keeps it inside
`R_{k_*}` by the definition of the uniform distance to that region's
complement. The base case follows by setting `r_Y = 0`. Premises 1-2 authorize
interpreting this stable decision as a model-relative commitment; premises 3-6
prove the metric stability.

The **certified hardening rule** commits only when all six premises are recorded.
Otherwise it returns `bottom`, leaves the item provisional, or reports the
earlier structural obstruction. This rule replaces an unexplained scalar
threshold with a theorem-backed certificate.

The theorem fixes the discrete model target while perturbing its numerical
realization. If new observations, policy versions, model structure, or support
scopes change `Tar_Y` or `Permit_P`, those structural quantities must be
recomputed. Numerical closeness cannot prove that a changed extension problem
has the same target.

**Corollary: safe knowledge feedback.** Suppose commitment `k_*` has a legal
supported fact representation `F_Y(k_*)` satisfying:

```
a contains F_Y(k)  iff  c_Y(a) = k.
```

Also require feedback to be support-closure neutral in the fixed scope:

```
SuppClosure(A union {F_Y(k_*)}) = SuppClosure(A),

Cand_M^W(A union {F_Y(k_*)}; S) = Cand_M^W(A; S)
  for every S in W.
```

The second equality is equality of provenance-labeled candidate sets, not only
of their underlying fact content. The feedback fact's derived provenance must
therefore be presentation-neutral under T1's sample-presentation convention.

Then:

```
Ext_raw^W(A union {F_Y(k_*)}) = Ext_raw^W(A).
```

**Proof.** Every extension on the right has target `k_*` because
`Tar_Y(A) = {k_*}`, so every such extension contains the added fact and the new
containment constraint removes nothing. Support-closure neutrality keeps the
scope and candidate domains fixed, so the feedback presentation introduces no
new candidate extension.

Thus the slow knowledge layer may record the certified target with derived
provenance without selecting among exact alternatives. If that commitment is
fed back as a new T5 boundary value, its numerical effect must still be included
in the §4 boundary radius and rechecked against the strict margin. This is the
theorem-level two-timescale contract.

The feedback fact retains the provenance of the certificate that produced it.
It is not a new independent view and cannot bootstrap P1's support count for
itself or for a later commitment.

## 6. Score-space corollaries

### 6.1 Thresholded argmax

Let `Z_Y = R^{K_Y}` with the sup norm. Suppose the hardener commits `k` only
when `k` is the unique argmax and its score is at least `tau`. For an exact
score vector `q` whose target is `k_*`, assume `q_{k_*} > tau` and
`gap(q) > 0`, and define:

```
gap(q) = q_{k_*} - Max_{j != k_*} q_j,

m_arg(q) = Min(
  q_{k_*} - tau,
  gap(q) / 2
).
```

The distance from `q` to either the threshold boundary or an argmax tie is
`m_arg(q)`. Therefore:

```
E_Y + r_Y < Inf_{q in Q_*} m_arg(q)
```

certifies the argmax commitment. A score above `tau` with a tiny competitor gap
is not stable.

### 6.2 Mutual-argmax identity

For a score matrix `S` with the entrywise sup norm, consider committing pair
`(i, j)` only when `S_ij >= tau` and it is the unique maximum in row `i` and
column `j`. At an exact reference matrix satisfying `S_ij > tau` and both
strict uniqueness conditions, define:

```
m_pair(S; i, j) = Min(
  S_ij - tau,
  (S_ij - Max_{l != j} S_il) / 2,
  (S_ij - Max_{k != i} S_kj) / 2
).
```

Taking the infimum over exact references gives the pair's decision-region
margin. The T7 inequality with this margin certifies that pair. It does not
certify all pairs in a matching unless the condition holds for each committed
pair and the target projection declares the resulting joint assignment legal.

These corollaries explain why `HARD_SIM = 0.5` is insufficient: `hardened`
checks the threshold, row-argmax, and column-argmax membership conditions with
silent tie-breaking, but records a positive margin for none of them and checks
none of the T1, policy, T5, or T6 premises.

## 7. Truth, policy, and audit firewalls

T7's conclusion is **determined and stable relative to the declared view
model**. To call `k_*` true of the external world, an application must also
instantiate T4's hidden-state, coverage, exact-answer, quotient, and bridge
premises for `Y`. A stable wrong model-relative commitment remains possible
when those premises fail.

The gates remain ordered:

1. T1-T3 classify the target extension set;
2. P1/P2 and other named policies permit or refuse;
3. T5 supplies a unique thinking field;
4. T6 supplies semantic approximation and capacity bounds;
5. T7 checks decision and perturbation margins;
6. T4, when instantiated, upgrades model-relative status to hidden-world
   identifiability.

T4 is logically independent and may be validated earlier, but it does not
replace any of the model-side gates. Gold ids, evaluation-only mappings, and
hypothetical states may audit the theorem after the fact; they may not enter a
runtime certificate.

Every commitment event records at least:

- `A`, `W`, `Y`, and the target projection version;
- the structural target and policy verdict;
- model, linearization, enrichment, and hardener versions;
- `E_Y`, `r_Y`, `m_Y`, and the strict inequality result;
- observed/derived provenance supporting the target.

If new evidence or a version change invalidates a premise, the commitment is
exactly retractable and the dependent derivations are replayed. Stability is
not permanence.

## 8. Relation to the current implementation

The current graded benchmark is not a T7 instance.

- T5 and T6 explicitly exclude its nonlinear Sinkhorn/annealing field and
  graded reducer, so no `E_Y` exists.
- `hardened` checks `S_ij >= HARD_SIM` and mutual `numpy.argmax`, but records no
  row gap, column gap, perturbation radius, or exact-reference margin.
- deterministic tie-breaking by `argmax` is not abstention and supplies no
  positive margin.
- non-anchor commits are not preceded by a target-level T1 classification and
  a recorded P1 policy verdict.
- no certificate or event record supports exact retraction.

The measured consequence is consistent with these missing premises: the
GraphLog arm produced two real mispairings and mean commit precision `0.807`,
missing its pre-registered `0.90` gate
(`results/graded-ensemble/graphlog.json`, `P-G3_commit_precision`). This is an
empirical failure of the current hardening gate, not a proof that every
mutual-argmax hardener fails.

Anchors are different: `hardened` inserts them as commitments by construction.
That is legitimate only because their observation process supplies exact typed
boundary facts; they do not earn commitment from `HARD_SIM`.

To instantiate T7, a replacement must satisfy T5 §9 and T6 §8, define
`c_Y`, `H_Y`, and `Permit_P`, compute uniform exact-reference margins, certify
field/evaluator perturbation radii, abstain on every failed premise, and persist
the complete audit record.

## 9. Bench translations

**E1 fresh-node forgery and E2 solo truth.** Both are determined-as-solo in the
canonical discrete scope, but P1 refuses absent cross-view support. T7 never
reopens the gate based on a stable score. Their hidden-world difference remains
T4's concern.

**E2b overlap forgery.** Under the measured P2/A1 process, T2 makes the target
extension set empty. Hardening is structurally blocked before any margin test.

**E3 orphan merges.** Multiple supported pairings remain uncommittable when
`Y` asks for a representative pairing. A quotient-orbit target may be committed
only if `c_Y` is invariant, its target set is singleton, P1 permits it, and the
full T7 margin certificate holds.

**E4 split-brain tax.** Stable commitment does not imply improved derivation or
benchmark accuracy. T6 operation coverage and approximation remain necessary.

**E5 rule_20.** The two false hardening-gate commits are the motivating current
examples of uncertified hardening. Their zero marginal effect in the frozen
configuration and large effect after rule translation do not change that
status: the output quotient lacked a structural and margin certificate. The
certified T7 rule would therefore abstain on those current commit events; the
evaluation-side falsehood does not by itself identify which T7 premise a future
model would fail. T7 does not predict the factorial interaction's size.

**E6 rule_27.** The hub identity was found and committed, yet making it exact
changed graded accuracy only `0.163 -> 0.168`. T7 could certify an identity's
stability, but cannot make that identity useful to an enrichment whose
derivation semantics do not consume it correctly.

**E7 confabulation and E8 component barrier.** Unsupported fields fail the
provenance/policy gate. Uncontrolled Dirichlet kernels fail T5 uniqueness. Zero
initialization or a repeatable argmax cannot turn either failure into a stable
commitment certificate.

**E9 capacity.** A stable decision inside a representation-collapsed carrier
can be consistently wrong relative to exact derivations. T6's `D`-separation
certificate remains a premise; T7 is not a substitute for capacity.

## 10. What T7 does and does not discharge

T7 supplies:

- target-level structural gating over exact extension sets;
- a general decision-region margin definition;
- boundary, operator, solver, and evaluator perturbation budgets;
- exact thresholded-argmax and mutual-argmax corollaries;
- a stable model-relative hardening theorem;
- a safe feedback lemma for the slow knowledge layer;
- an auditable abstain/commit/retract contract.

T7 does not supply:

- an external-truth guarantee without T4;
- policy permission without P1/P2;
- a T5/T6 instantiation for the current graded code;
- a universal perturbation radius or hardening threshold;
- benchmark accuracy from commitment stability;
- permanence under changed evidence or models;
- the T2 composition-closure extension.

T7 is discharged as a model-relative stability theorem. The designed T0-T7
theory chain is closed. A replacement implementation still must satisfy T5 §9,
T6 §8, and T7 §8 before citing that chain for its graded field, enrichment, or
commitments.
