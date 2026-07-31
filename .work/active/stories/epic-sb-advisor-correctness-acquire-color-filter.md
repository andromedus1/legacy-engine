---
id: epic-sb-advisor-correctness-acquire-color-filter
kind: story
stage: implementing
tags: [advisory, bug]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-27
updated: 2026-07-31
---

# Color-identity filter for advise acquire + sideboard candidate pool


**`advise acquire` (and the `advise sideboard` candidate pool) suggests off-color
cards the deck cannot cast — no color-identity filter.**

Found dogfooding Dimir Tempo (UB) on 2026-06-27. The acquire buy-list for a UB deck
recommended:
- Blood Moon, Pyroblast  (RED — uncastable in UB)
- Veil of Summer, Carpet of Flowers, Force of Vigor  (GREEN — uncastable in UB)
- Back to Basics  (castable, but actively anti-synergistic for a 2-basic Dimir
  manabase — it would hose the pilot's own nonbasics; arguably needs a
  hurts-my-own-manabase guard too)

A buy-list meant to optimize *my* sideboard must restrict candidates to the deck's
color identity (plus truly colorless/artifact cards like Null Rod, Damping Sphere,
Pithing Needle, Engineered Explosives). Off-color suggestions are noise at best and
misleading at worst.

Fix: derive the deck's color identity from the maindeck (or accept a `--colors`
override) and filter acquire/sideboard candidates to {deck colors} ∪ {colorless}.
Consider a secondary flag for cards whose downside scales with the pilot's own
nonbasic count (Back to Basics, Blood Moon mirror-hate).

Related: [[idea-archetype-conditioned-card-winrate]] (other advisory-honesty gap
found the same session).
