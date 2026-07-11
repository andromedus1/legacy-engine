"""Subgroup-diff analysis — validated discovery tool for sub-archetype variants.

Splits an archetype's decks on the presence of a candidate signature card and diffs the
two subgroups' *average* compositions to expose the variant character.  Follows the
**objective-search-split** pattern: one heavy DB pass → plain dicts → a pure diff function.

Validated method (2026-06-13): splitting Dimir Tempo on Mishra's Bauble revealed a coherent
variant — Bauble decks ran +2.43 Nethergoyf, +0.52 Daze, and −1.06 Barrowgoyf vs non-Bauble
decks.  This is the discovery front-end that tells you which signature card to write into the
variant registry.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from legacy_engine.analytics.match_results import _DUP_UNIQ_CTE, parse_match_result
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CardDiff:
    """Per-card diff between the with-subgroup and without-subgroup average compositions."""

    name: str
    avg_with: float     # average copies per deck in the with-subgroup (0.0 if absent)
    avg_without: float  # average copies per deck in the without-subgroup (0.0 if absent)
    delta: float        # avg_with − avg_without (positive = more in with-subgroup)


@dataclass
class SubgroupSplit:
    """Result of splitting an archetype on a signature card."""

    archetype: str
    signature_card: str
    board: str          # "main" or "side" — the board queried for the signature card
    n_with: int         # decks that contain the signature card
    n_without: int      # decks that do NOT contain the signature card
    diffs: list[CardDiff]    # sorted by abs(delta) descending
    tier_with: ConfidenceLevel
    tier_without: ConfidenceLevel
    thin: bool          # True when either subgroup is below the speculative floor (n < 30)

    # Optional per-camp match win-rate (epic-subarchetype-resolution-card-winrate).
    # None unless subgroup_compositions(..., with_winrates=True) was requested — default
    # off keeps this byte-identical to the pre-existing composition-only result.
    wins_with: int | None = None          # with-camp decisive match wins
    n_matches_with: int | None = None     # with-camp decisive matches (wins + losses)
    wins_without: int | None = None       # without-camp decisive match wins
    n_matches_without: int | None = None  # without-camp decisive matches (wins + losses)


# ---------------------------------------------------------------------------
# Unit 1 — pure diff function (no DB, hand-testable)
# ---------------------------------------------------------------------------

def diff_compositions(
    with_avg: dict[str, float],
    without_avg: dict[str, float],
) -> list[CardDiff]:
    """Pure function: diff two per-card average-copies dicts.

    Cards present on only one side get avg 0.0 for the other side.
    Returns ``CardDiff`` objects sorted by ``abs(delta)`` descending.
    Empty inputs return an empty list.
    """
    all_cards = set(with_avg) | set(without_avg)
    diffs: list[CardDiff] = []
    for name in all_cards:
        avg_w = with_avg.get(name, 0.0)
        avg_wo = without_avg.get(name, 0.0)
        delta = avg_w - avg_wo
        diffs.append(CardDiff(name=name, avg_with=avg_w, avg_without=avg_wo, delta=delta))
    # Sort by abs(delta) descending; tie-break by name for determinism.
    diffs.sort(key=lambda d: (-abs(d.delta), d.name))
    return diffs


# ---------------------------------------------------------------------------
# Unit 2 — DB query (objective-search-split: one pass → plain dicts)
# ---------------------------------------------------------------------------

def subgroup_compositions(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    signature_card: str,
    *,
    board: str = "main",
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    with_winrates: bool = False,
) -> SubgroupSplit:
    """Split ``archetype``'s in-window decks on presence of ``signature_card`` in ``board``.

    Returns a ``SubgroupSplit`` whose ``diffs`` are sorted by ``abs(delta)`` descending.
    When ``since`` and ``until`` are both ``None`` the default latest-regime window is used,
    matching the behaviour of ``consensus.card_frequencies``.

    The query does a single pass: partition the archetype's deck pool by whether the deck
    contains ``signature_card`` in ``board``, then aggregate per-card total counts per
    subgroup and divide by the subgroup size to get average copies per deck.

    ``with_winrates`` (opt-in, epic-subarchetype-resolution-card-winrate): when ``True``, also
    computes each camp's decisive match win-rate (``wins_with``/``n_matches_with``/
    ``wins_without``/``n_matches_without``) via a second, cardinality-safe pass over ``rounds``
    — the W/L split that actually decides a keep/cut, which previously had to be computed by
    hand from the composition diff alone. ``False`` (the default) skips this pass entirely and
    leaves those four fields ``None`` — byte-identical to the pre-existing behaviour.
    """
    from legacy_engine.generation.consensus import _latest_regime_window

    if since is None and until is None:
        since, until = _latest_regime_window()

    # --- Single DB pass: for every card in the archetype's deck pool, sum counts
    #     split by whether the deck contains the signature card in the given board.
    #
    # Approach:
    #   1. Build the deck_pool CTE (same shape as consensus.card_frequencies).
    #   2. Flag each deck: has_sig = 1 if it contains signature_card on `board`, else 0.
    #   3. Group by (card name, board, has_sig) → sum of counts.
    #   4. Pivot in Python.

    rows = con.execute(
        """
        WITH deck_pool AS (
            SELECT d.tournament_id, d.deck_idx
            FROM decks d
            JOIN tournaments t ON t.id = d.tournament_id
            WHERE d.archetype = ?
              AND (? IS NULL OR t.provenance = ?)
              AND (? IS NULL OR t.date >= ?)
              AND (? IS NULL OR t.date < ?)
        ),
        sig_decks AS (
            -- decks in pool that contain the signature card on the requested board
            SELECT DISTINCT dp.tournament_id, dp.deck_idx
            FROM deck_pool dp
            JOIN deck_cards sc
              ON sc.tournament_id = dp.tournament_id
             AND sc.deck_idx      = dp.deck_idx
            WHERE sc.name  = ?
              AND sc.board = ?
        ),
        flagged AS (
            SELECT dp.tournament_id,
                   dp.deck_idx,
                   CASE WHEN sd.deck_idx IS NOT NULL THEN 1 ELSE 0 END AS has_sig
            FROM deck_pool dp
            LEFT JOIN sig_decks sd
              ON sd.tournament_id = dp.tournament_id
             AND sd.deck_idx      = dp.deck_idx
        ),
        card_sums AS (
            SELECT dc.name,
                   f.has_sig,
                   sum(dc.count) AS total_count,
                   count(DISTINCT (f.tournament_id, f.deck_idx)) AS n_decks
            FROM flagged f
            JOIN deck_cards dc
              ON dc.tournament_id = f.tournament_id
             AND dc.deck_idx      = f.deck_idx
            WHERE dc.board = ?
            GROUP BY dc.name, f.has_sig
        ),
        totals AS (
            SELECT has_sig,
                   count(DISTINCT (tournament_id, deck_idx)) AS n
            FROM flagged
            GROUP BY has_sig
        )
        SELECT cs.name,
               cs.has_sig,
               cs.total_count,
               t.n AS group_n
        FROM card_sums cs
        JOIN totals t ON t.has_sig = cs.has_sig
        ORDER BY cs.has_sig, cs.name
        """,
        [
            archetype, provenance, provenance, since, since, until, until,
            signature_card, board,
            board,
        ],
    ).fetchall()

    # Pivot: accumulate per-subgroup totals and group sizes.
    with_totals: dict[str, float] = {}
    without_totals: dict[str, float] = {}
    n_with = 0
    n_without = 0

    for name, has_sig, total_count, group_n in rows:
        if has_sig:
            with_totals[name] = with_totals.get(name, 0.0) + total_count
            n_with = group_n
        else:
            without_totals[name] = without_totals.get(name, 0.0) + total_count
            n_without = group_n

    # Compute per-card averages (copies per deck).
    with_avg: dict[str, float] = {}
    without_avg: dict[str, float] = {}

    if n_with > 0:
        with_avg = {name: total / n_with for name, total in with_totals.items()}
    if n_without > 0:
        without_avg = {name: total / n_without for name, total in without_totals.items()}

    diffs = diff_compositions(with_avg, without_avg)

    tier_w = tier_for_sample(n_with)
    tier_wo = tier_for_sample(n_without)
    thin = tier_w == "speculative" or tier_wo == "speculative"

    wins_with = n_matches_with = wins_without = n_matches_without = None
    if with_winrates:
        wins_with, n_matches_with, wins_without, n_matches_without = _camp_winrates(
            con, archetype, signature_card, board=board,
            since=since, until=until, provenance=provenance,
        )

    return SubgroupSplit(
        archetype=archetype,
        signature_card=signature_card,
        board=board,
        n_with=n_with,
        n_without=n_without,
        diffs=diffs,
        tier_with=tier_w,
        tier_without=tier_wo,
        thin=thin,
        wins_with=wins_with,
        n_matches_with=n_matches_with,
        wins_without=wins_without,
        n_matches_without=n_matches_without,
    )


# ---------------------------------------------------------------------------
# Unit 4 — per-camp match win-rate (opt-in; epic-subarchetype-resolution-card-winrate)
# ---------------------------------------------------------------------------

# All of the archetype's decks in-window, keyed by (tournament_id, normalized player).
_ARCHETYPE_PLAYERS_SQL = """
SELECT DISTINCT d.tournament_id, lower(trim(d.player)) AS norm
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
WHERE d.archetype = ?
  AND (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <  ?)
