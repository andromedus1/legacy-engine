---
id: idea-superarchetype-matchup-aggregation
created: 2026-07-31
tags: [analytics, honesty, agency-page]
---

**Thin data is the biggest problem to solve on the best-deck/best-call HTML.** the maintainer's
framing (2026-07-31): too many cells are unmeasured or speculative, so rows can't be
grounded and the page's honesty gates discard most of the field.

**The idea:** cluster archetypes into **superarchetypes**, then use the archetypes *within*
each superarchetype cluster to generate a win rate against that superarchetype. That way we
get some signal against all the major strategies even when we don't have full data on every
individual archetype inside the cluster.

**What still needs solving:** the method for deriving superarchetype win-rate matchups from
the data actually available — how to aggregate/pool the member archetypes' cells into one
superarchetype cell, and how to handle uneven coverage across members.

Context that makes this intelligible later: the engine already has a two-level taxonomy
(parent archetype → data-driven camp). This adds a level *above* archetype, which the current
matchup/window machinery has no concept of. Relates to [[idea-path-to-grounding]] (converting
discarded coverage into an agenda), [[idea-lean-view-toggle]] (soft-weighting instead of hard
gates), [[feature-ranking-honesty-guards]], and [[idea-adj-field-wr-recompute-divergence]].
