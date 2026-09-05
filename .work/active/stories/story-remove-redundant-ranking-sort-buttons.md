---
id: story-remove-redundant-ranking-sort-buttons
kind: story
stage: done
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

## Verification and bounded inline review
Removed both controls, label, listeners, render-time lookups and unused pressed styling.
Only assertions for the deleted control IDs were removed; behavioral sorting tests remain.
48 existing report tests pass. Chromium verified both regenerated reports at 1440px and
390px: header sorting in both directions, search, inactive/tradeoff filters, counts and
no JS errors or page overflow. Analytical payloads are unchanged. Diff check passes.
Bounded host review approves the narrow removal; no independent reviewer or new tests
needed. No stale documentation assertions or adjacent issues found.
