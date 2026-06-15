---
id: feature-advise-provenance-flag
kind: feature
stage: done
tags: [advisory]
parent: epic-local-meta-support
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Thread `--provenance` through the advise commands

## Brief
`report meta/matchups` expose `--provenance online|paper` but the `advise` commands
(positioning/whattoplay/report/sideboard/refresh/acquire) don't — so a user can't run advisory against
a paper-only (or online-only) field. Thread `--provenance` through the advise command surfaces so the
expected field is built from the chosen provenance. Reuse the existing provenance-aware
`build_global_field`/`compute_metashare`/`build_advisory_inputs` plumbing (already accepts provenance).
Gated-additive: absent → current global behavior byte-identical. This is the discoverable, supported
version of the hand-rolled `--field` + paper workflow from the 2026-06-13 dogfood session.

## Design

### Layers that already had provenance

| Layer | Already provenance-aware? |
|---|---|
| `build_global_field(con, provenance=...)` | YES — passes through to `compute_metashare` |
| `_load_field(con, provenance=...)` | YES — passes to `build_global_field` when no field_text |
| `build_advisory_inputs(con, win, provenance=...)` | YES — passes to `build_matrix`/`build_adaptive_matrix` |
| `resolve_advisory_window(con, ..., provenance=...)` | YES — used for rounds-thinness count filter |

### Gap

The six `advise` CLI leaves (`positioning`, `whattoplay`, `report`, `sideboard`, `acquire`, `refresh`)
did not have a `--provenance` option and did not pass a `provenance` value to any of the above layers.
All calls used the implicit `provenance=None` (global/combined corpus).

### Change

1. Add `_provenance_opt(f)` decorator function (mirrors `_window_opts`) that attaches
   `--provenance [online|paper]` with `default=None` to any command.

2. Apply `@_provenance_opt` to all six advise leaves.

3. Each leaf threads `provenance` as follows:
   - `resolve_advisory_window(..., provenance=provenance)` — for thin-regime rounds-count filter
   - `build_advisory_inputs(con, win, provenance=provenance)` — for matchup matrix provenance
   - `_load_field(con, ..., provenance=field_provenance)` — for global field construction;
     `field_provenance = None if field_text is not None else provenance` (custom field unchanged)
   - Echo `// provenance: {provenance}` when provenance is set (audit-echo-comment-lines pattern)

4. Mutual exclusions:
   - `advise report --provenance` + `--venues`: error (venues already provides per-venue splits)
   - `advise refresh --provenance` + `--venues`: error (same reason)
   - `advise refresh --provenance paper` (without `--venues`): resolves `venue_list` to `["paper"]`
     via `resolve_venues(con, ["paper"])`

5. `--field` + `--provenance` precedence: `--field` (custom field) is NOT filtered by provenance.
   Only the matchup matrix is filtered. Documented in help text and echoed to output.

### Gated-additive gate

When `--provenance` is absent, `provenance=None` is passed everywhere — identical to the pre-patch
code path, which also passed `None` (implicitly). All existing tests pass unmodified.

## Implementation notes

- 6 advise leaves touched: `positioning`, `whattoplay`, `report`, `sideboard`, `acquire`, `refresh`
- `_provenance_opt` added as a reusable decorator at line ~57 in `cli.py` (below `_window_opts`)
- `advise refresh` with `--provenance` maps to a single-venue refresh via `resolve_venues(con, [provenance])`
- 33 new tests in `tests/test_advise_provenance_flag.py`: 8 test classes covering library-level
  provenance filtering, help-string presence, per-leaf acceptance/echo, gated-additive no-echo,
  invalid value rejection, mutual-exclusion errors, and --field+--provenance coexistence
- Full suite: 2024 passing (1991 pre-existing + 33 new), no ruff regressions introduced
