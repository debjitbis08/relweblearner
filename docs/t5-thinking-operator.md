# T5 — the anchored harmonic thinking operator

*Written 2026-07-15, after T0-T4 were discharged. This note defines the
linear thinking operator promised by design-problem D4/T5 and proves its
finite-dimensional boundary-value properties. It does not identify the
operator with the repository's existing nonlinear Sinkhorn/annealing loop;
that implementation boundary is explicit in §9. T5 concerns graded thinking,
not discrete compatibility, commitment, or external truth.*

## 1. Status

**Status: discharged after referee review.** Given a finite Hilbert-space
linearization `L(M)`, a declared anchor boundary `B`, and boundary values `b`,
T5 defines the thinking field as the minimizer of sheaf consistency energy. It
proves:

```
Argmin E_b = x_U^* + ker(Delta_UU),
unique  iff  ker(Delta_UU) = 0  iff  Delta_UU is positive definite.
```

In the unique case it also proves component locality, a perturbation bound,
finite-step propagation locality, and convergence of a local gradient
iteration from every initialization. These are exact model-relative claims.
T6 must justify the chosen linearization; T7 must justify hardening.

## 2. Inputs and firewalls

Fix a finite T0 model and a declared finite object scope `W`. T5 assumes a
linearization `L(M)` has been supplied on a finite cell complex `K_W` with:

- a finite-dimensional real Hilbert space `F(v)` at every vertex `v`;
- a finite-dimensional real Hilbert space `F(e)` at every edge `e`;
- linear restriction maps `rho_{v,e}: F(v) -> F(e)` for incident cells;
- positive-definite Hilbert metrics and optional nonnegative scalar coupling
  weights `w_e`.

Zero-weight edges are omitted from the operator. For each retained edge,
`w_e > 0` is incorporated as `sqrt(w_e)` in its coboundary block. An omitted
edge must not be used later as evidence of propagation.

The vertex cochain space is:

```
C^0 = DirectSum_{v in K_W^0} F(v),
```

and the edge cochain space `C^1` is defined analogously. Choose an arbitrary
orientation for every edge. The coboundary is:

```
(delta x)_e = sqrt(w_e) [
                rho_{head(e),e} x_{head(e)}
                - rho_{tail(e),e} x_{tail(e)}
              ].
```

Changing edge orientation changes a row sign and leaves all energies and
Laplacians below unchanged.

Declare an orthogonal block decomposition:

```
C^0 = C^0_B direct-sum C^0_U,
```

where `B` contains the pinned boundary blocks and `U` the free interior blocks.
A block may be a whole vertex stalk or a declared orthogonal summand of one;
the latter permits partial-coordinate anchors without silently pinning the rest
of the stalk. Boundary values `b in C^0_B` come only from typed anchors or
already committed assignments with provenance. A score, hidden gold identity,
imagined state, or unsupported candidate is not boundary data.

The firewalls from T0-T4 remain:

- a harmonic field is not a raw knowledge section;
- a low linear residual is not T1 compatibility;
- uniqueness is relative to `L(M)` and does not imply T4 truth;
- T5 does not authorize a hard identity or other commitment.

## 3. The Dirichlet problem

Let:

```
Delta = delta^* delta
```

be the degree-zero cellular sheaf Laplacian. Partition the coboundary and
Laplacian by boundary and interior coordinates:

```
delta = [ delta_B  delta_U ],

Delta = [ Delta_BB  Delta_BU ]
        [ Delta_UB  Delta_UU ],

Delta_UU = delta_U^* delta_U,
Delta_UB = delta_U^* delta_B.
```

For fixed boundary value `b`, define the consistency energy:

```
E_b(x_U) = 1/2 || delta_B b + delta_U x_U ||^2.
```

The **T5 thinking field** is the full cochain `x = (b, x_U)` for any minimizer
of `E_b`. Its interior Euler equation is the Dirichlet system:

```
Delta_UU x_U = -Delta_UB b.
```

