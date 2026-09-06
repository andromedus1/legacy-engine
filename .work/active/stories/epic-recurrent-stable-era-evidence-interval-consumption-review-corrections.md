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
- Added adversarial regression coverage for open-start provenance, excluded gaps, stable
  component-level selection, exact id partition, concentration, and prior overlap.
- Current, expanded, and added views now independently build W-L-n cells from selected rows;
  invalid/future certificate envelopes cannot alter the scalar current component, and returned
  interval matrix evidence is populated for parent and multi-split labels.
- Added explicit returned-evidence and DB-backed unavailable-certificate regression tests, plus
  typed scalar refusal assertions.
- Replaced the self-referential cell-rate prior with an exact-view, leave-cell-out hierarchy.
  Subject marginals and camp leave-camp-out parent cells are reconstructed from the canonical
  selected-row corpus; every prior publishes its exact match ids, digest, mean, and source.
- Added the public `SelectedOutcomeLedger`: one canonical physical orientation, stable
  outcome-independent match ids, exact entity eligibility/component/certificate provenance,
  independent clocks, and a deterministic content digest. Reverse-directed views reuse those
  physical ids rather than selecting or persisting a second copy.
- Threaded explicit `camp_parent` through single- and multi-split interval construction. Any pair
  containing a camp remains current-only, so neither a parent certificate nor the other side's
  certificate can expand camp history.
- Hardened exact-run consumption for malformed ledgers, duplicate ids, profile/schema/reference
  mismatches, non-passing guards, non-final certificate status, and unavailable/future knowledge.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_consume.py tests/test_match_results.py tests/test_matchup.py tests/test_matchup_multi_split.py` — 199 passed.
- `uv run ruff check src/legacy_engine/analytics/eras/consume.py src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py src/legacy_engine/analytics/eras/__init__.py` — passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/eras src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py` — passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py` — 3 passed.
- `uv run ruff check src/legacy_engine/analytics/eras/consume.py src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py tests/analytics/eras/test_interval_consumption.py` — passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py` — 6 passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py` — 15 passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras/test_interval_consumption.py tests/test_match_results.py tests/test_matchup.py tests/test_matchup_multi_split.py` — 190 passed.
- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras tests/test_match_results.py tests/test_matchup.py tests/test_matchup_multi_split.py tests/test_ranking_measurement.py` — 423 passed.
- `uv run ruff check src/legacy_engine/analytics/eras/consume.py src/legacy_engine/analytics/eras/__init__.py src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py tests/analytics/eras/test_interval_consumption.py` — passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/eras src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py` — passed.

## Coordination

Certification-owned files were intentionally excluded from this checkpoint; their worker changes
remain uncommitted in the shared worktree.

## Root verification closure

Commit `339407b` closes the named gap with real DuckDB-backed exact-store and matrix tests. The
tests prove exact current/reference/history identity, refusal variants, excluded gaps, populated
directed evidence, camp/single/multi parity, leave-cell-out hierarchy independence, and the
digest-bound selected-outcome handoff required by amplification. Administrative parent
verification remains; no second independent review is required by the feature's review policy.
