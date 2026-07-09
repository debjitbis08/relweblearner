"""Social-graph and world generators for the society layer (PS).

Small, deterministic helpers: concept lists, community/social graphs (as edge
lists over agents), and the fruit fact-world reused from the language phase (its
has-colour relation carries the automorphism orbits that make solipsism debt
concrete).
"""

from __future__ import annotations

import itertools

from .language import HC as FRUIT_HC  # noqa: F401  (re-exported for convenience)
from .language import concept_edges, concept_ids

CONCEPTS = [
    "mango", "banana", "lemon", "apple", "cherry", "lime",
    "yellow", "red", "green", "tree", "herb",
]


def clique_edges(agents: list) -> list:
    """All undirected pairs among ``agents`` (a fully connected community)."""
    return list(itertools.combinations(agents, 2))


def two_communities(agents_a: list, agents_b: list, *, contact: bool = False) -> list:
    """Edge list for two cliques; ``contact`` adds a single bridging edge.

    Without contact the communities form independent dialects; adding the bridge
    opens the channel that (with lateral inhibition) creolizes them.
    """
    edges = clique_edges(agents_a) + clique_edges(agents_b)
    if contact and agents_a and agents_b:
        edges.append((agents_a[0], agents_b[0]))
    return edges


__all__ = [
    "CONCEPTS",
    "clique_edges",
    "two_communities",
    "concept_edges",
    "concept_ids",
    "FRUIT_HC",
]
