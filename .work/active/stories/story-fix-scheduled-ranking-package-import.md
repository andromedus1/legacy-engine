---
id: story-fix-scheduled-ranking-package-import
kind: story
stage: done
created: 2026-08-16
updated: 2026-08-16
tags: [infra, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Make scheduled ranking generation independent of repository import paths

## Brief

Make `legacy-engine ops scheduled-refresh` load the production ranking generator through a
package-owned boundary so an installed console entrypoint can publish the ranking without the
repository root on `sys.path`. Preserve direct `scripts/refresh_best_call_ranking.py` compatibility
and the existing last-good atomic publication behavior.

## Simplification opportunity

Centralize the existing absolute-path script loading pattern behind one small package adapter and
reuse it from scheduled and bundle publication; do not relocate or rewrite the mature generator in
this focused repair.

## Symptom

The installed `.venv/bin/legacy-engine ops scheduled-refresh` command completed source refresh,
card reconciliation, labeling, camp application, and era detection, then failed at ranking with
`No module named 'scripts'`. The atomic publication boundary preserved the last-good HTML and the
durable operational status recorded the failure.

## Root cause

`DefaultDecisionRefreshPorts.write_ranking` imported
`scripts.refresh_best_call_ranking`. The `scripts` namespace is reachable when Python starts from
the repository root but is not part of the installed wheel or editable package import boundary, so
the console entrypoint could not resolve it when repository root was absent from `sys.path`.
`best_call_bundle` already avoided that assumption with an absolute-path loader, but the scheduled
port did not share the boundary.

## Fix approach

Move the established absolute-path loader into the package-owned
`legacy_engine.advisory.best_call_generator` adapter, use it from both scheduled and bundle
publication, and leave the mature generator script and direct CLI intact.

## Regression test

`tests/test_decision_refresh.py` removes repository root from `sys.path`, purges cached `scripts.*`
modules, loads the mature generator through the package adapter, and asserts the default ranking
port publishes one typed current target through that adapter.

## Implementation notes

- Execution capability: GPT-5.6 high; a narrow package-boundary repair was selected because the
  failure was deterministic and the mature 2,156-line generator did not need relocation.
- Files changed: `src/legacy_engine/advisory/best_call_generator.py`,
  `src/legacy_engine/advisory/best_call_bundle.py`,
  `src/legacy_engine/workflows/decision_refresh.py`, and `tests/test_decision_refresh.py`.
- The regression first failed because `legacy_engine.advisory.best_call_generator` did not exist;
  after the repair it passes while repository root is absent and no `scripts.*` module is cached.
- Confirmation evidence: the isolated regression and bundle tests pass (9 tests); the complete
  ranking/scheduler-focused set passes (82 tests); a broad run reached 2,921 passed and 1 skipped
  with no failures before it was intentionally interrupted rather than repeat the already-green
  expensive ranking cases. The parent operator will run the full scheduled wrapper once after this
  bounded fix review.
- Direct script compatibility remains covered by `tests/test_refresh_best_call_ranking.py` in the
  82-test focused set. Atomic publication behavior is unchanged.
- Adjacent issues parked: none.

## Review (2026-08-16)

**Verdict**: Approve

**Blockers**: none
**Important**: none
**Nits**: none
**Rejected**: none

**Notes**: Bounded inline review of a standalone fix story; no independent, fresh-context, or
cross-model reviewer ran. Correctness, regression coverage, design alignment, fixed-path safety,
public CLI compatibility, and foundation-assertion lenses passed. The adapter resolves only the
configured repository generator path, introduces no user-controlled import path, and leaves the
generator's direct CLI and atomic write boundary unchanged. The complete scheduled wrapper remains
the deliberately deferred operational confirmation because it repeats the expensive live ranking
generation; the isolated installed-entrypoint condition and all 82 relevant tests are green.
