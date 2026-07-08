# Design Log & Reconciliation Notes

A **running** document. The dev-doc (`dev-doc.md`) is the clean spec — phases,
invariants, acceptance tests. This file is everything *around* it: decisions
taken in conversation, reconciliations between competing framings, deliberate
deviations from the spec, and open questions. `scaling.md` owns the
distribution / web-scale story; this file points there rather than duplicating.

**How to use:** append dated entries; do not rewrite history. When a decision
here graduates into the spec, note it and leave the log entry as the rationale.
Cross-link with `[dev-doc §X]`, `[scaling.md §Y]`.

---

## 1. The reconciliation: two formalisms → one bare substrate

**The problem.** The dev-doc and reference experiments carry two different
substrates that were never explicitly bridged:

| | Holonomy substrate (P0/P1/P2/P3) | Counting substrate (P1b, `0e`–`0i`) |
|---|---|---|
| state | edges carry **Z**; BFS potential | **union-find** over collections |
| signal | nonzero loop **holonomy** = defect | "class ONEMORE of itself" |
| machinery | `holonomy.py` | bare `UF` + `derive()` |

The experiments `0e/0h/0i` re-implement their own mini-webs and never touch
`web.py`/`holonomy.py`, yet the repo layout routes everything through them and
invariant 9 defines the signal as defect *mass over loops* (a holonomy notion
the counting side never computes). Left unreconciled, the project is a pile of
demos and the "one algebra / one bus" thesis stays rhetorical.

**The resolution (decided 2026-07-09).** *"Bare web is the standard."* The
canonical atom is the bare `(collection₁, collection₂, pairing)` episode — no
numbers, no relation labels. Everything else is a **derived projection** on top:

- `ONEMORE(A,B)` → a `+1` edge between class nodes.
- `MATCH(A,B)` → a **merge** (node identification); the union-find quotient of
  the experiments *is* the merge-commitment projection.
- successor **injectivity** ("a class with two successors must merge them") →
  a merge of two nodes the holonomy says sit at **equal potential** — i.e. a
  0-holonomy *compression*, a sleep-phase quotient, not a defect repair. This
  is exactly how `0e.repair()` frames it.
- **"class ONEMORE of itself"** → a `+1` **self-loop** → holonomy `+1 ≠ 0` → a
  genuine defect. This is what makes **invariant 9 literally true** for the
  counting contradictions.
- subtraction-probe growth (the negative numbers) → `grow` at the quotient
  level → literally P1.

So the labeled, Z-valued web is not a parallel system; it is what the learner
*derives* from bare episodes. `holonomy.py` is the one defect engine; the
union-find in `0e`–`0i` is a fast special-case of the merge projection.

**Consequences for the build.**
- The bare `Episode` is the substrate atom (`episode.py`), already built in P0.
- P1b's job is the **derivation layer**: bare episodes → MATCH/ONEMORE →
  merge / `+1`-edge commitments, with the self-loop surfaced as a holonomy
  defect. `0e`–`0i` get refactored to route through `web.py` rather than
  standing alone.
- Downstream phases (P2, P3) consume the **derived class chain**, not synthetic
  number nodes [dev-doc P1b].

**Still open (see §5):** whether MATCH is best modelled as a node merge or as a
`0`-value "same" edge (I lean merge — it makes injectivity and retraction fall
out cleanly); and exactly how `loop_closes` / `distinct` observations are
themselves *derived* from bare episodes rather than asserted.

---

## 2. Decisions taken in conversation (2026-07-09)

Recorded with rationale so we don't relitigate.

