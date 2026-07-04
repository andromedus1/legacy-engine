---
id: feature-sb-board-backtest
kind: feature
stage: done
tags: [advisory, analytics]
parent: epic-sideboard-scoring-model
depends_on: [feature-sb-field-weighted-scorer]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Backtest recommended boards vs top-finisher boards

## Brief

Validation feature (E) of `epic-sideboard-scoring-model`, on top of the scorer (Feature B). The
empirical anchor for the whole scoring model.

Card-level impact CANNOT be validated directly with our data — the corpus has decklists + match
results, but no game-level with/without-card outcomes. What we *can* do: for a known field, compare
the scorer's recommended board against the sideboards that **top-finishing decks of the same archetype
actually ran**. If the recommended 15 systematically diverges from what wins in a comparable field,
that's evidence the model is off; if it converges, that's the closest thing to validation available.

Scope:
- For an archetype + field window, pull top-finisher decklists (standings + `deck_cards`) and extract
  their sideboards.
- Run the scorer for the same archetype/field and compare: overlap with observed winning boards,
  cards the scorer recommends that nobody plays (false positives), cards winners run that the scorer
  ranks low (false negatives / blind spots).
- Report as a validation summary, gated by sample tier (thin fields → low-confidence), on-ethos with
  the HONEST-DEGRADE POLICY.

Design notes:
- Reuse the corpus surfaces the engine already has: `decks`/`deck_cards`/`standings`/`rounds` and the
  player-strength subsystem (`analytics/players/*`) to define "top finisher."
- Beware confounds: winning boards are also self-selected and metagame-lagged; treat divergence as a
  signal to investigate, not proof of error. This backtest measures *resemblance to what wins*, not
  causal correctness.
- Motivating context: this is the guardrail against a beautiful-but-wrong scoring model — surfaced in
  the first-principles pass (falsification move) during the Dimir Tempo / Boulder-field dogfooding.

---

## Architectural choice

A new, self-contained validation surface — the empirical anchor for the scoring model. It does NOT touch the scorer's code path; it *calls* `recommend_sideboard` and compares its output to what top-finishing decks of the same archetype actually ran in a comparable field. Analysis logic in a new module `advisory/backtest.py`; a new `advise backtest` CLI leaf renders it. Reuses the corpus (`standings`/`decks`/`deck_cards`), the player-strength notion of "top finisher," and the confidence-metadata tiering for honest-degrade. Treats divergence as a signal to investigate, never as proof of error (winning boards are self-selected + metagame-lagged).

## Implementation Units

### Unit E1: backtest computation

**File**: `src/legacy_engine/advisory/backtest.py` (new). **Story**: `feature-sb-board-backtest-compute`.

```python
@dataclass(frozen=True)
class BoardBacktest:
    archetype: str
    n_winning_decks: int                    # sample of top-finisher decks compared against
    confidence: "ConfidenceLevel | None"    # tier_for_sample(n_winning_decks)
    recommended: tuple[str, ...]            # the scorer's board (card names)
    observed_frequency: dict[str, float]    # SB card → inclusion% among winning decks
    overlap: tuple[str, ...]                # recommended AND commonly-played (>= _OBSERVED_THRESHOLD)
    scorer_only: tuple[str, ...]            # recommended but rarely/never played (candidate false positives)
    winners_only: tuple[str, ...]           # commonly played but scorer ranked low (candidate blind spots)

_TOP_FINISHER_QUANTILE = 0.25   # top quartile by standings rank counts as "winning"
_OBSERVED_THRESHOLD = 0.20      # SB inclusion% among winners to count a card as "commonly played"

def backtest_board(con, archetype, field, *, since=None, until=None) -> BoardBacktest:
    """Pull top-finisher decklists of `archetype` in the window (standings rank <= top quartile),
    extract their sideboards + inclusion%, run recommend_sideboard for the same archetype+field,
    and diff. Honest-degrade: n_winning_decks below the evolving tier → low confidence label."""
```

### Unit E2: `advise backtest` CLI

**File**: `src/legacy_engine/cli.py`. **Story**: same.
`advise backtest --archetype <a> --field <file> [--since --until --db]`: render overlap / scorer-only / winners-only with observed inclusion%, an agreement summary, and the confidence tier. Honest-degrade banner when the winning-deck sample is thin; an explicit `// divergence is a signal to investigate, not proof of error (winning boards are self-selected + metagame-lagged)` caveat line.

## Implementation Order
Single story `…-compute` (E1 → E2).

## Testing
- `tests/test_backtest.py` (new): with a hermetic file-backed tmp DuckDB (standings + decks + deck_cards for an archetype with known SBs), `backtest_board` correctly classifies overlap / scorer-only / winners-only; honest-degrade tier on a thin winner sample; empty-corpus degrades to a labeled "insufficient data", not a crash.
- CLI test with a tmp `--db`.

## Risks
- **Confounds read as correctness** — winning boards are self-selected + lagged; a divergence isn't proof the scorer is wrong. *Fallback*: frame output as *resemblance*, with the explicit caveat line; never emit a pass/fail verdict.
- **Thin winner samples** — few top-finisher decks in a window. *Fallback*: `tier_for_sample` gates the confidence; below evolving → labeled low-confidence, no strong claims.
