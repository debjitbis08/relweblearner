# Referee report, round 2 — E2b (the overlap forgery) and the design problem

*Referee: please write your feedback in this file, under §2 below. It is
yours alone — nothing here will be edited by us; responses and any accepted
corrections will be worked into the documents under review as a new
revision (as round 1 was, design-problem.md rev 2), with this report
preserved verbatim.*

## 1. What is under review

- `docs/design-problem.md` — the problem statement, updated with the
  settled E2b result (§2, §6 P1 scope, §7, §9, §10).
- `docs/multiweb-overlap-forgery-plan.md` — the E2b pre-registration,
  including the pre-run §3a amendment, the backfilled §2a bring-up
  retune record, and the §8 post-run review notes.
- `results/bench-multiweb-overlap/` — the held-out scored run
  (50 seeds, block 1000–1049) and its report, including the post-run
  P1 attribution (P1 alone would have committed the forgery in 0.82
  of seeds).
- Implementation: `src/relweblearner/bench/multiweb_overlap.py`
  (frozen at commit `8ed73c1`); it reuses
  `src/relweblearner/bench/multiweb.py` unchanged.

Known limitations, disclosed up front rather than discovered: plan §8a
(the implemented Q-D metric was tautological; the pre-registered
attribution was computed post hoc from recorded data) and §8b (Q-E
denominators; baseline comparison).

## 2. Referee feedback

### Overall assessment

The recorded headline arithmetic is internally consistent. In the scored
block, all 50 E2b regions reach `contra >= 2`, E1 and E2 remain at zero, and
the saved corroboration counts are indeed 9 seeds at 0, 35 at 1, and 6 at 2.
Thus the post-hoc statement that P1 would commit the E2b region in 41/50 seeds
is supported by `results.json`. A read-only same-seed comparison against the
unmodified benchmark also produced identical recall and purity, so I found no
hidden collateral change in those two summary quantities.

I nevertheless see several issues. The first affects the interpretation of
the main result; the next three affect metrics or claims; the remaining items
are smaller implementation and reporting discrepancies.

### 1. Major: absence of an edge is not an observed incompatibility in this world model

`obstruction_pair()` calls a mapped backbone edge contradicted whenever the
other independently sampled web lacks a corresponding backbone edge. But each
web is constructed from a finite, noisy sample of 400 episodes. In this model,
an absent or weak target edge can mean "not observed strongly in this view";
it is not explicit negative evidence that the edge is forbidden.

This distinction is visible in the scored data rather than merely
hypothetical. Fifteen genuine region-instances are classified obstructed. A
diagnostic of those rows found that 14 of the 15 used correct direct anchors,
so most are not mapping mistakes: independently sampled true structure simply
failed the target-web backbone test.

Consequently, the experiment does establish a strong statistical
edge-disagreement signal for this constructed dense false merge. It does not,
without an additional completeness/closed-world axiom for each observed web,
establish literal incompatibility, `Ext(s) = empty`, or a policy-free empirical
instance of T2. Treating non-observation as contradiction is itself an
epistemic policy, even though it is distinct from P1. The design problem should
either state that axiom explicitly and justify it for co-occurrence data, or
weaken the conclusion from "extension is impossible" to "the disagreement
detector reliably separates this forgery distribution."

### 2. Q-D was not implemented as pre-registered

The implementation's `QD_e2b_geometric` is the same predicate as Q-B:

```python
lambda a: a["contra"] >= OBS_MIN_CONTRA
```

It therefore only repeats that obstruction fired. It cannot answer the
pre-registered attribution question about what P1 independently would have
done, and it makes the plan's "Q-C passes but Q-D fails" branch unreachable.
Plan §8a correctly identifies this defect, and the required attribution can be
recovered from the saved `corr` field: P1 would commit 41/50 E2b regions.

