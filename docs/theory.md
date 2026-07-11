# Theory — the technical tour

*This document assumes mathematical maturity but not familiarity with any
particular field: every concept is defined where it first appears, with
references for deeper reading. The [plain-language tour](how-it-works.md)
covers the same system without the formalism; [dev-doc.md](dev-doc.md) is the
original build spec with the architecture invariants; [design-log.md](design-log.md)
records every decision. File references point into `src/relweblearner/`.*

---

## 1. The design stance

Contemporary machine learning stores knowledge in the parameters of a
differentiable function and learns by gradient descent on a loss. This system
stores knowledge in the **topology of a labelled graph** and learns by
**discrete, audited edits** to that graph. The split is absolute and enforced:

- The **algebra** — the value set that edge labels live in, with its
  composition law — is *frozen*: written once in code
  ([`algebra.py`](../src/relweblearner/algebra.py)), never modified by
  learning, carrying no learned parameters.
- The **web** — which nodes exist and how they are wired — is the *only*
  degree of freedom.

The freeze is what makes contradiction *objective*: were the composition law
itself learnable, any defect could be absorbed by deforming the algebra —
bending the ruler instead of fixing the map — whereas a frozen algebra forces
every repair into the observable topology, where it can be audited, costed,
and refused. Everything else in the project is a consequence of taking that
split seriously: a gauge-theoretic notion of contradiction (§3), an
event-sourced notion of memory (§5), an evidential notion of belief (§6), and
a growth-based notion of concept formation (§8).

## 2. The objects

