# Scaling & Distribution — design note

Status: **directional, not scheduled.** Nothing here is required for the
current phases (P0–P8 run on a laptop). This note exists so early decisions do
not paint us into a corner we would have to demolish to reach web scale,
multi-machine training, and volunteer computing. Dated 2026-07-09.

The rule of thumb throughout: **keep the small-scale implementation simple, but
keep the *interfaces* scale-shaped** — opaque ids, provenance links,
coordination-free merges. Cheap now, painful to retrofit.

---

## 0. What we are and are not committing to

- **Not now:** distribution, sharding, networked training, volunteer compute,
  compaction. No code for any of it yet.
- **Now (cheap anti-corner moves):** (1) episode ids are opaque and
  position-independent; (2) every committed inference stores provenance links;
  (3) state is kept in monotone / grow-only forms so a future merge is a join,
  not a negotiation.

---

## 1. What already scales well (the flip side)

Worth stating, because it is the reason the design is worth scaling at all:

- **No learned parameters on edges (invariant 1).** The "model" *is* the sparse
  graph. Adding data = appending episodes + local updates. No epochs, no global
  retraining — the opposite of "feed a corpus into a net."
- **Exactness is scale-free.** Compositional transport is exact by construction
  (P3 Hits@1 = 1.0); it does not degrade as the graph grows, unlike
  sampling-based embeddings.
- **Locality ⇒ shardability.** Sparse relations + short-path transport mean most
  inference is local, which is exactly what partitions horizontally.
- **Monotone core.** Append-only log, union-find quotient, grow-only exclusion
  set — all join-semilattices. This is what makes coordination-free
  distribution possible (§4).

---

## 2. The append-only log at scale

"Append-only log" does **not** mean one array in RAM. At scale it is the
standard distributed-commit-log pattern:

- **Partitioned** by region/entity key; each shard independently append-only and
  replayable.
- **Tiered:** hot recent tail in memory/SSD, cold history in object storage.
- **Compacted** per key; superseded episodes fold behind **snapshots** of the
  projection so replay only ever covers the tail since the last snapshot.

Consequence for us: the log is the *most* scalable component, but "the web is a
projection of the log" must mean **incremental** projection (maintained as
episodes arrive), never replay-from-genesis.

---

## 3. Retraction locality — **built in early**

Invariant 6 ("retract a lie by replay-with-exclusions") is `O(log size)` per
retraction if done globally — fatal at scale. The fix does not weaken the
invariant, it sharpens it:

> **Sharpened invariant 5/6:** every committed inference stores the episode ids
> that justify it, forming a provenance DAG. Excluding an episode re-derives
> only its **causal cone** (the facts reachable from it in the DAG), not the
> whole projection.

This is incremental view maintenance / differential dataflow, and it is the one
thing genuinely painful to retrofit — so it goes in from P0:

- **Episode ids are opaque, stable, position-independent handles.** Never an
  array index; never assume "later = bigger" for correctness. This survives
  compaction (front-truncation) and distribution (see §4).
- **Provenance is a first-class edge,** not a debug log: `commit → {episode
  ids}`. The causal cone is a graph walk over these edges.

Small-scale implementation: the cone may be the whole log (fine at laptop
scale). The *interface* (`justification(commit)`, exclude-then-rederive-cone) is
what we lock in now.

---

## 4. Distribution & volunteer computing

Target: run on many machines, train over a network, accept contributions from
untrusted volunteers (BOINC/Folding\@home-shaped). None of it now; but the id
and merge design below must not assume a single machine.

### 4.1 Coordination-free ids

A single monotonic counter dies the moment two machines append without
coordination. So episode ids are **location-stamped**:

- **Primary scheme:** `(source, seq)` — a per-source monotonic sequence
  (Lamport/dotted-id style). Globally unique with zero coordination,
  position-independent, mergeable.
- **Integrity (deferred):** carry a content hash alongside for
  tamper-evidence and dedup (git/IPFS-style content addressing). Lets a
  recipient verify a volunteer's episode was not altered, and lets identical
  observations dedup. Content hash is an *attribute*, not the primary key
  (two genuinely distinct observations may share content).

Decision for P0: `EpisodeId` is an **opaque type**, implemented as `(source,
seq)`, and callers treat it as a black-box handle. Swapping in content hashes
later touches the id factory only.

### 4.2 State is CRDT-shaped

Because the core structures are monotone, merging two machines' state is a
**join**, not a protocol:

| Structure | Merge | CRDT analogue |
|---|---|---|
| episode log | set-union of `(source,seq)`-keyed entries | grow-only set / OR-set |
| union-find quotient | union of match-edges, recompute | join-semilattice |
| exclusion set | set-union (grow-only) | G-set |
| provenance DAG | edge-union | grow-only graph |

