---
id: gate-cruft-overprice-factor-dead-param
kind: story
stage: drafting
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
---

# `overprice_factor` threaded into the pure ranking core but never used there

## Confidence
Medium

## Category
unused argument (dead parameter + dead call-site argument)

## Location
`advisory/acquire.py:166` (param on `_rank_acquisitions`); passed at `acquire.py:648`

## Evidence
```python
def _rank_acquisitions(..., overprice_factor: float = _DEFAULT_OVERPRICE_FACTOR, ...):
    # body references overprice_factor ONLY in its docstring, never in code
plan = _rank_acquisitions(..., overprice_factor=overprice_factor, ...)  # line 648
```
The overpriced-printing logic actually runs in the orchestrator (acquire.py:622) BEFORE the core
is called; the core uses `over_cover_factor`, not `overprice_factor`.

## Removal
Drop the `overprice_factor` param (acquire.py:166), the call-site arg (acquire.py:648), and the
stale "overpriced-printing" docstring bullet. Verify `_rank_acquisitions` unit tests don't pass it.
