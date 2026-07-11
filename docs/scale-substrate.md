# The scale substrate — Creature, corpus firehose, bounded storage

The hand-training app (`docs/app-reading.md`) is an *action demo*: a human feeds
phrases one at a time and the whole model is re-derived from an append-only log on
every read. That is correct but does not scale — the log grows with everything
**read**, re-derivation is from-scratch, and there is no identity. This layer is
the scalable substrate for **larger-corpus experimentation**.

## The three problems, and the fixes

**1. Storing every episode won't scale — and what's stored is GEOMETRY.** The
project's thesis is *intelligence = fixed algebra + geometry*: the algebra
(composition, holonomy, the three costed moves) is frozen **in code**; the only
learned degree of freedom is the **web** — "a graph with fixed-algebra edge values"
(`web.py`). So the durable state of a creature is its geometry, never the algebra
and never the episode history:

- **concept web** — nodes (concepts) and typed, algebra-valued edges (facts):
  `src -[rel]-> tgt` with the frames that express it and its provenance/evidence;
- **language web** — the induced frames (constructions over the sequence web) and
  each frame's picture-slot orientation.

`Creature.geometry()` returns exactly this graph; `Creature.embedding()` recomputes
the **spatial** geometry (graph-Laplacian eigenmap coordinates per concept, via
`geometry.py`) from the stored web — geometry is the data, the algebra is the code.
`to_dict` serialises `identity + geometry` and explicitly marks the algebra as
"frozen in code (not stored)". A learner's memory thus grows with what it has
**learned** (which saturates on a fixed world), not with what it has read: episodes
stream through `observe()` in ~O(1) and are **not retained**; only a small rolling
induction `buffer` (default cap 500) is kept as a working reservoir.

**The invariant (stated carefully).** The geometry is NOT fixed-size. It grows
with what is *learned* — distinct concepts, edges, frames — and is **independent of
the episode count**: repetition is free, novelty costs. So on a *closed* world
learning saturates and the web plateaus, but on an *open* world (new animals,
relations, words; added webs) the web grows — 500 animals is 500 edges, a
Wikidata-scale world is millions. The genuine win over the append-only log is not
constancy but the *variable*: geometry is `O(distinct structure)` while the log is
`O(episodes read)`, and real reading is massively repetitive, so the web is far
smaller than the log — but unbounded as the world opens up.

Measured (`experiments/ec_scale.py`, one streaming pass over the **closed** 16-animal
generator world, so facts saturate — this shows episode-independence, NOT that the
model is constant in general):

| episodes | ingest | frames | facts | buffer | model file |
|---------:|-------:|-------:|------:|-------:|-----------:|
| 1,000    | 0.03s  | 4      | 48    | 35     | 15.6 KB |
| 20,000   | 0.37s  | 4      | 48    | 500    | 50.1 KB |
| 100,000  | 1.86s  | 4      | 48    | 500    | 50.3 KB |

Facts are flat because the world is closed; feed 500 distinct animals and the web
carries 500 edges regardless of episode count. Only the induction `buffer` (cap
500) and per-edge provenance (capped sources) are truly bounded. What this buys:
the append-only log of these 100k episodes would be megabytes and re-derived on
every read; the web is what was learned, not what was read.

