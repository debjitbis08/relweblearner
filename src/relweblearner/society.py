"""Society — the multi-agent layer (PS; standalone ``docs/spec-society.md``).

Multi-agent is forced *before* perception-at-scale by three facts the earlier
phases establish as limits: (1) a solitary learner grounds word meanings only up
to its concept web's automorphism orbits (the language-spec L3 limit) — only a
peer's ostension discharges the residue; (2) a single learner detects
incoherence but never non-correspondence — disagreement between two coherent
agents is the only native truth signal; (3) several planned measurements are
properties of a *population* of independently grown webs. This module is the
instrument.

Layers:

  * **S0 containerization** — an :class:`Agent` shares no memory; all interaction
    is message-passing. Provenance identity is per **owner**, not per agent
    (the Sybil boundary: N agents under one owner count as ONE origin).
  * **S1 dyad** — a naming game with **lateral inhibition** (Steels). Adopt-on-
    failure alone plateaus as synonyms churn; on a *successful* round both sides
    prune competitors, and only then does agreement converge to 1.0.
  * **S2 teaching** — an utterance read by a listener becomes an ordinary episode
    in its log, carrying the speaker's owner as source, entering the commitment
    policy like any evidence.
  * **S3 citation-tracked gossip** — every claim carries an ORIGIN SET (the owner
    ids where it entered the population); retellings transmit it UNCHANGED, and
    commitment needs ``>= k`` **distinct origins**. A rumor is loud but cites
    itself; independent teaching accumulates citations. The single-agent
    repeat-lie defense, socialized.
  * **S4 population** — agents on a social graph play only with neighbours:
    dialects form without contact, contact creolizes them (with inhibition).
  * **S5 disagreement** — a conflicting claim is not adopted or retracted; it is
    logged as an INTERFACE DEFECT (both origin sets), queryable, and resolved by
    own perception (which outranks testimony) else by origin weight.
"""

from __future__ import annotations

import itertools
import random
from collections import defaultdict

_SYLS = [c + v for c in "bcdfghjklmnpqrstvz" for v in "aeiou"]


# ================================================================= S0 — the agent
class Agent:
    """A containerized learner: concept beliefs + a lexicon + a citation log.

    Shares no memory with any other agent; every interaction below is an explicit
    method call standing in for a message. ``owner`` is the provenance identity
    (many agents may share one owner — the Sybil boundary).
    """

    def __init__(self, aid: str, owner: str | None = None, seed: int = 0):
        self.id = aid
        self.owner = owner if owner is not None else aid
        self._rng = random.Random(seed)
        # naming game: concept -> {word: weight}
        self.assoc: dict = defaultdict(lambda: defaultdict(float))
        # citation log: fact -> set of distinct origin owners
        self.beliefs: dict = defaultdict(set)
        # naive hearing count: fact -> tellings heard (the defeated baseline)
        self.heard: dict = defaultdict(int)
        # facts this agent grounded first-hand (perception outranks testimony)
        self.perceived: dict = {}
        # (other_id, (rel, x)) -> {"mine": (fact, origins), "theirs": (fact, origins)}
        self.interface_defects: dict = {}

    # ----------------------------------------------------- S1/S4 naming game
    def _coin(self) -> str:
        seen = {w for ws in self.assoc.values() for w in ws}
        while True:
            w = "".join(self._rng.sample(_SYLS, 2))
            if w not in seen:
                return w

    def top(self, concept):
        """The word this agent would produce for ``concept`` (None if it has no
        word yet). Highest-weight association, ties broken deterministically.
        """
        words = self.assoc.get(concept)
        if not words:
            return None
        return max(sorted(words), key=lambda w: words[w])

    def produce(self, concept) -> str:
        """Produce a word for ``concept``, coining one if the agent has none."""
        w = self.top(concept)
        if w is None:
            w = self._coin()
            self.assoc[concept][w] = 1.0
        return w

    def _inhibit(self, concept, word):
        """Lateral inhibition: demote competing synonyms for ``concept`` and
        competing meanings for ``word``; drop associations that fall to zero.
        """
        for w in list(self.assoc[concept]):
            if w != word:
                self.assoc[concept][w] -= 1.0
                if self.assoc[concept][w] <= 0:
                    del self.assoc[concept][w]
        for c in list(self.assoc):
            if c != concept and word in self.assoc[c]:
                self.assoc[c][word] -= 1.0
                if self.assoc[c][word] <= 0:
                    del self.assoc[c][word]

    def hear_name(self, concept, word, *, inhibit: bool = True) -> bool:
        """Listener side of one naming-game round (concept given by ostension).

        Returns whether the round *succeeded* (the listener already associated
        ``word`` with ``concept``). Always reinforces; prunes competitors on a
        successful round iff ``inhibit`` — the fix that lets a population
        converge instead of churning synonyms forever.
        """
        success = word in self.assoc[concept]
        self.assoc[concept][word] += 1.0
        if success and inhibit:
            self._inhibit(concept, word)
        return success


