# relweblearner — Fixed-Algebra Growing-Web Learner

A learner whose **algebra is frozen** and whose only degree of freedom is the
**web** (a graph with algebra-valued edges). Loops whose transport does not
compose to the identity are *defects*; defects are the learning signal, and the
only responses are three costed moves — `relabel` (free), `rewire` (cost 1),
`grow` (cost K). See [`docs/dev-doc.md`](docs/dev-doc.md) for the full design
and phase plan.

## Layout

This repo uses a `src/` package layout (a deliberate improvement over the flat
tree sketched in the dev doc):

```
src/relweblearner/
  episode.py     # the bare (coll1, coll2, pairing) atom — one homoiconic format
  journal.py     # append-only bus/log: emit traces, ingest world eps, replay-with-exclusions
  algebra.py     # frozen Algebra ABC: IntegerGroup, CyclicGroup, KleinFour, inverse monoids
  sweep.py       # (P4) per-algebra diagnostics: bloat, false-inverse, undefined-loop, relabel
  web.py         # Web as a projection of a commitment log; 3 moves; fork() for simulate
  holonomy.py    # BFS potential, defect extraction, holonomy, defect-mass objective
  growth.py      # (P1) persistence detector -> minimal grow; fork-scored rewire
  number.py      # (P1b) NumberLearner: bare episodes -> derived MATCH/ONEMORE -> number web
  sectors.py     # (P2) per-relation transport inference: symmetric / antisym / motif
  types.py       # (P2') unlabeled relation-type discovery: refinement + disjointness
  holdout.py     # (P3) compositional-holdout eval: web (exact) vs KGE baselines
  ensemble.py    # (P5) N-web interference + dynamic ensemble (learned web count)
  reflection.py  # (P6) act-classes from own traces; attention budget; self-count
  simulate.py    # (P6') fork-score-discard play loop: imagine-then-commit, lookahead
  audit.py       # (P7) adversarial: k>=2 gate, localize-and-replay, DoS budgets
  geometry.py    # (P8) graph-Laplacian eigenmaps; ensemble magnitude-axis stability
  language.py    # (PL) reading & writing: separate one-way web; ground/ostend/read/write
  society.py     # (PS) multi-agent: dyad naming game, citation gossip, population, disagreement
  invention.py   # (P7') content-vs-error defects: bank content, retract error, invention census
  datasets/      # generators: counting, arithmetic, sectors, bare, holdout, kinship, language, society
  baselines/     # (P3) TransE / ComplEx (numpy, Adam)
experiments/     # standalone proof-of-concept demos (experiment0*.py)
tests/           # acceptance tests, one module per phase
results/         # CSVs + plots
docs/            # dev-doc.md (spec), design-log.md (decisions/reconciliation), scaling.md
```

## Setup

Dependencies are managed with Poetry (an in-project `.venv/` is created):

```bash
poetry install
poetry run pytest        # run the acceptance suite
```

## Status

- **P0 — core substrate (re-founded on the event-sourced substrate): complete.**
  Beyond the original holonomy kernel, `web.py` is now a **projection of an
  append-only commitment log**, every act emits a **bare trace episode** onto a
  shared `Journal`, and `fork()` gives a simulate-before-commit seam. The
  22-test acceptance suite covers:
  - holonomy kernel — consistent web → 0 defects; one false-identity edge →
    exactly one independent defect class;
  - the **relabel-invariance property test** (1000 trials) — the correctness
    discipline for the whole codebase;
  - **inv 4** every act emits ≥1 well-formed episode; traces parse like world
    episodes (homoiconicity);
  - **inv 5** replay reproduces the web; excluding a commitment (or its
    justifying episode) revokes exactly it;
  - **inv 7** external writes into the act namespace are rejected;
  - **inv 8** a fork never mutates its parent (1000 random move sequences).

