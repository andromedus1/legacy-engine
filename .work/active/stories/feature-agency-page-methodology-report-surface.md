---
id: feature-agency-page-methodology-report-surface
kind: story
stage: done
tags: [analytics, advisory]
parent: feature-agency-page-methodology
depends_on:
  - feature-agency-page-methodology-kernel
  - feature-agency-page-methodology-grounding-path
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Best Call methodology payload and accessible diagnostic view

## Brief

Serialize package-owned lean, stability, and grounding evidence into the Best Call generator; add
the accessible opt-in diagnostic view and exact runbook contract without changing the gated default,
P(best), candidacy, or evidence strata.

## Implementation

Implement Unit 3 in the parent feature's `## Implementation Units` section after both package-owned
methodology stories are done.

## Implementation notes

- Execution capability: inherited frontier model at high effort; this checkpoint joins typed
  statistical evidence, a generated report contract, and an accessible interactive surface.
- Review weight: standard, inherited from the autopilot caller.
- Files changed: `scripts/refresh_best_call_ranking.py`,
  `scripts/best_call_ranking_template.html`, `docs/analysis/best-call-ranking.md`, generated
  `docs/knowledge-index{,-nav,-detail}.yaml`, and `tests/test_refresh_best_call_ranking.py`.
- Tests added/removed: added deterministic methodology payload/meta, canonical gated parity,
  exact-positive presence, plan-diagonal exclusion, methodology audit, accessible toggle/status,
  stability/path staleness, complete shortfall disclosure, and posterior interval/imputation/
  divergence regressions; no tests removed.
- Simplification: all methodology math and path planning remain package-owned; the generator adapts
  typed ledgers and the browser only renders immutable diagnostics or marks them stale. Existing
  gated row fields, P(best), candidacy, and evidence strata are not overwritten.
- Discrepancies from design: none.
- Adjacent issues parked: none.
- Documentation: the update-documentation workflow aligned the runbook; the normal linted
  knowledge-index workflow regenerated all three layers with zero errors (11 pre-existing
  warnings). No mock was added because the feature extends established controls and disclosures.
- Verification: focused ranking measurement/generator suite — 65 passed; Python compile and template
  JavaScript parse checks passed; full repository suite — 3,668 passed, 1 skipped. The direct pytest
  executable lacks the repository-root import path, so full verification used the authoritative
  `uv run --no-sync python -m pytest -q` invocation and left `uv.lock` untouched.
