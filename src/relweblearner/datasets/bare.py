"""Mixed unlabeled webs for relation-type discovery (P2').

A web with one successor chain and two attribute partitions (colors, plants)
laid over a ``color × plant`` grid. Fruits sit in grid cells; a fruit in cell
``(j, k)`` attaches to color hub ``c{j}`` and plant hub ``p{k}``. The learner
sees only unlabeled edges; ``truth`` (edge → ``succ`` / ``color`` / ``plant``)
is for scoring.

The knob is **crossing observations**: fruits that fill off-diagonal cells so a
color hub and a plant hub *overlap*. Overlap is what keeps the two attribute
systems distinguishable (their hubs are not disjoint). With too few crossings,
some color hub and plant hub are accidentally disjoint and get conflated — the
sparse-coverage failure mode.
"""

from __future__ import annotations

import random


def _all_cells(colors: int, plants: int) -> list:
    return [(j, k) for j in range(colors) for k in range(plants)]


def build_bare_web(
    colors: int = 3,
    plants: int = 2,
    n_crossing: int = 0,
    seed: int = 0,
    base_fruits: int = 3,
    n_chain: int = 20,
    full: bool = False,
) -> tuple[list, dict]:
    """Build an unlabeled edge web + hidden truth.

    Every color and plant hub is established by ``base_fruits`` fruits on a
    diagonal cell (so all hubs clear the degree threshold). Then ``n_crossing``
    fruits are placed in random cells, filling the empty off-diagonal cells that
    would otherwise conflate. ``full=True`` fills every cell (generic coverage).
    """
    rng = random.Random(seed)
    edges: list = []
    truth: dict = {}
    fid = [0]

    def E(u, v, t):
        edges.append((u, v))
        truth[frozenset((u, v))] = t

    def add_fruit(j, k, count):
        for _ in range(count):
            f = f"f{fid[0]}"
            fid[0] += 1
            E(f, f"c{j}", "color")
            E(f, f"p{k}", "plant")

    # the successor chain (the non-attribute relation)
    for i in range(n_chain - 1):
        E(f"n{i}", f"n{i + 1}", "succ")

    if full:
        for j, k in _all_cells(colors, plants):
            add_fruit(j, k, base_fruits)
        return edges, truth

    # base: establish every color hub and every plant hub
    for j in range(colors):
        add_fruit(j, j % plants, base_fruits)
    for k in range(plants):
        if k not in {j % plants for j in range(colors)}:
            add_fruit(0, k, base_fruits)

    # crossing observations: fruits in random cells, each creating overlap
    cells = _all_cells(colors, plants)
    for _ in range(n_crossing):
        j, k = rng.choice(cells)
        add_fruit(j, k, 1)

    return edges, truth
