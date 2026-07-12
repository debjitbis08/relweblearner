# Falsification report — what the benchmark said

*Run 2026-07-11, 5 seeds, against the design and predictions frozen in
[falsification-plan.md](falsification-plan.md) (commit 0208514, before this
run). Raw numbers: `results/bench/`. Reproduce with `relweb-bench --seeds 5`.*

## Headline

The central claim survives its floor test, loses exactly where code-reading
predicted, and is matched on capability by a statistical rule inducer — so
per the pre-registered criteria it is **kept, narrowed, and bounded**:

> An event-sourced, provenance-aware relational learner that discovers
> converse structure from raw text and uses fixed-algebra transport for exact
> inference, noise-robust inconsistency detection, and exact unlearning —
> within the converse/inversion sector it can currently discover.

"All learning reduces to geometry repair" is **not** supported by this run
and is no longer claimed.

## Results against predictions

| measure | lookup | induced | oracle | relweb | noderive | predicted (relweb) |
|---|---|---|---|---|---|---|
| F1 memory | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| F2 invert-step | 0.00 | 1.00 | 1.00 | **1.00** | 0.00 | ~1.0 ✓ |
| F3 skip-transfer | 0.00 | **1.00** | 1.00 | **0.00** | 0.00 | 0.0 (loss) ✓ |
| F4 invert-skip | 0.00 | 1.00 | 1.00 | **0.80 ± 0.45** | 0.00 | ~1.0 ✗ |
| F5 refuse-color | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| F6 plural-likes | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| D1 direct conflict | 1.00 | 1.00 | 1.00 | 1.00 | — | caught ✓ |
| D2 loop lie | **0.00** | 1.00 | **0.80** | **1.00** | — | caught ✓ |
| poisoned by lie | 1.00 | 1.00 | 1.00 | 1.00 | — | yes ✓ |
| U1 exact unlearning | exact | exact | exact | **1.00** | — | exact ✓ |
| clean-arm false alarms | 0 | 0 | 0 | 0 | — | 0 ✓ |

## Verdicts (pre-registered criteria)

- **C1 (claim dead?) — passed.** RelWeb reads raw pages, induces the frames,
  unifies the paraphrases, discovers that "comes right after" / "is just
  before" and "sits two past" / "lies two shy of" are converse pairs, and
  answers held-out inversions the lookup floor scores 0 on. The
  `relweb-noderive` ablation confirms the answers come from transport, not
  memory.
- **C2 (narrowed) — triggered.** `induced-rules` — an AMIE-style miner at the
  same confidence budget, admittedly fed gold parses — matches or beats
  RelWeb on every capability family. On this world, holonomy does not
  outperform statistical rule induction at *learning*; the honest claim is
  the guarantees (exactness, audit, refusal, unlearning), not capability
  advantage. README updated accordingly.
- **C3 (bounded) — confirmed.** F3 = 0.00 exactly as predicted: gauge groups
  form from converse 2-cycles only, so skip = step∘step is undiscoverable by
  the current mechanism, while the statistical competitor learns it from the
  same stream. "Learning is geometry repair" holds at most for the
  converse/inversion sector until composite (3-cycle) loop evidence is
  implemented. RelWeb *refuses* these queries rather than guessing — the
  failure mode is the designed one.
- The P3 holdout (`holdout.py`) is re-labeled: it demonstrates exact
  composition, a property of the representation, not a learning result.

## Findings the predictions missed

1. **RelWeb F4 dropped a seed (0.80 ± 0.45).** On seed 1 the `lies two shy
   of` frame never induced — the rarest frame (~30 pages) fell under the
   induction threshold, so skip⁺ had no converse evidence and stayed
   unconstrained (it refused; it did not guess). Discovery is data-hungry at
   the tail, and a capability built on discovery inherits that variance.
   Reported as measured; the world was not retuned to hide it.
