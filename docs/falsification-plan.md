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

## 6½. Bench v2 addendum (2026-07-12, pre-registered before the v2 run)

The composition follow-up left one measurement owed: miner-vs-gate under
poisoned composition evidence, at benchmark level. Bench v2 adds the **P7
poisoned-composition arm**: off-chain stranger entities in five 3-chains of
a new symmetric relation (``x stands near y``); the liars cap three chains
with forged ``step⁺`` facts (``end2 comes right after end0``) — evidence
engineered to be SELF-LICENSING for a PCA-confidence rule miner (the only
``near∘near`` body pairs whose subject carries step⁺ testimony are exactly
the forged heads → confidence 1.0), while admitting it as a geometric
constraint forces ``g(step) = 0 + 0`` and zeroes a live gauge group. The two
clean chains are the probes: asked ``step⁺`` about their ends, the right
answer is refusal; a system that admitted the rule derives garbage. The main
world's draws are bit-identical to v1 (strangers come from a child rng and
append after the stream), so F1–F6 are predicted unchanged.

Pre-registered predictions (P7, lie arm): induced-rules admits the junk rule
5/5 seeds and scores 0.00 refusal accuracy; relweb refuses the rule 5/5
(step stays a live ±1 generator) and scores 1.00; lookup and oracle-rules
score 1.00 (no such rule exists for them). If instead the gate admits the
forged rule on any seed, the "miner proposes, geometry disposes" claim from
the follow-up report is falsified at bench level and must be withdrawn.

## 6¾. GraphLog addendum (2026-07-12, pre-registered before the comparative run)

GraphLog v1.1 (external; Sinha et al., ICML 2020) is in hand: 51 training
worlds, each with its own binary composition rules, 5000/1000 train/test
instances, query edge held out. Adapter: `bench/graphlog.py`
(`relweb-graphlog`), evaluating the GEOMETRY CORE on gold triples (the
language pipeline is bypassed — GraphLog states each edge once, so frames
and k-witness commitment have nothing to do; stated as scope, not hidden).

Two facts established before predictions, disclosed: (a) the data carries
**zero converse 2-cycles** (0/14,943 edges sampled), so any structure the
transport learner finds comes through the 3-cycle composition gate alone;
(b) a per-world diagnostic solving the TRUE rules over ℤ (never shown to the
learner) says 12/51 worlds are fully degenerate (only g ≡ 0 solves them) and
the rest range up to dof 4 with 31–46 of ~171 relation pairs forced to
collide. One dry run was done on rule_0 (degenerate control) while building
the adapter: transport = majority there, as the diagnostic demands.

Calibration disclosed: `_mine_compositions`' support floor was relative to
head-class size (a coverage claim); on triangle-sparse worlds it mines
nothing. It is now absolute (≥ 2 triangles, the k-witness spirit) with a
deterministic top-K compute cap, and the culprit peel is skipped above
`PEEL_EDGE_CAP` (refusal, never corruption). The internal bench v2 was
re-run after the change and reproduces exactly (results/bench-v2b); the P7
gate story is unchanged — junk still has to survive the gate, which is the
semantic vetting.

Predictions for the comparative run (worlds spanning the diagnostic:
rule_43/44 most separable, rule_21/22 dof 4, rule_19 dof 3, rule_18 dof 2
with heavy collisions, rule_0 degenerate control):

- transport beats majority on every non-degenerate world and tracks the
  diagnostic: best on rule_43/44, ≈ majority on rule_0;
- transport ≤ cyk-miner everywhere (the miner's non-abelian rewrite rules
  are strictly more expressive than any ℤ embedding); the gap narrows as
  collisions shrink;
- cyk-oracle (true rules) is the path-reduction ceiling and stays well
  below 1.0 (path ambiguity), consistent with GraphLog's published
  supervised numbers being ~0.5–0.7;
- if transport beats the miner anywhere, that is evidence the global
  solve generalizes past locally-mined rules; not predicted, just scored.

The standing structural admission: GraphLog's rule systems are mostly
NON-ABELIAN, and the frozen ℤ algebra provably cannot represent relation
pairs its diagnostic marks as collided. A poor absolute score here is the
expected, honest outcome; the measured quantity is the correlation between
the diagnostic and the accuracy, plus the mechanism-vs-mechanism gap. The
motivated next step if the correlation holds is the P4′ move the theory doc
already names: richer frozen algebras (the free monoid/groupoid limit of
which IS rule rewriting).

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
