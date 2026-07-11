# relweblearner

**Raise a small artificial mind that keeps a diary, refuses to guess, and can
be taught it was wrong.**

There is no neural network here. No weights, no gradients, no embeddings. A
*creature* learns by writing every experience into an append-only log and
distilling it into a web of concepts — a graph whose edges carry values from a
small, **frozen** algebra (integers, at first). Contradictions show up as loops
in that web that don't "close", and closing them is the only thing learning is
allowed to do. Every belief can be traced to the episodes that justify it,
reproduced by replaying the log, and revoked by replaying without the lying
pages.

## The hypothesis

Stated technically, the claim under investigation is:

> **Some relational learning can be represented as fixed-algebra constraint
> discovery and geometry-gated repair — and this project measures exactly
> which sectors of knowledge admit that representation.** The state is a
> graph whose edges carry values from a frozen involutive monoid (ℤ under
> addition first; the algebra is code, never learned). Composing values
> along a path is parallel transport; a **contradiction is a loop whose
> transport is not the identity** — nonzero holonomy, the discrete analogue
> of curvature. Repair is the *cheapest observation-preserving edit* that
> removes such defects: relabel (free, provably changes no holonomy — the
> null move that keeps everything honest) < rewire < grow new nodes
> (budgeted; exhaustion means refusal, not fabrication).

The project began as a stronger bet — *all* learning reduces to geometry
repair — and the pre-registered falsification program below is what cut it
down: the universal form is **withdrawn**, and the sector boundary (which
relations the frozen algebra can and cannot carry) is now a measured
quantity rather than an aspiration.

Freezing the algebra is what makes contradiction *objective*: if the
composition law itself could learn, a defect could always be escaped by
bending the ruler instead of fixing the map. It also makes inference exact —
answering is transport, so entailments are computed, not approximated. Two
more commitments complete the design: the state is a **projection of an
append-only episode log** (so any belief is reproducible by replay and
revocable by replay-with-exclusions — retraction is a theorem, not a hope),
and commitment is **evidential** (a claim needs k independent — now
trust-weighted — witnesses before it counts as belief). Everything else in
the repo (invented numbers, frame induction, inheritance motifs, per-domain
trust, the society layer) is these few rules applied without exception; the
falsifiable part is how far they reach. The full story with definitions and
references is [docs/theory.md](docs/theory.md).

**Where the evidence stands** (a pre-registered falsification benchmark,
run 2026-07-11 — design in
[docs/falsification-plan.md](docs/falsification-plan.md), outcomes in
[docs/falsification-report.md](docs/falsification-report.md)): the creature
really does discover converse structure from raw pages and answer held-out
inversions by transport where pure recall scores zero, its refusals and
exact unlearning hold under adversarial lies, and its holonomy signal
detects a class of contradiction (the "loop lie") that lookup is
structurally blind to and statistical detectors miss under noise. The first
run also found the mechanism's edge honestly: composite relations
(skip = step∘step) were undiscoverable — gauge groups formed from converse
evidence only — and the follow-up run closed exactly that gap with 3-cycle
loop evidence behind a defect gate (candidates are mined statistically but
admitted only if the resulting geometry stays consistent: the miner
proposes, the geometry disposes). The flip is on the same frozen benchmark:
skip-transfer went 0.00 → 1.00, discovered from raw pages, with no false
alarms on the clean arm. What remains true: a plain statistical rule inducer
matches the capability numbers on the clean benchmark — the demonstrated
differentiators are the guarantees (exactness, audit, exact unlearning) plus
noise-robust detection and admission that is robust against **algebraically
incompatible** forged compositions (a statistically convincing rule that
would collapse live structure is refused; a *coherent* forgery still passes
— coherence is not correspondence, and that limit is measured, not hidden).
So the defensible claim today: an event-sourced, provenance-aware relational
learner with exact inference, geometry-gated structure discovery (converses
and binary compositions so far), noise-robust inconsistency detection, and
exact unlearning. On the external GraphLog benchmark the same machinery
discovers relation transports from composition evidence alone (the data has
no converse pairs at all), but recovery of the additive-oracle reference is
**inconsistent** — near-complete on one development world, near-floor on
most — and the reference itself is low, because GraphLog's rule systems are
non-abelian and the frozen ℤ algebra provably cannot represent them
(measured per world: the true rules, exactly solved through the same
decoder, top out at 0.02–0.58 where non-abelian rule rewriting reaches
0.48–0.88). Discovery, not only representation, remains a limitation there.
The evidence covers exactly that much; the next stake is a genuinely
noncommutative frozen carrier behind the same interface.

What the bet buys, concretely:

- **It composes exactly.** Taught "ten comes after nine", it *derives* the
  never-heard "nine is before ten" with zero parameters. (The older "100% vs
  ~50% against trained knowledge-graph embeddings" figure demonstrates exact
  composition — a property the representation entails — not superior
  learning; see the falsification report.)
- **It invents numbers.** It is only ever taught to count. Asked `three minus
  five`, it walks off the edge of its number line and *grows* the missing
  concepts — its own negative numbers, with correct arithmetic.
