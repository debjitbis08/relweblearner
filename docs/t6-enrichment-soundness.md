# T6 — enrichment soundness by local comparison

*Written 2026-07-15, after T0-T5 were discharged. This note states the
comparison theorem promised by design-problem D3/T6. It tells a declared
graded enrichment how to earn a finite-derivation approximation claim and
locates representation capacity in a checkable separation condition. It does
not declare one enrichment universally correct, identify model extensions with
hidden truth, or certify the repository's current graded benchmark.*

## 1. Status

**Status: discharged after referee review.** T6 has three parts:

1. a comparison bound between an encoded exact section and the unique T5
   harmonic field;
2. a compositional bound that transports local enrichment defects through a
   finite exact derivation;
3. a separation-margin criterion showing when the enrichment preserves the
   distinctions a declared derivation family can observe.

The theorem is model-relative and extension-relative. T7, not T6, decides
whether any approximate output is stable enough to harden.

## 2. Exact derivations and comparison data

Fix a finite T0 scope `W`, a finite observation family `A`, and one supported
exact extension:

```
a in Ext_raw^W(A).
```

If the extension set is empty, there is no exact derivation to approximate. If
it has several elements, T6 applies separately to each `a`; a graded score may
not silently select one of them. The chosen `a` is a model state, not a T4
hidden-world truth claim.

A system-level certificate based only on `A` must hold uniformly over every
`a in Ext_raw^W(A)`, for example by reporting the supremum root budget. The
per-extension statement is an analysis device, not a policy for resolving T3
ambiguity.

Fix before evaluation a finite family `D` of typed exact acyclic derivation
graphs; trees are the special case without shared subderivations. A leaf reads
a supported local value from `a`. Every internal node is a declared partial
structured operation:

```
mu_c: X_{tau_1} x ... x X_{tau_r} partial-to X_tau.
```

Only trees on which every exact operation is defined belong to `D`. Composition,
rule application, alternative-proof aggregation, path aggregation, and any
other semantics-affecting step must appear as named nodes. In particular,
addition, maximum, normalization, pruning, and fallback are not interchangeable
implementation details.

A **comparison package** `E` for `D` supplies:

- a metric enriched carrier `(Z_tau, d_tau)` and an encoding
  `iota_tau: X_tau -> Z_tau` for every exact type used by `D`;
- an enriched operation `tilde_mu_c` for every exact operation `mu_c` used by
  `D`;
- a declared tube around the encoded legal inputs on which `tilde_mu_c` is
  defined;
- a local commutation-defect constant `epsilon_c >= 0` satisfying, for every
  legal exact tuple `u`:

```
d_tau(
  tilde_mu_c(iota(u_1), ..., iota(u_r)),
  iota(mu_c(u_1, ..., u_r))
) <= epsilon_c;
```

- coordinate Lipschitz constants `L_{c,j} >= 0` on that tube:

```
d_tau(tilde_mu_c(z), tilde_mu_c(z'))
  <= Sum_j L_{c,j} d_{tau_j}(z_j, z'_j);
```

- typed leaf readers and the leaf bounds stated in §4;
- equivariance under T0's allowed relabelings and preservation of declared
  provenance/support partitions.

Equivariance is the well-definedness condition for this package: encodings,
defects, and budgets must descend through the opaque-id and sample-presentation
classes already quotiented by T0/T1, rather than changing with a representative.

When enriched values represent evidence mass, every contribution must retain a
declared source set. An operation may union or legally propagate its inputs'
sources, but normalization cannot manufacture a new evidence source. A prior,
regularizer, or imagined alternative must enter as its own typed leaf and be
compared with the corresponding exact semantics; it is not anchor evidence.

The package is **`D`-admissible at a stated budget** only when all required
operations exist, the constants are established independently of the tested
outputs, and at every operation the product of argument balls with radii
`E_{n_j}` around the encoded exact children lies inside the declared tube.
Finiteness makes the defects on encoded exact tuples computable; it does not
make them small. A package whose bound exceeds its declared tolerance is
falsified for that use.

An operation missing from the enriched language is not assigned a large
`epsilon_c`: the package is simply not admissible for derivations using it.
This distinction is load-bearing for the GraphLog translation failures.

## 3. The T5-to-exact comparison

For the Hilbert enrichment used by T5, the package also supplies an assembly
map from exact extensions to vertex cochains:

```
iota_W: Ext_raw^W(A) -> C^0.
```

Let `y = iota_W(a)`. The quantity `delta y` is the linearization's naturality
defect: it measures whether an exact compatible structured section becomes a
compatible linear section. Let `x = (b, x_U)` be the T5 field with declared
boundary `b`, and assume the T5 Dirichlet kernel vanishes. When `U` is
nonempty, define:

