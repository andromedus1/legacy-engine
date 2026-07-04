---
id: idea-consign-to-memory-tag-differentiation
created: 2026-07-03
tags: [advisory, sideboard]
---

# Consign to Memory winners-only divergence → missing colorless/ability axis

Field-scoped backtest: Consign is in **95.7%** of Boulder-relevant top-finisher Dimir boards but
never recommended. Mechanism (confirmed): its catalog `attacks = {combo, storm-reliant}` is a strict
subset of Force of Negation's `{combo, storm-reliant, noncreature-reliant}`, so under correct
submodular marginal-gain FoN dominates and Consign's marginal is ~0 once FoN is picked — inherent
tag-subset dominance, not a solver bug.

**Oracle (DB-verified 2026-07-03):** `{U}`, "Replicate {1}" + **"Counter target triggered ability or
colorless spell."** It counters COLORLESS spells and TRIGGERED ABILITIES only — not a general
counterspell. (An earlier version of this item mis-stated the card from memory — twice, once each by
two different models — which is itself evidence for [[idea-card-semantics-rules-layer]].)

**Fix direction:** the reason winners run BOTH FoN and Consign is that Consign answers an axis FoN
cannot: **triggered abilities and colorless spells** — Saga chapter triggers (Black Saga Storm /
Blue Artifacts), storm-count triggers, Chalice triggers, Eldrazi/colorless spells. The tag vocabulary
has no axis for this, so the two cards look like subset/superset when they're actually complements
in a colorless/trigger-heavy field. Add a mechanics-derived axis (e.g. `colorless-reliant` and/or
`trigger-reliant` — an archetype whose plan runs through colorless spells or key triggered
abilities), emit it from composition in whattoplay.py, and attach Consign (and Stifle-likes) to it.
Validate: Consign should move winners-only → overlap on the field-scoped backtest without any
empirical prior.
