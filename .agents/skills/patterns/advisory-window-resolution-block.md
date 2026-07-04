---
description: How every regime-windowed advisory/report leaf command opens and closes its DuckDB connection. Read before writing a new command that consumes the matchup matrix or advisory inputs.
type: pattern
kind: planning
updated: 2026-06-13
summary: |
  Every window-aware advisory or report command follows the same 5-step spine:
  connect → resolve_advisory_window → _echo_window → build_advisory_inputs (when needed)
  → do work → finally:close. The spine is load-bearing: it enforces the audit echo,
  the thin-regime degrade policy, and the connection lifecycle. Deviating from it
  silently bypasses the honesty layer.
decisions:
  - "resolve_advisory_window is always called before any analytics; its WindowResolution drives matrix selection."
  - "_echo_window is always called immediately after resolve — before any data access — so the audit header appears first in stdout."
  - "build_advisory_inputs is called when both the adaptive matrix AND the field window are needed; skipped for commands that only need the matrix."
  - "The connection is always closed in a finally block, never conditionally."
  - "Thin explicit windows degrade to full corpus inside resolve_advisory_window; the banner is surfaced by _echo_window."
---

# Pattern: Advisory Window Resolution Block

Every regime-windowed advisory or report leaf command in `cli.py` follows the same 5-step
spine for connecting to DuckDB, resolving the ban-regime window, and echoing the audit header
before doing any analytics work.

## The Spine

```
con = store.connect(db) if db else store.connect()
try:
    win = resolve_advisory_window(
        con, regime=regime, since=since, until=until, all_time=all_time,
    )
    _echo_window(win)
    inputs = build_advisory_inputs(con, win)   # when matrix + field window both needed
    for line in inputs.audit:
        click.echo(line)
    # ... do command-specific work using inputs.matrix / inputs.field_since / inputs.field_until
finally:
    con.close()
```

## Step Roles

1. **`store.connect()`** — opens the DuckDB file at `data/legacy.duckdb`; `--db` path override
   threads through for test fixtures.
2. **`resolve_advisory_window(con, ...)`** — converts `--since/--until/--regime/--all-time`
   flags into a `WindowResolution` (since, until, banner, mode). Degrades thin regimes (<500
   rounds) to full corpus and sets `banner`. Returns mode `"adaptive"` when no flags were given
   (the default per-cell ban-aware path).
3. **`_echo_window(win)`** — emits the `// window: ...` audit line (and the `// ⚠ ...` banner
   when a degrade occurred) to stdout. Always called before any analytics or user output — the
   header must come first.
4. **`build_advisory_inputs(con, win)`** *(optional)* — assembles the regime-aware `MatchupMatrix`
   and the correct field since/until; also fills `inputs.audit` with regime-provenance lines.
   Omit when the command only needs the window dates (e.g. `report trends`, `advise sideboard`
   which derive their own field).
5. **`finally: con.close()`** — closes the connection unconditionally; never in an `else` branch
   or after the main body (exceptions must still close it).

## Call-Site Count

~14 window-bearing commands follow this exact spine in `cli.py`:
`report_meta` (×2 sub-paths), `report_matchups`, `report_tiers`, `report_gaps`,
`report_subgroup`, `advise_positioning`, `advise_sideboard`, `advise_report` (×2),
`advise_refresh`, `advise_acquire`, `generate_consensus`, `viz_meta`, `viz_matchups`.

## Canonical Examples

```python
# advise_positioning  (cli.py:2529)
con = store.connect(db) if db else store.connect()
try:
    win = resolve_advisory_window(
        con, regime=regime, since=since, until=until, all_time=all_time,
    )
    _echo_window(win)
    inputs = build_advisory_inputs(con, win)
    for line in inputs.audit:
        click.echo(line)
    ...
finally:
    con.close()

# advise_refresh  (cli.py:3666) — simpler form without build_advisory_inputs
con = store.connect(db) if db else store.connect()
try:
    _echo_data_freshness(con)
    win = resolve_advisory_window(
        con, regime=regime, since=since, until=until, all_time=all_time,
    )
    _echo_window(win)
    ...
finally:
    con.close()
```

## When to Use

Use this spine for every new command that:
- accepts `--since/--until/--regime/--all-time` (apply `@_window_opts`)
- queries the matchup matrix or any regime-dependent analytics
- must emit an audit window header before user output

## Common Violations

- Calling analytics functions before `_echo_window` — the header must come first.
- Closing the connection conditionally (only in the happy path) — exceptions will leak the handle.
- Skipping `resolve_advisory_window` and passing raw `since/until` directly to analytics — bypasses
  the thin-regime degrade policy and the mode detection.
- Calling `build_advisory_inputs` when only the window dates are needed (unnecessary matrix build).
