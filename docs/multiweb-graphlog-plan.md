# Multi-web GraphLog — can the ensemble structure represent thinking and knowledge?

*Written 2026-07-12, BEFORE the held-out run. Bring-up happens on rule_0
(dev) only; the predictions in §5 are frozen with this document and scored
on the same 44 held-out worlds as the prior single-web validation
(results/graphlog-heldout, commit 49a866d).*

## 1. What this tests — and what the previous bench did not

The multiweb interference bench (docs/multiweb-plan.md) tested the ADD-ON:
detection of non-corresponding structure. The core thesis is representational:

> Thinking is geometric transformation in opaque webs; knowledge is the
> stable semantic structure projected from within and between them.

The previous bench demonstrated categorical knowledge only (stable regions →
concepts). Nothing was ever *derived*: no transformation was composed, no
held-out structure was inferred. Meanwhile the single-web system's measured
external result is a representational wall: frozen abelian ℤ cannot embed
GraphLog's rule systems (transport mean 0.134 over 44 held-out worlds,
Z-collision diagnostic pre-registered and confirmed — the algebra was the
limit, not discovery).

This experiment asks whether the ENSEMBLE structure clears that wall on the
same external data, under the substrate discipline the thesis demands:

- **no semantic labels on the substrate** — each view reads the world
  through its own opaque relation vocabulary; shared identity is never given;
- **knowledge as projection** — the shared rule system must be recovered as
  structure stable BETWEEN webs, through a discovered partial correspondence;
- **thinking as transformation** — queries are answered by composing
  transformations along paths and reducing them with the projected
  invariants (CYK over the rule web). The "dynamics" here is discrete path
  composition; this tests representational adequacy, not any claim about
  continuous dynamics.

## 2. The construction (per world, per seed)

From the world's 150 training instances plus S = 2 **shared** instances:

- **View A** = shared + half the remainder; **View B** = shared + the other
  half. Each view renames the world's relation labels through its own seeded
  bijection into opaque tokens. Below the evaluation layer, nothing ever
  sees a gold label or the other view's vocabulary.
- **Web per view**: the composition web mined from that view's instances —
  triangle evidence ``(a, b) → c`` over opaque tokens with support counts
  (`mine_rules`, unchanged constants: support ≥ 2, confidence ≥ 0.5).
- **Anchors**: the shared instances are co-witnessed events — the same edge
  slot read by both views yields a token pair. Only relations occurring in
  those 2 instances are anchored; the mapping starts partial.
- **Interference / mapping extension**: unmapped token pairs are scored by
  matched triangles under the current mapping (support-weighted); the best
  pair is accepted only with score ≥ 2 and ≥ 1.5× margin over the runner-up
  in both its row and column; iterate to fixpoint. Purely structural,
  label-free.
- **Projection**: B's triangle votes are translated through the mapping and
  pooled with A's; the same support/confidence floors then yield the
  projected rule set — knowledge as the structure the two webs agree on.
- **Answering (thinking)**: CYK path reduction over the projected rules, in
  A's vocabulary; predictions mapped back to gold labels for scoring only.

## 2b. Pre-run amendment (2026-07-12, after rule_0 bring-up, before any
held-out world was touched)

Bring-up on the dev world exposed two structural flaws in §2's construction:

1. **Whole-instance co-witnessing anchors whole components.** GraphLog
   instances live inside one rule-web component (rule_0's rule web has two
   disconnected components, 9 + 8 relations; the 2 shared instances anchored
   8/8 of one and 0/9 of the other). Triangle interference provably cannot
   cross a component boundary — no mixed triangles exist — so extension had
   literally nothing to do (0 pairs added), while the anchored component
   needed no extension at all.
2. **Instance-splitting yields no gap.** 75 instances nearly saturate rule
   mining (view-alone 0.410 vs gold-pooled 0.424 on rule_0): there is almost
   no knowledge for the ensemble to transfer, so T2 would be vacuous.

Amended construction — more demanding, and truer to "different views of the
same hidden world":

