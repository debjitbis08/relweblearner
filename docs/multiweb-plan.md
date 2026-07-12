# Multi-web interference — testing the original hypothesis

*Written 2026-07-12, BEFORE the first run of the benchmark it specifies. The
predictions in §6 are frozen with this document; whatever the run says is what
gets reported.*

## 1. The drift this corrects

The original idea, restated:

> Thinking occurs as dynamics in opaque geometric webs. Concepts and semantic
> knowledge are **projections of stable structures within and between** those
> webs. Thinking is geometric transformation; knowledge is the stable semantic
> structure projected from it.

```
Opaque episodes → Opaque web ensemble → Cross-web mappings and interference
              → Stable regions and invariants → Semantic knowledge projection
              → Language and explicit reasoning
```

The implementation drifted: concepts became **nodes**, semantics became
**labelled relation edges**, and there is exactly **one** web. The single-web
design has a measured, shared limit — bench v3's P8: a *coherent* forgery
(an internally consistent phantom world taught only by liars) is admitted by
every system that composes at all, because within one substrate coherence is
the only geometric test available. Recovery there is provenance, not geometry.

The original hypothesis makes a stronger claim: with an **ensemble** of webs
generated from *different views* of the same hidden world, a coherent false
pattern in one web is detectable **geometrically** — it fails to correspond
to any stable structure in the other webs. Semantics lives in the cross-web
agreement, not in either substrate. This experiment tests exactly that claim,
minimally, with no Creature code involved.

## 2. The world

A hidden world of **60 entities in 6 communities** of 10 (the communities are
the ground-truth stable structures — the things that deserve to become
concepts). Experience arrives only as **opaque episodes**: small sets of
entities that co-occur (drawn mostly within a community; a noise rate mixes
across). Nothing is ever labelled: no relation names, no attributes, no
community ids.

**K = 3 views**, each with:

- its own opaque renaming of entities (view-local ids; no shared names),
- partial coverage (each entity visible per view with p = 0.8),
- its own independent episode stream (co-occurrence counts become edge
  weights → one weighted undirected **web per view**).

One community (the **solo control**) is made visible *only* in view 0.

**Partial cross-web mappings.** For an entity visible in two views, an anchor
correspondence is given with p = 0.3 (the story: occasionally one event is
registered by two views simultaneously). Anchors are then extended by a
conservative structural propagation (an unmapped node is mapped to the
neighbour-signature best match in the other web only if it beats the
runner-up by a margin). The mapping stays partial by construction.

**The coherent forgery.** Into view 0's web ONLY: 8 fresh nodes wired among
themselves with internal density and edge weights *sampled from the empirical
distribution of the true communities in that same web*, attached to random
real nodes at the true cross-community rate. Internally it is statistically
indistinguishable from a real concept — coherence is matched by construction.
It has no anchors (a fabricated thing was never co-witnessed) and no
counterpart structure in the other webs.

## 3. Stable regions and invariants

Per web, independently, with no cross-web information: candidate regions are
found by modularity community detection (Louvain, seeded); a region is
**stable** if it persists (mean best-Jaccard ≥ 0.6) across 5 re-detections
under 20% edge dropout. Stability-under-perturbation is the operational
reading of "stable structures within the dynamics"; regions of < 4 nodes are
discarded as crumbs.

## 4. Interference and projection

For a stable region R in web i and another web j: map R's members through the
partial mapping (members without images are simply absent); R **corresponds**
in web j if ≥ 2 members have images and the images concentrate in a single
stable region of web j (concentration ≥ 0.6). R's **corroboration** is the
number of other webs in which it corresponds.

**Semantic projection:** a region with corroboration ≥ 1 (i.e. stable
structure agreeing across ≥ 2 webs) projects to a **concept** — the concept
is the cross-web equivalence class, a thing that exists *between* the webs.
A stable region with corroboration 0 is retained only as **provisional**.

## 5. The decisive comparison

| system | sees | promotes to concept |
|---|---|---|
| **one-web** | web 0 only (the forged one) | every stable region |
| **multi-web** | all 3 webs + partial mappings | corroborated regions only; rest provisional |

Scored per seed (50 seeds):

- **M1 one-web acceptance** — the forged region is discovered as a stable
  region of web 0 (and hence accepted as a concept by the one-web system).
- **M2 correspondence separation** — the forged region's best cross-web
  correspondence score vs. the score distribution of true regions whose
  community is covered in ≥ 2 views.
- **M3 projection outcomes** — (a) forgery excluded from concepts / marked
  provisional; (b) concept recall: fraction of ≥2-view-covered communities
  recovered as a projected concept; (c) concept purity: majority-community
  share of projected concepts' members (forged members count against purity).
- **M4 solo control (the honest limit)** — the true-but-single-view community
  must ALSO end up provisional. Interference measures **correspondence, not
  truth**: a single-source truth and a forgery are indistinguishable without
  more views or provenance. Stated up front, scored, and reported.
- **M5 mapping hallucination** — fraction of forged nodes that the structural
  extension wrongly assigns an image in another web.

## 6. Frozen predictions

- **P-A (one-web fails, ≥ 0.90 of seeds):** the forged region passes the
  stability test in web 0 — coherence + stability do not filter it. If the
  one-web system already rejects the forgery, the ensemble machinery is
  unnecessary and the experiment refutes the motivation for it.
- **P-B (separation, ~complete):** forged-region correspondence < 0.6 ≤
  true-region correspondence in ≥ 0.95 of seeds; distributions essentially
  disjoint.
- **P-C (projection, ≥ 0.95 of seeds):** the forgery is not projected as a
  concept; concept recall ≥ 0.80; concept purity ≥ 0.90.
- **P-D (honest limit, ≥ 0.90 of seeds):** the solo-control community is
  provisional, not a concept — the mechanism cannot and does not claim to
  distinguish unshared truth from fabrication.
- **P-E (hallucination low):** ≤ 10% of forged nodes acquire images through
  the conservative extension, and this does not lift the forged region over
  the correspondence threshold in > 0.05 of seeds.

## 7. Falsification criteria

- If the one-web system rejects the forgery (P-A fails), single-substrate
  stability suffices and the cross-web claim is unmotivated **here** — the
  forgery generator must be strengthened before any ensemble claim is made.
- If forged and true correspondence distributions overlap substantially
  (P-B fails), interference does not detect non-correspondence and the
  central mechanism of the hypothesis is refuted in this minimal setting.
- If concept recall or purity collapses (P-C fails), the projection discards
  or corrupts real semantics to reject the forgery — the mechanism would be
  buying safety with blindness, and the hypothesis is not supported.
- P-D failing in the *other* direction (solo control projected as a concept)
  means corroboration is leaking — the implementation, not the hypothesis,
  is broken; fix before interpreting anything else.

## 8. Relation to the existing system

This benchmark shares no code with the Creature. If it succeeds it does not
validate the current implementation — it indicts it, and the ensemble
substrate becomes the realignment target (the labelled-graph machinery
becomes, at most, one *projection* of the ensemble, per the original
architecture sketch). If it fails per §7 it is reported with the same
prominence as bench v3.
