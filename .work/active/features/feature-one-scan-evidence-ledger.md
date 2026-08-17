---
id: feature-one-scan-evidence-ledger
kind: feature
stage: review
created: 2026-08-16
updated: 2026-08-16
tags: [analytics, perf]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Build interval evidence from one physical match scan

## Brief

The live localized-evidence refresh spends minutes in `build_selected_outcome_ledger` because it
calls `resolve_match_records` once per subject/opponent pair and each call re-runs the full
rounds/decks/tournaments join. Replace the N-pair full-corpus rescans with one physical resolver scan
and in-memory canonical pair grouping, preserving byte-for-byte selected-ledger semantics, reverse
orientation derivation, half-open interval gaps, and atomic last-good report publication.

## Simplification opportunity

Delete the pair loop's repeated SQL resolution path. Resolve each physical match once, canonicalize
its orientation once, group it by pair once, and keep the existing pure interval selector as the
only admission authority.

## Design decisions

- Preserve `SelectedOutcomeLedger.content_sha256` and every selected row byte-for-byte; performance
  is not permission to change interval admission, orientation, or report authority.
- Measure the real current report's parent and camp interval builds. A deterministic resolver-call
  budget supplements wall-clock measurements so CI does not depend on machine speed.
- Keep this single-process and single-threaded. The higher-order fix is to eliminate redundant joins
  and scans, not to parallelize the N+1 path.

## Perf Overview

The normal current ranking completed its mature matrix/camp work in 37.8 seconds, then remained in
`build_selected_outcome_ledger` until the run was interrupted at 2 minutes 50 seconds. The live
traceback was inside `resolve_match_records`, called from the per-pair loop at
`match_results.py:978`. Each canonical pair repeats the same rounds/decks/tournaments join and
physical-id normalization, making the exact interval ledger O(pairs × corpus scan).

The solution resolves all physical matches once per ledger build, canonicalizes their orientation
once, groups them by unordered pair, then runs the unchanged pure interval selector per pair. The
ledger also retains a derived pair index so evidence projection does not repeatedly filter every
selected row for every directed cell.

## Profiling Summary

- **Workload baseline / CPU + I/O**: the live current command
  `.venv/bin/python scripts/refresh_best_call_ranking.py --db data/legacy.duckdb --out
  decks/best-deck-best-call-ranking.html` reached 118.9% CPU and 7.6% memory after 2:50, with more
  than two minutes spent after the 37.8-second mature matrix phase. The interrupt stack was in the
  repeated resolver called by the canonical-pair loop; publication remained atomic and left the
  last-good HTML untouched.
- **Complexity evidence**: `build_selected_outcome_ledger` calls the full `_JOIN_SQL` resolver once
  for every canonical pair. The live parent surface has 95 archetype rows and 61 current-field
  opponents, followed by a 106-row camp surface, so repeated full joins dominate before pure
  selection can finish.
- **Probe selection**: standard-library `perf_counter_ns` / `process_time_ns` provide repeatable
  end-to-end timing; deterministic resolver-call instrumentation proves the I/O budget; DuckDB
  `EXPLAIN ANALYZE`/JSON profiling and `cProfile` are available if the one-scan rewrite does not
  clear the target. Allocation, off-CPU, hardware-counter, cache, and branch probes are deferred
  because this is a measured redundant-query/complexity defect rather than a low-level CPU or
  concurrency bottleneck.

## Optimization Plan

### Optimization 1: Resolve and index physical matches once per ledger

**Hierarchy Level**: Algorithmic / data model, with an I/O boundary benefit
**Probe Family**: Workload baseline + DuckDB query/call count
**Bottleneck**: one identical full-corpus join and physical-id pass per unordered matchup pair
**Expected Metric Movement**: resolver calls fall from O(canonical pairs) to exactly one per parent
or camp ledger build; the current parent+camp interval phase completes instead of exceeding two
minutes, with the complete ranking target under 90 seconds on the current machine.
**Story**: `feature-one-scan-evidence-ledger-opt-batch-pairs`

#### Implementation Units

##### Unit 1.1: Canonical one-scan grouping

**File**: `src/legacy_engine/analytics/match_results.py`

```python
def build_selected_outcome_ledger(
    con: duckdb.DuckDBPyConnection,
    *,
    pair_keys: Collection[tuple[str, str]],
    entity_eligibility: Mapping[str, EntityEligibility],
    clock: AnalysisClock,
    certificate_run_id: str | None = None,
    provenance: str | None = None,
    split_variant: str | None = None,
    split_variants: Collection[str] | None = None,
) -> SelectedOutcomeLedger: ...
```

**Implementation Notes**:

- Call `resolve_match_records` once without a subject/opponent filter.
- Reverse only non-canonical records in memory, preserving match id, event/date/provenance, player
  orientation, win polarity, and mirror flag.
- Group canonical records by pair and pass only that tuple to the existing
  `select_pair_matches`; do not change exact interval membership.
- Build a tuple-valued pair index over final selected rows for repeated directed lookups; reverse
  results remain derived, never stored as a second physical observation.

**Acceptance Criteria**:

- [x] Fixture output rows and `content_sha256` exactly match a retained per-pair reference build.
- [x] One ledger build calls the resolver exactly once regardless of pair count.
- [x] Forward/reverse rows retain one physical id and complementary outcomes.
- [x] Current parent and camp report generation completes under the measured target without
  changing atomic publication behavior.

## Benchmarks

**Location**: `scripts/benchmark_interval_evidence.py` plus resolver-call/parity assertions in
`tests/analytics/eras/test_interval_consumption.py`
**Run command**: `.venv/bin/python scripts/benchmark_interval_evidence.py --db data/legacy.duckdb
--mode both`
**Baseline targets**: current mature matrices finish in 37.8s; the following interval phase remains
in repeated resolution beyond 132s and the total run was interrupted at 170s.
**Expected targets**: exactly one resolver call per ledger; parent+camp interval benchmark completes,
and the full current ranking completes in under 90s on the same corpus/machine.
**Counter targets**: not applicable; algorithmic/query elimination is the measured first-order fix.

## Implementation Order

1. Add exact reference parity and resolver-call-budget tests.
2. Implement one-scan canonical grouping and the derived pair index.
3. Run focused/full tests, benchmark parent+camp interval generation, then rerun the live current
   ranking to verify atomic publication and utility counts.

## Implementation Result

The selected-outcome ledger now resolves the physical corpus once, groups canonical pairs in
memory, and exposes a derived pair index. Interval construction also supplies only the relevant
subject or sibling-camp hierarchy rows to each evidence view. Reference tests preserve exact rows,
digests, forward/reverse polarity, and both parent and multi-split behavior while enforcing one
resolver call.

The live controlled benchmark completed the parent interval in 24.284 seconds and the camp interval
in 34.954 seconds (59.2 seconds combined), selecting 17,828 rows across 25,098 directed pairs. The
former run did not finish this phase after more than 132 seconds. A follow-up profile found the
remaining pre-index cost in repeated hierarchy-wide `_view_rows`/`_view_local_prior` scans; the
sibling/subject index removed that second-order scan with exact parity. Focused verification passed
79 tests.

Integrated verification also passed the complete repository suite: 3,997 passed, 1 skipped. The
final live report completed atomic publication with exact interval, compact-projection, and write
phase timings emitted separately.