```
kappa_B     = ||Delta_UU^{-1} Delta_UB||,
kappa_delta = ||Delta_UU^{-1} delta_U^*||,

beta(a, b) = kappa_B ||b - y_B||
             + kappa_delta ||delta y||.
```

If `U` is empty, the boundary specifies the whole field and set
`beta(a, b) = 0` without forming an inverse.

These are T5 spectral data, not new free constants. In the unique nonempty
case, `delta_U` has full column rank and:

```
Delta_UU^{-1} delta_U^* = delta_U^+,

kappa_delta = 1 / sigma_min(delta_U)
             = 1 / sqrt(lambda_min(Delta_UU)).
```

Here `delta_U^+` is the Moore-Penrose pseudoinverse. `kappa_B` is exactly T5
§6's boundary-sensitivity constant. Both constants are computable from the
operator and spectral bounds already required by T5 §9.

**Lemma: harmonic comparison.** The unique T5 field obeys:

```
||x_U - y_U|| <= beta(a, b).
```

Consequently:

```
||x - y|| <= e_field(a, b)
           = sqrt(||b - y_B||^2 + beta(a, b)^2).
```

**Proof.** Since `x` solves the T5 Dirichlet system:

```
Delta_UU x_U = -Delta_UB b.
```

The encoded exact cochain satisfies:

```
Delta_UU y_U + Delta_UB y_B = delta_U^* delta y.
```

Subtracting gives:

```
Delta_UU (x_U - y_U)
  = -Delta_UB (b - y_B) - delta_U^* delta y.
```

Invert `Delta_UU`, take norms, and use the triangle inequality. The full-field
bound follows from the orthogonal boundary/interior decomposition.

**Exact bridge corollary.** If the boundary matches (`b = y_B`) and the
linearization is natural on `a` (`delta y = 0`), then `x = y`. This is the
precise condition under which T5 harmonic thinking reproduces that exact
structured extension before any downstream derivation.

If the Dirichlet kernel is nonzero, T5 supplies an affine family rather than a
model-determined field. T6 v1 does not hide that ambiguity behind a
minimum-norm or initialization convention; the comparison theorem requires
the unique T5 case.

## 4. Compositional derivation error

For each leaf `ell` of a derivation `d`, let `v_ell(a)` be its exact value and
let `R_ell(x)` be the enriched value read from the T5 field. The comparison
package supplies constants `alpha_ell, epsilon_ell >= 0` such that:

```
d(
  R_ell(x),
  iota(v_ell(a))
) <= alpha_ell e_field(a, b) + epsilon_ell.
```

Here `epsilon_ell` covers a declared feature/encoding defect. For an
orthogonal coordinate projection with an exact encoder it is zero and
`alpha_ell <= 1`.

Evaluate `d` once in the exact structured algebra and once with the enriched
leaf readers and operations, memoizing one value per DAG node. Define an error
budget in topological order. At a leaf:

```
E_ell = alpha_ell e_field(a, b) + epsilon_ell.
```

At an internal node `n` labeled by operation `c` with children `n_j`:

```
E_n = epsilon_c + Sum_j L_{c,j} E_{n_j}.
```

**Lemma: derivation transport.** At every node `n`:

```
d(
  enriched_value(n),
  iota(exact_value(n))
) <= E_n.
```

**Proof.** Use topological induction over the DAG. The leaf case is the reader
contract. At an internal node, the induction hypotheses put enriched child
`n_j` within `E_{n_j}` of its encoded exact value. The admissibility side
condition says the product of precisely those argument balls lies inside the
declared tube, so the coordinate Lipschitz inequality is available. Insert the
enriched operation evaluated on encoded exact child values; the triangle
inequality splits the result into the local commutation defect and the change
caused by perturbed children. Apply the Lipschitz bound and induction
hypotheses.

Unrolling the recursion gives a sum of local defects, each multiplied by the
products of downstream Lipschitz constants along its path to the root. Thus
depth alone is not the error: contractive operations damp defects, expansive
operations amplify them, and a missing operation invalidates the comparison.

Alternative derivations may share subderivations in the same finite DAG. Their
sum, maximum, vote, or set union must be a declared aggregation node with its
own exact analogue and constants. A discontinuous top-k or threshold operation
needs a predeclared margin tube; without one it has no uniform local
certificate under this lemma and needs a separately reviewed discontinuous
derivation analysis. Final threshold or argmax hardening belongs to T7.

## 5. The theorem

**Theorem T6: local-to-global enrichment soundness.** Let:

1. `a in Ext_raw^W(A)` be a supported exact extension;
2. `L(M)` be a T5 Hilbert linearization with zero Dirichlet kernel;
3. `E` be a `D`-admissible comparison package whose assembly, leaf, operation,
   and tube contracts hold.

