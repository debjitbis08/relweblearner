# Falsification plan — backing the central claim with evidence, or giving it up

*Written 2026-07-11, after an external review, BEFORE the first comparative
run of the benchmark it specifies. The predictions in §5 are frozen with this
document; whatever the run says is what gets reported.*

## 1. Why this exists

The external review's sharpest point was accepted in full: the test suite
proves the system obeys its own specification, not the research hypothesis.
The headline P3 benchmark ([holdout.py](../src/relweblearner/holdout.py))
inserts integer transports and asks for their composite — "exact by
construction", as the code itself says. The README's central claim —
learning as fixed-algebra geometry repair — is not evidenced by a benchmark
whose answers its representation entails.

The question that must be answered honestly:

> **What does fixed-algebra transport + holonomy contribute beyond a
> provenance-aware graph with statistical rule induction?**

This document pre-registers a benchmark that gives the claim a real chance to
fail, states predictions (including expected losses) before the run, and
fixes the criteria under which the claim gets narrowed or given up.

## 2. The benchmark

One seeded generator (`bench/world.py`) renders a hidden 12-entity linear
order through six surface frame families (step ±1 and its converse, skip ±2
and its converse, a functional color attribute, a symmetric many-valued
`likes`). Every system trains on the same page stream. The creature reads raw
`{book, tokens, picture}` pages and must induce frames, unify relations,
orient facts, and fit transports itself. The **baselines read gold parses** —
a deliberate handicap *against* RelWeb, so RelWeb wins are conservative:

- **lookup** — provenance-aware committed-edge recall (k = 2 witnesses, the
  creature's own commit discipline). The floor.
- **induced-rules** — lookup + AMIE-style converse and 2-hop composition
  induction at the same confidence budget the creature uses, applied as
  bounded forward closure. The fair competitor.
- **oracle-rules** — the same engine handed the true rules. The ceiling.
- **relweb** — the creature, answering with `query()` (committed + derived).
- **relweb-noderive** — ablation: the creature's committed answers only.
  Isolates what transport derivation adds over its own memory.

Two arms per seed: a **clean arm** (liars filtered) scores capability
families F1–F6; a **lie arm** (two colluding books commit two lies) scores
detection, poisoning, and exact unlearning. ≥ 5 seeds; per-family accuracy
reported as mean ± sd over seeds.

Query families:

| family | held out | answerable by |
|---|---|---|
| F1 memory | nothing | recall |
| F2 invert-step | step⁻ direction for 3 pairs | discovering step⁺/step⁻ are converses |
| F3 skip-transfer | both skip directions for 3 pairs | discovering skip = step∘step |
| F4 invert-skip | skip⁻ direction for 2 pairs | discovering skip⁺/skip⁻ are converses |
| F5 refuse-color | 3 entities' colors | refusing (correct answer: unknown) |
| F6 plural-likes | nothing | recall without inventing a conflict |

Probes on the lie arm:

- **D1** — a committed second color for one entity: a direct functional
  double-target any conflict rule can see.
- **D2** — a committed `step⁺` lie whose subject's TRUE step fact is never
  taught: no double-target exists; the lie is visible only as a loop that
  fails to close. This is the "contradiction as curvature" claim made
  operational.
- **Poisoning** — who repeats the committed lie when asked.
- **U1** — retract the liar sources; every answer must match a control
  trained without the liar pages (exact unlearning at the behavioral level).

## 3. What the mechanism can and cannot do (known before the run)

Reading `transport.infer()` before designing the benchmark established: gauge
groups form **only from converse 2-cycle evidence**, and transport magnitudes
are gauge-fixed to ±1. The streaming creature therefore *cannot* discover
that skip = step∘step — that would need 3-cycle loop evidence it never
collects. F3 is in the benchmark precisely because the strong reading of
"learning is geometry repair" says it should compose, and the implementation
says it won't. A fair statistical competitor CAN learn it from data.

## 4. Bring-up findings (harness debugging, disclosed)

Building the world exposed four real defects/fragilities in the learner —
found and fixed BEFORE any comparative run, each now pinned by a test:

1. **`/api/ask` mutated without locks** (fixed separately; commit 856656f).
2. **One committed lying pair welded two gauge groups.** `infer()`'s link
   floor `max(1, …)` let a single k-corroborated lie whose converse shape
   collided with another class union their groups, poisoning every transport
   in both (the discovered order is erased). Floor raised to 2 — the
   docstring's own "one coincidental pair must not weld" rule, enforced.
3. **One lie could demote a true class to a motif.** A lying edge that lands
   on the BFS spanning tree smears its residual across many fundamental
   cycles; `non_homogeneous_by_defect` counted those as independent defects
   and blew the exception budget — one adversarial page flipped a
   classification, which the exception rule exists to forbid. The check now
   attributes defects to culprit edges first (greedy peel, charged to the
   culprit's class); a single lie survives as a *visible defect*, a genuinely
   non-homogeneous class still demotes.
4. **Cross-frame commitment piggy-back.** Commitment is per edge while class
   maps are per frame, so one junk page expressing an already-committed pair
   in a *different* frame drags that pair into a second relation class on one
   witness. Not fixed (needs per-(edge, class) commitment); avoided in the
   world and recorded here as known debt.

Also observed, kept as designed stressors for a later variant rather than
fixed: a symmetric relation sharing ≥ 2 entity pairs with an order relation
zeroes the order group's transports (`2g = 0` propagates group-wide); a
committed lie poisons derived answers within BFS range of its shortcut.

## 5. Pre-registered predictions

| measure | lookup | induced | oracle | relweb | relweb-noderive |
|---|---|---|---|---|---|
| F1 memory | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| F2 invert-step | 0.0 | ~1.0 | 1.0 | ~1.0 | 0.0 |
| F3 skip-transfer | 0.0 | ~1.0 | 1.0 | **0.0 (refuses)** | 0.0 |
| F4 invert-skip | 0.0 | ~1.0 | 1.0 | ~1.0 | 0.0 |
| F5 refuse-color | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| F6 plural-likes | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| D1 direct conflict | caught | caught | caught | caught | — |
| D2 loop lie | **missed** | caught | caught | caught | — |
| poisoned by committed lie | yes | yes | yes | yes | — |
| U1 exact unlearning | exact | exact | exact | exact | — |

Read the table honestly: **RelWeb is predicted to lose F3 outright** to a
statistical rule inducer, and its F2/F4/D2 wins over `lookup` are matched by
`induced-rules`. If the run comes out this way, the demonstrated *unique*
contributions of the geometry are not raw capability numbers but:

- structure discovered from raw text (baselines were handed gold parses);
- principled refusal (F5 falls out of gauge freedom, not a tuned threshold);
- D2 detection with *localization* and provenance, feeding repair/trust;
- exact unlearning as an architectural property rather than a recompute.

## 6. Decision criteria (the "give up" clause)

- **C1 — claim dead.** If RelWeb does not reach ≥ 0.9 mean on F2 *and* F4
  while lookup sits at 0, transport discovery is not even doing the basic
  thing, and the geometry-repair claim is unsupported at its friendliest.
  The README claim gets withdrawn, not narrowed.
- **C2 — claim narrowed.** If `induced-rules` matches or beats RelWeb on all
  of F2–F5 and D1–D2 (within seed sd), then on capability the honest claim is
  *"an event-sourced, provenance-aware relational learner whose fixed-algebra
  transport provides exact inference, localized inconsistency detection and
  exact unlearning"* — the guarantees differ, the outcomes don't. The README
  must say that, and drop any implication that holonomy outperforms rule
  induction at learning.
- **C3 — claim bounded (expected).** If RelWeb fails F3 as predicted, the
  README and theory doc must state explicitly: composite-relation discovery
  is outside the current mechanism (gauge groups form from converse evidence
  only); "learning is geometry repair" holds at most for the
  converse/inversion sector until 3-cycle evidence is implemented.
- In every case: the P3 "Hits@1 = 1.0 vs TransE/ComplEx" comparison stops
  being presented as a headline learning result and is re-labeled as what it
  is — a property of exact composition, demonstrated on a representation
  that entails it.

## 7. What this benchmark does not settle

Internal validity only: the world is synthetic, closed, and small, and the
generator was written by the same author as the learner (the bring-up
findings in §4 are exactly why external benchmarks matter). The next two
phases, in order:

1. **External benchmark** — GraphLog (compositional generalization over
   logical rule worlds) adapted through the reading pipeline; needs network
   access for the dataset (laptop-only constraint applies).
2. **Uncontrolled language** — a frozen small Gutenberg slice with
   hand-labeled gold facts: frame precision, fact precision, multiword
   entities, negation, temporal facts. A humiliating score here is more
   useful than another passing phase.
