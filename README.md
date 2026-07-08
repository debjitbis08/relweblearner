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
  algebra.py     # frozen algebra: IntegerGroup(Z, +, dagger=negate); Algebra ABC
  web.py         # Web + the three moves (relabel/rewire/grow), observations, growth log
  holonomy.py    # BFS potential, defect extraction, holonomy, defect-mass objective
  datasets/      # (P1+) generators: arithmetic, kinship
  baselines/     # (P3+) TransE / ComplEx
experiments/     # original standalone proof-of-concept demos (experiment0*.py)
tests/           # acceptance tests, one module per phase
results/         # CSVs + plots
```

## Setup

Dependencies are managed with Poetry (an in-project `.venv/` is created):

```bash
poetry install
poetry run pytest        # run the acceptance suite
```

## Status

- **P0 — core substrate: complete.** `algebra.py`, `web.py`, `holonomy.py` plus
  the acceptance suite: consistent web → zero defects; one false-identity edge →
  exactly one independent defect class; the **relabel-invariance property test**
  (1000 random trials) that Section 6 mandates stays in CI for every later phase.

Next: **P1 — growth engine** (persistence detector → minimal `grow`; the `e1`
subtraction-probe experiment).
