# The P2 discharge, amendment v2 — validation results

Pre-registered: docs/p2-discharge.md §9 (committed before this code or any computation touched seed block 3000–3049). Gating block: 3000–3049 (virgin). The 2000 block is V2-retrodiction, disclosed.

| check | fresh 3000 (gating) | 2000 (retro) |
|---|---|---|
| edge rate, correct endpoints | 0.0204 (71/3486) | 0.0188 (64/3405) |
| α₂ predicted (shared / indep) vs observed correct-only | 5.64 / 5.66 vs 11 | 5.07 / 5.1 vs 9 |
| detection: obstructed / per-bridge | 1.00 / 1.0000 | 1.00 / 1.0000 |

Verdict (fresh block): ```{
 "V2prime_mixture": {
  "pass": true,
  "band": [
   2.26,
   14.1
  ],
  "predicted_shared_p": 5.64,
  "predicted_indep_p": 5.66,
  "observed_correct_only": 11,
  "observed_total": 11
 },
 "V1_replication": {
  "pass": true,
  "band": [
   0.0,
   0.12371
  ],
  "observed": 0.02037
 },
 "V3_replication": {
  "pass": true,
  "obstructed_rate": 1.0,
  "bridge_contra_rate": 1.0
 },
 "discharged": true
}```