2. **Statistical conflict detection is noise-fragile; holonomy is not.** The
   oracle rule engine missed D2 on seed 3: sub-commitment gossip junk made
   `step⁺` look non-functional on raw testimony, silently disabling its
   derived-conflict rule. The holonomy detector fired 5/5 — it reads only
   committed geometry and needs no functionality statistics. This is a real
   differentiator in RelWeb's favor that the predictions did not anticipate,
   surfaced only because the baseline was built to compete honestly.
3. **Localization is weaker than detection: 0.40.** Holonomy names a
   defective *cycle*; the reported non-tree edge touched the lying edge's
   endpoints in only 2/5 seeds. Blame assignment needs provenance and trust
   on top of the geometric signal — consistent with the architecture's own
   story, now with a number attached.
4. **Everyone repeats a committed lie (poisoning 1.00 across systems).**
   k-witness commitment is collusion-*bounded*, not collusion-proof; the
   recovery story is detection (D2) → arbitration → retraction (U1 = 1.00),
   not immunity.

## Follow-up run (2026-07-12): 3-cycle evidence flips the F3 loss

The C3 bound named its own fix — composite relations need 3-cycle loop
evidence — so it was implemented and the SAME frozen benchmark re-run
(`results/bench-composition/`; the bench, world, queries and baselines are
untouched — only the learner changed).

The mechanism (`transport.infer()`): committed triangles
``(s,m) ∈ a, (m,t) ∈ b, (s,t) ∈ head`` witness ``g(head) = g(a) + g(b)``.
Candidates are mined by support but admitted only through a **defect gate**,
one at a time strongest-first: the whole constraint system (converse links +
accepted compositions) is fork-solved as a homogeneous integer system and
re-projected; a candidate is refused if it degrades any live antisymmetric
class (a junk composition that would zero a group) or brings over-budget new
*culprits* — defects are attributed to culprit edges before judging, so an
already-visible lie that merely smears across more cycles in the denser
merged web cannot veto a true composition. The miner proposes; the gauge
geometry disposes. The gauge convention generalizes unchanged: minimal
integers per constraint component, so step is ±1 and a composed skip is ±2
*in the same group*.

| measure | before | after | note |
|---|---|---|---|
| F3 skip-transfer (relweb) | 0.00 | **1.00** (5/5 seeds) | discovered, not given |
| F2 / F5 / F6 | 1.00 | 1.00 | unchanged |
| F4 invert-skip | 0.80 ± 0.45 | 0.80 ± 0.45 | seed-1 frame never induces; unrelated |
| D2 loop-lie detection | 1.00 | 1.00 | survives the denser merged web |
| U1 exact unlearning | 1.00 | 1.00 | retraction unaffected |
| clean-arm false alarms | 0 | 0 | the gate admitted no junk |
| D2 localization | 0.40 | 0.20 | merged web smears attribution further |

Two details worth the ink:

- **Seed 1 is the sharpest evidence for the gate's value.** Its `skip⁻`
  frame never induced, so skip⁺ had *zero converse evidence* — under 2-cycle
  inference it stayed unconstrained forever. Composition evidence alone
  constrained it to g = 2 in the step group, and F3 went 3/3 there. A
  capability was recovered for a class whose paraphrase data was too thin
  for the old mechanism.
- **The gate beats the miner exactly where predicted.** In the unit
  stressor (`test_junk_composition_refused_by_the_defect_gate`), junk
  triangles at PCA-confidence 1.0 — which the AMIE-style miner accepts and
  turns into garbage derivations — are refused by the gate because
  committing them would zero a live gauge group. Conversely a sub-budget
  committed lie does not veto a true composition
  (`test_sub_budget_lie_does_not_veto_a_true_composition`); it stays on
  display as a defect. This is the "miner proposes, geometry disposes"
  division of labor, now demonstrated rather than argued. Honest scope
  note: on the benchmark's clean arm the miner and the gate agree
  everywhere (both score 1.00 with zero false alarms); the difference shows
  under adversarial/coincidental evidence, and a full poisoned-composition
  *benchmark arm* (not just unit stressors) is the right next measurement.

