---
id: feature-ranking-credible-window-utility-horizon-clamp
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: feature-ranking-credible-window-utility
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Confirmed-ban lower bound for entity horizons

## Brief

Implement Unit 1 of the parent feature: combine stored/detected entity eras with confirmed direct
ban affectedness so the later boundary wins, while unaffected entities retain admissible history.

## Implementation notes

- Converted `EraHorizon` to the shared `LegacyEngineModel` boundary and added additive candidate
  provenance (`stored_since`, `affected_since`, `clamped_by_confirmed_ban`).
- `era_horizons` now computes direct affectedness independently for each requested entity and its
  mapped parent, taking the later confirmed material-impact date. A stored/parent horizon that is
  older becomes `ban-clamped` with an explicit ban trigger; unaffected and ban-only paths preserve
  their prior compact source vocabulary.
- Missing corpus tables remain a safe era-only degrade for small era fixtures; no matrix consumer
  changes were needed, so adaptive single/multi paths continue to consume the same `since` values.

## Verification

- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/analytics/eras/test_consume.py` (22 passed)

## Deviations / adjacent issues

- The design sketch names a typed `ProvenanceFilter`/`BanEvent`; this repository currently exposes
  provenance as `str | None` and curated B&R events as `(date, card, reason)` tuples, so the adapter
  accepts the existing tuple shape without introducing a parallel domain type.
