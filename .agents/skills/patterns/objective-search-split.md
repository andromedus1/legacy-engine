---
description: How to separate heavy data-dependent value computation from a pure search loop that takes the precomputed dict and an injected legality callable. Read before writing any greedy-search or optimization loop that touches the DB.
type: pattern
kind: planning
updated: 2026-05-31
summary: |
  Run the heavy DB-backed value computation once, producing a plain dict. Then pass that dict (plus
  an injected legality callable) into a pure loop function that has no DB dependency and is fully
  unit-testable with hand-built inputs. Eliminates vacuous DB-fixture tests and makes the search
  logic independently verifiable.
decisions:
  - "Value computation (field_weighted_values) runs ONCE before the loop and returns a plain dict[str, float]."
  - "The greedy loop (_greedy_tune) accepts fwv + legal_swap as parameters — no DB calls inside."
  - "legal_swap is an injected Callable so tests can supply a trivial lambda and avoid DB setup entirely."
  - "The orchestrator (tune_deck) owns the closure that wires the real DB-backed legality into the injected callable."
---

# Pattern: Objective-Search Split

Separate the heavy data-dependent value computation (run once → plain dict) from a pure search
loop that takes the value-lookup and an injected legality callable. The loop is unit-testable with
hand-built inputs and no DB.

## Rationale
A greedy search loop that calls the DB on every iteration is: (a) slow — N×M DB calls for N swap
rounds × M candidates; (b) hard to test — every test needs a realistic corpus fixture to exercise
any logic at all; and (c) hard to reason about — the heavy I/O path is entangled with the search
logic.

Splitting the two makes the search loop a pure function that can be tested with a hand-rolled
`fwv = {"Brainstorm": 0.05, "Ponder": -0.03}` and a `lambda m, c, a: (True, {...})` legality
stub. The test is fast, deterministic, and exercises the exact decision logic without a DB. The
real DB path is tested once at the orchestrator level.

## Example (canonical)

**File**: `src/legacy_engine/generation/tuning.py`

**Step 1 — value computation (runs ONCE):**
```python
def field_weighted_values(
    con: duckdb.DuckDBPyConnection,
    field: FieldDistribution,
    cards: list[str],
    *,
    since=None, until=None,
    gate=_VALUE_GATE,
) -> dict[str, float]:
    """Heavy path: runs compute_card_winrates ONCE, returns fwv[card] = Σ_opp share*lift."""
    r = compute_card_winrates(con, since=since, until=until)   # single DB call
    fwv: dict[str, float] = {card: 0.0 for card in cards}
    for opp, share in field.shares.items():
        cvs = card_values_vs(r, cards, "main", opp, gate=gate)
        for card, cv in cvs.items():
            if cv.tier in gate:
                fwv[card] = fwv.get(card, 0.0) + share * cv.lift
    return fwv
```

**Step 2 — pure greedy loop (no DB):**
```python
def _greedy_tune(
    fwv: dict[str, float],
    maindeck: dict[str, int],
    locked: dict[str, int],
    flex: dict[str, int],
    pool: list[str],
    *,
    max_swaps: int,
    legal_swap: Callable[[dict[str, int], str, str], tuple[bool, dict[str, int]]],
) -> tuple[dict[str, int], list[tuple[str, str]], float, float]:
    """Pure greedy maximising fwv[add] - fwv[cut].  No DB calls; legal_swap is injected."""
    ...
    for _round in range(max_swaps):
        for cut_card in sorted(current_flex.keys()):
            for add_card in pool:
                gain = fwv.get(add_card, 0.0) - fwv.get(cut_card, 0.0)
                if gain <= 0.0:
                    continue
                valid, new_main = legal_swap(current_main, cut_card, add_card)  # injected
                ...
```

**Step 3 — orchestrator wires the closure (tune_deck):**
```python
def _legal_swap_closure(current_main, cut, add):
    return _legal_swap_maindeck(current_main, cut, add, starting_sideboard,
                                banlist_snapshot=snapshot)

final_main, swaps, v_before, v_after = _greedy_tune(
    fwv, maindeck, locked, flex, pool,
    max_swaps=max_swaps,
    legal_swap=_legal_swap_closure,   # real DB-backed closure injected here
)
```

**Test**: `tests/test_generation_tuning.py::TestGreedyTune` — exercises `_greedy_tune` directly
with hand-built `fwv` dicts and a `lambda m, c, a: (True, {...})` legality stub. No DB, no
fixtures, deterministic. Tests cover: best-swap selection, locked-core protection, strict-improve
convergence, deterministic tie-break.

## When to use
- Any greedy/hill-climbing/search loop whose objective values come from a DB or external data.
- Anywhere you'd otherwise need to mock a DB connection to test loop convergence logic.

## When NOT to use
- One-shot functions where the computation and the "search" are a single pass with no iteration
  (no benefit to splitting; just adds indirection).
- When the loop needs DB access for reasons other than value lookup (e.g., legality requires a live
  corpus query on every candidate). In that case, mock the callable, not the DB.

## Common violations
- Calling `compute_card_winrates` or any DB query inside the loop body — turns an O(1) I/O cost
  into O(N×M).
- Hardcoding the legality function inside the loop instead of injecting it — forces DB fixtures in
  every test that touches the loop.
- Testing only the orchestrator (tune_deck) and skipping direct `_greedy_tune` tests — the loop
  logic gets covered only through the full integration path, hiding subtle convergence bugs.