C3's bound therefore moves: composite discovery now reaches 3-cycle
(binary-composition) evidence. Still outside the mechanism: longer
composition words, per-edge-varying transports (``double``), and anything
needing coordinates the P1b chain hasn't built. C2's verdict is refined but
not reversed — the fair miner still matches RelWeb's clean-arm capability;
the demonstrated differentiators are noise-robust detection (D2) and now
junk-robust *admission* (the gate), both properties of reading only
committed geometry.

## Bench v2 run (2026-07-12): the poisoned-composition arm lands on its predictions

The P7 attack (plan §6½, frozen before the run; `results/bench-v2/`):
self-licensing forged composition evidence — three stranger `near`-chains
capped with forged `step⁺` facts, engineered so the only applicable body
pairs for a PCA-confidence miner are the forged heads.

| system | junk rule admitted | refusal accuracy (clean chains) |
|---|---|---|
| lookup | 0.00 | 1.00 |
| **induced-rules** | **1.00** | **0.00** |
| oracle-rules | 0.00 | 1.00 |
| **relweb** | **0.00** | **1.00** |

Exactly the pre-registered outcome, 5/5 seeds: the statistical miner
inducts `step⁺ = near∘near` at confidence 1.0 and derives step-garbage on
every clean chain; the defect gate refuses the same candidate because
admitting it would zero a live gauge group. "Miner proposes, geometry
disposes" now holds at benchmark level under an adversarial forgery, not
just in unit stressors. All v1 families and probes reproduce unchanged; F4
rose 0.80 → 1.00 for a mundane reason stated plainly — the v2 stream is
longer, so seed 1's rare skip⁻ frame now clears the induction threshold
(the data-hunger variance is real; v2 just sits past it).

## Bench v3 run (2026-07-12, referee round 2): 50 seeds, the coherent forgery, tightened metrics

Plan §6⅞(b,c), predictions frozen first; `results/bench-v3/`. All capability
families reproduce at 50 seeds (RelWeb 1.00 on F1–F4/F6; the old F4
data-hunger variance is gone at this stream length). What the larger sample
and tightened metrics surfaced:

- **P8 coherent forgery: exactly as predicted, 50/50 seeds.** RelWeb admits
  the liars' consistent phantom structure through the gate (1.00), carries
  ZERO extra defects (coherence is invisible from inside — §16, now a
  number), and **derives the held-out fabricated fact** (1.00); the
  statistical miner does the same; lookup and oracle-rules refuse only
  because they hold no rules for it. Recovery is provenance, not geometry:
  after liar retraction the probe refuses again on 50/50 seeds and the full
  committed-belief set matches the liar-free control (1.00). P7's claim is
  therefore held to its narrow form: the gate rejects **algebraically
  incompatible** forgeries; a coherent one passes, measured.
- **D2 at n=50: relweb 1.00, miner 0.84, oracle-rules 0.66.** The
  noise-fragility of statistical conflict detection is bigger than the
  5-seed estimate suggested; holonomy detection (now scored causally:
  lie-arm defects vs the same seed's clean projection, plus post-retraction
  clearance) stays at 1.00. Localization re-estimates at 0.68 — the 5-seed
  figures (0.40, then 0.20) were small-sample noise in both directions.
- **The miner false-alarms on clean worlds: 24 flags across 50 clean arms
  (RelWeb: 0).** Its derived-conflict rule misfires without any adversary
  present — invisible at 5 seeds.
- **Admissions are now audited directly**: every gate-accepted composition
  on every clean arm checks out against the world's true offsets — and the
  audit itself needed fixing en route: the gate legitimately accepts
  ENTAILED compositions (step⁺ = skip⁺ ∘ step⁻, i.e. +1 = +2 − 1), which a
  shape whitelist would have miscounted as junk. "No false admissions" is a
  measurement now, not an inference from absent alarms.
