# SPEC — Reading & Writing (language webs)

Note: While writing this, the N web work was not conceived.

Standalone phase spec, to be handed to the agent AFTER the main DEVDOC
phases are underway. Self-contained; assumes only the DEVDOC glossary.
Reference implementation of every mechanism: experiment0j_readwrite.py
(all acceptance numbers below were produced by that run).

## 0. Position in the architecture

Language is a SEPARATE web (or webs), not extra relations inside the
concept web. Dependency is strictly one-way:

- the language web READS the concept web through a learned interface;
- the concept web never references the language web;
- deleting the language web must leave every concept-web acceptance
  test passing (CI test); deleting the concept web must make every
  reading/writing acceptance test fail (CI test).
  Language is a skill atop concepts: knowing concepts does not confer
  reading; reading cannot ground without concepts.
  Multiple language webs may interface the same concept web (this is the
  model of bilingualism, and it comes for free from the separation).

## 1. Input contract (barer than the main feed)

The sensor delivers a raw stream of atomic perceptual units (characters,
syllables, phonemes -- whatever the sensor's stable minimum is). NO word
boundaries, NO utterance boundaries, NO vocabulary, and NO identifier
shared with the concept web. Words are opaque; nothing may string-match
a concept id (CI test: concept ids and surface forms drawn from disjoint
namespaces).

## 2. Layers

### L1 — Segmentation (units from statistics)

Word boundaries = transition-probability dips in the unit stream
(within-word transitions are high, cross-word transitions are diluted).
Maintain the transition table incrementally; split below threshold.
For a NOVEL word heard once, transition statistics are silent: segment
by SUBTRACTION -- strip known words from both ends of the utterance;
the residue is the candidate new word.
**Accept:** on a synthetic lexicon with unique units per word, boundary
precision/recall 1.00 and exact lexicon recovery. On a stress lexicon
with shared units, report the degradation curve (reference run: 0.81
precision at 1.00 recall) -- segmentation is statistical, with a
measurable ceiling, and the ceiling is a logged metric, not a failure.

### L2 — Utterance structure (closed class from Zipf)

Frame words (relation markers, function words) are frequency outliers:
they occur in every utterance. Discover the closed class as the Zipf
head of the recovered lexicon; chunk the word stream into utterances at
closed-class tokens.
**Accept:** 100% of chunks have the frame shape on the synthetic corpus;
the closed/open class split is discovered, never given.

### L3 — Grounding (the interface, by structure alone)

Build the token web: utterances contribute edges between argument tokens,
typed by frame token. Ground = align token web to concept web:

- search the small space of frame-token <-> concept-relation-type
  bijections;
- for each, run joint Weisfeiler-Leman signature refinement on both
  webs; unique signature matches are grounded; equal-signature groups
  of size > 1 are ORBITS.
  THE STRUCTURAL LIMIT (state it as a result, and test it): distributional
  grounding resolves word meanings EXACTLY up to the automorphism orbits
  of the concept web restricted to the worded region. Structurally
  interchangeable concepts cannot be distinguished by any amount of text.
  (Reference run: 7/11 words grounded uniquely, and the unresolved
  residue was precisely the two 2-orbits of the concept graph.)
  **Accept:** grounded words all correct; unresolved set == computed
  automorphism orbits (compare against a brute-force orbit computation).

### L4 — Ostension (joint attention breaks symmetry)

An ostension event is a joint episode tagging one token AND one concept
with the same seed (pointing while naming). Seeds enter L3 as initial
WL colors on BOTH webs; re-run refinement.
Predictions to verify:

- ostension budget = number of nontrivial orbits (one pointing per
  orbit; elimination grounds the orbit's remaining members for free --
  reference run: 1 ostension took 7/11 -> 9/11, the second -> 11/11);
- ostensions are maximally informative on orbit members, redundant on
  already-unique words (log the marginal gain per ostension).
  **Accept:** full correct grounding with exactly #orbits ostensions.

### L5 — Reading (comprehension = writing into the concept web)

A grounded utterance maps through the interface to a concept-web edge.
Three cases, each with distinct behavior:

- the edge exists: comprehension confirms (a coherence check, free);
- the edge is new and coherent: the sentence TEACHES -- commit it via
  the standard commitment policy (text episodes are claims: they carry
  source provenance and count toward k-thresholds like any evidence,
  and a lying sentence is caught by the same defect machinery);
- the utterance contains an unknown word: FAST-MAP -- segment by
  subtraction (L1), constrain by frame position and the grounded
  remainder, resolve by mutual exclusivity against unworded concepts.
  (Reference run: one exposure grounded the novel word correctly.)
  **Accept:** all three paths demonstrated; fast-mapping accuracy on a
  held-out battery of single-exposure novel words; a false sentence is
  refused by rehearsal (see L6/simulation) or retracted by P7 machinery.

### L6 — Writing (inverse map + read-back before commit)

To express a target concept fact: apply the inverse interface to draft
a token sequence, then READ THE DRAFT BACK through the forward
interface on a fork; commit (utter) only if the reconstruction equals
the target. This is simulate-before-commit applied to speech.

- if a needed concept has no word (or its word is an unresolved
  orbit), the writer must REFUSE and may request ostension or coin a
  word -- never emit an ambiguous draft silently (reference run:
  pre-ostension write refused; post-grounding write committed with
  read-back equal to target).
  Adjunction tests (the correctness law of the whole layer):
- read(write(fact)) == fact, for all expressible facts;
- write(read(utterance)) is utterance-equivalent (same fact) --
  paraphrase is allowed, meaning drift is not.
  **Accept:** both laws hold over the full expressible set; every refusal
  is logged with its reason.

## 3. Metrics

- boundary precision/recall + degradation curve vs unit-sharing
- lexicon recovery; closed-class discovery correctness
- grounded fraction, grounding accuracy, orbit count, ostension budget
  and marginal gain per ostension
- fast-map single-exposure accuracy
- adjunction violation rate (must be 0 for commit-eligible drafts)
- one-way dependency CI results (Section 0)

## 4. Known limits (state in results, do not hide)

- The symmetry ceiling: no corpus volume substitutes for ostension on
  automorphic concepts. Deixis is architecturally necessary, not a
  convenience. (This is the formal content of the gavagai problem.)
- A word grounded only in token-token co-occurrence, never merged to a
  perception-built concept, is USE without UNDERSTANDING: the system can
  complete sequences with it but cannot answer concept queries through
  it. The architecture represents this difference explicitly; report the
  grounded/ungrounded ratio as a first-class metric.
- Text is claims: reading inherits the coherence-not-correspondence
  limit; the ensemble remains the only correspondence defense.
- Real language adds polysemy (handled as interface splits), word order
  variation, and non-compositional idiom; the synthetic corpus defers
  these deliberately. Scale-up order: free word order -> polysemy ->
  multi-clause utterances.
