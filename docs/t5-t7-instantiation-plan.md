# T5-T7 GraphLog instantiation and implementation plan

*Prepared 2026-07-15. This is the implementation handoff after the T0-T7
theory chain closed. It instantiates the theory for one GraphLog vertical
slice; it does not add another theorem and it does not certify the existing
`multiweb_graded.py` path.*

## 1. Decision and scope

The first implementation target is cross-view relation identity in the
two-view GraphLog bench. The development instance is `rule_20`, `n_train=150`,
view draw `seed=0`; `rule_27`, `seed=0` is the second regression. Both have
already influenced the design and are development data only.

The concrete instantiation is:

- **Observation family `A_G`.** The two opaque GraphLog training views, their
  support-counted composition triangles, and at most six co-witnessed typed
  anchors selected from opaque overlap events. The actual anchor count is part
  of the serialized instance. Hidden label permutations and test targets are
  evaluation-only and are not members of `A_G`.
- **Counting scope `W_G`.** The canonical T1 support closure of the two view
  charts, their pairwise identity-overlap chart, all triangle/rule cells
  reached from observed support, and the finite query derivation cells for
  paths of length at most `MAX_PATH=5`. Phase 1 materializes
  `W_20 = W_G(rule_20, 150, seed=0)`. The same frozen constructor is then used
  for `rule_27` and virgin draws.
- **Commitment type `Y`.** `CrossViewRelationIdentity`. A target instance
  `Y(a,b)` asks whether opaque A-token `a` and opaque B-token `b` denote the
  same relation in the scoped extension. Its finite commitment set is
  `{IDENTICAL, DISTINCT}`; the runtime may additionally return `ABSTAIN`, which
  is not a commitment. Positive commitments extend the partial A-to-B
  bijection. Negative target classifications are recorded but do not create a
  merge.
- **Derivation family `D_G`.** The finite DAGs consisting of (1) one identity
  score decoder `d_Y(a,b)` for every supported target candidate and (2) every
  rendered test path of length at most five, compiled into explicit
  translation, binary composition, within-span alternative aggregation,
  across-path aggregation, and output decoding nodes. Query gold is used only
  after evaluation. No top-k, activation floor, majority fallback, or hard
  argmax is hidden inside `D_G`.
- **Provenance model.** Every atom is a normalized finite set of immutable
  `ObservationRef` and `DerivationRef` records. An observation ref contains
  `(dataset_version, world, split, episode_id, edge_index, view_id)`; a
  derivation ref contains `(rule_version, operation_id, ordered_parent_ids)`.
  Anchor refs name the co-witnessed edge in both views. Source counting uses
  the underlying view/origin ids, not the number of derived paths. Priors,
  regularizers, imagined mappings, and evaluation gold have distinct kinds and
  cannot be promoted to anchor provenance.

`W_G`, `Y`, `D_G`, the comparison norm, all thresholds, and every version id
must be serialized before a scored run. A run whose serialized spec differs is
a different theorem instance.

## 2. Exact structured model and target classification

The GraphLog T0 value object is a finite composition-carrying structure. Its
atoms are opaque relation tokens, supported triples `(p,q)->h`, typed anchor
identities, and admitted exact negative overlap facts. A local overlap state is
a provenance-supported partial bijection. A legal state must:

1. contain every anchor;
2. be injective in both directions;
3. preserve every composition triangle whose complete image lies in scope;
4. preserve view, incidence, body order, and provenance labels; and
5. satisfy admitted P2 overlap conflicts before extension counting.

For this GraphLog theorem instance, the word "partial" uses a declared
completion convention. Every anchored A-token is forced to its anchored
B-token. Every other A-token reached by the supported candidate closure has
its provenance-backed B candidates plus an explicit `UNMAPPED` value. Among
the legal assignments satisfying the five conditions above, extensions are
the **inclusion-maximal partial bijections**: a solution is discarded when
another legal solution strictly contains its graph of identity pairs. Thus a
spurious propagated candidate may remain unmapped when adding it would break
composition, while an individually legal supported identity cannot be
omitted merely to manufacture an extra extension. Maximality never repairs an
anchored conflict because anchors cannot take `UNMAPPED`. This convention is
serialized as `extension_semantics_version`; changing it defines a different
theorem instance.

Candidate pairs enter `Prop_M^W` only through an anchor or a named structural
propagation rule backed by triangles from both views. Ambient Cartesian-product
pairs are search values, not supported facts, and cannot by themselves create
extensions. The exact solver is a deterministic finite backtracker with
constraint propagation. T1 classifies the whole finite solution set. Target
classification then applies T4's declared projection `pi_Y`/model-output
construction and T7's `Tar_Y` gate; it is not an additional conclusion of T1.
The runtime exposes:

