# Referee report — E6, the rule_27 diagnosis

## 1. Scope

This report reviews the four E6 commits from the pre-registration at
`2382f0f` through the design-problem update at `5b27278`:

- `docs/rule27-diagnosis-plan.md`;
- `src/relweblearner/bench/rule27_diag.py` and its CLI registration;
- `results/rule27-diagnosis/results.json`, `supplementary.json`, and
  `report.md`;
- the resulting changes to `docs/design-problem.md`.

The review covers experimental design, implementation, recorded artifacts,
and whether the stated conclusions follow from the diagnostics. No benchmark
or result file was changed during review.

## 2. Overall assessment

The consistency gate reproduces the frozen seed-0 discrete accuracies, the
graded accuracy reproduces, and the headline result artifacts agree with the
implementation. The evidence supports two useful conclusions:

1. seed 0 is an unusually damaging view draw rather than an accuracy shared by
   every draw of rule_27; and
2. repairing the unresolved `R_9_-` identity produces a large deterministic
   gain, from 0.163 to 0.496.

The work also correctly retracts the pre-plan inference that equal discrete
and graded aggregate accuracies meant no prediction moved: graded healed 22
discrete failures and broke 22 discrete successes.

Several stronger conclusions are not yet established. Most importantly, the
zero no-path cell is guaranteed by the renderer rather than discovered by the
diagnosis, and the pre-registered graded activation-death trace was not
implemented. The attribution table also mixes markers and counterfactual
sensitivity with causal failure shares.

## 3. Findings

### 3.1 Major: the no-path cell is guaranteed to be zero

`make_views()` chooses disjoint hidden relation sets. In ensemble mode,
`_render_test()` emits every edge: an edge visible to A receives A's label,
and an A-blind edge receives B's label because the hidden sets are disjoint.
The ensemble rendering therefore changes relation labels but preserves the
entire graph topology.

`attribute()` compares paths in this rendered graph with paths in the raw
gold graph. Because path existence depends on endpoints rather than relation
labels, the two renderings necessarily have the same source-to-target paths
and the same shortest path lengths. A deterministic review check confirmed
identical topology for all 1,000 seed-0 test episodes.

Thus `h1_gold_path_only = 0` was knowable from the frozen renderer before the
diagnosis ran. It does exclude a missing-path explanation, but it supplies no
new evidence against other harness interactions such as path voting,
tie-breaking, rule reduction over the rendered vocabulary, or intermediate
symbols re-crossing the seam. Those mechanisms remain live in the report's
own account of the unattributed 0.50 to 0.83 gap.

The report and design problem consequently overreach when they infer from the
zero cell that rule_27 is broadly "not a harness artifact" and retire the
whole harness-artifact branch. The supported statement is narrower: the
seed-0 failure is not caused by loss of a witnessing path or by a depth limit
that affects only the ensemble rendering.

### 3.2 Major: the graded activation-decay mechanism was not measured

Plan §4b requires the graded post-mortem to determine whether activation dies
below `ACT_MIN` at the blocking span. `probe_graded()` does not instrument
`graded_reduce()`, save span activations, identify the blocking span, or count
floor-pruned entries. It records token similarities, final predictions, and a
quantity named `failing_fell_back_to_majority`.

That last quantity is not a reliable fallback trace: it tests whether the
returned label equals `maj_a`, but a successful reduction can also return the
majority label. Conversely, it gives no information about which span or
similarity product caused an empty reduction.

The supplementary report observes that the graded system commits the
`R_9_-` identity at similarity 0.62 and still has aggregate accuracy 0.163.
That establishes that commitment alone was insufficient. It does not
establish that multiplicative similarity decay toward `ACT_MIN` was the cause.
The stated `0.62^2` factor applies only to a rule application in which both
inputs bridge through that similarity; it is not automatically the cost of
every use of the hub.

A causal diagnosis would require at least one of:

- the pre-registered per-span activation trace;
- rescoring with committed identity pairs treated as exact similarity 1;
- translating committed identities on rule inputs as well as output symbols;
- or an ablation of `ACT_MIN`/the multiplicative composition while holding the
  discovered identity field fixed.

Until then, “committed but not sufficient” is supported, while “uncashable
because multiplicative enrichment decays to the activation floor” remains a
hypothesis. Promoting it directly into D3/T6 as an enrichment-selector datum is
premature.

### 3.3 The attribution cells are not consistently causal or exclusive

For a CYK-dead episode, `_missing_keys()` gathers a union of missing frontier
keys over every witnessing path and split. The episode is labeled
`cyk-dead-split` if any gathered key contains a B-only token; otherwise it is
called `cyk-dead-missing-rule` if any gathered key maps to a gold rule. This is
a precedence classification, not the “first blocking cause” promised by the
plan, and an episode can contain multiple blockers.

