---
description: How to extend a shipped module with a new optional data-driven signal that activates ONLY when a confidence gate clears. Read before adding any new analytics-driven behavior to an existing module.
type: pattern
kind: planning
updated: 2026-05-31
summary: |
  Extend a shipped model by adding optional new fields (with safe defaults) and gating all new
  behavior behind an explicit data-presence check. When the gate fails the code path is a no-op
  and outputs are byte-identical to the pre-extension baseline — existing tests stay green with
  zero modification.
decisions:
  - "New fields on output dataclasses carry default_factory or literal defaults so existing constructors keep working."
  - "Gate check is a named predicate (e.g. has_value_signal, matchup_pressure=None) placed before the new logic branch — makes the no-op path explicit and grep-able."
  - "The no-op path must be byte-identical to the pre-extension output (not just semantically equivalent)."
  - "Existing tests never supply the new data source, so they exercise the no-op path and enforce the regression contract without modification."
---

# Pattern: Gated Additive Augmentation

Extend a shipped module with a new optional data-driven signal that activates ONLY when a
confidence gate clears. The data-absent path is byte-identical to the pre-extension baseline.

## Rationale
New analytics signals (per-card win-rate, matchup pressure) are only available when a rounds-bearing
corpus exists. If new behavior were unconditional, a rounds-less corpus would silently produce
different outputs than before, breaking callers that run on minimal data. Gating on data presence
keeps the module honest: no data → no new behavior, outputs unchanged.

The secondary benefit is test stability: existing unit tests were written against the old API. Since
they never supply the new data source, they naturally exercise the no-op path. No test is modified
to preserve coverage; coverage is preserved by construction.

## Example (canonical)

**File 1**: `src/legacy_engine/advisory/sideboard.py` — `matchup_pressure` gate in `_build_coverage_model`
```python
def _build_coverage_model(
    field, archetype_tags, deck_colors, deck_tags,
    *,
    catalog=None,
    matchup_pressure: Optional[dict[str, float]] = None,  # NEW — None = no-op
) -> CoverageModel:
    ...
    # Step 3b: Apply matchup_pressure multipliers (NEW, gated)
    # When matchup_pressure is None this step is a no-op → byte-identical to pre-rework.
    if matchup_pressure is not None:
        for key in list(element_weight.keys()):
            if "|" not in key:
                continue  # skip anti-hate pseudo-elements
            arch = key.split("|", 1)[0]
            multiplier = matchup_pressure.get(arch, 1.0)
            if multiplier != 1.0:
                element_weight[key] = element_weight[key] * multiplier
```

The caller derives `matchup_pressure` only when `any_gate_cleared=True`; otherwise passes `None`
→ the coverage model is built identically to before.

**File 2**: `src/legacy_engine/advisory/sideboard.py` — additive `SideboardPackage` fields
```python
@dataclass
class SideboardPackage:
    # original fields ...
    cards: dict[str, int]
    trace: list[PickTrace]
    ...
    # NEW additive fields — all have defaults so existing constructors keep working:
    matchup_plans: dict[str, MatchupPlan] = dc_field(default_factory=dict)
    value_informed: bool = False
    plan_window: tuple[str | None, str | None] = (None, None)
```

**File 3**: `src/legacy_engine/generation/tuning.py` — `has_value_signal` gate → `no-signal-skip`
```python
def has_value_signal(fwv: dict[str, float]) -> bool:
    """Return True iff any card has a non-zero field-weighted value."""
    return any(v != 0.0 for v in fwv.values())

# In tune_deck:
if not has_value_signal(fwv):
    reason = "no-signal-skip: no gate-clearing per-card matchup data found ..."
    # ... return TunedDeck with objective="no-signal-skip", fell_back=True, no swaps
```

**Regression test**: `tests/test_sideboard.py::TestRegressionRoundsless` — exercises a rounds-less
corpus (empty Rounds tables), asserts that `recommend_sideboard` output is byte-identical to the
pre-extension baseline. Never modified when new signals are added.

## When to use
- Adding a new analytics signal (per-card value, time-series data, goldfish output) to a module
  that already ships working behavior on a data subset.
- Any case where the signal is absent on some corpora (rounds-less, data-sparse, deferred pillars)
  and you need existing tests to stay green without modification.

## When NOT to use
- New behavior that should always run regardless of data (use a plain conditional, not a gate).
- When the extension changes the existing output schema in a breaking way (redesign the API instead
  of patching it additively).

## Common violations
- Activating new behavior unconditionally and updating tests to pass the new data — this hides
  regressions instead of preventing them.
- Putting the gate inside the new-data branch instead of around it (the no-op path must be reached
  when data is absent, not a fallback inside the new logic).
- Adding required constructor fields to the output dataclass without defaults — breaks every
  existing call site.
