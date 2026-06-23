---
id: idea-sb-color-contingent-hate
created: 2026-06-15
tags: [advisory, sideboard]
---

Hoser catalog + model: represent **color-contingent hate** and de-duplicate functionally-identical
hosers.

Found in the test-drive: the engine recommended **3 Hydroblast + 1 Blue Elemental Blast** as if they
were distinct coverage — but oracle text confirms **both target RED** (they're the same card; the
anti-*blue* blasts are Red Elemental Blast / Pyroblast, uncastable in U/B). Root cause is data +
modeling:
- `data/hosers/legacy.json`: **Hydroblast is mis-tagged** `attacks: ['greedy-manabase','low-interaction']`
  (it counters/destroys red, not manabases). **Blue Elemental Blast and Red Elemental Blast aren't in
  the catalog at all** — BEB only appeared via empirical promotion with the generic `'combo'` fallback
  tag, so the engine couldn't tell it's identical to Hydroblast.
- The vulnerability-tag system (graveyard-reliant / ramp / combo / creature-based / ...) has **no
  concept of color-contingent hate** ("anti-red", "anti-blue"), so color blasts get shoehorned into
  archetype tags awkwardly and stacked as if distinct.

Fix direction: (a) add BEB + REB to the catalog with correct attribution and fix Hydroblast's tag
(the catalog edit is ~one line and low-risk); (b) give the model a notion of color-contingent hate
and/or de-duplicate functionally-identical hosers so it won't recommend redundant copies as separate
coverage. (a) is a quick data fix; (b) is the deeper modeling change.
