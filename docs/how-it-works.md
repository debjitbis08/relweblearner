# How it works — the plain-language tour

*You don't need to know anything about AI or this project to read this. If
you're comfortable with high-school math, you have everything required. The
[technical companion](theory.md) covers the same ground with the math and the
references.*

---

## A different bet

Most modern AI works like this: take a network of billions of numeric dials,
show it enormous amounts of text, and nudge the dials until its outputs look
right. It works spectacularly well — and it has a strange consequence. Ask such
a system *why* it believes something and there is no answer to give. The belief
isn't stored anywhere. It's smeared across the dials, inseparable from every
other belief, unfixable except by more nudging.

This project makes the opposite bet. It builds a small artificial creature
whose entire mental life is inspectable:

- Everything it ever experiences is written down, in order, in a diary that is
  never erased.
- Everything it believes is a visible structure — a web of concepts — that can
  be rebuilt from the diary at any time, like re-deriving a theorem from
  axioms.
- Everything it *does* — reading, merging two ideas, answering, changing its
  mind — leaves a trace it can itself read.

Underneath the transparency sits the actual scientific bet, and it is worth
stating plainly, because every design choice in this document follows from it:

> **Everything the creature knows lives in the *shape* of its concept map —
> and nothing in the measuring instrument.** The instrument — the small
> arithmetic its connections carry, which we'll meet as the "frozen ruler" —
> is fixed once, in code, and can never be changed by learning. Learning is
> only allowed to *redraw the map*: cheapest corrections first, new territory
> only when nothing cheaper works.

Why insist the ruler be frozen? Because a contradiction, in this system, is a
route around the map that doesn't add up — and if the creature could adjust
the arithmetic itself, every contradiction could be escaped by quietly bending
the ruler instead of fixing the map. Freezing the instrument is what makes
"this doesn't add up" an objective fact rather than a matter of calibration.
The transparency isn't the bet; it's a consequence of winning it. And the open
question the project exists to probe is how far the bet reaches: how much of
what we call intelligence — counting, arithmetic, reading, generalizing,
doubting, trusting — can grow out of nothing but map repair over a fixed
ruler?

The rest of this document walks through the creature's life: how it remembers,
how it believes, how it does math it was never taught, how it reads, how it
answers, and how it changes its mind.

## The diary and the web

The creature's memory has two layers, and the difference between them is the
heart of the whole design.

The first layer is the **diary** (the *episode log*). Every experience — a
sentence read to it from a book, a pile of objects shown to it, one of its own
decisions — is appended as one entry. Entries are never edited and never
deleted. If an entry later turns out to be a lie, it is *flagged* as excluded,
the way a court strikes testimony from the record while the transcript keeps
every word.

The second layer is the **web of concepts**: a network in which each node is a
concept (`cat`, `blue`, `four`...) and each connection records a claim linking
two of them (`cat → blue`, learned from "the cat is blue"). This web is what
the creature *thinks with* — but here's the key move: the web is not a second
source of truth. It is a **summary of the diary**, and nothing more. Delete
the web entirely and replay the diary, and you get the identical web back.
Replay the diary while skipping the flagged entries, and you get the web *as
if those experiences had never happened*.

If you've ever kept accounts, this is double-entry bookkeeping for the mind:
the journal (every transaction, in order, immutable) versus the balance sheet
(the current state, derivable from the journal). Software engineers call the
pattern *event sourcing*. The consequence that matters: this creature can
change its mind **surgically and provably**, because "forget X" means "replay
history without the evidence for X" — a mathematical operation with an exact
answer — rather than "nudge millions of dials and hope".

## Believing takes two witnesses

The creature does not believe things just because it read them. Every claim in
the web carries its evidence: which sources asserted it, how many times. A
claim with a single source is held as **provisional** — noted, usable as a
hint, but not believed. Only when at least two *independent* sources agree does
a claim become **committed**: an actual belief, eligible to be used in
reasoning and taught to others.

This "two witnesses" rule sounds simple, but it quietly does a lot of work. A
single lying book cannot plant a belief. A rumor repeated a thousand times by
one gossip still counts as one witness. And when the creature is later wrong
anyway (it happens), the evidence trail tells it exactly which sources to blame
— which will matter later, when we get to trust.

## The frozen ruler, and loops that must close

Now the strangest and most important design decision. The connections in the
web don't just say *that* two concepts are related — many carry a **number**
saying *how far apart* they are. "Four comes after three" is stored as an edge
labeled **+1**. "Three is before four" is the same edge read backwards: **−1**.

These numbers come with three rules that are built into the machine and can
never be changed by learning — that's why the project calls its algebra
**frozen**:

1. Following a path adds the labels up. (Three steps of +1 is +3.)
2. Reading an edge backwards flips its sign.
3. **Walking around any closed loop must total zero.**

