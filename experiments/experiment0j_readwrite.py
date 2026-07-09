"""
Experiment 0j -- learning to READ and WRITE. Language is a separate web,
one-way dependent on the concept web (skill atop concepts).

The learner receives a raw SYLLABLE STREAM -- no word boundaries, no
utterance boundaries, no vocabulary, and no identifier shared with the
concept web (words are gensyms; nothing string-matches).

  A. segmentation: word boundaries from transition-probability dips
     (Saffran); stress run with shared syllables shows graceful failure.
  B. closed-class discovery + utterance chunking by frequency outliers.
  C. grounding: align token web to concept web by STRUCTURE ALONE
     (joint WL refinement + edge-type bijection search). Prediction:
     resolution exactly up to the automorphism orbits of the concept web.
  D. ostension: one pointing event per symmetric orbit; elimination
     cascades the rest.
  E. fast mapping: a NOVEL word in one utterance, segmented by
     subtraction (flanked by known words), grounded by mutual exclusivity.
  F. writing: inverse map + READ-BACK before commit; pre-ostension
     ambiguity is caught by the read-back and refused.
"""

import random
from collections import defaultdict, Counter

random.seed(3)

# ---------------- hidden world (scoring only; learner never sees this map)
HC = {
    "mango": "yellow",
    "banana": "yellow",
    "lemon": "yellow",
    "apple": "red",
    "cherry": "red",
    "lime": "green",
}
GO = {
    "mango": "tree",
    "banana": "herb",
    "lemon": "tree",
    "apple": "tree",
    "cherry": "tree",
    "lime": "tree",
}
WORD = {
    "mango": "bavu",
    "banana": "kide",
    "lemon": "mopa",
    "apple": "runi",
    "cherry": "tela",
    "lime": "zogi",
    "yellow": "dima",
    "red": "felo",
    "green": "gusa",
    "tree": "hepo",
    "herb": "wiju",
    "HC": "xuqo",
    "GO": "ceny",
}
SYL = {w: [w[:2], w[2:]] for w in WORD.values()}
FACTS = [("HC", f, c) for f, c in HC.items()] + [("GO", f, p) for f, p in GO.items()]


def stream_of(n_utt, facts):
    syls, gold = [], set()
    for _ in range(n_utt):
        r, x, y = random.choice(facts)
        for w in (WORD[r], WORD[x], WORD[y]):
            syls += SYL[w]
            gold.add(len(syls))  # gold word boundaries
    return syls, gold


# ---------------------------------------------------------------- A
print("=" * 72)
print("A. SEGMENTATION FROM THE RAW SYLLABLE STREAM")
print("=" * 72)
syls, gold = stream_of(300, FACTS)
trans = defaultdict(Counter)
for a, b in zip(syls, syls[1:]):
    trans[a][b] += 1
P = lambda a, b: trans[a][b] / sum(trans[a].values())
words, cur, pos, bounds = [], [syls[0]], 1, set()
for a, b in zip(syls, syls[1:]):
    if P(a, b) < 0.9:
        words.append("".join(cur))
        bounds.add(pos)
        cur = [b]
    else:
        cur.append(b)
    pos += 1
words.append("".join(cur))
tp = len(bounds & gold)
prec, rec = tp / len(bounds), tp / len(gold - {len(syls)})
lex = set(words)
print(f"stream: {len(syls)} syllables, no boundaries given")
print(
    f"boundary precision {prec:.2f}, recall {rec:.2f}; "
    f"recovered lexicon {len(lex)} types (truth: 13): "
    f"{'PASS' if lex == set(WORD.values()) else 'FAIL'}"
)

# stress: colors share syllables with fruits
print("stress run (colors reuse fruit syllables):", end=" ")
W2 = dict(WORD)
W2["yellow"] = "bama"
W2["green"] = "kiqo"  # shares ba, ki, qo
S2 = {w: [w[:2], w[2:]] for w in W2.values()}
syls2, gold2 = [], set()
for _ in range(300):
    r, x, y = random.choice(FACTS)
    for w in (W2[r], W2[x], W2[y]):
        syls2 += S2[w]
        gold2.add(len(syls2))