```
classify_extensions(A, W) -> EMPTY | SINGLETON | MANY
classify_target(A, W, Y(a,b)) -> empty | {IDENTICAL} | {DISTINCT} | many
```

The solver persists an exhaustion proof summary: variable order, candidate
domains with provenance, constraint counts, target witnesses, and a digest of
all solutions or target-equivalence classes. Target-directed search may avoid
materializing every whole extension, but it must prove that both target values
were exhausted. T1 proves finite computability; `UNKNOWN` on timeout or a
resource limit is a fail-closed runtime concession introduced by this plan,
not a fourth theoretical classification. T7 treats it as abstention, never as
singleton.

P1 is a separate policy verdict. A positive identity requires at least two
provenance-distinct view origins after provenance normalization. In GraphLog,
P2 changes the constraint set only when an exact negative overlap fact has
already been admitted; the adapter does not treat a detector output as exact
under the E2b discharge. That discharge is measured-tier only and scoped to
the declared E2b process—A1 worlds plus the overlap-forgery intervention—not
to GraphLog; no bounded/analytic P2 tier is discharged anywhere. P2 is never
inferred from a score. The optional T2 composition-closure extension remains
out of scope: composed conflict facts must be supplied as exact observations
until that work is separately discharged.

## 3. T5 replacement: anchored commutator field

### 3.1 Linearization

Let `R_A` and `R_B` be the opaque relation tokens in the two support-closed
view charts. The single alignment vertex has stalk

```
F(v_align) = R^(|R_A| x |R_B|)
```

with the Frobenius inner product. A cochain is a real alignment score matrix
`X`, with `X[a,b]` the graded identity coordinate.

For each ordered pair of distinct triangle positions `c=(i,j)`, build rational
role-adjacency matrices `A_c` and `B_c`. Entry `(r,s)` is the normalized
support of observed triangles having `r` at position `i` and `s` at position
`j`. Normalization is by a declared positive rational channel total, is fixed
before evaluation, and is equivariant under opaque-token relabeling.

Each retained channel is a loop 1-cell with two incidences at `v_align`, edge
stalk `R^(|R_A| x |R_B|)`, restrictions

```
rho_head,c(X) = A_c X
rho_tail,c(X) = X B_c
```

and positive rational weight `w_c`. Thus its coboundary block is

```
delta_c(X) = sqrt(w_c) (A_c X - X B_c).
```

The cell representation permits two named incidences of the same vertex so a
loop is not collapsed. Channels empty in either view have weight zero and are
omitted, recorded as non-propagating. The assembled objective is the fixed
quadratic graph-alignment energy

```
1/2 Sum_c w_c ||A_c X - X B_c||_F^2.
```

It is deliberately not Sinkhorn, annealing, or a triangle-product update.

An exact anchor `a<->b` pins a partial-coordinate boundary: `X[a,b]=1` and,
by the declared injective identity type, `X[a,b']=0` and `X[a',b]=0` for all
other scoped tokens. The zero coordinates carry derived
`bijection_exclusion(anchor_ref)` provenance. No other coordinate is pinned.
The exact boundary implication and its provenance are unit-tested separately.
If the opaque overlap stream yields fewer than six anchors, the implementation
uses exactly those anchors: it does not pad the boundary with values or
exclusions attributed to a nonexistent anchor.
The resulting `B/U` partition, including `U=empty`, is serialized and the
ordinary Dirichlet-kernel gate decides whether the smaller boundary controls
the field.

For an exact extension `e`, `iota_W(e)` is its zero-one partial-bijection
matrix on the same coordinates. This makes T6's boundary mismatch and
naturality defect directly computable.

### 3.2 Solver and numerical certificate

The reference implementation assembles both the sparse residual blocks and a
dense `Delta` (the current GraphLog relation sets make the dense reference
small enough). It exposes:

```
assemble_coboundary(linearization) -> Coboundary
partition_dirichlet(delta, boundary) -> DirichletSystem
certify_kernel(system) -> KernelCertificate
bound_spectrum(system) -> SpectralCertificate
solve_dirichlet(system, config) -> ThinkingField, SolverCertificate
```

Kernel certification uses the unweighted rational `delta_U`: positive row
weights do not change its kernel. Exact rank is computed through SymPy's exact
matrix domain. The numeric `Delta_UU` must also pass symmetry, PSD, and
Cholesky checks. A rank deficiency is reported as `UNCONTROLLED_KERNEL`; no
minimum-norm or zero-initialized field is called model-determined.

The spectral certificate records a conservative lower bound for
`lambda_min`, an upper bound for `lambda_max`, the method, residuals, and
rounding slack. Phase 1 computes the eigensystem and a Gershgorin/weighted-row
upper bound independently. The lower bound is accepted only after a
residual-inflated eigenvalue bound is strictly positive and is consistent with
the exact full-rank result. Failure to certify a positive lower bound causes
abstention even when a floating-point solve succeeds.