Rule 3 is the engine of everything. Think of the numbers as altitude gains on
hiking trails: any route that ends where it started must net zero climb,
because altitude is a function of *where you are*, not how you got there. In
physics the same idea appears when a force has a potential energy; in
bookkeeping, when accounts must reconcile.

So what happens when the creature's experiences *contradict* each other — say
some book claimed "nine comes after two"? That edge (+1 from two to nine) now
forms loops with the honest counting chain (which insists nine is seven steps
past two), and those loops **don't sum to zero**. Such a loop is called a
**defect**, and defects are the creature's learning signal — literally its
sense of "something itches here". A consistent mind is one with no defects;
learning is the activity of making defects go away *without ever deleting an
observation*.

One more subtlety, because it's the correctness principle for the entire
codebase. Suppose you shifted every concept's "altitude" by some amount — gave
`three` a headstart of +100, adjusting every edge in and out of it to match.
Nothing real would change: every loop would still sum to exactly what it
summed to before. Such bookkeeping shifts are considered *meaningless*, and
anything the creature computes is required to come out identical under all of
them. If a quantity would change under a bookkeeping shift, it's not real
knowledge, and the test suite hunts down any code that treats it as such.

## Three moves, priced like a lazy engineer

When a defect itches, the creature has exactly three ways to respond, and
they're deliberately priced:

- **Relabel** (free): shift the bookkeeping. Provably never fixes a defect —
  see above — but the machinery tries it first *because* proving a fix wasn't
  just bookkeeping is what makes real learning trustworthy.
- **Rewire** (cheap): change connections among existing concepts — merge two
  nodes that turn out to be the same thing, drop or add an edge, as long as no
  observation is contradicted.
- **Grow** (expensive): mint entirely new concepts. Only allowed when a
  problem *persists* through rounds of cheaper attempts, only in the minimal
  amount that resolves it, and only under a budget — when the budget runs
  out, the creature refuses the question rather than inventing junk.

Cheap before expensive; persistence before creation; refusal before nonsense.
That ordering — a kind of built-in Occam's razor — is the creature's entire
motivational system.

## It invents numbers (really)

Here is the payoff of all that machinery, and the project's favorite party
trick.

The creature is never given numbers. In its earliest "childhood" it plays a
wordless game: it's shown two piles of objects and a matching between them,
and it notices for itself whether the piles match exactly or one has a
leftover. Piles that match exactly get merged into a single concept — and
those merged classes, one for each size, connected by "one-more" edges into a
chain, simply *are* its numbers: invented, not taught. Later, an adult points
at a pile of three and says "three", and the creature attaches the word to the
class it had already built. (Philosophers will recognize the idea that number
is what equal-matching piles have in common; the creature discovers this
rather than being told.)

Then arithmetic comes free. "Seven plus six" is not a memorized fact — it's a
*walk*: start at seven, follow six one-more edges, read the name of where you
land. And when a walk falls off the end of the chain — "three minus five" —
the growth engine kicks in: the persistent obstruction licenses minting new
nodes past the edge of the known world, wired with the same +1 edges. The
creature has invented negative numbers, because it *needed* them, and its
subsequent arithmetic with them is exact. No sum was ever written into the
system by hand.

(A lovely aside: when the creature later learns clock-time, the "contradiction"
that 12 o'clock plus 1 is 1 o'clock forms a loop summing to +12 rather than
0. The machinery notices that this particular defect *contradicts no actual
observation* — nobody ever asserted 1 and 13 o'clock were different sightings
— and instead of retracting anything, it banks the loop as **content**: it has
discovered modular arithmetic, and afterwards answers "11 + 3" with "2" on the
clock. The line between an error and a discovery is precisely whether an
observation is violated.)

## Learning to read

Books reach the creature as bare word-sequences plus one act of pointing: each
page has a caption and a "tap" on the pictured word — the way a parent points
at the cow while saying "the cow says moo".

From nothing but many such pages, the creature notices that captions cluster
into repeated shapes: *the ___ is ___*, *___ has ___ legs*, *a ___ is a ___*.
These discovered templates are called **frames**, and they become the
creature's grammar: the fixed words identify the *relation*, the blanks carry
the *concepts*, and the tap tells it which blank the picture grounds — which
way around the fact goes. A sentence that fits no known frame isn't guessed
at; it lands in the **frontier**, a holding pen of not-yet-parseable
experience which, once enough similar shapes pile up, triggers the induction
of a new frame. The same "obstruction, then growth" rhythm as everywhere else.

Two nice consequences. Different phrasings — "a hen is a bird" and "the hen is
a kind of bird" — get discovered to be *the same relation*, not by being told,
but because they connect the same pairs of concepts; the creature merges them
only after imagining the merge on a scratch copy and checking that no
contradictions would result. And a brand-new word can be learned from a single
page — the frame carries the structure, so one tap on "zebu" teaches what kind
of thing a zebu is. Toddlers do this too; psychologists call it fast mapping.

