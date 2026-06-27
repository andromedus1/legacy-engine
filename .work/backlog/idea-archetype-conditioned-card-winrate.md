---
id: idea-archetype-conditioned-card-winrate
created: 2026-06-27
tags: [honesty, analytics]
---

**Engine honesty: marginal per-card win-rate (`report cards`) is cross-archetype
contaminated and can contradict the within-archetype subgroup truth.**

Concrete case found while dogfooding Dimir Tempo (2026-06-27):
- `report cards --archetype "Dimir Tempo"` showed **Mishra's Bauble at -0.040 marginal
  lift** — reads as a "cut this card" signal.
- But `report subgroup` within Dimir Tempo showed **Goyf+Bauble was the BEST-performing
  cell** (59.7% over 4mo, n=159) vs every no-Bauble config.
- The marginal number is contaminated: Bauble also lives in weaker archetypes
  (Scam, etc.), dragging its global win-rate below the Dimir Tempo reality.

The danger: an archetype-specific keep/cut decision made off the marginal card
win-rate alone would have been backwards.

Fix options (pick at scope time):
- (a) Add an **archetype-conditioned card win-rate mode** that restricts the W/L
  denominator to the archetype's own decks.
- (b) Emit an **honest-degrade warning** when a card's marginal lift conflicts in
  sign with its within-archetype subgroup win-rate.
- (c) **Surface subgroup win% directly inside `report subgroup`** output — it
  currently shows only copy-count deltas, not the W/L split that actually decides
  the question (had to compute that by hand from `standings` this session).

Decision-relevant principle: archetype-specific card keep/cut calls should never be
made off the marginal number alone.