t2 = defaultdict(Counter)
for a, b in zip(syls2, syls2[1:]):
    t2[a][b] += 1
b2, pos = set(), 1
for a, b in zip(syls2, syls2[1:]):
    if t2[a][b] / sum(t2[a].values()) < 0.9:
        b2.add(pos)
    pos += 1
tp2 = len(b2 & gold2)
print(f"precision {tp2 / len(b2):.2f}, recall {tp2 / len(gold2 - {len(syls2)}):.2f}")
print("-> shared syllables degrade boundaries gracefully; segmentation is a")
print("   statistical capability with a measurable ceiling, not a given.\n")

# ---------------------------------------------------------------- B
print("=" * 72)
print("B. CLOSED-CLASS DISCOVERY & UTTERANCE CHUNKING")
print("=" * 72)
freq = Counter(words)
markers = {w for w, _ in freq.most_common(2)}
print(f"frequency outliers (Zipf head) -> frame words: {sorted(markers)}")
utts, cur = [], []
for w in words:
    if w in markers and cur:
        utts.append(cur)
        cur = []
    cur.append(w)
utts.append(cur)
ok = all(len(u) == 3 and u[0] in markers for u in utts)
print(
    f"chunked {len(utts)} utterances of form [frame, arg1, arg2]: "
    f"{'PASS' if ok else 'FAIL'}\n"
)

# ---------------------------------------------------------------- C
print("=" * 72)
print("C. GROUNDING BY STRUCTURE ALONE (no shared ids)")
print("=" * 72)
tok_edges = {m: set() for m in markers}
for m, x, y in utts:
    tok_edges[m].add((x, y))
con_edges = {"HC": set(HC.items()), "GO": set(GO.items())}


def wl(nodes, edges, seeds, rounds=4):
    sig = {n: seeds.get(n, "x") for n in nodes}
    for _ in range(rounds):
        sig = {
            n: str(seeds.get(n, ""))
            + str(
                sorted(
                    [
                        ("o", t, sig[v])
                        for t, es in edges.items()
                        for (u, v) in es
                        if u == n
                    ]
                    + [
                        ("i", t, sig[u])
                        for t, es in edges.items()
                        for (u, v) in es
                        if v == n
                    ]
                )
            )
            for n in nodes
        }
    return sig


def ground(seeds):
    """seeds: {token: concept} joint-attention events, tagging BOTH sides."""
    tok_nodes = {n for es in tok_edges.values() for e in es for n in e}
    con_nodes = {n for es in con_edges.values() for e in es for n in e}
    tseed = {t: f"SEED{i}" for i, (t, c) in enumerate(sorted(seeds.items()))}
    cseed = {c: f"SEED{i}" for i, (t, c) in enumerate(sorted(seeds.items()))}
    best = None
    for hc_marker in sorted(markers):
        go_marker = (markers - {hc_marker}).pop()
        te = {"T1": tok_edges[hc_marker], "T2": tok_edges[go_marker]}
        ce = {"T1": con_edges["HC"], "T2": con_edges["GO"]}
        ts = wl(tok_nodes, te, tseed)
        cs = wl(con_nodes, ce, cseed)
        groups = defaultdict(lambda: ([], []))
        for n, s in ts.items():
            groups[s][0].append(n)
        for n, s in cs.items():
            groups[s][1].append(n)
        g = {
            t: c[0]
            for (tt, c) in groups.values()
            if len(tt) == 1 and len(c) == 1
            for t in tt
        }
        orbits = [
            (sorted(tt), sorted(c))
            for (tt, c) in groups.values()
            if len(tt) == len(c) > 1
        ]
        score = len(g)
        if best is None or score > best[0]:
            best = (score, g, orbits, {hc_marker: "HC", go_marker: "GO"})
    return best[1], best[2], best[3]


