---
id: story-fix-refresh-duplicate-decks
kind: story
stage: done
tags: [bug, ingestion, archetype]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-09-05
updated: 2026-09-05
---

# Invalidate incremental assignments when a tournament is reloaded

## Symptom

The September 4 decision-data refresh failed at `staged_camps` with:
`Constraint Error: Duplicate key "tournament_id: https://www.mtgo.com/decklist/legacy-league-2026-08-0610831, deck_idx: 4" violates primary key constraint.`

The cached corpus contains two files with this URI: a July 5 payload with 14 decks and an August 6
payload with 9 decks. Reloading the same tournament id reuses deck indexes while an incremental
assignment row from the previous lineup remains present.

## Root cause

`store.load_tournament` deletes and rebuilds the tournament's fact rows but leaves
`variant_incremental_assignments` rows keyed by `(tournament_id, deck_idx)`. When a changed cache
payload reuses an index for a deck under another archetype, `assign_incremental` processes that
index under the new parent while the stale assignment remains under its old parent, so its insert
violates the assignment table primary key. Existing databases can retain this state when an
unchanged cache hash skips the reload entirely.

## Fix approach

When reloading a tournament, clear any existing incremental-assignment rows for that tournament
before inserting the replacement deck lineup. At the `assign_incremental` boundary, clear owned
assignment rows whose key now belongs to the current parent under a different recorded parent, so
already-stale databases are repaired even when the cache is unchanged. The derived assignments are
reconstructed by the staged-camp pass from the current decks and registry; a missing assignment
table on older databases is treated as the normal pre-discovery state.

## Regression test

`tests/test_refresh_duplicate_decks.py` covers both paths: a same-URI lineup replacement clears a
stale assignment before the next pass, and an unchanged-cache pass repairs an already-stale
cross-parent row before writing the authoritative assignment.

## Implementation notes

- Execution capability: direct focused repair; the failure is isolated to tournament replacement
  invalidation in the ingestion store and one regression surface.
- Files changed: `src/legacy_engine/ingestion/store.py`,
  `src/legacy_engine/archetype/discovered.py`,
  `tests/test_refresh_duplicate_decks.py`, and this story.
- `load_tournament` now clears assignment rows for the replaced tournament id. Older databases
  without the lazily created assignment table continue through the normal load path.
- `assign_incremental` now removes only owned conflicting rows for current-parent deck keys before
  authoritative inserts, and raises for an unknown assignment owner rather than swallowing a
  collision.
- Regression first: both focused tests failed with the duplicate-key constraint before their
  respective repairs and pass afterward.
- Verification: focused store, tournament, discovery, and regression tests pass (`72 passed`);
  Ruff and `git diff --check` pass. A copied temporary database from the current local corpus had
  3 stale target assignments before staged-camps; the unchanged-cache staged-camps pass completed
  (`29 parents; 20,953 exact; 16,835 incremental`) and left 0 stale target assignments. No live
  database or network refresh was run.
- Adjacent issues parked: none.

## Review (2026-09-05)

**Verdict**: Approve.

**Blockers**: none. **Important**: none. **Nits**: none. **Rejected**: none.

**Notes**: Bounded inline standalone-story review; no independent reviewer. Inspected
replacement invalidation, cross-parent ownership filtering, parameterized deletes, absent lazy
table handling, and both failing-before/passing-after reproductions. Full suite: 4,110 passed,
1 skipped. The actual scheduled refresh now passes staged camps and publishes Deck Rankings;
remaining degraded status names operator era/release alerts rather than an execution failure.
