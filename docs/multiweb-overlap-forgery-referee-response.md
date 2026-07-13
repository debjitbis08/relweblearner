# Authors' response to referee report, round 2 — all seven points accepted

*2026-07-14. The report (docs/multiweb-overlap-forgery-referee-report.md) is
preserved verbatim; this file records the response and where each accepted
correction was worked in. Before acceptance, every diagnostic the referee
computed was independently reproduced, exactly: 179/2,092 pre-existing wired
bridge pairs (8.6%); the corroborated-only false-obstruction rate 15/616 =
2.44%; 14/15 falsely-obstructed true regions on correct direct anchors, with
seed 1029's single wrong-mapped node (`w1:17`) producing both of its counted
contradictions; ≥ 5 correct-direct-anchor contradictions for E2b in every
seed; and identical same-seed recall/purity against the unmodified benchmark
(50/50 on both). The corrections below therefore adopt the referee's numbers
as jointly verified.*

## Point 1 (major) — absence is not observed incompatibility. ACCEPTED.

This is the round's decisive correction, and it repeats rev 2's lesson one
level down: rev 2 named the closed-world commitment rule a policy (P1); the
referee has now caught a second policy presented as geometry — reading
non-observation of a backbone edge in a finite 400-episode sample as
refutation. It is named **P2** in design-problem §6, with its measured
sampling-variance cost (14/15 collateral flags on correct direct anchors)
stated alongside. All claims of "obstructed / Ext = ∅ / the empirical content
of T2 / policy-free geometric rejection" are weakened to what the run
establishes: a reliable, typed, cross-view **disagreement separation** (E2b
≥ 5 contradictions on correct direct anchors every seed; E1/E2 exactly 0).
The identification with literal incompatibility is carried as a standing
proof obligation — the **P2 discharge**: an explicit semantics for absent
co-occurrence edges plus a soundness argument connecting the operational
detector to Ext = ∅. Worked into design-problem (header, §2, §6, §7 E2b,
§8 T2, §9, §10), plan §9, and the results report.

## Point 2 — Q-D not implemented as pre-registered. ACCEPTED.

Self-identified in plan §8a and confirmed by the referee; the residual issue
the referee adds — that the machine-readable summary still carries the
tautological metric and a regenerated report would lose the hand repair — is
recorded as a re-run obligation in plan §8a/§9 (implement Q-D as the
P1-would-commit attribution over the saved `corr` field). The frozen scored
artifacts are left as they are.

## Point 3 — the P1 conclusion was overstated. ACCEPTED.

"P1 fails to reject at all" and "the only line of defense" conflicted with
the 9/50 provisional seeds. All statements now retain the denominators: P1
commits the false merge in 41/50 seeds and keeps it provisional in 9; the
detector catches all 50, is uniquely responsible in the 41, and is necessary
for complete rejection over the scored block. Corrected in plan §8a (with a
note that the earlier draft overstated), design-problem §2/§6/§7/§9/§10, and
the results report.

## Point 4 — two contradicted edges are not two independent refutations. ACCEPTED.

The §3a rationale for `OBS_MIN_CONTRA = 2` ("one noisy mapping cannot
manufacture a type") is falsified as stated: the gate counts edges, not
independent witnesses, and seed 1029 shows one wrong-mapped node clearing it
alone, producing one collateral error. The frozen §3a text stands as written;
the correction and the re-run obligation (require contradictions from
independent, directly anchored witnesses) are recorded in plan §9, and
design-problem §2 carries the caveat next to the count-not-ratio lesson.

## Point 5 — the forged bridge is not exactly weight-distribution matched. ACCEPTED.

`existing_weight + sampled_intra_weight` on the 8.6% of wired pairs with a
pre-existing noise edge is a shifted sample, systematically stronger than the
plan's matching claim, slightly favoring merge formation and backbone
survival. We agree with the referee's bound that this is unlikely to explain
the separation (the residual floor of 5 direct-anchor contradictions per seed
argues the same way), and record it as a construction mismatch with a re-run
obligation (replace, don't add — or declare the shift) in plan §9 and the
results report.

## Point 6 — the post-run provenance statement contradicted its own details. ACCEPTED.

The §8 preamble and the report heading said "no re-run" while §8a cited facts
(region memberships, correspondence scores) not stored in `results.json`.
Both now distinguish provenance (a) — read directly from the frozen
artifact — from provenance (b) — deterministic diagnostic recomputation of
individual scored seeds with the frozen module — and §8a's claims are marked
accordingly.

## Point 7 — Q-E used a broader denominator than the frozen prediction. ACCEPTED.

The corroborated-only rate the prediction names is 15/616 = 2.44% (jointly
verified), vs the stored broad 15/650 = 2.31%; the < 0.05 gate passes under
both. Recorded in plan §9 and the results report; the mislabeled machine
metric is a re-run obligation.

## On the recommendation

We adopt the referee's closing position as the project's: the scored
separation stands as evidence that a count of cross-view edge disagreements
rejects this overlap forgery while E1/E2 provide no checkable edges; the
identification of that count with an empty extension set is withdrawn until
the P2 discharge is done. E2b is accordingly demoted from "T2's empirical
anchor" to "T2's candidate anchor" everywhere, and the P2 discharge is listed
in design-problem §10 as a prerequisite for using E2b as a formal boundary
condition of T2.
