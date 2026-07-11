# Falsification benchmark — results

5 seeds, ~371 pages and 19 queries each; 1s total. Pre-registered design and predictions: docs/falsification-plan.md (written before this run).

Accuracy, mean +/- sd over seeds:

| family | lookup | induced-rules | oracle-rules | relweb | relweb-noderive |
|---|---|---|---|---|---|
| F1-memory | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 |
| F2-invert-step | 0.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.00 +/- 0.00 |
| F3-skip-transfer | 0.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.00 +/- 0.00 |
| F4-invert-skip | 0.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.80 +/- 0.45 | 0.00 +/- 0.00 |
| F5-refuse-color | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 |
| F6-plural-likes | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 |

Detection (rate over seeds):

| probe | lookup | induced-rules | oracle-rules | relweb |
|---|---|---|---|---|
| D1 direct conflict | 1.00 | 1.00 | 1.00 | 1.00 |
| D2 loop lie | 0.00 | 1.00 | 0.80 | 1.00 |

RelWeb D2 localization (defect touches the lie's endpoints): 0.20

Poisoning (committed lie repeated when asked): lookup 1.00, induced-rules 1.00, oracle-rules 1.00, relweb 1.00

U1 exact unlearning: relweb answer-match vs liar-free control 1.00; baselines exact by construction: True

False alarms on the clean arm (total over seeds): lookup 0, induced-rules 0, oracle-rules 0, relweb 0
