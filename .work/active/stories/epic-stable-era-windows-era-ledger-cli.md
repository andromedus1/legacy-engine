---
id: epic-stable-era-windows-era-ledger-cli
kind: story
stage: done
tags: [analytics]
parent: epic-stable-era-windows-era-ledger
depends_on: [epic-stable-era-windows-era-ledger-run]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# eras CLI group (run|list|explain|confirm)

## Brief
Unit E: the eras command group with audit-echo output, explain derivation walk, and the confirm loop appending to the curated events JSON (Candelabra registration = validation case).

## Implementation
Parent feature `epic-stable-era-windows-era-ledger` — exact contracts + acceptance criteria there.

## Implementation notes

**Unit E — `src/legacy_engine/cli.py`** (new `eras` group, nested-groups + audit-echo
conventions, placed after `discover` and before `if __name__ == "__main__":`):

- `eras run [--db --provenance --alpha]` — connects (`--db` or default), echoes data freshness,
  calls `run_eras`, renders per-entity `stable since <date>[ [inherited from parent]]
  (n_accepted/n_boundaries boundaries accepted)` lines, then `// ⚠ <entity>: <note>` for every
  fired alarm (or `// no drift alarms`).
- `eras list [--db]` — reads `read_entity_eras`; per entity shows `stable since`, `trigger`
  (the attribution detail of the boundary matching `stable_since`, or `(full history — no
  boundary)`), and `[<tier>, n=<post_boundary_decks>]` via `confidence.tier_for_sample`. Honest
  `(no era data — run \`eras run\` first)` on an empty/missing table.
- `eras explain ENTITY [--db]` — the `explain_valid_since` analog: per-boundary walk (date,
  BH/floor verdict as `ACCEPTED`/`FLOOR-REJECTED`/`BH-REJECTED`, p-value, attribution detail,
  every component signal's magnitude/p/evidence/trigger card), plus the alarm note if fired.
  Unknown entity -> `click.ClickException` ("unknown entity ... — run \`eras run\` first, or
  check \`eras list\`").
- `eras confirm DATE CARD REASON [--events-path]` — parses `DATE` (`ClickException` on a bad
  ISO date), calls `append_ban_event` (`--events-path` defaults to the shipped
  `config.BAN_EVENTS_PATH`; a duplicate `(date, card)` surfaces as a clean `ClickException`),
  echoes the registration + the healed regime window computed directly from the freshly
  re-read event list (never the in-process cached `BAN_EVENTS` — see docstring: BAN_EVENTS binds
  once at import, so a long-running process only sees the update on its next import; a fresh
  CLI invocation always does).
- All non-data lines use the `// ` audit-echo prefix (`// ⚠` for alarms/degrade notes),
  consistent with the rest of `cli.py`.

**Tests**: `tests/test_cli_eras.py` (15 new) — file-backed hermetic DuckDB via
`_build_eras_db(tmp_path) -> str` (the file-backed-cli-test-db-builder pattern; every
`runner.invoke` pinned to `--db <path>`, verified via a monkeypatched-`DUCKDB_PATH` guard that
the default DB is never touched). Covers: `run` reports all 3 entities + the Drift alarm;
`--provenance` filtering; `list` before/after a run (trigger + tier rendered); `explain` walks
Tron's ban-attributed boundary and Drift's unattributed-with-alarm boundary; unknown entity (both
after a run and with no run at all) raises a clean `ClickException`; `confirm` appends + echoes
the healed-regime line, round-trips through a fresh `load_ban_events` read, and — the load-bearing
check — demonstrates `analytics.trends.regime_windows()` gains a window opening at 2026-06-29
once `BAN_EVENTS` is refreshed (monkeypatched to the freshly re-read event tuple, simulating what
a fresh process picks up; `trends.py` captured its own `BAN_EVENTS` reference at its own import
time, so this couldn't be proven any other way without an actual subprocess); duplicate-event and
invalid-date `confirm` calls raise clean exceptions; the REAL shipped `events.json` is verified
byte-for-byte untouched by every `confirm` test (all point `--events-path` at a tmp copy).

**Verification**: `tests/test_cli_eras.py` 15 passed (~15s, dominated by the 7,560-deck synthetic
corpus build shared with the `-run` story's own end-to-end test); `ruff check` on
`src/legacy_engine/cli.py` shows the same 17 pre-existing `F821`/`F541` findings as the
pre-change baseline (all in forward-reference type hints of OTHER, unrelated report-printing
helpers — none introduced by this story; confirmed via `git stash` diff) — zero new lint findings
from the `eras` group itself. Full suite: 2881 passed, 1 xfailed (baseline 2813 + 1 xfail + net
new tests across all three stories: 23 + 30 + 15 = 68; matches 2813 + 68 = 2881).

**Deviations**: none from the pinned Unit E contract. `--events-path` defaults to
`config.BAN_EVENTS_PATH` (the shipped file) rather than requiring it explicitly, matching the
`--discovered-path`/`--registry-path` convention already used by `discover promote`.
