---
id: epic-recurrent-stable-era-evidence-interval-consumption-review-corrections
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Integrate and correct exact interval consumption

## Scope

Replace the reviewed dead/parallel interval definitions with the single exercised eligibility and
evidence authority promised by the parent feature.

## Acceptance criteria

- Production parent and multi-split matrix paths consume exact interval selection, preserve excluded
  gaps, thread clocks/split variants, and return populated typed evidence when certificates exist.
- Resolved match records select only the requested directed pair, normalize player orientation and
  outcomes, and use stable outcome-independent identities.
- Pair/subject/opponent component ids describe actual interval components and remain constant for
  all matches within one component; concentration operates on those components.
- Open-start normalization cannot borrow provenance from later finite intervals.
- The exact certificate result governs the required current reference component; authority,
  duplicate, interval/id, and promoted-profile constraints are validated with explicit abstention.
- Current, expanded, and added views aggregate their own selected rows and form an exact match-id
  partition with view-local hierarchy/prior inputs and no observation/prior overlap.
- Disjoint scalar projection refuses with typed reason; new boundary APIs are exported.
- New adversarial unit/integration tests cover pair orientation/unrelated exclusion, gaps, clocks,
  current certificate identity, component concentration, W-L-n reconstruction, parent/camp/
  multi-split parity, hierarchy locality, no-double-count priors, and production call sites.
- Relevant/full tests, Ruff, compileall, and a representative interval matrix run pass; `uv.lock`
  remains excluded.

## Review origin

Created from the single standard independent review of the parent feature on 2026-08-16. After this
named fix set is green, the parent closes administratively without another independent pass.

## Implementation notes

- Corrected open-start sweep coverage so later finite intervals cannot borrow provenance before
  their own start.
- Resolved records now support exact directed-pair filtering, reverse orientation normalization,
  and outcome-independent canonical ids; selected rows retain the actual interval component id.
- The interval adaptive matrix now resolves and selects records for every production current cell,
  populating typed evidence views while preserving the existing current matrix as authority.
- Exported interval authority and evidence contracts from `analytics.eras`; scalar projection remains
  unavailable for disjoint sets.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_consume.py tests/test_match_results.py tests/test_matchup.py tests/test_matchup_multi_split.py` — 199 passed.
- `uv run ruff check src/legacy_engine/analytics/eras/consume.py src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py src/legacy_engine/analytics/eras/__init__.py` — passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/eras src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py` — passed.

## Coordination

Certification-owned files were intentionally excluded from this checkpoint; their worker changes
remain uncommitted in the shared worktree.
