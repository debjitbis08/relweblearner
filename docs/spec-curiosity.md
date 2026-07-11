# SPEC — Curiosity (PQ): the wonder ledger + oracle ticks

Standalone phase spec, tests-first (`tests/test_curiosity.py` is the
acceptance gate; it `importorskip`s the module until the phase lands).
Self-contained; assumes the DEVDOC glossary and the trust phase
(`test_trust.py`) as prior art.

## 0. Position in the architecture

Curiosity is a **policy layer**, never a new epistemology. The frozen
algebra, the commitment gate (`commit_k` independent witnesses), the
per-domain trust ledger, and replay-with-exclusions retraction all apply
to curiosity-fetched answers UNCHANGED — an oracle is a source like any
book. The layer adds exactly two things:

1. a **wonder ledger** — the creature's open questions, on the record;
2. a **tick** — a budgeted batch step that routes open questions to
   declared oracles and ingests whatever comes back as ordinary
   testimony.

The theoretical statement, extending the move hierarchy: learning is the
cheapest observation-preserving repair — `relabel < rewire < grow` — and
**ask** is the move *below refusal*: when no edit can remove a defect or
commit a provisional edge because the problem is missing evidence, the
cheapest repair is to schedule an observation. Curiosity is the creature
choosing its own next input to shrink `defect mass + provisional mass`.

Deleting the curiosity module must leave every existing acceptance test
passing (it is atop the creature, like language atop concepts). The only
creature-core touches are: (a) `answer()` mints a wonder act when a
parsed question goes unanswered, (b) `_apply_act` folds the three new
act kinds into the ledger on replay, (c) one constructor knob
(`wonder_cap`).

## 1. The wonder ledger (a projection of the log)

There is **no second log** (invariant #4/#5). A question is an ACT ENTRY
on the persistent episode log, and the ledger is a *projection* — it
survives rebuild because it is recomputed from the record, exactly like
trust. Three act kinds (`{"kind": "act", "move": ...}`):

- `wonder` — a question is born. Carries a stable `wid`, the question
  kind, subject, the relation's **anchor words** (its stable name across
  replays, same trick as growth acts), and the phrase if user-asked.
- `sought` — one tick attempted it: which oracles were consulted. The
  tick that exhausts a wonder's attempts records the parking on its
  final `sought` act; the ledger derives `parked` from the record, so a
  later change of the `max_attempts` knob can never silently unpark
  history.
- `resolved` — it settled, with how (`committed` / `answered` /
  `settled`). A resolved wid never reopens.

### 1a. Where wonders come from

Three kinds, two provenances:

- **`unknown`** (event, persisted): `Creature.answer()` on a *parsed*
  question (frame matched — junk that fails to parse must NOT mint)
  whose result is `known: false` appends a `wonder` act. This covers
  both live users and failed worksheet questions — a flunked exam is
  curiosity fodder. Deduped by `wid`; bounded by the `wonder_cap`
  constructor knob (default 64): at the cap, minting is refused and
  traced (`refuse` on the bus), P7-style — refuse, don't flood.
- **`confirm`** (standing, computed): every provisional edge — a fact
  one independent witness short of belief. Not persisted: provisional-ness
  is already a projection; the ledger enumerates it fresh at read time.
- **`arbitrate`** (standing, computed): every standing committed
  conflict that `revise()` declines to settle (tied trust-weighted
  support) and every nonzero-holonomy defect edge. Also computed fresh.

### 1b. Ranking

`wonders(creature)` returns the OPEN ledger ranked: `arbitrate` >
`confirm` > `unknown` (repair live contradictions first, then cheapest
commits, then service unknowns), oldest first within a kind. Each row:
`{wid, qkind, subject, object?, anchors, phrase?, sought}`.
`ledger(creature)` additionally splits out `parked` and `resolved`.

**Accept:** a parsed-but-unanswerable question mints exactly one wonder
(re-asking dedups); an unparsed phrase mints nothing; minting refuses at
`wonder_cap`; a provisional edge appears as a `confirm` row and a tied
committed conflict as an `arbitrate` row; the ledger is ordered
arbitrate/confirm/unknown; `rebuild()` (full replay) reproduces the open
ledger exactly.

## 2. Oracles (declared, targeted, distrusted-by-default)

An **Oracle** is `{id, anchors, frames, lookup, domain}`:

- `id` — the source name stamped on every episode it teaches; this is
  the handle the trust ledger judges. One oracle = ONE witness, no
  matter how often it repeats itself (source-counted support, as ever).
- `anchors` — the relation-naming words it can answer about. Routing is
  lexical: a wonder routes to an oracle iff their anchor sets intersect.
- `frames` — paraphrase templates (`["the","{s}","is","{o}"]`) its
  triples are rendered through, one episode per triple per frame.
  P9 label discipline holds: the stream the creature reads stays
  label-free; the oracle's relation knowledge shapes only the SPARQL/
  lookup, never a label in the episode. Prefer constructions the
  curriculum already taught, so testimony lands in the induced class.
- `lookup(subject) -> [(subject, object), ...]` — the targeted fetch.

Declarative registry `corpus/oracles.json` (sibling of `sources.json`),
loaded by `oracles_from_json(path)`. Kinds:

- `triples` — inline table, offline (tests, hand-authored knowledge);
- `wordnet-lookup` — hypernyms of one word (nltk, offline);
- `wikidata-lookup` — one entity's one property via SPARQL
  (`factsource.wikidata_lookup(subject, property)`, new; same `_clean`
  single-token discipline, same UA, raises on throttle so the tick
  parks-and-retries rather than hammers).

**Accept:** `oracles_from_json` builds all three kinds without touching
the network (lookups are lazy); a `triples` oracle round-trips.

## 3. The tick (batch answering, budgeted)

`tick(creature, oracles, budget=8, corroborate=2, max_attempts=3)` — one
batch, designed to run beside the training tick under the same
`creature_lock` (cron: `scripts/wonder_tick.sh`; CLI: `relweb-wonder`).
Per tick:

1. Take the top `budget` open, un-parked wonders **that have at least
   one routable oracle** — an unroutable wonder is skipped untouched (it
   must not creep toward parked while no oracle exists for it).
2. For each: consult up to `corroborate` routable oracles (two when
   possible — one oracle can never commit alone, and that is the point,
   not a defect); render each answer through the oracle's frames; ingest
   as ordinary world episodes with `source = oracle.id`.
3. Re-check resolution: `unknown` resolves when the phrase now answers
   (`known: true` — even provisionally: the creature is no longer
   ignorant, and the thin edge immediately re-surfaces as a standing
   `confirm` wonder, which is the chaining that makes single-oracle
   answers honest); `confirm` resolves when the edge commits;
   `arbitrate` resolves when the conflict is gone (a decree settled it)
   or as INFORMED — the camps are no longer tied (trust-weighted support
   strictly ordered). Informed, never erased: testimony NEVER outranks
   testimony (`_beats`, the hen→bird lesson), so curiosity's whole job
   on a standing conflict is to gather the decisive margin and keep the
   dissent visible for decree or trust erosion to settle.
4. Log `resolved` or `sought` accordingly. A wonder with
   `max_attempts` fruitless soughts is PARKED: listed under `parked`,
   never attempted again, beliefs untouched — refusal, not fabrication.

Returns `{attempted: [wid], resolved: [wid], parked: [wid], open: n}`.

**Accept:** a provisional fact commits after one corroborating oracle;
an unknown answered by a single oracle becomes a PROVISIONAL belief
(never committed) plus a fresh `confirm` wonder; two independent oracles
commit; `budget=2` over four open wonders attempts exactly two; an
always-empty oracle parks a wonder after `max_attempts` ticks with zero
belief change; a tick with no routable oracle attempts nothing and adds
no world entries; a tied 2-vs-2 committed conflict plus one truthful
oracle resolves as informed — BOTH camps stay committed (testimony never
erases testimony), the majority's support strictly greater on the record.

## 4. Epistemic guarantees (the safety section)

These are what make self-directed internet learning safe HERE when it is
not safe in general, and each is a test:

- **Testimony, not truth.** An oracle answer enters through `ingest`
  like a book page: k-witness gated, trust-weighted, replayable,
  excludable. Nothing in the tick writes an edge directly.
- **Independence is per source.** `corroborate` oracles means two
  *different* trust-ledger rows; an oracle repeating itself stays one
  witness.
- **Lies are survivable.** An oracle caught wrong (`retract_claim` /
  `correct`) loses trust in that relation class only — the standard
  machinery, no special case (**Accept:** `source_weight(oracle_id,
  class) < 1` after adjudication).
- **Budgets everywhere.** `wonder_cap` on minting, `budget` per tick,
  `corroborate` per question, `max_attempts` before parking. Exhaustion
  degrades to refusal (P7), and the reflection layer's bounded-consume
  already models the answer-spawns-questions regress.
- **No new moves.** The tick's writes are world episodes + the three
  ledger act kinds. It never touches web geometry except through
  ordinary ingestion.

## 5. Metrics (log per tick, `results/` at scale)

Open/parked/resolved counts by kind; provisional→committed conversions
per tick; defect-mass delta across a tick; oracle trust rows (the trust
report already covers this); soughts-per-resolution (oracle usefulness).

## 6. Known limits (state them, don't hide them)

- **Routing is lexical.** Anchor-word matching inherits the creature's
  own relation unification — a mis-unified class routes to the wrong
  oracle. Harmless by construction (a wrong answer is just testimony the
  usual machinery weighs), but log route misses.
- **Naming grown nodes is deferred.** A `new-*` concept has no surface
  word to hand `lookup`; asking about it means phrasing through its
  committed neighbours. Out of scope for PQ; the ledger kind is reserved
  (`name`) but unminted.
- **Single-token discipline drops answers.** `_clean` keeps only
  single-token fillers; a targeted lookup whose answer is multi-word
  yields nothing and the wonder parks. Honest, but count it.
- **Wikidata throttles.** Targeted lookups are rate-limited; the tick
  must treat a network error as a fruitless sought, never a retry loop.

## 7. Deliverables

`src/relweblearner/curiosity.py` (Oracle, wonders, ledger, tick,
oracles_from_json) · `factsource.wikidata_lookup` / `wordnet_lookup` ·
`creature.py` seams (mint in `answer`, ledger folds in `_apply_act`,
`wonder_cap`) · `corpus/oracles.json` starter · `relweb-wonder` CLI
(`--show`, `--tick`, `--oracles`) · `scripts/wonder_tick.sh` ·
`GET /api/wonders` · docs updates (README §"Let it keep learning",
how-it-works, theory: the ask-move).
