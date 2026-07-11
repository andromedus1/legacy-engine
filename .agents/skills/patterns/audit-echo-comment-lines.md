---
description: How to emit machine-scannable provenance/status lines to stdout. Read before adding any status or window or degradation output to a CLI command.
type: pattern
kind: planning
updated: 2026-06-13
summary: |
  Every provenance, window, degradation, and operational status line in the CLI is emitted
  as a "//" comment prefix to stdout so it is visually distinguishable from data rows,
  grep-able from scripts, and never confused with the analytical output it annotates.
  94 uses in cli.py alone; the convention is also followed in ingestion and generation
  surfaces that emit advisory-style output.
decisions:
  - "Use the '// ' prefix for every non-data line: window headers, data-freshness lines, classification results, fallback banners, legality notes, staleness advisories."
  - "The prefix is literal — always the two-char string '// ' (with trailing space before the message), not a Python log call."
  - "Provenance lines precede data rows in the output so tools consuming stdout can strip headers at the top."
  - "Warnings that require action use '// ⚠' (Unicode warning sign); informational lines use plain '//'."
  - "Error-level lines (e.g. '[warn]') are still emitted via click.echo to stdout (not stderr) so they appear in piped output."
---

# Pattern: Audit-Echo Comment Lines

Every operational, provenance, window-context, and degradation line emitted by the CLI uses
the `// ` comment prefix so it is visually distinguishable from data output and can be
stripped or grepped reliably by downstream tooling.

## The Convention

```python
click.echo("// window: adaptive (per-cell ban-aware matrix; field = current regime)")
click.echo(f"// data as of {max_date} ({deck_count} decks)")
click.echo(f"// ⚠ newest event is {age} days old — data may be stale (run `refresh`)")
click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")
click.echo(f"// collection: {cv}")
click.echo(f"// [FALLBACK] {tuned.reason}")
click.echo(f"// [warn] {w}", err=True)   # ← error=True for action-required warnings
```

## Categories

| Category | Example prefix | Description |
|---|---|---|
| Window header | `// window: ...` | Emitted by `_echo_window`; always first before any data |
| Data freshness | `// data as of ...` | Emitted by `_echo_data_freshness`; corpus provenance |
| Price freshness | `// prices as of ...` | Emitted by `_echo_price_freshness` |
| Degradation banner | `// ⚠ ...` | Staleness advisory, thin-regime degrade |
| Classification | `// Classified archetype: ...` | Auto-classify result when no `--archetype` given |
| Collection | `// collection: ...` | CollectionView when `--collection` provided |
| Audit trail | `// Δvalue = ...` | Tuning objective delta |
| Fallback | `// [FALLBACK] ...` | Explicit fallback reason from generation |
| Warning | `// [warn] ...` | Advisory warnings; sent to `err=True` when action-required |
| Plan window | `// plan window: ...` | Adaptive per-opponent windows in sideboard plans |
| Release scan | `// Release scan: ...` | Upstream set scan result in `refresh cards` |

## Canonical Examples (cli.py line numbers)

```python
# _echo_window  (cli.py:75; banner echo at cli.py:86)
click.echo("// window: adaptive (per-cell ban-aware matrix; field = current regime)")
click.echo(f"// {res.banner}")

# _echo_data_freshness  (cli.py:110)
click.echo("// data as of: (empty corpus)")
click.echo(f"// data as of {max_date} ({deck_count} decks)")
click.echo(f"// ⚠ newest event is {age} days old — data may be stale (run `refresh`)")

# advise_sideboard classification  (cli.py:3058)
click.echo(f"// Classified archetype: {resolved_archetype} (kind={result.kind})")

# generate_tune objective  (cli.py:5166)
click.echo(f"// Δvalue = {tuned.value_after - tuned.value_before:+.4f}")
click.echo(f"// [FALLBACK] {tuned.reason}")
```

## Total Uses

94 `click.echo("// ...)` call sites in `cli.py` as of 2026-07-11. The pattern
also appears in `advisory/refresh.py`'s `render_refresh_result` for the multi-venue
output surface.

## When to Use

Use `// ` for every line that is:
- contextual metadata rather than a data row (window, freshness, provenance, audit)
- a conditional status line that should not break downstream parsing
- a degradation or fallback notice that explains a gap in data output

## When NOT to Use

- Actual data rows (archetype names, win rates, card names) — no prefix.
- `logging.debug/info/warning` calls to `sys.stderr` — those are a separate channel.
- Multi-line section headers (e.g. `=== Sideboard Recommendation ===`) — those use a distinct
  `===` wrapping convention.
