"""Fixed-Algebra Growing-Web Learner.

A learner whose algebra is frozen and whose only degree of freedom is the web,
projected from an append-only log of bare episodes. Start with :mod:`.episode`
and :mod:`.journal` (the substrate), then :mod:`.algebra`, :mod:`.web`,
:mod:`.holonomy`. See ``docs/dev-doc.md`` and ``docs/scaling.md``.
"""

from .algebra import (
    Algebra,
    CyclicGroup,
    FreeInvolutiveMonoid,
    IntegerGroup,
    KleinFour,
    SymmetricInverseMonoid,
)
from .episode import ACT_NAMESPACE, Episode, world_episode
from .holonomy import (
    Defect,
    cycle_basis_defects,
    defect_mass,
    defects,
    holonomy,
    potential,
)
from .journal import EpisodeId, Journal, NamespaceViolation
from .web import Commit, Edge, Observation, ObservationViolation, Web

__all__ = [
    # substrate
    "Episode",
    "world_episode",
    "ACT_NAMESPACE",
    "Journal",
    "EpisodeId",
    "NamespaceViolation",
    # algebra + web
    "Algebra",
    "IntegerGroup",
    "CyclicGroup",
    "KleinFour",
    "SymmetricInverseMonoid",
    "FreeInvolutiveMonoid",
    "Web",
    "Edge",
    "Commit",
    "Observation",
    "ObservationViolation",
    # holonomy
    "potential",
    "defects",
    "holonomy",
    "defect_mass",
    "cycle_basis_defects",
    "Defect",
]
