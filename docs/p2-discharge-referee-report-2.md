# Referee report — the P2 discharge, round 2 (on the v3 direct simulation)

*Delivered inline 2026-07-14; preserved verbatim. Response:
docs/p2-discharge-referee-response-2.md.*

V3 is materially better and reproduces exactly, but I still see one scope problem and several
statistical/testing issues.

- High — the measured result is under A1 plus the specific E2b forgery, not A1 alone. A1 still defines
  pristine independently generated webs (docs/p2-discharge.md:34), while v3 runs _pipeline(), which
  mutates view 0 with add_overlap_forgery (src/relweblearner/bench/p2_validate.py:103). Therefore §13's
  broad claim that behavior is measured "under A1" (docs/p2-discharge.md:395) overstates the scope. The
  evidence supports A1 plus this exact seeded E2b intervention—its bridge density, community selection,
  and weights. Either name that combined assumption/process or narrow the discharge explicitly to the
  E2b empirical instance.

- Medium — the bootstrap intervals omit model-sample uncertainty. bootstrap_pi() samples future 50-world
  blocks from the empirical 396-world distribution as if that distribution were known (src/
  relweblearner/bench/p2_validate.py:432). A predictive interval should also account for uncertainty in
  estimating the distribution from those 396 worlds. A simple prediction-error bootstrap widened the
  false-count PI from [2,16] to approximately [1.48,16.76]. The observed 9 still passes comfortably, so
  this does not change the result, but "99% predictive interval" is currently too strong.

- Medium — the ε_map rule-of-three bound again assumes independent edge trials. The zero-cell bound uses
  3 / wn (src/relweblearner/bench/p2_validate.py:468), although wrong-mapped edges share nodes and
  worlds. The overall total-false-obstruction gate correctly absorbs mapping errors, so the main verdict
  is unaffected; the reported ε_map upper bound should be cluster/world-based or labeled descriptive
  rather than a bound.

- Medium — measured detection uncertainty is not reported. V3 gates only the observed rate (src/
  relweblearner/bench/p2_validate.py:476). The model's 395/395 result is strong, but a measured error-
  rate claim should attach a world-level interval or zero-failure upper bound rather than equating no
  observed failures with zero β.

- Low — none of the new v3 validator functions have automated tests. The full suite passes, but tests/
  does not exercise direct_model, bootstrap_pi, fresh_block_v3, or the stricter bridge-attribution gate.
  The CLI replay currently covers them only manually.

Validation results:

- Full suite: 360 passed, 1 skipped
- Fresh v3 rerun exactly matches both committed artifacts.
- All declared v3 gates reproduce.
- Existing uncommitted pyproject.toml/uv.lock changes were preserved. If intended for commit, pytest
  should normally be a development dependency rather than a runtime dependency
