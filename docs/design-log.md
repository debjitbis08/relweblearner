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
- **P2 uses robust consensus, not `sympy` nullspace.** The spec suggests
  "sympy integer least squares / nullspace" for per-relation transport. Because
  the P1b chain already provides node coordinates, classification reduces to a
  per-relation transport-sample consensus under an exception budget — simpler,
  and it is what actually delivers e2's noise tolerance (a nullspace solve is
  brittle to a single bad row). `sympy` stays available for P4's partial-algebra
  work but is unused in P2. See §8.
- **P1b commits merges eagerly (single MATCH), not at k≥2 (inv 6).** Required
  for e1b(e) to exhibit a visible contradiction from one poison; k≥2 provisional
  commitment and localize-and-replay move to P7. Safe because the merge is
  event-sourced and retractable. See §5.
- **The number projection uses its own construction journal.** `project()`
  builds the number web with a fresh journal so replaying the world log N times
  does not pollute it with N copies of construction traces. The world log
  (`NumberLearner.journal`) stays the clean, replayable source of truth. A
  literal reading of inv 4 ("one bus") is bent here for projection hygiene; the
  world/reflection bus is still single.

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
- ~~**MATCH = merge, or MATCH = `0`-value "same" edge?**~~ **Resolved at P1b:
  MATCH = merge** (a rewire, with the poison's justifying episode as
  provenance). This makes the union-find quotient literally the merge
  projection, successor-injectivity a 0-holonomy compression, and — the payoff —
  "class ONEMORE of itself" a `+1` holonomy self-loop detected by
  `holonomy.defects` (invariant 9, no separate contradiction machinery). See §7.
- **How are `loop_closes` / `distinct` observations *derived* from bare
  episodes** rather than asserted? P1b derives MATCH/ONEMORE and never uses the
  pre-derivation Observation API, but the API still exists for P0/unit tests.
  Retire it once every phase consumes derived constraints.
- ~~**Provisional commitment (inv 6, k≥2).**~~ **Resolved at P7.** P1b commits
  eagerly (single MATCH) so e1b(e)'s poison is visible; **P7 adds the k≥2 gate**
  (`audit.derive_facts(k=2)`) as the primary defense — thinly-witnessed poison
  never enters the quotient, keeping purity 1.0 across the 0.1–5% sweep — with
  the greedy localize-and-replay of `experiment0h` as the fallback for lies that
  clear the gate. See §16.

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

## 7. P1b number-from-counting — notes (2026-07-09)

The reconciliation of §1 is now code (`number.py`):

- **Bare episode → derived predicate → web move.** `derive(ep)` reads only
  `ep.leftovers()`: both empty → MATCH; one singleton leftover → ONEMORE. No
  numbers, no labels. MATCH → `web.rewire(merge=...)`; ONEMORE → `+1` succ edge.
- **The union-find quotient IS the web's merge projection.** `web.resolve`
  gives the class; classes are the numbers, appearing only in the merge log.
- **Contradiction = holonomy, not a special case.** A false MATCH welds two
  size-classes; a ONEMORE edge between them becomes a `+1` self-loop;
  `holonomy.defects` reports it as 'class ONEMORE of itself'. Invariant 9 is
  literally the counting-contradiction detector. (Confirmed: `defects()` handles
  self-loop edges — residual `phi[u]+1-phi[u] = 1`.)
- **Guarded successor-injectivity** merges the (unique) successor of each class
  but refuses to merge two classes with ONEMORE evidence between them — that
  would *create* the self-loop, i.e. hide the contradiction. So the poison stays
  visible; it is never "repaired" into a coherent-but-wrong chain.
- **Projection = replay (inv 5).** `project(exclude=...)` replays the world log
  minus an exclusion set, so retracting the poison is `exclude({pid})` +
  re-project — purity restored, no data deleted. This is the P7 hook, working.
- **Deviations logged in §3/§5:** eager single-witness merge (k≥2 → P7); the
  projection uses its own construction journal.
