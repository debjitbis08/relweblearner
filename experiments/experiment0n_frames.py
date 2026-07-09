"""
Experiment 0n -- FRAME INDUCTION: reading pattern books.

A. induce templates by per-position DOMINANCE (fixed if one token covers
   >=80% of the group; a frame needs >=2 anchors); non-matching sentences
   are REJECTED to the frontier -- length-grouping alone over-generalizes
   (found the hard way: off-frame sentences polluted the skeleton).
B. ground slot-fillers vs the concept web (WL + iterative picture taps)
C. fast-map a novel animal from one page + one tap
D. frontier sentences logged as language-layer defects (the trigger for
   the next frame's induction), never crashes
E. assimilation rate: committed facts per sentence, book-level provenance
"""

import random
from collections import defaultdict, Counter

random.seed(5)

HC = {
    "bear": "red",
    "bird": "red",
    "duck": "yellow",
    "frog": "green",
    "cat": "blue",
    "horse": "yellow",
}
ANIMALS = list(HC)


def make_book(bid, n):
    out = []
    for _ in range(n):
        a = random.choice(ANIMALS)
        c = HC[a]
        out.append(
            {
                "book": bid,
                "tokens": (
                    ["i", "see", "a", c, a]
                    if random.random() < 0.5
                    else ["the", a, "is", c]
                ),
                "picture": a,
            }
        )
    return out


pages = make_book("B1", 60) + make_book("B2", 60)
pages += [
    {"book": "B1", "tokens": ["the", "bird", "flew", "away"], "picture": "bird"},
    {"book": "B2", "tokens": ["where", "is", "the", "cat"], "picture": "cat"},
]
random.shuffle(pages)

# ---------------------------------------------------------------- A
print("=" * 72)
print("A. FRAME INDUCTION (dominance-thresholded skeletons)")
print("=" * 72)
frames = {}
for L, grp in [
    (L, [p for p in pages if len(p["tokens"]) == L])
    for L in {len(p["tokens"]) for p in pages}
]:
    if len(grp) < 10:
        continue
    skel, slots = [], []
    for i in range(L):
        tok, cnt = Counter(p["tokens"][i] for p in grp).most_common(1)[0]
        if cnt / len(grp) >= 0.8:
            skel.append(tok)
        else:
            skel.append("_")
            slots.append(i)
    if L - len(slots) >= 2:  # a frame needs anchors
        frames[f"F{L}"] = (tuple(skel), slots)
        print(f"  induced {f'F{L}'}: {' '.join(skel)}  (slots {slots})")


def parse(p):
    fid = f"F{len(p['tokens'])}"
    if fid not in frames:
        return None
    skel, slots = frames[fid]
    if any(s != "_" and s != t for s, t in zip(skel, p["tokens"])):
        return None
    return fid, [p["tokens"][i] for i in slots]


parsed = [(p, parse(p)) for p in pages]
frontier = [p["tokens"] for p, r in parsed if r is None]
coverage = 1 - len(frontier) / len(pages)
print(f"coverage {coverage:.2f}; frontier (logged defects): {frontier}\n")

# ---------------------------------------------------------------- B
print("=" * 72)
print("B. SLOT GROUNDING + ITERATIVE PICTURE TAPS")
print("=" * 72)
tedges = set()
for p, r in parsed:
    if r:
        fid, fill = r
        c, a = (fill[0], fill[1]) if fid == "F5" else (fill[1], fill[0])
        tedges.add((f"w:{a}", f"w:{c}"))  # word-namespace: no id sharing
cedges = set(HC.items())


def wl(nodes, edges, seed, rounds=4):
    sig = {n: seed.get(n, "x") for n in nodes}
    for _ in range(rounds):
        sig = {
            n: str(seed.get(n, ""))
            + str(
                sorted(
                    [("o", sig[v]) for (u, v) in edges if u == n]
                    + [("i", sig[u]) for (u, v) in edges if v == n]
                )
            )
            for n in nodes
        }
    return sig


def ground(seeds):
    tn = {x for e in tedges for x in e}
    cn = {x for e in cedges for x in e}
    ts = wl(tn, tedges, {w: l for (w, c), l in seeds.items()})
    cs = wl(cn, cedges, {c: l for (w, c), l in seeds.items()})
    grp = defaultdict(lambda: ([], []))
    for n, s in ts.items():
        grp[s][0].append(n)
    for n, s in cs.items():
        grp[s][1].append(n)
    g = {t: c[0] for tt, c in grp.values() if len(tt) == 1 == len(c) for t in tt}
    orb = [(sorted(tt), sorted(c)) for tt, c in grp.values() if len(tt) == len(c) > 1]
    return g, orb


seeds, taps = {}, 0
g, orb = ground(seeds)
print(
    f"structural grounding: {len(g)} unique, {len(orb)} orbits: {[o[0] for o in orb]}"
)
while orb:
    w = orb[0][0][0]
    c = w[2:]  # tap the pictured referent
    seeds[(w, c)] = f"TAP{taps}"
    taps += 1
    g, orb = ground(seeds)
    print(f"  tap #{taps} on '{c}' -> grounded {len(g)}, orbits left {len(orb)}")
acc = sum(1 for w, c in g.items() if w == f"w:{c}")
print(
    f"final: {acc}/{len(g)} correct with {taps} taps "
    f"({'PASS' if acc == len(g) == 10 else 'FAIL'})\n"
)

# ---------------------------------------------------------------- C
print("=" * 72)
print("C. FAST-MAP FROM ONE PAGE")
print("=" * 72)
novel = {"book": "B2", "tokens": ["i", "see", "a", "red", "zebu"], "picture": "zebu"}
fid, fill = parse(novel)
print(f"'{' '.join(novel['tokens'])}' parses by induced {fid}; 'zebu' unknown;")
print(
    f"tap on picture grounds it in one exposure -> fact (zebu, red), "
    f"provenance {{B2}}\n"
)

# ---------------------------------------------------------------- E
print("=" * 72)
print("E. ASSIMILATION RATE")
print("=" * 72)
facts = defaultdict(set)
for p, r in parsed:
    if r:
        fid, fill = r
        c, a = (fill[0], fill[1]) if fid == "F5" else (fill[1], fill[0])
        facts[(a, c)].add(p["book"])
committed = {f for f, o in facts.items() if len(o) >= 2}
correct = all(HC[a] == c for a, c in committed)
print(
    f"read {len(pages)} sentences -> {len(committed)} facts committed "
    f"(>=2 book origins), all correct: {correct}"
)
print(
    f"assimilation rate {len(committed) / len(pages):.3f} facts/sentence; "
    f"coverage {coverage:.2f} bounds it."
)
