---
id: idea-bigmana-ramp-archetype-tag
created: 2026-06-06
tags: [advisory, archetype]
---

The vulnerability-tag taxonomy (whattoplay.py: graveyard-reliant, combo, low-curve, greedy-manabase, creature-based, low-interaction, storm-reliant) has no tag for **colorless big-mana / ramp** decks — Tron, Post (12-Post / Cloudpost), Eldrazi. These aren't "greedy-manabase" in the dual-land sense (they run colorless utility lands, not fragile rainbow manabases), so the existing greedy-manabase hosers (Wasteland, Back to Basics, Blood Moon) only partially apply, and dedicated answers (Harbinger of the Seas, Null Rod, Pithing Needle, Sphere effects) map to nothing.

Add a `ramp`/`big-mana` composition tag (heuristic: high count of colorless utility/ramp lands + low average colored-pip requirement, or presence of Urzatron/Cloudpost/Eldrazi-temple signatures) and the corresponding hoser mappings. This matters acutely right now: Tron spiked to 9.1% (the #1 deck) in the post-Undercity-Informer regime and is **completely uncovered** by both the matchup matrix and the hate model. Pairs with [[idea-hoser-catalog-expansion]] and [[idea-positioning-field-coverage-gap]].