Then for every `d in D`:

```
d_root(
  Eval_E(d, x),
  iota_root(Eval_exact(d, a))
) <= E_root(d; a, b),
```

where `x` is the unique T5 field, its contribution is bounded by §3, and
`E_root` is the recursive expression in §4.

If boundary matching, linear naturality, leaf comparison, and every operation
square are exact, then the enriched and exact derivations agree exactly after
encoding. Otherwise T6 reports the stated finite error; it does not convert
that error into a discrete decision.

**Proof.** The harmonic comparison lemma bounds the field presented to the
leaf readers. The derivation-transport lemma then propagates those leaf errors
and all local operation defects to the root.

The derivation lemma itself applies to non-Hilbert metric enrichments such as a
tropical or Hausdorff-metric set-valued evaluator when they supply the same
local contracts. Such an enrichment does not inherit T5's existence,
uniqueness, or convergence theorem; it needs its own thinking-operator theorem
or must be used only as a downstream evaluator of a T5 field.

## 6. Representation capacity

Approximation and capacity are related but distinct. Consider two comparison
instances `(A, a, b)` and `(A', a', b')`; they may be two extensions of the
same observations, in which case `A = A'` and normally `b = b'`. Let `x_a` and
`x_a'` denote the corresponding T5 fields. For a derivation `d`, define the
exact encoded separation:

```
gamma_d(a, a') = d_root(
  iota(Eval_exact(d, a)),
  iota(Eval_exact(d, a'))
).
```

Let their T6 root bounds be `E_d(a)` and `E_d(a')`.

**Lemma: retained separation.** The enriched outputs satisfy:

```
d_root(Eval_E(d, x_a), Eval_E(d, x_a'))
  >= gamma_d(a, a') - E_d(a) - E_d(a').
```

**Proof.** Apply the triangle inequality to the two exact encoded outputs and
move the two approximation errors to the other side.

Therefore a positive certified margin:

```
gamma_d(a, a') > E_d(a) + E_d(a')
```

guarantees that the enrichment preserves this exact distinction. Conversely,
if a deterministic enriched pipeline gives the same output for the two states,
at least one approximation error is at least `gamma_d(a, a') / 2`.

Call `E` **`D`-separating at its certified budget** when every pair with
different exact `D`-behavior has some `d in D` satisfying the strict margin
above. Then the enriched behavior is injective on exact `D`-behavior classes.
This is the T6 capacity certificate.

At T6's declared budget, the old frozen-algebra ceiling is certified absent
exactly when the package is `D`-separating. Failure can come from a literal
collision in the carrier/encoding/operation/decoder path or from an error
budget large enough to consume the exact margin. A larger carrier alone is not
sufficient: the all-identity and all-zero assignments in the carrier
experiments satisfy many equations while destroying discriminative separation.
Capacity lives in the whole comparison package.

This certificate is finite-family relative. It does not prove that future
queries, unsampled derivations, or the T4 hidden world are separated.

## 7. How D3 selects an enrichment

T6 does not choose between linear, tropical, probabilistic, set-valued, or
symbolic-rewriting semantics. It makes each candidate publish comparable,
falsifiable obligations for the same predeclared derivation family:

1. exact operations covered and operations omitted;
2. assembly naturality and boundary mismatch;
3. local defects and tube radii;
4. local Lipschitz constants and the resulting root bounds;
5. retained-separation margins;
6. computational cost and the solver theorem used.

Candidate comparison must keep representation, discovery, and decision policy
as separate factors. A poor learned assignment does not prove carrier
inadequacy; a representation collision does. Likewise, a hardening error is a
T7 failure unless it changes the boundary, output quotient, or operation
language consumed by the evaluated pipeline.

Empirical selector experiments may reject packages whose assumptions fail or
whose certified/observed errors are too large. They do not alter the theorem
after seeing the scores. In particular, no additive causal decomposition is
implied when factors change different pieces of the package.

For a factorial selector, write `E_theta` for the complete package at factor
setting `theta`. If a factor changes the derivation compiler, enriched
operation, boundary, or output quotient, it defines a different `E_theta`; T6
certifies each cell against its corresponding exact derivations. A candidate
claiming coverage of the rule_20 selector must therefore instantiate the
predeclared cells and reproduce the measured context-conditioned direction of
the soft contribution. The local theorem explains why additivity is not
expected, but it does not derive the empirical sign from structure alone.

Different view draws likewise define different observations, boundaries, and
often different derivation families. A certificate is draw-uniform only if its
constants and operation coverage are proved uniformly over that declared draw
class.

## 8. Relation to the current implementation