- **It refuses rather than confabulates.** Unknown means unknown. Thin evidence
  stays "provisional". A question it can't ground is declined, with the reason
  on the record.
- **It is curious about its own gaps.** A question it couldn't answer, a fact
  one witness short, a disagreement it's holding open — each is an open
  *wonder* on its ledger, and a scheduled tick batch-answers them from
  declared oracles (WordNet, Wikidata). Oracle answers are ordinary testimony:
  one source never commits a belief, and a lying oracle loses trust like any
  book.
- **It can be corrected without retraining.** Teach it the right fact once and
  it notices the contradiction, retracts the outweighed belief itself, and
  starts taking the sources that misled it with a grain of salt — per topic.
- **Everything it does is on the record.** Every observation, merge, growth,
  answer and retraction emits a trace onto the same bus it learns from, so it
  can (and does) reflect on its own acts.

New here? Two guided tours, written for people who've never seen the project:

- **[docs/how-it-works.md](docs/how-it-works.md)** — the whole system in plain
  language (no jargon, popular-science level).
- **[docs/theory.md](docs/theory.md)** — the technical story: the math, the
  architecture, and where each idea comes from, with references.

---

## Run it in five minutes

You need Python 3.11+ and [Poetry](https://python-poetry.org/). Everything runs
on CPU; there is nothing to download but the code.

```bash
git clone <this repo> && cd relweblearner
poetry install
poetry run pytest          # ~280 acceptance tests, a few minutes
```

### 1. Raise a scholar

```bash
poetry run relweb-train --all        # run the whole curriculum (~2 min + fetches)
poetry run relweb-progress           # report card: stages mastered, scores
```

This teaches a persistent creature (default name `scholar`, saved under
`data/creatures/`) through a mastery-gated curriculum: counting play first,
then arithmetic, elementary science, everyday words, real Project Gutenberg
books, WordNet taxonomy and Wikidata facts. After each stage it sits a
worksheet and only advances on a pass — otherwise it holds the stage and
re-sits next run.

### 2. Talk to it

```bash
poetry run relweb-serve              # → http://127.0.0.1:8000
```

The web console lets you **ask** it questions ("hen has ? legs" → *two*,
derived through "a hen is a kind of bird"), **teach** it new phrases by tapping
the pictured word, mark an answer **wrong** right on the card, and *watch it
think* — its concept web, its learned geometry, its relation classes, its
inheritance rules with the evidence for each, its trust ledger, and every
defect it knows it has.

From the shell:

```bash
poetry run relweb-correct --show cat            # current beliefs about 'cat'
poetry run relweb-correct --fix owl four two    # teach: owl has two legs, not four
poetry run relweb-correct --trust               # whom does it trust, about what?
```

`--fix` is not a database edit. It asserts the right fact once, with your
authority; the creature finds the contradiction, excludes the outweighed
episodes (flagged in the log, never deleted), rebuilds, and marks down the
sources that taught the lie — in that relation class only.

### 3. Let it keep learning on a schedule

```bash
# one lesson per tick; a no-op once the curriculum is mastered
*/30 * * * * /path/to/relweblearner/scripts/train_tick.sh >> /path/to/relweblearner/data/train.log 2>&1
# one curiosity batch per tick: answer its open questions from the declared oracles
15,45 * * * * /path/to/relweblearner/scripts/wonder_tick.sh >> /path/to/relweblearner/data/wonder.log 2>&1
# re-examine everything it has ever mastered; alert on any drift
50 */2 * * * /path/to/relweblearner/scripts/eval_tick.sh >> /path/to/relweblearner/data/eval.log 2>&1
# run the full acceptance suite nightly — local CI, no cloud runner
20 3 * * * /path/to/relweblearner/scripts/nightly_check.sh >> /path/to/relweblearner/data/nightly.log 2>&1
```

The wonder tick is the self-learning half ([docs/spec-curiosity.md](docs/spec-curiosity.md)):
questions it was asked and couldn't answer, facts one witness short of belief,
and standing disagreements are batch-answered from the oracles declared in
`corpus/oracles.json` — as ordinary, trust-weighted, revocable testimony.
Inspect its curiosity from the shell:

```bash
poetry run relweb-wonder --show          # what is it wondering about?
poetry run relweb-wonder --tick          # one batch: ask the oracles, ingest, resolve
```

The examination tick is the testing half: `relweb-eval --run` re-sits **every**
stage's worksheet (mastery must not decay), audits the invariants (holonomy
defects, refusal-not-confabulation, committed facts accounted for), appends a
row to `data/metrics.jsonl`, and compares it with the previous row — any
regression lands in `data/alerts.log`, raises a desktop notification, and exits
non-zero for cron. A question it misses on an exam becomes an open wonder, so
failing an exam literally makes it curious. `relweb-eval --report` prints the
trend and plots `results/eval_trend.png`. Everything runs on the one machine —
no CI service, no cloud runner.

