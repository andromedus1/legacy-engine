---
id: gate-patterns-fix-neutralized-by-vocab
kind: story
stage: drafting
tags: [refactor]
parent: null
depends_on: []
release_binding: null
gate_origin: patterns
created: 2026-07-04
updated: 2026-07-04
---

# Enforce the neutralized_by capability vocabulary at load (closed-vocabulary pattern)

## Divergence
linchpins.py:179-185 — `neutralized_by` is a documented 8-token vocabulary (impact.py:132) but the loader accepts ANY string; a typo'd token loads silently, unlike symmetry/cast_requires in the sibling hoser loader.

## Fix
Add `_VALID_NEUTRALIZED_BY` frozenset + membership check raising ValueError naming token + allowed set, per closed-vocabulary-fail-fast-token. Pure additive validation; add fail-fast test.
