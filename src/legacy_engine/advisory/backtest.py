"""Board backtest — the empirical anchor for the sideboard scoring model.

Card-level impact CANNOT be validated directly with this corpus (decklists + match
results, but no game-level with/without-card outcomes). What we *can* do: for a known
field, compare the scorer's recommended board (``recommend_sideboard``) against the
sideboards that top-finishing decks of the *same archetype* actually ran in a
comparable window. If the recommended 15 systematically diverges from what wins in a
comparable field, that's a signal to investigate; if it converges, that's the closest
thing to validation this corpus can offer.

This module does NOT touch the scorer's code path — it calls ``recommend_sideboard``
exactly as any other caller would and diffs its output against observed data. Reuses
the corpus surfaces (``standings``/``decks``/``deck_cards``) and the confidence-metadata
tiering for honest-degrade.

CONFOUNDS (read before interpreting output): winning boards are self-selected (players
choose what to sideboard; a card's presence does not mean it was correct) and
metagame-lagged (a winning list reflects the field at the time it was built, which may
differ from the field passed in here). Divergence between the scorer and observed
winning boards is a signal to investigate, never proof the scorer is wrong — and
agreement is not proof it is right, either. This module NEVER emits a pass/fail
verdict; it only reports resemblance, gated by sample-size confidence.

Top-finisher definition: for each tournament, a deck of the target archetype counts as
a "top finisher" when its player's ``standings.rank`` falls within the top
``_TOP_FINISHER_QUANTILE`` fraction of that tournament's field (ties in "how many
players count as top" are resolved by rounding UP — ``ceil`` — so a quartile cut on a
4-player tournament still yields at least 1 qualifying rank, never 0). Ambiguous
normalized player names (a handle that is non-unique within a tournament, in either
``decks`` or ``standings``) are excluded from the join rather than guessed at, mirroring
the dup/uniq precedent in ``analytics.match_results``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.sideboard import recommend_sideboard
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample
from legacy_engine.generation.consensus import card_frequencies

log = logging.getLogger(__name__)

# Top quartile by standings rank, per tournament, counts as "winning" for this backtest.
_TOP_FINISHER_QUANTILE = 0.25

# SB inclusion% among top-finisher decks required to count a card as "commonly played".
_OBSERVED_THRESHOLD = 0.20


@dataclass(frozen=True)
class BoardBacktest:
    """Result of backtesting the scorer's recommended board against observed winners.

    ``confidence`` is ``None`` when ``n_winning_decks == 0`` — there is literally nothing
    to compare against (a distinct, more honest state than ``tier_for_sample(0)``'s
    "speculative", which would imply a thin-but-real signal). When ``n_winning_decks > 0``
    it is ``tier_for_sample(n_winning_decks)`` ("speculative" / "evolving" / "established").

    ``recommended``, ``overlap``, and ``scorer_only`` are sorted tuples of card names for
    deterministic output; ``overlap`` ∪ ``scorer_only`` == ``recommended`` (a partition).
    ``winners_only`` cards are NOT in ``recommended`` at all — candidate blind spots.
    """

    archetype: str
    n_winning_decks: int                    # sample of top-finisher decks compared against
    confidence: "ConfidenceLevel | None"    # tier_for_sample(n_winning_decks), or None if n=0
    recommended: tuple[str, ...]            # the scorer's board (card names)
    observed_frequency: dict[str, float]    # SB card -> inclusion% among winning decks
    overlap: tuple[str, ...]                # recommended AND commonly-played (>= _OBSERVED_THRESHOLD)
    scorer_only: tuple[str, ...]            # recommended but rarely/never played (candidate false positives)
    winners_only: tuple[str, ...]           # commonly played but not recommended (candidate blind spots)


# ---------------------------------------------------------------------------
# Top-finisher deck resolution
# ---------------------------------------------------------------------------
# Mirrors analytics.match_results' dup/uniq-normalized-player-join precedent: a
# normalized handle (lower(trim(player))) that occurs more than once within a
# tournament is ambiguous and excluded rather than arbitrarily attributed.

_QUALIFYING_DECKS_SQL = """
WITH
dup_decks AS (
    SELECT tournament_id, lower(trim(player)) AS norm
    FROM decks
    GROUP BY tournament_id, lower(trim(player))
    HAVING count(*) > 1
),
dup_standings AS (
    SELECT tournament_id, lower(trim(player)) AS norm
    FROM standings
    GROUP BY tournament_id, lower(trim(player))
    HAVING count(*) > 1
),
uniq_standings AS (
    SELECT s.tournament_id, lower(trim(s.player)) AS norm, MIN(s.rank) AS rank
    FROM standings s
    LEFT JOIN dup_standings ds
        ON ds.tournament_id = s.tournament_id AND ds.norm = lower(trim(s.player))
    WHERE ds.norm IS NULL
    GROUP BY s.tournament_id, lower(trim(s.player))
),
field_size AS (
    SELECT tournament_id, count(*) AS n_players
    FROM uniq_standings
    GROUP BY tournament_id
),
qualifying AS (
    -- "Top finisher": rank <= the top-quantile cutoff for that tournament's field size,
    -- rounded UP so a quartile cut always keeps at least 1 qualifying rank.
    SELECT us.tournament_id, us.norm
    FROM uniq_standings us
    JOIN field_size fs ON fs.tournament_id = us.tournament_id
    WHERE us.rank <= GREATEST(1, CAST(CEIL(? * fs.n_players) AS INTEGER))
)
SELECT d.tournament_id, d.deck_idx
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
JOIN qualifying q ON q.tournament_id = d.tournament_id
                 AND q.norm = lower(trim(d.player))
