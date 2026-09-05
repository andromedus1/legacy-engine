---
id: story-remove-ranking-leader-tiles
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
