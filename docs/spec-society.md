# SPEC — Society (multi-agent layer)

Standalone spec, next after P0-P8 + the reading/writing spec. Self-
contained given the DEVDOC and SPEC_READWRITE glossaries. Reference
implementations: experiment0l_dyad.py (dyads), experiment0m_zoo.py
(population), experiment0k_invention.py (the P7 amendment, Section 7).
All acceptance numbers below were produced by those runs.

## 0. Why this layer, and why now

Three facts force multi-agent before perception-at-scale:

1. THE GROUNDING THEOREM (SPEC_READWRITE L3): a solitary learner resolves
   word meanings only up to the automorphism orbits of its concept web.
   The residue is provably closed to solo experience; only ostension
   from a peer discharges it. The orbit census is the "solipsism debt,"
   and this layer pays it.
2. COHERENCE != CORRESPONDENCE: a single learner can detect incoherence,
   never non-correspondence. A false belief consistent with an agent's
   own episodes is internally undetectable forever. Disagreement between
   two coherent agents is the ONLY native truth signal the architecture
   has. Perception-at-scale (which feeds claims, not ground truth) is
   unsafe without this channel.
3. ENSEMBLE SCIENCE: several planned measurements are properties of a
   population of independently-grown webs, not of any single web. The
   society is the instrument.

## 1. S0 — Agent containerization

An AGENT = (concept webs, language web, episode log, bus, id). Agents
share NO memory; all interaction is message-passing of episodes and
utterances. Each agent has an OWNER id (the human or process that
teaches it). CRITICAL: provenance identity is per-OWNER, not per-agent
(Section 4, sybil defense). CI: two agents in one process must produce
bit-identical behavior to two agents on separate machines given the
same message transcript.

## 2. S1 — Dyad protocol (naming games with lateral inhibition)

Repeated rounds: speaker picks a concept, utters its word (coining via
SPEC_READWRITE if it has none) with joint attention (ostension tagging
BOTH sides); listener adopts on failure.
REQUIRED FIX (found in the reference run): adopt-on-failure alone
plateaus (global agreement stalled at 0.36 in the population run
because synonyms churn forever). Implement LATERAL INHIBITION: on a
successful round, both parties prune competing synonyms for that
concept. Convergence to 1.0 is the acceptance bar BECAUSE of this fix;
without it the bar is unreachable.
**Accept (S1):**

- dyad communication success reaches 1.00 and lexicons are identical
  (reference: 0.86 in the first 80 rounds, 1.00 thereafter);
- solipsism debt: initialize two agents whose concept webs contain
  nontrivial automorphism orbits; after mutual-ostension play, the
  orbit census reaches 0 with exactly #orbits pointing events per agent;
- cross-agent adjunction: read_B(write_A(fact)) == fact over the full
  expressible set (reference: PASS on all facts).

## 3. S2 — Teaching (agents as sources)

An utterance from agent A, read by agent B, becomes an ordinary episode
in B's log with source = A's owner-chain (Section 4). It enters B's
commitment policy like any evidence: single-witness = provisional,
k-threshold to commit, retractable by replay. Agents may teach each
other facts the listener has never perceived.
**Accept (S2):** a fact taught (not perceived) commits at the same
thresholds, carries source provenance, and is retracted correctly if it
later conflicts (P7 machinery unchanged).

## 4. S3 — Citation-tracked gossip (the immune system)

Every fact-claim carries an ORIGIN SET: the owner ids where it entered
the population. Retellings transmit the origin set UNCHANGED -- an agent
relaying a fact adds nothing to its citations. Commitment requires >= k
DISTINCT ORIGINS (default 3).
Consequences to verify (reference run, 24 agents):

- a false fact taught 50 times by one owner and gossiped for 4000
  rounds: committed by 24/24 agents under naive hearing-counts, by
  0/24 under origin-counting;
