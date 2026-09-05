---
id: story-sort-superarchetype-columns
kind: story
stage: review
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
User follow-up also requests compact expanded rows: reduce nested ledger cell padding,
put estimates and intervals on one line, retain wrapping for long history notes, and
reduce the surrounding detail inset. Keep the existing readable font sizes.
Check both actual global/local pages in Chromium for every column, both directions,
missing values, expansion retention, keyboard activation, and unchanged archetype order.
Regenerate outputs from the tracked template. No foundation contract changes or new
permanent tests are needed for this reversible display interaction.

## Simplification
Reuse existing table styles, decision values, coverage calculation, and expansion state.

## Implementation and verification
The tracked template now sorts all five plan columns with independent state, stable
label ties, missing-last ordering, direction arrows and aria-sort. Header keyboard focus
survives rerendering; expanded detail rows stay attached. Nested ledger rows use 4px
vertical cell padding and inline intervals, with unchanged font sizes and wrapping history.

48 existing publication/presentation tests pass. Chromium checks on actual global/local
payloads verify every column in both directions, missing-value ordering, unchanged payload
and archetype order, keyboard activation/focus, expansion retention and mobile overflow.
Median expanded matchup row height is 27.3px in both tables/reports. Screenshots inspected
at desktop and 390px widths. No permanent low-value test added for this small UI change.
Documentation scan found no stale assertions; no foundation update needed. Global refresh
is running; saved local output was atomically regenerated from its existing analytical
payload using the updated tracked template.
