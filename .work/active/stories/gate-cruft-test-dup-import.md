---
id: gate-cruft-test-dup-import
kind: story
stage: implementing
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: cruft
created: 2026-07-04
updated: 2026-07-04
---

# Drop duplicate _build_coverage_model import (F811) in test_sideboard.py

## Confidence
High

## Category
Redundant import / redefinition

## Location
tests/test_sideboard.py:1963 redefines the import from line 35.

## Removal
Remove `_build_coverage_model` from the second import block; module-level import at line 35 already
binds it. (`_VALUE_GATE` in the same block is covered by gate-cruft-test-unused-imports.)