- a true fact taught once each by six owners: committed by 24/24 under
  origin-counting.
  A rumor is loud but cites itself; independent teaching accumulates
  citations. This is the single-agent repeat-lie defense socialized.
  SYBIL DEFENSE: origins are owner ids, and owner identity must be
  Sybil-resistant at the deployment boundary (accounts, rate limits --
  out of scope here, but the counting code must assume one human can
  control many agents: N agents under one owner = ONE origin).
  **Accept (S3):** the reference numbers reproduce (0/N false, N/N true);
  a sybil test with 10 agents under one owner still yields origin
  count 1.

## 5. S4 — Population dynamics

Agents on a social graph, games with neighbors only.
**Accept (S4):**

- dialects: two communities converge internally with cross-community
  agreement ~0 (reference: 0.53/0.53 within, 0.00 across);
- creolization: opening contact drives global agreement to >= 0.95
  (with lateral inhibition; the 0.36 plateau of the reference run is
  the failure mode being tested against);
- diffusion: log per-fact adoption curves across the graph; verify
  cited facts diffuse and rumors saturate exposure without commitment.

## 6. S5 — Disagreement protocol & ensemble science

When agent B reads a claim conflicting with a committed belief:
(1) B does NOT adopt or retract immediately; (2) B records an
INTERFACE DEFECT with both origin sets; (3) resolution follows origin
weight and, where available, B's own perceptual episodes (perception
outranks testimony about one's own log); (4) unresolved defects are
queryable -- "what do I disagree with X about" is a first-class query.
Ensemble measurements (the science this layer exists to enable):

- spectral embeddings across the population: does concept geometry
  stabilize over the ensemble where it varies per-agent;
- invention census (Section 7 classes) across agents;
- lexicon/diffusion statistics as standing metrics.
  **Accept (S5):** the false-belief scenario (one agent misperceives;
  peer utterance exposes it) reproduces: internal detection impossible,
  interface detection immediate; the disagreement is logged, queryable,
  and resolved by origin weight.

## 7. AMENDMENT to P7 (content vs error defects) — REQUIRED

The P7 rule "persistent defect -> localize and retract" is INCOMPLETE.
Discovered in experiment0k_invention.py: a persistent holonomy class
that contradicts ZERO observations is not an error but CONTENT (the
run's example: gluing a counting chain to a wrap-around observation
yields a loop with winding +12 that conflicts with nothing and
correctly predicts never-observed facts like 11+3=2; retraction would
destroy modular arithmetic).
Amended rule:

- persistent class WITH observation conflicts -> error: localize,
  retract (P7 unchanged);
- persistent class with NO observation conflicts -> content: BANK it
  (reify as structure), and log it in the invention census.
  Invention census entries also include posit-before-evidence events
  (entities grown from closure requirements before any witnessing
  episode, later confirmed or refuted -- track the confirmation rate).
  **Accept (P7'):** the clock-arithmetic construction survives defect
  handling and answers modular queries; the poisoned-merge cases from the
  original P7 suite still retract. Both in one test run.

## 8. Metrics

- dyad convergence curves; orbit census over time (solipsism debt)
- adjunction violation rate across agent pairs (must be 0)
- origin-count distributions per fact; rumor exposure vs commitment
- dialect agreement matrices; creolization curves
- interface-defect census: open, resolved, resolution method
- invention census: banked content classes, posit confirmation rate

## 9. Known limits (state, do not hide)

- Citations gate COMMITMENT, not EXPOSURE: agents still hear and can
  repeat uncommitted claims. Utterance-level policy is a deployment
  concern this spec does not solve.
- Origin-counting assumes owner identity is meaningful; it is only as
  strong as the deployment's sybil resistance.
- Consensus is not truth: N independent owners can share a false belief
  (culture-wide error). The ensemble raises the cost of falsehood; it
  does not eliminate it. Perception (P9) is the next independent check,
  which is why it follows this layer rather than preceding it.
