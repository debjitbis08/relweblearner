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
  algebra.py     # frozen algebra: IntegerGroup(Z, +, dagger=negate); Algebra ABC
  web.py         # Web as a projection of a commitment log; 3 moves; fork() for simulate
  holonomy.py    # BFS potential, defect extraction, holonomy, defect-mass objective
  growth.py      # (P1) persistence detector -> minimal grow; fork-scored rewire
  number.py      # (P1b) NumberLearner: bare episodes -> derived MATCH/ONEMORE -> number web
  sectors.py     # (P2) per-relation transport inference: symmetric / antisym / motif
  types.py       # (P2') unlabeled relation-type discovery: refinement + disjointness
  datasets/      # generators: counting, arithmetic, sectors, bare (unlabeled web)
  baselines/     # (P3+) TransE / ComplEx
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

See `docs/scaling.md` for the distribution / web-scale / volunteer-computing
direction, and `docs/design-log.md` for decisions & reconciliation notes.

Next: **P3** — compositional holdout vs TransE/ComplEx baselines (the headline
sample-efficiency figure; needs a small torch-CPU baseline).
