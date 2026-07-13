# The rule_27 diagnosis (E6) — attribution and probes

Pre-registered: docs/rule27-diagnosis-plan.md (committed before this code). Counterfactual probes are diagnostic instruments using evaluation-side gold — NOT system capabilities.

Consistency gate (plan §6): recomputed accuracies {'view-alone': 0.133, 'ensemble': 0.163, 'gold-pooled': 0.828} vs frozen {'view-alone': 0.133, 'ensemble': 0.163, 'gold-pooled': 0.828} — PASS.

## §4a Failure attribution (seed 0)

1000 test episodes: 163 correct, 0 accidental majority hits, 837 failing.

| cause | episodes |
|---|---|
| wrong-argmax-other | 333 |
| cyk-dead-split | 315 |
| wrong-argmax-orphan-tainted | 89 |
| cyk-dead-missing-rule | 71 |
| cyk-dead-other | 29 |

H1 cell (no ensemble path but gold path exists): 0

## §4b Probes

### Un-merge (H4)

```json
{
 "orphan_pairs": [
  [
   "a6",
   "b1",
   "R_4_+",
   "R_7_+"
  ]
 ],
 "acc_base": 0.163,
 "acc_unmerged": 0.169
}
```

### Oracle repair curve (H3)

```json
[
 {
  "repaired": null,
  "acc": 0.163
 },
 {
  "repaired": "R_9_-",
  "evicted": [],
  "acc": 0.496
 },
 {
  "repaired": "R_1_-",
  "evicted": [],
  "acc": 0.496
 }
]
```

### Rule patch (H2)

```json
{
 "n_missing": 15,
 "acc_base": 0.163,
 "acc_patched": 0.503,
 "acc_gold": 0.828,
 "acc_gold_ablated": 0.351
}
```

### Graded post-mortem (H3/H4 mechanism)

```json
{
 "graded_acc": 0.163,
 "graded_commits_n": 5,
 "failing_healed_by_graded": 22,
 "failing_fell_back_to_majority": 7,
 "implicated_tokens": [
  {
   "b_token": "b1",
   "raw": "R_7_+",
   "true_a": null,
   "committed_to": null
  },
  {
   "b_token": "b2",
   "raw": "R_6_-",
   "true_a": null,
   "committed_to": null
  }
 ]
}
```

## §4c Robustness (secondary, seeds 1+)

| seed | ensemble acc | cells |
|---|---|---|
| 1 | 0.683 | {'wrong-argmax-other': 313, 'cyk-dead-split': 3, 'cyk-dead-missing-rule': 1} |
| 2 | 0.414 | {'wrong-argmax-other': 503, 'wrong-argmax-orphan-tainted': 53, 'cyk-dead-missing-rule': 23, 'cyk-dead-other': 5, 'cyk-dead-split': 2} |
| 3 | 0.735 | {'wrong-argmax-other': 248, 'cyk-dead-split': 13, 'cyk-dead-other': 3, 'cyk-dead-missing-rule': 1} |
| 4 | 0.799 | {'wrong-argmax-other': 197, 'accidental-majority-hit': 1, 'cyk-dead-split': 3, 'cyk-dead-other': 1} |

## Supplementary cells (post-plan, same day — supplementary.json)

Computed with the same frozen machinery after reading the pre-registered
results; labeled per the E2b §8 convention so pre-registered and post-hoc
never blur:

- **Combined probe.** Repairing BOTH mutually-visible identities and
  patching all missing rules lands at **0.503** — the same ceiling as
  either probe alone (0.496 / 0.503). Identity and inventory are two faces
  of one seam failure, not additive causes.
- **Missing-rule structure.** Of the 15 missing gold rules, **6 are
  cross-blind** — they mention both an A-blind and a B-blind relation, so
  NEITHER view can mine them alone; vote pooling cannot synthesize a triple
  no view witnessed in full. (7 involve A-blind relations only, 2 B-blind
  only.)
- **Graded hub post-mortem.** The graded layer FOUND and COMMITTED the hub
  identity R_9_- (S = 0.62, mutual argmax, above HARD_SIM = 0.5) — and
  still scored 0.163. Commits merge output symbols only; rules stay in
  native vocabularies bridged by multiplicative similarity (0.62² ≈ 0.39
  per bridged span), so activation decays toward ACT_MIN on multi-step
  derivations. The discovered identity was never cashable in derivation —
  an enrichment-semantics datum (D3/T6), not an identity-discovery failure.
  Graded also made one WRONG commit (R_1_- → R_0_-, marrying a shared
  relation to an A-blind one).
- **Rule-head quality.** Only 6 of 100 ensemble rules carry a wrong head;
  15 carry keys absent from gold. The residual 0.50 → 0.83 gap is NOT
  attributed by these probes and is left open (candidates: not-in-gold keys
  firing on paths; path-vote statistics over the seam rendering; patched
  heads re-crossing the seam as intermediate symbols).
- **Plan premise correction.** Plan §1 inferred from the frozen 0.163 =
  0.163 that "no test prediction moved" under graded. Measured: graded
  healed 22 discrete failures and broke 22 discrete successes — the
  equality was a count coincidence, not immobility. The H3/H4 priors that
  inference motivated were nonetheless vindicated by the attribution.

## Findings

1. **H1 is refuted.** Zero failing episodes lack an ensemble witnessing
   path (gold-path-only cell: 0), and the same world clears 0.41–0.80 at
   seeds 1–4. rule_27 is NOT a harness artifact — the §9 reclassification
   does not trigger.
2. **The "immunity" is a catastrophic view DRAW, not a world property.**
   Seed 0 hid {R_0_-, R_6_-, R_7_+} from A and {R_4_+, R_4_-, R_8_+} from
   B, left hub R_9_- unresolved, and married A-blind R_4_+ to B-blind
   R_7_+ (the orphan merge). Under that draw: 38% of failures die at the
   seam (cyk-dead-split on imported A-blind tokens), 40% reduce to wrong
   answers, 11% are orphan-tainted, 8% lack a mineable rule.
3. **Repairs converge at 0.50; the seam is recursive.** Oracle identity
   repair, oracle rule patch, and both together all land at ~0.50 of the
   0.83 gold ceiling. Split-brain vocabulary is confirmed as the dominant
   mechanism (H3-family, with H2's cross-blind rules as its rule-level
   face), but it is NOT the whole story; the residual is unattributed.
4. **The graded layer's failure here is enrichment semantics, not
   discovery.** It found the hub, committed it, and could not cash it —
   multiplicative similarity taxes every bridged span, so a 0.62 identity
   is worth 0.39 per use and less with depth. This is direct E5/D3 input:
   the choice of enrichment decides whether discovered identity is usable.

## Data provenance

GraphLog v1.1 was absent from this machine at diagnosis time (data/ is
gitignored; the original host returns 404). Re-fetched from the author's
re-upload (facebookresearch/GraphLog issues #34/#35,
drive.google.com/file/d/1s6oG_5Ul199puKAu67z3QrOAm943hGV2, zip md5
5b6762c8e343659eaf96547787c596d4). Authenticity is established by the
consistency gate: all three frozen accuracies and the frozen graded
accuracy reproduce exactly.
