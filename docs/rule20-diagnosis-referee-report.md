# Referee report — E5, the rule_20 diagnosis

## 1. Scope

This report reviews the four E5 commits from the pre-registration at
`47410d3` through the design-problem update at `bef4039`:

- `docs/rule20-diagnosis-plan.md`;
- `src/relweblearner/bench/rule20_diag.py` and its CLI registration;
- `results/rule20-diagnosis/results.json`, `supplementary.json`, and
  `report.md`;
- the resulting changes to `docs/design-problem.md`.

The review covers the pre-registered design, implementation, frozen result
artifacts, post-plan supplementary work, and whether the conclusions folded
into the design problem follow from those measurements. No implementation or
result file was changed during review.

## 2. Overall assessment

The consistency gate reproduces the frozen seed-0 view-alone, discrete
ensemble, gold-pooled, and graded accuracies. The diagnostic copy is
prediction-identical to the frozen graded implementation, and the recorded
flip table and pre-registered probe summaries agree with the code.

The evidence supports several useful conclusions:

1. rule_20's seed-0 tear is not invariant across view draws;
2. the native soft bridge has negative net value on the frozen draw relative
   to removing cross-vocabulary firing;
3. the two wrong hardened identities are real and become highly damaging in
   an exactified translation context; and
4. the tested beam and activation-floor settings do not explain the frozen
   predictions.

The main problem is the stronger causal decomposition. At the frozen
configuration, removing the two wrong commits changes no prediction. Their
reported 0.267 cost appears only after other components are exactified. This
is a large interaction whose allocation depends on the order of the ladder,
not an order-independent decomposition into a dominant commit-policy cost and
a smaller enrichment cost. The exactification ladder that supplies every
headline conclusion is also absent from the committed implementation.

## 3. Findings

### 3.1 Major: the reported decomposition is order-dependent

The relevant measured configurations are:

| configuration | accuracy |
|---|---:|
| frozen graded | 0.317 |
| frozen graded minus the two wrong commits | 0.317 |
| translated rules/rendering plus identity similarity, wrong commits retained | 0.392 |
| same exactified configuration, wrong commits removed | 0.659 |

The marginal effect of removing the wrong commits is therefore context
dependent:

- at the frozen configuration: `0.317 - 0.317 = 0.000`;
- after translation/similarity exactification: `0.659 - 0.392 = 0.267`.

Likewise, the marginal effect of exactifying the other components is:

- while wrong commits remain: `0.392 - 0.317 = 0.075`;
- after wrong commits are removed: `0.659 - 0.317 = 0.342`.

The interaction term in this two-factor summary is 0.267. Walking the ladder
in the published order assigns that interaction to commit removal and yields
the stated 0.075 plus 0.267 decomposition. Walking it in the opposite order
assigns zero first to commit removal and the entire 0.342 to exactification.
Neither ordering is uniquely causal.

This does establish that the false commits are highly damaging *conditional
on translation and exact similarity being restored*. It does not establish
that they independently account for 0.267 of the frozen tear or are its
order-independent dominant cause. A factorial analysis should report main
effects and interactions explicitly, or adopt and justify an allocation such
as a Shapley average. The current design-problem language treats one path
through an interacting system as an exact causal decomposition.

### 3.2 Major: the essential exactification work is not implemented in the repository

The pre-registered probes leave the 0.342 tear largely unexplained. The
headline attribution comes from the post-plan exactification ladder in
`supplementary.json`. No function, script, test, notebook, prediction vector,
or heal/break artifact implementing that ladder is present in the repository.
`rule20_diag.py` ends with the pre-registered probes and the rule_27 companion.

As a result, a reviewer cannot inspect how translated rules and rendering were
constructed, how the alternative merge maps were applied, or independently
verify the asserted 1,000/1,000 prediction identity without reconstructing an
unrecorded diagnostic. This is especially significant because:

- the exactification ladder, not the pre-registered experiment, produces the
  settled mechanism;
- the project has just adopted a plan-to-code checklist in response to prior
  omissions; and
- the design problem closes the empirical queue on the strength of this
  supplementary result.

The post-plan status is disclosed, which is good, but provenance label (b)
does not substitute for a committed reproducer. The essential supplementary
experiment should be held to at least the same audit standard as the original
probes.

### 3.3 The plan-to-code checklist does not preserve the promised episode sets

Plan §4b requires every causal probe to report accuracy and the heal/break
episode sets. The §6b checklist claims that shared `audit()` implements this
requirement. In fact, `audit()` computes the full lists and then serializes
only `heal[:20]` and `brk[:20]`.

The loss is material:

