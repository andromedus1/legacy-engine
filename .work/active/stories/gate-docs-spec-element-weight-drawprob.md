---
id: gate-docs-spec-element-weight-drawprob
kind: story
stage: drafting
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: docs
created: 2026-07-04
updated: 2026-07-04
---

# SPEC pillar-4 says element weight includes draw-probability

## Drift category
foundation-doc-assertion

## Location
Doc: docs/SPEC.md:70 · Code: sideboard.py:1764

## Current doc text
> Per-card element weight is impact-decomposed (centrality × castability × symmetry × draw-probability...)

## Reality
Element weight dropped the draw-probability factor (per-copy taper owns it). README:53's per-card BREAKDOWN wording is correct and needs no change.

## Required edit
Drop '× draw-probability' from the element-weight formula or reword: 'the per-copy redundancy taper carries draw-probability separately.'