- **One new honest imperfection: RelWeb F5 refusal = 0.99 ± 0.05.** On seed
  11 the MOTIF layer (inheritance, not transport) induced a coincidental
  rule and derived a never-taught color — a hallucination the transport
  discipline would refuse, at 1/150 probes. The motif layer's statistical
  induction is a measured precision limit, recorded here rather than
  patched under the freeze.
- F6 rescored as set retrieval: precision/recall ≈ 1.00 for all systems
  (the miner drops a point of precision); U1 extended to full belief-set
  comparison: 1.00 over 50 seeds.

## GraphLog run (2026-07-12): the external benchmark, and the algebra's measured limit

GraphLog v1.1 (Sinha et al., ICML 2020), 7 worlds spanning the ℤ-embedding
diagnostic, 150 training instances each, full 1000-query test splits
(`results/graphlog/`, `relweb-graphlog`; predictions frozen in plan §6¾).
The adapter evaluates the geometry core on gold triples — the language
pipeline is out of scope here by design.

| world | majority | transport | **transport-oracle** | cyk-miner | cyk-oracle | Z-collisions |
|---|---|---|---|---|---|---|
| rule_43 | 0.004 | 0.004 | 0.050 | 0.451 | 0.585 | 31 |
| rule_44 | 0.000 | 0.123 | 0.248 | 0.639 | 0.785 | 31 |
| rule_21 | 0.048 | **0.515** | 0.576 | 0.763 | 0.878 | 45 |
| rule_22 | 0.029 | 0.029 | 0.455 | 0.807 | 0.873 | 45 |
| rule_19 | 0.050 | 0.060 | 0.415 | 0.685 | 0.807 | 45 |
| rule_18 | 0.010 | 0.010 | 0.263 | 0.414 | 0.515 | 46 |
| rule_0 | 0.002 | 0.034 | 0.022 | 0.423 | 0.484 | 136 |

**The headline number is `transport-oracle`: the additive-oracle
reference.** It is the TRUE rules, exactly solved over ℤ (generic nullspace
point, per-component gauges), evaluated through the same path-voting
decoder — i.e. oracle performance of the current one-dimensional additive
transport model and decoder, not a bound on every conceivable abelian
scheme. It spans 0.02–0.58 and sits far below the path-reduction reference
(cyk-oracle, 0.48–0.88) on every world. GraphLog's rule systems are
essentially non-abelian: **for this representation the binding constraint
is the algebra**, and (see below) discovery is a second, independent
limitation. This is the pre-registered structural limit, now carrying a
hard number per world.

Predictions scored:

- *"transport ≤ cyk-miner everywhere"* — **confirmed 7/7** (the miner's
  rewrite rules are strictly more expressive; it wins 0.41–0.81).
- *"cyk-oracle well below 1.0"* — **confirmed** (path ambiguity is real).
- *"transport beats majority on every non-degenerate world"* — **missed**:
  on rule_43, rule_22, rule_18 the learned transports predict at majority.
- *"best on rule_43/44 (fewest collisions)"* — **missed, instructively**:
  rule_43 has the LOWEST ceiling (0.05) despite the fewest forced
  collisions. The global collision count is a weak instrument; what matters
  is how the query distribution lands on the solution space's separable
  directions. The direct ceiling measurement replaces the diagnostic as the
  right tool.
- Discovery recovers the additive-oracle uplift **inconsistently**, and the
  honest per-world accounting is: rule_21 recovers 88% of the uplift over
  majority, rule_44 recovers ~50%, and rule_43/22/19/18 sit at or near the
  floor (0–3%). "Transports learned: 17–19/19" counts placements, not
  correctness — a count that does not establish the right constraint
  structure was learned. So on most evaluated worlds *discovery itself*,
  not only representation, remains a major limitation; the held-out run
  below adds a direct learned-vs-oracle constraint-recovery measurement to
  replace the placement count. What discovery does do here it does from
  3-cycle evidence alone, since GraphLog contains **zero converse pairs**.

