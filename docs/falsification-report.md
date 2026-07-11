# Falsification report — what the benchmark said

*Run 2026-07-11, 5 seeds, against the design and predictions frozen in
[falsification-plan.md](falsification-plan.md) (commit 0208514, before this
run). Raw numbers: `results/bench/`. Reproduce with `relweb-bench --seeds 5`.*

## Headline

The central claim survives its floor test, loses exactly where code-reading
predicted, and is matched on capability by a statistical rule inducer — so
per the pre-registered criteria it is **kept, narrowed, and bounded**:

> An event-sourced, provenance-aware relational learner that discovers
> converse structure from raw text and uses fixed-algebra transport for exact
> inference, noise-robust inconsistency detection, and exact unlearning —
> within the converse/inversion sector it can currently discover.

"All learning reduces to geometry repair" is **not** supported by this run
and is no longer claimed.

## Results against predictions

| measure | lookup | induced | oracle | relweb | noderive | predicted (relweb) |
|---|---|---|---|---|---|---|
| F1 memory | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| F2 invert-step | 0.00 | 1.00 | 1.00 | **1.00** | 0.00 | ~1.0 ✓ |
| F3 skip-transfer | 0.00 | **1.00** | 1.00 | **0.00** | 0.00 | 0.0 (loss) ✓ |
| F4 invert-skip | 0.00 | 1.00 | 1.00 | **0.80 ± 0.45** | 0.00 | ~1.0 ✗ |
| F5 refuse-color | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| F6 plural-likes | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.0 ✓ |
| D1 direct conflict | 1.00 | 1.00 | 1.00 | 1.00 | — | caught ✓ |
| D2 loop lie | **0.00** | 1.00 | **0.80** | **1.00** | — | caught ✓ |
| poisoned by lie | 1.00 | 1.00 | 1.00 | 1.00 | — | yes ✓ |
| U1 exact unlearning | exact | exact | exact | **1.00** | — | exact ✓ |
| clean-arm false alarms | 0 | 0 | 0 | 0 | — | 0 ✓ |

## Verdicts (pre-registered criteria)

- **C1 (claim dead?) — passed.** RelWeb reads raw pages, induces the frames,
  unifies the paraphrases, discovers that "comes right after" / "is just
  before" and "sits two past" / "lies two shy of" are converse pairs, and
  answers held-out inversions the lookup floor scores 0 on. The
  `relweb-noderive` ablation confirms the answers come from transport, not
  memory.
- **C2 (narrowed) — triggered.** `induced-rules` — an AMIE-style miner at the
  same confidence budget, admittedly fed gold parses — matches or beats
  RelWeb on every capability family. On this world, holonomy does not
  outperform statistical rule induction at *learning*; the honest claim is
  the guarantees (exactness, audit, refusal, unlearning), not capability
  advantage. README updated accordingly.
- **C3 (bounded) — confirmed.** F3 = 0.00 exactly as predicted: gauge groups
  form from converse 2-cycles only, so skip = step∘step is undiscoverable by
  the current mechanism, while the statistical competitor learns it from the
  same stream. "Learning is geometry repair" holds at most for the
  converse/inversion sector until composite (3-cycle) loop evidence is
  implemented. RelWeb *refuses* these queries rather than guessing — the
  failure mode is the designed one.
- The P3 holdout (`holdout.py`) is re-labeled: it demonstrates exact
  composition, a property of the representation, not a learning result.

## Findings the predictions missed

1. **RelWeb F4 dropped a seed (0.80 ± 0.45).** On seed 1 the `lies two shy
   of` frame never induced — the rarest frame (~30 pages) fell under the
   induction threshold, so skip⁺ had no converse evidence and stayed
   unconstrained (it refused; it did not guess). Discovery is data-hungry at
   the tail, and a capability built on discovery inherits that variance.
   Reported as measured; the world was not retuned to hide it.
2. **Statistical conflict detection is noise-fragile; holonomy is not.** The
   oracle rule engine missed D2 on seed 3: sub-commitment gossip junk made
   `step⁺` look non-functional on raw testimony, silently disabling its
   derived-conflict rule. The holonomy detector fired 5/5 — it reads only
   committed geometry and needs no functionality statistics. This is a real
   differentiator in RelWeb's favor that the predictions did not anticipate,
   surfaced only because the baseline was built to compete honestly.
3. **Localization is weaker than detection: 0.40.** Holonomy names a
   defective *cycle*; the reported non-tree edge touched the lying edge's
   endpoints in only 2/5 seeds. Blame assignment needs provenance and trust
   on top of the geometric signal — consistent with the architecture's own
   story, now with a number attached.
4. **Everyone repeats a committed lie (poisoning 1.00 across systems).**
   k-witness commitment is collusion-*bounded*, not collusion-proof; the
   recovery story is detection (D2) → arbitration → retraction (U1 = 1.00),
   not immunity.

## What this does not settle

Internal validity only: a synthetic, closed, 12-entity world authored by the
learner's own author. The bring-up phase alone found and fixed two
adversarial-robustness bugs in the learner (gauge-group welding by one lying
pair; motif demotion off one tree-placed lie — see plan §4), which is
evidence the harness bites, but external validity still requires:

1. **GraphLog** (external compositional benchmark) through the reading
   pipeline — blocked on network access under the laptop-only constraint;
2. **the uncontrolled-language eval** (frozen Gutenberg slice, hand-labeled
   gold): frame precision, fact precision, negation, temporal facts.