**2. The training method won't scale.** A human is O(time) per episode.
`datasets/patternbooks.py` is the corpus firehose: a frame-graded,
controlled-vocabulary generator (spec §4's LLM-authored pattern books), seeded and
reproducible, emitting `{book, tokens, picture, marks}` episodes at any volume —
with gold breakups for adjacent-filler frames so no human marking is needed. The
human's role becomes curriculum design + frontier review, not data entry.

**3. No identity.** A `Creature` has a stable `id` and `name` (plus `created` /
`level`) — an addressable entity whose persistent, distilled model *is* its memory,
not an anonymous file at a path.

## The honest tradeoff

Bounded memory costs **retroactivity**. The append-only Reader re-parses all past
episodes when a frame is induced late; the streaming Creature applies a new frame
to the ongoing stream and to whatever is still in the bounded buffer, **not** to
episodes already distilled and dropped. At scale the stream dwarfs the buffer, so
missing a frame's first few hundred exposures is negligible — perfect retroactivity
is a small-corpus luxury traded for O(world) memory.

## Algorithmic scaling of induction

`curriculum.induce_frames` was O(D²) in the number of distinct signatures. It is
now near-linear: signatures are unioned via an inverted index over
`min_anchors`-sized anchor-column combinations (identical clusters, no all-pairs
scan). Two robustness fixes came with scale: a **relative** anchor threshold
(`max(min_group, ceil(anchor_frac·N))`) so a frequent *filler* on a big corpus is
not mistaken for an anchor (which, via the transitive merge, would collapse
distinct frames), and a **promotion** pass so a rare *frame-word* (`where` in
`where is the __`) that the relative threshold demotes is recovered when its column
is constant.

## Layers

- `datasets/patternbooks.py` — the generator + hidden world + `truth()`.
- `creature.py` — `Creature`: identity, bounded model, `observe`/`ingest`,
  `snapshot`, `save`/`load`, talk-back.
- `talk.py` — shared talk-back (`about`/`answer`/`say`/`render_fact`) over a common
  `state` view; the interactive `Reader` and the streaming `Creature` speak
  identically, and both type facts by relation so a question in one frame is
  answered only from that relation's facts.
- `experiments/ec_scale.py` — the scale soak.
- `tests/test_creature.py` — bounded-model, streaming, identity, persistence.

## Indexed store — the web past memory (`store.py`)

The concept web's nodes + edges are the one unbounded part of the geometry. When
they outgrow a JSON blob / RAM, they move behind an **`EdgeStore`** — queried by
NEIGHBOURHOOD, never loaded whole:

- **`InMemoryEdgeStore`** — dict backing (small / interactive; the `Creature`
  default, so existing behaviour is unchanged);
- **`SqliteEdgeStore`** — B-tree-indexed tables (`nodes`, `edges`, `edge_rel`,
  `edge_src`) on disk. `observe` upserts one edge incrementally; point and
  neighbourhood queries are indexed; the **database file *is* the persistence**
  (reopen without re-ingest, no full rewrite);
- **`ShardedEdgeStore`** — routes edges to N shard stores by source concept, so no
  single file/process holds the whole web. Forward queries (`out_edges`, `get`,
  `bump`) hit one shard; reverse queries (`in_edges`) fan out.

A `Creature` takes any of these via `store=`. Everything else it holds (frames,
frontier, the capped buffer) stays bounded in memory; only the edges are
externalised. Measured (`experiments/ec_store.py`, open world streamed to disk):

| animals | episodes | nodes | edges | db | ingest | point query |
|--------:|---------:|------:|------:|---:|-------:|------------:|
| 5,000   | 10,000   | 5,006 | 5,000 | 0.3 MB | 0.46s | 51 µs |
| 50,000  | 100,000  | 50,006 | 50,000 | 10 MB | 4.8s | 57 µs |
| 200,000 | 400,000  | 200,006 | 200,000 | 42 MB | 20s | 54 µs |

The web grows with the world (200k concepts → 200k edges, on disk), yet **point-query
latency stays flat** — `about`/`answer` cost `O(neighbourhood)`, not `O(web)`,
however large the geometry gets. Sharded across 6 files it splits evenly (~10k
edges each). JSON geometry migrates into a store via `EdgeStore.put`.

## Relation unification (`Creature.unify_relations`)

Different frames can express the SAME concept-web relation — `the X is Y` and
`i see a Y X` are both animal→colour. A relation's identity is the edge set it
induces, so two frames unify iff their **committed edge sets agree**. Unification
maintains a union-find over frames (their relation CLASS); it is:

- **evidence-gated** — needs ≥ `min_shared` shared committed arguments agreeing at
  ≥ `agree_threshold` (the commitment discipline, in the relation dimension);
- **defect-guarded** — a merge that would make the relation non-functional (a
  source with two committed targets = a holonomy self-loop defect) is refused; the
  fixed algebra rejects a bad relation-merge exactly as it rejects a false MATCH.

Talk-back then filters by relation CLASS, not raw frame id, so synonymous frames
answer each other: a fact taught only through `i see a red moose` is answered by
`the moose is ?`. `is`/`see` merge; `is`/`eats` (disagreeing on every shared
animal) never do. The classes persist with the geometry. This is the same
mention/node-merge decision as cross-book character identity (R3), on the relation
axis; batch reference machinery is `types.py` (P2′) and `sectors.py`.

## Store selection in the live path (built)

The stores are wired into every entry point: `RELWEB_STORE=memory|sqlite|sharded[:N]`
(or `relweb-train --store`) selects the backend for the trainer, the server,
`relweb-correct`, `relweb-wonder` and `relweb-version` alike (`store.open_store`
is the one factory). Under a durable store the JSON checkpoint stops dumping the
web and records an **external pointer** (spec + counts) instead — the database
files are their own persistence — so `save` is O(bounded state) regardless of
geometry size. Saves are atomic (temp + rename) and stamped with the git commit
and curriculum hash that produced them; an inline-geometry checkpoint migrates
into a store the first time it is loaded with one; a lost database is rebuilt
from the episode log by replay (the log stays the belief source). Versioning
(`relweb-version`: tag / list / belief-diff / rollback, plus per-tick auto
snapshots) covers checkpoint + log + store files as one consistent unit.

## Not yet built (next steps)

- Migrating the web app to serve **named creatures** (identity in the API/UI).
- An archived/sampled episode stream alongside the store (currently episodes are
  distilled and dropped; keeping a sampled trail would aid audit/replay).
- Relation unification up to TRANSPOSE (a frame that orients the other way
  produces the transposed edge set) and non-functional relations — v1 handles the
  functional, same-orientation case.
