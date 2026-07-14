# The P2 discharge — validation results

Pre-registered: docs/p2-discharge.md (note and tolerances committed before this script existed). Model quantities from the declared process, seeds 10000–10199; V1–V3 on the HELD-OUT block 2000–2049; the frozen block 1000–1049 is retrodiction (V4), disclosed as such.

Model: p_miss = 0.0207 [0.0000, 0.0619], delta_x = 0.00046.

| check | held-out (V1–V3) | retro (V4) |
|---|---|---|
| edge rate, correct endpoints | 0.0188 (64/3405) | 0.0215 (77/3582) |
| epsilon_map contradicted edges | 3 | 2 |
| false-obstructed: predicted vs observed | 3.4 vs 10 | 3.91 vs 15 |
| detection: obstructed rate / per-bridge | 1.00 / 1.0000 | 1.00 / 1.0000 |

Verdict (held-out): ```{
 "V1_edge_rate": {
  "pass": true,
  "band": [
   0.0,
   0.12371
  ],
  "observed": 0.0188
 },
 "V2_region_count": {
  "pass": false,
  "band": [
   1.36,
   8.5
  ],
  "predicted": 3.4,
  "observed": 10
 },
 "V3_detection": {
  "pass": true,
  "obstructed_rate": 1.0,
  "bridge_contra_rate": 1.0
 },
 "discharged": false
}```
