"""The falsification benchmark (see docs/falsification-plan.md).

Everything under this package exists to answer one question honestly:

    What does fixed-algebra transport + holonomy contribute beyond a
    provenance-aware graph with statistical rule induction?

``world`` generates the frozen benchmark stream; ``baselines`` implements the
competitors over gold parses; ``run`` trains every system on the same stream
and scores the pre-registered query families. The generator is seeded and
deterministic; the plan document records the predictions made BEFORE the
first comparative run.
"""
