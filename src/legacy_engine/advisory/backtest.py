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

FIELD SCOPING (feature-sfv-backtest-scoped): a global, all-time top-finisher sample mixes
eras whose metagame looked nothing like the field being scored against — e.g. a
graveyard-strategy-heavy period contributes Surgical Extraction / Grafdigger's Cage to
``observed_frequency`` even when the caller's field (say, a current local-field-dominated
field) barely has a graveyard deck in it. ``field_scope`` (default on) filters OUT
candidate tournaments whose own realized metagame does not overlap the caller's
``field`` archetype set by at least ``_FIELD_OVERLAP_MIN`` — see
``_tournament_archetype_counts`` (DB) + ``_apply_field_scope`` (pure filter) below. This
is a cross-sectional filter (what archetypes were actually in that room), not a
calendar-era heuristic, so it captures metagame drift more precisely than a ban-regime
date window would; ``since``/``until`` remain available to layer an explicit calendar
window on top when wanted, but neither is defaulted to a "current regime" window here —
unlike ``generation.consensus.card_frequencies`` — because doing so would piggyback this
diagnostic's behavior on an unrelated module's regime SSOT and risks silently emptying
a deliberately-dated backtest; explicit ``None`` stays "full corpus", matching
``analytics.match_results``' documented convention.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
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