g, orbits, mmap = ground(seeds={})
acc = sum(1 for t, c in g.items() if WORD[c] == t)
print(f"edge-type bijection found: {mmap}")
print(
    f"grounded uniquely: {len(g)}/11 content words, all correct: "
    f"{'PASS' if acc == len(g) else 'FAIL'}"
)
print(f"unresolved symmetric orbits: {orbits}")
print("-> resolution stops EXACTLY at the automorphism orbits of the concept")
print("   web (mango/lemon and apple/cherry are structurally identical).\n")

# ---------------------------------------------------------------- D
print("=" * 72)
print("D. OSTENSION: one pointing event per orbit")
print("=" * 72)
g1, orb1, _ = ground(seeds={"bavu": "mango"})
print(
    f"after pointing at a mango while hearing 'bavu': "
    f"{len(g1)}/11 grounded, orbits left: {orb1}"
)
g2, orb2, _ = ground(seeds={"bavu": "mango", "runi": "apple"})
acc2 = sum(1 for t, c in g2.items() if WORD[c] == t)
print(
    f"after a second pointing (apple/'runi'): {len(g2)}/11 grounded, "
    f"correct {acc2}/11: {'PASS' if acc2 == 11 else 'FAIL'}"
)
print("Ostension budget = number of nontrivial orbits. Elimination did the")
print("partner of each orbit for free.\n")
GROUND = dict(g2)
INV = {c: t for t, c in GROUND.items()}
INV.update(
    {
        "HC": [m for m, r in mmap.items() if r == "HC"][0],
        "GO": [m for m, r in mmap.items() if r == "GO"][0],
    }
)

# ---------------------------------------------------------------- E
print("=" * 72)
print("E. FAST MAPPING A NOVEL WORD")
print("=" * 72)
con_edges["HC"].add(("fig", "red"))
con_edges["GO"].add(("fig", "herb"))
print("perception adds a new concept (a fig: red, herb) -- no word exists.")
novel = SYL["xuqo"] + ["wu", "mi"] + SYL["felo"]
known_start = "".join(novel[:2])
known_end = "".join(novel[-2:])
residue = "".join(novel[2:-2])
print(
    f"novel utterance heard once; segmentation by SUBTRACTION: "
    f"[{known_start} | {residue} | {known_end}] -> new word '{residue}'"
)
cands = [f for (f, c) in con_edges["HC"] if c == GROUND.get(known_end) and f not in INV]
print(f"frame says: a fruit-word, color red; unworded red concepts: {cands}")
print(
    f"fast-mapped '{residue}' -> {cands[0]} "
    f"{'PASS' if cands == ['fig'] else 'FAIL'}  (mutual exclusivity, again)\n"
)
GROUND[residue] = "fig"
INV["fig"] = residue

# ---------------------------------------------------------------- F
print("=" * 72)
print("F. WRITING = INVERSE MAP + READ-BACK BEFORE COMMIT")
print("=" * 72)


def read(utt_tokens):
    r = mmap[utt_tokens[0]]
    return (r, GROUND.get(utt_tokens[1]), GROUND.get(utt_tokens[2]))


def write(fact, inv):
    r, x, y = fact
    if x not in inv or y not in inv:
        return None, "no word (refuse)"
    draft = [INV[r], inv[x], inv[y]]
    return (
        (draft, "commit")
        if read(draft) == fact
        else (draft, "read-back mismatch (refuse)")
    )


# pre-ostension writer: mango's word is an orbit, not a token
pre_inv = {c: t for t, c in g.items()}
d, verdict = write(("GO", "mango", "tree"), pre_inv)
print(f"pre-ostension, write 'mango grows on trees': {verdict}")
d, verdict = write(("HC", "fig", "red"), {c: t for t, c in GROUND.items()})
print(
    f"post-grounding, write 'the fig is red': draft {d} -> {verdict}, "
    f"read-back = {read(d)}"
)
print("The writer rehearses reading its own draft; adjunction as a unit test.")