def naming_round(speaker: Agent, listener: Agent, concept, *, inhibit: bool = True) -> bool:
    """One joint-attention round: speaker names ``concept``, listener adopts on
    failure; on success both sides reinforce and (with ``inhibit``) prune.
    """
    word = speaker.produce(concept)
    success = listener.hear_name(concept, word, inhibit=inhibit)
    if success and inhibit:
        speaker._inhibit(concept, word)
    return success


def lexicon_agreement(agents: list, concepts: list) -> float:
    """Mean fraction of concepts on which two agents produce the same word,
    averaged over all agent pairs (1.0 = one shared language).
    """
    pairs = list(itertools.combinations(agents, 2))
    if not pairs or not concepts:
        return 1.0
    total = 0.0
    for a, b in pairs:
        shared = sum(1 for c in concepts if a.top(c) is not None and a.top(c) == b.top(c))
        total += shared / len(concepts)
    return total / len(pairs)


def lexical_convergence(agents: list, concepts: list) -> float:
    """How close the population is to ONE word per concept (1.0 = converged).

    For each concept, the share of the single most-held word across all agents'
    inventories. Lateral inhibition prunes synonyms so each concept collapses to
    a shared word (→ 1.0); without it synonyms are never eliminated and the share
    plateaus near ``1/#surviving-synonyms`` — the failure mode being tested.
    """
    from collections import Counter

    total = 0.0
    for c in concepts:
        counts: Counter = Counter()
        for a in agents:
            for w in a.assoc.get(c, ()):
                counts[w] += 1
        if counts:
            total += counts.most_common(1)[0][1] / sum(counts.values())
    return total / len(concepts) if concepts else 1.0


# ------------------------------------------------------ S1 cross-agent adjunction
def cross_agent_adjunction(writer: Agent, reader: Agent, facts: list) -> float:
    """Fraction of facts for which ``read_reader(write_writer(fact)) == fact``.

    The language-spec write/read law, socialized: once two agents share a
    lexicon, one can write a fact the other reads back exactly. Must be 1.0 over
    the expressible set.
    """
    ok = 0
    for rel, x, y in facts:
        tokens = [writer.top(x), writer.top(y)]
        if None in tokens:
            continue
        back = (reader.assoc_meaning(tokens[0]), reader.assoc_meaning(tokens[1]))
        if back == (x, y):
            ok += 1
    return ok / len(facts) if facts else 1.0


def _agent_meaning(agent: Agent, word):
    """Concept the agent comprehends ``word`` as (inverse of production)."""
    best, best_w = None, -1.0
    for c, ws in agent.assoc.items():
        if word in ws and ws[word] > best_w:
            best, best_w = c, ws[word]
    return best


Agent.assoc_meaning = _agent_meaning  # comprehension = inverse of production


# =============================================== S2/S3 — teaching & citation gossip
def teach(speaker: Agent, listener: Agent, fact) -> None:
    """Speaker teaches ``fact``: it enters the listener's log with origin =
    speaker's OWNER (not the agent). Many agents under one owner add one origin.
    Also bumps the naive hearing count (the baseline a rumor defeats).
    """
    listener.beliefs[fact].add(speaker.owner)
    listener.heard[fact] += 1


def relay(teller: Agent, listener: Agent, fact) -> None:
    """Retell a known fact, transmitting its origin set UNCHANGED (a relayer adds
    no citation of its own). Each retelling is one more *hearing*, so naive
    counting climbs with repetition while distinct origins do not.
    """
    if fact in teller.beliefs:
        listener.beliefs[fact] |= teller.beliefs[fact]
        listener.heard[fact] += 1


