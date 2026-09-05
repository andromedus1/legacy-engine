---
id: bug-ranking-evaluation-override-source-keys
kind: story
stage: implementing
parent: feature-validated-historical-evidence-promotion
depends_on: [feature-deck-rankings]
release_binding: null
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

## Scoped repair

Single-owner child checkpoint within the authorized evaluator feature. The private handoff's
override_sources keys must exactly match cell_overrides; ordinary source notes remain in the
publication ledger. Apply the same selection already used by the publisher. Verification is the
real freeze regression plus focused projection checks. No new abstraction or API behavior is
needed. The evaluator worker owns this repair alongside accepted provenance changes.
