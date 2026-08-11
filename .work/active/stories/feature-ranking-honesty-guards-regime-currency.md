---
id: feature-ranking-honesty-guards-regime-currency
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-ranking-honesty-guards
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Typed field regime currency

## Brief

Measure the share of a global field backed by current-regime observations, accept an exact custom
current-regime numerator only when count-backed, and emit named informational/warning audit lines.
Undated custom aggregates degrade to an explicit unavailable reason rather than a fabricated rate.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` section. Do not add refresh,
card-dimension, monitoring, reweighting, or other `feature-decision-data-currency` responsibilities.

## Implementation notes

- Added immutable `RegimeCurrency` evidence to `FieldDistribution`. Global fields measure the
  positionable population with the same definition, provenance, and half-open window as the field;
  the numerator is clamped to the current `regime_windows()` boundary.
- Custom fields accept `# current_regime_n: N` only with per-line counts or an allocated
  `# effective_n`. Missing dated evidence degrades to the typed reason `unavailable for undated
  aggregate`; malformed or impossible numerators fail fast.
- Advisory CLI field loads now emit the named currency audit line before result data, warn below
  50%, and warn explicitly when currency is unavailable. No refresh, reweighting, acquisition, or
  card-dimension behavior was added.
- Verification: `uv run --no-sync python -m pytest tests/test_field_model.py
  tests/test_advise_report.py tests/test_advise_field.py -q` — 192 passed.
