---
id: epic-sideboard-core-and-hedge-hedge-allocator
kind: feature
stage: drafting
tags: [advisory, sideboard, fast-follow]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-dedicated-core, epic-sideboard-core-and-hedge-output-contract]
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Stage-2 hedge allocator (FAST-FOLLOW)

## Brief

Fill the slots the dedicated core left open (up to an operator cap) with **hedge** cards chosen for
robustness against field uncertainty, rather than padding the field already covered. This is the
fast-follow wave — **separable from the v1 core fix**, which already ends the padding on its own.
The hedge optimizes coverage over a *wider* field than the point estimate: reuse `positioning.py`'s
Dirichlet share draws as the ambiguity set (and/or blend the local field toward the global/online
field), with a strong **1-of diversity preference** (reuse the `U_redundancy` concavity — it falls
off fastest here). Adds the **insurance** label that the output-contract feature reserved.

Per the brief this is the NEUTRAL/judgment region: expose the dial (off / expected-coverage /
CVaR-α), default to a mild expected-coverage hedge, and **never let the hedge override a dedicated
core commit**. This feature carries the most open design judgment in the epic (how wide the
ambiguity set, expected vs CVaR, which α) — resolve it in its `/feature-design` pass against the
brief's framing; not pinned here on purpose.

Does NOT change the core or the output shape — it fills reserved slots and sets the insurance label.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: **fast-follow**, after the v1 core wave. Consumes the dedicated core + the output
  contract's reserved insurance slots. Deferrable — the core fix is independently shippable.

## Inherited design decisions
- Hedging is primarily the operator's job; the model hedges only in flex slots, never overriding a
  core commit.
- Expose an aggressiveness dial (off / expected / CVaR-α); default mild expected-coverage. Don't bake
  in a hedge-aggressiveness constant.
- Diversity-preferring (1-ofs); reuse the concave value's redundancy term.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §3 (the hedge — DRO/CVaR framing, ambiguity set, the
  judgment dials) — the load-bearing section for this feature.
- `docs/briefs/advisory-methods.md` §2 (the Dirichlet share posterior to reuse as the ambiguity set).

## Foundation references
- `src/legacy_engine/advisory/positioning.py` — Monte-Carlo Dirichlet share draws (the ambiguity set).
- `src/legacy_engine/advisory/field.py` — `FieldDistribution` + Dirichlet `counts`; local→global blend.
- Patterns: [[honest-degrade-marker]], [[objective-search-split]].
