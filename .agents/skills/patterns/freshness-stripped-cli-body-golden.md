# Freshness-stripped pinned CLI-body golden (test)

CLI outputs open with a data-dependent freshness/header block (today's date, window echo) that
cannot be pinned literally. To assert an output body is byte-identical, split off the leading block
at the first blank line — `body = result.output.split("\n\n", 1)[1]` — and pin the remainder
(including the stable `//` audit lines and the data grid) against a `GOLDEN` string literal. This is
the enforcement half of [opt-in-analytics-overlay](opt-in-analytics-overlay.md).

## Examples

- `tests/test_conditioned_card_winrate.py:98` — `TestGoldenReportCardsDefault`: split + `assert
  body == self.GOLDEN`.
- `tests/test_conditioned_card_winrate.py:140` — `TestGoldenReportSubgroupDefault`: GOLDEN retains
  the `//` thin-subgroup audit line inside the pinned body.
- `tests/test_matchup_split_variant.py:386` — `TestGoldenReportMatchupsDefault`: GOLDEN retains
  `// window: full-corpus`.

## When to Use
- Locking a CLI command's default output against regression when the head is time/data-variable but
  the body is deterministic given a hermetic test DB.

## When NOT to Use
- Non-deterministic bodies (ordering not tie-broken, floats not formatted).
- Model/function-level output — assert the value directly; no header to strip.

## Common Violations
- Filtering `//` lines out and pinning only data rows — drops the audit lines the golden should lock.
- Splitting on a hardcoded line count instead of the blank-line boundary (brittle to header changes).
