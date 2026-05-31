---
description: How to apply two-level empirical-Bayes shrinkage for per-card×matchup win-rate estimates. Read before computing any conditional win-rate stat that has a natural hierarchy (card marginal → card-vs-opponent cell).
type: pattern
kind: planning
updated: 2026-05-31
summary: |
  Chain beta_binomial_shrink_to in two passes: first shrink the per-card marginal toward the global
  baseline; then shrink the per-(card, opponent) cell toward the SHRUNK marginal (not the raw prior).
  Thin matchup cells pull toward the card's overall inclusion-lift rather than the grand prior,
  preserving genuine card-level signal. The prior-contains-cell simplification is documented and
  accepted.
decisions:
  - "beta_binomial_shrink_to(wins, n, prior_mean, strength) is the generalized primitive; beta_binomial_shrink delegates to it with prior_mean=0.5 for the matchup matrix."
  - "Level 1 (marginal): shrink per-(card, board) aggregate toward global baseline_winrate (~0.5)."
  - "Level 2 (matchup cell): shrink per-(card, board, opponent) cell toward the card's shrunk marginal from level 1 — not the raw baseline."
  - "prior-contains-cell simplification: the card marginal aggregates ALL opponents including the target, so the prior is not strictly independent of the cell data. This is a standard, accepted EB approximation (documented in card_value.py)."
---

# Pattern: Two-Level Empirical-Bayes Shrinkage

`beta_binomial_shrink_to` is the generalized primitive. Chain it: shrink the marginal toward
the global baseline, then shrink the conditional cell toward the SHRUNK marginal.

## Rationale
A per-(card, opponent) cell has far fewer observations than the card's overall record. Shrinking
directly toward 0.5 (the grand prior) would ignore the card's known overall inclusion-lift — a
card like Brainstorm genuinely wins more than 50% even in thin cells, so a pure 0.5 prior is too
conservative.

Two-level EB fixes this: the card's marginal (computed from all opponents) is itself shrunk toward
0.5, but the shrinkage is weak at the margin's typical sample sizes (hundreds of matches). That
shrunk marginal becomes the prior for the matchup cell, so thin cells pull toward "the card's known
baseline" not "the global 50%". This preserves genuine card-level signal while still regularizing
volatile cell estimates.

The standard EB simplification: the card marginal sums over ALL opponents including the target cell,
so the prior is not strictly independent of the cell data (a card with one dominant opponent sees
its marginal inflated by that opponent's games). This slightly understates matchup lift magnitude
for dominant-matchup cards. It is a known, documented, accepted approximation — not a bug.

## Example (canonical)

**File 1**: `src/legacy_engine/analytics/matchup.py` — the generalized primitive
```python
SHRINK_STRENGTH = 15  # α+β = 15 (α=β=7.5, prior centered 0.5)

def beta_binomial_shrink_to(
    wins: int, n: int, *, prior_mean: float, strength: float = SHRINK_STRENGTH
) -> float:
    """Posterior-mean shrinkage toward an arbitrary prior_mean.

    a = prior_mean * strength
    b = (1 - prior_mean) * strength
    posterior_mean = (a + wins) / (a + b + n)

    n==0 → returns prior_mean (the prior, no data).
    """
    a = prior_mean * strength
    b = (1.0 - prior_mean) * strength
    denom = a + b + n
    return (a + wins) / denom if denom else prior_mean

def beta_binomial_shrink(wins, n, *, a=SHRINK_ALPHA, b=SHRINK_BETA) -> float:
    """Backward-compat wrapper: delegates to beta_binomial_shrink_to with prior_mean=0.5."""
    ...
```

**File 2**: `src/legacy_engine/analytics/card_value.py` — two-level chain
```python
def card_value_marginal(r: CardWinRates, card: str, board: str) -> CardValue:
    """Level 1: shrink per-(card, board) aggregate toward global baseline_winrate."""
    prior_mean = r.baseline_winrate   # ~0.5 by construction
    ...
    p_shrunk = beta_binomial_shrink_to(rec.wins, n, prior_mean=prior_mean,
                                       strength=SHRINK_STRENGTH)
    return CardValue(..., p_shrunk=p_shrunk, prior_mean=prior_mean, ...)

def card_value_matchup(r: CardWinRates, card: str, board: str, opponent: str) -> CardValue:
    """Level 2: shrink per-(card, board, opponent) cell toward the card's shrunk marginal."""
    marginal_cv = card_value_marginal(r, card, board)  # level-1 result
    prior_mean = marginal_cv.p_shrunk                  # SHRUNK marginal, not raw baseline
    # Note: prior-contains-cell EB simplification documented here — accepted.
    ...
    p_shrunk = beta_binomial_shrink_to(rec.wins, n, prior_mean=prior_mean,
                                       strength=SHRINK_STRENGTH)
    return CardValue(..., p_shrunk=p_shrunk, prior_mean=prior_mean,
                     lift=p_shrunk - prior_mean, ...)
```

The `lift` field is the key consumer signal: positive lift = this card outperforms its own marginal
vs this opponent; negative = it underperforms. The `tier` field (from `tier_for_sample(n)`) governs
whether callers trust the lift or degrade to a coverage heuristic.

## When to use
- Any hierarchical win-rate problem where you have a card (or deck, or player) marginal and a
  conditional cell against a specific opponent/context with fewer observations.
- Wherever the marginal provides a better prior than the grand mean (cards have known skill levels;
  decks have known meta-positioning).

## When NOT to use
- Flat stats with no natural hierarchy (e.g., meta-share % — there is no per-archetype marginal
  that conditions the per-event share; use Wilson/Jeffreys CI directly).
- When the marginal itself has very few observations (n < 30) — the level-1 shrinkage is weak and
  the "shrunk marginal as prior" offers little advantage over 0.5. Gate by tier first.

## Common violations
- Shrinking the matchup cell toward the RAW baseline (0.5) instead of the shrunk marginal — this
  ignores the card's known overall inclusion-lift and over-shrinks strong cards.
- Treating level-2 `lift` as causal (game-by-game draw effect). It is presence-correlational:
  "decks running this card vs this opponent win more often" — not a causal matchup delta.
- Forgetting the prior-contains-cell note when reviewing anomalous lift magnitudes for dominant
  matchup cards — the understatement is expected and documented, not a bug.
