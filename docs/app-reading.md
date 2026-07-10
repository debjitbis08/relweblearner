# The reading app — hand-training the creature from books

The first **action layer** over the research library: a web app where a human
reads phrases from books to the creature, taps the pictured referent, and the
creature reads, commits beliefs, and talks back. It adds no new learning — it
runs the R2 curriculum-reading pipeline (`docs/spec-curriculum-reading.md`)
**incrementally and statefully**, with persistence and a UI.

## Architecture (three faithful choices)

1. **The referent tag IS the ostension.** When you feed a phrase you tap the word
   for the thing in the picture (e.g. `bear`). That tap orients every fact
   (`curriculum._orient`) exactly as `fast_map_page` does — it is the
   symmetry-breaker the grounding layer needs (spec §0), delivered without an
   image pipeline. Text-only would hit the automorphism ceiling; the tap avoids it.
2. **The concept web is bootstrapped from the reading.** A pure reader has no
   prior concept web to align to, so grounding-through-frames collapses to picture
   orientation and the **committed facts are the concept web**.
3. **State is a projection of an append-only log.** As everywhere in this repo,
   derived state (frames, facts, beliefs) is a pure function of the page log.
   `Reader.feed` appends one line to a JSONL log; `Reader.load` replays it to
   reconstruct a session exactly. The log is the source of truth.

## Layers

- **`src/relweblearner/reader.py`** — `Reader`, the stateful session. `feed`,
  `about` / `answer` (ask), `say` (state what it learned, L6 write + read-back),
  `snapshot` (spec §6 metrics), `load` (replay).
- **`src/relweblearner/serve/`** — a thin FastAPI app; every endpoint is a direct
  call into `Reader`. Static single-file UI in `serve/static/index.html`.
- **`tests/test_reader.py`** — the session acceptance suite.

## Commitment

A fact is **provisional** when heard from one book and **committed** once it has
`commit_k` distinct book/source origins (default 2 — spec §0.3 / §6). The UI shows
both, so learning is visible on the first read while belief still requires
corroboration. Off-frame phrases land on the **frontier** ("what confuses it"),
never force-parsed; enough similar frontier phrases trigger a new frame.

## Talk-back

- **Ask** a question with a blank: `the bear is ?` → answers from committed facts
  (forward or reverse lookup by the frame's learned orientation), or refuses
  honestly if the phrase matches no known frame. A lone word is treated as "tell
  me about X".
- **Say**: fills an induced frame from a committed fact and **reads the draft
  back** (re-parses, re-orients) before offering it — the L6 adjunction
  `read(write(f)) == f`. Ambiguous drafts are never emitted.

## Run it

```bash
poetry install
poetry run relweb-serve            # -> http://127.0.0.1:8000
# or: poetry run python -m relweblearner.serve
```

Environment: `RELWEB_DATA` (log path, default `data/session.jsonl`),
`RELWEB_HOST`, `RELWEB_PORT`, `RELWEB_RELOAD`.

### Deploy (single container, one data volume)

```bash
docker build -t relweb .
docker run -p 8000:8000 -v relweb-data:/data relweb
```

The container is stateless except for the `/data` volume; putting it behind a
host (Fly.io / Render / a VPS) is a small step from here. **Before exposing it
publicly, add authentication** — the API is currently open, appropriate for
single-user local use.

## API

| Method | Path             | Body / query                         | Returns |
|--------|------------------|--------------------------------------|---------|
| GET    | `/api/status`    | —                                    | frames, beliefs, frontier, metrics |
| GET    | `/api/tokenize`  | `?text=`                             | word tokens (UI chip source) |
| POST   | `/api/feed`      | `{text, picture, book}`              | observation + updated status |
| POST   | `/api/ask`       | `{text}`                             | answer (blank or about) |
| POST   | `/api/say`       | `{referent?}`                        | generated sentences |

## Known limits (stated, not hidden)

- Single-user; no auth; one process, one session log (a process lock serialises
  writes). Multi-user / multi-creature is future work.
- Real StoryWeaver-tier books will have coverage < 1 (spec §7); the app skips and
  logs unparsed sentences to the frontier by design.
- `min_group` is lowered to 3 (from the batch spec's 10) for interactive feeding;
  frames form after a few same-shape phrases. This is the dominance/anchor
  discipline unchanged, only the support floor relaxed for hand-training scale.
