---
id: feature-sb-field-weighted-scorer
kind: feature
stage: drafting
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: [feature-sb-effect-tagging-model]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Field-weighted card scorer (coverage diagnostic + decomposed impact)

## Brief

Core feature (B) of `epic-sideboard-scoring-model`. The scorer that consumes the effect-tagging /
linchpin model (Feature A) and ranks/optimizes the 15 over the owned card pool.

Commitments (from the epic):
- **Objective = `Σ(field_share × Δequity)`** (expected match-win contribution). Coverage % is a
  *diagnostic* surfaced alongside, never the optimization target.
- **Decomposed impact** — `impact(card, opp) = centrality × symmetry × castability × draw-probability`
  (draw-probability = `P(draw ≥1 in a Bo3)` given copy count; hypergeometric). Reads centrality,
  symmetry, castability from Feature A.
- **Owned-only** via `data/collection/inventory.json`.
- **Field-share uncertainty** — propagate the Dirichlet field-share uncertainty already used in
  `advise positioning`; don't over-commit silver bullets to a noisy small-share matchup; flag
  brittle boards over-tuned to the snapshot.
- **Explainable** — every per-card score decomposes into its factors so the pilot can audit it
  (transparency substitutes for the empirical validation we can't do).
- **Honest-degrade gating** — thin/uncovered field cells labeled low-confidence (the Boulder field
  has ~36% of matchups with no data).

<!-- Design input below preserved from the folded backlog idea. -->

## Design input (from idea-field-weighted-sideboard-optimizer)

Score every sideboard candidate on two axes, then run all owned options through the scorer to
optimize the 15:
1. **Field coverage** — the share of the current field a card is *meaningfully relevant* against,
   summing field-shares of the archetypes it impacts (e.g. "Null Rod hits ~26%": Painter + D&T +
   Saga Storm + Eldrazi + Blue Artifacts). A single headline number per card, per field.
2. **Per-opponent impact score** — how hard the card swings each specific matchup it touches.
   Coverage % hides this: Null Rod is a near hard-lock vs Painter (stops Grindstone's activated
   ability) but a marginal mana-tax vs Eldrazi (doesn't touch Chalice, which is static). Impact is
   per-(card, opponent), not flat.

The novel/hard part is the **mechanics-grounded per-opponent IMPACT model** — what the card actually
does to that deck's gameplan — rather than curated swing constants or a presence-correlational proxy.
It reads the card-effect → archetype-plan interaction layer from Feature A (activated ability?
colorless spell? Tomb? a graveyard the deck doesn't have? a linchpin?).

Connects to existing surfaces: extends `advise sideboard` (field-weighting, `--smart` coverage
curve, natural-budget τ, per-card gain in `advisory/sideboard.py`); reuses `report cards --contrast`
as one empirical impact input where n≥30; feeds `feature-sb-slot-roi-punt` (this scores cards, that
allocates slots).

Honesty gates: coverage % is a *relevance* number, not a measured win-rate lift; impact scores are
mechanics-inferred, NOT causal before/after-board measurements (no game-level data in corpus). Every
score carries the caveat and gates by sample tier.

Motivating session (2026-07-03): hand-computed exactly this for Andrew's Dimir Tempo board vs the
107-player Boulder field; surfaced Mystical Dispute (~43%) and Spell Pierce (~54%) as high-coverage
anti-blue cards absent from the current SB.