However, the generated summary in `results.json` and the original Q-D line in
the report still carry the tautological metric. The post-run hand-written
section repairs the interpretation for this run, but the implementation and
machine-readable result remain out of specification and a regenerated report
would lose the repair.

### 3. The P1 conclusion is overstated

The new text says that P1 "does not catch the overlap forgery at all," "fails
to reject at all," and that obstruction is "the only line of defense here."
Those universal statements conflict with the immediately preceding result:
P1 keeps the E2b region provisional in 9/50 seeds and commits it in 41/50.

The supported conclusion is both strong and precise: obstruction catches all
50 constructed E2b cases; P1 fails in 41/50; and in those 41 seeds obstruction
is uniquely responsible for rejection. Equivalently, obstruction is necessary
for complete rejection over the scored block, but P1 is not wholly ineffective
against every overlap forgery. The claims in the report, plan, and design
problem should retain those denominators.

### 4. Two contradicted edges are not two independent refutations

Plan §3a justifies `OBS_MIN_CONTRA = 2` as "at least two independent refuting
backbone edges, so one noisy mapping cannot manufacture a type." The code only
counts edges; it does not require disjoint endpoints, distinct mapping facts,
or direct anchors. One incorrectly mapped node can therefore participate in
several absent target edges and clear the threshold by itself.

This occurs in the scored block: in seed 1029, one incorrectly mapped node
produces two counted contradictions and makes a genuine region obstructed.
This does not explain the E2b headline—the E2b residuals were overwhelmingly
on correct direct anchors, and every seed had at least five such direct
contradictions—but it falsifies the stated noise-robustness rationale for the
threshold and explains one collateral error.

### 5. The forged bridge is not exactly weight-distribution matched

For a selected A-B pair that already has a noise edge, the implementation sets
the final weight to `existing_weight + sampled_intra_weight`. The final bridge
weight is then not a sample from the empirical intra-community distribution as
the plan claims; it is a shifted sample and is systematically stronger.

Across seeds 1000–1049, 179 of 2,092 modified bridge pairs (8.6%) already had
an edge. This is unlikely to explain the large residual separation, but it is
a real construction mismatch and slightly favors both formation of the stable
merge and survival of the forged edges above the backbone threshold.

### 6. The post-run provenance statement contradicts the details it introduces

Plan §8 says its analyses use only recorded `results.json` data, "with no
re-run." Section 8a then says the claims were "verified by recomputation on
individual scored seeds," including correspondence scores up to 0.75 and the
fact that every selected region contains the full A union B. Neither the raw
region memberships nor the correspondence scores are stored in `results.json`.
The report heading likewise says "computed from the frozen results.json, no
re-run."

The scored results need not be changed, but the provenance should distinguish
facts derived directly from the frozen artifact from later deterministic
diagnostic recomputations. As written, a reader cannot reproduce every new
claim from the artifact named as its sole source.

### 7. Q-E uses a broader denominator than the frozen prediction

The frozen Q-E prediction specifies the false-obstruction rate over true
*corroborated* regions. The implementation's `true_rows` includes all true
multi-covered regions regardless of corroboration. This dilutes the stated
denominator, although it does not change the pass in this run: the stored broad
rate is 15/650 = 2.31%, while the requested corroborated-only rate is
15/616 = 2.44%, still below 5%.

The uncommitted review note discloses this mismatch, which is good, but the
machine-generated metric remains mislabeled relative to the pre-registration.

### Recommendation

The empirical separation itself is real and reproducible for the scored
construction. I would accept it as evidence that a count of cross-view edge
disagreements can reject this overlap forgery while E1/E2 provide no checkable
edges. I would not yet accept the stronger identification of that count with a
literal empty extension set or policy-free geometric obstruction. That step
requires an explicit semantics for absent co-occurrence edges and a soundness
argument connecting the operational detector to incompatibility. The Q-D,
denominator, construction, and reporting issues above should also be corrected
or bounded before the result is used as a formal boundary condition for T2.
