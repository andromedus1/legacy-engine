---
id: feature-sb-slot-roi-punt
kind: feature
stage: done
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: [feature-sb-field-weighted-scorer]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Sideboard slot ROI / punt detection

## Brief

Refinement (D) of `epic-sideboard-scoring-model`, on top of the scorer (Feature B). Decide whether
dedicating N slots to a bad matchup is worth it vs conceding it and reallocating — the slot-allocation
layer above per-card scoring. (Second-wave extension noted in the epic: model the OUT-side cost of the
swap, not just the IN.)

<!-- Design input below preserved from the folded backlog idea. -->

## Design input (from idea-sideboard-slot-roi)

Decide whether dedicating N sideboard slots to a bad matchup is worth it, vs accepting the matchup as
unwinnable and reallocating the slots. A slot has opportunity cost — quantify the marginal value of
each dedicated SB card per matchup and flag matchups where investment doesn't pay.

**Core question:** spending 6 cards to lift a 35% matchup to 42% (still a loss) at 5% field share may
be worse than spending those slots on a matchup you can flip across 0.5, or a higher-share matchup.

### Dimensions to model

- **Swing-per-card with diminishing returns.** The first hate card swings more than the 6th. Current
  swing magnitudes (`_SWING_DEDICATED=0.20`, `_SWING_SOFT=0.10`) are flat per-card constants. Need a
  concave swing curve with a cap on how far N cards can realistically move a cell.
- **Post-board win rate vs the 0.5 threshold.** Distinguish "investment crosses into favorable" from
  "investment just makes a loss less bad" (equity gained while still below 0.5 is worth less than
  equity that flips a coin-flip).
- **Field-share weighting.** `marginal matchup-equity gain × field share = expected match-win
  contribution` — the real ROI unit, comparable across matchups (this is the epic's objective).
- **Opportunity cost / reallocation.** Rank matchups by ROI-per-slot; surface "these slots would buy
  more expected wins if moved to matchup X."
- **Punt threshold.** Detect matchups where even max realistic dedication can't cross 0.5 (or beat the
  ROI of the next-best slot) and recommend conceding them.

Connects to existing surfaces: extends the smart sideboard (`--smart` coverage curve + natural-budget
τ). Reuse the adaptive ban-aware matchup matrix for base equities. Honesty gates: swing magnitudes are
heuristic / presence-correlational; any ROI number carries the caveat and gates by sample tier; a punt
recommendation on a thin/speculative cell is labeled low-confidence.

Worked example (Dimir Tempo board): Death & Taxes ~36% and Lands ~36% are the worst separated
matchups, and the board spends heavily on them. Is that the right allocation, or would some slots buy
more expected wins reallocated to Blue Artifacts (~41%, closer to flippable)? The engine currently
can't answer — this feature would.

Related: `idea-sb-transformational-sideboarding` (the "transform vs answer" axis is the other half of
the slot-allocation decision).

---

## Architectural choice

Additive analysis/output layer (same shape as B5): compute a per-matchup slot-ROI table + punt flags from the field + the adaptive matchup matrix (base equities) + the coverage model's realistic marginal-gain curve, append to `SideboardPackage`, and render in `advise sideboard`. Does NOT change the solver objective or which cards are picked — it's decision support about *slot allocation*. Consumes Feature B's `_build_coverage_model` output; reuses `analytics/matchup` for base equities and the confidence-metadata tiering for honest-degrade.

## Implementation Units

### Unit D1: per-matchup slot-ROI computation

**File**: `src/legacy_engine/advisory/sideboard.py`. **Story**: `feature-sb-slot-roi-punt-roi`.

```python
@dataclass(frozen=True)
class MatchupROI:
    opponent: str
    field_share: float
    base_equity: float          # matchup cell p_shrunk vs my archetype (0.5 when thin/absent)
    max_equity_gain: float      # realistic ceiling from dedicating slots (concave swing cap, saturating)
    roi_per_slot: float         # marginal equity gain of the FIRST dedicated slot × field_share
    crosses_half: bool          # base_equity + max_equity_gain >= 0.5
    punt: bool
    confidence: "ConfidenceLevel | None"

def _slot_roi_table(deck_archetype, field, matchup_matrix, coverage_model) -> list[MatchupROI]:
    """Per field matchup: base equity from matchup_matrix (honest-degrade to 0.5 + low confidence
    when the cell is thin/absent), the concave marginal-gain curve reused from the coverage model's
    swing × _u_redundancy shaping (so ROI is consistent with what the solver can actually buy),
    field_share weighting, ranked by roi_per_slot desc."""
```

### Unit D2: punt detection

**File**: same. **Story**: same.
Flag `punt = True` when EITHER: (a) `base_equity + max_equity_gain < 0.5` (max realistic dedication still can't win the matchup) OR (b) `roi_per_slot` is below the ROI of the next-best *unfilled* slot elsewhere (the slots buy more expected wins reallocated). Never punt a `speculative`-tier (thin-data) matchup — label it low-confidence instead of recommending a concession on noise.

### Unit D3: render in `advise sideboard`

**File**: `src/legacy_engine/advisory/sideboard.py` (+ `cli.py` render). **Story**: same.
A `// slot-ROI (decision support — expected match-win per dedicated slot):` block: ranked matchups with base→ceiling equity, ROI/slot, and a `[PUNT — reallocate: max dedication still <50%]` / `[PUNT — better ROI elsewhere]` marker, each with its confidence tier. Honest-degrade: thin cells labeled, no punt call on speculative data.

## Implementation Order
Single story `…-roi` (D1 → D2 → D3). Cohesive analysis layer; additive to the package.

## Testing
- `tests/test_sideboard.py`: `_slot_roi_table` ROI ranking + base-equity honest-degrade (thin cell → 0.5 + low confidence); punt flag on a can't-cross-0.5 matchup; NO punt on a speculative-tier matchup; reallocation punt when a lower-ROI slot loses to a higher-ROI one; additive/byte-identical to the card selection (D changes no picks).
- CLI render test with a tmp `--db`.

## Risks
- **Punting a winnable matchup on thin data** — the whole point is not to concede on noise. *Fallback*: hard rule — never punt a `speculative` cell; punts require an `evolving`+ base-equity tier.
- **ROI curve inconsistent with the solver** — if D's marginal-gain curve diverges from what the solver actually buys, the advice misleads. *Fallback*: reuse the coverage model's own `swing × _u_redundancy` shaping so D's ROI and the solver's picks share one curve.
