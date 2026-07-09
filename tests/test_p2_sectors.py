"""P2 acceptance (e2): symmetry-sector inference.

Accepts iff:
  * same/succ classified correctly from >= 30 random loop observations, 20/20
    seeds;
  * `double` flagged non-homogeneous;
  * with one adversarially mislabeled example injected, the induced rule is
    unchanged in >= 18/20 seeds.
"""

from __future__ import annotations

from relweblearner.datasets.sectors import (
    inject_mislabel,
    loop_observations,
    make_entities,
)
from relweblearner.sectors import (
    ANTISYMMETRIC,
    NON_HOMOGENEOUS,
    SYMMETRIC,
    infer_sectors,
)

BY_COUNT, COORD = make_entities(max_count=8, per_count=3)


def test_same_and_succ_classified_correctly_20_seeds():
    for seed in range(20):
        obs = loop_observations(BY_COUNT, 30, seed)
        assert len(obs) >= 30
        sec = infer_sectors(obs, COORD)
        assert sec["same"].sector == SYMMETRIC and sec["same"].transport == 0
        assert sec["succ"].sector == ANTISYMMETRIC and sec["succ"].transport == 1


def test_double_flagged_non_homogeneous_20_seeds():
    for seed in range(20):
        obs = loop_observations(BY_COUNT, 30, seed)
        sec = infer_sectors(obs, COORD)
        assert sec["double"].sector == NON_HOMOGENEOUS
        assert sec["double"].transport is None
        assert sec["double"].is_motif


def test_one_adversarial_mislabel_leaves_the_rule_unchanged():
    unchanged = 0
    for seed in range(20):
        obs = loop_observations(BY_COUNT, 30, seed)
        poisoned = inject_mislabel(obs, "succ", seed)      # 1 lying succ example
        sec = infer_sectors(poisoned, COORD)
        if sec["succ"].sector == ANTISYMMETRIC and sec["succ"].transport == 1:
            unchanged += 1
    assert unchanged >= 18, f"noise flipped the rule in {20 - unchanged} seeds"


def test_symmetric_signal_is_2g_equals_0():
    # a relation seen both ways between the same pair: transport 0 each way,
    # consistent only with g = 0 (2g = 0 over Z) -> symmetric.
    obs = loop_observations(BY_COUNT, 40, seed=3)
    sec = infer_sectors(obs, COORD)
    assert sec["same"].transport == 0
    assert sec["same"].support == 1.0
