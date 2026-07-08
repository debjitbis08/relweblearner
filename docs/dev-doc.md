# Fixed-Algebra Growing-Web Learner — Dev Doc

Execution plan for a coding agent. Python 3.11+, CPU only. Self-contained:
all concepts used below are defined in Section 0. Reference implementations
of the core mechanisms exist in `experiment0.py` (numeric domain),
`experiment0b_fruits.py` (partial relations), `experiment0c_learning.py`
(motif induction), `experiment0d_bare.py` (unlabeled-relation discovery);
read them first. Each phase has acceptance tests; do not proceed past a
failing phase.

## 0. Concepts & glossary (read first)

- **Web**: a graph W = (V, E). Nodes are opaque ids (no attributes). Each
  directed edge carries a value from a fixed algebra; every edge has a
  converse edge in the opposite direction carrying the inverse value.
- **Algebra**: the value set on edges, with composition, an identity, and
  an involution ("dagger" = converse). First implementation: the integers
  under addition (converse of +k is -k). Later: small finite monoids with
  involution. The algebra is FIXED; it is never learned or modified.
- **Transport of a path**: compose the edge values along the path.
- **Holonomy of a loop**: the transport around a closed path. A loop is
  _consistent_ if its holonomy is the identity (sums to 0 over Z).
- **Potential / relabeling**: an assignment phi: V -> algebra. Replacing
  each edge value g(u,v) by phi(u) + g(u,v) - phi(v) (over Z) changes no
  loop holonomy. Any transformation of this form is called a _relabeling_
  and is considered free/meaningless (a change of bookkeeping).
- **Defect**: a loop whose holonomy is not the identity. Because
  relabelings never change holonomy, a defect can only be removed by
  changing the web itself (rewiring or adding nodes). Defects are the
  learning signal. Independent defects can be enumerated via a cycle
  basis of the graph.
- **Observation**: an assertion from the data stream, either "this loop
  closes" (holonomy = identity) or "this loop does not close" / "these
  two nodes are distinct". Observations are immutable data; the learner
  may never delete one to escape a defect.
- **Motif**: a composite relation defined as a word over existing edge
  types, e.g. same-color(x,y) := exists c: has-color(x,c) and
  has-color(y,c) — equivalently the path x -> c -> y using an edge and a
  converse edge. Learned concepts are motifs, not new algebra operations.

## 1. Architecture invariants (never violate)

1. **The algebra is frozen.** One module `algebra.py` defines composition,
   identity, dagger, and the carrier (start: Z; later: finite involutive
   monoids behind the same interface). No other module may define or
   modify algebraic operations. No learned parameters live on edges, ever.
2. **Only the web mutates.** `web.py` owns nodes/edges. All learning is
   one of three moves with a fixed cost schedule:
   - `relabel` (cost 0): as defined above; must change no loop holonomy
     (assert this in tests).
   - `rewire` (cost 1): add/remove/merge edges among existing nodes,
     subject to never contradicting an observation.
   - `grow` (cost K >> 1): add new nodes (and their edges). K is a
     hyperparameter.
3. **Observations are loop-closure and distinctness assertions only.**
   No coordinates, no node attributes.
4. **The learning signal is defect persistence.** The objective is total
   defect mass over observed loops; `grow` fires only when a defect
   persists under exhaustive relabel+rewire within budget (persistence
   threshold P).

## 2. Repo layout

