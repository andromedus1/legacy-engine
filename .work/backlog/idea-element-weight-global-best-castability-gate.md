---
id: idea-element-weight-global-best-castability-gate
created: 2026-07-03
tags: [advisory, sideboard]
---

# Element weights hard-gated by the GLOBAL best hoser's deck-specific castability

Found by independent review (2026-07-03), pre-existing from epic-1 B3 wiring (sideboard.py
~1718-1733): each `(archetype, tag)` element's weight is multiplied by the impact of
`best_hoser_for_tag[tag]` — selected globally by swing with no castability input — evaluated with
THIS deck's colors. If the global best answer for a tag is off-color for the deck (e.g. best =
Sheoldred's Edict {B}, deck = mono-U), `castability_factor` returns 0.0 and the element weight
zeroes FOR EVERY CANDIDATE — including castable colorless answers (e.g. Engineered Explosives)
that cover the same tag. Milder variant: a symmetric-floored global best deflates the element
×0.15 for asymmetric alternatives.

Fix: evaluate the impact multiplier with the best CASTABLE-for-this-deck hoser for the tag, or take
the max impact over covering candidates. Test: a mono-U deck's creature-based element stays live
via EE when the global best is off-color black.
