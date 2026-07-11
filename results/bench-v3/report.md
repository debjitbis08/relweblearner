# Falsification benchmark — results

50 seeds, ~557 pages and 24 queries each; 22s total. Pre-registered design and predictions: docs/falsification-plan.md (written before this run).

Accuracy, mean +/- sd over seeds:

| family | lookup | induced-rules | oracle-rules | relweb | relweb-noderive |
|---|---|---|---|---|---|
| F1-memory | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 |
| F2-invert-step | 0.00 +/- 0.00 | 0.99 +/- 0.09 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.00 +/- 0.00 |
| F3-skip-transfer | 0.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.00 +/- 0.00 |
| F4-invert-skip | 0.00 +/- 0.00 | 0.99 +/- 0.07 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 0.00 +/- 0.00 |
| F5-refuse-color | 1.00 +/- 0.00 | 0.97 +/- 0.11 | 1.00 +/- 0.00 | 0.99 +/- 0.05 | 1.00 +/- 0.00 |
| F6-plural-likes | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 | 1.00 +/- 0.00 |

Detection (rate over seeds):

| probe | lookup | induced-rules | oracle-rules | relweb |
|---|---|---|---|---|
| D1 direct conflict | 1.00 | 1.00 | 1.00 | 1.00 |
| D2 loop lie | 0.00 | 0.84 | 0.66 | 1.00 |

RelWeb D2 localization (defect touches the lie's endpoints): 0.68

P7 poisoned composition (lie arm; forged rule step+ = near∘near):

| system | junk rule admitted | refusal accuracy on clean chains |
|---|---|---|
| lookup | 0.00 | 1.00 |
| induced-rules | 1.00 | 0.00 |
| oracle-rules | 0.00 | 1.00 |
| relweb | 0.00 | 1.00 |

P8 coherent forgery (lie arm; a consistent phantom world taught only by the liars — coherence is not correspondence, and this arm exists to measure that limit, which is SHARED):

| system | refused (honest) | derived the fabrication |
|---|---|---|
| lookup | 1.00 | 0.00 |
| induced-rules | 0.00 | 1.00 |
| oracle-rules | 1.00 | 0.00 |
| relweb | 0.00 | 1.00 |

RelWeb admitted the phantom structure through the gate: 1.00 of seeds (predicted 1.00 — zero-defect coherent structure is invisible from inside; recovery is provenance: post-retraction refusal 1.00).

F6 as set retrieval (mean precision / recall over the full answer set): lookup 1.00/1.00, induced-rules 0.99/1.00, oracle-rules 1.00/1.00, relweb 1.00/1.00

Poisoning (committed lie repeated when asked): lookup 1.00, induced-rules 1.00, oracle-rules 1.00, relweb 1.00

U1 exact unlearning: relweb answer-match vs liar-free control 1.00; full committed-belief-set match 1.00; baselines exact by construction: True

False alarms on the clean arm (total over seeds): lookup 0, induced-rules 24, oracle-rules 0, relweb 0; every clean-arm gate admission audited true: True