The production reference solver is local gradient descent with

```
eta = 2 / (lambda_min_lower + lambda_max_upper)
```

clipped, if necessary, to remain strictly below `2/lambda_max_upper`. It stops
when the certified residual-to-error bound

```
||Delta_UU x + Delta_UB b|| / lambda_min_lower <= field_tolerance
```

holds. It also records the geometric T5 round bound. `numpy.linalg.solve` is
an independent oracle in tests, not a replacement for the stopping
certificate. `U=empty` is handled explicitly.

## 4. T6 comparison package

### 4.1 Carriers and operations

Exact relation values are finite token sets, proof-count vectors, or partial
identity matrices, depending on type. Their enriched carriers are the
corresponding finite real vector spaces with the predeclared sup norm for
decision outputs and Euclidean/Frobenius norm for field-facing leaves.
Encodings are zero-one indicator vectors/matrices.

The GraphLog comparison package exposes these operations rather than fusing
them in `graded_reduce`:

| operation | exact operation | enriched operation | required contract |
|---|---|---|---|
| `translate_B_to_A` | apply the extension's partial bijection, retaining an imported token when undefined | multiply by/read from `X`; do not hard-merge first | leaf/linear error and source preservation |
| `compose` | apply every defined supported `(p,q)->h` rule | contract the declared rule tensor with the two input score vectors | finite local defect; coordinate Lipschitz bounds on a norm-bounded tube |
| `span_aggregate` | union alternative reductions within a CYK span | coordinatewise maximum | zero/finite defect and 1-Lipschitz sup-norm tube |
| `path_aggregate` | sum one contribution per completed path | vector addition | zero defect and coordinate constants 1 |
| `decode_output` | project the exact token/proof vector to the declared A-side output quotient | apply the soft translation/quotient map | finite defect and quotient-separation check |
| `decode_identity` | encode the exact partial-bijection matrix | return the corresponding field score matrix | T5 leaf bound used by `d_Y` |

All paths are exhaustively enumerated to length five. Certified evaluation has
no `TOP_K` or `ACT_MIN`. Absence of a derivation returns an empty proof vector;
majority fallback is reported as an uncertified baseline decision, never as a
T6 operation. Final threshold/argmax decisions are outside T6.

For every operation, the package stores:

- exact input/output type ids and the legal exact tuple set;
- enriched implementation/version id;
- tube centre rule and radius;
- independently established `epsilon_c` and coordinate `L_cj`;
- a provenance-transform rule; and
- equivariance results under A/B opaque-token permutations.

Local defects are exhaustively computed on the finite legal exact tuples.
Analytic Lipschitz constants are also checked by adversarial/property tests.
For bilinear rule-tensor composition, the constants use the tensor operator
norm and the declared child-tube radii; they are not fitted to test outputs.

### 4.2 Budgets and capacity

For every exact extension, compute T6's

```
kappa_B, kappa_delta, beta(e,b), e_field(e,b), E_node, E_root.
```

Every child ball must lie inside the consuming operation's tube. The runtime
certificate takes the supremum over all exact extensions in the target class;
if the extension solver cannot complete that supremum, the result is
uncertified.

Capacity is checked separately. For every pair of extension classes with
different `D_G` behavior, compute an exact encoded separation `gamma_d` and
require some predeclared `d in D_G` to satisfy

```
gamma_d > E_d(e) + E_d(e').
```

The certificate lists all compared classes, the witnessing derivation, both
budgets, and the remaining separation margin. A literal collision and a
budget-consumed distinction are reported separately. Failure rejects this
comparison package for the affected derivations; it is not repaired by a
hardening threshold.

## 5. T7 certified hardening

For each candidate `Y(a,b)`, the target projection asks whether `(a,b)` is in
the extension's partial bijection. The gate order is fixed:

1. T1 whole-extension classification followed by T4/T7 target projection;
2. P1/P2 policy verdict;
3. T5 uniqueness and solver certificate;
4. uniform T6 budget and `D_G` separation;
5. joint tube checks and decision/perturbation margins;
6. commit or abstain.

This is the phase-1 model-relative implementation gate, not a renumbering of
T7 §7's truth/policy firewall. T7's sixth firewall stage is the separate T4
upgrade to hidden-world identifiability. Phase 1 does not instantiate that
upgrade and must never label its commitments externally true.

The positive-identity hardener uses the mutual-argmax region in the score
matrix. Its threshold is `tau=0.5`, now part of a versioned hardener rather
than a sufficient gate by itself. For an exact zero-one identity matrix this
maximizes the smaller of the threshold and row/column tie margins. Runtime
code computes the actual uniform margin

```
m_pair = min(score-threshold margin,
             half row gap,
             half column gap)
```