## Answering: look it up, then walk

Ask the creature a question and it tries, in order:

1. **Lookup** — a committed edge that directly answers ("the cat is ? " →
   blue).
2. **Walking** — compose edges using the frozen rules. Taught only "ten comes
   after nine", it answers the never-heard "nine is before ten" by reading the
   edge backwards. This is why held-out questions cost it nothing: the answer
   was *entailed*, not memorized.
3. **Inheritance** — discovered rules of the form "leg-count passes through
   kind-of": a hen is a kind of bird and birds have two legs, so "hen has ?
   legs" → *two*, marked as **derived** rather than known. Crucially these
   rules are themselves evidence-scored: leg-count earns the rule (animals
   agree with their kind), color is *refused* the rule (a red bird under a
   generally-feathered class disagrees), and the table of accepted and refused
   rules — with witness counts — is on display in the UI.
4. **Growth** — if the walk falls off the web, the question itself may license
   inventing a concept (that's how the negative numbers happened).
5. **Refusal** — otherwise it says it doesn't know. It would rather be
   visibly ignorant than fluently wrong.

Every answer comes back labeled: *committed* (believed on evidence),
*provisional* (one witness), *derived* (computed, not stored), *grown*
(invented under budget). The label is the creature showing its work.

## Changing its mind

The creature will sometimes be wrong — a book lied, or the world was
misdescribed. What happens next is where this design is at its most opinionated.

**You never operate on its memory.** You teach. Telling it `owl has two legs,
not four` writes exactly one new diary entry, in a special voice reserved for
its owner (a *correction*). The creature then notices, by itself, that it now
holds two committed values for a single-valued relation. It resolves the
conflict — your word outranks testimony; a newer correction outranks an older
one — by flagging the outweighed episodes excluded and rebuilding the web from
the diary. The lie is gone; the books' *other* facts survive; and the whole
transaction, including the reason, is in the record. If the books later
re-teach the lie, the standing correction wins again automatically.

**Blame is assigned — and it's local.** The sources whose testimony was struck
lose standing, but only *in that topic*. A field guide caught wrong about leg
counts is thereafter taken with a grain of salt about anatomy — its future
claims there need extra corroboration — while its testimony about colors
remains as good as anyone's. Conversely, a source with a long, clean,
independently-corroborated record in one topic *earns authority* there: its
lone word eventually suffices, in that topic and nowhere else. Trust, in other
words, is not a reputation score. It's a ledger of per-domain track records —
you can read it in the UI or with `relweb-correct --trust`.

**And it will not guess between honest disagreements.** During development,
an early version of the conflict-resolver was allowed to let majorities
outvote minorities. On real data it promptly deleted the belief that a hen is
a bird — because one corpus said "bird", a different corpus said "female", and
"bird" merely *outnumbered* it, while both are simply true. The rule that
survived that lesson: corroborated testimony never erases corroborated
testimony. When two well-supported camps disagree, the creature keeps both,
displays the tension as an open defect, and waits — for a teacher, or for one
camp's credibility to erode on its own. No statistic can distinguish a
disagreement from two truths; the creature knows better than to pretend
otherwise.

## Watching it think

One last architectural vow: **no silent operations**. Every single act — each
observation, each frame induced, each merge imagined and committed or refused,
each answer, each retraction — emits a trace *in the same format as its
experiences*, onto the same bus. Its own mental life is just more diary.

This has a practical payoff — the web console can show you its concept web,
its learned map of ideas (concepts positioned by their relations, so the
numbers literally line up along an axis), its accepted and refused
generalizations, its trust ledger, and its known contradictions. And it has a
philosophical one: the creature can read its own traces with the same
machinery it reads the world, count its own mistakes with the number chain it
built itself, and budget attention for reflection like any other activity.

## What it isn't

Fairness demands the limits be as visible as the tricks:

- **It is small.** Its whole world is what its curriculum teaches — counting,
  elementary science, taxonomies, capitals. It converses in the frames it has
  induced, not in free English.
- **Coherence isn't truth.** A perfectly consistent lie creates no defect and
  cannot be detected from the inside. The design's answer is outside: many
  creatures comparing notes (there is a whole society layer — naming games,
  gossip with citations, dialect formation — where disagreement between agents
  becomes the truth signal a single agent lacks).
- **Colluding sources can fool it** — until they're caught once, at which
  point the trust machinery starts discounting them where it matters.
- **It trades fluency for accountability**, on purpose. It will never dazzle
  you; it will also never confidently tell you something it cannot show its
  work for.

If this made you want the equations underneath — what "loops must close" has
to do with gauge theory, why bookkeeping shifts form a group, how the trust
weights are computed — the [technical tour](theory.md) starts from zero and
brings references.
