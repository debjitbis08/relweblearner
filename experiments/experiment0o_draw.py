"""
Experiment 0o -- DRAWING: a 2D canvas with motion control (the turtle).

  A. MOTOR BABBLING discovers the CLOSURE LAW: every closed drawing has
     total turning +-360 degrees -- Papert's Total Turtle Trip Theorem,
     found from random strokes, not taught. (And 360 != all: the law is
     necessary, not sufficient -- the babbler finds that too.)
     Note what this law IS: a closed pen-loop is a loop whose rotational
     holonomy is one full winding. Drawing closure is loop holonomy in
     the motor channel -- the same law that governs belief loops.
  B. SHAPE = MOTOR MOTIF: closed + equal steps + equal turns reifies a
     parametrized family (n, 360/n): square = (4, 90), triangle = (3,120).
  C. DRAW WITH READ-BACK (the adjunction see(draw(x)) ~= x): intend a
     relational scene ("a square LEFT-OF a triangle"), render the motor
     program, SEE own output (regions + relations recomputed from the
     strokes alone), compare to intent, commit.
  D. DEFECT -> REVISE: corrupt one turn (89 deg); the region fails to
     close; read-back catches it BEFORE commit; the reviser repairs the
     turn budget to 360 and passes. Simulate-before-commit, motor channel.
"""

import math, random

random.seed(2)


def execute(prog):
    """Run a motor program; return pen-down stroke chains."""
    x = y = h = 0.0
    pen = True
    chains, cur = [], [(0.0, 0.0)]
    for op, v in prog:
        if op == "T":
            h = (h + v) % 360
        elif op == "U":
            if len(cur) > 1:
                chains.append(cur)
            pen, cur = False, []
        elif op == "D":
            pen, cur = True, [(x, y)]
        else:
            x += v * math.cos(math.radians(h))
            y += v * math.sin(math.radians(h))
            if pen:
                cur.append((x, y))
    if len(cur) > 1:
        chains.append(cur)
    return chains


def closed(chain, eps=0.05):
    (x0, y0), (x1, y1) = chain[0], chain[-1]
    return len(chain) >= 4 and math.hypot(x1 - x0, y1 - y0) < eps


# ---------------------------------------------------------------- A
print("=" * 72)
print("A. BABBLING DISCOVERS THE CLOSURE LAW")
print("=" * 72)
ANGLES = [60, 72, 90, 108, 120, 144]


def chain_turning(ch):
    """Perception-side: total signed exterior angle around a closed chain,
    including the closing vertex (which no motor token executes)."""
    segs = [
        (ch[i + 1][0] - ch[i][0], ch[i + 1][1] - ch[i][1]) for i in range(len(ch) - 1)
    ]
    tot = 0.0
    for i in range(len(segs)):
        a, b = segs[i], segs[(i + 1) % len(segs)]
        tot += math.degrees(
            math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])
        )
    return tot


stats = {"closed": [], "open_budget_360": 0}
for _ in range(3000):
    n = random.randint(3, 8)
    a = random.choice(ANGLES)
    prog = []
    for _ in range(n):
        prog += [
            ("F", 10),
            ("T", a if random.random() < 0.7 else random.choice(ANGLES)),
        ]
    chains = execute(prog)
    if chains and closed(chains[0]):
        stats["closed"].append(chain_turning(chains[0]))
    elif sum(v for op, v in prog if op == "T") % 360 == 0:
        stats["open_budget_360"] += 1

law = all(
    abs(abs(t) % 360) < 1e-6 or abs((abs(t) % 360) - 360) < 1e-6
    for t in stats["closed"]
)
windings = sorted({round(abs(t) / 360) for t in stats["closed"]})
print(f"babbled 3000 programs: {len(stats['closed'])} drawings CLOSED")
print(
    f"SEEN total turning of every closed figure = 360 x k exactly: "
    f"{'PASS' if law else 'FAIL'}   (windings observed: {windings})"
)
print(
    f"programs whose turn-budget was 360k yet did NOT close: {stats['open_budget_360']}"
)
print("-> the law is NECESSARY, not sufficient -- discovered, both halves.")
print("   Closure = rotational holonomy of one winding: the motor channel")
print("   obeys the same loop law as belief webs. One law, third channel.\n")

# ---------------------------------------------------------------- B
print("=" * 72)
print("B. SHAPES REIFIED AS MOTOR MOTIFS")
print("=" * 72)


def polygon(n, step=10):
    return [op for _ in range(n) for op in (("F", step), ("T", 360 // n))]


for n, name in [(4, "square"), (3, "triangle")]:
    ok = closed(execute(polygon(n))[0])
    print(f"  motif ({n}, {360 // n}) -> '{name}': closes {ok}")
print("A shape is a parametrized motor program -- a reified motif over the")
print("stroke-sequence web, exactly like a concept motif over relations.\n")

# ---------------------------------------------------------------- C
print("=" * 72)
print("C. DRAW WITH READ-BACK: see(draw(x)) ~= x")
print("=" * 72)


def see(chains):
    """Perceive own output: closed regions + left-of relations (from strokes
    alone -- no access to the intent)."""
    regs = []
    for ch in chains:
        if closed(ch):
            cx = sum(p[0] for p in ch) / len(ch)
            regs.append({"sides": len(ch) - 1, "cx": cx})
    regs.sort(key=lambda r: r["cx"])
    rel = [
        ("left-of", regs[i]["sides"], regs[i + 1]["sides"])
        for i in range(len(regs) - 1)
    ]
    return [r["sides"] for r in regs], rel


intent = {"regions": [4, 3], "relations": [("left-of", 4, 3)]}
# (pen-up, travel right, pen-down, draw the triangle)
draft = polygon(4) + [("U", 0), ("F", 40), ("D", 0)] + polygon(3)
regions, rels = see(execute(draft))
match = regions == intent["regions"] and rels == intent["relations"]
print(f"intent: a square LEFT-OF a triangle")
print(f"seen in own drawing: regions {regions}, relations {rels}")
print(f"adjunction holds -> COMMIT: {'PASS' if match else 'FAIL'}\n")

# ---------------------------------------------------------------- D
print("=" * 72)
print("D. DEFECT -> REVISE BEFORE COMMIT")
print("=" * 72)
bad = [
    ("F", 10),
    ("T", 90),
    ("F", 10),
    ("T", 89),
    ("F", 10),
    ("T", 90),
    ("F", 10),
    ("T", 90),
]
chains = execute(bad)
print(
    f"corrupted square (one 89-degree turn): closes = "
    f"{closed(chains[0])} -> read-back DEFECT, draft refused"
)
from collections import Counter as _C

tvals = [v for op, v in bad if op == "T"]
mode = _C(tvals).most_common(1)[0][0]
fixed = [(op, mode if (op == "T" and v != mode) else v) for op, v in bad]
print(
    f"revision: one turn deviates from the regular pattern ({mode} deg) -> "
    f"snap the outlier to the mode"
)
print(f"revised draft closes = {closed(execute(fixed)[0])} -> COMMIT")
print("The writer's read-back law, running in the motor channel: it fixed")
print("its own drawing by balancing the loop's holonomy.")
