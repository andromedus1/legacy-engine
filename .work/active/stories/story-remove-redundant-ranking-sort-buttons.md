---
id: story-remove-redundant-ranking-sort-buttons
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

# Remove redundant ranking sort buttons

Remove the Performance and Matchup floor toolbar buttons and their Rank by label.
Delete their event listeners, pressed-state updates, and unused pressed-button style.
Keep column-header sorting, search, inactive/tradeoff filters and counts. Remove stale
test assertions for the deleted controls; retain existing sorting behavior coverage.

Inline implementation and bounded standalone review, reusing existing UI without a
mock. Regenerate both reports from unchanged payloads using the tracked template.
Verify header sorts and remaining controls in desktop/mobile Chromium, and run the
existing report tests. Documentation already describes column-based comparisons.
