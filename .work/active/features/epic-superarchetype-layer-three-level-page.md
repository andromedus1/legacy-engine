---
id: epic-superarchetype-layer-three-level-page
kind: feature
stage: drafting
tags: [analytics, viz]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-chain, epic-superarchetype-layer-best-call-fallback]
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-08-01
---

# Three-level best-call page + superarchetype agency map

## Brief

**Andrew's directive (2026-08-01, verbatim intent):** whenever the superarchetype methodology is
finished and producing nice quality output, add it to the best-deck/best-call doc as a THIRD table
(superarchetype, archetype, subarchetype/camp). Also do an agency map for superarchetype — and
maybe one for subarchetype as well.

Deliverables:
1. **Third ranking table at superarchetype granularity** on
   decks/best-deck-best-call-ranking.html, alongside the existing archetype (View 1) and camp
   (View 2) views — same agency methodology, computed over pooled/licensed superarchetype cells.
   Consider (design option, not committed) nesting: superarchetype row expands to its member
   archetypes, archetype expands to its camps — the full taxonomy as one navigable surface.
2. **Superarchetype agency map**: the S×S strategy-level matchup heatmap. This is where the
   coarse level shines — the brief measured cluster×cluster displayability at 70.3% (K=8) vs
   0.3% at archetype level, so the map is DENSE where the archetype matrix is empty. Agency
   metric definition needs care at this level: worst-grounded-matchup is vs other
   superarchetypes; intra-family cells carry their flag; gates/refusals render as labeled holes,
   never blanks.
3. **Camp-level agency map — RECOMMENDED FORM: rectangular camps × parent-level opponents**,
   which is literally what MultiSplitMatrix produces (cheap since the 26x adaptive build).
   Camp × camp is REJECTED for the map: mostly speculative cells (the thinness this epic exists
   to fight); revisit only if pooling changes that picture.

## Quality gate (Andrew's bar: "nice quality output")
Ships only AFTER -chain and -best-call-fallback are done AND their output has passed a
dogfooding quality review — the pooled/imputed cells must have survived real use before they
anchor a headline table. Do not bind to a release before that review happens.

## Inherited constraints
Epic addenda #1/#2 bind: labeled leans never grounded rows; freshness/churn provenance on every
pooled or imputed number; the I² one-sidedness caveat on the definitional card; page muting rules
apply at all three levels.
