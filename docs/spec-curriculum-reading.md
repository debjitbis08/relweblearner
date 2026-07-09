# SPEC — Curriculum Reading (frame induction & the book path)

Extends SPEC_READWRITE. Direction set by product: the creature is taught
from children's-book-style content — picture books first, Wikidata-scale
feeds deferred until much later. Reading skill is the compounding rate on
all future content; this spec is the optimization of that path.
Reference implementation: experiment0n_frames.py (all numbers below).

## 0. Why picture books are the architecturally correct corpus

1. A picture-book PAGE is a native JOINT EPISODE: illustration (perceptual
   channel) + caption (language channel), co-presented. A tap on the
   pictured referent while the caption is read IS the ostension event
   the grounding layer requires. Text-only corpora hit the automorphism
   ceiling; illustrated corpora carry their own symmetry-breaker.
2. Early children's books are FRAME MACHINES: one template iterated with
   slot substitution (the Brown-Bear genre convention). This matches the
   usage-based acquisition sequence (item-based frames before abstract
   grammar) and is exactly what L2' below induces.
3. Repetition-with-substitution gives the commitment policy natural
   evidence structure: the same fact across pages/books accrues origins.

## 1. L2' — Frame induction (the gating capability)

Sentences are word sequences (L1 segmentation already supplies words).
Induce templates from repetition:

- group candidate sentences; for each position compute the DOMINANT token
  frequency; position is FIXED if dominance >= 0.8, else a SLOT;
- a frame requires >= 2 fixed anchor tokens (reject degenerate all-slot
  skeletons);
- sentences not matching any induced skeleton are REJECTED to the
  FRONTIER — never force-parsed.
  REQUIRED FAILURE-MODE TEST (found the hard way): grouping by length alone
  lets off-frame sentences pollute the skeleton and over-generalize to
  all-slots. The dominance threshold + anchor minimum + rejection is the
  fix; a test must reproduce the failure without it.
  FRONTIER AS TRIGGER: unparsed sentences are language-layer defects. When
  a frontier subset itself shows repetition-with-substitution, it triggers
  induction of the NEXT frame — the same obstruction->growth pattern as
  everywhere else. Constructions are motifs over the sequence web.
  **Accept:** on the synthetic pattern-book corpus: both frames recovered
  exactly, coverage 0.98 with the two off-frame sentences (and only those)
  in the frontier; the pollution failure-mode test in CI.

## 2. Grounding through frames (unchanged machinery)

A frame is a multi-word relation marker; slot-fillers are the arguments.
Slot grounding = the existing WL alignment; picture taps seed BOTH sides
(joint attention); taps proceed iteratively, one per remaining orbit,
elimination and refinement doing the rest.
**Accept:** 10/10 slot-filler grounding with tap count equal to what the
orbit structure requires (reference: 4 taps for a 4-orbit + three
2-orbits world); fast-map: a novel word on one page with one tap yields
a committed-eligible fact with book provenance.

## 3. The book-reader UI (an episode composer in disguise)

The teaching UI the product wants IS the data pipeline:

- a page shows an illustration with TAPPABLE REGIONS + a caption;
- the reader (human) taps the pictured referent as the caption is read
  -> emits a joint episode (perceptual tokens + word sequence + tap);
- page-turn streams episodes; a book is a curriculum unit (target frame
  - vocabulary set + fact set);
- counting pages embed P1b pairing games (tap to pair collections);
- NO alphabet module: a text-native learner receives atomic units from
  the sensor; the alphabet ritual maps speech to print for children and
  has no machine analogue. Do not build UI for a non-problem.
  Author tooling: composing a book = choosing pictures, defining tappable
  regions, writing frame-conformant captions. The author is writing
  episodes without knowing it. Curated KG-style facts enter ONLY as
  generated pattern-book pages, never as labeled triples (labels would
  re-smuggle what P2' discovers).

## 4. Corpus plan

- StoryWeaver (Pratham Books): thousands of CC-licensed illustrated
  children's books, leveled, including Indian languages. Primary real
  corpus; reading levels map to the ladder below.
- Global Digital Library: additional open-licensed leveled readers.
- LLM-AUTHORED ORIGINAL PATTERN BOOKS: copyright-safe, controlled
  vocabulary, frame-graded; the cheap way to manufacture curriculum
  precisely at the creature's current level. (Classic titles in the
  genre are copyrighted; do not ingest them.)
  Multilingual note: separate language webs per language over one concept
  web comes free from the architecture; StoryWeaver's parallel translations
  are a ready-made bilingual curriculum when wanted.

## 5. The reading ladder (research milestones = content unlocks)

- R1 (done): fixed frames, syllable/word segmentation, ostension,
  fast-mapping. Unlocks: authored frame books.
- R2 (this spec): frame INDUCTION + frontier-triggered template growth.
  Unlocks: pattern books (StoryWeaver level 1-ish).
- R3: anaphora via page-context binding — pronouns bind to the currently
  ostended/pictured referent (deixis again); plural morphology as
  suffix-frames; question frames as adjacency pairs. Unlocks: simple
  narrative books. ALSO DUE HERE: cross-book character identity ("the
  bear" of book 1 vs book 2) — entity resolution returns in miniature;
  treat as the mention/node merge decision with book provenance.
- R4: negation, quantifiers, multi-clause sentences. Unlocks: early
  chapter books. Expect diminishing frame-coverage; this is where the
  approach is genuinely untested.

## 6. Metrics (define now, optimize the path)

- COVERAGE per book tier: fraction of sentences parsed by induced frames
  (frontier size is the complement and the induction queue).
- ASSIMILATION RATE: committed, correct, NON-REDUNDANT facts per
  sentence read (raw facts/sentence saturates on small worlds — the
  reference run's 0.049 is saturation, not capability).
- TAPS PER BOOK: ostension cost; should fall as the concept web grows
  (more structure = fewer orbits).
- FRONTIER CENSUS: unparsed-pattern clusters awaiting induction — the
  reading layer's "what confuses me" view, a product feature for free.
- COMPREHENSION CHECK: after a book, generated questions in known frames
  answered from the concept web (reading verified by use, not echo).

## 7. Known limits (state, do not hide)

- Real books at any tier will have coverage < 1; unparsed sentences are
  skipped gracefully and logged. Optimizing coverage on real StoryWeaver
  level-1 books is the first honest benchmark; expect it to be humbling.
- The dominance threshold and anchor minimum are hyperparameters;
  report sensitivity.
- Illustrations are assumed pre-segmented into tappable regions (human
  authoring or off-the-shelf segmentation); creature-side vision is NOT
  in scope — the picture channel arrives as region tokens.
- Wikidata-scale ingestion is deferred BY DESIGN (product decision);
  note the cost: breadth grows at curriculum-authoring speed, and
  cross-book identity (R3) is the small-scale rehearsal of the entity
  resolution that scale will eventually demand.
