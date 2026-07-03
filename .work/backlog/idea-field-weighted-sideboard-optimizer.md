---
id: idea-field-weighted-sideboard-optimizer
created: 2026-07-03
tags: [advisory, sideboard]
---

# Field-weighted sideboard optimizer (coverage × per-opponent impact)

Score every sideboard candidate on two axes, then run all owned options through the
scorer to optimize the 15:

1. **Field coverage** — the share of the current field a card is *meaningfully relevant*
   against, computed by summing the field-shares of the archetypes it impacts (e.g.
   "Null Rod hits ~26%": Painter + D&T + Saga Storm + Eldrazi + Blue Artifacts). A single
   headline number per card, per field.
2. **Per-opponent impact score** — how hard the card swings each specific matchup it
   touches. Coverage % hides this: Null Rod is a near hard-lock vs Painter (stops
   Grindstone's activated ability) but only a marginal mana-tax vs Eldrazi (doesn't touch
   Chalice, which is static). Impact must be per-(card, opponent), not flat.

Combine `coverage × per-opponent impact`, field-weighted, into one card score; rank and
optimize the board over the pool.

## The missing piece

The novel/hard part is a **principled per-opponent IMPACT model grounded in card
mechanics / oracle text** — what the card actually does to that deck's gameplan (e.g.
"stops the combo's activated ability," "counters their only Kappa answer," "sweeps their
whole board," "color-screws a nonbasic manabase") — rather than the curated swing
constants or presence-correlational proxy the current tools lean on. This likely needs a
card-effect → archetype-plan interaction layer (does the card hit an activated ability?
a colorless spell? a Tomb? a graveyard the deck doesn't have?).

## Connects to existing surfaces

- Extends `advise sideboard`: it already has field-weighting, a `--smart` coverage curve,
  natural-budget τ, and a per-card gain — but uses curated `_SWING_DEDICATED`/`_SWING_SOFT`
  constants + a presence-correlational swing proxy (`advisory/sideboard.py`).
- Reuses `report cards --contrast` (matchup-conditioned WITH/WITHOUT slot test) as one
  empirical impact input where n≥30.
- Feeds [[idea-sideboard-slot-roi]] — that item is the slot opportunity-cost / punt-detection
  ranker; this item is the per-card scoring engine it would consume. They compose:
  coverage×impact per card → ROI-per-slot allocation across matchups.

## Honesty gates (project ethos)

Coverage % is a *relevance* number, not a measured win-rate lift; impact scores are
mechanics-inferred or presence-correlational, NOT causal before/after-board measurements
(no game-level data in corpus). Every score carries the caveat and gates by sample tier;
thin/uncovered field cells (the 107-player Boulder field has ~36% of matchups with no
data) are labeled low-confidence. Should respect the collection (owned-only mode).

## Motivating session (2026-07-03)

Hand-computed exactly this for Andrew's Dimir Tempo board vs the 107-player Boulder field:
ranked owned hate by field-coverage % against the Null Rod benchmark (~26%). Surfaced
**Mystical Dispute (~43%)** and **Spell Pierce (~54%)** as high-coverage anti-blue cards
absent from the current SB, and flagged coverage-vs-impact divergence (Null Rod's flat 26%
spans a Painter lock and a marginal Eldrazi tax). The manual pass is what this feature
would automate.
