---
id: feature-sb-slot-roi-punt
kind: feature
stage: drafting
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
