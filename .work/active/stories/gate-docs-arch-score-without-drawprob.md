---
id: gate-docs-arch-score-without-drawprob
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: docs
created: 2026-07-04
updated: 2026-07-04
---

# ARCHITECTURE sideboard.py row cites .score() for element weights (draw-prob folded in)

## Drift category
foundation-doc-assertion

## Location
Doc: docs/ARCHITECTURE.md:187 · Code: src/legacy_engine/advisory/sideboard.py:1764, impact.py:99-119

## Current doc text
> element weight ... `field_share × swing × impact(best_hoser, archetype, ...).score()`

## Reality
Element weights now use `.score_without_draw_prob()` (centrality × symmetry × castability); draw-probability lives exclusively in the per-copy taper. `.score()` is used only for the per-card explainability breakdown.

## Required edit
Replace .score() with .score_without_draw_prob() in that clause; state the weight is centrality × symmetry × castability with draw-probability only in the per-copy redundancy taper. Roll forward in place.