**What the external data fixed in the learner.** Two genuine defects
surfaced only at GraphLog density, both now in `transport.py` with the
internal bench re-verified byte-identical after each change:

1. `_solve`'s seed-and-propagate was INCOMPLETE: a variable forced by
   simultaneous equations (``g1+g2=g3, g1+g3=g2`` forces ``g1=0``) cannot be
   found by 2-of-3 propagation, so the solver seeded it, read its own guess
   back as a conflict, and zeroed whole components — silently, on any
   sufficiently dense constraint system. Replaced with exact Gaussian
   elimination and a GENERIC nullspace point (classes collide only when
   forced). Tree-like constraint systems — everything the internal bench
   generates — never trip this, which is precisely why external data was
   needed to find it.
2. The admission gate went through the same fixpoint-and-bootstrap hardening
   (interlocking rule systems admit in passes; unconstrained classes may
   bootstrap), and prediction was made component-aware — composing
   transports across mutually-ungauged groups is the false-inverse
   manufacture P4′ forbids, and the first adapter did it.

**Verdict.** On its own algebra's terms the geometry core does what it
claims — discovers structure through the gate (up to 19/19 transports, no
converse evidence needed) and predicts near its representational ceiling on
the worlds where that ceiling is nontrivial. But the ceiling itself is low:
GraphLog composition is non-abelian, and the honest statement for the
README is that the frozen ℤ algebra does not extend to it. The motivated
next step is the one the theory doc already names as P4′: richer frozen
carriers (ℤⁿ, permutation/matrix monoids — the free-monoid limit of which
IS the rule rewriting that scores 0.8 here), swapped behind the same
interface and gated by the same defect discipline.

## Held-out GraphLog validation (2026-07-12): 44 untouched worlds, frozen implementation

The seven development worlds found bugs and drove fixes, so they stopped
being validation data (plan §6⅞a). The implementation was frozen at
f4b1a82 and every remaining train-split world ran untouched
(`results/graphlog-heldout/`, 44 worlds, full test splits, 3313s). No code
changed after observing these numbers.

Medians across the 44 worlds: majority 0.007, **transport 0.068**,
additive-oracle reference 0.224, cyk-miner 0.717, cyk-oracle 0.827. The
held-out set includes a harsher degeneracy tier than development suggested
(eleven worlds carry 136–171 forced collisions; their additive reference is
at or near floor).

Pre-registered predictions, scored:

- *"transport ≤ cyk-miner on every world"* — **confirmed 44/44**.
- *"median uplift recovery < 50%, a minority above 80%"* — **confirmed**:
  over the 33 worlds with meaningful additive-oracle uplift, median
  recovery is 0.28, six worlds exceed 80% (best: rule_23 at 0.57 accuracy
  against a 0.76 reference; rule_34 slightly above its reference), eleven
  sit under 10%. Discovery is real and remains inconsistent, exactly as the
  development data indicated.
- *"recovery correlates with the constraint-recovery metrics"* —
  **missed**, and the miss is informative. `accepted_oracle_consistency`
  does land below 1.0 on 32/44 worlds (the gate admits coherent-but-false
  constraints in the wild, as P8 predicted it must), but neither metric
  predicts uplift recovery (Spearman ρ = 0.15 and 0.05), and
  `true_rule_satisfaction` is low everywhere (median 0.15, max 0.40) — the
  learned assignment satisfies only a small fraction of the generative
  rules even on the best-predicting worlds. Prediction quality is evidently
  driven by whether the mined subset captures the structure the TEST
  QUERIES traverse, not by global rule recovery. Both metrics stay in the
  harness; the theory of what makes a world recoverable is open.

