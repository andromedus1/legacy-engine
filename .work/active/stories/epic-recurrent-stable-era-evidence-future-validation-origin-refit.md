---
id: epic-recurrent-stable-era-evidence-future-validation-origin-refit
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-future-validation
depends_on: [epic-recurrent-stable-era-evidence-future-validation-protocol-registry]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Refit and seal the evidence chain at every origin

## Brief

Build each cutoff-safe origin snapshot, rerun discovery, certification, exact interval consumption,
and every amplification candidate within its two clocks, then freeze a digest-bound common forecast
universe with auditable evidence, service, fallback, and jointly replayable uncertainty.

## Implementation

Implement Unit 2, **Cutoff-safe chained refit and sealed origin forecast**, from the parent feature.
Do not load current derived state or permit a challenger failure to shrink the common pair universe.

## Acceptance

Satisfy every Unit 2 acceptance criterion in the parent feature: two-clock cutoff safety, exact
stage/digest chain, common corpus/baselines, gap/camp/prior integrity, and jointly replayable draws.

## Tests

Implement the file-backed origin and adversarial leakage suites named by Unit 2. Inject future state
at every discovery/certification/interval/amplification boundary and prove sealed bytes do not move.

## Implementation notes

- Added digest-bound `OriginRefitManifest`, frozen prediction, and origin bundle contracts.
- Added injected-artifact `freeze_origin`/`refit_and_freeze_origin` boundary that refuses incomplete
  stage chains and deterministically seals pair-universe/prediction digests without reading latest
  state.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/advisory/test_recurrent_validation_protocol.py tests/workflows/test_recurrent_validation_origin.py` — 6 passed.
- `uv run ruff check src/legacy_engine/advisory/recurrent_validation.py tests/advisory/test_recurrent_validation_protocol.py tests/workflows/test_recurrent_validation_origin.py` — passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/advisory/recurrent_validation.py` — passed.
