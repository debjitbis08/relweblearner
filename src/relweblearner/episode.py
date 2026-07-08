"""The bare episode: the one and only observation format.

"Bare web is the standard." Every event the system ever handles — a world
observation, a learner's own act, an imagined (counterfactual) move — is the
same shape: two collections of opaque object ids and a pairing between them.

    Episode(id1, members1, id2, members2, pairing, cf=False)

There are **no numbers and no relation labels** in an episode. A pairing edge
just says "these two objects were put together"; whether that pairing
*saturates* both sides (MATCH), leaves exactly one over (ONEMORE), or double-
tags an object (a poison contradiction) is *derived* by the learner
(:mod:`relweblearner` P1b), never given. The only structural fact an episode
exposes is :meth:`leftovers` — the objects the pairing did not cover — which
the learner "computes itself" (glossary).

Homoiconicity (invariant 4): a trace of an act is an ordinary ``Episode``, so
the world parser consumes act traces with zero branching on origin.

Provenance (invariant 7): act traces live in a reserved namespace — their ids
start with :data:`ACT_NAMESPACE`. Only the learner mints those; the
:class:`~relweblearner.journal.Journal` rejects any external episode whose ids
intrude on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Hashable, Iterable

#: reserved id prefix for learner-emitted act traces (invariant 7).
ACT_NAMESPACE = "@act"


def in_act_namespace(x: Hashable) -> bool:
    """True iff ``x`` is an id reserved for learner act traces."""
    return isinstance(x, str) and x.startswith(ACT_NAMESPACE)


@dataclass(frozen=True)
class Episode:
    """Two collections and a pairing between them. The bare observation atom.

    Fields are coerced to immutable containers so an episode is hashable and
    safe to store in the append-only journal. Well-formedness (checked on
    construction): every pairing endpoint lies in its collection. Note that a
    *poison* episode that double-tags an object is still well-formed — the
    contradiction is a derived fact, detected downstream, not a parse error.
    """

    id1: Hashable
    members1: frozenset
    id2: Hashable
    members2: frozenset
    pairing: tuple
    cf: bool = False

    def __post_init__(self) -> None:
        # coerce containers (accept set/list/tuple on the way in)
        object.__setattr__(self, "members1", frozenset(self.members1))
        object.__setattr__(self, "members2", frozenset(self.members2))
        object.__setattr__(
            self, "pairing", tuple((a, b) for a, b in self.pairing)
        )
        for a, b in self.pairing:
            if a not in self.members1:
                raise ValueError(f"pairing left endpoint {a!r} not in members1")
            if b not in self.members2:
                raise ValueError(f"pairing right endpoint {b!r} not in members2")

    # ---- structural facts the learner is allowed to read (no numbers) ----
    def leftovers(self) -> tuple[frozenset, frozenset]:
        """The unpaired objects on each side (learner computes leftovers)."""
        left_used = frozenset(a for a, _ in self.pairing)
        right_used = frozenset(b for _, b in self.pairing)
        return self.members1 - left_used, self.members2 - right_used

    def is_injective(self) -> bool:
        """True iff no object is used twice in the pairing (a clean tagging).

        A poison/double-tagged episode returns False; this is *evidence* for a
        derived contradiction, not a validity check.
        """
        lefts = [a for a, _ in self.pairing]
        rights = [b for _, b in self.pairing]
        return len(lefts) == len(set(lefts)) and len(rights) == len(set(rights))

    # ---- namespace / provenance ----
    def all_ids(self) -> set:
        """Every id the episode mentions: collection ids, members, endpoints."""
        ids: set = {self.id1, self.id2}
        ids |= set(self.members1) | set(self.members2)
        for a, b in self.pairing:
            ids.add(a)
            ids.add(b)
        return ids

    def is_act_trace(self) -> bool:
        """True iff this episode is a learner act trace (act-namespace ids)."""
        return in_act_namespace(self.id1) or in_act_namespace(self.id2)

    def touches_act_namespace(self) -> bool:
        """True iff any id (not just the collection ids) is in the reserved
        namespace — used by the journal to reject namespace-squatting."""
        return any(in_act_namespace(x) for x in self.all_ids())

    def as_counterfactual(self) -> "Episode":
        """A cf-flagged copy (invariant 8); content otherwise identical."""
        return Episode(
            self.id1, self.members1, self.id2, self.members2, self.pairing, cf=True
        )


def world_episode(
    id1: Hashable,
    members1: Iterable,
    id2: Hashable,
    members2: Iterable,
    pairing: Iterable = (),
) -> Episode:
    """Construct a world (non-act, non-cf) episode. Convenience for datasets."""
    return Episode(id1, members1, id2, members2, tuple(pairing), cf=False)
