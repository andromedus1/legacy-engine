---
id: epic-recurrent-stable-era-evidence-amplification-review-corrections
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Implement and prove the amplification challenger lane

## Scope

Replace the reviewed scaffolding with the four real, separately falsifiable challenger models and
the immutable diagnostic artifacts promised by the parent feature.

## Acceptance criteria

- A real `IntervalAdaptiveMatrix`/selected-ledger run completes, round-trips by exact id, and uses
  canonical string-keyed payloads without weakening typed pair identities.
- Component hierarchy fits component-level commensurability/partial pooling; composition kernel
  selects and weights eligible non-target donors; strategic-family ladder applies frozen membership
  with leave-target-out support; and skew low-rank ranks 1/2/4 recover directed cyclic structure with
  niche/stability/connectivity refusals. They produce materially distinct synthetic predictions.
- Every method enforces no target-as-donor, no shrunk-cell pseudo-observations, no reverse duplicate,
  no certificate feedback, and no observation/prior overlap.
- Prediction intervals/draws come from deterministic whole-event resampling/refits (not point
  placeholders); service gates use effective support/concentration; fit ids are consistent;
  decomposition has direct/history/borrowed evidence, leave-target-pair-out ablations, honest
  non-additive remainder, imputation state, and borrowed concentration.
- The corpus recomputes/verifies selected-ledger digest and wrapper clock/certificate/evidence
  identity, deep-copies or freezes baseline inputs, and binds both current and expanded baselines.
- Closed discriminated method/profile schemas reject wrong variants, unknown keys, non-finite or
  negative gates; runner honors enabled/order/seed/parameters and exports typed method registry.
- Aligned cross-cell draw artifacts contain actual draws or a complete deterministic event-block
  replay schedule with fitted prediction identity; origin injection and all-case outputs are
  independent from service state.
- Store recomputes run/audit/draw ids, rejects tampering/unknown methods or authority, and has no
  latest/best/winner/promotion path.
- New `tests/analytics/amplification/` adversarial suite covers each hypothesis, negative transfer,
  sparse refusal, identity/tamper, same-corpus fairness, aligned replay, and authority invariants;
  focused/broader tests, Ruff, compileall pass. `uv.lock` remains excluded.

## Review origin

Created from the single standard independent review on 2026-08-16. Once the named fix set is green,
the parent closes administratively without another independent pass.

## Implementation evidence

- Replaced all raw-rate scaffolds with component partial pooling, composition-kernel donors,
  frozen strategic-family ladders, and deterministic skew low-rank ranks 1/2/4. Physical matches
  are consumed once, target/reverse donor leakage is excluded, and directed reverse predictions,
  intervals, and ablations are complement-derived.
- Closed the profile and public package contracts around typed method ids/specs, collision-free
  string pair keys, exact corpus/clock/certificate/structure/baseline identities, typed candidate
  failures, explicit all-case versus served state, and diagnostic-only authority.
- Added deterministic whole-event refit schedules and retained aligned draw values, fit identities,
  origin injection, effective-support/concentration gates, current/history/borrowed decomposition,
  leave-target-out ablations, and non-additive remainder reporting.
- Added content-addressed exact-id storage with read/write validation of the corpus rows, both direct
  baseline views, common universes, audit, replay plan, aligned draw series, method registry, and
  outer run. Typed `MatchupCell` round-trips without degrading to an untyped dictionary.
- Added 619 lines under `tests/analytics/amplification/` covering a real selected-ledger run,
  estimator hypotheses, negative transfer and sparse refusals, leakage and reverse duplication,
  discriminated profiles, origin replay, complement parity, authority, and nested tampering.

## Verification

- `uv run pytest -q tests/analytics/amplification tests/analytics/eras/test_interval_consumption.py`
  — 44 passed.
- Broader match-results, matchup, ranking-measurement, interval, certification, and era-store
  regression selection — 340 passed.
- `uv run ruff check` over changed production and amplification-test paths — passed.
- `.venv/bin/python -m compileall -q src/legacy_engine tests/analytics/amplification` — passed.
- `git diff --check` — passed. Pre-existing `uv.lock` modifications were excluded.
