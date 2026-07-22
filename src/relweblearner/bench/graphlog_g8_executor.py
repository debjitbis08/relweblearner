"""Reviewed G8 phase adapters: the full G7 layer plus the interior-decisiveness
overlay, one adapter per study part.

Every phase delegates verbatim to the pinned G7 executor's ``execute_phase``,
so all structural, T5, T6, T7, and accuracy artifacts are byte-identical to a
G7 rerun.  The only G8 addition is one artifact appended in T6 --
``g8-t6-interior-decisiveness.json`` -- carrying the exact-contraction
interior-decisiveness certificate and the single-artifact secondary report
beside the reproduced G7 conditional layer.  No pinned module is modified and
no G7-layer artifact is altered or re-written; the overlay is reconstructed
read-only from the T5 opaque state, exactly as the Part I precomputation
harness does.  Every receipt is re-stamped with the G8 receipt schema.

Part identity is structural, not conventional (plan §4): the module exposes
one pinnable adapter per part -- ``execute_phase_verification`` (Part I,
``g8-verification``) and ``execute_phase_test`` (Part II, ``g8``) -- and the
harness refuses to run a study under the other part's adapter
(``graphlog_g8.G8_EXECUTOR_QUALNAMES``).  Part I overlay statuses use a
disjoint vocabulary (``VERIFIED_PRECOMPUTED*``, never any ``SEPARATING*`` or
``INTERIOR*`` success string) so a sealed Part I artifact -- whose outcome is
precomputed by design -- cannot be miscited as a finding.  Part II keeps the
normal measurement vocabulary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..certification.types import canonical_digest
from . import graphlog_g6_executor as g6x
from . import graphlog_g7_executor as g7x
from .graphlog_certified.linearization import encode_extension
from .graphlog_certified.spec import DEFAULT_SPEC
from .graphlog_g6 import G6Draw, G6Phase
from .graphlog_g7_conditional import conditioned_branch, discover_conditions
from .graphlog_g8 import (
    G8_PART_TEST,
    G8_PART_VERIFICATION,
    G8_RECEIPT_SCHEMA,
)
from .graphlog_g8_conditional import interior_decisiveness, secondary_metrics


G8_EXECUTOR_VERSION = "graphlog-certified-g8-executor/v1"

# G7 conditional statuses whose worlds actually invented a condition with
# solved branches: only these carry an interior-decisiveness certificate.
_CONDITIONED_STATUSES = ("SEPARATING_CONDITIONAL", "CONDITIONED_NOT_SEPARATING")

# Overlay status vocabularies, disjoint by part (plan §4).  Part I statuses
# deliberately contain no SEPARATING/INTERIOR success string: a Part I block
# verifies a precomputation and licenses nothing beyond "the machinery
# computes what the analysis computed".
G8_PART1_OVERLAY_STATUSES = (
    "VERIFIED_PRECOMPUTED",
    "VERIFIED_PRECOMPUTED_PASSTHROUGH",
)
G8_PART2_OVERLAY_STATUSES = (
    "INTERIOR_SEPARATING",
    "SEPARATING_PIVOT_ONLY",
    "NOT_SEPARATING",
    "NO_CONDITIONAL_LAYER",
)


def overlay_status(
    part: str,
    *,
    conditioned: bool,
    certificate: Mapping[str, Any] | None = None,
) -> str:
    """Stamp the overlay status in the vocabulary of the executing part."""
    if part == G8_PART_VERIFICATION:
        return (
            "VERIFIED_PRECOMPUTED" if conditioned
            else "VERIFIED_PRECOMPUTED_PASSTHROUGH"
        )
    if part != G8_PART_TEST:
        raise ValueError(f"unknown G8 part {part!r}")
    if not conditioned:
        return "NO_CONDITIONAL_LAYER"
    if certificate is None:
        raise ValueError("conditioned Part II status requires a certificate")
    if not certificate["separating"]:
        return "NOT_SEPARATING"
    if certificate["interior_separated_pair_count"] > 0:
        return "INTERIOR_SEPARATING"
    return "SEPARATING_PIVOT_ONLY"


def _envelope(artifact_type: str, draw: G6Draw, payload: Any) -> dict[str, Any]:
    value = g7x._envelope(artifact_type, draw, payload)
    value["version_ids"] = {
        **value["version_ids"], "g8_executor": G8_EXECUTOR_VERSION,
    }
    return value


def _receipt(
    phase: G6Phase,
    draw: G6Draw,
    output: Path,
    *,
    status: str,
) -> dict[str, Any]:
    """Rebuild the receipt over the current output directory, G8-stamped.

    Scanning the directory (rather than restamping the delegate receipt)
    guarantees the appended overlay artifact is counted, so the harness's
    artifact-record check still holds.
    """
    receipt = g6x._receipt(phase, draw, output, status=status)
    receipt["schema_version"] = G8_RECEIPT_SCHEMA
    return receipt


def _append_interior_decisiveness(
    part: str, draw: G6Draw, prior: Mapping[G6Phase, Path], output: Path,
) -> None:
    """Append the G8 overlay by reconstructing the conditional layer read-only."""
    g7_record = json.loads(
        (output / "conditional-separation.json").read_text(encoding="utf-8")
    )["payload"]
    g7_status = g7_record.get("status")
    if g7_status not in _CONDITIONED_STATUSES:
        g6x._write_json(output / "g8-t6-interior-decisiveness.json", _envelope(
            "g8-t6-interior-decisiveness/v1",
            draw,
            {
                "part": part,
                "status": overlay_status(part, conditioned=False),
                "g7_conditional_status": g7_status,
                "certificate": None,
                "secondary_metrics": None,
            },
        ))
        return
    (
        _observations, _scope, extensions, _compiled, linearization,
        system, _t5_run,
    ) = g6x._load_state(
        prior[G6Phase.T5] / "opaque-state.pkl", G6Phase.T5, draw,
    )
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
    certificate = interior_decisiveness(
        discovery=discovery,
        branches=branches,
        cochains=cochains,
        coordinate_ids=coordinate_ids,
    )
    # Single-artifact secondary report (plan §5): interior counts and margins,
    # anti-propagation, and the hedge mean/max carried over from the
    # reproduced G7 hedge-localization record.
    secondary = secondary_metrics(
        certificate, g7_record.get("hedge_localization"),
    )
    g6x._write_json(output / "g8-t6-interior-decisiveness.json", _envelope(
        "g8-t6-interior-decisiveness/v1",
        draw,
        {
            "part": part,
            "status": overlay_status(
                part, conditioned=True, certificate=certificate,
            ),
            "g7_conditional_status": g7_status,
            "condition_id": discovery.condition_id,
            "certificate_digest": canonical_digest(certificate),
            "interior_separated_pair_count":
                certificate["interior_separated_pair_count"],
            "bound_soundness_violation_count":
                certificate["bound_soundness_violation_count"],
            "secondary_metrics": secondary,
            "certificate": certificate,
        },
    ))


def _execute_phase(
    part: str,
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """Execute one preregistered G8 phase/world unit via the pinned G7 adapter."""
    base = g7x.execute_phase(
        phase, draw, prior_phase_directories, output_directory,
    )
    if phase is G6Phase.T6 \
            and (output_directory / "conditional-separation.json").is_file():
        try:
            _append_interior_decisiveness(
                part, draw, prior_phase_directories, output_directory,
            )
        except Exception as error:
            g6x._write_json(
                output_directory / "g8-t6-interior-decisiveness.json",
                _envelope(
                    "reported-g8-overlay-failure/v1",
                    draw,
                    {
                        "part": part,
                        "category": (
                            f"{type(error).__module__}."
                            f"{type(error).__qualname__}"
                        ),
                        "detail": str(error),
                    },
                ),
            )
            return _receipt(
                phase, draw, output_directory, status="REPORTED_FAILURE",
            )
    return _receipt(phase, draw, output_directory, status=base["status"])


def execute_phase_verification(
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """Part I (``g8-verification``) adapter: precomputed-verification vocabulary."""
    return _execute_phase(
        G8_PART_VERIFICATION, phase, draw,
        prior_phase_directories, output_directory,
    )


def execute_phase_test(
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """Part II (``g8``) adapter: normal measurement vocabulary."""
    return _execute_phase(
        G8_PART_TEST, phase, draw,
        prior_phase_directories, output_directory,
    )