LEFT JOIN dup_decks dd ON dd.tournament_id = d.tournament_id
                       AND dd.norm = lower(trim(d.player))
WHERE d.archetype = ?
  AND dd.norm IS NULL
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date < ?)
"""


def _qualifying_top_finisher_decks(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    *,
    since: str | None,
    until: str | None,
) -> list[tuple[str, int]]:
    """Return ``[(tournament_id, deck_idx), ...]`` for top-finisher decks of ``archetype``.

    Never raises — a query failure (e.g. schema not initialised) degrades to an empty
    list, which the caller turns into an honest "insufficient data" result rather than
    a crash.
    """
    try:
        rows = con.execute(
            _QUALIFYING_DECKS_SQL,
            [_TOP_FINISHER_QUANTILE, archetype, since, since, until, until],
        ).fetchall()
    except Exception as exc:
        log.debug(
            "_qualifying_top_finisher_decks: query failed for %r: %s", archetype, exc
        )
        return []
    return [(tid, idx) for tid, idx in rows]


def _observed_sideboard_frequency(
    con: duckdb.DuckDBPyConnection,
    deck_keys: list[tuple[str, int]],
) -> dict[str, float]:
    """Per-card sideboard inclusion% across ``deck_keys`` (each weighted equally, once).

    Returns ``{}`` for an empty ``deck_keys`` (nothing to observe) and degrades to ``{}``
    on any query failure rather than raising.
    """
    if not deck_keys:
        return {}
    try:
        values_sql = ", ".join(["(?, ?)"] * len(deck_keys))
        params: list = [v for pair in deck_keys for v in pair]
        rows = con.execute(
            f"""
            SELECT DISTINCT dc.tournament_id, dc.deck_idx, dc.name
            FROM deck_cards dc
            JOIN (VALUES {values_sql}) AS qd(tournament_id, deck_idx)
              ON dc.tournament_id = qd.tournament_id AND dc.deck_idx = qd.deck_idx
            WHERE dc.board = 'side'
            """,
            params,
        ).fetchall()
    except Exception as exc:
        log.debug("_observed_sideboard_frequency: query failed: %s", exc)
        return {}

    n = len(deck_keys)
    card_deck_count: dict[str, int] = {}
    for _tid, _idx, name in rows:
        card_deck_count[name] = card_deck_count.get(name, 0) + 1
    return {name: count / n for name, count in card_deck_count.items()}


def backtest_board(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    field: FieldDistribution,
    *,
    since: str | None = None,
    until: str | None = None,
) -> BoardBacktest:
    """Backtest the scorer's recommended board against top-finisher boards.

    Pulls top-finisher decklists of ``archetype`` in the ``[since, until)`` window
    (standings rank within the top ``_TOP_FINISHER_QUANTILE`` of the field, per
    tournament — see module docstring), extracts their sideboards + inclusion%, runs
    ``recommend_sideboard`` for the same archetype + ``field`` over the archetype's
    modal in-window maindeck (no real user decklist exists in a backtest; the modal
    composition — the same role ``card_frequencies`` already plays for
    ``advisory.sideboard._archetype_linchpins_and_cards`` — stands in), and classifies
    every card into overlap / scorer_only / winners_only using ``_OBSERVED_THRESHOLD``.

    Honest-degrade: never raises. A thin or absent top-finisher sample degrades to a
    low/absent confidence label (``None`` at n=0, else ``tier_for_sample``); a scorer
    failure degrades ``recommended`` to an empty tuple (every observed card then reads
    as ``winners_only``, which is the correct honest signal — "we have nothing to
    compare the scorer against"). This function never emits a pass/fail verdict.
    """
    deck_keys = _qualifying_top_finisher_decks(con, archetype, since=since, until=until)
    n_winning_decks = len(deck_keys)
    observed_frequency = _observed_sideboard_frequency(con, deck_keys)

    recommended: tuple[str, ...] = ()
    try:
        main_freqs = card_frequencies(con, archetype, board="main", since=since, until=until)
        modal_maindeck = {cf.name: cf.modal_count for cf in main_freqs}
        pkg = recommend_sideboard(
            con, field, modal_maindeck,
            archetype=archetype,
            since=since,
            until=until,
        )
        recommended = tuple(sorted(pkg.cards.keys()))
    except Exception as exc:
        log.debug("backtest_board: recommend_sideboard failed for %r: %s", archetype, exc)
        recommended = ()

    overlap = tuple(
        sorted(c for c in recommended if observed_frequency.get(c, 0.0) >= _OBSERVED_THRESHOLD)
    )
    scorer_only = tuple(
        sorted(c for c in recommended if observed_frequency.get(c, 0.0) < _OBSERVED_THRESHOLD)
    )
    recommended_set = set(recommended)
    winners_only = tuple(
        sorted(
            c
            for c, pct in observed_frequency.items()
            if pct >= _OBSERVED_THRESHOLD and c not in recommended_set
        )
    )

    confidence: "ConfidenceLevel | None" = (
        None if n_winning_decks == 0 else tier_for_sample(n_winning_decks)
    )

    return BoardBacktest(
        archetype=archetype,
        n_winning_decks=n_winning_decks,
        confidence=confidence,
        recommended=recommended,
        observed_frequency=observed_frequency,
        overlap=overlap,
        scorer_only=scorer_only,
        winners_only=winners_only,
    )
