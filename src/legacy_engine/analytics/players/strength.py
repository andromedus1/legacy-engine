"""Player strength scoring — per-player track record from ``standings``.

Aggregates ``standings`` rows (wins / losses / draws / rank) across events for
each identity-resolved player, then scores each player with a shrunk match-win-
rate and the project confidence tier.

Design (feature-strong-player-signal § Decision 2):
  "strong" = shrunk win-rate ≥ min_win_rate  AND
             events ≥ min_events  AND
             tier ≥ min_tier  (default: "evolving" = ≥30 decisive matches)

A single 5-0 finish fails both the event floor (events=1) AND the tier gate
(n≈7 → speculative).  This is the spec's explicit requirement: one hot finish
never qualifies as strong.

Primitives reused:
  - ``beta_binomial_shrink_to`` (matchup.py) — shrinkage toward 0.5 prior
  - ``tier_for_sample`` (confidence.py) — speculative / evolving / established
  - ``resolve_player`` (identity.py) — fold alias handles into canonical player_id

Gated-additive: when ``alias_map`` is empty (no curated entries), every player
resolves to their own normalized handle — behaviour is unchanged relative to
no-identity-resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from legacy_engine.analytics.matchup import beta_binomial_shrink_to
from legacy_engine.analytics.players.identity import resolve_player
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

if TYPE_CHECKING:
    import duckdb

# Prior centered at 0.5, strength = 15 (matches the matchup.py convention).
_SHRINK_PRIOR = 0.5
_SHRINK_STRENGTH = 15.0

# Default gate thresholds (all exposed as kwargs so callers can override).
_DEFAULT_MIN_EVENTS = 3
_DEFAULT_MIN_TIER: ConfidenceLevel = "evolving"
_DEFAULT_MIN_WIN_RATE = 0.55


# ---------------------------------------------------------------------------
# Unit 1 — PlayerRecord + compute_player_records
# ---------------------------------------------------------------------------


@dataclass
class PlayerRecord:
    """Per-player track record aggregated across events.

    Fields
    ------
    player_id : str
        Canonical identity (after alias resolution).
    display : str
        A human-readable display name (the most common raw handle seen for this
        player_id in the queried window, or the player_id itself).
    events : int
        Distinct tournaments where this player has a ``standings`` row.  Note:
        MTGO League 5-0 dumps do not produce standings rows — so a player's
        online record may understate their event count (honest, documented).
    match_wins / match_losses / match_draws : int
        Summed across all standings rows in the window.
    top_finishes : int
        Standings rows where ``rank <= cut_size`` (default: ≤8).
    win_rate_shrunk : float
        Posterior-mean shrinkage of wins/(wins+losses) toward 0.5 using the
        Beta-Binomial primitive.  n=0 → 0.5 (prior, no data).
    tier : ConfidenceLevel
        ``tier_for_sample(match_wins + match_losses)`` — the project's standard
        sample-size→trust mapping.
    """

    player_id: str
    display: str
    events: int = 0
    match_wins: int = 0
    match_losses: int = 0
    match_draws: int = 0
    top_finishes: int = 0
    win_rate_shrunk: float = 0.5
    tier: ConfidenceLevel = "speculative"


def compute_player_records(
    con: "duckdb.DuckDBPyConnection",
    *,
    alias_map: dict[str, str],
    since: str | None = None,
    until: str | None = None,
    provenance: str | None = None,
    cut_size: int = 8,
) -> dict[str, PlayerRecord]:
    """Aggregate ``standings`` into per-player track records.

    Parameters
    ----------
    con :
        DuckDB connection (must have ``standings`` and ``tournaments`` tables).
    alias_map :
        ``{handle_norm: player_id}`` from ``load_alias_map``.  Empty dict →
        every player resolves to their own normalized handle (gated-additive).
    since / until :
        Half-open ``[since, until)`` date window applied to ``tournaments.date``
        (ISO strings, ``None`` = open bound = full corpus).
    provenance :
        ``"online"`` / ``"paper"`` / ``None`` (all).  Filters ``tournaments.provenance``.
    cut_size :
        Top-N threshold for counting ``top_finishes`` (default: ≤8, i.e. top-8).

    Returns
    -------
    dict[str, PlayerRecord]
        Keyed by canonical ``player_id``.
    """
    # --- Build the windowed query over standings ← tournaments -----------------
    # We pull: tournament_id, player (raw), rank, wins, losses, draws
    # then apply window / provenance filters.

    conditions: list[str] = [
        "s.player IS NOT NULL",
        "trim(s.player) != ''",
    ]
    params: list[object] = []

    if since is not None:
        conditions.append("t.date >= ?")
        params.append(since)
    if until is not None:
        conditions.append("t.date < ?")
        params.append(until)
    if provenance is not None:
        conditions.append("t.provenance = ?")
        params.append(provenance)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            s.player        AS player_raw,
            s.tournament_id AS tid,
            s.rank          AS rank,
            s.wins          AS wins,
            s.losses        AS losses,
            s.draws         AS draws
        FROM standings s
        JOIN tournaments t ON t.id = s.tournament_id
        WHERE {where_clause}
    """

    try:
        rows = con.execute(sql, params).fetchall()
    except Exception:
        # standings or tournaments table absent — return empty (graceful no-op).
        return {}

    if not rows:
        return {}

    # --- Accumulate per-player-id --------------------------------------------
    # We need: events (distinct tids), total wins/losses/draws, top finishes.
    # Also track raw handle frequencies to pick the best display name.

    from collections import defaultdict

    wins_by_id: dict[str, int] = defaultdict(int)
    losses_by_id: dict[str, int] = defaultdict(int)
    draws_by_id: dict[str, int] = defaultdict(int)
    events_by_id: dict[str, set[str]] = defaultdict(set)
    tops_by_id: dict[str, int] = defaultdict(int)
    # frequency of each raw handle per player_id → pick most common as display
    display_freq: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for player_raw, tid, rank, wins, losses, draws in rows:
        pid = resolve_player(player_raw, alias_map)
        if not pid:
            continue
        events_by_id[pid].add(tid)
        wins_by_id[pid] += wins or 0
        losses_by_id[pid] += losses or 0
        draws_by_id[pid] += draws or 0
        if rank is not None and rank <= cut_size:
            tops_by_id[pid] += 1
        display_freq[pid][player_raw] += 1

    # --- Build PlayerRecord for each player_id --------------------------------
    records: dict[str, PlayerRecord] = {}
    all_pids = set(events_by_id)

    for pid in all_pids:
        w = wins_by_id[pid]
        l = losses_by_id[pid]  # noqa: E741 (variable named l)
        d = draws_by_id[pid]
        n_decisive = w + l
        shrunk = beta_binomial_shrink_to(
            w, n_decisive, prior_mean=_SHRINK_PRIOR, strength=_SHRINK_STRENGTH
        )
        tier = tier_for_sample(n_decisive)

        # Pick display name: raw handle with highest frequency in this window.
        freq_map = display_freq[pid]
        display = max(freq_map, key=lambda h: freq_map[h]) if freq_map else pid

        records[pid] = PlayerRecord(
            player_id=pid,
            display=display,
            events=len(events_by_id[pid]),
            match_wins=w,
            match_losses=l,
            match_draws=d,
            top_finishes=tops_by_id[pid],
            win_rate_shrunk=shrunk,
            tier=tier,
        )

    return records