# A candidate tournament counts as "in-field" only when at least this fraction of its
# (labeled) decks belong to an archetype present in the caller's FieldDistribution.
_FIELD_OVERLAP_MIN = 0.5


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

    ``field_scope``/``n_tournaments_considered``/``n_tournaments_excluded`` (feature-
    sfv-backtest-scoped) report the field-scoping decision honestly: how many candidate
    tournaments (post window, pre field filter) were considered, and how many of those
    were dropped for not resembling the caller's field. Both counts are 0 when
    ``field_scope=False`` (no filtering applied) or when there were no candidates at all.
    """

    archetype: str
    n_winning_decks: int                    # sample of top-finisher decks compared against
    confidence: "ConfidenceLevel | None"    # tier_for_sample(n_winning_decks), or None if n=0
    recommended: tuple[str, ...]            # the scorer's board (card names)
    observed_frequency: dict[str, float]    # SB card -> inclusion% among winning decks
    overlap: tuple[str, ...]                # recommended AND commonly-played (>= _OBSERVED_THRESHOLD)
    scorer_only: tuple[str, ...]            # recommended but rarely/never played (candidate false positives)
    winners_only: tuple[str, ...]           # commonly played but not recommended (candidate blind spots)
    field_scope: bool = True                # whether the tournament-level field-overlap filter ran
    n_tournaments_considered: int = 0       # distinct candidate tournaments, post window / pre field filter
    n_tournaments_excluded: int = 0         # of those, how many were dropped as off-field


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


# ---------------------------------------------------------------------------
# Field scoping (feature-sfv-backtest-scoped)
# ---------------------------------------------------------------------------
# Objective-search-split shape (see .agents/skills/patterns/objective-search-split.md):
# `_tournament_archetype_counts` does the one heavy, archetype-agnostic DB read; the
# actual field-membership decision is a pure function (`_apply_field_scope`) over plain
# dicts, so the filtering logic is unit-testable with hand-built inputs and no DB.


def _tournament_archetype_counts(
    con: duckdb.DuckDBPyConnection,
    tournament_ids: list[str],
) -> dict[str, dict[str, int]]:
    """Return ``{tournament_id: {archetype: n_decks}}`` for every id in ``tournament_ids``.

    Archetype-agnostic on purpose — this is the heavy DB half of the field-scoping split;
    ``_apply_field_scope`` decides which archetypes "count" as in-field. Decks with a
    ``NULL`` archetype are excluded from the counts entirely (an unlabeled deck is not
    evidence either way, so it should not dilute the denominator). Never raises — a query
    failure degrades to ``{}``, which ``_apply_field_scope`` treats as "no evidence" for
    every affected tournament (conservatively excluded, never fabricated as in-field).
    """
    if not tournament_ids:
        return {}
    try:
        placeholders = ", ".join(["?"] * len(tournament_ids))
        rows = con.execute(
            f"""
            SELECT tournament_id, archetype, count(*) AS n
            FROM decks
            WHERE tournament_id IN ({placeholders})
              AND archetype IS NOT NULL
            GROUP BY tournament_id, archetype
            """,
            tournament_ids,
        ).fetchall()
    except Exception as exc:
        log.debug("_tournament_archetype_counts: query failed: %s", exc)
        return {}

    out: dict[str, dict[str, int]] = {}
    for tid, archetype, n in rows:
        out.setdefault(tid, {})[archetype] = n
    return out


def _apply_field_scope(
    deck_keys: list[tuple[str, int]],
    archetype_counts: dict[str, dict[str, int]],
    field_archetypes: Collection[str],
    *,
    min_overlap: float = _FIELD_OVERLAP_MIN,
) -> tuple[list[tuple[str, int]], int, int]:
    """Pure filter: keep only decks whose tournament's realized metagame overlaps ``field_archetypes``.

    A tournament counts as "in-field" when at least ``min_overlap`` of its labeled decks
    (per ``archetype_counts``) belong to an archetype in ``field_archetypes`` — e.g. a
    tournament that was 6/8 Reanimator does not represent a local field and is dropped
    even though its top-finishing the local meta decks pass the rank cut on their own.

    Returns ``(kept_deck_keys, n_tournaments_considered, n_tournaments_excluded)`` where
    the counts are over the DISTINCT tournaments present in ``deck_keys`` (for the CLI's
    honest field-scope banner). No DB access — hand-built dicts exercise this directly.
    """
    field_set = frozenset(field_archetypes)
    considered_tids = {tid for tid, _ in deck_keys}

    in_field_tids: set[str] = set()
    for tid in considered_tids:
        counts = archetype_counts.get(tid, {})
        total = sum(counts.values())
        if total == 0:
            continue  # no labeled evidence -> conservatively excluded, not fabricated in-field
        in_field = sum(n for a, n in counts.items() if a in field_set)
        if (in_field / total) >= min_overlap:
            in_field_tids.add(tid)

    kept = [(tid, idx) for tid, idx in deck_keys if tid in in_field_tids]
    n_considered = len(considered_tids)
    n_excluded = n_considered - len(in_field_tids)
    return kept, n_considered, n_excluded


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
    field_scope: bool = True,
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

    ``field_scope`` (default ``True``, feature-sfv-backtest-scoped): when set, candidate
    top-finisher tournaments whose own realized metagame does not overlap ``field``'s
    archetype set by ``_FIELD_OVERLAP_MIN`` are dropped before computing
    ``observed_frequency`` — see the module docstring's FIELD SCOPING section. Pass
    ``False`` to reproduce the prior (global, unscoped) sample for comparison/debugging.

    Honest-degrade: never raises. A thin or absent top-finisher sample (whether thin from
    the start or thinned BY field-scoping) degrades to a low/absent confidence label
    (``None`` at n=0, else ``tier_for_sample``); a scorer failure degrades ``recommended``
    to an empty tuple (every observed card then reads as ``winners_only``, which is the
    correct honest signal — "we have nothing to compare the scorer against"). This
    function never emits a pass/fail verdict.
    """
    deck_keys = _qualifying_top_finisher_decks(con, archetype, since=since, until=until)

    n_tournaments_considered = len({tid for tid, _ in deck_keys})
    n_tournaments_excluded = 0
    if field_scope and deck_keys:
        tournament_ids = sorted({tid for tid, _ in deck_keys})
        archetype_counts = _tournament_archetype_counts(con, tournament_ids)
        deck_keys, n_tournaments_considered, n_tournaments_excluded = _apply_field_scope(
            deck_keys, archetype_counts, field.shares.keys(),
        )

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
        field_scope=field_scope,
        n_tournaments_considered=n_tournaments_considered,
        n_tournaments_excluded=n_tournaments_excluded,
    )
