"""Fixed-Algebra Growing-Web Learner.

A learner whose algebra is frozen and whose *only* degree of freedom is the
web. See ``docs/dev-doc.md`` for the full design; start with :mod:`.algebra`,
:mod:`.web`, :mod:`.holonomy`.
"""

from .algebra import Algebra, IntegerGroup
from .holonomy import (
    Defect,
    cycle_basis_defects,
    defect_mass,
    defects,
    holonomy,
    potential,
)
from .web import Edge, Observation, ObservationViolation, Web

__all__ = [
    "Algebra",
    "IntegerGroup",
    "Web",
    "Edge",
    "Observation",
    "ObservationViolation",
    "potential",
    "defects",
    "holonomy",
    "defect_mass",
    "cycle_basis_defects",
    "Defect",
]
