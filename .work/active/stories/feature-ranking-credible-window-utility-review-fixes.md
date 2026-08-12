---
id: feature-ranking-credible-window-utility-review-fixes
kind: story
stage: done
tags: [bug, analytics, advisory, ui, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-usefulness-contract]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Credible-window utility standard-review fixes

## Brief

Close every receiver-confirmed finding from the feature's single standard review before publication:

- exclude prior mass only for archetypes affected at the current boundary, not any historical ban;
- record explicit-null stored horizons as real confirmed-ban clamps with both candidates;
- use preceding-regime camp composition for prior-only supported parents;
- serialize exact observed count, prior contribution, and decision share per row, make
  `transition-prior` presence outrank imputation quality, and align first-read/field-basis copy;
- record degraded written artifacts as written and make unavailable utility operationally degraded;
- add hermetic affected/unaffected/new/prior-only, August-10-shaped zero-grounded-but-supported,
  first-read/JS, refresh/status, and compatibility regressions;
- return `observed-thin` when no preceding confirmed regime exists;
- reject a practical call outside the rendered ranked prefix and inconsistent useful/degraded status.

The fix keeps proof-grade production ordering and benchmark authority unchanged, does not rerun the
future-only benchmark, and requires receiver verification rather than a second independent review.

## Implementation notes

- `era_horizons` now treats an explicit `stable_since: null` as a real analyzed candidate when a
  confirmed ban affects the entity, publishing `stored_since`, `affected_since`, and the clamp
  flag together. Legacy unaffected and ban-only payloads retain their compact shape.
- Transition stabilization filters the lifetime affectedness map to the current confirmed boundary.
  The preceding regime is absent when no earlier confirmed opening exists, yielding
  `observed-thin`; otherwise the deterministic bounded prior retains unaffected historical mass.
- Camp field shares use the preceding-regime camp composition for prior-only supported parents.
  Archetype and camp rows now carry observed count, prior contribution, decision share, and field
  evidence kind; the browser's field-basis and practical first-read copy distinguishes observed
  decks from decision pseudo-decks.
- `transition-prior` is classified before imputation dominance. The usefulness validator now
  checks the rendered ranked prefix and useful/degraded consistency. Degraded artifacts remain
  written, while unavailable utility marks refresh and scheduled status degraded.

## Exact verification

- Focused: `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/analytics/eras/test_consume.py tests/test_field_model.py tests/test_positioning.py tests/test_decision_refresh.py tests/test_refresh_best_call_ranking.py tests/test_ops_status.py tests/test_scheduled_refresh.py` — passed.
- Authoritative: `PYTHONPATH=. uv run --no-sync python -m pytest -q` — **3845 passed, 1 skipped**.
- Added hermetic coverage for explicit-null clamps, current-boundary affected/unaffected prior
  semantics, no-preceding-regime cold starts, transition-prior precedence, prior-only/public row
  provenance, first-read JavaScript compatibility, ranked-prefix validation, unavailable utility,
  degraded artifact publication, and scheduled/legacy parity.
- No benchmark rerun, live HTML refresh, database mutation, or `uv.lock` change was performed.

## Deviations / adjacent issues

- The smallest faithful row contract applies transition provenance to every archetype and camp row;
  the existing parity expectation was extended additively to acknowledge those new fields. No
  unrelated production issue surfaced and none was parked.

## Closure

Receiver verification is complete for all eight connected review blockers. Standard policy requires
no second independent review; the parent feature may close directly after this story commit.
