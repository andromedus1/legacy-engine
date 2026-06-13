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

from dataclasses import dataclass, field

import duckdb

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
) -> SubgroupSplit:
    """Split ``archetype``'s in-window decks on presence of ``signature_card`` in ``board``.

    Returns a ``SubgroupSplit`` whose ``diffs`` are sorted by ``abs(delta)`` descending.
    When ``since`` and ``until`` are both ``None`` the default latest-regime window is used,
    matching the behaviour of ``consensus.card_frequencies``.

    The query does a single pass: partition the archetype's deck pool by whether the deck
    contains ``signature_card`` in ``board``, then aggregate per-card total counts per
    subgroup and divide by the subgroup size to get average copies per deck.
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
    )