If the minimum energy is zero, the field is an exact compatible linear
section. Otherwise it is the least-squares harmonic extension of the declared
boundary, with residual `delta x`. The residual is diagnostic; T5 does not
reinterpret it as a discrete obstruction or cohomology class.

## 4. Existence and the solution set

**Lemma: existence.** For every finite `L(M)`, every boundary set `B`, and
every boundary value `b`, `E_b` has at least one minimizer.

**Proof.** This is the finite-dimensional least-squares problem:

```
minimize || delta_U x_U - (-delta_B b) ||^2.
```

Orthogonal projection of `-delta_B b` onto `image(delta_U)` exists, so at
least one preimage minimizing the residual exists. The least-squares normal
equation is exactly the displayed Dirichlet system.

**Lemma: affine solution set.** If `x_U^*` is one minimizer, then:

```
Argmin E_b = x_U^* + ker(delta_U)
           = x_U^* + ker(Delta_UU).
```

**Proof.** Two least-squares minimizers have the same orthogonal projection in
`image(delta_U)`, so their difference lies in `ker(delta_U)`. Conversely,
adding a kernel vector does not change the residual. Finally:

```
<z, Delta_UU z> = ||delta_U z||^2,
```

so `ker(delta_U) = ker(Delta_UU)`.

Existence therefore does not require anchors in every component. The declared
boundary affects uniqueness through the Dirichlet kernel, not existence.

## 5. Uniqueness and the Dirichlet kernel

Define the **Dirichlet kernel**:

```
K_D(B) = {
  z in C^0 : z_B = 0 and delta z = 0
}.
```

Restriction to interior coordinates identifies `K_D(B)` with
`ker(Delta_UU)`. Hence the following are equivalent:

1. every boundary value has exactly one harmonic extension;
2. `K_D(B) = 0`;
3. `ker(Delta_UU) = 0`;
4. `Delta_UU` is positive definite.

Equivalently, boundary evaluation is injective on the global linear-section
space:

```
ev_B: ker(delta) -> C^0_B.
```

This is the exact E8 condition. “An anchor in every connected component” is
not sufficient for an arbitrary cellular sheaf: a nonzero global section can
vanish at an anchored vertex when restriction maps have kernels or split
degrees of freedom.

**Scalar-graph corollary.** If every vertex stalk is `R`, every positive-weight
restriction is the identity, and the coupling graph is undirected, then
`ker(delta)` consists of constants on connected components. In this special
case `Delta_UU` is positive definite exactly when every positive-weight
connected component contains at least one boundary vertex.

**Identity-vector corollary.** The same component criterion holds for stalk
`R^d` with identity restrictions, provided a boundary vertex pins all `d`
coordinates. Partial-coordinate anchors use the block decomposition in §2 and
require the general injectivity test.

If `K_D(B)` is nonzero, choosing the minimum-norm solution, adding a ridge
term, or initializing the iteration at zero selects a representative by
convention. None of those choices turns the field into a model-determined
quantity. T5 requires the system to report an uncontrolled linear kernel or
to declare and justify the extra gauge condition.

## 6. Locality and sensitivity

Let the **operator graph** have one vertex for each declared orthogonal stalk
block and connect blocks `v` and `w` when the off-diagonal block `Delta_vw` is
nonzero. Its connected components may refine or equal the retained
coupling-graph components; they cannot join two separate coupling components.
Two declared blocks of the same vertex stalk may still be adjacent through an
off-diagonal sub-block of that stalk's diagonal Laplacian block.

**Component locality.** After permuting coordinates by operator component,
`Delta_UU` and `Delta_UB` are block diagonal. In the unique case:

```
x_U = -Delta_UU^{-1} Delta_UB b.
```

Therefore the field in one operator component depends only on boundary values
in that component. A boundary perturbation cannot cross a zero coupling or a
component boundary. This is the precise locality claim behind E8.

Harmonic extension is generally not finite-radius local at equilibrium: a
boundary change can influence every vertex in its connected operator
component. T5 does not claim otherwise.

**Sensitivity.** For a boundary perturbation `db`, the unique field changes by:

```
dx_U = -Delta_UU^{-1} Delta_UB db,
```