over every exact reference in the singleton target class. Ties have zero
margin and abstain; array order never decides a commitment.

The initial perturbation family is fixed and dimension-preserving:

- exact rational operator versus float assembly (`H` and `g`);
- finite solver residual;
- floating evaluator/decoder error; and
- zero boundary perturbation for the initial observed-anchor run.

For the operator term, the certificate computes `H` and `g`, proves that the
perturbed matrix remains self-adjoint positive definite, and checks
`h=||A^-1 H||<1` before using T7's Neumann bound. If any check fails, or if
dimensions or the boundary/interior partition change, the bound is
inapplicable. For evaluator changes, leaf radii are
`R_leaf=A_leaf*r_field+zeta_leaf` and internal radii are propagated as
`R_n=zeta_c+Sum_j L_cj R_child_j` in DAG topological order.

Each term is recorded once. Future committed-feedback or changed boundary
runs must add `sqrt(1+kappa_B^2)||db||`; support, scope, dimension, evidence,
or model-version changes trigger full recomputation rather than use of the
operator-perturbation formula. Nodewise `E_n + R_n` balls, not separate `E`
and `R` balls, must remain in every T6 tube.

The only positive commit condition is

```
Tar_Y(A) = {IDENTICAL}
and Permit_P(A,W,Y,IDENTICAL)
and E_Y + r_Y < m_Y.
```

Every other outcome is a typed abstention or structural rejection. A
`DISTINCT` singleton may be persisted as an exclusion certificate but is not
fed to the merge map in phase 1.

Commitments are append-only events with content-addressed certificate ids.
Retracting an observation invalidates every dependent provenance node,
rebuilds `A`, `W`, the exact extension classification, and all downstream
T5-T7 certificates, then emits explicit `RETRACT` events for commitments no
longer certified. Replaying the remaining observation log must reproduce the
same live commitments byte-for-byte. A derived commitment retains its original
source closure and cannot count as a new view for P1 or bootstrap itself.
Phase 1 does not feed certified identities back into `A`. A later feedback
phase must first prove support-closure neutrality and equality of
provenance-labeled candidate sets as required by T7's safe-feedback corollary.

## 6. Module map

New theorem-facing code must not live in a benchmark monolith.

| module | responsibility |
|---|---|
| `src/relweblearner/certification/types.py` | immutable ids, norms, version refs, typed verdicts, serialization primitives |
| `src/relweblearner/certification/provenance.py` | normalized source/derivation DAGs, origin counting, dependency closure |
| `src/relweblearner/certification/extensions.py` | finite T1 CSP interfaces and whole-extension classification |
| `src/relweblearner/certification/t5.py` | cells/stalks/restrictions, coboundary/Laplacian assembly, boundary partition, kernel/spectral/solver certificates |
| `src/relweblearner/certification/t6.py` | typed derivation DAGs, comparison contracts, tube checks, recursive budgets, separation certificates |
| `src/relweblearner/certification/t7.py` | target projection, policy gates, perturbation budgets, margins, commit/abstain decision |
| `src/relweblearner/certification/ledger.py` | append-only certificate/commit/retract records and deterministic replay |
| `src/relweblearner/bench/graphlog_certified/spec.py` | frozen `W_G`, `Y`, `D_G`, validation cohort, versions, norms, tolerances, and artifact schema |
| `src/relweblearner/bench/graphlog_certified/ingest.py` | trusted raw-label boundary; emits an opaque runtime view/overlap bundle and a separately sealed evaluation key |
| `src/relweblearner/bench/graphlog_certified/model.py` | GraphLog observations, support closure, exact composition structure, target CSP |
| `src/relweblearner/bench/graphlog_certified/linearization.py` | role matrices, loop cells, anchor boundary, exact-section assembly |
| `src/relweblearner/bench/graphlog_certified/enrichment.py` | exact/enriched translation, composition, aggregations, decoders, local contracts |
| `src/relweblearner/bench/graphlog_certified/derivations.py` | exhaustive path enumeration and memoized typed CYK DAG compiler |
| `src/relweblearner/bench/graphlog_certified/policy.py` | GraphLog P1 verdict and admitted P2 evidence adapter |
| `src/relweblearner/bench/graphlog_certified/runner.py` | vertical-slice execution, baseline joins, artifact emission; no theorem logic |
| `src/relweblearner/bench/graphlog_certified/evaluation.py` | only consumer of sealed permutations, true map, query targets, and oracle rules |