- **P1 — growth engine: complete.** `growth.py` — a persistence-gated,
  minimal-growth engine. A query walk that falls off the web is an obstruction;
  the engine spends `P` rounds trying the cheap moves (relabel, proven futile;
  rewire, scored on a `fork()`) before paying to `grow` the fewest nodes that
  discharge it, wired with the frozen algebra. `e1` accepted:
  (a) refuses growth while probes stay in-web; (b) grows exactly `|deficit|`
  nodes on `3-5`; (c) ≥20 unseen arithmetic facts through the invented nodes are
  exact zero-shot; plus a sharp growth-vs-position threshold
  (`results/e1_growth.{csv,png}`) and a rewire-discharges-without-growth case.

- **P1b — constructing number from counting: complete.** `number.py` — the
  reconciliation made concrete. The learner ingests only bare pairing episodes,
  derives MATCH/ONEMORE from leftovers, and **projects** them onto a web:
  MATCH→merge (the union-find quotient *is* the merge projection), ONEMORE→`+1`
  succ edge. The emergent class nodes are the numbers. A false MATCH (poison)
  welds two size-classes and surfaces as a `+1` **holonomy self-loop** — "class
  ONEMORE of itself" — so invariant 9 (defect mass) literally detects counting
  contradictions. `e1b` accepted: (a) no numeral tokens; (b) pure classes +
  single naturals chain; (c) fresh collection counted by chain-pairing;
  (d) staged crystallization (a "2-knower" before full data); (e) poison →
  self-loop defect, quarantined and **retractable by replay-with-exclusion**
  (`results/e1b_number.{csv,png}`).

- **P2 — symmetry-sector inference: complete.** `sectors.py` — each loop
  observation gives a relation a transport sample `coord(b) - coord(a)` (the
  coordinates come from the P1b chain); the relation's sector is read from
  whether a single transport fits under an exception budget: `g=0` →
  **symmetric** (the `2g=0` signal), `g≠0` → **antisymmetric**, no constant fit
  → **non-homogeneous / motif**. `e2` accepted: same/succ classified 20/20
  seeds; `double` flagged a motif; one adversarial mislabel leaves the rule
  unchanged (20/20). End-to-end demo consumes a real P1b `NumberChain`
  (`results/e2_sectors.{csv,png}`).

- **P2' — unlabeled-relation type discovery: complete.** `types.py` — edges
  carry no labels; a relation type is a structural equivalence class. Degree-role
  **refinement** over-refines (WL degree-pair: 4 classes for 3 true types);
  **disjointness compression** (mutual exclusivity — hubs merge iff their
  member-sets are disjoint) recovers the truth. Generic coverage → the mixed web
  (chain + colors + plants) recovered at purity 1.0; sparse coverage conflates,
  and the conflation-vs-coverage curve falls 1.0 → 0.13 as crossing observations
  arrive (`results/e2p_types.{csv,png}`).

- **P3 — compositional holdout vs baselines: complete.** Train `n-(+k)->n+k`
  for k∈{1,2}; hold out all k=5. The web scores `+5` by transport composition —
  **Hits@1 = 1.0 by construction, zero parameters** for the held-out relation.
  KGE baselines (dim 32) must compose learned embeddings: **ComplEx** memorizes
  training perfectly yet composes `+5` only to Hits@1 0.49 / Hits@10 0.85;
  **TransE** 0.15. The gap is the headline sample-efficiency figure
  (`results/e3_holdout.{csv,png}`). Baselines are numpy (Adam inline), not torch.

- **P4 — algebra sweep: complete.** Swap ℤ for finite involutive monoids
  (`Z_2`, `Z_4`, `Z_2×Z_2`, the symmetric inverse monoid with *partial*
  composition, a truncated free involutive monoid) behind the **unchanged**
  frozen `Algebra` interface — no web/holonomy/growth changes. The pre-committed
  tradeoff frontier (`bloat = C/D` vs `false_inverse_rate`) is the finding:
  **Z** (no bloat, hallucinates inverses) and the **inverse monoid** (honest
  partial inverses + flagged undefined loops, at a bloat cost) are non-dominated;
  small groups bloat *and* hallucinate. Relabel-invariance holds for every
  algebra (`results/e4_sweep.{csv,png}`).

