#!/usr/bin/env python3
"""G8 Part II pre-committed analysis: the preregistered report, sealed first.

Plan §7.2: the entire G8 motivation is that an un-preregistered post-hoc
analysis of the sealed G7 block chose the next bound; leaving the analysis
loop open would reopen exactly that for G9.  This script is therefore
committed and frozen in the Part II amendment chain BEFORE the Part II
manifest is authored, and it is the only sanctioned first read of the sealed
Part II block.

It is an AGGREGATOR, not a re-computer: every number it reports is read from
the sealed artifacts (the harness already computed and receipted them); it
adds no bound, threshold, or criterion.  It evaluates exactly the
preregistered claims of plan §5 and assembles the secondary report under the
G7 secondary-report discipline:

  Instrument claims (exact-arithmetic theorems; failure = defect, block release):
    1. Soundness:  bound_soundness_violation_count == 0 everywhere.
    2. Tightness:  no witness-exclusion / unsound-witness alarm fired
       (any firing is a float-slack breach by theorem, never a discarded
       witness).

  Empirical claims (genuinely falsifiable):
    3. Hedge localization on fresh draws: every conditioned world's
       reproduced G7 hedge record has localized == True (mean absolute
       off-scope error <= its frozen threshold, 0.1).
    4. Conditions invented iff |S| > 1, with AMBIGUITY_OVERFLOW a reported
       outcome, not a defect.

  Non-vacuity (fixed in the plan): fewer than 2 conditioned worlds means the
  block is EMPIRICALLY UNINFORMATIVE for interior decisiveness and no
  mechanism claim of any strength is made.

  Secondary report (measured outcomes, never predictions): the
  interior-decisiveness count, per-pair best interior margins, the
  anti-propagation count, and the mean AND max off-scope field errors (the
  sealed rule_2 draw hides a 1.10 pointwise excursion under a passing 0.016
  mean, so the max is first-class).

Read-only by construction; writes nothing inside the block.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from relweblearner.certification.types import canonical_bytes  # noqa: E402

DEFAULT_BLOCK = ROOT / "results/graphlog-certified/g8"
CONDITIONED_G7_STATUSES = ("SEPARATING_CONDITIONAL", "CONDITIONED_NOT_SEPARATING")
NON_VACUITY_MINIMUM = 2
OVERLAY_NAME = "g8-t6-interior-decisiveness.json"


def _load_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["payload"]


def _pair_alarms(certificate: dict) -> list[str]:
    """Collect every unsound-witness alarm recorded in a certificate."""
    alarms = []
    for pair in certificate.get("compared_pairs", ()):
        for coordinate in pair.get("unsound_witness_coordinate_ids", ()):
            alarms.append(coordinate)
    return alarms


def analyze_block(block: Path) -> dict:
    index = json.loads((block / "study-index.json").read_text(encoding="utf-8"))
    if index.get("part") != "g8":
        raise SystemExit(
            f"refusing to analyze part {index.get('part')!r}: this report is "
            "preregistered for the Part II measurement block only"
        )
    worlds = list(index["world_order"])

    per_world = []
    conditioned = []
    overflowed = []
    soundness_violations = 0
    tightness_alarms = []
    hedge_failures = []
    iff_violations = []
    interior_separating = []

    for ordinal, world in enumerate(worlds):
        unit = block / f"{ordinal:02d}-{world}" / "T6"
        g7 = _load_payload(unit / "conditional-separation.json")
        overlay = _load_payload(unit / OVERLAY_NAME)
        g7_status = g7.get("status")
        conditions_invented = bool(g7.get("conditions_invented"))

        # Claim 4: conditions invented iff |S| > 1.  The G7 layer invents a
        # conditional layer exactly on ambiguity; AMBIGUITY_OVERFLOW is a
        # reported outcome.  A conditioned status without invention (or the
        # converse) is an iff violation.
        if g7_status == "AMBIGUITY_OVERFLOW":
            overflowed.append(world)
        elif conditions_invented != (g7_status in CONDITIONED_G7_STATUSES):
            iff_violations.append(world)

        record = {
            "world": world,
            "g7_conditional_status": g7_status,
            "conditions_invented": conditions_invented,
            "g8_overlay_status": overlay.get("status"),
            "interior_separated_pair_count":
                overlay.get("interior_separated_pair_count"),
            "bound_soundness_violation_count":
                overlay.get("bound_soundness_violation_count"),
            "secondary_metrics": overlay.get("secondary_metrics"),
            "hedge_localization": g7.get("hedge_localization"),
        }
        per_world.append(record)

        if g7_status in CONDITIONED_G7_STATUSES:
            conditioned.append(world)
            soundness_violations += int(
                overlay.get("bound_soundness_violation_count") or 0
            )
            certificate = overlay.get("certificate") or {}
            for coordinate in _pair_alarms(certificate):
                tightness_alarms.append({"world": world, "coordinate": coordinate})
            hedge = g7.get("hedge_localization") or {}
            if hedge.get("localized") is not True:
                hedge_failures.append(world)
            if overlay.get("status") == "INTERIOR_SEPARATING":
                interior_separating.append(world)

    non_vacuous = len(conditioned) >= NON_VACUITY_MINIMUM
    report = {
        "record_type": "g8-part2-preregistered-report/v1",
        "block": str(block),
        "study_manifest_id": index.get("study_manifest_id"),
        "amendment_manifest_id": index.get("amendment_manifest_id"),
        "world_count": len(worlds),
        "conditioned_worlds": conditioned,
        "ambiguity_overflow_worlds": overflowed,
        "claims": {
            "1_tight_bound_soundness": {
                "violation_total": soundness_violations,
                "passed": soundness_violations == 0,
                "on_failure": "implementation/float defect; block release",
            },
            "2_tight_bound_tightness": {
                "witness_exclusion_alarms": tightness_alarms,
                "passed": not tightness_alarms,
                "on_failure": "float-slack breach by theorem; block release",
            },
            "3_hedge_localization_fresh_draws": {
                "failing_worlds": hedge_failures,
                "passed": not hedge_failures,
                "on_failure": "empirical claim genuinely failed; report as such",
            },
            "4_conditions_iff_ambiguous": {
                "iff_violations": iff_violations,
                "passed": not iff_violations,
                "note": "AMBIGUITY_OVERFLOW is a reported outcome, not a defect",
            },
        },
        "non_vacuity": {
            "minimum_conditioned_worlds": NON_VACUITY_MINIMUM,
            "conditioned_world_count": len(conditioned),
            "empirically_informative": non_vacuous,
            "on_vacuous": (
                "report the block as empirically uninformative for interior "
                "decisiveness; no mechanism claim of any strength is made"
            ),
        },
        "secondary_report": {
            "discipline": (
                "measured outcomes only; none of these numbers was predicted "
                "and none licenses a claim beyond its own value"
            ),
            "interior_decisiveness_count": len(interior_separating),
            "interior_separating_worlds": interior_separating,
            "per_world": per_world,
        },
    }
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", type=Path, default=DEFAULT_BLOCK)
    parser.add_argument(
        "--out", type=Path, default=None,
        help="optional path OUTSIDE the block to write the canonical report",
    )
    args = parser.parse_args(argv)
    report = analyze_block(args.block.resolve())
    payload = canonical_bytes(report) + b"\n"
    if args.out is not None:
        out = args.out.resolve()
        if str(out).startswith(str(args.block.resolve())):
            raise SystemExit("refusing to write inside the sealed block")
        out.write_bytes(payload)
    sys.stdout.write(payload.decode("utf-8"))


if __name__ == "__main__":
    main()