# ---------------------------------------------------------------------------
# Unit 2 — is_strong + strong_player_set
# ---------------------------------------------------------------------------

_TIER_ORDER: dict[ConfidenceLevel, int] = {
    "speculative": 0,
    "evolving": 1,
    "established": 2,
}


def is_strong(
    rec: PlayerRecord,
    *,
    min_events: int = _DEFAULT_MIN_EVENTS,
    min_tier: ConfidenceLevel = _DEFAULT_MIN_TIER,
    min_win_rate: float = _DEFAULT_MIN_WIN_RATE,
) -> bool:
    """Return ``True`` iff *rec* clears ALL three strength gates.

    Gates (all must pass):
    1. ``rec.events >= min_events`` — sustained participation (default: ≥3 distinct events).
    2. ``rec.tier`` ≥ ``min_tier`` in the order speculative < evolving < established
       (default: ≥evolving, i.e. ≥30 decisive matches).
    3. ``rec.win_rate_shrunk >= min_win_rate`` — performance (default: ≥0.55 after shrinkage).

    A single 5-0 fails gates (1) and (2) by construction:
    - events=1 < 3 (event floor).
    - n≈7 decisive matches → speculative < evolving (tier gate).
    """
    if rec.events < min_events:
        return False
    if _TIER_ORDER[rec.tier] < _TIER_ORDER[min_tier]:
        return False
    if rec.win_rate_shrunk < min_win_rate:
        return False
    return True


def strong_player_set(
    records: dict[str, PlayerRecord],
    *,
    min_events: int = _DEFAULT_MIN_EVENTS,
    min_tier: ConfidenceLevel = _DEFAULT_MIN_TIER,
    min_win_rate: float = _DEFAULT_MIN_WIN_RATE,
) -> set[str]:
    """Return the set of ``player_id`` values that pass ``is_strong``.

    Compute over the consumer's window: pass in the ``records`` dict returned by
    ``compute_player_records`` for the desired date window so "strong in the current
    regime" is expressible without re-running the query.
    """
    return {
        pid
        for pid, rec in records.items()
        if is_strong(rec, min_events=min_events, min_tier=min_tier, min_win_rate=min_win_rate)
    }