- e1b accepted (5 tests); `experiments/e1b_number.py` reproduces `0e` (staging,
  counting, poison) on the substrate. `results/e1b_number.{csv,png}`.

## 8. P2 symmetry-sector inference — notes (2026-07-09)

- **Coordinates come from P1b, so classification is per-relation transport
  consensus.** Each loop observation ``(a, b, r)`` contributes a sample
  ``coord(b) - coord(a)``; the winning transport is the one that minimizes
  exceptions (DL rule). A relation is homogeneous iff one transport explains
  ``≥ 1 - exception_fraction`` of samples.
  - ``g = 0`` → **symmetric** (the ``2g = 0`` signal: seen both ways, transport
    0 each way, consistent only with 0 over Z).
  - ``g ≠ 0`` → **antisymmetric**.
  - no constant fits → **non-homogeneous / motif** — ``double``'s transport is
    ``count(a)``, so support collapses (≈0.3–0.5, well under the 0.8 threshold).
- **Noise tolerance falls straight out of the exception budget.** One
  adversarial mislabel is a single exception, cheaper than abandoning the true
  transport, so the rule is unchanged (e2: 20/20, not just ≥18/20).
- **Consumes the constructed chain (dev-doc mandate).** `e2_sectors.py`
  end-to-end takes coordinates from a P1b `NumberChain` (class position), not
  given numbers; same/succ/double still classify correctly.
- Deviation logged in §3: robust consensus replaces the spec's sympy nullspace.
- e2 accepted (4 tests); `results/e2_sectors.{csv,png}`.

## 9. P2' unlabeled-relation type discovery — notes (2026-07-09)

- **The most "bare web is standard" phase.** Edges carry no labels; a relation
  type is a *structural equivalence class*. Two opposing operations, per the
  spec: **refinement** (`naive_degree_typing`, a 1-round WL degree-pair coloring
  that over-refines — 4 classes for 3 true types) and **compression** (the
  disjointness / mutual-exclusivity merge that recovers the truth).
- **Disjointness = Markman's mutual exclusivity.** Hubs whose member-sets are
  disjoint are the same type (colors are pairwise disjoint; plants are; a color
  and a plant *overlap* via shared fruits, so they stay distinct). Connected
  components of the disjointness graph are the attribute types; hub-free edges
  are the chain type.
- **Failure mode is a data-volume prediction, not a bug.** With too few crossing
  observations a color hub and a plant hub are accidentally disjoint → one
  bridging edge welds the two cliques → everything conflates into one type. The
  conflation-vs-coverage curve falls from 1.0 (no crossings) to ~0.13 (20
  crossings); generic/full coverage → 0. `results/e2p_types.{csv,png}`.
- **Runs on discovered types, not given ones** (dev-doc mandate): discovery
  consumes only unlabeled `(u, v)` pairs; `truth` is used solely for scoring.
- Kept as an unlabeled edge-list module (`types.py`) rather than forcing the
  bare-episode/Web wrapper — the discovery is purely structural over the graph;
  a `Web`'s `underlying_graph()` feeds it directly when needed.
- Accepted (4 tests); the naive-refinement over-refinement is logged for contrast.

## 10. P3 compositional holdout vs baselines — notes (2026-07-09)

- **Headline (N=200):** web **Hits@1 = 1.0 / MRR = 1.0** on the held-out ``+5``
  relation, with **zero parameters** learned for it — it composes ``+1`` and
  ``+2`` transports exactly. Baselines (dim 32): **ComplEx** 0.49 / 0.85 / 0.61
  (Hits@1/Hits@10/MRR), **TransE** 0.15 / 0.38 / 0.23. `results/e3_holdout.{csv,png}`.
- **The clean finding:** ComplEx *memorizes the training relations perfectly*
  (Hits@1 = 1.0 on ``+1``/``+2``) yet composes the unseen ``+5`` only ~half the
  time. Memorization ≠ composition; the web composes by construction.