"""

# The subset of the archetype's decks that run the signature card on the given board.
_ARCHETYPE_WITH_SIGNATURE_SQL = """
SELECT DISTINCT d.tournament_id, lower(trim(d.player)) AS norm
FROM decks d
JOIN tournaments t ON t.id = d.tournament_id
JOIN deck_cards dc ON dc.tournament_id = d.tournament_id AND dc.deck_idx = d.deck_idx
WHERE d.archetype = ?
  AND dc.name = ? AND dc.board = ?
  AND (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <  ?)
"""

# Decisive-match resolution restricted to pairings where at least one side is the requested
# archetype. Reuses _DUP_UNIQ_CTE verbatim (SSOT, same cardinality-safe guards as
# match_results.compute_card_winrates / analytics.slot_test).
_CAMP_RESOLVE_SQL = f"""
WITH
{_DUP_UNIQ_CTE}
SELECT r.tournament_id,
       lower(trim(r.player1)) AS p1,
       lower(trim(r.player2)) AS p2,
       r.result,
       d1.archetype AS a1,
       d2.archetype AS a2,
       (du1.norm IS NOT NULL) AS amb1,
       (du2.norm IS NOT NULL) AS amb2
FROM rounds r
JOIN tournaments t ON t.id = r.tournament_id
LEFT JOIN uniq_decks d1 ON d1.tournament_id = r.tournament_id AND d1.norm = lower(trim(r.player1))
LEFT JOIN uniq_decks d2 ON d2.tournament_id = r.tournament_id AND d2.norm = lower(trim(r.player2))
LEFT JOIN dup du1 ON du1.tournament_id = r.tournament_id AND du1.norm = lower(trim(r.player1))
LEFT JOIN dup du2 ON du2.tournament_id = r.tournament_id AND du2.norm = lower(trim(r.player2))
WHERE (? IS NULL OR t.provenance = ?)
  AND (? IS NULL OR t.date >= ?)
  AND (? IS NULL OR t.date <  ?)
  AND (d1.archetype = ? OR d2.archetype = ?)