def committed(agent: Agent, fact, k: int = 3) -> bool:
    """A fact commits only with ``>= k`` DISTINCT origins (default 3)."""
    return len(agent.beliefs.get(fact, ())) >= k


def committed_naive(agent: Agent, fact, k: int = 3) -> bool:
    """The defeated baseline: commit on ``>= k`` *hearings*. A rumor drills this
    threshold with sheer repetition — which is exactly why it is unsafe.
    """
    return agent.heard.get(fact, 0) >= k


def origin_count(agent: Agent, fact) -> int:
    return len(agent.beliefs.get(fact, ()))


def naive_hearing_count(agent: Agent, fact) -> int:
    """How many tellings of ``fact`` this agent has heard (repetition, not
    independence) — the quantity origin-counting deliberately ignores.
    """
    return agent.heard.get(fact, 0)


# ===================================================== S4 — population dynamics
def run_population(agents: list, edges: list, concepts: list, rounds: int,
                   *, inhibit: bool = True, seed: int = 0) -> None:
    """Play naming games along social-graph ``edges`` (neighbours only)."""
    rng = random.Random(seed)
    for _ in range(rounds):
        a, b = rng.choice(edges)
        speaker, listener = (a, b) if rng.random() < 0.5 else (b, a)
        naming_round(speaker, listener, rng.choice(concepts), inhibit=inhibit)


def community_agreement(community: list, concepts: list) -> float:
    return lexicon_agreement(community, concepts)


def cross_agreement(comm_a: list, comm_b: list, concepts: list) -> float:
    """Mean same-word fraction across the two communities (0 = separate dialects)."""
    total, n = 0.0, 0
    for a in comm_a:
        for b in comm_b:
            total += sum(1 for c in concepts if a.top(c) is not None and a.top(c) == b.top(c)) / len(concepts)
            n += 1
    return total / n if n else 0.0


def diffusion_snapshot(agents: list, fact, k: int = 3) -> dict:
    """Adoption (heard at all) vs commitment (>= k distinct origins) for a fact."""
    heard = sum(1 for a in agents if fact in a.beliefs and a.beliefs[fact])
    commit = sum(1 for a in agents if committed(a, fact, k))
    return {"heard": heard, "committed": commit, "n": len(agents)}


# ===================================================== S5 — disagreement protocol
def hear_claim(agent: Agent, other_id: str, fact, origins: set, *, k: int = 3) -> str:
    """Hear a fact-claim. If it conflicts with a COMMITTED belief about the same
    (relation, subject), log an interface defect (both origin sets) instead of
    adopting or retracting. Otherwise accumulate its origins.
    """
    subj = (fact[0], fact[1])
    for f in list(agent.beliefs):
        if (f[0], f[1]) == subj and f[2] != fact[2] and committed(agent, f, k):
            agent.interface_defects[(other_id, subj)] = {
                "mine": (f, set(agent.beliefs[f])),
                "theirs": (fact, set(origins)),
            }
            return "interface_defect"
    agent.beliefs[fact] |= set(origins)
    return "adopted"


def disagreements_with(agent: Agent, other_id: str) -> list:
    """First-class query: what this agent disagrees with ``other_id`` about."""
    return [key for key in agent.interface_defects if key[0] == other_id]


def resolve_defect(agent: Agent, key) -> tuple:
    """Resolve a logged interface defect.

    Perception outranks testimony about one's own log: if the agent perceived
    its own belief first-hand, that wins (the documented consensus≠truth limit).
    Otherwise the claim with greater origin weight wins. Returns the winning fact.
    """
    d = agent.interface_defects[key]
    mine_fact, mine_org = d["mine"]
    their_fact, their_org = d["theirs"]
    if mine_fact in agent.perceived:
        winner = mine_fact                      # perception outranks testimony
    elif len(their_org) > len(mine_org):
        winner = their_fact
        agent.beliefs[their_fact] |= their_org  # adopt the better-cited claim
    else:
        winner = mine_fact
    return winner, ("perception" if mine_fact in agent.perceived else "origin_weight")
