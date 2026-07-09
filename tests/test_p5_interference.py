"""P5 acceptance (e5): N-web interference + dynamic ensemble.

Generalizes the dev-doc's pairwise e5 to N webs and adds the dynamic ensemble:
  (a) the learner finds the mismatch-minimizing interface map by search alone;
  (b) transfer: the interface reduces holdout error strictly through the map,
      zero shared parameters;
  (c) a poisoned identification is resolved by split, both concepts locally
      consistent afterward;
  (+) N webs (>2) interoperate, and the web count evolves over a stimulus stream.
"""

from __future__ import annotations

from relweblearner.datasets.kinship import (
    arithmetic_web,
    kinship_web,
    poison_identification,
    steps_web,
    true_identifications,
)
from relweblearner.ensemble import SPLIT, Ensemble
from relweblearner.holonomy import defect_mass


def _ensemble3():
    E = Ensemble()
    E.add_web(arithmetic_web(6))     # a0..a5
    E.add_web(kinship_web(12))       # k0..k11
    E.add_web(steps_web(10))         # s0..s9
    return E


# ------------------------------------------------------- (a) map by search
def test_learner_finds_mismatch_minimizing_map_over_n_webs():
    E = _ensemble3()
    candidates = (
        true_identifications("a", "k", 6)
        + true_identifications("k", "s", 10)
        + [poison_identification("a", "k", 2, 2)]   # a2 <-> k4, wrong
    )
    offset, consistent, poison = E.find_interface_map(candidates)
    assert offset == 0
    assert poison == [("a2", "k4")]
    for a, b in consistent:
        E.identify(a, b)
    assert E.interface_defect_mass() == 0            # the found map is consistent


# ------------------------------------------------------------ (b) transfer
def test_transfer_through_the_interface_with_zero_shared_parameters():
    E = _ensemble3()
    for a, b in true_identifications("a", "k", 6):
        E.identify(a, b)
    for a, b in true_identifications("k", "s", 10):
        E.identify(a, b)
    facts = [("a3", k) for k in range(1, 7)]          # 3+k, several land beyond a5
    without = E.answerable(facts, use_interface=False)
    with_iface = E.answerable(facts, use_interface=True)
    assert with_iface > without                       # measurable transfer
    assert with_iface == 1.0                           # the fabric answers all


# --------------------------------------------------------- (c) poison split
def test_poisoned_identification_resolved_by_split():
    E = _ensemble3()
    for a, b in true_identifications("a", "k", 6):
        E.identify(a, b)
    clean = E.interface_defect_mass()
    assert clean == 0

    poison = E.identify("a2", "k4")                    # wrong: a2 is not gen-4
    assert E.interface_defect_mass() > 0               # interface defect appears

    E.resolve(poison, SPLIT)                            # sever the identification
    assert E.interface_defect_mass() == 0              # discharged
    # both webs remain locally consistent
    assert defect_mass(E.webs["a"]) == 0
    assert defect_mass(E.webs["k"]) == 0


# ----------------------------------------------------- dynamic ensemble
def test_web_count_evolves_over_the_stimulus_stream():
    E = _ensemble3()                                   # 3 webs
    events = (
        [("identify", "a", "k")] * 2                   # merge a,k  (3 -> 2)
        + [("identify", "k", "s")] * 2                 # merge in s (2 -> 1)
        + [("contradict", "a")] * 3                    # split      (1 -> 2)
    )
    history = E.stream_dynamics(events, k=2, P=3)
    assert history[0] == 3                              # start: three webs
    assert min(history) == 1                            # merged down to one
    assert history[-1] == 2                             # a contradiction split it
    # the count genuinely changed over time (not static)
    assert len(set(history)) >= 3