`multiweb_graded.py` and `multiweb_graphlog.py` remain frozen baselines. Their
current view/anchor/rendering interfaces are not safe certified-runner imports:
`pick_anchors` and the mapping/query-edge construction read `perm_a`/`perm_b`
directly. Before G1, `ingest.py` must refactor the boundary to return
`RuntimeViewBundle(opaque_views, opaque_overlap_events, observation_refs)` and
a separately sealed `EvaluationKey`. Anchor selection consumes only opaque
token-pair overlap events and A's opaque component structure; query rendering
consumes pre-rendered opaque per-view edge events. Runtime types contain no
permutation or latent-label field. The certified path may reuse a pure miner
such as `triangle_votes` only after a reachability test proves that its inputs
and outputs are opaque and provenanced; it must not import `make_views`,
`pick_anchors`, `_render_test`, or the existing graded runner construction.

## 7. Runtime types and theorem-object traceability

| theorem object | runtime type | constructor/check |
|---|---|---|
| `A`, observed/derived provenance | `ObservationFamily`, `ProvenanceDAG` | `build_observations`, `normalize_provenance` |
| `W`, support closure | `CountingScope` | `build_scope`, `check_support_closed` |
| T1 `Ext_raw^W(A)` | `ExtensionClassification` | `classify_extensions` |
| T4 `pi_Y`/`Out_M^Y(A)` and T7 `Tar_Y` | `TargetProjection`, `TargetClassification` | `project_target`, `classify_target` |
| `K_W`, `F(v)`, `F(e)`, `rho`, `w` | `CellComplex`, `StalkSpec`, `Restriction`, `EdgeWeight` | `build_linearization`, `validate_linearization` |
| `B`, `b`, `U` | `AnchorBoundary`, `CoordinatePartition` | `build_anchor_boundary` |
| `delta`, `Delta_UU`, `Delta_UB` | `Coboundary`, `DirichletSystem` | `assemble_coboundary`, `partition_dirichlet` |
| `K_D(B)` | `KernelCertificate` | `certify_kernel` |
| `lambda_min/max`, `eta`, tolerance | `SpectralCertificate`, `SolverConfig` | `bound_spectrum`, `solve_dirichlet` |
| T5 field and residual | `ThinkingField`, `T5Certificate` | `run_t5` |
| exact types/operations and `D` | `ExactType`, `ExactOperation`, `DerivationDAG` | `compile_derivations`, `eval_exact` |
| enriched carriers/operations | `MetricCarrier`, `EnrichedOperation` | `build_comparison_package`, `eval_enriched` |
| leaf readers, tubes, defects, Lipschitz constants | `LeafReaderContract`, `Tube`, `LocalComparisonContract` | `verify_leaf_bounds`, `compute_local_defects`, `verify_lipschitz` |
| `beta`, `e_field`, `E_n` | `FieldComparison`, `NodeBudget`, `T6Certificate` | `compare_field`, `propagate_budget` |
| `gamma_d` separation | `SeparationCertificate` | `check_separation` |
| `c_Y`, `Permit_P`, `H_Y` | `TargetProjection`, `PolicyVerdict`, `HardenerSpec` | `classify_target`, `permit`, `harden` |
| `m_Y`, `R_n`, `r_Y` | `DecisionMargin`, `PerturbationBudget`, `JointTubeReport` | `compute_margin`, `propagate_perturbation`, `check_joint_tubes` |
| commit/abstain/retract | `StableCommitmentCertificate`, `CommitEvent`, `RetractEvent` | `certify_commitment`, `replay_ledger` |

This table is normative: no item may be represented only by an untyped JSON
field in the runner.

## 8. Tests

### 8.1 Core T5 tests

- Hand-computed scalar and matrix sheaves: exact `delta`, `Delta`, energy,
  solution, and residual.
- Edge reorientation and orthogonal coordinate-change invariance.
- Positive weights affect energy; zero weights are omitted and cannot join
  operator components.
- Whole- and partial-coordinate anchors, including derived row/column
  exclusions and provenance.
- Exact nonsingular, singular, disconnected, `U=empty`, and ill-conditioned
  fixtures. Singular systems report the kernel regardless of initialization.
- Exact-rank result agrees with numeric SPD checks; spectral upper/lower
  bounds contain high-precision reference eigenvalues.
- Gradient iterates respect finite-step operator-graph locality, converge from
  zero/uniform/random starts, and stop only at the declared error tolerance.
- Boundary sensitivity and component locality are checked against direct
  perturbed solves.

### 8.2 Core T6 tests

- Every operation label in a compiled DAG has exactly one exact and one
  enriched implementation; a missing translation or aggregation rejects the
  package.
- Exhaustive local commutation squares on small finite algebras.
- Tube boundary, joint-child-ball, analytic Lipschitz, and discontinuity
  margin tests.
- Recursive DAG budgets, including shared subderivations, agree with a manual
  calculation and dominate observed errors.
- Relabeling equivariance and provenance-source preservation.
- Exact bridge fixture gives zero budget; boundary mismatch and naturality
  defect increase the correct terms.
- Separation passes for an injective package and fails for an all-zero,
  all-identity, or deliberately colliding carrier.

