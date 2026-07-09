# VERIFICATION — post-build protocol

For the agent, now that P0-P8 + SPEC_READWRITE + SPEC_SOCIETY report
complete. Nothing here adds capability; it establishes what is actually
true about the build. Do not begin new phases until Part B passes.

## Part A — Deliverables requested

1. ACCEPTANCE MATRIX: every accept criterion from all three documents,
   as a table: phase | criterion | pass/fail | seeds used | run command.
   Any criterion passed with a single seed is marked PROVISIONAL.
2. DEVIATION LOG: every place the implementation departs from spec text,
   with reason. Deviations are not failures; undocumented deviations are.
3. STRUGGLE LOG: the three phases that took the most retries, and why.
   (These mark where the spec was wrong or the idea is weak -- the most
   valuable information the build produced.)
4. DATA ARTIFACTS (CSV or equivalent, with generating scripts):
   - P4 algebra sweep table: algebras x metrics, incl. web-size-per-
     concept and false-inverse rate; the weak/strong frontier plot
   - P8 ensemble geometry: per-agent spectral embeddings + the cross-
     ensemble stability statistic (does geometry stabilize over the
     population where it varies per agent?)
   - P2' conflation-vs-coverage curve
   - P7 cost-of-lying curve; collateral-retraction counts
   - growth logs, defect censuses, orbit censuses (solipsism debt over
     time), invention census (banked content classes; posit-before-
     evidence events and their confirmation rate)
   - reflection backlog curves (emitted vs consumed traces, long runs)
   - naming-game convergence and rumor exposure-vs-commitment curves

## Part B — Integration tests (new; no spec required these compositions)

I1. TEACH A FRIEND TO COUNT (P1b -> language -> society).
Agent A constructs number from raw pairing episodes (no numeral
tokens anywhere). A and B converge a lexicon (S1) that includes
words for A's constructed classes. A teaches B arithmetic facts by
utterance only. Then B, WITHOUT ever receiving pairing episodes for
them, answers held-out arithmetic queries correctly, with A's owner
as provenance.
PASS: B's accuracy = A's on the held-out set; B's facts carry
source provenance; grep-proof holds end-to-end (no numeral ever
crossed the wire -- only coined words).

I2. INVENTION DIFFUSION (P7' amendment -> society).
Agent A builds a banked content-class (the clock-arithmetic
construction: persistent winding, zero observation conflicts). A
teaches it to B through language. PASS: B banks it as CONTENT (does
not trigger retraction machinery), answers modular queries, records
A as origin; the original P7 poisoned-merge suite still retracts in
the same build. FAIL MODES TO CHECK EXPLICITLY: B retracting the
taught structure as an error; or B committing it with fewer than
the required distinct origins.

I3. DISCOVERED-TYPES AUDIT (P2' -> everything downstream).
Static + runtime audit that no downstream phase consumes given
relation labels: all relation types in P3, P5, read/write grounding,
and society teaching must be traceable to P2' discovery events.
PASS: an automated trace from every relation type in use back to
its discovery record. Any type without a discovery record is a
smuggled label.

I4. REFLECTION x SOCIETY ISOLATION.
Trace episodes (cf-flagged and act-namespace) must never cross the
agent boundary: A's self-observations are not episodes in B's log,
and a malicious agent sending act-namespace messages is rejected
(bus provenance, socialized). PASS: property test over random
dyad transcripts, plus one adversarial injection attempt.

I5. FULL REGRESSION UNDER SOCIETY.
Re-run the complete P0-P8 + read/write acceptance suites INSIDE a
live society member (games running, gossip arriving). PASS: every
prior gate still passes; report any metric that degraded and by
how much (emission overhead, backlog, timing).

## Part C — Seed variance

Re-run at 20 seeds and report mean/min/max (not just best): P1 growth
threshold sharpness; P2' type recovery and conflation rate; ostension
budget vs computed orbit count; naming-game rounds-to-convergence;
rumor test (must be 0/N at every seed); I1 end-to-end. Any
previously-PASS criterion that fails at any seed reverts the matrix
entry to FAIL.

## Part D — Soak

One society of 12 agents, 10^6 interaction rounds, natural noise (1%
corrupt episodes). PASS: defect mass bounded (no runaway); no concept-
fragmentation cascade (split budget holds); reflection backlog bounded;
memory growth sublinear in rounds after lexicon convergence; the
acceptance-relevant metrics at round 10^6 within 5% of round 10^4
values. Report the four curves.
