---
id: feature-ranking-credible-window-utility
kind: feature
stage: drafting
tags: [analytics, advisory, ui, testing]
parent: null
depends_on: [feature-ranking-honesty-guards, feature-agency-page-methodology]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Credible-window ranking utility

## Brief

Restore the Best Deck / Best Call HTML page as a useful decision surface without weakening its
evidence honesty. A newly confirmed B&R event currently resets the entire field to a tiny post-ban
sample, while the page can simultaneously let an older stored era override the new ban boundary for
archetypes that actually played the banned card. The proof-grade `grounded` contract then acts as a
speaking gate, leaving nearly every row silent even when it has an admissible, uncertainty-bearing
historical window.

Separate three concerns that the page currently conflates: which historical observations remain
admissible after a B&R event, how to estimate a cold-start current field, and how strongly the page
may characterize each ranking. Directly affected archetypes must never borrow pre-ban matchup
results; unaffected archetypes retain their credible entity-era history. During a thin post-ban
field, current observations remain visible but are stabilized by an explicit prior credible field
rather than either replacing it wholesale or pretending nothing changed. Every supported row should
receive a comparable estimate and uncertainty tier; `grounded` remains a valuable high-confidence
badge, not the difference between a recommendation and `n/a`.

The feature also owns a causal postmortem and durable regression contract. Tests must reproduce the
August 10 failure shape and fail if a refreshed page becomes honest-but-vacuous again, if a confirmed
ban fails to clamp a directly affected archetype, or if an unaffected archetype loses valid history
merely because another deck was banned. No estimator may be promoted as predictively validated by
this corrective work; the completed benchmark remains descriptive.

## Strategic decisions

- **Utility and honesty are separate obligations**: serve estimates for admissible evidence with
  visible uncertainty; reserve suppression for truly unscorable rows.
- **B&R affectedness is a hard lower bound**: a newer confirmed material-impact boundary cannot be
  overridden by an older detected/stored era.
- **Cold-start fields are stabilized, never concealed**: show observed post-ban counts and the
  explicit influence of prior credible field evidence.
- **Grounded remains a badge, not an inclusion gate**: high-confidence status still matters, while
  lower-confidence supported rows remain comparable and interesting.
- **The process must test usefulness**: correctness tests alone are insufficient when the output can
  legally collapse into a non-answer.

## Simplification opportunity

Replace the page's independent global-ban default, era-first matchup selection, and candidacy/
grounding suppression decisions with one typed evidence-policy projection consumed by ranking,
recommendation, audit copy, and browser rendering. Remove duplicated interpretations rather than
adding another diagnostic ranking beside the existing ones.

## UI surface

This is an existing single-page HTML surface. Preserve its established visual language, but redesign
the first-read hierarchy so a reader sees: the actionable ranking, confidence/credibility tier, how
the cold-start field was formed, and which evidence was reset by the ban. Advanced ledger and
methodology details remain progressively disclosed.

