---
id: epic-stable-era-windows-shrinkage-goldens
kind: story
stage: done
tags: [analytics, methodology]
parent: epic-stable-era-windows-shrinkage
depends_on: [epic-stable-era-windows-shrinkage-hierarchy]
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-12
---

# Golden re-pins + prior-source surfacing

## Brief
Unit 3: re-pin full-body goldens (raw/n byte-identical, only shrunk values + labels move); render prior labels on split-variant rows.

## Implementation
Parent feature `epic-stable-era-windows-shrinkage` — exact contracts + acceptance criteria there.

## Implementation notes

**Golden re-pin**, `tests/test_matchup_split_variant.py::TestGoldenReportMatchupsDefault`: the
no-flag `report matchups` body golden moved (Control's cell 17%→7%, Doomsday's 83%→93% — expected,
documented consequence of the -shrinkage-hierarchy story landing; see that story's notes for why).
Kept the old grid as `_GRID_PRE_HIERARCHY` alongside the new `_GRID` and added
`test_repin_only_shrunk_values_moved_raw_n_identical`, a mechanical regex-based test that extracts
every cell's `raw%`/`n=` token from both goldens and asserts they are byte-identical while at
least one `shrunk%` token differs — the "raw/n columns are byte-identical" proof the parent
feature's Unit 3 requires, enforced as a permanent test rather than a one-off script check.

**Prior-source surfacing**, `src/legacy_engine/cli.py`:
- `_print_head_to_head`: added a `prior          = <source>` line (mirrors the existing `tier`
  line's format) whenever `cell.prior_source is not None` — true for every cell built by
  `build_matrix`/`build_adaptive_matrix` now that Unit 1 always supplies a hierarchy label.
- `_print_matchup_matrix` gained an opt-in `split_variant` kwarg (default `None`, byte-identical
  when omitted — the no-flag `report matchups` path never emits these lines, asserted directly).
  When set, after the grid it emits one `// prior: <camp> vs <opponent>: <source>` audit-echo
  line per non-mirror cell touching a camp row — the AC's "camp rows show prior labels",
  grep-able per the project's audit-echo-comment-lines pattern. `report_matchups` now passes
  `split_variant` through to the matrix printer.

**Tests**: 2 new tests in `tests/test_matchup_split_variant.py`
(`test_repin_only_shrunk_values_moved_raw_n_identical`,
`test_split_flag_camp_rows_show_prior_labels`) plus one new assertion in the existing
`test_head_to_head_accepts_camp_label`. Ran ruff on `cli.py` and the test file — the only findings
are 17 pre-existing `F821` forward-reference false-positives (the file's established
lazy-local-import annotation style, e.g. `MatchupMatrix`/`MatchupCell` on `_print_head_to_head`'s
own signature, unrelated to my two added lines) and 1 pre-existing unrelated `F541`; none touch
lines I changed. Full suite: `.venv/bin/python -m pytest -q` → all green (see full-suite section
below), golden re-pinned, no more expected failures.

No production bugs found or parked during this story.
