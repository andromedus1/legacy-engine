---
id: feature-ban-localized-evidence-recovery-exposure-authority
kind: story
stage: done
tags: [analytics, testing]
parent: feature-ban-localized-evidence-recovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-17
updated: 2026-08-16
---

# Exposure-boundary authority and localized clean-interval atoms

## Brief

Implement Unit 1 of the parent feature: add a typed exposure-boundary authority for localized bans
so materially affected entities can contribute clean pre-exposure and post-ban intervals while the
contaminated exposure span remains explicitly excluded.

For the forcing case, Fantasticar exposure is `2026-06-20` through the `2026-08-10` ban. The
implementation must generalize beyond that one card and preserve deterministic provenance for how
each bound was chosen.

## Implementation notes

- Execution capability: GPT-5.6 high; this is a cross-module evidence-authority change with exact
  interval and cardinality risk.
- Review weight: standard (project default); feature review remains the independent boundary.
- Added a typed, validated same-date ban-event exposure authority. Authoritative release dates are
  supported; corpus-first-seen is the deterministic outcome-free fallback used by the current data.
- Compiled explicit clean pre-exposure and post-ban atoms around the positive contamination gap.
  The existing selected-outcome ledger remains the single physical-match selection seam.
- Multi-card bans use one union-materiality cohort gap, preventing a tiny individual card from
  silently widening an entity while retaining every contributing card name.
- Camps bypass localized parent history and remain current-only.
- Tests added: Fantasticar-shaped pre/gap/post recovery, unaffected entity retention, same-date
  multi-card cohort materiality, gap exclusion, reverse-derived selection, and no duplicate match
  ids across a view.
- Simplification: localized evidence reuses `normalize_atoms`, `intersect_atoms`, and the existing
  exact ledger; no second SQL outcome aggregation path was introduced.
- Discrepancies from design: none.
- Adjacent issues parked: none.

## Verification evidence

- `.venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py tests/test_match_results.py`
  — 66 passed.
- `.venv/bin/python -m compileall -q src/legacy_engine/analytics/affectedness.py
  src/legacy_engine/analytics/eras/consume.py` — passed.