Training, wondering and serving share a lock, so a correction can never
interleave with a scheduled run. Each training tick also snapshots the state it
produced (see versioning below), so any night's run can be undone. Or ship the
whole thing as a container:

```bash
docker build -t relweb . && docker run -p 8000:8000 -v relweb-data:/data relweb
```

---

## Make it yours

Almost everything you'd want to change is data or a constructor argument, not
code.

**Grow the syllabus** — the entire curriculum is one declarative file,
`corpus/sources.json`. Add a source and a stage; the next training tick picks
it up, no code change:

```jsonc
// a real knowledge source: one line = hundreds of gradeable facts
{ "id": "wn-birds", "kind": "wordnet", "root": "bird.n.01", "max": 200,
  "domain": "science", "title": "bird taxonomy",
  "frames": [["a", "{s}", "is", "a", "{o}"],
             ["the", "{s}", "is", "a", "kind", "of", "{o}"]] }
```

Source kinds: `generated` (the hand-built math/science/pattern worlds under
`src/relweblearner/datasets/`), `gutenberg` (public-domain books, fetched on
demand), `wordnet` (is-a subtrees, offline), `wikidata` (any property, via
SPARQL, cached). Facts arrive as label-free sentences in several paraphrase
constructions, so the creature must *discover* that they express one relation —
the label survives only as the worksheet's answer key.

**Name your creature** — `relweb-train --name darwin` raises a separate
creature with its own log, checkpoint and report card. `RELWEB_CREATURE` /
`RELWEB_DATA` point the server at it.

**Scale its memory** — by default the concept web lives in RAM and inside the
JSON checkpoint; past a laptop-sized world, move it behind an indexed on-disk
store. One switch, honoured by every command (`relweb-train --store` sets it
per run):

```bash
export RELWEB_STORE=sqlite      # or sharded:6 — memory is the default
```

The checkpoint then records a *pointer* to the database instead of dumping the
web, saves stay O(what-is-bounded) however large the geometry grows, and
queries stay O(neighbourhood) (measured to 200k+ concepts,
[docs/scale-substrate.md](docs/scale-substrate.md)). An existing JSON-trained
creature migrates automatically the first time it is opened with a store; if
the database file is ever lost, the episode log rebuilds it by replay.

**Version the mind** — a creature's whole state is checkpoint + append-only
log (+ store files), so a *version* is a consistent, taggable copy of the
three, and two versions diff as **belief sets**, not bytes:

```bash
relweb-version --tag before-wikidata     # snapshot the current state
relweb-version --diff before-wikidata    # what has it learned/unlearned since?
relweb-version --rollback before-wikidata# restore it (current state rotated aside)
relweb-version --list                    # every version, with the code that made it
```

Every training tick auto-snapshots (`auto-*` tags, newest
`RELWEB_AUTOSNAP_KEEP` kept, `RELWEB_AUTOSNAP=0` disables), rollback restores
the log too (so the abandoned tail can never replay back on top), and every
checkpoint is stamped with the git commit and curriculum hash that produced
it — any state file is traceable to the exact code and syllabus behind it.

**Tune its epistemology** — `Creature(...)` constructor knobs, all with the
defaults visible in `src/relweblearner/creature.py`:

| knob | default | what it changes |
|---|---|---|
| `commit_k` | 2 | independent witnesses a fact needs to be believed |
| `authority_k` | 10 | clean corroborated facts before a source's lone word suffices (0 = never) |
| `distrust_penalty` | 3.0 | how much one caught lie costs vs. one truth earned |
| `agree_threshold` | 0.8 | how single-valued a relation must look before a second value counts as contradiction |
| `exception_fraction` | 0.2 | tolerated exceptions before a rule/motif is refused |
| `growth_budget` | 16 | how many concepts it may invent before refusing |
| `wonder_cap` | 64 | open unanswered questions it may hold before refusing to mint more |

**Swap the algebra** — the frozen algebra behind the web is one interface
(`src/relweblearner/algebra.py`): integers by default; cyclic groups, Klein
four, and partial inverse monoids ship with it, with a measured trade-off
frontier (`experiments/`, P4). Nothing downstream changes.

**Watch a single idea in isolation** — every mechanism has a standalone,
runnable demo in `experiments/` (number invention, adversarial audits, naming
games between two creatures, clock arithmetic banked as *content* rather than
error...). Each writes CSVs and plots to `results/`.

---

## Where things live

```
src/relweblearner/     the library: creature, web, algebra, holonomy, trust, motifs...
corpus/sources.json    the declarative curriculum (sources + stages)
data/                  your creatures: checkpoint + append-only episode log (gitignored)
experiments/           one runnable demo per mechanism, with plots
tests/                 the acceptance suite — each architectural promise is a test
docs/                  how-it-works.md · theory.md · dev-doc.md (spec) ·
                       design-log.md (every decision) · phase-status.md (build record)
```

The build record — a dozen-plus phases, each gated on acceptance tests, on one
substrate that never needed a redesign — is in
[docs/phase-status.md](docs/phase-status.md), and the reasoning behind every
design decision is in [docs/design-log.md](docs/design-log.md).