### 8.3 Core T7 tests

- Empty, positive singleton, negative singleton, many, and `UNKNOWN` target
  classifications take the correct structural branch.
- P1 refusal and admitted P2 conflict occur before metric hardening.
- Threshold, row gap, column gap, exact tie, near tie, and silent-argmax-order
  fixtures verify the mutual-argmax margin.
- Boundary, operator, solver, and evaluator budgets are counted once; changed
  dimension/scope refuses the perturbation shortcut.
- Separate tube checks pass while a joint `E+R` tube fails, forcing abstention.
- Each of T7's six premises is removed in turn and must force abstention.
- Evaluation gold is rejected if presented as runtime provenance.
- Retraction and replay remove exactly the dependent commitments; derived
  feedback cannot increment its own P1 origin count.

### 8.4 GraphLog adapter and regression tests

- Synthetic isomorphic and non-isomorphic triangle webs verify the commutator,
  exact mapping encoding, target classifier, and identity hardener end to end.
- Imported vocabulary, missing translation, differing rule tables, alternative
  reductions, and multiple paths each exercise a named T6 node.
- After the pre-G1 baseline-notarization work item, reproduce the frozen
  `rule_20` and `rule_27` outputs and verify them against the newly recorded
  semantic artifact digests and expected fields. A mismatch blocks causal or
  comparative claims.
- The rule_20 fixture asserts the measured **joint** `C×R` expectation, not
  separable translation and commitment effects: frozen/C-only/R-only/`C+R`
  accuracies are `0.317/0.317/0.371/0.669`; removing the two wrong commits is
  worth `0.000` without translated rules and `+0.298` with them. Rendering
  translation factor `D` is inert in every factorial context. The certified
  replacement must therefore exercise explicit rule translation and
  abstention on uncertified identities jointly, without assigning independent
  marginal credit to either repair.
- The rule_27 fixture records preserved topology and no genuine no-path
  failure. Missing rule bodies are a symptom marker—the all-body patch heals
  only 1 of the 71 episodes marked `missing-rule`. The dominant discrete cause
  is the unresolved split-hub identity `R_9_-`, whose oracle identity repair
  moves `0.163 -> 0.496` and whose visible symptom is CYK-dead derivation.
  Despite the existing heuristic graded commit, the certified path must not
  relabel that hub as an identity success: it abstains when the target or
  margin is uncertifiable and preserves the causal signature in its trace.
- Add a no-gold reachability/serialization test over the certified runner.
  Raw permutations may exist only transiently inside the trusted ingest
  boundary and inside its sealed `EvaluationKey`; that key, `true_map`, query
  targets, and oracle rules are readable only by `evaluation.py`. None may
  occur in `RuntimeViewBundle`, runtime provenance, or a certificate artifact.

## 9. Certificate artifacts

Before per-run artifacts exist, the pre-G1 notarization step creates
`results/graphlog-certified/baselines/manifest.json`. It content-addresses the
currently unhashed discrete, graded, rule_20, and rule_27 result artifacts and
the code/data/spec inputs needed to reproduce them. Each later run references
that immutable manifest id.

Each run writes a content-addressed directory under
`results/graphlog-certified/<run_id>/`:

| artifact | contents |
|---|---|
| `manifest.json` | code/data/spec versions, hashes, world/draw, tolerances, baseline artifact ids |
| `scope.json` | `A`, `W`, support closure, provenance DAG, `Y`, and compiled `D_G` digest |
| `t1.json` | T1 whole-extension classification, witnesses, domains, and exhaustion summary |
| `targets.json` | T4 target projection/output sets, T7 `Tar_Y` classifications, and P1/P2 inputs |
| `operator.npz` + `t5.json` | role matrices, boundary partition, `delta/Delta` hashes, kernel/spectral/solver certificates, field/residual hash |
| `comparison.json` | operation coverage table, local defects, Lipschitz constants, tubes, per-node and uniform root budgets |
| `separation.json` | exact behavior classes, witness derivations, `gamma`, budgets, remaining margins |
| `commitments.jsonl` | one complete T7 premise record per commit/abstention/rejection and later retraction events |
| `evaluation.json` | theorem-premise rates and separately labeled accuracy/precision/coverage comparisons using evaluation-only gold |

JSON uses a canonical serializer; arrays carry shape/dtype/order metadata and a
SHA-256 digest. A certificate is invalid if a referenced artifact is missing,
has a mismatched digest, contains NaN/Inf, or lacks a version id. The artifact
schema has a version and a round-trip validator.

## 10. Delivery sequence and acceptance gates

### Gate G0 — reviewed instantiation freeze

