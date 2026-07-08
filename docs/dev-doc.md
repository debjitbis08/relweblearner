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
- **Collection / pairing episode**: the barest observation format. A
  collection is a set of opaque object ids presented together. A pairing
  episode presents two collections plus a set of pairing edges between
  their objects (each object used at most once). The learner computes
  leftovers itself. NO node in the input stream is ever a number, and no
  relation in the input stream is ever named.
- **Simulation (fork-score-discard)**: because the web is a projection of
  an immutable log (invariant 5), it can be FORKED cheaply. A simulation
  applies candidate moves to a fork, scores the result (defect mass, size),
  and discards the fork. Nothing is committed to the real log unless the
  score clears a policy. A simulated act emits a trace flagged
  counterfactual ('cf'); imagined episodes are episodes.
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
4. **No silent operations (reflection is constitutive).** Every operation
   of every web -- edge addition, loop check, merge, growth, query walk,
   comparison -- MUST emit a trace episode in the standard observation
   format (collection_1, collection_2, pairing) onto the same stream as
   world episodes. One event bus; one parser; zero branching on origin.
   Emission is free and unconditional (it defines what an operation is);
   CONSUMPTION of traces is an ordinary act drawn from a bounded attention
   budget. A web too small to repair anything still emits. CI test: every
   public method appends >= 1 well-formed episode; the world-episode
   parser accepts every trace episode unchanged. Reference:
   experiment0f_reflection.py.
5. **Belief/data separation (event sourcing).** The episode log is
   immutable and append-only; the web (merges, motifs, growth) is a
   PROJECTION of the log. Every committed inference stores its
   justifying episodes. Any belief must be reproducible by replaying the
   log and revocable by replaying with an exclusion set. Never mutate
   beliefs in place in a way that cannot be rebuilt from the log.
6. **Commitment policy (do not be eagerly trusting).**
   - Single-witness inferences are PROVISIONAL; commit a merge only at
     > = 2 independent supporting episodes (threshold k, default 2).
   - On a genuine contradiction (e.g. a class ONEMORE of itself),
     LOCALIZE: greedily find the minimal set of match-edges whose
     exclusion dissolves the contradiction (each step: exclude the edge
     whose removal minimizes remaining contradictions), then rebuild by
     replay-with-exclusions. Excluded episodes are flagged in the log,
     never deleted. Reference: experiment0h_adversarial.py.
   - Report collateral retraction (clean edges excluded alongside the
     lie) as a metric; it is the price of recovery, keep it logged.
7. **Bus provenance.** Trace episodes live in a reserved namespace
   (act-ids are generated only by the learner). External episodes
   claiming the act namespace are rejected at ingestion. CI test:
   attempt an external write into the act namespace; it must fail.
8. **Simulate before committing consequential moves.** Any non-trivial
   move (a merge, a growth, a motif reification) is first applied to a
   FORK of the projection and scored; it is committed to the real log
   only if it clears policy (default: introduces zero new contradictions,
   or strictly reduces defect mass). Simulated acts emit cf-flagged
   traces on the shared bus and MUST NOT alter the real projection. This
   is a seam over existing parts (fork = invariant 5; moves = invariant
   2; score = invariant 8/defect mass), not a new subsystem. Known limit:
   simulation catches only conflicts with ALREADY-KNOWN structure -- it
   detects incoherence, never non-correspondence. Reference:
   experiment0i_simulate.py.
9. **The learning signal is defect persistence.** The objective is total
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
                    #   play  - propose closures, SIMULATE each on a fork,
                    #           commit only the best-scoring (invariant 8)
  datasets/
    counting.py     # generators: collections of opaque objects + pairing
                    #   episodes (NO number nodes; see P1b). Staged
                    #   presentation schedules (small-collections-first).
    arithmetic.py   # synthetic chain webs -- UNIT TESTS ONLY for the
                    #   growth engine (P1); superseded by constructed
                    #   number classes (P1b) as the data source for P2+
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

### P1b — Constructing number from counting (one-two days)

Numbers must never be input nodes. The stream contains only pairing
episodes over collections of opaque objects (see glossary). The learner
derives two predicates itself: MATCH (the pairing saturates both sides)
and ONEMORE (saturates one side, exactly one object unpaired on the
other). Pipeline:

1. quotient: union-find merge over MATCH evidence -> emergent class
   nodes. These classes ARE the numbers; they appear in the growth/merge
   log, not in the input.
2. successor: ONEMORE descends to classes. Use successor INJECTIVITY as
   an inference rule: a class with two successor-classes forces those
   targets to merge -- guarded: never merge two classes that have
   ONEMORE evidence between each other (that would make a class ONEMORE
   of itself, a genuine contradiction to be reported, not repaired).
3. counting routine: to number a fresh collection, pair it against
   class representatives along the chain until saturation; its number
   is the position. Log query cost.