Standing conclusion, now on untouched data: within its algebra the
transport core clears the floor it claims (44/44 above-or-at majority is
not claimed — eleven worlds sit at it; six worlds recover most of their
additive reference), the non-abelian gap is unchanged (miner 0.72 median vs
transport 0.07), and the case for a noncommutative carrier — referee step
6, next — is now made on frozen, held-out external data rather than on
development worlds.

## Carrier-ladder feasibility (2026-07-12): no 3-point carrier earns discovery code

The referee's nested sweep — Z, S3, I3, B3, CYK — run as oracle
feasibility over all 51 train-split worlds (plan §7¼, predictions and
decision rule frozen first; `results/carriers/`, 1520s). Medians:

| | Z | S3 | I3 | B3 | cyk-oracle |
|---|---|---|---|---|---|
| median oracle accuracy | 0.248 | 0.124 | 0.110 | 0.251 | 0.807 |
| median uplift over Z | — | −0.096 | −0.025 | **+0.000** | +0.456 |

**The decision rule fires negative: no rung clears the bar** (≥ 2× Z's own
+0.225 median uplift over majority), so per the frozen rule no 3-point
carrier gets discovery code, and the rewriting route wins the next phase.

Predictions scored:

- *"S3 alone does not solve GraphLog"* — **confirmed**: totality and
  invertibility mis-model these relations; S3 sits below Z on median.
- *"B3 unlocks high-collision worlds"* — **partially confirmed, and the
  partial matters**: 11 of the 17 worlds where Z ≤ 0.1 improve under B3,
  a few dramatically (rule_4: 0.024 → **0.624**, nearly reaching its
  cyk-oracle of 0.679; rule_41: 0.222 → 0.702; rule_5: 0.126 → 0.489) —
  but the median across those worlds is only 0.109. B3 is transformative
  on a minority of worlds and median-neutral overall (beats Z on 19/51,
  loses on 18/51).
- *"ladder nondecreasing on a majority of worlds"* — **missed** (21/51).
  Nesting guarantees solutions EXIST monotonically up the ladder; a
  min-conflicts search does not FIND them monotonically. This is a solver
  artifact and a real caveat on every number here: B3 reached exactness on
  only 8/51 worlds (most sit at 17–19 of 20 rules), so the B3 column is a
  lower bound that a SAT/SMT solve could lift.
- *"B3 remains well below cyk-oracle"* — **confirmed emphatically**:
  median gap 0.456.

**The ladder answered the referee's question.** The missing ingredient on
GraphLog is not noncommutativity (S3 flat), not partiality (I3 flat), and
not even arbitrary many-to-many relational transport (B3 median-neutral):
it is **contextual rule rewriting** — the CYK reference towers over every
fixed finite carrier tried. Two escape hatches remain open and are recorded
rather than pursued now: exact B3 solving (SAT) could raise the B3 lower
bound, and larger latent sets (B4, B5) were not swept; but the frozen
decision rule points the discovery phase at the free-monoid/rewriting
sector — discovered binary rules applied as typed rewriting, with the
defect gate admitting rules the way it admits compositions today — rather
than at a richer fixed carrier. The one bright spot worth keeping: on the
minority of worlds where B3 shines, it nearly closes the gap to CYK, so a
per-gauge-group carrier CHOICE (Z where abelian fits, B3 where it pays,
rewriting above both) remains consistent with everything measured.

## What this does not settle

Internal validity only: a synthetic, closed, 12-entity world authored by the
learner's own author. The bring-up phase alone found and fixed two
adversarial-robustness bugs in the learner (gauge-group welding by one lying
pair; motif demotion off one tree-placed lie — see plan §4), which is
evidence the harness bites, but external validity still requires:

1. **GraphLog** (external compositional benchmark) through the reading
   pipeline — blocked on network access under the laptop-only constraint;
2. **the uncontrolled-language eval** (frozen Gutenberg slice, hand-labeled
   gold): frame precision, fact precision, negation, temporal facts.
