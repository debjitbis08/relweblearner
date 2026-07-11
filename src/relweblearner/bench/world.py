"""The benchmark world: an ordered chain spoken through surface frames.

A hidden linear order over freshly named entities is expressed through SIX
frame families. Nothing in the stream names a relation or a number; the
learner sees only ``{book, tokens, picture}`` pages, exactly like every other
corpus. The GOLD stream (relation, source, target per page) is returned
separately for the baselines — the creature never sees it.

The relations, and what each one probes:

    step+   ``<x> comes right after <y>``   (x = y+1; functional)
    step-   ``<x> is just before <y>``      (x = y-1; step+'s converse)
    skip+   ``<x> sits two past <y>``       (x = y+2; functional)
    skip-   ``<x> lies two shy of <y>``     (x = y-2; skip+'s converse)
    color   ``the <x> looks <c>``           (functional attribute; no order)
    likes   ``<x> plays with <y>``          (symmetric, genuinely many-valued)

Holdouts (per seed, disjoint):

    F2  step- never taught for INVERT_STEP pairs   -> ask it (inversion)
    F4  skip- never taught for INVERT_SKIP pairs   -> ask it (inversion)
    F3  skip never taught AT ALL for TRANSFER pairs whose step path is fully
        taught -> ask skip+ (answerable only by discovering skip = step∘step)
    F5  color never taught for REFUSE entities     -> ask it (must refuse)

Lies (two colluding books, so they commit at k=2):

    D1  a second color for an entity with a committed true color — a direct
        functional double-target any conflict rule can see.
    D2  a step+ fact ``<e_j+1> comes right after <e_far>`` for a subject whose
        TRUE step+ page is never taught by anyone — no double-target exists,
        so a lookup conflict rule is structurally blind to it; the lie is
        visible only as a loop that fails to close.

Determinism: everything is drawn from one ``random.Random(seed)``; the same
seed always yields the identical stream, gold, and query set.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# Surface vocabulary the entity names must avoid.
ANCHORS = {"comes", "right", "after", "is", "just", "before", "sits", "two",
           "past", "lies", "shy", "of", "the", "looks", "plays", "with"}
COLORS = ["red", "blue", "green", "gold"]

N_CHAIN = 12          # entities on the hidden line
INVERT_STEP = 3       # F2: step- held-out pairs
INVERT_SKIP = 2       # F4: skip- held-out pairs
TRANSFER = 3          # F3: skip pairs held out entirely
REFUSE = 3            # F5: entities with no color taught
HONEST_BOOKS = 4
WITNESSES = 2         # distinct honest books per taught fact (= commit_k)
REPEATS = 3           # pages per (fact, book) — induction mass
OFF_FRAME_RATE = 0.03
GOSSIP_RATE = 0.02    # single-source junk; must never commit at k=2

OFF_FRAME = [
    ["what", "a", "fine", "day"],
    ["let", "us", "walk", "along"],
    ["that", "was", "quite", "enough"],
]

_CONSONANTS = "bdfgklmnprstvz"
_VOWELS = "aeiou"

# v2, the poisoned-composition arm: stranger chains of the symmetric 'near'
# relation, three of them capped by FORGED step+ facts (the liars fabricating
# self-licensing composition evidence), two kept clean as garbage probes.
STRANGER_CHAINS = 5
FORGED_CHAINS = 3


def _names(rng: random.Random, n: int, avoid: tuple = ()) -> list[str]:
    """Fresh CVCVC entity names, disjoint from every anchor/color word."""
    out: list[str] = []
    seen = set(ANCHORS) | set(COLORS) | set(OFF_FRAME[0] + OFF_FRAME[1] + OFF_FRAME[2])
    seen |= set(avoid)
    while len(out) < n:
        w = (rng.choice(_CONSONANTS) + rng.choice(_VOWELS) + rng.choice(_CONSONANTS)
             + rng.choice(_VOWELS) + rng.choice(_CONSONANTS))
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


# ------------------------------------------------------------- rendering
# Each renderer returns (tokens, picture); picture is the FIRST slot filler,
# so the oriented fact is (picture, other) — the same convention as every
# other corpus generator.

def _r_step_fwd(x, y):    return ([x, "comes", "right", "after", y], x)
def _r_step_rev(x, y):    return ([x, "is", "just", "before", y], x)
def _r_skip_fwd(x, y):    return ([x, "sits", "two", "past", y], x)
def _r_skip_rev(x, y):    return ([x, "lies", "two", "shy", "of", y], x)
def _r_color(x, c):       return (["the", x, "looks", c], x)
def _r_likes(x, y):       return ([x, "plays", "with", y], x)
def _r_near(x, y):        return ([x, "stands", "near", y], x)
def _r_fstep(x, y):       return ([x, "drifts", "toward", y], x)     # P8: forged family
def _r_fskip(x, y):       return ([x, "vaults", "beyond", y], x)

RENDER = {"step+": _r_step_fwd, "step-": _r_step_rev,
          "skip+": _r_skip_fwd, "skip-": _r_skip_rev,
          "color": _r_color, "likes": _r_likes, "near": _r_near,
          "fstep": _r_fstep, "fskip": _r_fskip}

# How each relation is ASKED (the second slot blanked).
ASK = {"step+": "{s} comes right after ?", "step-": "{s} is just before ?",
       "skip+": "{s} sits two past ?", "skip-": "{s} lies two shy of ?",
       "color": "the {s} looks ?", "likes": "{s} plays with ?",
       "fstep": "{s} drifts toward ?", "fskip": "{s} vaults beyond ?"}


@dataclass
class World:
    """One seeded benchmark instance: the stream, the gold, and the answer key."""
    seed: int
    chain: list[str]                       # entities in hidden order
    episodes: list[dict]                   # what every system is trained on
    gold: list[tuple | None]               # per-episode (rel, src, tgt); None = junk/off-frame
    queries: list[dict]                    # {family, rel, phrase, subject, expect}
    liar_books: tuple[str, str] = ("liar-a", "liar-b")
    d1: dict = field(default_factory=dict)  # the functional lie {subject, wrong, right}
    d2: dict = field(default_factory=dict)  # the loop lie {subject, wrong, right}
    forged: dict = field(default_factory=dict)  # the P7 attack {rule, forged_subjects, probes}


def generate(seed: int = 0) -> World:
    rng = random.Random(seed)
    chain = _names(rng, N_CHAIN)
    colors = {e: rng.choice(COLORS) for e in chain}
    books = [f"h{i}" for i in range(HONEST_BOOKS)]

    # ---------------- holdout selection (disjoint index pools)
    step_pairs = list(range(N_CHAIN - 1))            # i -> (chain[i], chain[i+1])
    skip_pairs = list(range(N_CHAIN - 2))            # i -> (chain[i], chain[i+2])
    pool = rng.sample(step_pairs[1:-1], INVERT_STEP + 1)   # keep chain ends taught
    invert_step, d2_pair = set(pool[:INVERT_STEP]), pool[INVERT_STEP]
    # F3 transfer pairs: their step path must be fully taught, so avoid d2's
    # missing step+ page. (invert_step only drops step-, the path survives.)
    transfer_ok = [i for i in skip_pairs if d2_pair not in (i, i + 1)]
    picked = rng.sample(transfer_ok, TRANSFER + INVERT_SKIP)
    transfer, invert_skip = set(picked[:TRANSFER]), set(picked[TRANSFER:])
    refuse = set(rng.sample(chain, REFUSE))

    # likes: unordered pairs at chain distance >= 3, so the symmetric class
    # shares NO entity pair with the order relations. (Bring-up finding,
    # recorded in the plan doc: a symmetric relation that shares >= 2 pairs
    # with an order relation welds into its gauge group and 2g = 0 zeroes the
    # whole group's transports — the discovered order is erased. The main
    # world isolates that fragility instead of letting it confound every
    # family; the overlap variant is a separate stressor.)
    idx = {e: i for i, e in enumerate(chain)}
    def _far_pair():
        while True:
            a, b = rng.sample(chain, 2)
            if abs(idx[a] - idx[b]) >= 3:
                return tuple(sorted((a, b)))
    likes_pairs = {_far_pair() for _ in range(8)}
    hub = rng.choice(chain)
    far_others = [e for e in chain if abs(idx[e] - idx[hub]) >= 3]
    likes_pairs |= {tuple(sorted((hub, o))) for o in rng.sample(far_others, 2)}

    # ---------------- the taught fact list: (rel, src, tgt)
    facts: list[tuple] = []
    for i in step_pairs:
        x, y = chain[i + 1], chain[i]
        facts.append(("step+", x, y)) if i != d2_pair else None
        if i not in invert_step:
            facts.append(("step-", y, x))
    for i in skip_pairs:
        if i in transfer:
            continue
        x, y = chain[i + 2], chain[i]
        facts.append(("skip+", x, y))
        if i not in invert_skip:
            facts.append(("skip-", y, x))
    for e in chain:
        if e not in refuse:
            facts.append(("color", e, colors[e]))
    for a, b in sorted(likes_pairs):
        facts.append(("likes", a, b))
        facts.append(("likes", b, a))

    # ---------------- the lies
    d1_victim = rng.choice([e for e in chain if e not in refuse])
    d1_wrong = rng.choice([c for c in COLORS if c != colors[d1_victim]])
    d1 = {"subject": d1_victim, "wrong": d1_wrong, "right": colors[d1_victim]}
    # the loop lie's far endpoint must stay >= 2 steps from its subject (so the
    # loop is real) and off every holdout-query entity (families stay isolated:
    # a lie endpoint on an F2 subject creates a tied derived answer there,
    # measuring the lie twice).
    # only F2 subjects need blocking: the lie is a STEP edge, and derivation
    # runs per gauge web, so skip-web queries (F3/F4) cannot route through it.
    # Distance >= 3 keeps the lying pair off every TRUE relation shape (step
    # is 1, skip is 2), and off the likes pairs: a committed lie whose
    # converse lands in another class is converse-link evidence that welds
    # gauge groups (a designed stressor for later, not this world).
    subject_idx = d2_pair + 1
    blocked = {j for p in invert_step for j in (p, p + 1)}
    far = rng.choice([j for j in range(N_CHAIN)
                      if abs(j - subject_idx) >= 3 and j not in blocked
                      and tuple(sorted((chain[j], chain[subject_idx]))) not in likes_pairs])
    d2 = {"subject": chain[subject_idx], "wrong": chain[far],
          "right": chain[d2_pair]}
    lies = [("color", d1["subject"], d1["wrong"]),
            ("step+", d2["subject"], d2["wrong"])]

    # ---------------- render the stream: every fact from WITNESSES distinct
    # honest books, REPEATS pages each; lies from both liar books.
    pages: list[tuple[dict, tuple | None]] = []
    for rel, s, t in facts:
        for book in rng.sample(books, WITNESSES):
            tokens, pic = RENDER[rel](s, t)
            for _ in range(REPEATS):
                pages.append(({"book": book, "tokens": list(tokens),
                               "picture": pic, "marks": None}, (rel, s, t)))
    for rel, s, t in lies:
        for book in ("liar-a", "liar-b"):
            tokens, pic = RENDER[rel](s, t)
            for _ in range(REPEATS):
                pages.append(({"book": book, "tokens": list(tokens),
                               "picture": pic, "marks": None}, (rel, s, t)))

    # single-source gossip junk (must never commit) + off-frame narrative.
    # Junk is drawn only on entity pairs with NO true fact in ANY relation,
    # either direction: commitment is per edge while class maps are per frame,
    # so junk expressed over an already-committed pair would piggy-back into a
    # second relation class on one witness (bring-up finding, see plan doc).
    n_gossip = int(GOSSIP_RATE * len(pages))
    taught_pairs = {(s, t) for _r, s, t in facts} | {(t, s) for _r, s, t in facts} \
        | {(s, t) for _r, s, t in lies} | {(t, s) for _r, s, t in lies}
    # Junk is step+ only: a single junk COLOR page makes its subject raw-
    # multi-valued, and a few of those make the whole color class look
    # genuinely many-valued — suppressing the D1 conflict the benchmark is
    # supposed to probe (functionality is judged on raw testimony, by design).
    off_limits = refuse | {d1["subject"], d2["subject"]}   # keep F5/D-probes unpolluted
    drawn: set = set()
    for g in range(n_gossip):
        while True:
            s = rng.choice([e for e in chain if e not in off_limits])
            t = rng.choice(chain)
            if s != t and (s, t) not in taught_pairs and ("step+", s, t) not in drawn:
                drawn.add(("step+", s, t))
                break
        rel = "step+"
        tokens, pic = RENDER[rel](s, t)
        pages.append(({"book": f"gossip-{g}", "tokens": list(tokens),
                       "picture": pic, "marks": None}, (rel, s, t)))
    for _ in range(int(OFF_FRAME_RATE * len(pages))):
        pages.append(({"book": rng.choice(books),
                       "tokens": list(rng.choice(OFF_FRAME)),
                       "picture": None, "marks": None}, None))

    rng.shuffle(pages)
    episodes = [p for p, _g in pages]
    gold = [g for _p, g in pages]

    # ---------------- the answer key
    queries: list[dict] = []

    def ask(family, rel, s, expect):
        queries.append({"family": family, "rel": rel, "subject": s,
                        "phrase": ASK[rel].format(s=s), "expect": expect})

    for i in rng.sample([i for i in step_pairs if i != d2_pair and i not in invert_step], 4):
        ask("F1-memory", "step+", chain[i + 1], chain[i])
    for e in rng.sample([e for e in chain if e not in refuse and e != d1["subject"]], 3):
        ask("F1-memory", "color", e, colors[e])
    for i in sorted(invert_step):
        ask("F2-invert-step", "step-", chain[i], chain[i + 1])
    for i in sorted(transfer):
        ask("F3-skip-transfer", "skip+", chain[i + 2], chain[i])
    for i in sorted(invert_skip):
        ask("F4-invert-skip", "skip-", chain[i], chain[i + 2])
    for e in sorted(refuse):
        ask("F5-refuse-color", "color", e, None)
    partners = sorted({b for a, b in likes_pairs if a == hub}
                      | {a for a, b in likes_pairs if b == hub})
    ask("F6-plural-likes", "likes", hub, set(partners))

    # ---------------- v2: the poisoned-composition attack (P7)
    # Off-chain STRANGER entities in 3-chains of the symmetric 'near'
    # relation; the liars cap FORGED_CHAINS of them with forged step+ facts
    # ("end2 comes right after end0") — SELF-LICENSING composition evidence:
    # the only near∘near body pairs whose subject carries any step+ testimony
    # are exactly the forged heads, so a PCA-confidence rule miner reads the
    # rule step+ = near∘near at confidence 1.0, while accepting it as a
    # geometric constraint would force g(step) = 0 + 0 and zero a live gauge
    # group. The clean chains are the garbage probes: a system that admitted
    # the rule derives step+ facts there; the right answer is refusal.
    # A CHILD rng keeps every draw above bit-identical to bench v1; stranger
    # pages append after the main stream, shuffled among themselves.
    srng = random.Random((seed << 16) + 7)
    strangers = _names(srng, 3 * STRANGER_CHAINS, avoid=tuple(chain))
    chains3 = [strangers[i * 3:i * 3 + 3] for i in range(STRANGER_CHAINS)]
    spages: list[tuple[dict, tuple | None]] = []
    for c3 in chains3:
        for x, y in ((c3[0], c3[1]), (c3[1], c3[2])):
            for s, t in ((x, y), (y, x)):                  # symmetric: both ways
                for book in srng.sample(books, WITNESSES):
                    tokens, pic = _r_near(s, t)
                    for _ in range(REPEATS):
                        spages.append(({"book": book, "tokens": list(tokens),
                                        "picture": pic, "marks": None},
                                       ("near", s, t)))
    forged_subjects = []
    for c3 in chains3[:FORGED_CHAINS]:
        s, t = c3[2], c3[0]                                # end2 comes right after end0
        forged_subjects.append(s)
        for book in ("liar-a", "liar-b"):
            tokens, pic = _r_step_fwd(s, t)
            for _ in range(REPEATS):
                spages.append(({"book": book, "tokens": list(tokens),
                                "picture": pic, "marks": None},
                               ("step+", s, t)))
    srng.shuffle(spages)
    episodes += [p for p, _g in spages]
    gold += [g for _p, g in spages]
    probes = []
    for c3 in chains3[FORGED_CHAINS:]:
        for s in (c3[0], c3[2]):                           # both clean-chain ends
            ask("P7-junkcomp", "step+", s, None)
            probes.append(s)
    forged = {"rule": ("step+", "near", "near"),
              "forged_subjects": forged_subjects, "probes": probes}

    # ---------------- v3: the COHERENT forgery (P8)
    # The liars fabricate a wholly consistent phantom world: fresh entities
    # in a chain, a forged step family and a forged skip family whose
    # triangles all close. Nothing contradicts anything — coherence is not
    # correspondence, so the composition gate is PREDICTED to admit the
    # structure with zero defects, and the creature to DERIVE the held-out
    # fabricated facts (P8 probes; the correspondence-honest answer is
    # refusal). The recovery story is provenance, not geometry: retracting
    # the liars must erase the whole phantom component exactly.
    prng = random.Random((seed << 16) + 13)
    phantoms = _names(prng, 6, avoid=tuple(chain) + tuple(strangers))
    p8pages: list[tuple[dict, tuple | None]] = []
    fskip_holdout = prng.randrange(len(phantoms) - 2)
    for i in range(len(phantoms) - 1):
        x, y = phantoms[i + 1], phantoms[i]
        for book in ("liar-a", "liar-b"):
            tokens, pic = _r_fstep(x, y)
            for _ in range(REPEATS):
                p8pages.append(({"book": book, "tokens": list(tokens),
                                 "picture": pic, "marks": None}, ("fstep", x, y)))
    for i in range(len(phantoms) - 2):
        if i == fskip_holdout:
            continue                                       # the derivation probe
        x, y = phantoms[i + 2], phantoms[i]
        for book in ("liar-a", "liar-b"):
            tokens, pic = _r_fskip(x, y)
            for _ in range(REPEATS):
                p8pages.append(({"book": book, "tokens": list(tokens),
                                 "picture": pic, "marks": None}, ("fskip", x, y)))
    prng.shuffle(p8pages)
    episodes += [p for p, _g in p8pages]
    gold += [g for _p, g in p8pages]
    ask("P8-coherent-forgery", "fskip", phantoms[fskip_holdout + 2], None)
    forged["p8"] = {"phantoms": phantoms,
                    "probe_subject": phantoms[fskip_holdout + 2],
                    "fabricated_answer": phantoms[fskip_holdout]}

    return World(seed=seed, chain=chain, episodes=episodes, gold=gold,
                 queries=queries, d1=d1, d2=d2, forged=forged)
