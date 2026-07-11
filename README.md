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

What that buys you, concretely:

- **It composes exactly.** Taught "ten comes after nine", it *derives* the
  never-heard "nine is before ten" — and held-out arithmetic scores 100% with
  zero parameters where trained knowledge-graph embeddings score ~50%.
- **It invents numbers.** It is only ever taught to count. Asked `three minus
  five`, it walks off the edge of its number line and *grows* the missing
  concepts — its own negative numbers, with correct arithmetic.
- **It refuses rather than confabulates.** Unknown means unknown. Thin evidence
  stays "provisional". A question it can't ground is declined, with the reason
  on the record.
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
```

Training and serving share a lock, so a correction can never interleave with a
scheduled run. Or ship the whole thing as a container:

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