- **P5 — N-web dynamic ensemble: complete.** `ensemble.py` generalizes
  interference beyond pairwise: the union of N webs + cross-web *identifications*
  is one graph, and an interface defect is a holonomy defect on it. The learner
  finds the mismatch-minimizing interface map by consensus (isolating a poisoned
  identification), **transfers through the fabric with zero shared parameters**
  (holdout answerability 0.33 → 1.00), resolves the poison by **split**, and —
  the dynamic part — runs a stimulus stream where the **number of webs is
  learned**: persistence-gated merges/splits evolve the count `3 → 2 → 1 → 2`
  (`results/e5_interference.{csv,png}`).

- **P6 — reflection: complete.** With invariant 4 already emitting every act as
  a bare episode, reflection needs no new machinery. `reflection.py` feeds the
  learner's own act traces back through the ordinary path: **(a)** act-classes
  crystallize at **purity 1.0** by the same structural type-discovery used for
  relations (and act traces parse like world episodes — homoiconicity); **(b)**
  an **attention budget bounds the regress** (emission never stops, consumption
  is capped, backlog finite); **(c)** the learner **counts its own defect
  reports** with the P1b number chain (1/2/3 → 1/2/3) — self-measurement with
  its own ruler (`results/e6_reflection.{csv,png}`).

- **P6' — simulation & lookahead: complete.** `simulate.py` routes consequential
  moves through the `fork` seam (fork → apply → score by holonomy → discard):
  **imagine-then-commit** (commit only if defect mass doesn't rise, else refuse
  with a logged reason), **lookahead** (score candidates on forks, commit the
  least `(defect, size)` — **20/20 seeds**), and **cf isolation** (simulated acts
  are cf-flagged, never enter the committed stream, and are countable with the
  P1b chain). Documents the limit: a *consistent* lie has 0 defect and cannot be
  refused — coherence is checkable, correspondence needs the ensemble
  (`results/e6p_simulate.{csv,png}`). Fixed a latent merge-semantics bug in the
  substrate along the way (merge now genuinely collapses the graph).

- **P7 — adversarial audit: complete.** `audit.py` — the **k≥2 provisional-
  commitment gate** (resolving the P1b deviation) is the primary defense:
  thinly-witnessed poison never enters the quotient, so purity stays **1.0 across
  the 0.1–5% sweep**. **Localize-and-replay** (greedy min-cut, support-tie-broken)
  is the fallback for lies that clear the gate, with collateral logged as the
  price of recovery. **Repeat-lie is one cut** (attacker pays N, learner pays 1);
  the **consistent-lie cost curve is exactly linear in loop connectivity** —
  a coherent lie must out-fake every loop through the region (the core security
  property); and DoS budgets degrade the learner to *refusal*, not corruption.
  Documented limit: a fully consistent lie is undetectable to a single learner —
  correspondence needs the ensemble (`results/e7_adversarial.{csv,png}`).

- **P8 — ensemble geometry (stretch): complete.** `geometry.py` — graph-Laplacian
  eigenmaps of each learner's relational graph recover a **magnitude axis** (the
  Fiedler vector orders the numbers). The axis is real in every run but its
  **orientation is arbitrary**, so the raw ensemble mean washes out — while the
  **sign-aligned ensemble** recovers a stable monotonic axis (spread 0.11 → 0.05).
  Concept geometry is stable only across the ensemble, exactly the hypothesis
  (`results/e8_geometry.{csv,png}`).

