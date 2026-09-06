---
id: feature-card-name-reconciliation-closure-provider-serialization
kind: story
stage: done
tags: [ingestion, data-quality, benchmark]
parent: feature-card-name-reconciliation-closure
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Resolve verified provider serialization shapes

## Brief

Implement Unit 1 from the parent design: evidence-scoped deterministic candidates for verified
set-prefix, duplicated-name, duplicated-final-face, and localized-face serialization, with exact
canonical-target and provider guards. Preserve every ambiguous, unsupported, or speculative value.

## Acceptance criteria

- The parent Unit 1 acceptance criteria are green.
- Focused reconciliation tests cover each positive class and every named safety boundary.
- Implementation notes record the admitted rule registry and any corpus discrepancy.

## Implementation notes

- Execution capability: direct cohesive implementation; the typed registry, resolver seam, and
  safety regressions are one bounded reconciliation unit.
- Review weight: standard, inherited from the parent feature/default project policy.
- Files changed: `src/legacy_engine/ingestion/card_coverage.py`,
  `src/legacy_engine/data/card_name_aliases/legacy.json`, and
  `tests/test_card_name_resolution.py`.
- Tests added: positive regressions for all four admitted shapes and fail-closed coverage for
  undeclared prefixes, unsupported/mixed providers, absent targets, invalid three-face forms, and
  unique localized-face composition.
- Simplification: one typed provider registry replaces repetitive exact aliases while exact curated
  aliases remain authoritative for exceptional historical spellings.
- Discrepancies from design: exact curated aliases run before normalized canonical matching so the
  declared authority order is actually enforced; the public candidate helper also accepts
  `resolved_at` so emitted audit evidence remains deterministic in tests.
- Registry evidence: MTGmelee rules admit only the ten observed set codes and three exact face/name
  structures. Provider provenance must be singular, and every result must already exist verbatim in
  the canonical card dimension.
- Verification: `24 passed` in `tests/test_card_name_resolution.py`; Ruff passes on touched Python.
- Adjacent issues parked: none.
