---
id: idea-variant-conditioned-matchup-cells
created: 2026-07-04
tags: [analytics, advisory]
---

# Variant-conditioned matchup cells — test the tempo-pivot hypothesis properly

Stage-4 comparison (decks/dimir-vs-doomsday-tempo-comparison.md) had to use ARCHETYPE-level
matchup cells: "Doomsday" mixes tempo+turbo+residue camps, so the live harder-tempo-pivot
hypothesis (tempo Doomsday's cells vs blue decks sit closer to Dimir's) remains untested.
The stage-3 split persisted `decks.variant` labels (Tempo n=47 / Turbo n=49, current
regime), which makes variant-conditioned cells COMPUTABLE now: extend the matchup matrix
builder with an optional variant dimension on one side (speculative-tier honesty labels
mandatory at these n). Also generalizes: any archetype with a persisted variant split gets
camp-level matchup resolution. Relates to [[idea-subarchetype-discovery]].