- **Deviations (logged):**
  - **numpy, not torch, for baselines.** The spec lists torch-CPU as optional;
    the models are tiny (dim 32, N≈200) so numpy is competent, deterministic,
    and dependency-light. Adam is implemented inline.
  - **TransE needs hard (nearby) negatives.** With standard uniform corruption
    it collapses to the ``r ≈ 0`` degenerate on a dense integer chain (a known
    TransE weakness) and learns nothing; mixing in nearby negatives lets it
    learn local order. ComplEx fits fine with standard uniform negatives, so the
    strong baseline is fully standard.
  - **Report Hits@1 / Hits@10 / MRR**, not Hits@1 alone — it shows the baselines
    *do* learn approximate structure (ComplEx Hits@10 0.85) but cannot nail the
    exact composition the web gets for free.
- e3 accepted (3 tests): web exact; baselines fall short by a large gap.

## 11. P4 algebra sweep — notes (2026-07-09)

- **Pre-committed tradeoff metric** (declared before running, Section 6): the
  two axes are ``bloat = C/D`` (weakness) and ``false_inverse_rate`` (strength);
  no scalar winner; the ``(bloat, false_inverse)`` frontier is the finding.
  Recorded here *before* the numbers to honor "do not tune post hoc".
- **The frozen `Algebra` ABC held.** Adding `CyclicGroup`, `KleinFour`,
  `SymmetricInverseMonoid`, `FreeInvolutiveMonoid` needed no change to web /
  holonomy / growth — exactly the P0 bet (partial composition via `None` was
  already in the interface). Only holonomy needed None-guards (undefined loops
  skipped + counted, Section 6).
- **The table (C=12):**

  | algebra | D | bloat | false_inv | undef | relabel_ok |
  |---|---|---|---|---|---|
  | Z | 12 | 1.00 | 1.00 | 0.00 | ✓ |
  | Z_2 | 2 | 6.00 | 1.00 | 0.00 | ✓ |
  | Z_4 | 4 | 3.00 | 1.00 | 0.00 | ✓ |
  | Z2xZ2 | 2 | 6.00 | 1.00 | 0.00 | ✓ |
  | InvMon_3 | 3 | 4.00 | **0.00** | 0.31 | ✓ |
  | Free_L3 | 4 | 3.00 | 1.00 | 0.00 | ✓ |

  Non-dominated: **Z** (no bloat, hallucinates inverses) and **InvMon_3**
  (honest partial inverses + 31% undefined loops flagged, at a bloat cost). The
  small groups bloat *and* hallucinate — dominated. `results/e4_sweep.{csv,png}`.
- **Relabel-invariance extended to every algebra** (Section 6 mandate): checked
  as defect-*status* invariance under *unit* relabels (permutations for the
  inverse monoid), the universal form of the P0 discipline. Held for all.
- Scope note: e1/e2/e3 re-runs *per algebra* were folded into the ``bloat``
  expressivity axis (D distinct signatures = how much of the integer task the
  algebra can represent) rather than re-run separately; the two named
  diagnostics + the frontier are the deliverable the acceptance asks for.
- Accepted (6 tests).

## 12. P5 design — N-web dynamic ensemble (decided 2026-07-09)

The user extended P5 beyond the dev-doc's pairwise A↔B: **N webs**, and **webs
that split/merge over long stimulus streams**. Both fit the substrate cleanly.

- **N-web interference is one graph.** The union of N webs + their cross-web
  *identifications* is a single graph; an **interface defect** is a holonomy
  defect on that union — a loop that crosses web boundaries and fails to close.
  `holonomy.py` is already graph-agnostic, so N webs is nearly free. An
  **interface** is a graph of identifications `A:x ↔ B:y` carrying a translation
  value (identity for same-count↔same-generation; a transport for
  successor↔generation-shift). Since webs are internally consistent chains,
  `interface_defect_mass = defect_mass(union)`.
- **Mismatch-minimizing map = alignment search** over candidate identifications
  minimizing union defect mass (bipartite for 2 webs, multi-web for N).
- **Transfer with zero shared parameters** flows through the interface *fabric*
  transitively (A→B→C): only graph edges carry the frozen algebra — no weights.
