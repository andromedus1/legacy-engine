---
id: epic-stable-era-windows-discovery-gate-core
kind: story
stage: review
tags: [analytics, archetype]
parent: epic-stable-era-windows-discovery-gate
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-12
---

# Gate C temporal-mixing in the discovery core

## Brief
Unit 1: DeckVector dates, per-camp median/%current, temporal_mixing flag + label in cluster_and_validate — all additive.

## Implementation
Parent feature `epic-stable-era-windows-discovery-gate` — exact contracts + acceptance criteria there.

## Implementation notes

**`src/legacy_engine/analytics/discovery.py`**
- `DeckVector` gains `date: str | None = None` (additive; existing hand-built `DeckVector(key=...,
  counts=...)` calls in tests/callers are untouched).
- `discover_subarchetypes`'s pool query now selects `t.date` alongside the existing columns and
  threads it into each `DeckVector.date`; `**params`' pass-through split (`_MATRIX_PARAM_NAMES`)
  already routes an unrecognized `current_since` kwarg to `cluster_and_validate` with no wrapper
  change needed.
- `Camp` gains `median_date: str | None = None` and `pct_current: float | None = None`.
  `DiscoveredSplit` gains `temporal_mixing: bool = False` and `temporal_note: str | None = None`.
  All four are additive with defaults — every existing constructor call stays green untouched.
- `cluster_and_validate` gains `current_since: str | None = None`. After camps are formed (all
  branches: 2-camp / 3+-camp / single-cluster), each `Camp` is re-stamped via
  `dataclasses.replace` with `median_date`/`pct_current` from the new `_camp_temporal_stats`
  helper: `median_date` is the median ISO date over the camp's dated members (`_median_date`,
  ordinal-day averaging so an even count still lands on a real calendar day); `pct_current` is
  the fraction of the camp's full membership (not just dated decks) whose date is present and
  `>= current_since` — `None` whenever `current_since` isn't supplied (honest — no fabricated
  fraction against an unknown reference).
- **Gate C** runs only in the `len(unique_camps) >= 2` branch (noise and the 0/1-camp branches
  never reach it — noise is excluded by construction since `camp_keys` only ever holds non-noise
  cluster members). Compares the max pairwise gap (in days) between camps' `median_date`s
  against the named constant `_TEMPORAL_GAP_DAYS = 120`; `temporal_mixing=True` +
  `temporal_note="camps may be list generations"` when the gap is `>=` the threshold. **Gate C
  never fails the split** — `passed` stays `gate_a_pass and gate_b_pass` exactly as before; Gate
  C only sets the two new flag fields and appends a `"gate C temporal: ..."` line to `reasons`
  (a distinct "insufficient dated decks" reason when fewer than 2 camps carry a date at all).
- `_TEMPORAL_GAP_DAYS`'s calibration comment cites the two synthetic fixtures in
  `TestClusterAndValidateGateC` (see below) — a real two-sample distributional test can replace
  the heuristic later without touching the `DiscoveredSplit` API.

**Tests**: `tests/analytics/test_discovery.py`
- `TestClusterAndValidateGateC` (6 tests): two-generation split (camp medians 2025-06-01 vs
  2026-05-01, ~334d apart) flags with the exact label and `passed is True` (Gate C never fails a
  statistically-valid split); a contemporaneous split (both camps dated within a ~30-day window)
  does not flag; fully undated decks report "insufficient dated decks" honestly rather than
  fabricating a gap; `pct_current` is `None` on every camp when `current_since` isn't passed and
  computed correctly (0.0 / 1.0) when it is; a hand-built `Camp(...)` with no temporal kwargs
  still constructs (additive-defaults contract).
- `TestDiscoverSubarchetypesDB::test_tournament_date_rides_the_pool_query_into_gate_c`: two
  tournaments dated 2025-06-01/2026-05-01 seeded into a hermetic in-memory DuckDB, confirming
  `t.date` flows end-to-end from the SQL join through `DeckVector.date` into a real Gate C flag.

**Full suite**: `2918 passed, 1 xfailed` (baseline was `2911 passed, 1 xfailed`; the 7 new tests
above account for the delta exactly). `ruff check` clean on both changed files.

**Deviations**: none from the parent feature's Unit 1 contract.
