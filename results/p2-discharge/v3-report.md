# The P2 discharge, amendment v3 — direct-simulation validation

Pre-registered: docs/p2-discharge.md §12 (committed before this code or any touch of seed block 4000–4049). Model = the ACTUAL frozen pipeline, forgery mutation included, on the declared block [10000, 10399] (396 valid worlds); 99% predictive intervals by world-level bootstrap (n=20000, seed 4242). Gating block: 4000–4049 (virgin). Other blocks are retrodiction.

Model: per-region false-obstruction rate 0.01262, pooled edge rate 0.01881, eps_map rate 0.02083, detection 395/395; block-count PI99 [2, 16] (mean 8.22), rate PI99 [0.01228, 0.02631].

| block | false-obs total (correct-only) | edge rate | detection |
|---|---|---|---|
| fresh_4000 | 9 (8) | 0.01753 | 50/50 |
| retro_3000 | 11 (11) | 0.02037 | 48/48 |
| retro_2000 | 10 (9) | 0.0188 | 50/50 |
| retro_1000 | 15 (14) | 0.0215 | 50/50 |

Verdict (fresh 4000): ```{
 "V2ppp_count": {
  "pass": true,
  "pi99": [
   2,
   16
  ],
  "predicted_mean": 8.22,
  "observed": 9
 },
 "V1ppp_rate": {
  "pass": true,
  "pi99": [
   0.01228,
   0.02631
  ],
  "predicted_mean": 0.01884,
  "observed": 0.01753
 },
 "V3ppp_detection": {
  "pass": true,
  "eligible": 50,
  "rate": 1.0
 },
 "discharged_measured_tier": true
}```