- **Aspect-partial views.** Both views read ALL training episodes; each view
  is blind to its own seeded 15% of relation types (disjoint sets, so the
  union sees everything, and neither view alone does). Edges carrying a
  view's blind relations simply do not exist in its web. Queries whose
  reduction needs an A-blind relation are answerable only through B's web,
  translated through the discovered mapping — including relations A has no
  token for, which enter the projection as imported vocabulary.
- **Edge-level, curiosity-placed anchors.** The co-witnessing budget is 6
  single edges (events registered by both views), not instances. The first
  is the first co-perceivable edge in the stream; each further anchor is
  spent on the largest component of A's OWN mined web that has none yet
  (label-free — the learner notices an unanchored island and asks for one
  shared experience there). Extension must recover the remaining ~2/3 of
  the vocabulary along triangles.
- Test episodes are co-witnessed (both views read them); view-alone sees
  only A's rendering.

Bring-up also added one mechanism and surfaced one phenomenon, both on the
dev world only:

- **Destructive interference.** Positive-only triangle matching confabulates:
  when the leftover unmatched tokens on each side are married off to each
  other, margins pass trivially (no runner-up). Extension therefore also
  counts CONTRADICTED evidence — triples on either side, fully mapped under
  the trial pairing, with no counterpart in the other web — and accepts only
  at agreement ≥ 0.5. On dev this killed 2 of 3 confabulations.
- **Orphan merges.** The third survived at agreement 0.99 on ~2,900 weight
  of evidence: an A-only relation and a B-only relation occupying identical
  compositional roles in the visible structure. The webs genuinely agree on
  the identification; no label-free test can refuse it without refusing true
  pairs. Nominal precision (P-K1, frozen) counts these as errors; the run
  additionally reports the orphan/real split of extension errors, since
  merging structurally indistinguishable orphans is defensible projection
  behaviour while mispairing two present tokens is not.

The §5 predictions are unchanged and remain frozen.

## 3. Systems

| system | sees | what it measures |
|---|---|---|
| view-alone | A's web only | one web, no ensemble |
| **ensemble** | A + B's web through the DISCOVERED mapping | the thesis |
| gold-pooled | all instances, true shared labels | alignment-free reference |
| transport | (prior run, joined) | the old structure's wall |
| cyk-oracle | (prior run, joined) | path-reduction ceiling |

transport, majority and cyk-oracle are joined from
results/graphlog-heldout/results.json (identical worlds, identical test
splits) rather than recomputed.

## 4. Metrics

- **K1 alignment**: precision of extension-added token pairs (anchors are
  correct by construction and excluded); coverage = mapped fraction of B
  tokens appearing in ≥ 2 mined B-triples.
- **K2 knowledge**: ensemble accuracy vs gold-pooled (mean over worlds).
- **T1 thinking vs the wall**: ensemble − transport, mean over worlds.
- **T2 transfer**: gap closure = (ensemble − view-alone) / (gold-pooled −
  view-alone), mean over worlds with gap ≥ 0.02 — measures that knowledge
  genuinely flows between webs through the discovered correspondence.
- **Exploratory, no gate**: an S = 0 arm (no shared instances) probing
  whether correspondence can bootstrap from rule-web structure alone,
  seeded by positional-degree signatures. Reported either way.

## 5. Frozen predictions

- **P-K1**: extension precision ≥ 0.85; coverage ≥ 0.60 (means over worlds).
- **P-K2**: mean ensemble accuracy ≥ 0.90 × mean gold-pooled accuracy.
- **P-T1**: mean ensemble − mean transport ≥ +0.30.
- **P-T2**: mean gap closure ≥ 0.50.
- **Honest limit**: everything stays below cyk-oracle (mean 0.762); that
  ceiling belongs to path-reduction depth and rule completeness, not to the
  ensemble, and is inherited unchanged.

## 6. Falsification criteria

- Extension precision < 0.70: structural correspondence cannot be discovered
  between opaque webs on external data — the "between webs" half of the
  thesis fails where it matters.
- Gap closure < 0.20: the projection carries no usable knowledge; the
  ensemble is decoration over the single web.
- Ensemble < 0.70 × gold-pooled: opacity + discovered correspondence costs
  most of the knowledge; the substrate discipline would be self-defeating.
- Any failure is reported with the same prominence as a pass, per house
  rules.
