"""Per-player archetype/list evolution across ban-list regimes.

``player_archetype_history`` answers: "what archetypes has this player piloted
in each ban regime, and how many decks did they register under each?"

Uses ``trends.regime_windows`` for the canonical regime partition (same SSOT as
``compute_trends``), then queries ``decks`` ← ``tournaments`` for the player's
entries in each window.  Identity is resolved via ``resolve_player`` + ``alias_map``
so all of a player's aliases pool into one history (gated-additive: empty map →
each raw handle is its own row as before).

CLI surface is deferred to the consensus story (story 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from legacy_engine.analytics.trends import RegimeWindow, regime_windows

if TYPE_CHECKING:
    import duckdb


# ---------------------------------------------------------------------------
# ArchetypeRegimeRow — one (regime, archetype) cell for a player
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArchetypeRegimeRow:
    """One (player, regime, archetype) cell in the player's history table.

    ``deck_count`` is the number of decks registered by this player under this
    archetype in this regime window.  Rows with ``archetype=None`` (unlabeled
    decks) are included so the caller can see coverage gaps — they are NOT
    filtered out silently.
    """

    regime_label: str
    archetype: str | None  # None for decks without an archetype label
    deck_count: int


# ---------------------------------------------------------------------------
# player_archetype_history
# ---------------------------------------------------------------------------


def player_archetype_history(
    con: "duckdb.DuckDBPyConnection",
    player_id: str,
    *,
    alias_map: dict[str, str],
) -> list[ArchetypeRegimeRow]:
    """Return per-regime archetype counts for one player.

    Algorithm:
    1. Build the set of normalized handles for *player_id* from *alias_map*
       (handles that resolve to this player_id via ``resolve_player``).  If the
       player has no explicit alias entries the set is ``{player_id}`` itself.
    2. Walk ``regime_windows()`` in order; for each regime query ``decks`` ←
       ``tournaments`` for rows where ``lower(trim(d.player)) IN handles_norm``
       and the tournament date is in ``[since, until)``.
    3. Aggregate ``(archetype, count)`` per regime and build ``ArchetypeRegimeRow``
       instances.  Regimes where the player has zero decks are omitted (no noise).

    Returns a list of ``ArchetypeRegimeRow``, ordered by regime then archetype.
    Gracefully returns ``[]`` when the required tables are absent.
    """
    if not player_id:
        return []

    # --- Collect all normalized handles that map to this player_id -----------
    # A player may have zero explicit alias entries (they resolve via identity).
    # In that case their only handle is player_id itself.
    handles_norm: set[str] = set()
    for handle_norm, pid in alias_map.items():
        if pid == player_id:
            handles_norm.add(handle_norm)
    # Always include the player_id itself as a possible raw handle.
    handles_norm.add(player_id)

    # --- Verify required tables exist ----------------------------------------
    try:
        tables_res = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('decks', 'tournaments')"
        ).fetchall()
        table_names = {r[0] for r in tables_res}
        if "decks" not in table_names or "tournaments" not in table_names:
            return []
    except Exception:
        return []

    # Convert handles to a SQL-injectable tuple literal.
    # DuckDB supports parameterized IN with a list parameter via executemany-style
    # binding, but the simplest safe approach for a small fixed set is to build
    # the placeholder list.
    placeholders = ", ".join(["?" for _ in handles_norm])
    handles_list = list(handles_norm)

    windows = regime_windows()
    result: list[ArchetypeRegimeRow] = []

    for window in windows:
        rows = _query_regime(con, window, handles_list, placeholders)
        for archetype, count in rows:
            result.append(
                ArchetypeRegimeRow(
                    regime_label=window.label,
                    archetype=archetype,
                    deck_count=count,
                )
            )

    return result


def _query_regime(
    con: "duckdb.DuckDBPyConnection",
    window: RegimeWindow,
    handles_list: list[str],
    placeholders: str,
) -> list[tuple[str | None, int]]:
    """Query deck counts by archetype for one regime window.

    Returns ``[(archetype, count), ...]``, ordered by count DESC then archetype.
    Returns ``[]`` when the player has no decks in this window or the query fails.
    """
    conditions: list[str] = [
        f"lower(trim(d.player)) IN ({placeholders})",
    ]
    params: list[object] = list(handles_list)

    if window.since is not None:
        conditions.append("t.date >= ?")
        params.append(window.since.isoformat())
    if window.until is not None:
        conditions.append("t.date < ?")
        params.append(window.until.isoformat())

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            d.archetype       AS archetype,
            COUNT(*)          AS deck_count
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        WHERE {where_clause}
        GROUP BY d.archetype
        ORDER BY deck_count DESC, d.archetype ASC NULLS LAST
    """

    try:
        rows = con.execute(sql, params).fetchall()
    except Exception:
        return []

    return [(archetype, int(count)) for archetype, count in rows]
