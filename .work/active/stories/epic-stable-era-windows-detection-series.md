---
id: epic-stable-era-windows-detection-series
kind: story
stage: done
tags: [analytics]
parent: epic-stable-era-windows-detection
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Entity series builder (analytics/eras/series.py)

## Brief
One batched DuckDB scan → per-entity density-adaptive bucketed series (share, W/L, flex-band
inclusion), plain frozen dataclasses, partial-trailing-bucket flag, camp entities from
decks.variant. Objective-search-split: everything downstream is pure.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 1 (exact signatures + acceptance
criteria there).

## Implementation notes

Built `src/legacy_engine/analytics/eras/` (new package) with `series.py` implementing
`Bucket`, `EntitySeries`, `build_entity_series` exactly per the parent feature's Unit 1 contract,
plus package `__init__.py` re-exporting both stories' public names.

Three batched scans (objective-search-split, no per-entity queries): `decks`x`tournaments`
population pass, `deck_cards` flex-band pass, and a dup-safe `rounds` join (the same
cardinality-safe idiom as `match_results.py`'s `_DUP_UNIQ_CTE`, reproduced rather than imported
since it's a private module constant and this query's shape differs). Bucketing groups the
corpus's *active* ISO weeks (weeks with zero tournaments anywhere are dropped, never
zero-padded) into `bucket_weeks`-sized chunks anchored at the corpus's first active week;
density is the median weekly deck count over that same active-week list. Completeness is a
single symmetric check per bucket (`corpus_min_date > bucket.start` OR
`corpus_max_date < bucket_end - 1 day`), which naturally produces both the leading-partial and
trailing-partial flags without special-casing bucket position.

Deviations from the design (both sanctioned by the story prompt):
- Added `min_camp_decks: int = 30` as an extra keyword-only parameter beyond the feature's
  literal `build_entity_series` signature, so tests can lower both floors independently to keep
  fixtures small (the prompt explicitly authorized this).
- `card_incl` is sparse (only cards actually run appear as keys) rather than a dense dict over
  every flex card — an implementation choice, not specified either way by the design.
- Flex band counts a card from *either* board (main or side), per the story's explicit
  instruction — a deliberate difference from `discovery.py`'s mainboard-only scope, documented
  in the module docstring.

Tests: `tests/analytics/eras/test_series.py`, 17 tests, hermetic in-memory DuckDB, hand-built
8-week synthetic corpus (4 archetypes + 2 camps) plus a dedicated 2-tournament fixture for the
leading-partial-bucket case. Covers: exact spot-week decks/field_decks/wins/losses, entity-floor
inclusion/exclusion, density-adaptive bucket_weeks (1/2/4), camp entity emission + floor
exclusion, flex-band parent-vs-camp asymmetry, provenance filtering, and the empty-corpus path.
All pass; full repo suite (`pytest -q`) is green at 2770 passed / 1 pre-existing xfail.

No production bugs found or parked during this story.