For a wrong reduction, the code calls an episode
`wrong-argmax-orphan-tainted` whenever removing the orphan mapping changes the
predicted wrong label. It does not record whether the orphan symbol or a rule
affected by it participates in the winning derivation, as the plan specifies.

Deterministic counterfactual checks clarify the cells:

- repairing the two mutually visible identities heals all 315
  `cyk-dead-split` episodes plus 18 `wrong-argmax-other` episodes, with no
  previously correct episode broken; the split cell is therefore strongly
  validated for seed 0 despite the classifier's precedence;
- patching all 15 recorded missing rule bodies heals only 1 of the 71
  `cyk-dead-missing-rule` episodes;
- unmerging changes all 89 episodes labeled orphan-tainted, but fixes only 18
  of them; the other 71 change from one wrong answer to another;
- unmerging also breaks 12 previously correct episodes, yielding the reported
  net gain of only 6 correct predictions.

The report may accurately call the latter episodes “sensitive to the orphan
merge,” but it should not present 11% as a causal H4 share. Likewise, the 8%
missing-rule cell records the presence of a missing gold frontier key, not 71
failures that the missing-rule oracle actually repairs.

### 3.4 “100/103 rules present” is not supported by inventory counts

The plan infers that the ensemble lacks three rules because its inventory has
100 entries and the gold inventory has 103. Cardinality difference does not
establish set containment. The result itself demonstrates this: the rule
probe finds 15 translated gold bodies absent from the ensemble, while the
supplementary rule-head audit reports 15 ensemble keys absent from gold.

The design problem nevertheless retains the phrase “100/103 rules present.”
It should say “100 ensemble rules versus 103 gold rules” and separately report
the chosen comparison's missing, extra, and wrong-head counts.

The probe named an oracle rule-inventory patch is also narrower than that name
suggests. It adds gold rules whose translated body key is absent, but it does
not repair an existing body with the wrong head. Wrong mappings can also make
the raw-to-ensemble token translation non-injective, causing distinct gold
rules to collide on one rendered body. The result is a missing-body oracle
under the existing rendered vocabulary, not a complete gold-rule oracle.

### 3.5 Equal aggregate repair scores hide different episode behavior

The supplementary conclusion calls identity repair and rule patch “two faces
of one seam failure” because their accuracies are 0.496 and 0.503 and the
combined probe remains at 0.503. The report has already established that equal
aggregate accuracies can conceal offsetting prediction changes, so this claim
should be supported by episode-level overlap rather than the ceiling alone.

The episode comparison shows:

- identity repair heals 333 failures and breaks none;
- the missing-rule patch heals 350 failures and breaks 10 successes;
- identity repair and rule patch produce different predictions on 197 of
  1,000 episodes;
- their sets of correctly answered episodes have a symmetric difference of
  27;
- the combined probe and rule-patch probe happen to produce identical
  predictions on all 1,000 episodes under the implemented construction.

There is substantial mechanistic overlap: both interventions heal all 315
split-dead episodes. That is good evidence that split vocabulary and rendered
rule availability interact at the seam. It is not evidence that the two
interventions are causally identical everywhere, and the differing healed and
broken sets should accompany the “two faces” interpretation.

### 3.6 The data-authenticity claim is stronger than the gate proves

Reproducing four aggregate accuracies is a useful and important regression
gate. It strongly suggests that the fetched data and frozen code reproduce the
previous experiment. It is not, by itself, proof of file authenticity: many
different artifacts could in principle share four aggregate scores, and the
reported MD5 is not compared with a checksum from an independent trusted
source.

The provenance may reasonably say that the data came from the author's
re-upload and that the benchmark outputs reproduce. “Authenticity is
established by the consistency gate” should be softened unless a trusted
published checksum or byte-for-byte comparison with the original artifact is
available.

## 4. Recommendation

Accept the diagnosis as evidence that seed 0 is an unusually bad vocabulary
seam draw and that one unresolved hub identity accounts for a large part of
the loss. Retain the useful correction that equal aggregate graded accuracy
did not mean prediction immobility.

Do not yet retire the broad harness-interaction possibility or promote the
specific multiplicative-decay explanation into D3/T6. Narrow the H1 conclusion
to path preservation, describe the attribution cells according to what they
actually measure, correct the rule-inventory language, and run the
pre-registered graded activation trace or an equivalent causal intervention.
The remaining 0.50 to 0.83 gap should stay explicitly open.
