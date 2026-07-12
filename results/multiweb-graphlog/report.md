# Multi-web GraphLog — results

44 held-out worlds (identical to the prior single-web validation), 150
training instances each, full test splits, 112s. Pre-registered design:
docs/multiweb-graphlog-plan.md (committed at 924acfc; §2b amendment and the
destructive-interference gate committed at b53f046, both from dev-world
bring-up only, before this run). Per-world numbers: results.json.

## Scorecard against the frozen predictions

| prediction | measured | verdict |
|---|---|---|
| P-K1 extension precision ≥ 0.85 | 0.92 | PASS |
| P-K1 coverage ≥ 0.60 | 0.72 | PASS |
| P-K2 ensemble ≥ 0.90 × gold-pooled | **0.79** | **FAIL** |
| P-T1 ensemble − transport ≥ +0.30 | +0.38 | PASS |
| P-T2 gap closure ≥ 0.50 | 0.56 (41 worlds) | PASS |

Means over worlds: view-alone 0.389, **ensemble 0.514**, gold-pooled 0.648,
old-structure transport 0.134 (joined from results/graphlog-heldout).

## What passed, and what it means

- **Thinking across webs works on external data.** The ensemble answers at
  0.514 where the frozen-ℤ single web answered at 0.134 — the wall bench
  v3 measured ("the algebra is the limit") is cleared by replacing the
  frozen carrier with rule invariants projected across webs. Gap closure
  0.56: over half of what a label-free view loses by partial perception is
  recovered through a correspondence the system discovered itself.
- **The interference gate is clean.** Across all 44 worlds, extension made
  ZERO real mispairings. Every one of the 17 wrong pairs is an orphan
  merge: an A-only and a B-only relation occupying identical compositional
  roles in the visible structure — an identification the webs genuinely
  agree on, indistinguishable from inside (dev-world exhibit: agreement
  0.99 on ~2,900 evidence weight). Six worlds see small net damage from
  the ensemble (worst −0.058), consistent with orphan merges piling one
  relation's evidence onto another's symbol.
- **Exploratory S0 arm**: with NO co-witnessed anchors at all, pure
  structural bootstrap maps ~4 tokens/world at 0.87 precision — partial,
  but correspondence can begin from structure alone.

## The P-K2 failure, diagnosed

The ensemble recovers 0.79 × gold-pooled, not the predicted 0.90 (the §6
kill line was 0.70; the claim survives, the prediction does not). The loss
is NOT mapping error (precision 0.92, zero real mispairs) and NOT missing
knowledge: on the worst world, rule_27, the projected inventory holds 100
rules vs gold's 103, yet accuracy is 0.163 vs 0.828. Recovery is nearly
flat across coverage bands (0.83 / 0.79 / 0.78 for cov ≥ 0.75 / 0.6–0.75 /
< 0.6), so the binding constraint is not how MUCH was mapped either.

The tax is **split-brain vocabulary**: for relations both views perceive
but the mapping left unresolved (~28% of tokens on average), B's projected
rules name the imported symbol while test paths name A's token. CYK
reduction needs every step of a path to connect, so one split symbol on a
4-edge path kills the whole derivation — a superlinear price for a linear
identity shortfall. The knowledge is present but stored under two names
the system rightly refused to merge without evidence.

This is the finding: **in an ensemble substrate, identity resolution IS
the bottleneck of thinking** — not rule discovery, not composition. The
natural next mechanism is thesis-native: when reduction stalls, propose
the provisional identification that would unblock it and test it against
both webs' evidence (interference-checked abduction) — discovery driven by
the needs of thinking, which is where this architecture was always headed.

## Honest limits

- The ceiling inherited from path reduction (cyk-oracle 0.762 mean) binds
  here too; nothing in the ensemble lifts it.
- Aspect masks are drawn uniformly (15%/15% disjoint); adversarial mask
  placement was not tested.
- One external benchmark family; K = 2 views; anchors are given events
  (budget 6), not negotiated.