and therefore:

```
||dx_U|| <= ||Delta_UU^{-1} Delta_UB|| ||db||.
```

Since `||Delta_UU^{-1}|| = 1 / lambda_min(Delta_UU)`, a small Dirichlet
spectral gap means large possible amplification. T5 proves the bound but does
not assume the constant is small; T7 must use an application-specific bound
before hardening.

**Finite-step locality.** The gradient iteration in §7 multiplies by the
sparse matrix `I - eta Delta_UU` once per step. Starting from `x_U^(0)`, the
effect of boundary forcing after `t` steps can travel at most `t` edges in the
operator graph. The converged field remains component-global.

## 7. Convergence

Assume the equivalent uniqueness conditions in §5. Let:

```
0 < lambda_min <= lambda_max
```

be the smallest and largest eigenvalues of `Delta_UU`. Consider local gradient
descent on `E_b`:

```
x_U^(t+1) = x_U^t
            - eta (Delta_UU x_U^t + Delta_UB b).
```

For any fixed step size:

```
0 < eta < 2 / lambda_max,
```

the iteration converges from every initialization to the unique harmonic
extension. If `e_t = x_U^t - x_U^*`, then:

```
e_{t+1} = (I - eta Delta_UU) e_t,

||e_t|| <= q^t ||e_0||,
q = max_{lambda in spectrum(Delta_UU)} |1 - eta lambda| < 1.
```

**Proof.** Diagonalize the positive-definite self-adjoint matrix
`Delta_UU`. Every eigenmode is multiplied by `1 - eta lambda`; the step-size
condition puts all factors strictly inside the unit disk.

The optimal constant step for this bound is:

```
eta_* = 2 / (lambda_min + lambda_max),
q_* = (kappa - 1) / (kappa + 1),
kappa = lambda_max / lambda_min.
```

If `U` is empty, the boundary already specifies the whole field and the
convergence claim is vacuous; the spectral step-size statement concerns the
nonempty interior case.

Thus a round count must be selected from a declared tolerance using the error
bound; a fixed number such as eight is not a theorem. No annealing schedule is
needed for this quadratic operator, and in the unique case the converged field
is independent of zero, uniform, or random initialization.

If `Delta_UU` is singular and `0 < eta < 2 / lambda_max` on its nonzero
spectrum, gradient descent reduces the range component of the error while
preserving the initialization's kernel component. The limit is then
initialization-dependent unless an extra gauge rule is imposed. This is why
zero initialization cannot substitute for the Dirichlet-kernel test.

## 8. The theorem

**Theorem T5.** For every finite Hilbert-space linearization `L(M)`, declared
boundary `B`, and boundary value `b`:

1. a harmonic thinking field exists;
2. its interior solution set is `x_U^* + K_D(B)|_U`, equivalently
   `x_U^* + ker(Delta_UU)`;
3. it is unique exactly when `K_D(B) = 0`, equivalently when
   `Delta_UU` is positive definite;
4. in the unique case, the field is component-local and obeys the sensitivity
   bound in §6;
5. in the unique case, local gradient descent converges from every
   initialization under the step-size condition in §7, with the stated
   geometric rate.

**Proof.** Items 1-3 are §§4-5. Item 4 follows from block decomposition and
the inverse Dirichlet system in §6. Item 5 is the spectral argument in §7.

The theorem is invariant under edge reorientation and under orthogonal changes
of stalk coordinates when all data are transported with them. For orthogonal
maps `Q_v` and `Q_e`, this means:

```
rho'_{v,e} = Q_e rho_{v,e} Q_v^*,
b' = Q_B b.
```

A non-orthogonal coordinate change also preserves the abstract minimizer only
when the Hilbert metrics, restriction maps, boundary data, and adjoints are
transported with it; fixing coordinates while changing the metric changes the
operator and is a D3 modeling choice.

## 9. Relation to the current graded implementation

The current functions in `src/relweblearner/bench/multiweb_graded.py` are not
an implementation of the T5 operator as presently written:

- `token_similarity` alternates nonlinear triangle-product updates with
  Sinkhorn normalization and a changing sharpening exponent;