1. **Re-found P0 on the event-sourced substrate now**, rather than building P1
   on the in-place P0 and retrofitting. Rationale: invariants 4–8 are
   foundational; if the log/bus/projection/fork don't exist from the start, the
   later phases stop being "seams" (inv 8's own claim) and become rewrites.
   *Done — commit `7944776`.*

2. **"Bare web is the standard"** — see §1.

3. **Retraction locality is built in early.** Provenance links are first-class
   (`commit → episode ids`); episode ids are opaque `(source, seq)` handles, not
   list positions, so compaction and multi-source merge never break provenance.
   Whole-log rebuild for now; causal-cone scoping deferred [scaling.md §3].

4. **Not a local monolith.** The system must be able to run across machines /
   over a network / with volunteer compute eventually. The monotone core (log,
   union-find, exclusion set) is CRDT-shaped, so distribution is a *join*, not a
   protocol. Nothing scheduled [scaling.md §4].

5. **"Every op emits" (inv 4) is a bootstrap property, not an eternal law.**
   At scale, *what* to emit and *when* to simulate become **learned** attention
   policies; emission may be aggregated; simulation is phase-gated by wake /
   sleep / dream cycles, not always-on. Keep emission behind a single seam
   (`Web._trace` / `Journal.emit`) so the future policy has one hook
   [scaling.md §6].

6. **Perception (text/media → episodes) is out of scope.** This project is the
   "after clean relational episodes" engine; the front-end sets the real
   accuracy ceiling at scale [scaling.md §7].

---

## 3. Deliberate deviations from the dev-doc

Where the implementation intentionally differs from the letter of the spec, and
why. (Candidate dev-doc edits are flagged in §4.)

- **Package layout.** Spec sketches a flat `relweb/`. We use an installable
  `src/relweblearner/` package (Poetry, in-project `.venv`). Requested: "keep
  src/, use better structure than the doc."
- **Defect extraction.** Spec says `nx.minimum_cycle_basis`. We use
  **spanning-tree fundamental cycles** (BFS potential → per-non-tree-edge
  residual). Reason: `minimum_cycle_basis` returns *unordered node sets*, which
  cannot be walked to compute a holonomy, and it is blind to parallel-edge
  bigons. Fundamental cycles are ordered, multigraph-safe, and give the same
  independent-class count. `nx.cycle_basis` (ordered) is kept as a cross-check
  in `cycle_basis_defects`.
- **Episode ids.** Opaque `(source, seq)` instead of positional indices — for
  compaction/merge-readiness [scaling.md §3–4].
- **`relabel` is ephemeral.** It mutates live edge values but is *not* a
  commitment (relabeling is meaningless bookkeeping, glossary), so a rebuild
  resets values. Holonomy is invariant either way.
- **Observation API is pre-derivation.** `observe_loop_closes` /
  `observe_distinct` are a low-level convenience like `add_edge`; P1b will
  derive these constraints from bare episodes. Kept for unit tests / scaffolding.
- **Loop-closure contradiction detection is best-effort under parallel/merged
  edges.** Node-path holonomy is only well-defined on a simple graph; under
  parallels a node path is ambiguous. Distinctness-under-merge is checked
  exactly (alias map). Robust cycle-basis loop-closure checking lands with the
  P1 growth/rewire search.
- **Whole-log rebuild** rather than incremental/cone-scoped projection — correct
  at laptop scale; optimized when a phase stresses memory (P7 floods).
- **`sympy` treated as a hard dep** (P2's noise-tolerant integer nullspace),
  though the spec lists it optional. Already installed.

---

## 4. Candidate dev-doc edits (not yet applied — spec owned by you)

Left for you since you're actively editing `dev-doc.md`:

- **P0 acceptance:** replace "extract independent defect classes via networkx
  `minimum_cycle_basis`" with fundamental-cycle residuals (+ `cycle_basis`
  cross-check). See §3.
- **P3 vs P1b tension:** P3 still describes synthetic entities `0..N`, but P1b
  mandates downstream phases consume the *constructed* class chain. Clarify that
  baselines get synthetic triples while the web learner gets constructed classes.
- **§4 Metrics is stale** vs the new phases: add collateral-retraction count,
  detection rate / time-to-detection, cf-vs-real act split, attention backlog,
  and the consistent-lie cost curve.
- **Invariant 4 wording:** note it is constitutive at bootstrap and becomes a
  learned/aggregated policy at scale (see §2.5, scaling.md §6), so the CI test
  ("every public method emits") is a current-phase property, not eternal.
- **Repo layout block** references `relweb/`; we use `src/relweblearner/`.

---

## 5. Open questions

Reconciliation / substrate:
- **MATCH = merge, or MATCH = `0`-value "same" edge?** Leaning merge (makes
  injectivity a 0-holonomy compression and retraction a commit exclusion). A
  `0`-edge keeps nodes distinct and defers identification — may matter for
  provisional (k≥2) commitment [dev-doc inv 6]. Decide at P1b.
- **How are `loop_closes` / `distinct` observations *derived* from bare
  episodes** rather than asserted? (MATCH ⇒ loop closes / same; ONEMORE ⇒
  distinct + successor.) Needed to retire the pre-derivation Observation API.
- **Provisional commitment vs projection.** Inv 6 wants merges provisional
  until k≥2 witnesses. Does "provisional" mean the merge commitment is withheld,
  or committed-but-flagged and easily excluded? Ties to the MATCH question.

Carried from `scaling.md §9`:
- snapshot granularity; when a causal cone is safe to *seal* (compact);
  ensemble merge semantics across untrusted volunteers; whether aggregated
  emission preserves enough signal for P6 reflection to still form act-classes.

---

## 6. P1 growth engine — notes (2026-07-09)

- **Query walk is an act** (`Web.walk`, inv 4): stepping follows relation
  *structure*, not edge values, so a boundary walk-off is reachability, not
  gauge — which is why relabel is provably futile against it.
- **Persistence detector without corrupting state.** The "P rounds of
  relabel+rewire" run on **forks** (`Web.fork`, inv 8), never the committed web:
  relabel-futility is demonstrated on a throwaway fork, and each rewire
  candidate is scored on a fork (accept only if the whole walk completes in-web
  with no new defect). *Bug found & fixed:* an earlier version relabeled the
  real web, so `_step_value` read gauge-mangled values and accepted a bogus
  "bouncing" reconnection. Lesson logged: gauge moves must stay off the
  committed projection during search.
- **rewire-before-grow is real, not cosmetic.** If an existing node can
  complete the walk (e.g. a removed middle edge), a single rewire discharges it
  and growth is refused (`test_obstruction_completable_in_web_is_discharged_by_rewire`).
  Growth fires only for genuine boundary walk-offs.
- **Minimal growth** = exactly `deficit` fresh nodes chained with the frozen
  step value; "BFS over completion candidates" degenerates to this for a linear
  walk with no reusable node. Zero-shot arithmetic through the invented nodes is
  exact because the edges carry the same frozen `+1` (e1 (c): ≥20 facts).
- **Threshold, not drift** (e1 plot): growth is flat-zero for every in-web probe
  and turns on exactly at the first boundary crossing. `results/e1_growth.{csv,png}`.
- Open: the discharge accepts the *first* consistent in-web completion (bare —
  no notion of the "intended" node). Fine for e1; revisit if a phase needs the
  minimal/most-justified completion rather than any.

## 7. Log

- **2026-07-09** — P0 (original holonomy kernel) committed `9b75123`.
- **2026-07-09** — Doc revised (invariants 4–8, P1b, P6/P6'/P7/P8; new
  reference experiments `0e`–`0i`). Feedback given; decisions §2 taken.
- **2026-07-09** — `scaling.md` written (distribution/web-scale/volunteer).
- **2026-07-09** — P0 re-founded on event-sourced substrate committed
  `7944776` (`episode.py`, `journal.py`, `web.py` as projection; 22 tests).
- **2026-07-09** — This design log created.
- **2026-07-09** — P1 growth engine: `web.walk`, `growth.py`,
  `datasets/arithmetic.py`, `experiments/e1_growth.py`; e1 accepted (27 tests).
