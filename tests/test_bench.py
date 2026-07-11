"""Acceptance for the falsification benchmark (docs/falsification-plan.md).

The benchmark is only evidence if the harness itself is trustworthy: the
generator must be deterministic and its holdouts real (nothing held out ever
appears in the stream), the baselines must behave as their definitions say on
the world's own structure, and the creature must clear the C1 floor of the
plan's decision criteria on at least one seed end to end.
"""

from __future__ import annotations

import pytest

from relweblearner.bench import world as W
from relweblearner.bench.baselines import GoldKB, InducedRules, Lookup, bench_oracle


@pytest.fixture(scope="module")
def w() -> W.World:
    return W.generate(0)


def _clean_kb(w: W.World) -> GoldKB:
    return GoldKB([(ep["book"], g) for ep, g in zip(w.episodes, w.gold)
                   if ep["book"] not in w.liar_books])


def test_generator_is_deterministic(w):
    w2 = W.generate(0)
    assert w2.episodes == w.episodes and w2.gold == w.gold
    assert w2.queries == w.queries and w2.chain == w.chain
    assert W.generate(1).episodes != w.episodes


def test_holdouts_are_real_and_junk_never_commits(w):
    """Nothing a query holds out is taught anywhere in the stream, and every
    non-liar gold fact outside the answer key is either honestly witnessed
    (>= 2 books) or single-source junk."""
    taught = {g for ep, g in zip(w.episodes, w.gold) if g is not None}
    for q in w.queries:
        if q["family"].startswith(("F2", "F3", "F4")):
            assert (q["rel"], q["subject"], q["expect"]) not in taught, q
        if q["family"] == "F5-refuse-color":
            assert not any(r == "color" and s == q["subject"]
                           for r, s, _t in taught), q
    kb = _clean_kb(w)
    assert all(len(bs) >= 2 for f, bs in kb.witnesses.items() if f in kb.committed)
    gossip = [f for f, bs in kb.witnesses.items()
              if all(b.startswith("gossip") for b in bs)]
    assert gossip and all(f not in kb.committed for f in gossip)


def test_lies_commit_only_on_the_lie_arm(w):
    lie_kb = GoldKB([(ep["book"], g) for ep, g in zip(w.episodes, w.gold)])
    d1 = ("color", w.d1["subject"], w.d1["wrong"])
    d2 = ("step+", w.d2["subject"], w.d2["wrong"])
    assert d1 in lie_kb.committed and d2 in lie_kb.committed
    clean = _clean_kb(w)
    assert d1 not in clean.committed and d2 not in clean.committed
    # D2 is a LOOP lie: its subject holds no committed double-target
    assert len(clean.pairs("step+") & {(w.d2["subject"], t) for t in w.chain}) == 0


def test_baselines_match_their_definitions(w):
    """Lookup refuses everything held out; the oracle aces every derivable
    family; induced-rules discovers the converses and the composition from
    the committed graph alone."""
    kb = _clean_kb(w)
    lookup, induced, oracle = Lookup(kb), InducedRules(kb), bench_oracle(kb)
    per = {}
    for q in w.queries:
        fam = q["family"]
        for name, b in (("lookup", lookup), ("induced", induced), ("oracle", oracle)):
            got = b.answer(q["rel"], q["subject"])
            exp = q["expect"]
            ok = (got is None if exp is None
                  else got in exp if isinstance(exp, set) else got == exp)
            per.setdefault((name, fam), []).append(ok)
    for fam in ("F2-invert-step", "F3-skip-transfer", "F4-invert-skip"):
        assert not any(per[("lookup", fam)]), fam   # recall alone answers nothing held out
        assert all(per[("oracle", fam)]), fam
    assert all(per[("lookup", "F1-memory")])
    assert all(per[("lookup", "F5-refuse-color")])
    # the fair competitor really induced the structure
    assert "step-" in induced.converses.get("step+", set())
    assert ("skip+", "step+", "step+") in induced.compositions


def test_p7_attack_traps_the_miner_and_not_the_gate(w):
    """The poisoned-composition arm's contract, on one seed end to end: the
    forged step+ pages over stranger 'near' chains are SELF-LICENSING for a
    PCA-confidence miner (the only applicable body pairs are the forged
    heads), so it inducts step+ = near∘near and derives step-garbage on the
    clean chains — while the defect gate refuses the same candidate because
    accepting it would zero the live step generator (g = 0 + 0)."""
    from relweblearner.bench.baselines import InducedRules
    from relweblearner.bench.run import P_FAMILY, _relweb_answer, _score, _train

    lie_kb = GoldKB([(ep["book"], g) for ep, g in zip(w.episodes, w.gold)])
    miner = InducedRules(lie_kb)
    assert tuple(w.forged["rule"]) in miner.compositions      # trapped
    mined = _score(w, lambda q: miner.answer(q["rel"], q["subject"]),
                   families=[P_FAMILY])[P_FAMILY]
    assert not any(mined)                                     # garbage everywhere

    c = _train(list(w.episodes), seed=0)
    step = next(r for r in c._sector_rows()
                if any("comes right after" in t for t in r["templates"]))
    assert step["sector"] == "antisymmetric" and step["transport"] != 0
    ours = _score(w, lambda q: _relweb_answer(c, q["phrase"]),
                  families=[P_FAMILY])[P_FAMILY]
    assert all(ours)                                          # refused, correctly

    # and the clean arm never even mines the rule (no forged evidence)
    clean_kb = _clean_kb(w)
    assert tuple(w.forged["rule"]) not in InducedRules(clean_kb).compositions


def test_creature_clears_the_c1_floor_on_seed_zero(w):
    """End to end on one seed: the creature, reading raw pages, discovers the
    converse structure and answers the F2/F4 inversions (the plan's C1
    criterion), refuses F5, and keeps F1 — while the noderive ablation shows
    the derivations really come from transport."""
    from relweblearner.bench.run import FAMILIES, _relweb_answer, _score, _train

    clean = [ep for ep, _ in zip(w.episodes, w.gold)
             if ep["book"] not in w.liar_books]
    c = _train(clean, seed=0)
    full = _score(w, lambda q: _relweb_answer(c, q["phrase"]))
    ablated = _score(w, lambda q: _relweb_answer(c, q["phrase"], derive=False))
    assert all(full["F1-memory"]) and all(full["F5-refuse-color"])
    assert all(full["F2-invert-step"]) and all(full["F4-invert-skip"])
    assert not any(ablated["F2-invert-step"])       # memory alone cannot invert
    assert set(full) == set(FAMILIES)
