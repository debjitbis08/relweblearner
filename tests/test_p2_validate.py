"""Tests for the v3 P2-discharge validator (referee round 2, finding 5)."""

from relweblearner.bench import p2_validate as P


def _w(fo=0, cc=0, cn=10, wc=0, wn=0, n_true=5, elig=1, succ=1):
    return {"n_true": n_true, "false_obs_total": fo,
            "false_obs_correct_only": fo, "cc": cc, "cn": cn,
            "wc": wc, "wn": wn, "det_eligible": elig, "det_success": succ}


def test_bootstrap_pi_contains_mean_and_pe_is_wider():
    worlds = [_w(fo=i % 3, cc=i % 2, cn=20) for i in range(60)]
    pi = P.bootstrap_pi(worlds, block_size=10, n=2000, seed=1)
    lo, hi = pi["count_pi99_pe"]
    assert lo <= pi["count_mean"] <= hi
    plo, phi = pi["count_pi99_plain"]
    assert lo <= plo and hi >= phi          # estimation uncertainty widens
    assert pi["rate_pi99_pe"][0] <= pi["rate_mean"] <= pi["rate_pi99_pe"][1]


def test_verdict_v3_gates_and_beta_bound():
    pi = {"count_pi99_pe": [2, 16], "count_pi99_plain": [3, 15],
          "rate_pi99_pe": [0.01, 0.03], "rate_pi99_plain": [0.012, 0.028],
          "count_mean": 8.0, "rate_mean": 0.019}
    fresh = {"false_obs_total": 9, "edge_rate_correct": 0.018,
             "detection_eligible": 50, "detection_rate": 1.0}
    v = P.verdict_v3(pi, fresh, model_eligible=395, model_success=395)
    assert v["discharged_measured_tier"]
    assert v["V3ppp_detection"]["beta_upper_rule3_world_level"] == round(3 / 395, 5)
    # each gate can fail independently
    assert not P.verdict_v3(pi, {**fresh, "false_obs_total": 17},
                            395, 395)["V2ppp_count"]["pass"]
    assert not P.verdict_v3(pi, {**fresh, "edge_rate_correct": 0.05},
                            395, 395)["V1ppp_rate"]["pass"]
    assert not P.verdict_v3(pi, {**fresh, "detection_rate": 0.9},
                            395, 395)["V3ppp_detection"]["pass"]
    # a detection failure in the model voids the zero-failure bound
    assert (P.verdict_v3(pi, fresh, 395, 394)
            ["V3ppp_detection"]["beta_upper_rule3_world_level"] is None)


def test_world_stats_smoke_and_bridge_attribution_strictness():
    # one world from the frozen E2b block: pipeline runs, detection uses the
    # strict per-view bridge-attributable condition
    st = P._world_stats(1000, "test_smoke")
    assert st is not None
    assert st["n_true"] > 0 and st["cn"] > 0
    assert st["det_eligible"] == 1 and st["det_success"] == 1


def test_detection_cell_synthetic_counterexamples():
    from collections import Counter
    C = Counter
    # bridges POOLED across views (1+1) must NOT qualify — the pre-round-2
    # implementation would have accepted this
    assert P._detection_cell(C({1: 1, 2: 1}), C({1: 1, 2: 1})) == (0, 0)
    # eligible in view 1, but the contradictions sit in a NON-eligible view:
    # unrelated contradictions must not count as bridge-attributable success
    assert P._detection_cell(C({1: 2, 2: 1}), C({2: 2})) == (1, 0)
    # eligible view whose OWN bridges are contradicted: success
    assert P._detection_cell(C({1: 2}), C({1: 2})) == (1, 1)
    # eligible but only one of its bridges contradicted: below OBS_MIN_CONTRA
    assert P._detection_cell(C({1: 3}), C({1: 1})) == (1, 0)
    # two eligible views, success carried by the second
    assert P._detection_cell(C({1: 2, 2: 2}), C({2: 2})) == (1, 1)


def test_fresh_block_v3_eps_map_descriptive_semantics():
    P.SKIPPED.setdefault("test_block", [])
    out = P.fresh_block_v3(range(1000, 1002), "test_block")
    assert out["n_worlds"] == 2
    if out["eps_map_rate"] == 0.0:
        assert out["eps_map_zero_cell_descriptive"] is not None
    else:
        assert out["eps_map_zero_cell_descriptive"] is None
