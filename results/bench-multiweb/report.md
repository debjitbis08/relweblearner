# Multi-web interference — results

50 seeds, ~4s per run. Pre-registered design and predictions:
docs/multiweb-plan.md (committed at ce78b95, before the first run). Two runs
are reported: run 1 as pre-registered, run 2 after the single §7b amendment
(extension restricted to the structural backbone). No other constant changed
between runs.

## The decisive comparison (rates over 50 seeds, run 2)

| outcome | one-web | multi-web |
|---|---|---|
| coherent forgery accepted as concept | **1.00** | **0.00** |

The forged region — internally indistinguishable from a real concept by
construction — passes the one-web stability test in every seed. It fails
cross-web correspondence in every seed.

## Correspondence (the interference signal)

| quantity | run 1 | run 2 |
|---|---|---|
| forged region best cross-web score | 0.09 | **0.00** |
| true-region score, checkable (>=2 mapped members) | 1.00 | **1.00** |
| true-region score, all | 0.92 | 0.92 |
| forged below theta = 0.6 | 0.96 | **1.00** |

Separation is complete in run 2: the distributions do not touch. The 0.92
"all" figure reflects true regions whose image fell below the 2-member floor
in one view pair (they corroborate through the other pair — recall below).

## Scorecard against the frozen predictions

| quantity | run 1 | run 2 | prediction |
|---|---|---|---|
| P-A one-web accepts the forgery | 1.00 | 1.00 | >= 0.90 PASS |
| P-B forged below theta | 0.96 | 1.00 | >= 0.95 PASS |
| P-C forgery kept out of projection | 0.96 | 1.00 | >= 0.95 PASS |
| P-C concept recall (>=2-view communities) | 0.97 | 0.96 | >= 0.80 PASS |
| P-C concept purity | 1.00 | 1.00 | >= 0.90 PASS |
| P-D solo truth found stable | 1.00 | 1.00 | (precondition) |
| P-D solo truth kept provisional | **0.82 FAIL** | 1.00 | >= 0.90 |
| P-E forged nodes given images | 0.105 | 0.00 | <= 0.10 PASS |

**Run 1 failed P-D** — in the direction §7 pre-designates as an
implementation leak, and the diagnosis confirmed it: the structural extension
hallucinated images for never-co-witnessed nodes over weight-1 noise edges;
two such images landing in one region clear the >= 2-member floor at
concentration 1.0. The §7b fix (identity evidence only rides edges above
half the web's median weight — web-local, label-free) closes the leak and
simultaneously zeroes P-E. Every other metric moved only toward the
predictions, so the fix bought no blindness: recall 0.97 -> 0.96, purity
1.00 -> 1.00.

## Reading

1. **Coherence is not correspondence, and now the difference is measured
   geometrically.** Bench v3's P8 showed every composing single-substrate
   system derives a coherent forgery; recovery there was provenance-only.
   Here, with an ensemble of opaque webs from different views, the same kind
   of forgery is excluded by structure alone: it is stable *within* its web
   and corresponds to nothing *between* webs.
2. **The honest limit held, both ways.** The solo control — a TRUE community
   seen by only one view — is also left provisional in every seed.
   Interference measures correspondence, not truth; a single-source truth
   and a fabrication are indistinguishable until another view covers them or
   provenance is consulted. "Provisional" is the calibrated answer, not a
   miss.
3. **The projection did not pay for safety with blindness.** 96% of
   multi-view communities project as concepts at purity 1.00, through
   mappings that are deliberately partial (anchor rate 0.4 of co-visible
   entities plus a conservative backbone-only extension).
4. **What this says about the current system.** Per plan §8: this success
   indicts the single-web implementation rather than validating it. Concepts
   as labelled nodes/edges in one substrate cannot express the quantity that
   did the work here — cross-web corroboration of stable regions. The
   realignment target is the ensemble: opaque episodes -> several webs ->
   stable regions -> interference -> projected semantics, with the existing
   labelled-graph machinery reinterpreted as one *projection* of that
   ensemble, and P8-class forgeries handled by geometry first, provenance
   second.

## Caveats

- One world family (planted co-occurrence communities), one forgery family
  (statistics-matched phantom cluster), K = 3 views. The forger here cannot
  see the other webs; a forger who corrupts *two* views defeats
  2-corroboration by construction — robustness is a quorum property, as in
  bench v3's collusion arm.
- Anchors are given, not discovered (rate 0.4 of co-visible entities); the
  discovered part of the mapping (backbone extension) contributes but was
  not ablated separately.
- Stable-region discovery is Louvain + dropout persistence — a stand-in for
  "invariants of the dynamics", chosen for minimality, not a claim about the
  right dynamics.
