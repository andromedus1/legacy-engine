---
id: gate-cruft-parse-decklist-stale-docstring
kind: story
stage: done
tags: [cleanup, documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-15
---

# Stale "previously said" migration prose in `_parse_decklist` docstring

## Confidence
Low

## Category
stale comment

## Location
`advisory/report.py:40-43`

## Evidence
```python
"""... Error messages previously said ``_parse_decklist:``; the promoted function says
``parse_decklist:`` — callers catching ``ValueError`` should match on the exception type ..."""
```

## Removal
Rolling-foundation: drop the "previously said …" historical framing (git carries history). Keep
only the present-tense load-bearing advice ("match on exception type, not the prefix string") if
still relevant.

## Resolution (2026-06-15)
Docstring rewritten to present tense: kept the load-bearing advice ("match on the exception type,
not on any message prefix"), dropped the "previously said …" history. Bonus: removed the adjacent
dead `_COUNT_RE` regex (defined in `report.py` but used nowhere — the live one is in
`models/decklist.py`) and its now-unused `import re`.