Freeze `W_G`, `Y`, `D_G`, provenance normalization, role channels, weights,
norms, tolerances, hardener, perturbation family, artifact schema, and the
validation cohort below. Pass requires the traceability table to cover every
T5 section 9, T6 section 8, and T7 section 8 obligation. In this plan,
`T5 §9.1` through `T5 §9.6` mean numbered items 1 through 6 inside T5's single
§9; they are traceability labels, not source-document subsections. No scored
validation may begin before this gate.

The validation cohort is copied by value into `spec.py` and the validation
manifest; it is never imported dynamically from either existing list:

```
VALIDATION_WORLDS = (
  "rule_1", "rule_2", "rule_3", "rule_4", "rule_5", "rule_6",
  "rule_7", "rule_8", "rule_9", "rule_10", "rule_11", "rule_12",
  "rule_13", "rule_14", "rule_15", "rule_16", "rule_17", "rule_20",
  "rule_23", "rule_24", "rule_25", "rule_26", "rule_27", "rule_28",
  "rule_29", "rule_30", "rule_31", "rule_32", "rule_33", "rule_34",
  "rule_35", "rule_36", "rule_37", "rule_38", "rule_39", "rule_40",
  "rule_41", "rule_42", "rule_45", "rule_46", "rule_47", "rule_48",
  "rule_49", "rule_50",
)
```

This is the current 44-world `multiweb_graphlog.HELDOUT` cohort, explicitly
including `rule_20` and `rule_27`. Their `seed=0` draws remain development data;
only newly generated draws can enter G6.

### Gate G0b — pre-G1 boundary and baseline notarization

Two prerequisites are real implementation work and must finish before G1:

1. Refactor the opaque ingest/anchor/rendering boundary described in §6 and
   pass the no-gold reachability and serialization tests. Verifying the current
   `pick_anchors` interface is insufficient because that interface is known to
   expose `perm_a`/`perm_b`.
2. Create `results/graphlog-certified/baselines/manifest.json`. The existing
   artifacts have no digest fields today. The manifest records raw SHA-256,
   canonical semantic SHA-256, byte size, schema, and producing code/data ids
   for `multiweb-graphlog`, frozen graded GraphLog, rule_20 factorial/episode
   sets, and rule_27 diagnosis/graded-causal artifacts. The semantic hash uses
   an explicit exclusion list for nondeterministic metadata such as elapsed
   time. Reproduction commands and expected headline/per-episode fields are
   part of the manifest.

G5 baseline consistency compares regenerated semantic hashes and expected
fields against this notarized manifest. It does not pretend that hashes were
already present in the historical result files.

### Gate G1 — exact structural layer

Implement scope/support closure, the extension CSP, target projection, and
P1/P2 adapters. Pass requires exhaustive agreement with hand-enumerated small
fixtures, explicit fail-closed `UNKNOWN` handling as a runtime concession,
relabeling invariance, provenance normalization, and no evaluation-gold
dependency. Reports distinguish T1 whole-extension classification from the
T4/T7 target projection and target-set verdict.

### Gate G2 — T5 operator

Implement assembly, boundary, exact kernel test, spectral bounds, local solver,
and stopping certificate. Pass requires all T5 tests; every field accepted as
unique has exact full column rank, a positive certified spectral lower bound,
and a tolerance-backed error radius. Fixed rounds or initialization-dependent
selection are release blockers.

### Gate G3 — T6 comparison and capacity

Implement the exact/enriched algebra and compile `D_G`. Pass requires 100%
named operation coverage, independently computed local constants, successful
nodewise tube checks, observed errors no larger than certified budgets on all
development fixtures, and an explicit separation verdict. A failed separation
verdict rejects the enrichment for that behavior class but is a valid,
non-crashing research outcome.

### Gate G4 — T7 commitment and retraction

Implement all six gates, joint budgets, abstention, ledger, and replay. Pass
requires zero commits with a missing premise, zero deterministic tie commits,
complete provenance on every event, and byte-identical live commitments after
retraction/replay. No direct `HARD_SIM` call may be reachable from the
certified runner.

### Gate G5 — development vertical slice

Run `rule_20/seed=0`, then `rule_27/seed=0`. Pass for implementation means
baseline consistency, complete artifacts, and internally valid certificates;
it does not require improved accuracy. Research outcomes are reported
separately:

- false current hardening events should abstain unless their new structural
  and margin premises genuinely pass;
- at least one synthetic and one real non-anchor target must certify, or the
  package is reported as vacuous and G6 does not claim usefulness;
- query accuracy is joined against discrete and existing graded baselines,
  with per-episode flips and abstentions, not only a mean.

The usefulness hypothesis has a development-data motivation: rule_20's best
joint `C+R` factorial cell retained frozen soft similarity and scored `0.669`,
above the discrete ensemble's `0.659`. This datum is neither validation nor a
license to tune constants; it explains why G6's primary usefulness comparison
is non-arbitrary.