"""


def _camp_winrates(
    con: duckdb.DuckDBPyConnection,
    archetype: str,
    signature_card: str,
    *,
    board: str,
    since: str | None,
    until: str | None,
    provenance: str | None,
) -> tuple[int, int, int, int]:
    """Compute (wins_with, n_matches_with, wins_without, n_matches_without) for the camp split.

    A decisive match is attributed to whichever camp (with/without the signature card) the
    ``archetype`` hero deck belongs to. Matches where BOTH sides are ``archetype`` are excluded
    as an archetype-level mirror — identical to the mirror-exclusion convention in
    ``match_results.compute_match_results``/``compute_card_winrates`` — rather than resolved at
    camp granularity, which this feature does not attempt.
    """
    all_rows = con.execute(
        _ARCHETYPE_PLAYERS_SQL,
        [archetype, provenance, provenance, since, since, until, until],
    ).fetchall()
    all_players = {(tid, norm) for tid, norm in all_rows}

    with_rows = con.execute(
        _ARCHETYPE_WITH_SIGNATURE_SQL,
        [archetype, signature_card, board, provenance, provenance, since, since, until, until],
    ).fetchall()
    with_players = {(tid, norm) for tid, norm in with_rows}
    without_players = all_players - with_players

    resolve_rows = con.execute(
        _CAMP_RESOLVE_SQL,
        [provenance, provenance, since, since, until, until, archetype, archetype],
    ).fetchall()

    wins_with = losses_with = wins_without = losses_without = 0
    for tid, p1, p2, result, a1, a2, amb1, amb2 in resolve_rows:
        if not (p2 and p2.strip()):
            continue  # bye
        if amb1 or amb2:
            continue  # ambiguous normalized name
        if a1 is None or a2 is None:
            continue  # unmatched
        if a1 == a2:
            continue  # archetype-level mirror — excluded, matches project convention
        outcome = parse_match_result(result)
        if outcome is None or outcome.winner is None:
            continue  # bye/forfeit/draw

        if a1 == archetype:
            hero_key, hero_won = (tid, p1), outcome.winner == "p1"
        elif a2 == archetype:
            hero_key, hero_won = (tid, p2), outcome.winner == "p2"
        else:
            continue  # neither side is the requested archetype (shouldn't reach here given WHERE)

        if hero_key in with_players:
            if hero_won:
                wins_with += 1
            else:
                losses_with += 1
        elif hero_key in without_players:
            if hero_won:
                wins_without += 1
            else:
                losses_without += 1
        # else: hero deck not in either bucket (no deck_cards rows to classify it) — skip.

    return wins_with, wins_with + losses_with, wins_without, wins_without + losses_without
