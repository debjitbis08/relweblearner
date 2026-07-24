"""Reviewed G9 phase adapter: the pinned G8 part-``"g8"`` layer, unchanged.

G9 adds NO overlay artifact.  The G9 layer -- crossing guard band,
ambiguity reporting, predictor evaluation, and the decode-decisiveness
vocabulary -- is realized entirely by the pre-committed Phase B report
script against the sealed block, so the block's artifacts are exactly a G8
part-``"g8"`` unit's: every phase delegates verbatim to the pinned G8 Part
II adapter ``execute_phase_test``, which itself delegates to the pinned G7
executor and appends the ``g8-t6-interior-decisiveness.json`` overlay with
the normal measurement vocabulary.  No pinned module is modified and no
delegate artifact is altered, appended to, or re-written; the only G9
action is re-stamping the returned receipt with the G9 receipt schema so a
sealed G9 block can never be miscited as a G8 one.

The single adapter ``execute_phase_g9`` is the one qualname the harness
will pin (``graphlog_g9.G9_EXECUTOR_QUALNAMES``); no part-less adapter
exists to bypass that pairing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import graphlog_g8_executor as g8x
from .graphlog_g6 import G6Draw, G6Phase
from .graphlog_g9 import G9_RECEIPT_SCHEMA


G9_EXECUTOR_VERSION = "graphlog-certified-g9-executor/v1"
# Module identity constant only: it is not stamped into any artifact -- the
# delegate owns the artifact envelopes, which G9 leaves byte-identical.


def execute_phase_g9(
    phase: G6Phase,
    draw: G6Draw,
    prior_phase_directories: Mapping[G6Phase, Path],
    output_directory: Path,
) -> Mapping[str, Any]:
    """G9 (``g9``) adapter: the pinned G8 Part II computation, G9-stamped."""
    receipt = dict(g8x.execute_phase_test(
        phase, draw, prior_phase_directories, output_directory,
    ))
    receipt["schema_version"] = G9_RECEIPT_SCHEMA
    return receipt
