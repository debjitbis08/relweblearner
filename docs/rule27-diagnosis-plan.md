# The rule_27 diagnosis (E6) — pre-registered diagnostic plan

*Written 2026-07-14, BEFORE any diagnostic code is run. This is a DIAGNOSIS,
not a bench: there are no scored pass/fail predictions, and its output is an
attribution table, not a rate. It is pre-committed anyway, so the hypothesis
space, the discriminators, and our declared priors are frozen before the data
can steer them — whatever the attribution says is what gets reported. E6 is
the head of design-problem.md §10's empirical queue ("diagnose before
formalizing; a theory built to explain misdiagnosed data is designed wrong"),
and §9 lists one E6 outcome as a falsifier-adjacent reclassification: if
rule_27 is a harness artifact, it constrains the benches, not the theory.
Provenance vocabulary as in multiweb-overlap-forgery-plan.md §8: (a) read
from frozen artifacts; (b) deterministic recomputation with frozen code.*

## 1. The question this settles

rule_27 is the worst world of the multiweb-graphlog bench and the poster
child of the split-brain diagnosis — and the split-brain diagnosis does not
explain it. The projected ensemble inventory holds 100 rules against gold's
103, yet ensemble accuracy is 0.163 against gold-pooled 0.828. The knowledge
is present; derivation fails. Worse for the current story: the graded
ensemble (multiweb_graded, soft coupling that healed rule_26 0.29→0.64 and
pushed rule_32 above gold-pooled) left rule_27 at **0.163 exactly** — not
approximately: no test prediction moved. Whatever blocks rule_27, graded
similarity neither bridges nor even perturbs it. The split-brain account
("identity resolution is the binding constraint") is therefore necessary but
demonstrably not sufficient here, and rule_27 is the single strongest lever
on whether that account — which feeds D2 and T5 — is the right one to
formalize.

The question: **what, mechanically, blocks rule_27's derivations?** Not "what
is plausible" — which token, which rule, which path, per failing test
episode.

## 2. The frozen facts (provenance (a) unless noted)

From results/multiweb-graphlog/results.json (world rule_27, seed 0) and the
frozen modules:

- Accuracies: view-alone 0.133, ensemble 0.163, gold-pooled 0.828. The
  ensemble adds 31 rules over view-alone (69 → 100 vs gold 103) and buys
  +0.03.
- Priors row: cyk-miner 0.828, cyk-oracle 0.918 — the harness derives GOLD
  fine at `MAX_PATH = 5`, so any horizon artifact must be an *interaction*
  with the ensemble rendering, not a flat depth ceiling.
- Vocabulary: 19 labels; each view blind to 3 (disjoint, HIDE_FRAC = 0.15).
- Mapping: 6 anchors + 6 extended pairs = 12 of 19 tokens resolved;
  coverage 0.75; ext_precision 0.833 — **exactly one wrong pair, and it is
  an orphan merge** (wrong_orphan 1, wrong_real 0): one of only 17 orphan
  merges across all 44 worlds sits in this world.
- Graded arm: rule_27 unmoved at 0.163 (results/graded-ensemble); the
  graded machinery commits identities at mutual-argmax with
  `HARD_SIM = 0.5` and reduces with a TOP_K = 8 beam over activations
  floored at ACT_MIN = 0.01 (multiweb_graded.py).
- The ensemble test rendering (_render_test): A-blind edges are supplied in
  B's naming, translated where mapped, IMPORTED otherwise; projected B rules
  likewise keep B naming for unresolved tokens. CYK reduction
  (graphlog.cyk_predict) needs every span to hit a rule key exactly, so one
  unresolved token on a path can kill every derivation through it; an
  episode with no reduction at all falls back to the majority label
  (0.006 here).

## 3. Hypotheses, with declared priors

Not mutually exclusive; the attribution table (§4) assigns shares. Declared
priors, so hindsight cannot be claimed later: the exact-zero graded movement
and the single resident orphan merge elevate **H3 and H4**; H1 is the cheap
first check; H2 is the quick oracle patch.

- **H1 — harness interaction (the §9 reclassification candidate).** Failing
  episodes have no u→v witnessing path of length ≤ MAX_PATH *under the
  ensemble rendering* (e.g. A-blind edges divert or truncate the path
  census), even though gold's rendering has one. Pure-horizon is already
  half-refuted by cyk-miner 0.828; what remains is the interaction.
- **H2 — the 3 missing rules are load-bearing.** Gold's 103 minus the
  ensemble's 100: if those 3 sit on the critical path of most test
  derivations, the immunity is inventory, not identity.
- **H3 — a split HUB.** Among the unresolved tokens, one (or few) is a
  hub: it appears on nearly every failing derivation, so B-projected rules
  name it one way and test paths the other. (From the frozen counts the
  candidate set is SMALL: B carries 16 tokens, 12 are mapped and one of
  those wrongly, leaving at most 4 unmapped — some of them A-blind imports
  with no counterpart at all. A hub, if there is one, is nearly pinned
  before the diagnostic runs.) Predicts: an oracle repair of
  that single identity recovers a large step of accuracy; and its
  similarity row in the graded run explains the immunity (true counterpart
  below HARD_SIM, or mutual-argmax lost, or activation dead below ACT_MIN
  mid-reduction).