- `node_similarity` uses bilateral matrix diffusion, backbone-thresholded
  adjacencies, Sinkhorn competition, anchor clamping, and a final absolute-mass
  field distinct from the balanced iterate;
- `graded_reduce` uses products, maxima, top-k pruning, and an activation
  floor;
- hardening uses mutual argmax and `HARD_SIM`.

Those mechanisms need not minimize one fixed quadratic energy, and T5 does not
prove their uniqueness, locality, or convergence. In particular, the existing
constants `ROUNDS`, `HARD_SIM`, `TOP_K`, `ACT_MIN`, `MASS_FLOOR`, the
softassign annealing schedule, and the half-median backbone cut are not retired
by T5 alone.

To instantiate T5, a follow-up must:

1. construct `K_W`, stalk spaces, Hilbert metrics, restrictions, and boundary
   values from the declared T0/D3 model;
2. either replace the nonlinear loop with a solver for the Dirichlet system or
   prove that a named transformed objective puts that loop under another
   reviewed convergence theorem;
3. compute or bound the Dirichlet kernel on every relevant operator component;
4. compute or bound `lambda_max` to choose a valid step size; a scalar
   Gershgorin or weighted-row-sum bound is available once the finite operator is
   assembled;
5. compute or bound `lambda_min`, or provide a certified residual-to-error
   relation, and select stopping from a declared tolerance rather than an
   unexplained fixed round count;
6. leave hardening to T7.

T6 separately owes the semantic comparison between this linearized field and
the discrete structured derivations. T5 proves the operator once chosen, not
that the choice is useful.

## 10. Bench translations

**E7 confabulation trilogy.** Anchor-only boundary data and the support graph
make “identity flows from evidence” a boundary-value statement. An unanchored
component is not automatically the zero field: in the scalar case it carries a
constant kernel, and zero initialization merely chooses zero. The honest T5
response is uncontrolled kernel/no interpretation, not invented confidence.

**E8 component barrier.** Triangle interference cannot cross disconnected
rule-web components because the operator is block diagonal there. For scalar
or identity-restriction fields, one full anchor per relevant component gives
uniqueness. For a general sheaf, E8 must use the stronger injectivity condition
`K_D(B) = 0`.

**E4 split-brain tax.** T5 explains how boundary information can propagate
through a connected linearized component and gives its convergence rate. It
does not prove that the resulting field closes the measured accuracy gap; that
requires T6 and the chosen enrichment.

**E5 rule_20.** The measured draw-dependent interaction between translation,
false commits, and similarity is not an existence/uniqueness phenomenon. T5
does not explain it or exonerate the two-timescale architecture.

**E6 rule_27.** The measured graded mechanism remains open. A harmonic theorem
cannot be cited for the current nonlinear implementation, and a low linear
residual would not replace the missing discrete seam witness.

**E9 representation capacity.** Capacity lives in the declared stalk spaces,
restriction maps, and enrichment `L`; T5 only proves well-posed propagation
inside that chosen representation. T6 must show that the old frozen-algebra
ceiling does not reappear semantically.

## 11. What T5 does and does not discharge

T5 supplies:

- an explicit linear thinking operator and energy;
- unconditional finite-dimensional existence;
- the exact Dirichlet-kernel uniqueness criterion;
- the correctly scoped component locality and sensitivity statements;
- an initialization-independent convergence theorem when the kernel vanishes;
- a precise replacement target for fixed rounds and annealing.

T5 does not supply:

- the construction or semantic soundness of `L(M)`;
- a proof for the current Sinkhorn/annealing implementation;
- a universal “one anchor per graph component” theorem for arbitrary sheaves;
- a small stability constant or a safe hardening threshold;
- discrete compatibility, hidden-world truth, or commitment;
- the T2 composition-closure extension.

T5 is discharged as a finite-dimensional, model-relative theorem. T6-T7 may
use that theorem for a declared `L(M)`, but may not cite it as a guarantee for
the current graded benchmark without satisfying the instantiation obligations
in §9.
