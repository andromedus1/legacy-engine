"""Per-card value builder — two-level empirical-Bayes confidence-rated estimates.

PRESENCE-CORRELATIONAL, NOT CAUSAL: all numbers here reflect the *registered 75*
for decks that appeared in resolved matches.  "Decks running card X win more vs
archetype M" is confounded by deck and pilot selection — we see presence, not
game-by-game draw sequences or sideboarding decisions.  Callers must not present
these as causal win-rate claims.

Two-level empirical-Bayes shrinkage:
  1. ``card_value_marginal``: shrink the per-(card, board) aggregate toward the
     global baseline win-rate (~0.5).
  2. ``card_value_matchup``: shrink the per-(card, board, opponent) cell toward
     the card's shrunk marginal from step 1.

This way thin matchup cells (low n) pull toward the card's overall inclusion-lift
rather than the raw grand prior, preserving any genuine card-level signal.
"""

from __future__ import annotations

from dataclasses import dataclass

from legacy_engine.analytics.match_results import CardWinRates
from legacy_engine.analytics.matchup import SHRINK_STRENGTH, beta_binomial_shrink_to
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample


@dataclass(frozen=True)
class CardValue:
    """Confidence-rated per-card value estimate.

    ``card``/``board``/``opponent``: the slice.  ``opponent`` is ``None`` for
    the overall marginal.

    ``p_raw``: raw wins/n.  ``None`` when ``n == 0`` (no observations).

    ``p_shrunk``: two-level empirical-Bayes posterior mean — what the model
    believes after shrinking toward the prior.

    ``prior_mean``: what ``p_shrunk`` was shrunk toward.  For the marginal this
    is the global ``baseline_winrate``; for the matchup cell this is the card's
    shrunk marginal ``p_shrunk``.

    ``lift``: ``p_shrunk - prior_mean`` — how much better/worse this card does
    above the prior in this slice.  Positive = favourable.

    ``n``: decisive match count for this cell.

    ``tier``: ``tier_for_sample(n)`` — ``"speculative"``/``"evolving"``/
    ``"established"``.  Consumers use this to decide whether to trust the
    number or degrade to a coverage heuristic.
    """

    card: str
    board: str
    opponent: str | None  # None = overall marginal
    p_raw: float | None   # wins/n, None when n==0
    p_shrunk: float       # two-level empirical-Bayes posterior mean
    prior_mean: float     # what p_shrunk was shrunk toward
    lift: float           # p_shrunk - prior_mean
    n: int
    tier: ConfidenceLevel  # tier_for_sample(n)


def card_value_marginal(r: CardWinRates, card: str, board: str) -> CardValue:
    """Overall inclusion-lift: how the card's deck-level win-rate compares to baseline.

    Prior is the global ``baseline_winrate`` (~0.5 by construction).  Shrinks the
    per-(card, board) marginal toward it.  Returns a zero-observation ``CardValue``
    (``n=0``, ``p_raw=None``, ``p_shrunk == prior_mean``) when the card is absent
    from the corpus.

    Presence-correlational: lift ≠ causal effect size.
    """
    rec = r.marginal.get((card, board))
    prior_mean = r.baseline_winrate
    if rec is None or rec.n == 0:
        return CardValue(
            card=card,
            board=board,
            opponent=None,
            p_raw=None,
            p_shrunk=prior_mean,
            prior_mean=prior_mean,
            lift=0.0,
            n=0,
            tier=tier_for_sample(0),
        )
    n = rec.n
    p_raw = rec.wins / n
    p_shrunk = beta_binomial_shrink_to(rec.wins, n, prior_mean=prior_mean, strength=SHRINK_STRENGTH)
    return CardValue(
        card=card,
        board=board,
        opponent=None,
        p_raw=p_raw,
        p_shrunk=p_shrunk,
        prior_mean=prior_mean,
        lift=p_shrunk - prior_mean,
        n=n,
        tier=tier_for_sample(n),
    )


def card_value_matchup(
    r: CardWinRates, card: str, board: str, opponent: str
) -> CardValue:
    """Per-card×matchup lift: how the card does vs THIS opponent vs the card's overall.

    Two-level shrinkage: the matchup cell shrinks toward the card's shrunk marginal
    (from ``card_value_marginal``), which itself shrinks toward the global baseline.
    For an unseen (card, board, opponent) cell ``n=0`` and ``p_shrunk == prior_mean``
    (the marginal).

    Presence-correlational: lift ≠ causal matchup delta.
    """
    marginal_cv = card_value_marginal(r, card, board)
    prior_mean = marginal_cv.p_shrunk  # two-level: matchup shrinks toward shrunk marginal

    rec = r.matchup.get((card, board, opponent))
    if rec is None or rec.n == 0:
        return CardValue(
            card=card,
            board=board,
            opponent=opponent,
            p_raw=None,
            p_shrunk=prior_mean,
            prior_mean=prior_mean,
            lift=0.0,
            n=0,
            tier=tier_for_sample(0),
        )
    n = rec.n
    p_raw = rec.wins / n
    p_shrunk = beta_binomial_shrink_to(rec.wins, n, prior_mean=prior_mean, strength=SHRINK_STRENGTH)
    return CardValue(
        card=card,
        board=board,
        opponent=opponent,
        p_raw=p_raw,
        p_shrunk=p_shrunk,
        prior_mean=prior_mean,
        lift=p_shrunk - prior_mean,
        n=n,
        tier=tier_for_sample(n),
    )


def card_values_vs(
    r: CardWinRates,
    cards: list[str],
    board: str,
    opponent: str,
    *,
    gate: tuple[str, ...] = ("evolving", "established"),
) -> dict[str, CardValue]:
    """Value each card vs ``opponent`` in ``board``.

    Returns a dict of ``card → CardValue`` for every card in ``cards``,
    regardless of tier.  The ``gate`` parameter is passed through for
    consumer convenience — callers use ``cv.tier in gate`` to decide whether
    to trust the number or degrade to a coverage heuristic.

    This function does NOT suppress any rows; suppression is the caller's
    responsibility so that the contract with ``epic-deck-generation-sideboard-
    maindeck`` and the tuning rework remains gate-then-degrade.
    """
    return {card: card_value_matchup(r, card, board, opponent) for card in cards}