- **Dynamic webs = the number of webs is learned structure**, exactly like the
  number of classes in P1b but at the web level. Splits/merges are the existing
  moves, **persistence-gated over the stimulus stream** (P1's detector, sleep/
  dream phase, `scaling.md §6`): a web with a persistent undischargeable defect
  **splits**; two webs with a consistently-supported (k≥2) zero-defect
  identification **merge**. Over long stimuli the web count evolves.
- **Three resolutions** of an interface defect: *project* (trust one web —
  overwrite the interface value), *split* (bifurcate the shared node — the webs
  meant different things), *superpose* (keep both readings, weighted).
- This dynamic ensemble is also the substrate P8 (ensemble geometry) wants.

## 13. P5 implementation — notes (2026-07-09)

- **N-web interface = union holonomy, as designed (§12).** `ensemble.py` builds
  the union graph (all webs' edges + `iface` identification edges) and reads
  interface defects straight off `holonomy.defects`. `interface_defect_mass =
  defect_mass(union) - internal`. Confirmed on 3 webs (arith / kinship / steps).
- **Map search reuses the P2 consensus.** Each candidate identification implies
  an offset `coord(b) - coord(a)`; the modal offset is the interface map, and the
  poison (`a2 ↔ k4`, offset 2) falls out as the lone outlier. Committing the
  consistent map → 0 defect; adding the poison → mass 8; `split` → 0.
- **Transfer, zero shared parameters.** With the interface, the union's
  coordinates extend web A's reach through K and S: holdout answerability
  0.33 → 1.00. Nothing is shared but graph edges over the frozen algebra.
- **Dynamic ensemble works.** `stream_dynamics` gates merges (support ≥ k) and
  splits (contradiction persists ≥ P) over a stimulus stream; the web-group
  count evolves `3 → 2 → 1 → 2` — the number of webs is learned, exactly the
  P1b class-count idea lifted to the web level.
- Scope note: the dynamic model is web-group-level (union-find over web names)
  rather than full node-level bifurcation — enough to demonstrate the learned
  count over time; node-level split already exists (P1b / resolutions).
- e5 accepted (4 tests). `results/e5_interference.{csv,png}`.

## 14. P6 reflection — notes (2026-07-09)

- **No new machinery, as the dev-doc promised.** Invariant 4 already puts every
  act on the bus as a bare episode; `reflection.py` only *reads* them back.
- **(a) act-classes at purity 1.0.** Structural role refinement (the P2'
  refinement key: collection sizes + pairing arity + reflexivity) types the
  acts; each signature is one operation kind (add_edge (1,1,1), merge/rewire
  (2,1,1,reflexive), grow (2,1,0), walk-off-web (1,2,0)). The world parser
  (`number.derive`) consumes act episodes unchanged — homoiconicity, verified.
- **(b) the regress is potential, not actual.** `bounded_consume`: each
  consumption emits (emission never stops), but consumption is capped at the
  attention budget, so the backlog is finite. Matches `experiment0f` part 4.
- **(c) self-measurement.** The learner counts its own defect-report acts with
  the P1b chain: 1/2/3 defects → counted 1/2/3. The ruler it built measures the
  hand that built it.
- **A real subtlety surfaced (logged):** on a chain, asserting `0≡3` and `1≡4`
  is *one* independent defect, not two — `1≡4` is implied by the period-3 wrap.
  `defects()` correctly returned 1; the test fixture had to use *disjoint*
  regions for N genuinely-independent defects. Good confirmation that the defect
  count is the rank of the holonomy map, not the count of "wrong-looking edges."
- Accepted (4 tests). `results/e6_reflection.{csv,png}`.

## 15. P6' simulation & lookahead — notes (2026-07-09)

- **Pure seam, as promised.** `simulate.py` is fork (inv 5) + apply (inv 2) +
  score by holonomy (inv 8/9) + discard. No new primitive. `imagine_then_commit`
  commits only if defect mass does not rise; else it emits a `refuse` trace with
  the reason. `lookahead` scores candidates on forks and commits the least
  `(defect, size)` — 20/20 seeds pick the min-defect merge.
- **cf isolation is structural.** Simulations run on `fork()` (cf=True), so their
  traces are cf-flagged and `Journal.committed` never yields them; the learner
  counts its own simulations with the P1b chain (3 → 3).
- **Documented limit:** a *consistent* but false merge (two nodes with no
  distinguishing edge) has 0 defect, so simulation cannot refuse it — coherence
  is checkable, correspondence needs an independent source (the ensemble, P7).
- **Latent substrate bug found and fixed (important).** A `merge` was updating
  only the alias map, not the graph — so holonomy never saw a merge, and P1b's
  "class ONEMORE of itself" worked *only* because `number.project` re-resolved
  endpoints when adding edges. Fixed `Web._rebuild` to a **two-pass** rebuild:
  build the alias from all merge commits, then rebuild nodes/edges with
  endpoints resolved through it. Now a merge genuinely collapses the graph (an
  edge whose endpoints collapse becomes a self-loop = a holonomy defect), and
  P1b membership is recovered via `Web.all_node_ids()` (current + merged-away).
  All 57 prior tests still pass. This is the correct event-sourced merge.
- Accepted (5 tests). `results/e6p_simulate.{csv,png}`.

## 16. P7 adversarial audit — notes (2026-07-09)

- **The k>=2 provisional-commitment gate is the primary defense** (resolves the
  P1b deviation, invariant 6). Thinly-witnessed poison (1 episode) never enters
  the quotient, so purity stays 1.0 across the whole 0.1%–5% sweep with zero
  damage and zero collateral. This is cleaner than any recovery.
- **Localize-and-replay is the fallback** for lies that pass the gate. Greedy
  min-cut over deduped match-pairs, tie-broken by support (cut thinly-witnessed
  edges first). Recovers purity, but **honest finding logged**: with *many*
  independent poison bridges between the same two clusters the greedy is
  imprecise — removing a clean member reduces the contradiction count as much as
  cutting a bridge, so it over-cuts (collateral ≈ 30, the documented "price of
  recovery"). A true graph min-cut would be tighter; greedy is what `0h` uses
  and it suffices for single/coordinated lies. At ≤2% k=1 still reaches 1.0.
- **Repeat-lie is one cut.** Match evidence deduped by pair: the same false pair
  asserted 50× is a single edge to cut. Attacker pays 50, learner pays 1.
- **Consistent-lie cost curve = connectivity, exactly** (`consistent_lie_cost`
  measured on the real holonomy substrate — a false merge turns each independent
  A–B loop into a defect, so a coherent lie must out-fake every loop). Linear,
  slope 1: the denser the region, the more expensive the lie. The core security
  property. Note this is holonomy, not union-find (which sees only adjacent
  false merges).
- **DoS budgets** hold: split budget bounds fragmentation, growth budget bounds
  invention; the learner degrades to *refusal*, not corruption.
- **Documented limit:** a fully consistent lie (no contradicting loop) is
  undetectable to a single learner — coherence is checkable, correspondence
  needs the ensemble (P5). Ties to the P6' limit.
- Accepted (7 tests). `results/e7_adversarial.{csv,png}`.

## 17. P8 ensemble geometry — notes (2026-07-09)

- **Hypothesis confirmed.** Graph-Laplacian eigenmaps of each learner's
  relational graph (collections; MATCH clusters + ONEMORE chain) recover a
  **magnitude axis** — the Fiedler vector orders the size-classes. Per-run axis
  recovery |corr| ≈ 0.90 (the axis is real every run), but the **orientation is
  arbitrary** (Fiedler sign splits ~half/half across 24 runs).
- **Stable only across the aligned ensemble.** The *raw* ensemble mean washes
  out (spread 0.109, axis recovery 0.86 — the ± runs cancel). The *sign-aligned*
  ensemble mean is a clean monotonic magnitude axis (spread 0.046, recovery
  0.93). So the concept geometry stabilizes across the ensemble even though it
  varies per run — exactly the P8 hypothesis. `results/e8_geometry.{csv,png}`.
- Embarrassingly parallel, pure numpy (`np.linalg.eigh`), CPU. No new substrate.
- This sits on P5's ensemble idea and closes the roadmap.
- Accepted (3 tests).

## 18. Log

- **2026-07-09** — P0 (original holonomy kernel) committed `9b75123`.
- **2026-07-09** — Doc revised (invariants 4–8, P1b, P6/P6'/P7/P8; new
  reference experiments `0e`–`0i`). Feedback given; decisions §2 taken.
- **2026-07-09** — `scaling.md` written (distribution/web-scale/volunteer).
- **2026-07-09** — P0 re-founded on event-sourced substrate committed
  `7944776` (`episode.py`, `journal.py`, `web.py` as projection; 22 tests).
- **2026-07-09** — This design log created.
- **2026-07-09** — P1 growth engine: `web.walk`, `growth.py`,
  `datasets/arithmetic.py`, `experiments/e1_growth.py`; e1 accepted (27 tests).
- **2026-07-09** — P1b number-from-counting: `datasets/counting.py`,
  `number.py`, `experiments/e1b_number.py`; e1b accepted (32 tests). MATCH=merge
  resolved; contradiction = holonomy self-loop; poison retractable by replay.
- **2026-07-09** — P2 symmetry-sector inference: `datasets/sectors.py`,
  `sectors.py`, `experiments/e2_sectors.py`; e2 accepted (36 tests). same→sym,
  succ→antisym, double→motif; noise-tolerant; consumes the P1b chain.
- **2026-07-09** — P2' unlabeled type discovery: `datasets/bare.py`, `types.py`,
  `experiments/e2p_types.py`; accepted (40 tests). Refinement over-refines,
  disjointness compression recovers types at purity 1.0; conflation-vs-coverage
  curve logged.
- **2026-07-09** — P3 compositional holdout: `datasets/holdout.py`,
  `baselines/kge.py`, `holdout.py`, `experiments/e3_holdout.py`; e3 accepted
  (43 tests). web Hits@1=1.0 by construction; ComplEx 0.49, TransE 0.15 — gap
  recorded. numpy baselines (Adam inline).
- **2026-07-09** — P4 algebra sweep: finite involutive monoids in `algebra.py`,
  `sweep.py`, `experiments/e4_sweep.py`; e4 accepted (49 tests). Frozen Algebra
  ABC held with zero substrate changes; frontier = {Z, InvMon_3}; relabel-
  invariance extended to every algebra.
- **2026-07-09** — P5 N-web dynamic ensemble: `ensemble.py`,
  `datasets/kinship.py`, `experiments/e5_interference.py`; e5 accepted (53
  tests). N-web interface via union holonomy; consensus map finds/isolates
  poison; transfer 0.33→1.0 zero-shared-params; web count evolves 3→2→1→2.
- **2026-07-09** — P6 reflection: `reflection.py`,
  `experiments/e6_reflection.py`; accepted (57 tests). Act-classes crystallize
  at purity 1.0 (unchanged machinery); attention budget bounds the regress;
  learner counts its own defect-reports with the P1b chain.
- **2026-07-09** — P6' simulation & lookahead: `simulate.py`,
  `experiments/e6p_simulate.py`; e6' accepted (62 tests). Fork-score-discard
  play loop; refuse-with-reason; lookahead 20/20; cf never in committed. Fixed a
  latent merge-semantics bug (two-pass `_rebuild`; `all_node_ids`).
- **2026-07-09** — P7 adversarial audit: `audit.py`,
  `experiments/e7_adversarial.py`; e7 accepted (69 tests). k>=2 gate keeps purity
  1.0 across the sweep; localize-and-replay recovery (collateral logged);
  repeat-lie = 1 cut; consistent-lie cost = connectivity (linear); DoS budgets;
  k>=2 deviation from P1b resolved.
- **2026-07-09** — P8 ensemble geometry (stretch): `geometry.py`,
  `experiments/e8_geometry.py`; accepted (72 tests). Magnitude axis recovered per
  run, orientation arbitrary; stable only across the sign-aligned ensemble.
  **Roadmap P0–P8 complete.**