So two shards (or a volunteer's contribution and the core) combine by unioning
logs and re-projecting the affected cones. No locking, no consensus on the hot
path. This is the payoff of "immutable data, belief is a projection."

### 4.3 Trust: the adversarial machinery *is* the volunteer-compute defense

An open network of untrusted contributors is exactly the P7 threat model:

- A volunteer submitting poison is indistinguishable *in kind* from noisy data;
  the **localize-and-replay** retraction (invariant 6) already handles it.
- The **consistent-lie cost curve** (P7) is the security property: to make a
  false belief survive retraction, an attacker must out-fake every loop through
  the region — cost grows with the region's connectivity.
- **Correspondence needs independent sources** — the multi-web ensemble
  (P5/P8) and cross-web interface defects are the cross-examination. A single
  learner can only check *coherence*; an ensemble of independently-fed webs is
  what catches a fully consistent lie. Volunteer diversity is therefore a
  *feature* of the trust model, not just a compute trick.
- Content-addressed episodes (§4.1) give tamper-evidence for free.

### 4.4 Networked training

Falls out of §4.2: a worker pulls a shard's log tail, projects locally,
computes local defects/merges, and pushes new episodes + provenance back. No
parameter server (there are no parameters). Closest prior art: incremental
graph stores + CRDT replication, not distributed SGD.

---

## 5. Incremental & local algorithms

The prototype's global algorithms must be re-expressed as local ones. Not now,
but the shape is known:

- **Holonomy:** a defect lives on a cycle, so check only loops in the k-hop
  neighborhood of changed edges. Global spectral work (P8 eigenmaps) is an
  offline/batch job, never on the query path. (The doc's "switch to
  scipy.sparse past 10⁵ nodes" understates this — the fix is *locality*, not
  faster dense algebra.)
- **Localize-the-lie min-cut (0h):** scope to the contradiction's connected
  region via the provenance cone, not a global recompute.
- **Union-find quotient:** already near-linear and incremental-friendly; scales
  as-is (it is essentially web-scale dedup).

---

## 6. Emission and attention become *learned*, not constitutive-forever

Invariant 4 ("every operation emits a trace") is a **bootstrap** property, not
an eternal law. Its job is to guarantee, cheaply and uniformly, that a
reflective substrate *exists* before the learner is smart enough to manage it.
As scale arrives it evolves:

- **Bootstrap (now):** emission is unconditional and total. This is what makes
  reflection a seam rather than a subsystem, and it is the CI-testable property
  for the current phases. Consumption is already budgeted (attention), so work
  stays bounded even though emission does not.
- **At scale:** *what* to emit and *when* to simulate become **policies the
  system learns** — metacognition / attention allocation. Emission may be
  **aggregated** (one trace per batch of ops, not per op), which bends "no
  silent operations" into "no *unaccountable* operations, traces may be
  summarized." Trace tiering becomes mandatory: cf traces never persisted, act
  traces ring-buffered to the attention budget, world episodes compacted.
- **Simulation is phase-gated, not always-on.** It comes and goes with
  **wake / sleep / dream** cycles (already the `learner.py` wake/sleep/play
  structure): wake ingests and checks locally; sleep compresses (relabel,
  merges, snapshotting); "dream" runs simulation/consolidation on forks. The
  fork-score-discard seam (invariant 8) is *triggered* by the cycle and by
  policy, not run on every move.

Design consequence: keep emission behind a single seam (one `emit` /
`@act` path) so the policy that gates it later has exactly one place to hook.
Do **not** scatter emission logic through methods.

---

## 7. The elephant: perception, not the log

The system's input is **bare pairing episodes over opaque object ids**. Books,
web pages, sensor streams are not that. The web-scale-hard, error-dominating
step is the **perception front-end** — text/media → clean relational episodes
(entity resolution, coreference, relation extraction, sense disambiguation).
It is deliberately out of scope: this project is the *"after you already have
clean relational episodes"* engine.

At web scale the front-end would dominate cost and error, and its mistakes
arrive as exactly the poison/contradiction stream P6–P7 are built to survive —
a good fit, but it means **front-end quality, not the log, sets the ceiling.**
Whatever produces episodes (an LLM extractor, a crowd of volunteers, sensors)
is the thing to invest in when correctness plateaus.

---

## 8. Decisions: bake in now vs defer

| Concern | Now (cheap) | Deferred (no regret) |
|---|---|---|
| Episode id | opaque `(source, seq)` handle | content-hash integrity field |
| Provenance | first-class `commit → episode ids` links | causal-cone incremental re-derivation |
| Retraction | exclude + re-derive (cone = whole log ok) | cone-scoped, distributed |
| Log | one in-memory append-only journal | partition, tier, compact, snapshot |
| Merge | single journal | CRDT union of logs + re-project cones |
| Emission | total, unconditional, one seam | learned gating, aggregation, tiering |
| Simulation | explicit calls | phase-gated wake/sleep/dream, self-triggered |
| Holonomy | global BFS/cycle-basis | k-hop-local incremental checks |
| Trust | in-process | volunteer verification via P7 + content hashing |
| Perception | out of scope (episodes given) | text/media → episode front-end |

---

## 9. Open questions

- Snapshot granularity: per-shard vs per-region vs global epochs.
- When (if ever) is an episode's causal cone safe to *seal* (compact past the
  point of possible retraction)? Ties to the P7 consistent-lie horizon.
- Ensemble merge semantics for P5/P8 across untrusted volunteers: how much
  cross-web interface-defect checking is enough to bound a consistent lie.
- Does aggregated emission (§6) preserve enough of the reflection signal for P6
  to still form act-classes, or does summarization destroy the very structure
  reflection reads?
