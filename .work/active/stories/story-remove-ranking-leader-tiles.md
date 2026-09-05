---
id: story-remove-ranking-leader-tiles
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

# Remove redundant ranking leader tiles

Remove the Performance leader and Matchup floor leader tiles as requested. Keep
the two sortable table priorities, rankings, map, and refresh insights. Delete the
unused tile renderer and styles; preserve the shared label style used by What changed.
Update existing tests that asserted removed tile contents to check their retained
table counterparts. Regenerate global/local HTML from the unchanged analytical payloads
and the tracked template; this presentation change needs no data acquisition or refit.

Inline host implementation and bounded standalone review. Existing-component removal
needs no mock. Verify table sorting, filters, expansion, and no browser errors; run
the existing report tests. No new permanent tests for this small visual removal.

## Implementation, verification, and bounded review
Removed the section, tile-only CSS, renderer, and render call. Existing tests now
verify retained table evidence and filters instead of deleted tile contents. Both
global/local pages were atomically regenerated through the tracked template with
byte-equivalent analytical payloads. No data acquisition/refit was needed. The
scheduled-refresh status remains the historical record of its last scheduled run.

48 report tests pass. Chromium verified both outputs at desktop and 390px widths:
no leader tiles, working table sorts/expansion, coverage filters, agency map,
no horizontal page overflow or JavaScript errors. Runbook/README updated; generated
knowledge index has zero errors and six pre-existing warnings.

Bounded inline review: approve. Removed code has no remaining consumers, the shared
What changed label style stays, and analytical decisions remain unchanged. Updated
assertions preserve coverage of sorting, thin/prior cells, intervals and escaping.
No independent code reviewer was used for this standalone story; no adjacent issues.
