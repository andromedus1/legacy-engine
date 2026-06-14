---
id: feature-bigmana-ramp-tag
kind: feature
stage: drafting
tags: [advisory, archetype]
parent: epic-bigmana-coverage-sideboard-fidelity
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# `ramp`/`big-mana` vulnerability tag + hoser mappings

## Brief
Colorless big-mana / ramp decks (Urzatron, Cloudpost/Post, Eldrazi) are completely outside the hate
model — there's no `ramp`/`big-mana` composition vulnerability tag, so Tron (current regime #1 at ~9%)
falls between `greedy-manabase` and uncovered, and its dedicated answers (Harbinger of the Seas, Null
Rod, Pithing Needle, Damping Sphere) map to nothing. Add a `ramp`/`big-mana` composition tag (signatures:
Urzatron lands / Cloudpost / Eldrazi temples, high colorless utility-land density, low colored-pip
requirement) in `advisory/whattoplay.py` vulnerability tagging, plus corresponding hoser→tag mappings so
the recommender answers big mana. Gated-additive: existing tags/coverage unchanged.
