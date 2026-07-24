# G9 Phase B execution runbook

Status: AUTHORED 2026-07-24; nothing below has been executed. This is
the ordered procedure from here to a sealed G9 block, with the two
human gates marked. It implements plan §5–§7 with the constants fixed
by the sealed Phase A report §6 and the §8 resolutions.

## Already in place (committed)

- Pinned numerics: `src/relweblearner/bench/graphlog_g9_conditional.py`
  (Chebyshev predictor identical to Phase A round 2, guard band,
  Jeffreys pass rule — reference values cross-validated against the
  §4.5 referee's independent computations).
- Harness: `src/relweblearner/bench/graphlog_g9.py` (manifest loader /
  amendment chain / preflight / executor gating, mirroring G8) and
  `graphlog_g9_executor.py` (`execute_phase_g9` delegates every phase
  verbatim to the pinned G8 part-"g8" adapter and restamps the G9
  receipt schema; no new overlay artifact — the G9 layer is the
  report script).
- Pre-committed analysis: `scripts/g9_phase_b_report.py`
  (verification + measurement modes; mandatory first read of the
  sealed block).
- Phase A record: report sealed at `233fc6e`; script digest
  `c2779fc3…`; outputs `29dc768d…` (round 1), `4fe027a4…` (round 2).

## Step 1 — seed commitment (HUMAN GATE: push)

1. Choose the pulse time T: the first NIST beacon chain-2 pulse at or
   after a chosen UTC minute, far enough out to complete the push
   with margin (G8 used ~19 minutes; allow ≥30 to absorb a slow
   push).
2. Author `results/graphlog-certified/g9-seed-commitment.json`
   (canonical JSON, manifest_id = digest of body): the selection rule
   (chain 2, first pulse ≥ T, master seed = SHA-256 of the
   hex-decoded outputValue), T itself, and the pinned digests —
   Phase A script/report/outputs, `scripts/g9_phase_b_report.py`,
   `src/relweblearner/bench/graphlog_g9_conditional.py`,
   `src/relweblearner/bench/graphlog_g9.py`,
   `src/relweblearner/bench/graphlog_g9_executor.py`, and the
   sealed-g8 `study-index.json` sha256 (`a79b1d4d…`, the ordering
   witness). Pinning the harness pair costs nothing and removes the
   residual post-pulse-edit surface (referee finding).
3. Commit. **Push to origin and confirm the commit is fetchable from
   the public remote BEFORE T** (the §7 public-anchor upgrade). The
   enabling amendment will record the remote-side reference.
4. Deterministic race rule (no discretionary branch): if the push is
   not confirmed before T, the T-pulse is **burned unexpanded** — pick
   T′, amend the commitment, push before T′. Proceeding on local
   evidence is not an option.

## Step 2 — verification pass (after the commitment, before the pulse
is expanded into a manifest)

Run `scripts/g9_phase_b_report.py --mode verification
--phase-a-output <round-2 JSON>`: instrument claims 1–3 on the sealed
g8 block plus bit-identical replication of Phase A's predictions
(plan §8.3 resolution). Outcomes are precomputed and disclosed; any
failure is an implementation defect that stops the ceremony.

## Step 3 — manifest and amendments (after the pulse exists)

1. Fetch pulse ≥ T from chain 2; derive master seed; expand the 44
   per-world draws via the frozen `SHA-256(master ‖ world)`.
2. Author `g9-validation-manifest.json`: G8-shaped body (cohort,
   seed expansion rows, freeze section, acceptance rules) plus the
   loader-validated `g9_preregistration` section (Phase A digests,
   predictor constants, claim-4 floor and pass rule, claim-5 drop,
   non-vacuity minimums, sealed-g8 ordering witness).
3. Author amendment-1 (execution disabled), then the enabling
   amendment-2 pinning `execute_phase_g9`, the implementation files,
   the harness commit, and the remote-side push evidence for the
   commitment commit.
4. `python -m relweblearner.bench.graphlog_g9` preflight must print
   READY (clean worktree, freezes verified, script digests match,
   ordering witness matches, no existing output).

## Step 4 — run (HUMAN GATE: launch)

Detached launch (the G8 pattern: setsid, pid + log in ~), expect
~7 h for 220 units. Success marker: `results/graphlog-certified/g9`
exists via atomic rename and the log ends PROMOTED. Refuse-resume: an
environmentally killed run is deleted unobserved, disposition
amendment authored, relaunched — never resumed.

## Step 5 — first read and closeout

1. FIRST READ of the sealed block:
   `scripts/g9_phase_b_report.py` (measurement mode). No ad-hoc
   inspection before it runs.
2. Receipt re-hash (220 receipts, G9 schema), manifest chain
   recompute, archive to `/data/graphlog-certified/g9`
   destination-verified + symlink (the G6→G8 pattern), §9-style
   execution-outcome write-up in the plan doc, referee-reviewed.
