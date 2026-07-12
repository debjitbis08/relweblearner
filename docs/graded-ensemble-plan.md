# Graded ensemble — two-timescale webs: soft thinking, hard knowledge

*Written 2026-07-12, BEFORE bring-up and the scored runs. Bring-up: GraphLog
arm on rule_0 (dev) only; forgery arm on seeds 1000–1002 only. Scored runs:
the same 44 held-out GraphLog worlds (seed 0, identical views and anchors as
the discrete run) and the same forgery seeds 0–49. Predictions in §5 frozen
with this document.*

## 1. Why

The discrete ensemble cleared the frozen-algebra wall (multiweb GraphLog:
0.514 vs 0.134) but failed P-K2 at 0.79 × gold-pooled, and the diagnosis was
sharp: **split-brain vocabulary** — knowledge present under two names,
derivations dying at the seam, because identity was decided by vote-counting
with hard commits. The NN observation reframes it: in a neural web nothing
is a discrete name, identity is soft, blending is free — and that failure
mode cannot occur. But an NN is the one-web system of the P8 arm: no
refusal, no audit; hallucination is the coherent forgery accepted.

The corrected architecture is two-timescale:

- **thinking** — fast, graded signal propagation over the opaque webs, with
  SOFT cross-web identity: the webs are ways of thinking, and understanding
  is what the coupled run produces;
- **knowledge** — slow, discrete, audited projection: identities harden into
  commitments only where the coupled dynamics has made them unambiguous;
  refusal, retraction and provenance live here.

Each half is tested where the other architecture fails: gradedness on the
split-brain gap (P-K2's quantity), discreteness on the coherent forgery
(P8's quantity). Failing either kills the two-timescale claim.

## 2. The coupling (both arms)

Cross-web identity is a similarity field S(u, v) computed by **coupled
propagation on the product of the two webs** — no votes, no thresholds
during thinking. S is seeded by the anchors (clamped: an anchor's row and
column are certain), and iterated: a pair's similarity is the propagated
similarity of the company it keeps —

- token webs (GraphLog): S'(x, y) ∝ Σ over triangle pairs with x, y in the
  same position of the product of S over the other two positions, weighted
  by shared support;
- node webs (forgery bench): S' ∝ Ŵ_A · S · Ŵ_B^T with row-normalised
  weighted adjacencies (coupled diffusion).

Eight rounds, Sinkhorn-style row/column normalisation each round, anchors
re-clamped; deterministic throughout.

## 3. GraphLog arm — graded thinking across webs

Identical worlds, views, masks and anchors as the discrete run (seed 0;
the discrete comparator is JOINED from results/multiweb-graphlog, not
recomputed). The construction differs downstream of the webs:

- **No translation layer.** Each web keeps its own invariants in its own
  vocabulary (A-rules, B-rules). Nothing is imported or renamed.
- **Test rendering**: A-visible edges arrive as A tokens; A-blind edges as
  raw B tokens. Seams are left in the path.
- **Graded reduction**: CYK where a rule from either web fires on any
  symbol pair at strength = matched similarity (same symbol: 1; cross-web:
  S). Activations multiply along a parse and sum across paths; pruned
  deterministically (top-k per span).
- **The projection layer**: pairs that are mutual argmax with S ≥ 0.5
  harden into committed identities (auditable; precision scored). Committed
  classes aggregate activation before the final argmax; nothing else does.

## 4. Forgery arm — graded interference must still refuse

Identical generator and seeds as bench-multiweb run 2. Region
correspondence is replaced by the soft field: a region's cross-web
correspondence is the concentration of its members' similarity mass in a
single stable region of the other web, gated by an absolute mass floor
(mean cross-mass per member ≥ 0.15 — a region whose members carry almost
no coupled similarity cannot corroborate, however concentrated the crumbs).
Concept / provisional decisions as in run 2.

## 5. Frozen predictions

GraphLog arm (44 worlds):

- **P-G1 (headline)**: mean graded-ensemble accuracy ≥ 0.90 × mean
  gold-pooled (discrete: 0.794×).
- **P-G2**: graded ≥ discrete ensemble in ≥ 0.75 of worlds; mean
  improvement ≥ +0.05 absolute.
- **P-G3**: hardened-commit precision ≥ 0.90, orphan merges reported
  separately as before.

Forgery arm (50 seeds):

- **P-G4 (the guard)**: coherent forgery excluded from projection in
  ≥ 0.95 of seeds.
- **P-G5**: concept recall ≥ 0.90 and purity ≥ 0.90; solo control
  provisional in ≥ 0.95 of seeds.

## 6. Falsification criteria

- Graded ≤ discrete on mean accuracy: gradedness bought nothing; the
  NN-turn of the thesis is unsupported on this data.
- Forgery admitted in > 0.10 of seeds: graded blending reintroduces the
  one-web failure mode — soft thinking cannot be safely combined with
  projection, and the two-timescale claim fails its guard.
- Hardened-commit precision < 0.75: the projection layer is committing
  identities the dynamics does not justify; the audit story collapses.
- Any failure reported at the same prominence as a pass.
