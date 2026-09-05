---
id: bug-ranking-evaluation-override-source-keys
created: 2026-09-05
updated: 2026-09-05
tags: [analytics, advisory]
---

A real file-backed freeze in `tests/workflows/test_served_ranking_freeze.py` fails with
`ValueError: override source labels must name a cell override`. `_publish_deck_rankings`
correctly filters source notes when invoking its own projection, but its private evaluator
handoff stores all source notes. The evaluator passes them as override labels even when
an era/fallback cell is not overridden. Keep the failing integrated test; this is a product
bug in the newly implemented evaluation path, not fixture drift.
