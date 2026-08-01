---
id: idea-superarchetype-matchup-aggregation
created: 2026-07-31
tags: [analytics, honesty, agency-page]
---

**Thin data is the biggest problem to solve on the best-deck/best-call HTML.** Andrew's
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

## Worked example found 2026-07-31 (Aluren ≡ Show and Tell family)

Measured while building the Aluren primer — a concrete case the superarchetype layer would fix:

`Aluren [Acererak the Archlich]` (n=47, since 2026-05-11) vs `Show and Tell` (n=334), maindeck
inclusion ≥50% as the "core":
- **shared core = 15 cards**: Show and Tell, Omniscience, Emrakul, Atraxa, Ancient Tomb, City of
  Traitors, Lotus Petal, Force of Will, Brainstorm, Ponder, Stock Up, Island, Misty Rainforest,
  Polluted Delta, Flooded Strand — i.e. the whole engine
- **core Jaccard = 0.54**
- Aluren-only core: Aluren, Acererak, Boseiju, Forest, Hedge Maze, Tropical Island, Veil of Summer
  (the UG package)
- S&T-only core: Sneak Attack (77%), Volcanic Island, Mountain, Scalding Tarn, Thundering Falls
  (the UR package)

So they are one chassis with two interchangeable second-engine packages, and S&T's own camps are
already `Sneak Attack` (252) / `non-Sneak Attack` (44). A "cheat-into-play combo" superarchetype
would pool all of it — and the pooled opponent cells are exactly what both labels currently lack
(every Aluren cell is n<30).

Note the honesty consequence this cuts both ways: the Aluren build's best-looking cell is
**73.9% vs Show and Tell (n=23)**, which under a superarchetype view is an INTRA-family cell, not
an edge against a distinct strategy. Superarchetype aggregation needs a rule for whether
intra-cluster matches count toward a member's record against its own cluster. See
[[idea-aluren-label-is-show-and-tell-variant]] for the labeling half of this.
