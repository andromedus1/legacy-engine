---
id: epic-gap-discovery-archetype-gaps
kind: feature
stage: drafting
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Archetype-Gap Finder (`report gaps`)

## Brief

Surfaces **under-explored archetypes** — shells with high positioning `S` (well-positioned
versus the current field, per `advisory/positioning`) but low meta-share (per
`analytics/metashare`). These are the strategies the field is sleeping on: strong matchup
math, little adoption. Ranks archetypes by a gap score of the shape `S − g(share)` (reward
strong position, penalize already-popular), confidence-gated so a shell whose `S` rests on
thin matchup data does not surface.

Delivers a new `report gaps` CLI command in the existing `report` family
(`report meta|matchups|tiers|trends|cards`), following that group's established output
conventions and disclaimer wording. This is the **archetype-gap half** of deck-generation
mode 3 — mechanical, composing two already-shipped surfaces; the brief flags it as needing
no external research.

Does NOT cover card-level discovery (the adjacent swap-in half — see the sibling features).
It only ranks whole archetypes, not cards within a deck.

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: independent capability — no shared types with the card-discovery half;
  fully parallelizable with `epic-gap-discovery-adjacency`.

## Inherited design decisions

- **Archetype-gap surface = new `report gaps` command** — fits the existing `report` family
  pattern rather than folding an under-explored column into `report tiers` (keeps the two
  distinct reads uncoupled).
- Gate the gap ranking by the **existing `ConfidenceMetadata` tiers** — never surface an
  archetype whose `S` is computed from thin matchup data.
- The exact gap-score shape (`g(share)`) and display threshold are this feature's own
  design-pass calls.

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §4 (the archetype-gap half — "rank archetypes
  by `S − g(share)`; reuses positioning + metashare; no external research required").

## Foundation references

- `src/legacy_engine/advisory/positioning.py` — `positioning_score` / `PositioningResult`
  (`S` is the well-positioned-vs-field score).
- `src/legacy_engine/analytics/metashare.py` — `compute_metashare` / `MetaShareReport`
  (meta-share per archetype).
- `src/legacy_engine/cli.py` — `report` command group (`@report.command(...)`, ~line 148+).