4. staging: run a small-collections-first presentation schedule and log
   class crystallization order.
   Reference implementation: experiment0e_number.py.
   **Accept (e1b):** (a) grep-proof: no input token is a numeral; (b) final
   quotient classes are pure by hidden size and the successor graph is a
   single chain isomorphic to an initial segment of the naturals; (c) a
   fresh collection is numbered correctly by the chain-pairing routine;
   (d) staged schedule yields staged crystallization (classes for 1 and 2
   exist while larger collections remain singletons) before full data;
   (e) a double-tagged (corrupt) pairing episode produces exactly the
   'class ONEMORE of itself' defect and is quarantined, never repaired by
   merging. Downstream phases (P2, P3) must consume the CONSTRUCTED class
   chain, not synthetic number nodes; subtraction probes (P1) then trigger
   growth at the quotient level (new classes with no witnessing collections
   -- the learner's negative numbers).

### P2 — Symmetry-sector inference (one day)

Given loop assertions only, solve for a per-relation-type transport over
Z (sympy integer least squares / nullspace). A relation observed in both
directions between the same pair forces 2g = 0, i.e. g = 0: classify it
symmetric; relations with nonzero transport are antisymmetric. Report
classification vs ground truth. Add the stressor: `double` cannot carry
any constant additive transport — correct behavior is that the solver
REJECTS type-homogeneity for it (residual stays high) and the learner
represents doubling as a motif (a family of edges) instead. Document it.
Induction must be noise-tolerant: replace exact consistency with a
best-fit-under-exception-budget rule (an exception costs a fixed
description-length penalty; the winning hypothesis minimizes total
cost). A single mislabeled example must not be able to eliminate the
true hypothesis.
**Accept (e2):** same/succ classified correctly from >= 30 random loop
observations, 20/20 seeds; `double` flagged non-homogeneous; with one
adversarially mislabeled training example injected, the induced rule is
unchanged in >= 18/20 seeds.

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

### P6 — Reflection experiments (one-two days)

With invariant 4 in place, reflection needs no new machinery -- only
attention allocation. Feed the learner's own trace stream back through
the ordinary ingest/compare path, mixed with world episodes, and test:
(a) classes crystallize over the learner's own acts (merge-acts,
growth-acts, defect-reports) using UNCHANGED type-discovery machinery;
(b) the attention budget bounds actual regress: emitted-but-unconsumed
backlog stays finite and consumption never exceeds budget;
(c) self-derived quantities appear: the learner counts its own defect
reports with the number chain it constructed in P1b (the system measuring
itself with its own ruler).
**Accept:** all three logged, with (a) scored as purity of act-classes
against hidden operation types.

### P6' — Simulation & lookahead (one-two days)

Implement the fork-score-discard seam and route `play` through it.

1. imagine-then-commit: every consequential move is scored on a fork;
   commit only if policy clears. Verify the fork never mutates the real
   projection (property test, 1000 random move sequences).
2. lookahead: given >1 candidate move for an open query, simulate each
   and pick least (defect, size); commit only the winner.
3. counterfactual provenance: simulated acts are cf-flagged on the bus;
   the cf set and the real set never cross-contaminate (CI test). The
   learner can count its own simulations with the P1b number chain.
4. rehearsal-refusal: a move whose simulation shows a contradiction is
   refused, with a logged reason.
   Optional depth: n-step lookahead (simulate a move, then simulate moves on
   that fork) with a branching budget; report solution quality vs budget.
   **Accept (e6'):** honest moves commit, incoherent moves are refused with
   reasons, lookahead picks the min-defect candidate 20/20 seeds, and no cf
   act ever appears in the committed projection. Document the known limit
   (coherence != correspondence) in results, tying it to the P7 consistent-
   lie curve: simulation raises the cost of an INCONSISTENT lie to infinity
   (auto-refused) but does nothing to a fully CONSISTENT one -- only the
   ensemble does.

### P7 — Adversarial audit (one-two days)

Attack the learner deliberately; measure detection, damage, recovery.

- Poison-rate sweep: inject corrupt pairing episodes at rates 0.1%-5%.
  Log detection rate, time-to-detection (episodes until first genuine
  defect), quotient purity before/after retraction, collateral
  retraction count. **Accept:** purity restored to 1.0 at <= 1% poison;
  detection rate 100% for contradictions reachable by observed loops.
- Repeat-lie attack: the same false pair asserted many times. Must cost
  the attacker; must not cost the learner (parallel evidence on one
  pair is a single cut).
- Consistent-lie cost curve: minimum number of coordinated fake
  episodes needed for a false merge to survive retraction, as a
  function of the target region's loop connectivity. This curve is the
  system's core security property (lies must out-fake every loop
  through the region); plot it.
- DoS caps: contradiction-flood (must not fragment concepts without
  bound -- split budget) and unclosable-query flood (must not grow
  without bound -- growth budget). **Accept:** both budgets hold and
  the learner degrades to refusal, not to corruption.
  Honest limit to document in results: a fully consistent lie -- a
  coherent alternative web with no contradicting loops -- is
  indistinguishable from truth for a single learner. Coherence is
  checkable; correspondence requires independent sources (the multi-web
  ensemble of P5/P8 is the real defense, cross-web interface defects the
  cross-examination).

### P8 (stretch) — Ensemble geometry

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
