---
id: feature-ranking-credible-window-utility-usefulness-contract
kind: story
stage: done
tags: [analytics, advisory, ui, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-practical-surface]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Usefulness publication contract and causal postmortem

## Brief

Implement Unit 4 of the parent feature: make report usefulness a typed refresh/status invariant and
document the causal failure chain and preventive regression seams.

## Implementation notes

- Added `RankingUtilitySummary` and `validate_ranking_utility` to the refresh workflow. The
  generator serializes the same summary in the HTML metadata and returns it through the refresh
  port; contradictions fail before the writer is accepted, while thin/low-grounded output is
  explicitly `degraded` when a practical call remains available.
- Scheduled status carries the summary additively in `ArtifactIdentity`; old status JSON remains
  readable and new audit output names observed/effective field sizes, prior, and practical call.
- Documented the August 10 causal chain and preventive credible-window/practical/usefulness seams
  in the ranking runbook and architecture, then regenerated all three knowledge-index layers.

## Verification

- `PYTHONPATH=. uv run --no-sync python -m pytest -q tests/test_decision_refresh.py tests/test_ops_status.py tests/test_ops_cli.py` (38 passed)
- `PYTHONPATH=. uv run --no-sync python scripts/gen_knowledge_index.py --lint-only` (0 errors; 6 existing warnings)
- `PYTHONPATH=. uv run --no-sync python -m pytest -q` (3838 passed, 1 skipped)

## Deviations / adjacent issues

- `practical_ranked_actions` is an additive field on the summary so the validator can prove that
  the practical call is actually present in the rendered shortlist; the design sketch listed only
  the selected call and count, which cannot detect that contradiction by itself.
- The generated page remains descriptive and keeps benchmark validation/production ordering
  untouched; this feature makes no predictive-validation claim.
