"""Frontier-priority, cluster-fair retention — the Referee's re-scoping of replay
(``experiments/experiment0q_reservoir.py``) run inside real :class:`Creature`s.

The boundary the audit forced: distillation is a projection, and replay can only
regenerate its image — a relation the geometry never kept is unrecoverable *in
principle*, so the retroactivity budget is not replay but the RESERVOIR. Two facts
follow. (a) The buffer is already frontier-priority *structurally*: parsed episodes
are distilled into geometry on arrival and never enter the buffer, so memory holds
only the un-assimilated — the sole irreplaceable text. (b) Within the frontier,
retention must be cluster-fair: a firehose of un-learnable noise must not evict a
rare-but-learnable pattern below its induction threshold. At identical memory, the
retention POLICY decides whether a late frame can ever form.
"""

from __future__ import annotations

import random

from relweblearner.creature import Creature


def _stream(n=10000, seed=11):
    """A common frame (55%, distils early), a RARE learnable pattern (3%, stays
    frontier long after streaming by), and an un-learnable NOISE firehose (42%,
    random length-6 tokens — no anchor ever recurs, so it never induces)."""
    rng = random.Random(seed)
    animals = [f"a{i}" for i in range(15)]
    colors, times = ["red", "blue", "green"], ["dawn", "noon", "dusk"]
    color_of = {a: rng.choice(colors) for a in animals}
    sleep_at = {a: rng.choice(times) for a in animals}
    books = ["b0", "b1", "b2"]
    eps = []
    for i in range(n):
        a = rng.choice(animals)
        src = books[i % 3]
        r = rng.random()
        if r < 0.03:                                   # rare, learnable: length 5
            eps.append({"tokens": ["the", a, "sleeps", "at", sleep_at[a]], "picture": a, "source": src})
        elif r < 0.45:                                 # noise firehose: length 6, unanchored
            eps.append({"tokens": [f"n{rng.randrange(2000)}" for _ in range(6)], "picture": None, "source": src})
        else:                                          # common frame: length 4
            eps.append({"tokens": ["the", a, "is", color_of[a]], "picture": a, "source": src})
    return eps, sleep_at


def _make(stratify: bool) -> Creature:
    return Creature("res", commit_k=2, min_group=20, induction_interval=200,
                    buffer_cap=120, seed=5, reservoir_stratify=stratify)


def _has_rare_frame(c: Creature) -> bool:
    return any("sleeps" in f.anchors and "at" in f.anchors for f in c.frames.values())


def _rare_facts_recovered(c: Creature, sleep_at: dict) -> int:
    committed = {(s, t) for s, t, _ in c.edges.committed(c.commit_k)}
    return sum(1 for a, t in sleep_at.items() if (a, t) in committed)


def test_cluster_fair_retention_recovers_a_rare_pattern_a_firehose_would_bury():
    eps, sleep_at = _stream()

    strat = _make(stratify=True).ingest(eps)
    flat = _make(stratify=False).ingest(eps)

    # both learn the dominant common frame either way (15 colour facts commit)
    assert strat.edges.num_committed(2) >= 15 and flat.edges.num_committed(2) >= 15
    # identical memory bound — the ONLY difference is retention policy
    assert strat.buffer_cap == flat.buffer_cap == 120
    assert len(strat._buffer) <= 120 and len(flat._buffer) <= 120

    # the firehose buries the rare pattern under a flat reservoir: never induces
    assert not _has_rare_frame(flat)
    assert _rare_facts_recovered(flat, sleep_at) == 0

    # cluster-fair retention protects it: the late frame forms and its facts commit
    assert _has_rare_frame(strat)
    assert _rare_facts_recovered(strat, sleep_at) >= 10


def test_stratified_buffer_holds_a_fair_share_of_the_rare_cluster():
    # isolate the retention policy: induction OFF, so nothing is assimilated out of
    # the buffer and its steady-state composition is directly observable. The rare
    # length-5 cluster is 3% of the stream; a flat reservoir mirrors that (~3-4 of
    # 120), a cluster-fair one lifts it toward its fair share.
    eps, _ = _stream()
    off = dict(commit_k=2, min_group=10**9, induction_interval=10**9, buffer_cap=120, seed=5)
    strat = Creature("s", reservoir_stratify=True, **off).ingest(eps)
    flat = Creature("f", reservoir_stratify=False, **off).ingest(eps)
    rare_strat = sum(1 for e in strat._buffer if len(e["tokens"]) == 5)
    rare_flat = sum(1 for e in flat._buffer if len(e["tokens"]) == 5)
    assert rare_strat >= 20                        # enough exemplars to cross induction
    assert rare_flat < 20                          # the flat reservoir starves it
    assert rare_strat > 2 * rare_flat


def test_single_cluster_reduces_to_uniform_reservoir():
    # with one length-cluster, cluster-fair retention IS Algorithm R: it must still
    # retain episodes a FIFO window of the same cap would have evicted.
    c = Creature("one", buffer_cap=50, induction_interval=10**9, min_group=10**9, seed=7)
    n = 2000
    for i in range(n):
        c.observe(["qqq", f"u{i}"], source="stream")
    assert len(c._buffer) == 50
    idx = [int(e["tokens"][1][1:]) for e in c._buffer]
    assert min(idx) < 1950                         # not a mere recency window
    assert sum(1 for i in idx if i < n // 2) >= 5  # sample spans the whole stream
