---
id: story-sort-superarchetype-columns
kind: story
stage: implementing
tags: [analytics, ui]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-09-05
updated: 2026-09-05
---

# Sort the superarchetype table by column

## Brief and design
Make all five superarchetype headers clickable using the existing archetype-table
button style and direction arrows. Keep this table's sort independent of archetype/camp
ranking controls. Numeric columns begin descending, Plan begins alphabetically;
repeated clicks reverse direction. Missing values stay last, ties use plan label,
and expanded details stay with their plan. Local scenarios can still sort plan shares
when performance/floor values are unavailable. Preserve keyboard focus after rendering.

## Scope and verification
One template change, owned inline by the host; standard bounded standalone-story review.
No mock needed: this reuses the existing header interaction without changing layout.
Check both actual global/local pages in Chromium for every column, both directions,
missing values, expansion retention, keyboard activation, and unchanged archetype order.
Regenerate outputs from the tracked template. No foundation contract changes or new
permanent tests are needed for this reversible display interaction.

## Simplification
Reuse existing table styles, decision values, coverage calculation, and expansion state.
