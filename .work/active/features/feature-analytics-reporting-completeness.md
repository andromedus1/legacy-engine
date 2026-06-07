---
id: feature-analytics-reporting-completeness
kind: feature
stage: drafting
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Analytics Reporting Completeness

## Brief

A handful of analytics reports have coverage gaps or missing affordances that surfaced during
dogfooding — none individually large, but cohesive enough to design and ship together. All sit in the
Meta & Performance pillar (`analytics/` + `report` CLI) and are additive reporting features, not
behavioral changes to existing math. `/agile-workflow:feature-design` decomposes into child stories.

## Member findings (absorbed from backlog — full text in git history)

- **wrw-windowed** [analytics]: win-rate-weighted meta share (`--definition wrw`) is full-corpus only
  ('skipping wrw under a window') so it can't be windowed to a regime. Make wrw windowable.
- **trends-biggest-movers** [analytics]: `report trends` emits a dense 7-regime × ~28-archetype matrix
  with no digest. Add a 'biggest movers' summary of what actually changed between regimes.
- **head-to-head-matchup-lookup** [analytics]: inspecting one matchup requires reading the full matrix;
  add a direct head-to-head lookup (e.g. `report matchups --a <x> --b <y>`).
- **affectedness-explain** [analytics]: the per-deck ban-affectedness `valid_since` (e.g. why
  Doomsday's window is 2024-12-16) is computed but uninspectable. Add an explain mode that shows the
  derivation (which ban event × which card frequencies drove it).
