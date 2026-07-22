#!/usr/bin/env python3
"""G8 Part I precomputation record: exact-contraction bound-gap analysis.

Reads the sealed G7 block read-only.  For each SEPARATING_CONDITIONAL world it
reconstructs the conditional layer from the sealed T5 opaque state with the
pinned code, verifies the reconstruction reproduces the *entire* sealed G7
conditional-separation certificate (a full canonical-digest comparison, not
just the condition id plus one witness), then, for the tight
exact-contraction bound, reports at every interior differing coordinate:

  1. observed error per side (|field_c - y_c|)          -- ground truth
  2. shipped G7 bound = ||g|| * ||r||   (Cauchy-Schwarz vs GLOBAL residual)
  3. tight G8 bound   = |g . r|         (exact contraction: e = -H_uu^{-1} r,
                       so |e_c| = |g . r|), each + solver_bound + slack.

It also reports the anti-propagation count (§8.4) and the interior-decisiveness
verdict (does gamma - (tight_L + tight_R) > 0 anywhere?).

NOTE ON FAITHFULNESS: this script does not *assume* the reconstruction is
bit-for-bit; it *verifies* it.  The sealed certificate is only trusted to
equal the reconstruction once ``full-certificate comparison passed`` prints
for a world.  Any mismatch aborts with an AssertionError before any bound
numbers are reported.

This is a human-gated read-only analysis.  Per the G8 no-smoke-run rule the
authors do NOT run it against the sealed block as part of implementation; it
imports cleanly and its comparison logic is exercised on synthetic fixtures
(see ``tests/test_graphlog_g8.py``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from relweblearner.bench import graphlog_g6_executor as g6x  # noqa: E402
from relweblearner.certification.types import canonical_bytes  # noqa: E402
from relweblearner.bench.graphlog_certified.linearization import (  # noqa: E402
    encode_extension,
)
from relweblearner.bench.graphlog_certified.spec import DEFAULT_SPEC  # noqa: E402
from relweblearner.bench.graphlog_g6 import G6Phase  # noqa: E402
from relweblearner.bench.graphlog_g7 import (  # noqa: E402
    G7_MANIFEST,
    load_study_manifest,
)
from relweblearner.bench.graphlog_g7_conditional import (  # noqa: E402
    conditional_separation,
    conditioned_branch,
    discover_conditions,
    localized_error_bounds,
)
from relweblearner.bench.graphlog_g8_conditional import (  # noqa: E402
    interior_decisiveness,
    tight_localized_error_bounds,
)
from relweblearner.certification.types import canonical_digest  # noqa: E402


DEFAULT_BLOCK = ROOT / "results/graphlog-certified/g7"
SEPARATING_WORLDS = ("rule_2", "rule_3", "rule_7")


def reconstruct(draw, block):
    """Reconstruct discovery, branches, and cochains from the sealed T5 state."""
    unit = block / f"{draw.ordinal:02d}-{draw.world}"
    (
        _observations, _scope, extensions, _compiled, linearization,
        system, _t5_run,
    ) = g6x._load_state(unit / "T5" / "opaque-state.pkl", G6Phase.T5, draw)
    cochains = tuple(
        encode_extension(extension, linearization).reshape(-1)
        for extension in extensions.solutions
    )
    coordinate_ids = tuple(linearization.core.coordinate_ids)
    discovery = discover_conditions(cochains, coordinate_ids)
    branches = tuple(
        conditioned_branch(
            branch_index=index,
            base_system=system,
            cochain=cochain,
            pivot_indices=discovery.pivot_indices,
            coordinate_ids=coordinate_ids,
            field_tolerance=float(DEFAULT_SPEC.field_tolerance),
        )
        for index, cochain in enumerate(cochains)
    )
    return unit, discovery, branches, cochains, coordinate_ids


def verify_full_certificate(unit, discovery, branches, cochains, coordinate_ids):
    """Full-certificate faithfulness check: reconstruction == sealed cert.

    Compares the canonical digest of the freshly reconstructed G7 certificate
    against the canonical digest of the sealed certificate payload -- every
    pair, bound, witness, and count, not just the condition id and one
    witness.  Returns the reconstructed certificate on success; raises
    AssertionError on any divergence.
    """
    sealed = json.loads(
        (unit / "T6" / "conditional-separation.json").read_text(encoding="utf-8")
    )["payload"]
    live = conditional_separation(
        discovery=discovery,
        branches=branches,
        cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    sealed_cert = sealed["certificate"]
    if canonical_digest(live) != canonical_digest(sealed_cert):
        raise AssertionError(
            "reconstruction does not reproduce the sealed G7 certificate "
            "bit-for-bit; refusing to report bound numbers"
        )
    return live


def analyze(draw, block):
    unit, discovery, branches, cochains, coordinate_ids = reconstruct(draw, block)
    verify_full_certificate(unit, discovery, branches, cochains, coordinate_ids)
    print(f"\n=== {draw.world}  (full-certificate comparison passed) ===")
    print(f"pivot {tuple(coordinate_ids[i] for i in discovery.pivot_indices)}, "
          f"disputed {tuple(coordinate_ids[i] for i in discovery.disputed_indices)}")

    pinned = set(discovery.pivot_indices)
    interior = [i for i in discovery.disputed_indices if i not in pinned]
    v0, v1 = (np.asarray(c, dtype=float) for c in cochains)

    shipped = [localized_error_bounds(b, c, interior)
               for b, c in zip(branches, cochains)]
    tight = [tight_localized_error_bounds(b, c, interior)
             for b, c in zip(branches, cochains)]

    header = (f"  {'coord':<10} {'gamma':>5} | {'obs_L':>8} {'obs_R':>8} | "
              f"{'ship_L':>7} {'ship_R':>7} {'m_ship':>8} | "
              f"{'tght_L':>8} {'tght_R':>8} {'m_tight':>9} | verdict")
    print(header)
    for i in interior:
        if v0[i] == v1[i]:
            continue
        gamma = abs(v0[i] - v1[i])
        m_ship = gamma - shipped[0][i]["bound"] - shipped[1][i]["bound"]
        m_tight = gamma - tight[0][i]["bound"] - tight[1][i]["bound"]
        m_oracle = (gamma - tight[0][i]["observed_error"]
                    - tight[1][i]["observed_error"])
        verdict = ("TIGHT-CERTIFIES" if m_tight > 0 else
                   ("oracle-only" if m_oracle > 0 else "FALSE-CLAIM"))
        print(f"  {coordinate_ids[i]:<10} {gamma:>5.2f} | "
              f"{tight[0][i]['observed_error']:>8.5f} "
              f"{tight[1][i]['observed_error']:>8.5f} | "
              f"{shipped[0][i]['bound']:>7.3f} {shipped[1][i]['bound']:>7.3f} "
              f"{m_ship:>8.3f} | "
              f"{tight[0][i]['bound']:>8.5f} {tight[1][i]['bound']:>8.5f} "
              f"{m_tight:>9.5f} | {verdict}")

    aligns = [tight[s][i]["alignment"] for s in (0, 1) for i in interior]
    print(f"  Cauchy-Schwarz alignment |g.r|/(|g||r|): "
          f"min {min(aligns):.2e}, max {max(aligns):.2e}")

    certificate = interior_decisiveness(
        discovery=discovery,
        branches=branches,
        cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    anti = certificate["anti_propagation"]["anti_propagation_count"]
    print(f"  interior_separated_pair_count = "
          f"{certificate['interior_separated_pair_count']}, "
          f"bound_soundness_violations = "
          f"{certificate['bound_soundness_violation_count']}, "
          f"anti_propagation_count = {anti}")

    best = max(
        (
            (float(abs(v0[i] - v1[i]))
             - tight[0][i]["bound"] - tight[1][i]["bound"], i)
            for i in interior if v0[i] != v1[i]
        ),
    )
    margin, witness_index = best
    return {
        "world": draw.world,
        "pivot_coordinate_ids": [
            coordinate_ids[i] for i in discovery.pivot_indices
        ],
        "certifying_witness_coordinate_id": coordinate_ids[witness_index],
        "tight_interior_margin": margin,
        "interior_separated_pair_count":
            certificate["interior_separated_pair_count"],
        "bound_soundness_violation_count":
            certificate["bound_soundness_violation_count"],
        "anti_propagation_count": anti,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block", type=Path, default=DEFAULT_BLOCK,
                        help="sealed G7 block root (read-only)")
    parser.add_argument("--manifest", type=Path, default=ROOT / G7_MANIFEST)
    parser.add_argument(
        "--emit-expectations", type=Path, default=None,
        help="write the full-precision Part I expectation record (canonical "
             "JSON) to this path; the G8 Part I manifest embeds these values "
             "verbatim, never rounded quotes",
    )
    args = parser.parse_args(argv)
    study = load_study_manifest(args.manifest)
    draws = {draw.world: draw for draw in study.draws}
    records = [analyze(draws[world], args.block) for world in SEPARATING_WORLDS]
    if args.emit_expectations is not None:
        payload = {
            "record_type": "g8-part1-precomputed-expectations/v1",
            "source_study_manifest_id": study.manifest_id,
            "source_block": "results/graphlog-certified/g7",
            "expectations": records,
        }
        args.emit_expectations.write_bytes(canonical_bytes(payload) + b"\n")
        print(f"\nexpectations written: {args.emit_expectations}")


if __name__ == "__main__":
    main()
