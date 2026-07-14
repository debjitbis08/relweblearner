# Referee report — the P2 discharge (v1 + v2 validation)

*Delivered inline 2026-07-14; preserved here verbatim. Response:
docs/p2-discharge-referee-response.md.*

I don't think the current evidence supports marking P2 as discharged. I found these issues, ordered by
importance:

- High — α₂ is not a false-alarm bound. The implementation assumes binomially independent edge failures
  conditional on a sampled rate and multiplies those tails across views (src/relweblearner/bench/
  p2_validate.py:267). A1 does not supply that independence: edges share nodes, episodes, and a global
  median threshold. The report itself acknowledges an unmodeled clustering effect and a ×1.95
  underprediction (docs/p2-discharge.md:271). Passing a ×2.5 engineering tolerance makes α₂ a roughly
  calibrated prediction, not the upper bound or "computed error rate" required by the soundness
  statement. Consequently, the claimed implication from obstruction to Ext = ∅ remains unsupported.

- High — the model distribution does not match the evaluated pipeline. model_rates() measures untouched
  generated webs (src/relweblearner/bench/p2_validate.py:58), whereas _pipeline() first mutates view 0
  with the overlap forgery (src/relweblearner/bench/p2_validate.py:109). That mutation changes the
  global backbone threshold and therefore true-edge miss probabilities. On my fresh-block replay, view
  0's average intra-community miss rate changed from 0.03048 to 0.03794; its threshold changed from 3.0
  to 3.234, affecting 23 of 48 valid worlds. Thus F is not the distribution governing all edges used by
  V1/V2, and the evaluated worlds no longer satisfy A1 literally.

- Medium — ε_map is never converted into the probability used by the theorem. The soundness statement
  adds ε_map to a per-region false-alarm probability (docs/p2-discharge.md:87), but the validator
  reports only a raw count of contradicted wrongly mapped edges (src/relweblearner/bench/
  p2_validate.py:206). There is no denominator, region-level probability, or uncertainty bound. In
  particular, zero such edges in the fresh block does not establish ε_map = 0.

- Medium — V3 does not implement its stated eligibility and causality conditions. It accepts two good
  bridges accumulated across all target views, although the theorem requires b_j ≥ 2 in one view. It
  then checks row["contra"], which may have been caused by unrelated edges rather than those bridges
  (src/relweblearner/bench/p2_validate.py:246). My targeted replay found that the stronger intended
  condition happens to hold for all current cases—48/48 fresh and 50/50 held-out—but the validator
  itself can produce a false pass on future data.

- Medium — the pre-registered model seed block is not the block actually sampled. Because model_rates()
  replaces crashing seeds until it obtains 200 successful worlds, it includes seeds 10200 and 10201
  despite the declared block being 10000–10199 (src/relweblearner/bench/p2_validate.py:63). Using
  exactly the 198 successful worlds in the declared block changes α₂ from 5.64 to 5.67, so it does not
  change this verdict, but the report is inaccurate about its model sample.

- Medium — V1's gate is extremely weak and statistically mismatched. It compares an aggregate rate
  across thousands of edges with quantiles of individual world-view rates, then doubles that range.
  Because the lower quantile is zero, the resulting acceptance interval is [0, 0.12371] (src/
  relweblearner/bench/p2_validate.py:295); a rate roughly six times the model mean would still pass.

The recorded totals otherwise reproduce, and the pre-registration chronology looks correct. The worktree
remains clean. I couldn't run the pytest suite because pytest is not installed in the project
environment; the targeted fresh/held-out replays completed successfully.