The current graded GraphLog path is not a T6 instance.

- `token_similarity` is the nonlinear Sinkhorn/annealing loop already excluded
  by T5 §9, so no T5 field `x` or harmonic comparison constant is available.
  Its uniform initialization is an explicit prior over token pairs, not
  provenance inherited from anchors.
- `graded_reduce` fuses native-vocabulary rule application with per-use
  similarity instead of exposing translate-then-derive. Such a fused operation
  could be compared with the exact composite, but the current code declares no
  comparison square or defect bound for it.
- Within a span it takes a maximum activation per rule head; across completed
  paths it sums activations; committed classes are pooled before a final
  argmax. Those are three distinct aggregation operations and need three
  comparison squares.
- `TOP_K`, `ACT_MIN`, `HARD_SIM`, fallback-to-majority, and mutual argmax are
  discontinuous without declared margins. They have no T6 certificate in the
  current code.
- No local defect, Lipschitz, tube, spectral, or retained-separation table is
  computed.

The carrier ladder is also not a T6 certificate. It is a useful feasibility
selector: it shows that equations can be satisfied by nondiscriminative
assignments and that tested three-point carriers do not uniformly beat the
frozen additive carrier under the heuristic solver. It neither proves
infeasibility nor supplies the comparison constants required here.

To instantiate T6 for a replacement implementation, the project must define a
finite `D`, implement the T5 package or name another reviewed operator, expose
every derivation/aggregation operation, compute the local comparison table,
and verify the recursive budgets and separation margins before scoring.

## 9. Bench translations

**E4 split-brain tax.** T6 makes recovery conditional on operation coverage.
Soft symbol similarity has no approximation claim when the package provides
neither an explicit translate/compose counterpart nor a certified fused
counterpart. When one is present, the theorem states the per-derivation
recovery error through `E_root`; it does not predict a benchmark accuracy
uplift from that norm bound alone. The measured `+0.0215` mean graded uplift is
from `results/graded-ensemble/graphlog.json`
(`P-G2_mean_improvement`), but sits inside a failed pre-registered headline
gate: `P-G1_graded_over_gold = 0.8272 < 0.90` on the same run.

**E5 rule_20.** The accepted factorial changes different theorem inputs. Rule
translation changes operation coverage; removal of two false commits changes
the output quotient and decoder supplied by hardening; similarity
exactification changes local leaf/operation defects; rendering translation was
inert in all measured cells. Their `0.267` commit-by-translation interaction is
therefore compatible with T6 and cannot be replaced by an additive error
attribution. The key selector datum is also preserved: after translation and
commit repair, the frozen soft similarity is mildly beneficial (`0.669` versus
discrete `0.659`). E5 rejects the frozen package, not soft enrichment in
isolation.

**E6 rule_27.** T6 does not fill the open graded mechanism. The current graded
pipeline found the hub identity, but exactifying it changed accuracy only
`0.163 -> 0.168`; the corrected referee record withdrew multiplicative decay
as the binding explanation. With no T5 instance, no translation-complete
operation package, and no local comparison table, no T6 premise is validated.
The 44 predictions that differ from discrete remain unattributed.

**E9 representation capacity.** The carrier/encoding/operation/decoder package
must be `D`-separating. This explains both sides of the record: the one-web
integer carrier collapsed query-relevant relations, while multi-view symbolic
rewriting recovered distinctions by retaining relation symbols and learned
composition rules. The old ceiling does not rebind for a declared `D` exactly
when the retained-separation certificate holds; the measured `0.13 -> 0.51`
gain is evidence for broader capacity, not a universal certificate.

## 10. Firewalls and remaining work

T6 supplies:

- a typed definition of comparison-admissible enrichment;
- an exact T5-to-structured field bound;
- a local-to-global finite-derivation error theorem;
- a separation-margin capacity certificate;
- a precise account of why missing translation is not numerical noise;
- explicit selector and implementation obligations.

T6 does not supply:

- a unique exact extension when T1 reports many, or any extension when T2
  reports empty;
- a hidden-world truth claim or coverage theorem;
- an instantiation for the current nonlinear graded benchmark;
- a universal ranking of enrichment families;
- a benchmark-accuracy bound derived from a norm bound;
- stable hardening, threshold selection, or commitment;
- the T2 composition-closure extension.

T6 is discharged as a finite-family, model-relative comparison theorem. T7 may
consume `E_root` and an exact output margin to prove stable commitment. The
current graded benchmark remains outside T6 until it satisfies the
instantiation obligations in §8.

T7's target-level stable-commitment theorem is discharged after referee review
in docs/t7-stable-commitment.md. The designed T0-T7 theory chain is closed; T6's
§8 current-implementation exclusion remains active.
