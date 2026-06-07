---
id: epic-advisory-output-honesty-whattoplay-honesty
kind: feature
stage: drafting
tags: [advisory]
parent: epic-advisory-output-honesty
depends_on: [epic-advisory-output-honesty-positioning-coverage]
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-06
---

# Honest "What to Play" Output

## Brief

Fix two ways the "what to play" advisor misleads or omits. First, `best_deck_vs_best_call` uses hard
cutoffs (spread_hi=0.02, mean_hi=0.52) that create cliff effects — Death & Taxes was the best field
pick yet got labeled "neither" because it sat the wrong side of a threshold. Second, `whattoplay`
prints proactivity, vulnerability tags, and the best-deck-call but omits the positioning `S` (expected
win rate) — the single number a user most wants from the advisor.

Covers: replacing the best-call threshold cliffs with a continuous/gradient signal (so near-boundary
decks aren't mislabeled); surfacing the positioning S in the whattoplay output. The S surfaced here is
the **coverage-aware S** from the positioning-coverage feature, so the advisor never prints an
imputation-prior number without its coverage context.

Does NOT cover: the positioning math/coverage itself (that's the dependency); sideboard output.

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: consumer of `positioning-coverage` (surfaces its coverage-aware S).

## Inherited design decisions
- **Surface the coverage-aware S** from `epic-advisory-output-honesty-positioning-coverage` — do not
  recompute a bare full-field S in the whattoplay surface.
- Best-call gradient replaces the hard spread_hi/mean_hi cutoffs; near-threshold decks get a
  continuous signal rather than a binary "neither".

## Foundation references
- `docs/SPEC.md` — Pillar 4 "What to play" advisor; "no unlabeled headline numbers" NFR
- `src/legacy_engine/advisory/whattoplay.py`, `advisory/report.py`, `cli.py`
