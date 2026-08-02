---
id: feature-strategic-plan-best-call-viz
kind: feature
stage: drafting
tags: [analytics, viz, ui]
parent: null
depends_on: [epic-superarchetype-layer-three-level-page]
release_binding: null
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Strategic-plan table in Best Deck / Best Call

## Brief

Add a curated semantic layer above composition-derived superarchetypes to the existing self-contained
Best Deck / Best Call HTML. Each archetype has one primary strategic plan for aggregation and may
carry secondary explanatory labels: Disrupt and pressure, Go off, Go over, Go wide, or Lock and
outlast. Recompute plan-versus-plan performance from decisive matches rather than averaging rendered
archetype percentages. Render the plans as the same sortable/filterable metric table used by
Archetypes and Camps; each row expands through an accessible semantic control into the selected-plan
portrait plus exact opponent-plan ledger. Remove the strategy-family agency map and camps × parent
opponents figure. Keep composition-derived superarchetypes as the internal statistical-borrowing
layer rather than conflating composition with strategic intent.

The arc ends in `decks/best-deck-best-call-ranking.html`; it does not create a separate archetype
page. The portrait/data contract should be reusable by the future `DeckDashboard`.

## Strategic decisions

- Primary strategic plan alone owns aggregation; secondary plans explain hybrids without double-counting.
- Same-plan matches contribute structural 50% to field expectation but cannot set the floor.
- Plan results come from underlying decisive matches and retain window/sample/provenance fields.
- Existing visual language is locked; selected mock direction is the Option 1 + 2 hybrid.

## Mockups

- Comparison: `.mockups/screens/epic-superarchetype-layer-three-level-page/index.html`
- Selected: hybrid of `strategy-option-1.html` and `strategy-option-2.html`, approved 2026-08-02.
- Accessibility contract: `strategy-option-1-sr.html`.

## Simplification

Delete the two low-value heatmap renderers and their DOM/CSS after the table replaces them. Reuse
the existing table sorting/filtering/ledger machinery instead of adding a parallel widget system.
