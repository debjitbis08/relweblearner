"""Frozen G0 parameters for the first GraphLog theorem instance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ...certification.types import NormId, canonical_digest


# Copied by value from the reviewed plan.  Never replace this with a dynamic
# import from either legacy runner.
VALIDATION_WORLDS = (
    "rule_1", "rule_2", "rule_3", "rule_4", "rule_5", "rule_6",
    "rule_7", "rule_8", "rule_9", "rule_10", "rule_11", "rule_12",
    "rule_13", "rule_14", "rule_15", "rule_16", "rule_17", "rule_20",
    "rule_23", "rule_24", "rule_25", "rule_26", "rule_27", "rule_28",
    "rule_29", "rule_30", "rule_31", "rule_32", "rule_33", "rule_34",
    "rule_35", "rule_36", "rule_37", "rule_38", "rule_39", "rule_40",
    "rule_41", "rule_42", "rule_45", "rule_46", "rule_47", "rule_48",
    "rule_49", "rule_50",
)


@dataclass(frozen=True, slots=True)
class GraphLogCertifiedSpec:
    schema_version: str = "graphlog-certified/v1"
    dataset_version: str = "graphlog/v1.1"
    observation_family_version: str = "A_G/two-view-triangles-overlap/v1"
    scope_version: str = "W_G/support-closure/v1"
    extension_semantics_version: str = "maximal-supported-partial-bijection/v1"
    derivation_version: str = "D_G/cyk-max-path-5/v1"
    provenance_version: str = "provenance/normalized-refs/v1"
    linearization_version: str = "commutator-role-adjacency/v1"
    comparison_version: str = "graphlog-exact-enriched/v1"
    policy_version: str = "graphlog-p1-p2/v1"
    hardener_version: str = "mutual-argmax/v1"
    artifact_version: str = "graphlog-certified-artifacts/v1"
    target_type: str = "CrossViewRelationIdentity"
    target_commitments: tuple[str, str] = ("IDENTICAL", "DISTINCT")
    runtime_noncommitment: str = "ABSTAIN"
    max_path: int = 5
    anchor_budget: int = 6
    hide_fraction: Fraction = Fraction(15, 100)
    role_channels: tuple[tuple[int, int], ...] = (
        (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1),
    )
    role_channel_weights: tuple[Fraction, ...] = (
        Fraction(1), Fraction(1), Fraction(1),
        Fraction(1), Fraction(1), Fraction(1),
    )
    role_normalization: str = "positive-rational-channel-total/v1"
    decision_norm: NormId = NormId.SUP
    field_norm: NormId = NormId.FROBENIUS
    derivation_operations: tuple[str, ...] = (
        "translate_B_to_A",
        "compose",
        "span_aggregate",
        "path_aggregate",
        "decode_output",
        "decode_identity",
    )
    identity_threshold: Fraction = Fraction(1, 2)
    field_tolerance: Fraction = Fraction(1, 1_000_000)
    kernel_method: str = "sympy-exact-rank/v1"
    spectral_method: str = "residual-eigenbound-plus-gershgorin/v1"
    solver_method: str = "local-gradient-descent/v1"
    solver_step_rule: str = "2/(lambda_min_lower+lambda_max_upper)"
    perturbation_terms: tuple[str, ...] = (
        "rational-vs-float-operator",
        "finite-solver-residual",
        "floating-evaluator-decoder",
        "zero-initial-boundary",
    )

    def __post_init__(self) -> None:
        if self.max_path != 5:
            raise ValueError("the frozen D_G scope requires max_path=5")
        if self.anchor_budget < 0:
            raise ValueError("anchor_budget must be non-negative")
        if self.target_commitments != ("IDENTICAL", "DISTINCT"):
            raise ValueError("the frozen identity commitment set changed")
        if len(self.role_channels) != len(self.role_channel_weights):
            raise ValueError("every role channel requires one weight")
        if len(set(self.role_channels)) != len(self.role_channels):
            raise ValueError("role channels must be unique")
        if any(i == j or i not in range(3) or j not in range(3)
               for i, j in self.role_channels):
            raise ValueError("role channels must be ordered distinct triangle positions")
        if any(weight <= 0 for weight in self.role_channel_weights):
            raise ValueError("declared retained channel weights must be positive")
        if len(set(self.derivation_operations)) != len(self.derivation_operations):
            raise ValueError("derivation operation ids must be unique")
        if not 0 < self.identity_threshold < 1:
            raise ValueError("identity threshold must lie strictly between zero and one")
        if self.field_tolerance <= 0:
            raise ValueError("field tolerance must be positive")

    @property
    def digest(self) -> str:
        return canonical_digest(self)


DEFAULT_SPEC = GraphLogCertifiedSpec()
