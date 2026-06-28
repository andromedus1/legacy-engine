---
id: idea-sideboard-slot-roi
created: 2026-06-28
tags: [advisory, sideboard]
---

# Sideboard slot ROI / "punt detection"

Decide whether dedicating N sideboard slots to a bad matchup is worth it, vs accepting
the matchup as unwinnable and reallocating the slots. A sideboard slot has opportunity
cost — the engine should quantify the marginal value of each dedicated SB card per
matchup and flag matchups where investment doesn't pay (i.e. tell the user "just accept
this is a bad matchup").

**Core question:** spending 6 cards to lift a 35% matchup to 42% (still a loss) at 5%
field share may be worse than spending those slots on a matchup you can flip across 0.5,
or on a higher-share matchup.

## Dimensions to model

- **Swing-per-card with diminishing returns.** The first hate card swings a matchup more
  than the 6th. Current swing magnitudes (`_SWING_DEDICATED=0.20`, `_SWING_SOFT=0.10` in
  `advisory/sideboard.py`) are flat per-card constants — they don't capture saturation.
  Need a concave swing curve with a cap on how far N cards can realistically move a cell.
- **Post-board win rate vs the 0.5 threshold.** Distinguish "investment crosses into
  favorable" (worth it) from "investment just makes a loss less bad" (often not worth it
  — equity gained while still below 0.5 is worth less than equity that flips a coin-flip).
- **Field-share weighting.** `marginal matchup-equity gain × field share = expected
  match-win contribution` — the real ROI unit, comparable across matchups.
- **Opportunity cost / reallocation.** Rank matchups by ROI-per-slot; surface "these
  slots would buy more expected wins if moved to matchup X."
- **Punt threshold.** Detect matchups where even max realistic dedication can't cross 0.5
  (or can't beat the ROI of the next-best slot) and recommend conceding them — spend the
  slots elsewhere or on proactive / maindeck-overlap cards.

## Connects to existing surfaces

Extends the smart sideboard (`--smart` coverage curve + natural-budget τ in
`advisory/sideboard.py`) with a per-matchup marginal-ROI table and a punt recommendation.
Reuse the adaptive ban-aware matchup matrix for base equities and the presence-correlational
swing proxy where n≥30, falling back to curated swing constants (with the honest-degrade
caveat) for thin cells.

## Honesty gates (project ethos)

Swing magnitudes are heuristic / presence-correlational, NOT causal before/after-board
measurements (no game-level data in corpus) — any ROI number must carry that caveat and
gate by sample tier. A punt recommendation on a thin/speculative matchup cell should be
labeled low-confidence.

## Worked example (today's Dimir Tempo board)

Death & Taxes 36.0% (n=106, established) and Lands 35.9% (n=123, established) are the worst
separated matchups, and the board spends heavily on them (2 Massacre, 2 Toxic Deluge,
Harbinger, Null Rod). Is that the right allocation, or would some of those slots buy more
expected wins reallocated to Blue Artifacts (41.3%, closer to flippable) or to shoring up
an even matchup? The engine currently can't answer that — this feature would.

Related: [[idea-sb-transformational-sideboarding]] (the "transform vs. answer" axis is the
other half of the slot-allocation decision).
