"""Source trust — learned, per relation class, as a projection of the record.

Humans learn to take an unreliable narrator with a grain of salt, and they learn
it PER DOMAIN: the field guide that misprints leg counts may still be right about
colours; the ornithologist is an authority on birds and nobody on engines. This
module gives a creature the same discrimination, with no new mutable state:

  * a source's **good marks** in a relation class are its distinct facts there
    that stand independently corroborated in the current web;
  * its **bad marks** are its distinct facts among the log's EXCLUDED episodes —
    testimony that was adjudicated wrong (retraction, correction, revision).

Both are read off the store and the episode log, so trust is a PROJECTION
(invariant #5): rebuilt on demand, reproducible by replay, never checkpointed.
A source is not a scalar reputation but a ledger of per-domain track records.

The weight a source's testimony carries in one class:

  * fresh source                  -> 1.0 (one ordinary witness — the old rule);
  * caught lying (bad marks)      -> below 1: its word alone counts for less, so
    its claims need MORE independent corroboration to commit; a sustained good
    record climbs back toward (never past) ordinary;
  * long clean record (``good >= authority_k``, no bad marks) -> ``commit_k``:
    earned authority — its lone word suffices IN THAT CLASS, and only there.

Honest limits, stated: corroboration is agreement with the record, so a
colluding majority *is* the record until it is caught (the k-collusion caveat
the store already carries); the edge store keys provenance by (edge, source),
not (edge, source, frame), so a value shared across relations credits both; and
under a ``NullEpisodeLog`` nothing is ever excluded, so bad marks cannot accrue
— the 0q tradeoff surfacing again.

The FIAT namespaces are not trust but decree: ``act:*`` is the learner's own
committed moves (invariant #7) and ``correction*`` is its owner's deliberate
voice. Both carry ``commit_k`` by construction, earn nothing, and lose nothing
— a correction is accountable through the log, not through reputation.
"""

from __future__ import annotations

FIAT_ACT = "act:"
FIAT_CORRECTION = "correction"


def is_fiat(source: str) -> bool:
    """True for the reserved namespaces whose word is authoritative by
    construction rather than by track record: the learner's own acts and the
    owner's corrections (``correction`` or ``correction:*`` — the latter also
    matches the k-witness form an earlier release wrote)."""
    s = str(source)
    return (s.startswith(FIAT_ACT) or s == FIAT_CORRECTION
            or s.startswith(FIAT_CORRECTION + ":"))


def weight(good: int, bad: int, *, commit_k: int, authority_k: int,
           penalty: float) -> float:
    """The witness weight of one source's testimony in one relation class.

    ``(1 + good) / (1 + good + penalty * bad)`` — 1.0 with a clean slate, driven
    down by each caught lie (``penalty`` makes a lie cost more than a truth
    earns, so distrust is quick and forgiveness slow), asymptotically restored
    toward 1.0 by an ongoing good record. A record of ``authority_k`` clean
    corroborated facts earns ``commit_k``: sole-witness commitment in that
    class. One caught lie forfeits authority outright (the cliff is the point:
    betrayed trust does not degrade gracefully) and ``authority_k <= 0``
    disables authority altogether."""
    if bad == 0 and authority_k > 0 and good >= authority_k:
        return float(commit_k)
    return (1.0 + good) / (1.0 + good + penalty * bad)
