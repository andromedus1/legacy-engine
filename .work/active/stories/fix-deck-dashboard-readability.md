---
id: fix-deck-dashboard-readability
kind: story
stage: done
tags: [viz]
parent: epic-deck-viz-platform
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-01
updated: 2026-06-14
---

# Fix: deck-dashboard readability (the maintainer feedback)

## Brief
Post-ship readability fixes to the per-deck dashboard from the maintainer's review of the Dimir Tempo / Lands
dashboards. Three display-only changes (the regime-aware FIELD methodology is confirmed correct and kept
— positioning weights the field granularly, NOT the chart's "Other" bucket):

1. **Meta-share tile — Other floats to the top.** `spec_metashare` sorts the y-axis by share desc, so
   the aggregate "Other" (≈29%) sorts above every real archetype and dwarfs them. Fix: cap to **top-N
   (12)** named archetypes by share and **pin "Other" to the bottom** via an explicit ordered sort list.
2. **Charts don't fill their tiles (trends "much too narrow").** The spec builders set no width, so
   vega-embed renders at the Vega-Lite default instead of filling the col_span tile. Fix: set
   `width:"container"` on each chart spec in the HTML-embed path (`layout._tile_html`) so charts fill
   the grid cell. (Kept OUT of the spec builders — `"container"` breaks static PNG, which has no
   container to measure; PNG export keeps the default fixed width.)
3. **Trends is spaghetti.** Limit the dashboard trends tile to the **top-K (8)** archetypes by latest
   share, always including the subject deck.

Plus a light touch: surface the field basis (current ban-regime window + deck count) in the primer so
the thin-window caveat is more visible.

## Diagnosis notes (for the record)
- Fragmentation is Legacy's inherent long tail, NOT a thin-window artifact: Other = 29% @ current ~12d,
  33% @ 90d, 47% @ full corpus — widening the window makes it worse, so the fix is display (top-N), not
  a window change.
- Positioning's field (`build_global_field`) is granular (`group_other=False`, 0% no-data mass) — the
  chart's "Other" does not feed positioning. `data_coverage≈0.37` is mostly the adaptive matrix's
  conservative per-cell windows on ban-affected pairings — the intended regime-aware tradeoff, honestly
  flagged. Field methodology kept as-is per the maintainer.

## Acceptance
- Meta-share tile: ≤ 13 bars (top-12 + Other), Other rendered last (bottom).
- Dashboard chart tiles fill their width (specs carry `width:"container"` in the HTML embed only).
- Trends tile: ≤ 9 lines (top-8 + subject).
- PNG export path unchanged (no `"container"` width in render_png).
- Full suite green.

## Done
Implemented all three fixes + field-basis primer note. spec_metashare top-12 + Other pinned last (verified: 13 bars, Other_last=True); layout._tile_html sets width:"container" on chart embeds (PNG path untouched); deck_dashboard caps trends to top-8 lines + subject (verified: 8 lines, subject included). +3 regression tests. Suite 1176 green. Re-rendered Dimir Tempo + Lands.