- P-ident reports 73 heals and 32 breaks but stores only 20 indices from each;
- P-max reports 45 heals and 86 breaks but stores only 20 from each;
- P-count reports 140 breaks but stores only 20.

The aggregate counts can be reproduced by rerunning the code, but the frozen
artifact does not contain the promised episode sets and cannot support later
episode-overlap analysis on its own. The implementation and commit message
should not describe the checklist as complete without disclosing this
truncation.

### 3.4 “Every single-factor probe was near-inert” is inaccurate

Only P-commits and the tested beam variants are prediction-inert. Other probes
cause substantial changes:

- P-ident heals 73 and breaks 32, changing 105 predictions and improving
  accuracy by 0.041;
- max aggregation heals 45 and breaks 86, changing 131 predictions;
- count aggregation heals 6 and breaks 140, changing 146 predictions.

These interventions do not recover the discrete tear and two make net
accuracy worse. That supports rejecting them as the dominant repair at the
frozen configuration. It does not make them inert or uninformative.

The valid masking lesson is narrower and still important: the two wrong
commits have a zero marginal effect in the frozen context despite a large
conditional interaction after exactification. The broader methodological
claim that every single-factor counterfactual read approximately zero is not
supported by the recorded heal/break sets.

### 3.5 Exactifying the graded predictor into the discrete predictor is not evidence that the architecture is exonerated

The terminal ladder configuration replaces native graded rules and seam
rendering with translated discrete counterparts, uses exact identity
similarity, and removes the harmful merges. At that point the parameterized
graded reduction has been configured to implement the discrete predictor's
effective semantics, so 1,000/1,000 prediction identity is a valuable
implementation and endpoint validation.

It does not show that the original two-timescale architecture is sound. It
shows that replacing its distinguishing operational choices with the discrete
ones recovers discrete behavior. The result can identify which operational
differences matter on this draw, but “the two-timescale architecture per se is
exonerated” is stronger than the counterfactual warrants.

### 3.6 The rule_27 companion narrows but does not close the graded residual

The companion cell shows that discrete and graded rule_27 predictions agree
on 956 of 1,000 episodes. This is good evidence that rule_27's very low
accuracy is predominantly inherited from the discrete seam failure rather
than caused by a large additional graded degradation.

However, the graded system still heals 22 episodes and tears 22 others. The
companion runs only a flip table and winner markers; it includes no causal
probe explaining those 44 changes. Aggregate equality and 95.6% prediction
agreement do not imply that no distinct graded mechanism exists. The E6
graded residual is substantially narrowed, but calling it closed and saying
there is “no distinct mechanism” overstates the available evidence.

### 3.7 The draw-level conclusion should be scoped to rule_20

Five view draws show that rule_20's seed-0 tear is not a fixed property of the
world: seeds 0 and 2 tear, while seeds 1, 3, and 4 are neutral or healing. This
supports calling the rule_20 failure draw-dependent.

It does not establish that the graded ensemble's entire 44-world bimodality is
a property of draws rather than worlds. Other torn and healed worlds were not
rerun over view draws, and the mechanism of rule_20 seed 2 remains explicitly
unchecked. The design problem should scope the conclusion to rule_20 unless a
crossed world-by-seed experiment supports the general statement.

### 3.8 The marker limitations remain relevant

The supplementary artifact correctly discloses that `commit_pooled` includes
pooling through anchors as well as hardened commits, making it nearly
universal over torn episodes. There are two additional interpretation limits:

- `cross_fired` means that some winning derivation factor is below 1; it does
  not distinguish a correct cross-view correspondence from spurious firing;
- `beam_starved` marks any target-mapped symbol pruned at any visited span,
  not necessarily an intermediate required by the winning correct
  derivation.

The report properly calls these markers rather than causal shares. They should
not be used as further support for the exact decomposition beyond the causal
probes.

## 4. Recommendation

Accept the frozen gate, paired flip table, draw sensitivity, and the finding
that the two wrong commits participate in a large interaction after
translation is restored. Retain the negative-net observation for the native
soft bridge on the seed-0 draw.

Do not yet treat `−0.267 commits + −0.075 soft bridging` as a settled exact
causal decomposition. Commit a reproducer for the exactification cells and
run a genuine factorial analysis that reports interactions and complete
episode-level heal/break sets. Narrow the rule_27 and draw-level claims, and
describe the architecture endpoint as recovery under discrete exactification
rather than exoneration.

The empirical queue should not be considered closed on E5's mechanism until
the supplementary experiment that carries the conclusion is reproducible and
the order-dependent interaction is represented honestly in the design
problem.
