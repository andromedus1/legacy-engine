---
description: How CLI tests stand up a hermetic, archetype-labeled DuckDB corpus in a tmp file and pin every `runner.invoke` to it via `--db`. Read before writing any test that drives a CLI command which reads from the DB — never let a CLI test fall back to the default DB.
type: pattern
kind: planning
updated: 2026-06-14
summary: |
  A module-level `_build_*_db(tmp_path) -> str` helper opens a file-backed DuckDB under tmp_path,
  inits schema, loads cards + tournaments via `parse_cache_item` + `store.load_tournament`, stamps
  archetypes with `UPDATE decks SET archetype = …`, closes, and returns the path string. Tests then
  invoke the CLI with `--db <that path>`, never the developer's default DB.
decisions:
  - "CLI tests build a temp DuckDB file under tmp_path and ALWAYS pass it via `--db` — never the default DB (green-local/red-CI trap)."
  - "The builder is a plain module-level function returning a `str` path, not a pytest fixture closure (distinct from pytest-factory-fixtures)."
  - "Post-load `UPDATE decks SET archetype = …` is load-bearing: load_tournament stores raw decks; analytics/advisory surfaces key on archetype."
  - "Return `str`, not `Path` — `--db` and `store.connect` take strings throughout."
---

# Pattern: File-backed hermetic CLI test DB builder

A module-level `_build_*_db(tmp_path) -> str` (or `_setup_db`) helper opens a file-backed DuckDB
under `tmp_path`, inits schema, loads tournaments via `parse_cache_item` + `store.load_tournament`,
stamps archetypes with `UPDATE decks SET archetype = …`, closes, and returns the path string —
which tests pass to `runner.invoke(main, [..., "--db", db_path])`.

## Rationale
CLI commands connect to a DuckDB file, falling back to the default project DB when `--db` is
omitted. To stay hermetic — and to avoid the green-local / red-CI trap where a test silently reads
the developer's real DB — CLI tests must run against a temp DB they built. This pattern packages
"stand up a realistic, archetype-labeled corpus in a tmp file and hand back its path" into one
reusable builder per test module, so each `runner.invoke` is explicitly pinned to `--db <tmp
path>`. The `UPDATE decks SET archetype` step is load-bearing: `load_tournament` stores raw decks,
but the analytics/advisory surfaces key on `archetype`, so a test that skips the stamp gets empty
reports.

## Example (canonical)

**File**: `tests/test_advise_field.py:140` — mixed online/paper corpus
```python
def _build_mixed_db(tmp_path) -> str:
    db_path = str(tmp_path / "mixed.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, _TEST_CARDS)
    tid_online = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Control' WHERE tournament_id = ?", [tid_online])
    tid_paper = store.load_tournament(con, parse_cache_item(_PAPER_TOURNAMENT, "mtgmelee"))
    con.execute("UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ?", [tid_paper])
    con.close()
    return db_path

# used at tests/test_advise_field.py:221 via
#   runner.invoke(main, ["advise", "field", "--db", db_path])
```

Further occurrences: `tests/test_cli_venues.py:63` (`_build_venue_db`), `tests/test_advise_report.py:468`
(`_setup_db`, schema-only), `tests/test_advise_provenance_flag.py:145,168`, `tests/test_advise_field.py:157`
(`_build_online_only_db`), `tests/test_ingest_diff_persist.py:118` (`_make_tiny_db`),
`tests/test_matchup.py:700` (`_build_db_with_labeled_data`). The companion
`runner.invoke(main, [..., "--db", str(...)])` shape appears 60+ times across 11+ files.

## When to use
- Any test that drives a CLI command which reads from a DuckDB file.
- When you need a small but realistic, archetype-labeled tournament corpus for advisory/analytics
  CLI assertions.

## When NOT to use
- Pure unit tests of analytics functions that take a connection directly — use an in-memory
  `store.connect(":memory:")` corpus and skip the file/path round-trip.
- Tests that don't invoke the CLI at all.

## Common violations
- Invoking a CLI command without `--db` — falls back to the developer's real default DB; green
  locally, red/empty in CI. This is the explicit hermeticity rule.
- Loading tournaments but forgetting the `UPDATE decks SET archetype` stamp — archetype-keyed
  reports come back empty.
- Returning the `Path` object instead of `str` — `--db` and `store.connect` paths are strings
  throughout.