- **PL — reading & writing (language): complete.** `language.py` — the
  standalone read/write spec (`docs/spec-read-write.md`), off the numbered
  dev-doc roadmap (whose P9 is Perception & data feed — unrelated; handled
  later). **Language is a separate web**, one-way dependent on the
  concept web (a skill atop concepts): deleting language leaves every
  concept-web test passing; reading cannot ground without concepts, and surface
  forms share no namespace with concept ids (both CI-tested). Six layers from a
  raw syllable stream: **L1** boundaries from transition-probability dips
  (precision/recall 1.0, exact lexicon; a logged degradation curve 1.00 → 0.71
  as words share units, recall pinned at 1.0) + novel-word segmentation by
  subtraction; **L2** the closed (frame) class **discovered, not given** (the
  count maximizes frame-shape regularity); **L3** grounding by structure alone
  (joint WL + frame↔relation bijection) that resolves meanings **exactly up to
  the concept web's automorphism orbits** — 7/11 grounded, the unresolved
  residue equal to a **brute-force orbit computation** (the formal gavagai
  limit); **L4** ostension (budget = #orbits; one pointing per orbit cascades
  7 → 9 → 11); **L5** reading as confirm / teach / fast-map (single-exposure
  novel word → correct) / refuse-a-false-claim; **L6** writing = inverse map +
  **read-back before commit**, refusing ambiguous orbit words, with the
  adjunction laws `read(write(f)) == f` and `write(read(u)) ~ u` holding at
  **0 violations** over the full expressible set (`results/el_readwrite.{csv,png}`).

- **PS — society (multi-agent layer): complete.** `society.py` — the standalone
  society spec (`docs/spec-society.md`), off the numbered roadmap. Multi-agent is
  forced *before* perception-at-scale by three limits the earlier phases prove:
  solipsism debt (grounding only up to orbits), coherence≠correspondence
  (disagreement is the only native truth signal), and ensemble science.
  **S0** agents share no memory (message-passing only); provenance is
  per-**owner** (the Sybil boundary). **S1** a dyad naming game with **lateral
  inhibition** converges to one shared lexicon (communication success 0.86 →
  1.00), cross-agent adjunction `read_B(write_A(f)) == f` at 1.0, and **peer
  ostension discharges the solipsism debt** (unresolved orbits 2 → 1 → 0).
  **S3** citation-tracked gossip: every claim carries an **origin set**
  transmitted unchanged, commit needs ≥k **distinct origins** — a rumor (1 owner,
  50 tellings, 4000 gossip rounds) commits **0/24**, an independently-cited fact
  (6 owners) **24/24**, and 10 Sybils under one owner count as **1** origin.
  **S4** dialects form without contact (within 1.00, cross 0.00) and contact
  **creolizes only with inhibition** (1.00 vs a 0.35 adopt-only plateau — the
  failure mode the fix is tested against). **S5** a conflicting claim is logged
  as a queryable **interface defect** (both origin sets), resolved by origin
  weight, with own perception outranking testimony (`results/es_society.{csv,png}`).
- **P7' — content vs error defects (society §7 amendment): complete.**
  `invention.py` — a persistent holonomy class that **conflicts with no
  observation is CONTENT** (banked as structure), not error. Clock arithmetic
  (a counting chain glued to a wrap-around) carries winding **+12**, conflicts
  nothing, is banked, and answers modular queries (**11 + 3 ≡ 2 mod 12**); a
  poisoned merge ("class ONEMORE of itself") **conflicts with an observation**,
  so P7 localize-and-replay still retracts it (contradictions 24 → 0, purity
  0.80 → 1.00) — both in one run. Plus the invention census: banked content +
  posit-before-evidence confirmation rate (`results/es_invention.{csv,png}`).

**The dev-doc roadmap P0–P8 is complete**, plus the standalone **PL** (language)
and **PS** (society, incl. the **P7'** defect amendment) phases — 101 acceptance
tests, one substrate that never needed a redesign after P0. (P9 — Perception &
data feed — is now in the dev-doc and handled later; the society layer is the
independent truth-channel it depends on.) See `docs/scaling.md` for the
distribution / web-scale / volunteer-computing direction, and
`docs/design-log.md` for the decision & reconciliation log.
