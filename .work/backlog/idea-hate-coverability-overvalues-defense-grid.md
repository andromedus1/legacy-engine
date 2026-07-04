---
id: idea-hate-coverability-overvalues-defense-grid
created: 2026-07-03
tags: [advisory, sideboard]
---

# `_hate` coverability over-values Defense Grid (0% of winners, recommended)

Surfaced by the field-scoped `advise backtest` on Dimir Tempo + Boulder (2026-07-03), post
`feature-sfv-weights`. Making `_hate:` self-protection coverable (correctly) turned Defense Grid
into a live candidate that the solver now picks (for `_hate:combo` self-protection), but the
backtest shows Defense Grid at **0% inclusion in 258 Boulder-relevant top-finisher boards** — a
scorer-only false positive.

The divergence is the backtest working as intended (a flag to investigate, not an auto-calibration).
Likely causes to weigh: (a) the `_hate:` element weights are still too high relative to real
opponent coverage even after the coverability fix (the self-protection need is over-stated for a
proactive tempo deck); (b) Defense Grid's own value is over-credited (a symmetric tax that also hits
the caster's instant-speed plays — its `symmetry: symmetric` flag exists but may not discount its
`_hate` coverage); (c) genuinely a mispricing the field hasn't caught (least likely at 0%).

Fix direction: re-examine `_hate:` element weighting + whether a symmetric protective card should
have its `_hate` coverage discounted by its self-cost. Validate against the same field-scoped
backtest (Defense Grid should drop out of the recommended board). Relates to
[[idea-consign-to-memory-tag-differentiation]] (the other backtest-surfaced divergence).