**Episode.** The atomic experience, deliberately impoverished: two collections
of opaque ids plus a partial pairing between them
([`episode.py`](../src/relweblearner/episode.py)). Sentences, worksheet
answers, and the learner's own internal acts are all rendered in this one
format ("homoiconicity" — code-as-data in the Lisp sense
\[[Wikipedia](https://en.wikipedia.org/wiki/Homoiconicity)\], here
acts-as-experience). Nothing in the input stream is ever a numeral, and no
relation is ever named by a label.

**Web.** A directed graph W = (V, E) with opaque node ids (no attributes — an
important discipline, see §11) where each edge carries a value g(u,v) from the
algebra, and each edge has a converse edge carrying the involuted value.

**Algebra.** A set A with an associative composition (possibly *partial*), a
two-sided identity e, an involution a ↦ a† satisfying (a†)† = a and
(ab)† = b†a†, and a norm ‖a‖ ≥ 0 vanishing exactly at e. In semigroup
language: an **involutive monoid**, with the partial-composition variants
being **inverse semigroups**
\[[Wikipedia](https://en.wikipedia.org/wiki/Inverse_semigroup); Lawson,
*Inverse Semigroups: The Theory of Partial Symmetries*, 1998\]. The default
carrier is (ℤ, +, 0, −, |·|); the P4 phase swaps in ℤ₂, ℤ₄, the Klein group,
and a symmetric inverse monoid behind the same interface and measures the
trade-off (bloat vs. hallucinated inverses) each induces.

## 3. Holonomy: contradiction as curvature

Assigning an algebra value to each directed edge of a graph is, in the
language of differential geometry, a discrete **connection**; composing the
values along a path is **parallel transport**; and the transport around a
closed loop is the loop's **holonomy**
\[[Wikipedia](https://en.wikipedia.org/wiki/Holonomy); for the smooth story,
Baez & Muniain, *Gauge Fields, Knots and Gravity*, 1994\]. The same structure
on a lattice is the starting point of lattice gauge theory
\[[Wikipedia](https://en.wikipedia.org/wiki/Lattice_gauge_theory); Wilson,
*Confinement of quarks*, Phys. Rev. D 10, 1974\].

The system's central definitions:

- A loop is **consistent** if its holonomy is the identity (sums to 0 over ℤ).
- A **defect** is a loop with non-identity holonomy. Defects are the *only*
  learning signal (invariant #9), and their total norm — the **defect mass** —
  is the objective that learning must not increase.

**Gauge invariance as a correctness discipline.** A **relabeling** is a map
φ: V → A applied as g(u,v) ↦ φ(u) · g(u,v) · φ(v)†. This is precisely a gauge
transformation, and a two-line computation shows it changes no loop's
holonomy. The design declares relabelings *meaningless* (a change of
bookkeeping), so every quantity the learner computes must be
relabeling-invariant — pinned by a 1000-trial property test that has caught
real bugs. For the abelian case there is a tidy cohomological reading: edge
labels form a 1-cochain, relabelings are exactly the coboundaries, so defects
detect a nonzero class in the first cohomology of the graph with coefficients
in A \[[Wikipedia](https://en.wikipedia.org/wiki/Graph_homology); Sunada,
*Topological Crystallography*, 2013\].

**Computing the signal** ([`holonomy.py`](../src/relweblearner/holonomy.py)).
Fix a spanning forest and set a potential φ by BFS (φ(root) = e,
φ(v) = φ(u)·g along tree edges) — a spanning-tree gauge fixing. Every non-tree
edge then closes exactly one **fundamental cycle**, and its residual mismatch
*is* that cycle's holonomy; the fundamental cycles form a basis of the graph's
**cycle space** \[[Wikipedia](https://en.wikipedia.org/wiki/Cycle_space)\], so
the non-tree residuals enumerate the independent defect classes in O(E).

## 4. Learning as costed repair

Observations (loop-closure and distinctness assertions) are immutable; the
learner may never delete one to escape a defect. Its full repertoire is three
moves with a fixed price ordering
([`web.py`](../src/relweblearner/web.py), invariant #2):

1. **relabel** — cost 0, provably cannot fix a defect (§3); tried first
   *because* its futility is what certifies that a real fix changed something
   real.
2. **rewire** — cost 1: add/remove/merge edges among existing nodes, subject
   to contradicting no observation.
3. **grow** — cost K ≫ 1: mint new nodes. Gated on *persistence* (the
   obstruction must survive rounds of cheaper attempts), minimal (the fewest
   nodes that discharge it), and budgeted (exhaustion degrades to refusal,
   not fabrication) — [`growth.py`](../src/relweblearner/growth.py).

The cost schedule is a crude but effective description-length prior — the
minimum-description-length idea that a model earns complexity only by paying
for it in explained data \[[Wikipedia](https://en.wikipedia.org/wiki/Minimum_description_length);
Rissanen 1978; Grünwald, *The MDL Principle*, 2007\].

Consequential moves are additionally **simulated before commitment**
(invariant #8, [`simulate.py`](../src/relweblearner/simulate.py)): the
candidate is applied to a *fork* of the projection (cheap, because state is a
projection of a log — §5), scored by defect mass, and committed only if the
score clears policy. Refusals are logged with reasons ("rehearsal-refusal").
Simulated acts emit traces flagged counterfactual — imagining is on the
record, but never in belief.

## 5. Memory: event sourcing, replay, and retraction

State management follows **event sourcing**: the append-only episode log is
the sole source of truth, and every belief structure is a **projection** of it
\[[Fowler, *Event Sourcing*](https://martinfowler.com/eaaDev/EventSourcing.html);
cf. CQRS\]. Concretely
([`episodelog.py`](../src/relweblearner/episodelog.py), invariant #5):

- **Write-ahead:** `observe()` appends to the log *before* distilling into the
  web; the distilled creature is a *checkpoint* of a replay (load = checkpoint
  + tail replay).
- **Reproducibility:** `rebuild()` re-derives the whole model by replaying
  from zero.
- **Retraction = replay-with-exclusions:** entries are *flagged* excluded,
  never deleted, and the model is rebuilt as if they had never happened. This
  gives exact, claim-granular unlearning — `retract_claim("owl","four")`
  finds every episode that parses to that oriented fact under current frames
  and excludes precisely those.

A cheaper aggregate-level path also exists: per-edge provenance is a map
source → count, so belief is a sum of separable per-source summands and a
whole source can be retracted by *decrement* — a join-semilattice/CRDT-style
design \[Shapiro et al., *Conflict-free Replicated Data Types*, SSS 2011,
[inria-00609399](https://hal.inria.fr/inria-00609399)\]. The log remains
ground truth; the decrement is the fast path.

The closest classical relatives of this whole apparatus are
**truth-maintenance systems**, which also store justifications and retract by
removing support \[Doyle, *A Truth Maintenance System*, AIJ 1979; de Kleer,
*An Assumption-based TMS*, AIJ 1986\] — here reconstructed on an immutable log
so that retraction is a *replay*, not an in-place mutation.

## 6. Belief: witnesses, weights, and learned trust

**Commitment** (invariant #6). A parsed claim becomes an edge immediately but
is only *believed* — used in transport, taught onward, shown as fact — when
its support clears a threshold. Originally: ≥ k distinct sources (default
k = 2), which already blocks single-source lies and makes a thousand
repetitions by one gossip count once.

**Trust** ([`trust.py`](../src/relweblearner/trust.py)) upgrades counting to
weighing. For each (source, relation class) pair, define a track record:
*good* = distinct standing facts of that source independently corroborated in
that class; *bad* = its distinct facts among the log's excluded episodes
(i.e., testimony that lost an adjudication — §7). The witness weight is

```
w = (1 + good) / (1 + good + p · bad)        p = distrust_penalty (default 3)
```

— a Laplace-style smoothed ratio (cf. the [rule of
succession](https://en.wikipedia.org/wiki/Rule_of_succession)) in the spirit
of Beta-distribution reputation systems \[Jøsang & Ismail, *The Beta
Reputation System*, Bled eCommerce 2002; Jøsang, *Subjective Logic*, 2016\],
with lies costing p× what truths earn. A fresh source has w = 1 (recovering
the old counting rule exactly); a caught source needs extra corroboration *in
the class where it was caught* and nowhere else; and a source with
`authority_k` clean corroborated facts in a class earns w = commit_k there —
sole-witness commitment, forfeited by a single caught lie. An edge commits
when Σ w over its sources ≥ commit_k. Trust is itself a projection of
store + log — reproducible by replay, never checkpointed.

Two reserved *fiat* namespaces sit outside reputation: `act:*` (the learner's
own gated moves, invariant #7 — external episodes claiming it are rejected)
and `correction*` (the owner's voice, §7). Both carry weight commit_k by
construction and can neither earn nor lose standing.

## 7. Revision: how it changes its mind

Classical belief-revision theory (AGM) axiomatizes how a belief *set* should
contract and revise \[Alchourrón, Gärdenfors & Makinson, *On the Logic of
Theory Change*, JSL 1985;
[SEP entry](https://plato.stanford.edu/entries/logic-belief-revision/)\].
This system takes a different, evidence-first route: beliefs are never edited;
*evidence* is adjudicated, and beliefs follow by replay.

A **conflict** is a source concept holding ≥ 2 committed targets in a relation
class that is otherwise *functional* — single-valued for ≥ `agree_threshold`
of its subjects, judged on **raw testimony** rather than committed coverage
(thin corroboration must not make a genuinely many-valued relation like
taxonomy look single-valued). `Creature.revise()` runs in every ingest and:

- **Adjudicates only when a decree is party.** Fiat outranks testimony; a
  later fiat outranks an earlier one (log order). The losing side's episodes
  are excluded with the verdict recorded as the reason, the model rebuilt, and
  the losing sources take the bad marks that drive §6's weights. Because this
  runs on every ingest, corrections *defend themselves* against recidivist
  testimony.
- **Never lets testimony erase testimony.** This is an empirical scar, not an
  aesthetic: a margin rule ("majority outvotes minority") was dry-run on the
  real trained creature and promptly deleted *hen → bird* — 414 true episodes
  — because one corpus said "bird", another said "female", and both were
  simply true. Corroborated dissent is kept, reported, and displayed as an
  open defect until a teacher settles it or one camp's credibility erodes.

A **correction** (`correct(src, wrong, right)`) is therefore *teaching*: one
honest fiat episode asserting the right fact through a frame of the wrong
fact's own relation, after which the creature's own conflict machinery does
the retraction and the blame. The surgical instrument (`retract_claim`)
remains for testimony with no better fact to teach.

## 8. Number, invented

The number construction implements, almost literally, the logicist idea that
number is what equinumerous collections share — **Hume's principle**: the
number of F's equals the number of G's iff F ≈ G (bijection)
\[[SEP: Frege's theorem](https://plato.stanford.edu/entries/frege-theorem/)\].

From bare pairing episodes ([`number.py`](../src/relweblearner/number.py)) the
learner derives MATCH (pairing saturates both collections) or ONEMORE (exactly
one leftover) — *derived, never given*. MATCH-classes are merged via
union-find (the quotient by equinumerosity); ONEMORE installs a +1 edge
between classes. The emergent quotient classes, chained by +1, **are** the
numbers — a Peano-style successor structure
\[[Wikipedia](https://en.wikipedia.org/wiki/Peano_axioms)\] built from
experience. Numerals attach later by **ostension** (a tapped word naming a
pile the creature has itself counted), and the map between the word chain and
the constructed chain is found by mismatch-minimizing search over the chain's
sign gauge (x ↦ −x is a ℤ-automorphism, so orientation is genuinely
underdetermined — the search must decide it).

Arithmetic is transport (walk the chain); *negative numbers are grown* when a
subtraction walks off the end and the P1 engine mints the missing nodes.
And a persistent defect that **contradicts no observation** is reclassified
as *content* rather than error ([`invention.py`](../src/relweblearner/invention.py)):
a counting chain glued to a wrap-around observation carries holonomy +12 —
which is not a mistake but the discovery of ℤ/12ℤ, banked and thereafter used
to answer modular queries. The error/content boundary is exactly "is an
observation violated?".

## 9. Relations: sectors, transport, and zero-parameter composition

Relations are not labelled; they are discovered as equivalence classes of
frames (§10) and then *typed by their transport*
([`sectors.py`](../src/relweblearner/sectors.py),
[`transport.py`](../src/relweblearner/transport.py)). Using coordinates from
the number chain, each relation class gets fitted with a constant transport g:
g = 0 → symmetric (its own converse); g ≠ 0 → antisymmetric converse pair
("comes after"/"is before" resolve to ±1); no constant fit → unconstrained
attribute relation (color, diet), which supports no derivation. Committed
facts project into algebra-valued webs per **gauge group** (mutually
ungauged), and a never-taught question is answered by **transport
composition**: taught n —(+k)→ n+k for k ∈ {1,2}, the composite +5 answers all
held-out k = 5 questions exactly.

That yields the project's headline sample-efficiency comparison: on the same
compositional holdout, the web scores Hits@1 = 1.0 with zero parameters, while
trained knowledge-graph-embedding baselines — TransE \[Bordes et al., NeurIPS
2013\] and ComplEx \[Trouillon et al., ICML 2016,
[arXiv:1606.06357](https://arxiv.org/abs/1606.06357)\] — memorize training
perfectly yet compose the held-out relation at Hits@1 ≈ 0.15 and 0.49. Exact
composition is what the frozen algebra buys.

## 10. Motifs: learned concepts as words over edges

Invariant #1 forbids learned algebra operations, so learned concepts are
**motifs**: composite relations defined as words over existing edge types
(e.g. same-color(x,y) := ∃c. has-color(x,c) ∧ has-color(y,c)). The
implemented family ([`motif.py`](../src/relweblearner/motif.py)) is
inheritance, rel(x,z) ⊇ via(x,y) ∘ rel(y,z) — with via = *kind-of* this is
property inheritance (hen → bird → two legs), with via = rel it is
transitivity. Candidate rules are scored on committed testimony only: a
composite path whose head also carries direct testimony is a witness (agrees)
or violation (disagrees); heads with no direct testimony are *silent* — they
are the cases the rule would answer, so letting them vote would be the rule
voting for itself. Commit at ≥ k witnesses and support ≥ 1 − ε. The violation
test deliberately errs conservative on multi-valued relations, which is why
taxonomic transitivity — though true — stays refused: honest under-commitment
over silent self-confirmation. Nothing is ever reified: motif answers are
computed at query time and evaporate with the projection, so a taught fact
always overrides an inherited one.

## 11. Language: from syllables to grounded frames

Language is a **separate web, one-way dependent** on the concept web — a
skill atop concepts, deletable without disturbing them
([`language.py`](../src/relweblearner/language.py),
[`curriculum.py`](../src/relweblearner/curriculum.py)). The pipeline, each
stage with an acceptance test:

- **Segmentation** of a raw syllable stream at transition-probability dips —
  the statistical-learning result from infant studies \[Saffran, Aslin &
  Newport, *Statistical Learning by 8-Month-Old Infants*, Science 274, 1996\].
- **Frame induction**: captions grouped by shape; a token position becomes an
  anchor when one word dominates it (≥ 0.8), else a slot; non-matching
  captions are *rejected to a frontier* rather than force-fitted, and a
  swelling frontier triggers induction of the next frame — the same
  obstruction→growth rhythm as §4. (Skipping the rejection discipline
  reproducibly over-generalizes to an all-slot skeleton; that failure mode is
  kept in CI.)
- **Grounding by structure alone**: matching the language web to the concept
  web by joint structural refinement (in the spirit of Weisfeiler–Leman
  refinement \[[Wikipedia](https://en.wikipedia.org/wiki/Weisfeiler_Leman_graph_isomorphism_test)\])
  resolves word meanings **exactly up to the concept web's automorphism
  orbits** — a formal version of Quine's *gavagai* indeterminacy \[Quine,
  *Word and Object*, 1960\]. The residue is discharged by **ostension**
  (pointing), with the required budget provably = the number of orbits.
- **Reading and writing** as adjoint maps, with write followed by read-back
  before commitment (`read(write(f)) = f` holding at zero violations). Note
  the design decision this encodes: reading and writing are *not* separate
  webs but the two directions of one interface over one language web —
  writing is *defined* as the inverse map followed by reading one's own
  draft, so the adjunction laws are checkable at all. What the spec does
  allow in the plural is *languages*: several word-webs may interface the
  same concept web, which is the structural model of bilingualism (and a
  second language's frames would unify with the first's across the shared
  edge sets by the ordinary §9 machinery — cross-language synonymy as
  paraphrase).

Oriented facts come from the **picture channel**: a tap marks which slot the
illustration grounds, so token order never has to be trusted — which is what
lets real WordNet/Wikidata facts be rendered through several paraphrase
constructions (including argument-reversed ones) with the relation identity
left for unification to *discover* (§9), the stripped label surviving only as
the worksheet answer key.

**An honest bend in the streaming creature.** The phase implementation
enforces the one-way dependency by CI (delete language, concept tests pass;
disjoint namespaces). The streaming creature keeps the *behavioural*
discipline — frames are a separate bounded structure, `_draft_fact` does the
L6 read-back — but its concept edges carry frame ids as their relation-type
markers, a reference from the concept layer into language that the spec's
ideal forbids. The reason is stated in the roadmap: with no non-linguistic
perception channel yet (the planned P9), language is the creature's *only*
source of relations, so frames stand in for the relation types that P2′-style
discovery should eventually supply. A bend pending P9, not a silent drift.

### 11½. Many webs

"The web" is a convenient singular; the architecture is plural at four
levels, and the plurality is load-bearing:

- **Language vs concepts** — the one-way split above; several language webs
  per concept web is bilingualism for free.
- **Concept webs per gauge group** ([`transport.py`](../src/relweblearner/transport.py)):
  committed facts project into one valued web per *constraint group* of
  interlocking relation classes, and the groups are **mutually ungauged**
  (P4′) — no potential is shared across them, so no relabeling in one can
  disguise or create a defect in another. Error stays local by construction.
  This partition is the streaming creature's dynamism: it is a projection,
  re-inferred whenever the committed geometry changes, so a newly committed
  converse link *merges* two webs and a retraction that breaks one *splits*
  them — the web count is a consequence of evidence, never a parameter (the
  trained scholar currently runs 16).
- **The dynamic ensemble** ([`ensemble.py`](../src/relweblearner/ensemble.py)):
  N webs plus cross-web *identifications* form one union graph on which an
  interface mismatch is just another holonomy defect; transfer flows through
  the identifications with zero shared parameters, a poisoned identification
  is isolated by consensus and resolved by *split* — and under a stimulus
  stream the **number of webs is itself learned** (persistence-gated merges
  and splits evolved the count 3 → 2 → 1 → 2 in the acceptance run). Honest
  scope note: this machinery is accepted phase code the streaming creature
  does not yet wire in — its within-mind identification decisions are played
  by relation unification (fork-simulated, §4), and its dynamism by the
  gauge-group reprojection above; explicit identification edges *between* a
  creature's webs remain a stated seam (natural once P9 perception gives a
  second, non-linguistic web to identify against).
- **One web per agent** (§13): the society layer is an ensemble whose
  members share no memory at all; agreement across webs is the system's only
  correspondence signal.

## 12. Reflection and simulation

Because every operation emits a trace episode in the world-episode format
(invariant #4 — "no silent operations"), reflection needs no new machinery:
the learner runs its own act stream through the ordinary pipeline
([`reflection.py`](../src/relweblearner/reflection.py)) — act-classes
crystallize by the same structural type discovery used for relations, an
attention budget bounds the regress (emission free and unconditional,
consumption budgeted, backlog finite), and the learner counts its own defect
reports with the number chain it built in §8. Self-measurement with its own
ruler.

## 13. Society: where truth comes from

A single agent can verify **coherence** (defects) but not **correspondence**:
a fully consistent lie is invisible from the inside — proved as a limit in the
adversarial phase. The society layer
([`society.py`](../src/relweblearner/society.py)) supplies the missing signal
by making *disagreement between agents* observable:

- **Naming games with lateral inhibition** converge a dyad (then a population)
  to a shared lexicon \[Steels, *A self-organizing spatial vocabulary*,
  Artificial Life 2(3), 1995; the field's survey literature under "naming
  game"\], and *peer ostension* discharges the solipsism debt left by §11's
  orbit indeterminacy.
- **Citation-tracked gossip**: every claim travels with its origin set;
  commitment requires ≥ k *distinct origins*. A rumor (one owner, thousands of
  retellings) commits nothing; ten Sybil identities under one owner count as
  one — the classic Sybil-attack boundary drawn at provenance \[Douceur, *The
  Sybil Attack*, IPTPS 2002\].
- **Dialects** form in isolated populations and creolize on contact only with
  inhibition enabled; conflicting claims persist as queryable interface
  defects resolved by origin weight, with own perception outranking testimony.

The per-domain trust of §6 is this layer's within-agent shadow: sources today
are books; tomorrow they are peers.

## 14. Geometry: what the mind looks like

For inspection (never for inference), the concept web is embedded by spectral
methods: graph-Laplacian eigenmaps \[Belkin & Niyogi, *Laplacian Eigenmaps for
Dimensionality Reduction*, Neural Computation 15(6), 2003\] and classical
multidimensional scaling over shortest-path relational distance
\[[Wikipedia](https://en.wikipedia.org/wiki/Multidimensional_scaling)\]. A
robust finding: each learner's Fiedler vector recovers a magnitude axis (the
numbers order themselves along it), but its *orientation* is arbitrary per
learner — only the sign-aligned ensemble has stable geometry, echoing §13's
moral that structure is objective, coordinates are not.

## 15. The invariants, compactly

The architecture is governed by nine invariants (full text in
[dev-doc.md](dev-doc.md) §1); the one-line versions:

1. The algebra is frozen; no learned parameters on edges, ever.
2. Only the web mutates, via relabel/rewire/grow with fixed costs.
3. Observations are loop-closure and distinctness assertions only.
4. No silent operations: every act emits a trace episode on the shared bus.
5. Belief/data separation: the log is immutable; all belief is a replayable
   projection; retraction is replay-with-exclusions.
6. Commitment discipline: k independent witnesses, now trust-weighted (§6);
   contradictions are localized and excluded, collateral reported.
7. Bus provenance: the act namespace is the learner's alone.
8. Simulate before committing consequential moves.
9. The learning signal is defect persistence.

## 16. Honest limits

- **Coherence ≠ correspondence.** A consistent lie has zero defect mass; only
  the ensemble/society can catch it.
- **Collusion-until-caught.** Trust's good marks are corroboration, and a
  colluding corroborated majority *is* the record until one member is caught.
- **Statistical indistinguishability of dissent.** Two corroborated camps
  disagreeing cannot be told from two truths (§7's hen); the system refuses to
  guess, by design.
- **Scale.** The trace bus is in-RAM and O(experience); the geometry views are
  O(edges); SQLite/sharded edge stores and file-backed logs are the stated
  seams (see [scale-substrate.md](scale-substrate.md), [scaling.md](scaling.md)).
- **Closed world.** The creature knows its curriculum, speaks its induced
  frames, and nothing else.

## 17. Reading list

Gauge/holonomy: Baez & Muniain, *Gauge Fields, Knots and Gravity* (1994);
[Lattice gauge theory](https://en.wikipedia.org/wiki/Lattice_gauge_theory);
Sunada, *Topological Crystallography* (2013).
Graphs: [Cycle space](https://en.wikipedia.org/wiki/Cycle_space);
[Weisfeiler–Leman](https://en.wikipedia.org/wiki/Weisfeiler_Leman_graph_isomorphism_test).
Semigroups: Lawson, *Inverse Semigroups* (1998).
Memory: [Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html);
Shapiro et al., CRDTs (2011); Doyle, TMS (1979); de Kleer, ATMS (1986).
Belief & trust: AGM (1985) and the
[SEP belief-revision entry](https://plato.stanford.edu/entries/logic-belief-revision/);
Jøsang & Ismail, Beta Reputation (2002);
[Rule of succession](https://en.wikipedia.org/wiki/Rule_of_succession).
Number & meaning: [Frege's theorem / Hume's principle](https://plato.stanford.edu/entries/frege-theorem/);
[Peano axioms](https://en.wikipedia.org/wiki/Peano_axioms); Quine, *Word and
Object* (1960); Saffran, Aslin & Newport, Science 274 (1996).
Baselines: Bordes et al., TransE (NeurIPS 2013); Trouillon et al., ComplEx
([arXiv:1606.06357](https://arxiv.org/abs/1606.06357)).
Complexity prior: [MDL](https://en.wikipedia.org/wiki/Minimum_description_length);
Grünwald (2007).
Society: Steels, naming games (Artificial Life, 1995); Douceur, *The Sybil
Attack* (IPTPS 2002).
Geometry: Belkin & Niyogi, Laplacian Eigenmaps (2003);
[MDS](https://en.wikipedia.org/wiki/Multidimensional_scaling).