```
relweblearner/
  algebra.py        # frozen algebra: Group(Z), later FiniteInvolutiveMonoid
  web.py            # Web, the three moves, growth log
  holonomy.py       # potential assignment (BFS), defect extraction,
                    #   cycle basis, defect-mass objective
  learner.py        # control loop with three phases:
                    #   wake  - ingest observations, local defect checks
                    #   sleep - batch compression: relabel search,
                    #           node/edge-class merging (quotients)
                    #   play  - propose loop closures, test grow candidates
  datasets/
    arithmetic.py   # generators: chain webs; addition facts as loop
                    #   assertions; subtraction probes; doubling probes
    kinship.py      # kinship relations as loop assertions
  experiments/
    e1_growth.py    # forced-growth threshold
    e2_sectors.py   # symmetric/antisymmetric self-classification
    e3_holdout.py   # compositional holdout vs neural baselines
    e4_sweep.py     # algebra as independent variable
    e5_interference.py  # two webs, overlap mismatch, three resolutions
  baselines/
    kge.py          # TransE + ComplEx, small, numpy or torch-cpu
  tests/            # acceptance tests per phase
  results/          # CSVs + plots (matplotlib)
```

Dependencies: numpy, networkx, matplotlib, pytest. Optional: sympy
(integer linear systems), torch CPU (baselines only). Nothing else.

## 3. Phases

### P0 — Core substrate (half a day)

Implement `algebra.py` (Z with dagger), `web.py`, `holonomy.py`.
Holonomy: assign a potential phi by BFS per connected component; residual
edge mismatches are defects; extract independent defect classes via
networkx `minimum_cycle_basis` on the underlying graph.
**Accept:** consistent web -> zero defects; a single false-identity edge
-> exactly one independent defect class; relabel provably cannot change
any defect (property test over random potentials, 1000 trials).

### P1 — Growth engine (one day)

Persistence detector: a defect (or a query path that walks off the web)
surviving P rounds of relabel+rewire triggers `grow`. Growth must be
minimal: add the fewest nodes that discharge the obstruction (BFS over
completion candidates). Reference behavior: `experiment0.py`, demo B.
**Accept (e1):** chain web of nodes 0..9 + subtraction probe stream. The
system (a) refuses growth while probes stay inside the web, (b) grows
exactly |deficit| nodes on the probe 3-5, (c) zero-shot: after growth, 20
unseen arithmetic facts through the new nodes all hold exactly. Plot:
growth events vs probe-stream position — expected result is a sharp
threshold, not a drift.

### P2 — Symmetry-sector inference (one day)

Given loop assertions only, solve for a per-relation-type transport over
Z (sympy integer least squares / nullspace). A relation observed in both
directions between the same pair forces 2g = 0, i.e. g = 0: classify it
symmetric; relations with nonzero transport are antisymmetric. Report
classification vs ground truth. Add the stressor: `double` cannot carry
any constant additive transport — correct behavior is that the solver
REJECTS type-homogeneity for it (residual stays high) and the learner
represents doubling as a motif (a family of edges) instead. Document it.
**Accept (e2):** same/succ classified correctly from >= 30 random loop
observations, 20/20 seeds; `double` flagged non-homogeneous.

### P2' — Unlabeled-relation type discovery (one-two days)

Drop relation labels from the observation stream entirely: episodes are
unlabeled subgraphs; node identity across episodes is the only given.
Relation types = structural equivalence classes of edges, found by two
opposing operations: refinement (Weisfeiler-Leman-style role distinction;
tends to over-refine) and compression (merging edge classes; run in the
sleep phase). Implemented criterion for attribute-like relations: two hub
nodes belong to the same relation type iff their member-sets are DISJOINT
(mutual exclusivity within a type; overlap across types). Reference
implementation and a known failure mode: `experiment0d_bare.py` — under
sparse coverage, accidentally-disjoint hubs from different types get
conflated.
**Accept:** mixed unlabeled web (one chain + >=2 attribute partitions)
recovers ground-truth types at purity 1.0 under generic coverage; log the
conflation-vs-coverage curve (fraction of conflated runs as crossing
observations increase). Downstream phases must run on DISCOVERED types,
not given ones.

### P3 — Compositional holdout vs baselines (one-two days)

Dataset: entities 0..N (N=200), facts n -(+k)-> n+k for k in {1,2} as
training; all k=5 facts held out. The web learner should score exactly by
transport composition. Baselines: TransE and ComplEx (embedding dim 32,
standard negative sampling) evaluated on the held-out k=5 triples (MRR,
Hits@1).
**Accept (e3):** web learner Hits@1 = 1.0 by construction; record the
baseline gap. This is the headline sample-efficiency figure.

