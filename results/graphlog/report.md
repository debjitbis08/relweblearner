# GraphLog (external): transport core vs rule mining

7 worlds, 150 training instances each, full test splits; 568s.

| world | majority | transport | transport-oracle | cyk-miner | cyk-oracle | Z-collisions | transports learned |
|---|---|---|---|---|---|---|---|
| rule_43 | 0.004 | 0.004 | 0.050 | 0.451 | 0.585 | 31 | 17/19 |
| rule_44 | 0.000 | 0.123 | 0.248 | 0.639 | 0.785 | 31 | 17/19 |
| rule_21 | 0.048 | 0.515 | 0.576 | 0.763 | 0.878 | 45 | 19/19 |
| rule_22 | 0.029 | 0.029 | 0.455 | 0.807 | 0.873 | 45 | 18/19 |
| rule_19 | 0.050 | 0.060 | 0.415 | 0.685 | 0.807 | 45 | 18/19 |
| rule_18 | 0.010 | 0.010 | 0.263 | 0.414 | 0.515 | 46 | 17/19 |
| rule_0 | 0.002 | 0.034 | 0.022 | 0.423 | 0.484 | 136 | 15/17 |
