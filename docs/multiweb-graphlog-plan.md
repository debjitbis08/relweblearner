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