### P4 — Algebra sweep (two-three days)

Swap Z for candidates behind one interface `FiniteInvolutiveMonoid`:

- the cyclic groups Z_2 and Z_4, and Z_2 x Z_2,
- the symmetric inverse monoid on 2 and 3 points (partial bijections;
  composition may be undefined),
- free involutive monoid truncated at word length L (control).
  Fixed machinery, sweep the algebra, score each on: e1 threshold
  sharpness, e2 sector accuracy, e3 exactness, plus two diagnostics:
- web-size-per-concept (algebra too weak -> node bloat as the web
  compensates with witness nodes),
- false-inverse rate on deliberately partial relations, e.g. capital-of
  (algebra too strong -> hallucinated inverses).
  **Accept (e4):** a results table algebras x metrics, with the weak/strong
  tradeoff plotted as a frontier. No winner is prescribed; the table IS the
  finding. Pre-commit the tradeoff metric before running (Section 6).

### P5 — Two-web interference (two days)

Two webs A (arithmetic) and B (kinship) with a small shared interface
(candidate identifications: generation-shift <-> successor;
same-generation <-> same-count). Compare the two webs' transports on
loops through the shared nodes; a nonzero mismatch is an _interface
defect_. Implement the three resolutions:

- project: trust one web on the overlap,
- split: duplicate the shared node — the two webs meant different things,
- superpose: keep both readings with weights.
  Poison one identification deliberately.
  **Accept (e5):** (a) the learner finds the mismatch-minimizing interface
  map by search alone; (b) transfer: kinship training measurably reduces
  arithmetic holdout error strictly through the interface map, zero shared
  parameters; (c) the poisoned identification is resolved by split at a
  measurable threshold, and both split-off concepts are locally consistent
  afterward. Reference behavior: `experiment0.py` demo D and
  `experiment0c_learning.py` (autonomous split).

### P6 (stretch) — Ensemble geometry

Hypothesis to test: geometric structure of the learned concept space may
be stable only across an ensemble, not in any single run. Train an
ensemble of learners (different seeds and observation orders),
spectral-embed each web (graph-Laplacian eigenmaps), and test whether
concept geometry (symmetric/antisymmetric regions, a magnitude axis)
stabilizes across the ensemble even when it varies per run.
Embarrassingly parallel, CPU pool.

## 4. Metrics to log everywhere

- defect mass (total |holonomy| over observed loops), per step
- growth events: when, size, triggering defect class
- web size / concept count (bloat diagnostic)
- exactness on held-out compositions (Hits@1)
- for e5: interface defect norm before/after resolution; transfer delta

## 5. Compute budget

Everything above: laptop CPU. Largest run is P4 (sweep x seeds) — batch
of ~200 runs, each < 1 min at N=200 nodes: under an hour on 4 cores.
P3 baselines at dim 32 / N=200: minutes on CPU torch. No GPU anywhere.
If N is ever pushed to 10^5+ nodes with spectral embeddings, switch
`holonomy` to scipy.sparse before considering hardware.

## 6. Known risks / pre-commitments

- Partial composition (P4 partial-bijection candidates): the defect
  definition needs care where a composite is undefined; define defects
  only on loops whose composite is defined, and log the fraction of
  undefined loops as its own signal.
- Pre-commit the weak/strong tradeoff metric (P4 diagnostics) BEFORE
  running the sweep; do not tune it post hoc.
- The relabel-invariance property test (P0) is the correctness discipline
  for the whole codebase; keep it in CI and run it against every later
  phase.
- Observations are immutable: no code path may delete or down-weight an
  observation to reduce defect mass. If a defect looks unresolvable,
  growth (e.g. node splitting) is the sanctioned escape, never data
  deletion.
