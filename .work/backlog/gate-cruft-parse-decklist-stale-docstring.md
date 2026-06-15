---
id: gate-cruft-parse-decklist-stale-docstring
kind: story
stage: drafting
tags: [cleanup, documentation]
parent: null
depends_on: []
release_binding: null
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
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
