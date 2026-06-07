---
id: epic-advisory-output-honesty-field-consistency
kind: feature
stage: drafting
tags: [analytics, archetype, correctness]
parent: epic-advisory-output-honesty
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Field & Regime Consistency

## Brief

Make "what counts as the current field" consistent across the toolset. Two inconsistencies mislead
today. First, `report tiers` defaults to the full corpus (all-time), so it crowned Dimir Reanimator
#1 — a deck dead in the current regime — while the advisory layer already defaults to the current
regime; the two surfaces contradict each other. Second, 'Unknown' is treated as a real opponent in
some surfaces (matchup rows, meta-share) while already excluded from positioning fields, so the same
~8.5%-share placeholder is handled three different ways.

Covers: flipping `report tiers` to default to the current ban regime (with `--all-time` escape),
matching the regime-aware advisory default; applying consistent 'Unknown' semantics everywhere —
**bucket Unknown into the 'Other' tail in fields/positioning (where it's already excluded), but keep
it visible in meta-share as a labeled data-quality signal**.

Does NOT cover: the positioning coverage math (separate feature); sub-archetype variant splitting
(separate backlog item).

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: independent capability — parallelizable with positioning-coverage and transparency.

## Inherited design decisions
- **Tiers default**: flip to current-regime (with `--all-time` escape) for consistency with the
  shipped regime-aware advisory default.
- **Unknown semantics**: bucket into 'Other' in fields/positioning; keep visible + labeled as a
  data-quality signal in meta-share. Apply the same rule across matchup rows so Unknown isn't a
  silent real-opponent anywhere.

## Foundation references
- `docs/SPEC.md` — "Source transparency"; regime-awareness (epic-regime-aware-advisory, done)
- `src/legacy_engine/analytics/metashare.py`, `analytics/matchup.py`, `advisory/field.py`; tiers in `cli.py`/analytics
