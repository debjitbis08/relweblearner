"""
Experiment 0k -- can it INVENT, or only retrieve?

Two signatures that separate invention from search, both testable:

  1. POSIT-BEFORE-EVIDENCE (the neutrino pattern): a conservation-style
     motif is banked from experience; an episode then violates it; the
     only discharge is to posit an UNSEEN entity with derived properties.
     The posit is timestamped BEFORE the confirming observation. A
     retrieval system, asked the same question at the same time, has
     nothing to return.

  2. EMERGENT PREDICTION FROM A BLEND: glue two webs (linear hour-chain
     learned by counting + a wrap observation from day boundaries). The
     blend answers 11+3 = 2 -- a fact never observed, FALSE in the chain
     parent (which says 14), and inexpressible in the wrap parent (which
     has no addition). Bonus: the blend carries a persistent nonzero
     holonomy (winding +12) that contradicts NO observation -- a defect
     reclassified as CONTENT. The invented object (clock arithmetic) IS
     a stabilized harmonic class.
"""

# ---------------------------------------------------------------- Part 1
print("=" * 72)
print("1. POSIT-BEFORE-EVIDENCE (inventing an unseen entity)")
print("=" * 72)

log = []  # timestamped episodes
t = 0


def obs(kind, payload):
    global t
    t += 1
    log.append((t, kind, payload))
    return t


# phase A: complete split episodes -> the conservation motif is banked
for src, dests in [
    ({"a1", "a2", "a3"}, [{"a1"}, {"a2", "a3"}]),
    ({"b1", "b2", "b3", "b4"}, [{"b1", "b2"}, {"b3", "b4"}]),
    ({"c1", "c2"}, [{"c1"}, {"c2"}]),
]:
    obs("split", (src, dests))
covered = all(s == set().union(*d) for _, _, (s, d) in log)
print(
    f"banked motif from {len(log)} complete splits: "
    f"'a split saturates its source' (holds in all observed: {covered})"
)

# phase B: an incomplete split -- o5's destination is never observed
src = {"o1", "o2", "o3", "o4", "o5"}
seen_dests = [{"o1", "o2"}, {"o3", "o4"}]
t_defect = obs("split", (src, seen_dests))
missing = src - set().union(*seen_dests)
print(
    f"\nepisode at t={t_defect}: split of 5 accounts for only 4 -> defect"
    f" against the banked motif"
)

# discharge: GROW an unseen container holding exactly the missing members
posit = {"id": "H*", "members": missing, "posited_at": obs("posit", missing)}
print(
    f"POSIT at t={posit['posited_at']}: unseen container H* with members "
    f"{sorted(posit['members'])} -- derived, not observed"
)

# a retrieval baseline, asked NOW: where is o5?
recall = [e for e in log if e[1] == "split" and "o5" in set().union(*e[2][1])]
print(
    f"retrieval baseline asked 'where is o5?' now: "
    f"{'no record -> unknown' if not recall else recall}"
)

# phase C: the world later reveals the hidden container
t_reveal = obs("observe", {"container": "D7", "members": {"o5"}})
confirmed = log[-1][2]["members"] == posit["members"]
print(
    f"\nREVEAL at t={t_reveal}: container observed with members "
    f"{sorted(log[-1][2]['members'])}"
)
print(
    f"posit preceded evidence: {posit['posited_at']} < {t_reveal} -> "
    f"{'PASS' if posit['posited_at'] < t_reveal and confirmed else 'FAIL'}"
    f"  (content confirmed: {confirmed})"
)
print("The entity was constructed from a closure requirement, not retrieved.")
print("Pauli's neutrino, at toy scale: invented to balance a loop, seen later.\n")

# ---------------------------------------------------------------- Part 2
print("=" * 72)
print("2. EMERGENT PREDICTION FROM A BLEND (clock arithmetic)")
print("=" * 72)

# parent 1: the hour chain, learned by counting (P1b machinery)
succ = {f"h{i}": (f"h{i + 1}", +1) for i in range(11)}
# parent 2: wrap observations from day boundaries ("after 11 comes 0")
wrap_obs = [("h11", "h0", +1)]
episodes = [(u, v) for u, (v, _) in succ.items()] + [(u, v) for u, v, _ in wrap_obs]

# the blend: union over the shared nodes (a pushout along h0..h11)
blend = dict(succ)
blend["h11"] = ("h0", +1)


def walk(g, start, k):
    cur = start
    for _ in range(k):
        if cur not in g:
            return None
        cur = g[cur][0]
    return cur


chain_answer = walk(succ, "h11", 3)  # falls off; would need growth
blend_answer = walk(blend, "h11", 3)
print(f"query 11+3:  chain parent -> {chain_answer} (walks off; growth would say h14)")
print(f"             wrap parent  -> no addition exists in it at all")
print(
    f"             BLEND        -> {blend_answer}   ground truth (11+3)%12 "
    f"= 2: {'PASS' if blend_answer == 'h2' else 'FAIL'}"
)
print("A correct prediction licensed by NEITHER parent: emergent structure.")

# the deep part: the blend's 12-loop has nonzero holonomy...
winding = sum(g for (_, g) in blend.values())
# ...yet contradicts no observation:
violated = [e for e in episodes if walk(blend, e[0], 1) != e[1]]
print(f"\nblend loop holonomy = +{winding} (nonzero, PERSISTENT)")
print(f"observations contradicted by the blend: {violated}  (none)")
print("Criterion: a persistent class WITH observation conflicts is an error")
print("(retract, P7); a persistent class WITHOUT conflicts is CONTENT --")
print("bank it. Clock arithmetic IS this stabilized winding; the invented")
print("object is a defect the system learned to keep.")