- **H4 — the orphan merge poisons.** The world's one wrong pair piles one
  relation's evidence onto another's symbol inside the pooled rules;
  derivations then reduce to the wrong head, or competing wrong reductions
  win argmaxes. Predicts: un-merging that single pair moves accuracy;
  distinguishes from H3 by direction (H3 = absence of a needed
  identification; H4 = presence of a wrong one).

## 4. The instrument

A new module `src/relweblearner/bench/rule27_diag.py`, importing the frozen
graphlog / multiweb_graphlog / multiweb_graded machinery UNCHANGED (the
multiweb_overlap reuse pattern); no constant is touched, `MAX_PATH`, floors,
and seeds stay frozen. Everything below is provenance (b): deterministic
recomputation of `run_world("rule_27", seed=0)` internals. Output to
`results/rule27-diagnosis/` (attribution table + per-episode records).

**4a. Failure attribution (the core).** For every test episode, in ensemble
mode, record the FIRST blocking cause:

1. `no-path` — no u→v path of length ≤ MAX_PATH exists in the rendered
   episode (H1's cell; compare the same census under gold rendering);
2. `cyk-dead` — paths exist but no label sequence reduces to any relation:
   record the missing `(a, b)` rule keys at the blocking spans and whether
   a or b is an unresolved/imported token (H3's cell) or a gold-missing
   rule (H2's cell);
3. `wrong-argmax` — reductions exist but the winning label is wrong: record
   which rule produced the winner and whether the orphan-merged symbol
   participates (H4's cell).

The headline of the diagnosis is this table: failures × {no-path, cyk-dead
(split-token / missing-rule), wrong-argmax (orphan-tainted / other)}.

**4b. Counterfactual probes (one per hypothesis, labeled diagnostic —
never scored as bench results):**

- *Oracle repair curve (H3):* greedily add true-map identities for the
  unresolved tokens that possess a true counterpart (mutually visible
  ones; at most 4 candidates per §3 H3), one at a time, best-first by
  accuracy gain, re-scoring after each. A step function at one token is a
  hub; a flat ramp is diffuse split-brain.
- *Un-merge (H4):* remove the single wrong orphan pair from the mapping,
  re-project, re-score.
- *Rule patch (H2):* add gold's 3 absent rules to the ensemble inventory
  (oracle patch), re-score; and ablate the same 3 from gold, re-score gold.
- *Path census (H1):* per failing episode, shortest witnessing path length
  under gold vs ensemble rendering.
- *Graded post-mortem (H3/H4 mechanism):* read the frozen similarity matrix
  for the implicated token(s): value against true counterpart, mutual-argmax
  status vs HARD_SIM, and whether graded_reduce's activation dies below
  ACT_MIN at the blocking span — this must also explain the 0.163-exactly
  immobility (e.g. every affected episode already fell back to majority, so
  soft coupling had nothing to move).

**4c. Robustness (secondary):** the frozen result is seed 0; repeat 4a on
seeds 1–4 and report whether the attribution shares are stable. Reported
separately, never pooled into the seed-0 headline.

## 5. Outcome routing (fixed now, per design-problem §9/§10)

- **Mostly H1** → rule_27 is reclassified per §9: a bench/harness
  constraint, not theory data. E6's "immunity" line leaves the boundary
  conditions (§7) and moves to the bench's known-limitations; the
  split-brain finding stands on the other worlds.
- **Mostly H3** → the split-brain account deepens from "identity shortfall
  taxes derivation superlinearly" to "hub identities gate whole worlds":
  feeds D2 (what stalks carry) and T5's uniqueness conditions (anchors per
  component was E8; this would be its token-level analogue — anchors per
  HUB). The graded immunity must be explained by the post-mortem or H3 is
  not accepted.
- **Mostly H2** → inventory, not identity: diagnose why mining/projection
  missed those 3 (support floor? blind-relation interaction?); constrains
  the MIN_SUPPORT/MIN_CONF story, not the conjecture.
- **Mostly H4** → the first measured world-scale damage from an orphan
  merge: connects to E3/T3 (identity underdetermined up to overlap-visible
  automorphism — the merge was defensible from inside) and sharpens the
  commit-policy discussion (P1/P2 family): a defensible identification can
  still be expensive; what evidence should retract it?
- **Split attribution** → report the shares; no single reclassification;
  the follow-up (if any) is licensed by whichever share dominates the
  FAILING episodes, not by preference.

Whatever the outcome, the result ships as a report in
results/rule27-diagnosis/ and design-problem §7 E6 / §9 / §10 are updated to
cite it — the same fold-in discipline as E2b.

## 6. Discipline

This plan is committed before `rule27_diag.py` exists. The probes in §4b are
counterfactuals for attribution only: none of them (oracle identities, rule
patches, un-merges) may be reported as system capabilities, and no frozen
bench artifact is rewritten. If the diagnosis reveals a bench bug (H1 in the
strong form), the fix is out of scope here and needs its own pre-registered
plan before any re-run, exactly as the E2b re-run obligations are queued in
multiweb-overlap-forgery-plan.md §9 rather than silently applied.
