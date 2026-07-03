---
id: feature-sb-board-backtest
kind: feature
stage: drafting
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
