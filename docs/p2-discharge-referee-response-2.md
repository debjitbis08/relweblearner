# Authors' response to the P2-discharge referee report, round 2 — all five findings accepted

*2026-07-15. The report (docs/p2-discharge-referee-report-2.md) is
preserved verbatim. The referee's prediction-error bootstrap was reproduced
before acceptance (count PI [2, 17] under integer quantiles vs their
interpolated ~[1.48, 16.76] — same substance, verdict unchanged either
way). Corrections declared in note §14 before the deterministic re-verdict
ran; all gates re-pass under the corrected intervals.*

**Finding 1 (High) — scope. ACCEPTED; renamed, not narrowed by stealth.**
The measured rates are properties of the **declared E2b evaluation
process** — A1 worlds plus the pre-registered overlap-forgery intervention
with its specific bridge density, community selection, and weights — and
every discharge statement now says so (note §13–§14, design-problem
§6/§7/§8/§10). We take the naming option rather than the narrowing option
because this scope is exactly what P2 exists for: licensing the reading of
E2b's verdicts. Behavior under other interventions, or under pristine A1
worlds, is separate, unclaimed work.

**Finding 2 — model-sample uncertainty omitted. ACCEPTED.** The gating
intervals are now the prediction-error bootstrap's (outer resample of the
396 model worlds, then the future block): count PI99 [2, 17], rate PI99
[0.01194, 0.02686]. Observed 9 and 0.01753 remain comfortably inside; the
plain intervals are retained in the artifact for continuity and labeled as
treating the model sample as known.

**Finding 3 — ε_map rule-of-three is not a bound here. ACCEPTED.** The
zero-cell figure is relabeled DESCRIPTIVE with the clustering caveat in
code and report; the gating verdict already absorbs mapping errors through
the total false-obstruction count, as the referee notes.

**Finding 4 — detection uncertainty unreported. ACCEPTED.** Worlds are iid
by construction, so the world-level rule of three is legitimate where the
edge-level one was not: β ≤ 3/395 = 0.0076 at 95% per eligible world is
now attached to the verdict, and β = 0 is never claimed.

**Finding 5 (Low) — no automated tests. ACCEPTED.**
tests/test_p2_validate.py covers both bootstrap variants (including that
prediction-error is at least as wide as plain), all three verdict gates
failing independently, the β-bound voiding on any model detection failure,
a pipeline smoke test with the strict per-view bridge-attribution
condition, and the ε_map descriptive-cell semantics.

**Environment note.** pytest is moved from the runtime dependency list to
the dev dependency group, per the referee's suggestion, with the lockfile
regenerated.
