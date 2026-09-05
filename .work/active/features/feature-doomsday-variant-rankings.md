---
id: feature-doomsday-variant-rankings
kind: feature
stage: drafting
tags: [analytics, advisory, ui]
parent: null
depends_on: [feature-deck-rankings]
release_binding: null
gate_origin: null
research_refs: [doomsday-splash-variants, doomsday-pivot-performance, doomsday-variant-experiments]
created: 2026-09-05
updated: 2026-09-05
---

# Doomsday variant rankings and deck learning report

## Authorized outcome
Create a self-contained Doomsday comparison deliverable in the Deck Rankings style:
sortable variant rows, agency map, compact matchup dropdowns, and concrete decklists.
Compare Esper Teferi, Sultai Veil, Grixis Hexing Squelcher, plus omitted mana-base
families grounded in the corpus (Dimir and white/green four-color). Be direct about
tiny or historical samples while still producing useful estimates and insights.
Keep historical observations distinct from current-field projections. Reuse the
existing Doomsday research/candidate lists and current global field/model rather
than restating the dated field guide as a current win-rate study.

## Directional design pass
The user explicitly chose the existing ranking map/table style and blunt small-sample
methods. No open audience or layout decision. Existing components/patterns are the
reference; this specialized report uses their layout and needs no new visual mock.
First inspect exact color/package cohorts and resolvable rounds before fixing the
historical window and estimation contract. Ordinary observational reporting must not
turn published 5-0 leagues into an all-entry win rate or zero evidence into certainty.

## Simplification
Use the shared posterior ranking kernel and read-only corpus extraction. Keep this
report separate from the canonical global rankings and from the older research field
guide. No taxonomy mutation, database migration, ingestion rewrite, or causal ranking.