Rule_20 and rule_27 may guide debugging and regression expectations, but no
constant may be selected from them and then described as validation.

### Gate G6 — pre-registered virgin validation

After code and G0-G5 artifacts are frozen, write and commit a validation
manifest before generating a fresh master view seed. The manifest embeds the
literal 44-name `VALIDATION_WORLDS` tuple frozen at G0 and expands one master
seed deterministically by `SHA-256(master_seed || world_name)`; neither
`graphlog.DEFAULT_WORLDS` nor a dynamically read `multiweb_graphlog.HELDOUT`
may choose the cohort at run time. The seed and all generated draws must be
absent from prior artifacts and exploratory logs. No replacement or deletion
of an unfavorable draw is allowed. A new external dataset requires its own
pre-registered study and cannot replace this cohort after any G6 outcome is
seen.

Validate premises before accuracy:

1. structural classification completion and target state counts;
2. T5 kernel, spectrum, conditioning, solver tolerance, and residual rates;
3. T6 operation coverage, tube validity, root-budget distribution, and
   separation rate;
4. T7 policy/margin outcomes, abstention reasons, certificate coverage, and
   evaluation-only false-commit count;
5. only then, query accuracy against the discrete and frozen graded baselines.

The implementation gate is: every item labeled `CERTIFIED` passes all premises
and artifact validation, with zero evaluation-side false positive identity
commits. Abstention is allowed but reported. Non-vacuity requires at least one
real non-anchor certified identity in the frozen validation block; otherwise
the theory instance is operationally correct but empirically uninformative.

The pre-registered research comparisons are:

- **primary usefulness:** replacement mean query accuracy is no worse than the
  discrete ensemble on the paired virgin draws;
- **secondary usefulness:** replacement mean query accuracy is no worse than
  the existing graded baseline;
- **coverage:** report the fraction of structurally positive singleton targets
  that become certified, with a paired bootstrap interval;
- **safety:** report commit precision and a one-sided interval even when the
  observed false-commit count is zero.

Failure of a usefulness comparison rejects or narrows this enrichment; it does
not license relaxing a theorem premise. Failure of certificate soundness blocks
release and requires a defect investigation.

## 11. Obligation review

The plan covers the current-implementation exclusions as follows.

| source obligation | planned discharge |
|---|---|
| T5 §9.1 construct complex/stalks/metrics/restrictions/boundary | §§3.1, 6-7; `linearization.py` |
| T5 §9.2 replace nonlinear loop with Dirichlet solver | §3.2; `t5.py` |
| T5 §9.3 kernel per component | exact rational rank plus operator-component report |
| T5 §9.4 `lambda_max` and valid step | independent spectral/row-sum upper bounds |
| T5 §9.5 `lambda_min` or residual-to-error stopping | positive lower bound and tolerance certificate |
| T5 §9.6 leave hardening to T7 | no hardening in T5/T6; §5 owns it |
| T6 §8 finite `D` | explicit finite `D_G`, max path five |
| T6 §8 named operator | T5 commutator field, not Sinkhorn |
| T6 §8 expose every operation | translation, composition, two aggregations, two decoders |
| T6 §8 local comparison table and recursive budgets | §§4.1-4.2 and `comparison.json` |
| T6 §8 separation before scoring | §4.2, G3, `separation.json` |
| T7 §8 satisfy T5/T6 first | fixed gate order in §5 |
| T7 §8 define `c_Y`, `H_Y`, `Permit_P` | §§1-2 and §5 |
| T7 §8 uniform margins and perturbation radii | §5, including joint tubes |
| T7 §8 abstain on every failed premise | typed branch tests and G4 |
| T7 §8 complete audit and exact retraction | ledger, artifacts, replay tests |

Review findings that remain implementation risks, not missing plan items:

1. The commutator linearization may have an uncontrolled kernel or fail
   `D_G` separation on real worlds. The correct phase-1 result is abstention
   and rejection of this enrichment, not a ridge or heuristic tie-break.
2. Exact extension classification can grow combinatorially. Target-directed
   pruning is allowed only with an exhaustion certificate; resource exhaustion
   is `UNKNOWN`.
3. Numerical spectral certification is the highest-risk shared component.
   It must be reviewed independently before any T7 artifact is called
   certified.
4. Query accuracy is not implied by T5-T7. Keeping premise gates, safety,
   coverage, and accuracy as separate reports prevents an accuracy gain from
   masking a failed certificate or a perfectly safe all-abstain system from
   being called useful.
5. T2 composition closure remains a separate optional theory task. This plan
   neither assumes nor silently implements it.

With those explicit failure routes, the plan is ready to enter G0 review and
then implementation. The first code milestone is G0b's opaque-boundary
refactor and baseline notarization; theorem-neutral runtime types and the exact
`rule_20` instantiation artifact follow, then T5—not a change to the existing
graded loop.
