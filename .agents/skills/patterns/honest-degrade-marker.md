---
description: How to surface absent/thin signal without fabricating data. Read before implementing any analytics output that may lack data for some inputs — this is the project's honesty contract for absent data.
type: pattern
kind: planning
updated: 2026-06-13
summary: |
  When signal is thin or absent, the system surfaces a labeled banner, a degraded flag, or
  an explicit null — always with a named reason — and suppresses magnitude (no fabricated
  numbers). The caller never sees a silent 0 or a placeholder value. This is the defining
  output-honesty shape of the advisory-honesty-transparency epic.
decisions:
  - "Never emit a silent zero, placeholder win-rate, or fabricated cost when data is absent."
  - "The honest-null shape: a named boolean/flag + a reason string. The caller sees the gap; it decides how to surface it."
  - "When magnitude is suppressed, the label explains why (e.g. 'PRE-DATA FORECAST', 'degraded — no per-card data', 'all_null — no paper USD price')."
  - "Degrade direction: thin window → full corpus (not empty output); degraded matchup plan → reasoning-based label (not suppressed plan entry)."
  - "The degrade/banner is always logged to stdout via the '// ' comment-line convention before data rows."
---

# Pattern: Honest Degrade Marker

When a signal is thin, absent, or pre-data, the system surfaces an explicit labeled marker
(banner / degraded flag / explicit null) with a named reason and suppresses any fabricated
magnitude. The caller always knows what it is missing and why.

## The Five Instantiations

### 1. Thin-Regime Window Degrade (window.py)

When a requested ban-regime window has fewer than 500 rounds, `resolve_advisory_window`
degrades to the full corpus and sets `banner`:

```python
# advisory/window.py:113-119
if n_rounds < thin_floor:
    banner = (
        f"⚠ requested window ({label}) is THIN: {n_rounds} rounds < floor {thin_floor} — "
        f"degraded to full corpus for reliable matchup math"
    )
    return WindowResolution(None, None, banner, label, mode="uniform")
```

`_echo_window(win)` always echoes `// {win.banner}` before any data output (cli.py:86, in `_echo_window` at cli.py:75).

### 2. Degraded Matchup Plan / Primer (sideboard.py + primer.py)

When per-card data is absent for a matchup opponent, the plan is degraded with an explicit note:

```python
# advisory/sideboard.py:1451-1472
# Build an honest degraded note: name the adaptive window if one was used
return MatchupPlan(
    ...
    note="no per-card data — coverage from sideboard composition only",
    degraded=True,
    n_basis=0,
    tier="speculative",
    ...
)
```

`primer.py:224-226` routes degraded plans to `_prose_degraded`, which labels the section
reasoning-based and never emits a win-rate or swap magnitude:

```python
# advisory/primer.py:224-226
if degraded or n_basis == 0:
    prose = _prose_degraded(opponent, tier, note, sideboard)
```

The render layer in `report.py:312-313` echoes the reason to the audit trail:
```python
if plan.degraded:
    audit.append(f"  matchup_plan[{opp}]: degraded — {plan.note}")
```

### 3. PRE-DATA FORECAST Label (speculation.py)

Every `SpeculativeForecast` carries the `PRE_DATA_BANNER` as its `label` field:

```python
# analytics/speculation.py:71-72
PRE_DATA_BANNER = "PRE-DATA FORECAST — no tournament data yet"
# analytics/speculation.py:554-558
label = f"{PRE_DATA_BANNER} — {len(gated)} gated analogue(s) used as prior"
# or:
label = f"{PRE_DATA_BANNER} — intrinsic score only (no gated analogues)"
```

The CLI always echoes this banner as the first line of speculation output so the user never
mistakes the forecast for observed data (`_print_speculation` at cli.py:2022, label echo at cli.py:2027).

### 4. all_null / Unpriced Explicit Null (prices.py)

`price_quote` never returns a silent 0 or raises when every paper printing lacks a USD price:

```python
# ingestion/prices.py:87-97
all_null: True when every paper printing of this card has `usd: null`.
# ingestion/prices.py:392
return PriceQuote(..., all_null=True, unit_price=None, ...)
```

`deck_cost` accumulates an explicit `unpriced` list and excludes those cards from `total_usd`
(never silently drops them):

```python
# ingestion/prices.py:471-472
if q.all_null:
    unpriced.append(name)
```

The CLI renders `all_null=True` to the user with context:
```python
# cli.py:1823-1824
if q.all_null:
    click.echo(f"  all_null=True — no paper USD price in card_prices (source: {q.source})")
```

### 5. Venue Divergence Labeled Output (venue.py + cli.py)

Cross-venue meta-share divergence is rendered as a labeled table with the divergence magnitude
explicit. When venues differ on share, the `VenueDivergence` carries per-archetype spread values
that are printed verbatim — never combined into a single unlabeled average:

```python
# cli.py:675  _print_venue_divergence (called at cli.py:590)
# Renders: archetype | online_share | paper_share | spread | direction
```

## Shape Summary

| Instantiation | Honest-null form | Suppresses |
|---|---|---|
| Thin window | `WindowResolution.banner` (non-null string) | None — degrades to full corpus, still outputs |
| Degraded matchup plan | `MatchupPlan.degraded=True` + `note` | Swap magnitudes, win-rate estimates |
| Speculation | `SpeculativeForecast.label = PRE_DATA_BANNER` | Confidence in forecast (labeled speculative) |
| Unpriced card | `PriceQuote.all_null=True` + `unit_price=None` | Cost in `deck_cost.total_usd` |
| Venue divergence | Named `VenueDivergence` with per-archetype spread | Nothing suppressed — fully labeled |

## When to Use

Use this pattern when:
- A stat or recommendation depends on a data source that may be empty (no rounds, no prices, pre-data card).
- A window or corpus is too thin for reliable math (use `thin_floor` gating).
- A model needs to degrade gracefully to a reasoning-based fallback when signal is absent.

## Common Violations

- Returning `0.0` when signal is absent (caller can't distinguish zero from "no data").
- Filling a missing stat with an imputed value without labeling it imputed.
- Suppressing the output block entirely when data is absent — prefer a labeled "no data" entry.
- Mixing degraded and non-degraded outputs without the flag (caller can't tell which rows to trust).
