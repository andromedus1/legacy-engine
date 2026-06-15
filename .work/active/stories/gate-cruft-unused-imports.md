---
id: gate-cruft-unused-imports
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
---

# Unused imports — 9 sites (ruff F401-verified)

## Confidence
High

## Category
unused import

## Location
`cli.py:522`, `cli.py:1446`, `cli.py:1808`, `cli.py:2699`, `cli.py:3094`;
`analytics/subgroup.py:15`; `generation/consensus.py:34`

## Evidence
```python
# cli.py:522  — MetaShareReport, compute_all unreferenced in body
from legacy_engine.analytics.metashare import MetaShareReport, compute_all, compute_metashare
# cli.py:1446 — CardValue, card_value_matchup unused
from legacy_engine.analytics.card_value import CardValue, card_value_marginal, card_value_matchup, card_values_vs
# cli.py:1808 deck_cost unused; cli.py:2699 PickTrace unused; cli.py:3094 RefreshResult unused
# subgroup.py:15  `field` imported, never used
# consensus.py:34 Sun Jun 14 20:15:55 MDT 2026 imported, never used (only in SQL strings/docstrings)
```

## Removal
`uvx ruff check src/legacy_engine --select F401 --fix` handles all 9 safely (zero references
in scope). Do NOT touch the string forward-ref annotations (F821 false positives — lazy noqa
imports). Run the suite after.
